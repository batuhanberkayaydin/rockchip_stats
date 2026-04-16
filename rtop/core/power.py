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
Power monitoring for Rockchip SoCs.

Scans /sys/class/hwmon for INA2xx-style power sensors (INA219 / INA226 /
INA3221 are the common ones on RK3588/RK3576 dev-boards) and returns a
jtop-shaped dict:

    {
      'rail': { 'VDD_CORE': {'power': <mW>, 'volt': <mV>, 'curr': <mA>}, ... },
      'tot':  {'power': <mW>, 'volt': <mV>, 'curr': <mA>, 'name': 'ALL'}
    }

Units match jtop so the existing ``unit_to_string(value, 'm', 'W')`` helpers
keep working.  Returns ``None`` when no rails are found so callers can hide
the power UI entirely on boards without telemetry.
"""

import os
import re
import logging
from .common import cat

logger = logging.getLogger(__name__)

_HWMON_ROOT = '/sys/class/hwmon'

# Drivers that expose power telemetry. Thermal hwmon nodes (soc_thermal etc.)
# also live under /sys/class/hwmon so we allowlist the known power chips.
_POWER_DRIVER_HINTS = (
    'ina2',       # ina219, ina226
    'ina3',       # ina3221
    'fusb',       # usb-c PD controllers (rare but possible)
    'rk8',        # rk808/rk809/rk817 PMICs expose limited power data
    'bq',         # ti bq* battery gauges
)

_INPUT_RE = re.compile(r'^(in|curr|power)(\d+)_input$')


def _read_int(path):
    try:
        return int(cat(path).strip())
    except (IOError, ValueError, PermissionError):
        return None


def _read_label(hwmon_path, idx, kind):
    """Read <kind><idx>_label (e.g. in1_label -> 'VDD_CORE'). Fallback: raw."""
    lbl_path = os.path.join(hwmon_path, '{}{}_label'.format(kind, idx))
    if os.path.isfile(lbl_path):
        try:
            return cat(lbl_path).strip()
        except (IOError, PermissionError):
            pass
    return None


def _driver_is_power(name):
    if not name:
        return False
    lo = name.lower()
    return any(hint in lo for hint in _POWER_DRIVER_HINTS)


def _scan_hwmon_rails():
    """Return a flat dict: rail_name -> {'power'?, 'volt'?, 'curr'?} (all in
    milli-units to match jtop's expectations)."""
    rails = {}
    if not os.path.isdir(_HWMON_ROOT):
        return rails

    for entry in sorted(os.listdir(_HWMON_ROOT)):
        hwmon_path = os.path.join(_HWMON_ROOT, entry)
        name_path = os.path.join(hwmon_path, 'name')
        if not os.path.isfile(name_path):
            continue
        try:
            name = cat(name_path).strip()
        except (IOError, PermissionError):
            continue
        if not _driver_is_power(name):
            continue

        for fname in sorted(os.listdir(hwmon_path)):
            m = _INPUT_RE.match(fname)
            if not m:
                continue
            kind, idx = m.group(1), m.group(2)
            value = _read_int(os.path.join(hwmon_path, fname))
            if value is None:
                continue
            label = _read_label(hwmon_path, idx, kind) or '{}_{}{}'.format(
                name.upper(), kind.upper(), idx)
            rail = rails.setdefault(label, {})

            if kind == 'power':
                # hwmon power*_input is in microwatts → convert to mW
                rail['power'] = value // 1000
            elif kind == 'in':
                # voltage already in millivolts
                rail['volt'] = value
            elif kind == 'curr':
                # current already in milliamps
                rail['curr'] = value

    # Derive power when only V+I is reported.
    for rail in rails.values():
        if 'power' not in rail and 'volt' in rail and 'curr' in rail:
            rail['power'] = (rail['volt'] * rail['curr']) // 1000
    return rails


class Power(object):
    """Aggregate power readings from all available hwmon rails."""

    def __init__(self):
        rails = _scan_hwmon_rails()
        self._available = bool(rails)
        if self._available:
            logger.info("Power rails detected: %s", list(rails.keys()))
        else:
            logger.info("No power rails found on this board")

    @property
    def available(self):
        return self._available

    def get_status(self):
        rails = _scan_hwmon_rails()
        if not rails:
            return None
        total_power = sum(r.get('power', 0) for r in rails.values())
        return {
            'rail': rails,
            'tot': {'power': total_power, 'name': 'ALL'},
        }


class PowerService(object):

    def __init__(self):
        self._power = Power()

    @property
    def available(self):
        return self._power.available

    def get_status(self):
        return self._power.get_status()
