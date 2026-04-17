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
RGA (Rockchip Graphics Acceleration) monitoring.

RGA is Rockchip's 2D hardware accelerator for rotation, scaling, and color
conversion. Modern kernels expose per-core loads via:
  /sys/kernel/debug/rkrga/load

Load format (multi-core):
  RGA2 load:  core0: 0%, core1: 0%
  RGA3 load:  core0: 0%, core1: 0%, core2: 0%

Frequency is read via devfreq (if exposed) or clk_summary.
"""

import os
import re
import logging
from .common import cat
from .hw_detect import get_rga_debug_path, get_rga_devfreq_path

logger = logging.getLogger(__name__)

# Legacy "core0: 12%" format (older kernels)
RGA_CORE_REG = re.compile(r'core(\d+):\s*(\d+)%', re.IGNORECASE)

# Modern scheduler block:
#   scheduler[0]: rga3_core0
#       load = 3%
RGA_SCHED_REG = re.compile(
    r'scheduler\[(\d+)\]:\s*(\S+).*?load\s*=\s*(\d+)%',
    re.IGNORECASE | re.DOTALL)

# Version tag — modern output puts the name inside scheduler entries
# (rga3_core0, rga2, …). Legacy output has "RGA2 load:" / "RGA3 load:".
RGA_VERSION_REG = re.compile(r'(RGA\w*)\s+load', re.IGNORECASE)


class RGAService(object):
    """Service for collecting RGA hardware accelerator statistics."""

    def __init__(self):
        self._debug_path = get_rga_debug_path()
        self._devfreq_path = get_rga_devfreq_path()
        if self._debug_path:
            logger.info("RGA debug path: %s", self._debug_path)
        else:
            logger.info("No RGA debugfs found")
        if self._devfreq_path:
            logger.info("RGA devfreq path: %s", self._devfreq_path)

    @property
    def available(self):
        return self._debug_path is not None

    def get_status(self):
        """Get current RGA status with per-core load and frequency."""
        status = {'online': False, 'load': 0, 'cores': [], 'freq': {}, 'version': ''}

        if not self._debug_path:
            return status

        # --- Load ---
        try:
            raw = open(self._debug_path, 'r').read()

            # Modern scheduler format. Each scheduler entry carries a name
            # like "rga3_core0" / "rga2" and a "load = N%" line.
            sched_loads = {}   # idx -> load
            sched_names = {}   # idx -> scheduler name
            for m in RGA_SCHED_REG.finditer(raw):
                idx = int(m.group(1))
                sched_names[idx] = m.group(2)
                sched_loads[idx] = int(m.group(3))

            if sched_loads:
                ordered = sorted(sched_loads)
                status['cores'] = [sched_loads[k] for k in ordered]
                status['core_names'] = [sched_names[k] for k in ordered]
                status['load'] = max(status['cores'])
                status['online'] = True
                status['active'] = any(v > 0 for v in status['cores'])
                # Version from first scheduler name (rga3_core0 -> RGA3)
                first = sched_names[ordered[0]].upper()
                vm = re.match(r'(RGA\d+)', first)
                status['version'] = vm.group(1) if vm else first
            else:
                # Legacy "RGA2 load: core0: 0%, core1: 0%" format
                ver_match = RGA_VERSION_REG.search(raw)
                if ver_match:
                    status['version'] = ver_match.group(1).upper()
                core_loads = {}
                for m in RGA_CORE_REG.finditer(raw):
                    core_loads[int(m.group(1))] = int(m.group(2))
                if core_loads:
                    status['cores'] = [core_loads[k] for k in sorted(core_loads)]
                    status['load'] = max(status['cores'])
                    status['online'] = True
                    status['active'] = any(v > 0 for v in status['cores'])
                else:
                    bare = re.search(r'(\d+)%', raw)
                    if bare:
                        v = int(bare.group(1))
                        status['cores'] = [v]
                        status['load'] = v
                        status['online'] = True
                        status['active'] = v > 0
        except (IOError, PermissionError):
            logger.debug("Cannot read RGA load (needs root)")
            status['load'] = -1   # permission flag for GUI

        # --- Frequency ---
        status['freq'] = self._read_freq()
        return status

    def _read_freq(self):
        """Read RGA frequency — prefer devfreq, fall back to clk_summary."""
        # devfreq (cur_freq in Hz)
        if self._devfreq_path:
            cur_path = os.path.join(self._devfreq_path, 'cur_freq')
            if os.path.isfile(cur_path):
                try:
                    return {'cur': int(cat(cur_path).strip())}  # return Hz; GUI converts
                except (ValueError, IOError):
                    pass

        # clk_summary fallback (needs root)
        clk_path = "/sys/kernel/debug/clk/clk_summary"
        if os.path.isfile(clk_path):
            try:
                with open(clk_path, 'r') as f:
                    for line in f:
                        lo = line.lower()
                        if 'rga' in lo and 'clk' in lo:
                            parts = line.split()
                            # format: name  enable_cnt  prepare_cnt  rate  ...
                            if len(parts) >= 4:
                                try:
                                    rate = int(parts[3])
                                    if rate > 0:
                                        return {'cur': rate}  # Hz
                                except ValueError:
                                    pass
            except (IOError, PermissionError):
                pass
        return {}
