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
Fan and cooling device monitoring for Rockchip SoCs.

Reads fan speed and cooling device state from sysfs thermal interface.
Supports PWM fan control via hwmon and cooling device state via thermal subsystem.
"""

import os
import logging
from .common import cat, GenericInterface

logger = logging.getLogger(__name__)

# Fan control constants
FAN_PWM_CAP = 255
COOLING_DEVICE_PATH = "/sys/class/thermal/cooling_device"
HWMON_PATH = "/sys/class/hwmon"


def ValueToPWM(value, pwm_cap=FAN_PWM_CAP):
    """Convert percentage (0-100) to PWM value (0-255)."""
    return int(value * pwm_cap / 100)


def PWMtoValue(value, pwm_cap=FAN_PWM_CAP):
    """Convert PWM value (0-255) to percentage (0-100)."""
    return float(value * 100 / pwm_cap)


class Fan(GenericInterface):
    """Fan statistics and control interface."""

    def __init__(self):
        super(Fan, self).__init__()
        self._cooling_devices = self._detect_cooling_devices()
        self._pwm_fans = self._detect_pwm_fans()
        logger.info("Cooling devices: %d, PWM fans: %d",
                    len(self._cooling_devices), len(self._pwm_fans))

    def _detect_cooling_devices(self):
        """Detect all cooling devices."""
        devices = {}
        idx = 0
        while True:
            dev_path = "{}{}".format(COOLING_DEVICE_PATH, idx)
            if not os.path.isdir(dev_path):
                break
            # Read type
            type_path = os.path.join(dev_path, "type")
            if os.path.isfile(type_path):
                try:
                    dev_type = cat(type_path).strip()
                    cur_state_path = os.path.join(dev_path, "cur_state")
                    max_state_path = os.path.join(dev_path, "max_state")
                    device_info = {
                        'type': dev_type,
                        'path': dev_path,
                        'cur_state_path': cur_state_path,
                        'max_state_path': max_state_path,
                    }
                    devices["cooling_device{}".format(idx)] = device_info
                    logger.info("Found cooling device %d: %s", idx, dev_type)
                except (IOError, PermissionError):
                    pass
            idx += 1
        return devices

    def _detect_pwm_fans(self):
        """Detect PWM fan controllers via hwmon."""
        fans = {}
        if not os.path.isdir(HWMON_PATH):
            return fans
        for hwmon_dir in sorted(os.listdir(HWMON_PATH)):
            hwmon_path = os.path.join(HWMON_PATH, hwmon_dir)
            if not os.path.isdir(hwmon_path):
                continue
            # Look for PWM files
            for f in sorted(os.listdir(hwmon_path)):
                if f.startswith('pwm') and '_' not in f and not f.endswith('enable'):
                    pwm_path = os.path.join(hwmon_path, f)
                    pwm_num = f.replace('pwm', '')
                    fan_info = {
                        'pwm_path': pwm_path,
                        'enable_path': os.path.join(hwmon_path, "pwm{}_enable".format(pwm_num)),
                    }
                    # Try to find tachometer (RPM)
                    fan_input = os.path.join(hwmon_path, "fan{}_input".format(pwm_num))
                    has_rpm = os.path.isfile(fan_input)
                    if has_rpm:
                        fan_info['rpm_path'] = fan_input
                    has_enable = os.path.isfile(fan_info['enable_path'])
                    # Only register if there's evidence of a real fan (RPM or enable)
                    if not has_rpm and not has_enable:
                        logger.info("Skipping PWM %s at %s: no RPM or enable file", pwm_num, hwmon_path)
                        continue
                    fans["fan{}".format(pwm_num)] = fan_info
                    logger.info("Found PWM fan %s at %s", pwm_num, hwmon_path)
        return fans

    def get_status(self):
        """Get current fan/cooling status."""
        status = {}

        # Cooling devices
        for name, info in self._cooling_devices.items():
            dev_status = {'type': info['type']}
            try:
                if os.path.isfile(info['cur_state_path']):
                    dev_status['cur_state'] = int(cat(info['cur_state_path']))
                if os.path.isfile(info['max_state_path']):
                    dev_status['max_state'] = int(cat(info['max_state_path']))
            except (IOError, ValueError):
                pass
            status[name] = dev_status

        # PWM fans
        for name, info in self._pwm_fans.items():
            fan_status = {}
            try:
                if os.path.isfile(info['pwm_path']):
                    pwm_val = int(cat(info['pwm_path']))
                    fan_status['pwm'] = pwm_val
                    fan_status['speed'] = PWMtoValue(pwm_val)
                if 'rpm_path' in info and os.path.isfile(info['rpm_path']):
                    fan_status['rpm'] = int(cat(info['rpm_path']))
                if os.path.isfile(info.get('enable_path', '')):
                    fan_status['mode'] = int(cat(info['enable_path']))
            except (IOError, ValueError):
                pass
            if fan_status:
                status[name] = fan_status

        return status

    def set_fan_speed(self, fan_name, percentage):
        """Set fan speed as percentage (0-100). Requires root."""
        if fan_name not in self._pwm_fans:
            return False
        pwm_path = self._pwm_fans[fan_name]['pwm_path']
        enable_path = self._pwm_fans[fan_name].get('enable_path')
        try:
            # Set to manual mode
            if enable_path and os.path.isfile(enable_path):
                with open(enable_path, 'w') as f:
                    f.write('1')
            # Set PWM value
            pwm_value = ValueToPWM(percentage)
            with open(pwm_path, 'w') as f:
                f.write(str(pwm_value))
            return True
        except (IOError, PermissionError) as e:
            logger.error("Failed to set fan speed: %s", e)
            return False

    def set_fan_auto(self, fan_name):
        """Set fan to automatic mode. Requires root."""
        if fan_name not in self._pwm_fans:
            return False
        enable_path = self._pwm_fans[fan_name].get('enable_path')
        if enable_path and os.path.isfile(enable_path):
            try:
                with open(enable_path, 'w') as f:
                    f.write('2')
                return True
            except (IOError, PermissionError) as e:
                logger.error("Failed to set fan auto: %s", e)
        return False


class FanService(object):
    """Service for collecting fan statistics."""

    def __init__(self):
        self._fan = Fan()

    def get_status(self):
        """Get current fan status."""
        return self._fan.get_status()

    def set_fan_speed(self, fan_name, percentage):
        """Set fan speed."""
        return self._fan.set_fan_speed(fan_name, percentage)

    def set_fan_auto(self, fan_name):
        """Set fan to automatic mode."""
        return self._fan.set_fan_auto(fan_name)
