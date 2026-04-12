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
CPU monitoring for Rockchip SoCs.

Reads per-core frequency, governor, and load from sysfs and /proc/stat.
Supports big.LITTLE architectures (e.g., RK3588: 4x A55 + 4x A76).
"""

import os
import re
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)

# Regex patterns
REGEXP = re.compile(r'(.+?): ((.*))')
CPU_PROG_REG = re.compile(r'cpu(.+?) ((.*))')

# CPU sysfs paths
CPU_BASE_PATH = "/sys/devices/system/cpu"
CPU_FREQ_PATH = CPU_BASE_PATH + "/cpu{core}/cpufreq"


def cpu_info():
    """Read CPU information from /proc/cpuinfo."""
    list_cpu = {}
    num_cpu = 0
    try:
        with open("/proc/cpuinfo", "r") as fp:
            for line in fp:
                match = REGEXP.search(line)
                if match:
                    key = match.group(1).rstrip()
                    value = match.group(2).rstrip()
                    if key == "processor":
                        num_cpu = int(value)
                        list_cpu[num_cpu] = {}
                        continue
                    if key == "model name":
                        list_cpu[num_cpu]['model'] = value
                    elif key == "BogoMIPS":
                        list_cpu[num_cpu]['bogomips'] = value
                    elif key == "Hardware":
                        list_cpu[num_cpu]['hardware'] = value
    except IOError:
        logger.warning("Cannot read /proc/cpuinfo")
    return list_cpu


def _read_cpu_freq(core):
    """Read frequency info for a specific CPU core."""
    freq_path = CPU_FREQ_PATH.format(core=core)
    freq = {}
    try:
        cur_path = os.path.join(freq_path, "scaling_cur_freq")
        if os.path.isfile(cur_path):
            with open(cur_path, 'r') as f:
                freq['cur'] = int(f.read().strip()) // 1000  # Convert to MHz
    except (IOError, ValueError):
        pass
    try:
        max_path = os.path.join(freq_path, "scaling_max_freq")
        if os.path.isfile(max_path):
            with open(max_path, 'r') as f:
                freq['max'] = int(f.read().strip()) // 1000
    except (IOError, ValueError):
        pass
    try:
        min_path = os.path.join(freq_path, "scaling_min_freq")
        if os.path.isfile(min_path):
            with open(min_path, 'r') as f:
                freq['min'] = int(f.read().strip()) // 1000
    except (IOError, ValueError):
        pass
    return freq


def _read_cpu_governor(core):
    """Read the governor for a specific CPU core."""
    gov_path = os.path.join(CPU_FREQ_PATH.format(core=core), "scaling_governor")
    try:
        if os.path.isfile(gov_path):
            with open(gov_path, 'r') as f:
                return f.read().strip()
    except IOError:
        pass
    return "unknown"


def _read_cpu_online(core):
    """Check if a CPU core is online."""
    online_path = os.path.join(CPU_BASE_PATH, "cpu{}".format(core), "online")
    try:
        if os.path.isfile(online_path):
            with open(online_path, 'r') as f:
                return int(f.read().strip()) == 1
    except (IOError, ValueError):
        pass
    return True  # Assume online if can't read


class CPUService(object):
    """Service for collecting CPU statistics."""

    def __init__(self):
        self._num_cores = self._detect_cores()
        self._prev_stat = self._read_proc_stat()
        logger.info("CPU cores detected: %d", self._num_cores)

    def _detect_cores(self):
        """Detect the number of CPU cores."""
        count = 0
        while os.path.isdir(os.path.join(CPU_BASE_PATH, "cpu{}".format(count))):
            count += 1
        return count

    def _read_proc_stat(self):
        """Read CPU times from /proc/stat."""
        stat = {}
        try:
            with open("/proc/stat", 'r') as f:
                for line in f:
                    match = CPU_PROG_REG.match(line)
                    if match:
                        core_id = match.group(1).strip()
                        values = match.group(2).strip().split()
                        # user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice
                        times = [int(v) for v in values]
                        stat[core_id] = times
        except IOError:
            logger.warning("Cannot read /proc/stat")
        return stat

    @property
    def num_cores(self):
        """Return the number of CPU cores."""
        return self._num_cores

    def get_status(self):
        """Get current CPU status for all cores."""
        status = {}
        # Read current stat
        current_stat = self._read_proc_stat()

        # Per-core info
        for core in range(self._num_cores):
            core_status = {}
            # Online status
            core_status['online'] = _read_cpu_online(core)
            # Frequency
            core_status['freq'] = _read_cpu_freq(core)
            # Governor
            core_status['governor'] = _read_cpu_governor(core)
            # CPU load calculation
            core_id = str(core)
            if core_id in current_stat and core_id in self._prev_stat:
                prev = self._prev_stat[core_id]
                curr = current_stat[core_id]
                # Calculate delta
                prev_idle = prev[3] + prev[4]  # idle + iowait
                curr_idle = curr[3] + curr[4]
                prev_total = sum(prev)
                curr_total = sum(curr)
                delta_total = curr_total - prev_total
                delta_idle = curr_idle - prev_idle
                if delta_total > 0:
                    load = (1.0 - float(delta_idle) / float(delta_total)) * 100.0
                    core_status['load'] = round(load, 1)
                else:
                    core_status['load'] = 0.0
            else:
                core_status['load'] = 0.0
            status[core] = core_status

        # Total CPU load
        total_id = ''
        if total_id in current_stat and total_id in self._prev_stat:
            prev = self._prev_stat[total_id]
            curr = current_stat[total_id]
            prev_idle = prev[3] + prev[4]
            curr_idle = curr[3] + curr[4]
            prev_total = sum(prev)
            curr_total = sum(curr)
            delta_total = curr_total - prev_total
            delta_idle = curr_idle - prev_idle
            if delta_total > 0:
                total_load = (1.0 - float(delta_idle) / float(delta_total)) * 100.0
                status['total'] = {'load': round(total_load, 1)}
            else:
                status['total'] = {'load': 0.0}
        else:
            status['total'] = {'load': 0.0}

        # Update previous stat
        self._prev_stat = current_stat
        return status
