# -*- coding: UTF-8 -*-
# Copyright (c) 2026 Batuhan Berkay Aydın.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

"""
Temperature monitoring for Rockchip SoCs.

Reads thermal zone temperatures and trip points from sysfs.
Rockchip devices typically have thermal zones for CPU, GPU, NPU, and SoC center.
"""

import os
import re
import time
import logging
from .common import cat, check_file

logger = logging.getLogger(__name__)

TEMPERATURE_OFFLINE = -256

_TRIP_TEMP_RE = re.compile(r'^trip_point_(\d+)_temp$')

# GUI fallback when rtop.service omits trip_points (older binary).
_TRIPS_SYSFS_CACHE = (None, 0.0)


def read_temperature(data):
    """Read temperature values from a dict of name -> path."""
    values = {}
    for name, path in data.items():
        try:
            value = float(cat(path)) / 1000.0  # millidegrees to degrees
            values[name] = value
        except (OSError, ValueError):
            values[name] = TEMPERATURE_OFFLINE
    return values


def _discover_trip_point_paths(zone_path):
    """Return sorted list of trip dicts with sysfs paths to temp/type/hyst."""
    trips = []
    try:
        entries = os.listdir(zone_path)
    except OSError:
        return trips
    for entry in entries:
        m = _TRIP_TEMP_RE.match(entry)
        if not m:
            continue
        idx = m.group(1)
        temp_path = os.path.join(zone_path, entry)
        type_path = os.path.join(zone_path, 'trip_point_{}_type'.format(idx))
        hyst_path = os.path.join(zone_path, 'trip_point_{}_hyst'.format(idx))
        if not os.path.isfile(temp_path):
            continue
        trips.append({
            'index': int(idx),
            'temp': temp_path,
            'type': type_path if os.path.isfile(type_path) else None,
            'hyst': hyst_path if os.path.isfile(hyst_path) else None,
        })
    trips.sort(key=lambda t: t['index'])
    return trips


def get_thermal_zones(thermal_path="/sys/class/thermal"):
    """Discover thermal zones: zone_name -> {'temp': path, 'trips': [...]}."""
    zones = {}
    if not os.path.isdir(thermal_path):
        logger.warning("Thermal path not found: %s", thermal_path)
        return zones

    items = os.listdir(thermal_path)
    subdirectories = [
        os.path.join(thermal_path, item)
        for item in items
        if os.path.isdir(os.path.join(thermal_path, item)) and 'thermal_zone' in item
    ]

    idx = 0
    for zone_path in subdirectories:
        path_name = os.path.join(zone_path, "type")
        path_value = os.path.join(zone_path, "temp")
        if os.path.isfile(path_name) and os.path.isfile(path_value):
            try:
                raw_name = cat(path_name).strip()
                name = raw_name.split("-")[0] if '-' in raw_name else raw_name.split("_")[0]
                name = name if name not in zones else "{name}{idx}".format(name=name, idx=idx)
                idx = idx if name not in zones else idx + 1
                if check_file(path_value):
                    zones[name] = {
                        'temp': path_value,
                        'trips': _discover_trip_point_paths(zone_path),
                    }
                    logger.info("Found thermal zone '%s' at %s", name, os.path.basename(zone_path))
            except (IOError, PermissionError):
                pass

    return dict(sorted(zones.items(), key=lambda item: item[0].lower()))


def _read_trip_points(trip_meta_list):
    """Read trip point values from discovered paths. Returns list of dicts (°C)."""
    result = []
    for meta in trip_meta_list:
        try:
            temp_mc = float(cat(meta['temp']))
            temp_c = temp_mc / 1000.0
            trip_type = 'unknown'
            if meta.get('type') and os.path.isfile(meta['type']):
                trip_type = cat(meta['type']).strip().lower()
            hyst_c = 0.0
            if meta.get('hyst') and os.path.isfile(meta['hyst']):
                hyst_c = float(cat(meta['hyst'])) / 1000.0
            result.append({
                'type': trip_type,
                'temp': temp_c,
                'hyst': hyst_c,
            })
        except (OSError, ValueError, TypeError):
            continue
    return result


def snapshot_zone_trips_millidegrees(ttl_sec=5.0):
    """Sysfs trip points keyed by zone name (millidegrees); short-lived cache."""
    global _TRIPS_SYSFS_CACHE
    now = time.monotonic()
    data, ts = _TRIPS_SYSFS_CACHE
    if data is not None and (now - ts) < ttl_sec:
        return data
    data = {}
    try:
        zones = get_thermal_zones()
    except Exception as exc:
        logger.debug("snapshot_zone_trips_millidegrees: %s", exc)
        _TRIPS_SYSFS_CACHE = ({}, now)
        return data
    for zname, meta in zones.items():
        trips = _read_trip_points(meta.get('trips', []))
        data[zname] = [
            {
                'type': t['type'],
                'temp': t['temp'] * 1000.0,
                'hyst': t['hyst'] * 1000.0,
            }
            for t in trips
        ]
    _TRIPS_SYSFS_CACHE = (data, now)
    return data


class TemperatureService(object):
    """Service for collecting temperature statistics."""

    def __init__(self):
        self._zones = {}
        sys_folder = "/sys"
        thermal_path = os.path.join(sys_folder, "class", "thermal")
        if os.path.isdir(thermal_path):
            self._zones = get_thermal_zones(thermal_path)
        if not self._zones:
            logger.warning("No thermal zones found!")
        else:
            logger.info("Thermal zones found: %s", list(self._zones.keys()))

    def get_status(self):
        """Per-zone dict with legacy name key, temp, online, trip_points (°C)."""
        status = {}
        for name, meta in self._zones.items():
            path = meta['temp']
            values = read_temperature({name: path})
            temp_c = values.get(name, TEMPERATURE_OFFLINE)
            online = temp_c != TEMPERATURE_OFFLINE
            trip_points = _read_trip_points(meta.get('trips', []))
            status[name] = {
                name: temp_c,
                'temp': temp_c,
                'online': online,
                'trip_points': trip_points,
            }
        return status
