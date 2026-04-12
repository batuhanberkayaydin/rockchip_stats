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

Reads thermal zone temperatures from sysfs.
Rockchip devices typically have thermal zones for CPU, GPU, NPU, and SoC center.
"""

import os
import logging
from .common import cat, check_file

logger = logging.getLogger(__name__)

TEMPERATURE_OFFLINE = -256


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


def get_thermal_zones(thermal_path="/sys/class/thermal"):
    """Discover all thermal zones and their temperature paths."""
    temperature = {}
    if not os.path.isdir(thermal_path):
        logger.warning("Thermal path not found: %s", thermal_path)
        return temperature

    items = os.listdir(thermal_path)
    subdirectories = [os.path.join(thermal_path, item)
                      for item in items
                      if os.path.isdir(os.path.join(thermal_path, item)) and 'thermal_zone' in item]

    idx = 0
    for zone_path in subdirectories:
        path_name = os.path.join(zone_path, "type")
        path_value = os.path.join(zone_path, "temp")
        if os.path.isfile(path_name) and os.path.isfile(path_value):
            try:
                raw_name = cat(path_name).strip()
                # Clean up name
                name = raw_name.split("-")[0] if '-' in raw_name else raw_name.split("_")[0]
                # Handle duplicate names
                name = name if name not in temperature else "{name}{idx}".format(name=name, idx=idx)
                idx = idx if name not in temperature else idx + 1
                # Store temperature path
                if check_file(path_value):
                    temperature[name] = path_value
                    logger.info("Found thermal zone '%s' at %s", name, os.path.basename(zone_path))
            except (IOError, PermissionError):
                pass

    return dict(sorted(temperature.items(), key=lambda item: item[0].lower()))


class TemperatureService(object):
    """Service for collecting temperature statistics."""

    def __init__(self):
        self._temperature = {}
        sys_folder = "/sys"
        thermal_path = os.path.join(sys_folder, "class", "thermal")
        if os.path.isdir(thermal_path):
            self._temperature = get_thermal_zones(thermal_path)
        if not self._temperature:
            logger.warning("No thermal zones found!")
        else:
            logger.info("Thermal zones found: %s", list(self._temperature.keys()))

    def get_status(self):
        """Get current temperature readings."""
        status = {}
        for name, path in self._temperature.items():
            values = read_temperature({name: path})
            values['online'] = values.get(name, TEMPERATURE_OFFLINE) != TEMPERATURE_OFFLINE
            status[name] = values
        return status
