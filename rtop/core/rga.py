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
conversion. Preferred load source (root / rtop service):
  /sys/kernel/debug/rkrga/load

Load format (multi-core):
  RGA2 load:  core0: 0%, core1: 0%
  RGA3 load:  core0: 0%, core1: 0%, core2: 0%

When debugfs is unreadable (typical for unprivileged rtop), activity is
inferred from world-readable platform runtime PM:
  /sys/bus/platform/drivers/rga3_core0|rga3_core1|rga2/<addr>.rga/power/

Frequency is read via devfreq (if exposed) or clk_summary.
"""

import os
import re
import logging
from .common import cat
from .hw_detect import (
    RGA_DEVICE,
    get_rga_debug_path,
    get_rga_devfreq_path,
    get_rga_platform_cores,
    read_runtime_pm,
    runtime_pm_busy,
)

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


def _version_from_names(names):
    """Build a short version string from scheduler / driver names."""
    gens = []
    for name in names:
        upper = (name or '').upper()
        vm = re.match(r'(RGA\d+)', upper)
        tag = vm.group(1) if vm else None
        if tag and tag not in gens:
            gens.append(tag)
    return '+'.join(gens) or 'RGA'


class RGAService(object):
    """Service for collecting RGA hardware accelerator statistics."""

    def __init__(self):
        self._debug_path = get_rga_debug_path()
        self._devfreq_path = get_rga_devfreq_path()
        self._platform_cores = get_rga_platform_cores()
        self._prev_active_time = {}
        logger.info(
            "RGA debug=%s  platform_cores=%s  devfreq=%s",
            self._debug_path,
            [c.get('name') for c in self._platform_cores],
            self._devfreq_path,
        )

    @property
    def available(self):
        return bool(self._debug_path or self._platform_cores or os.path.exists(RGA_DEVICE))

    def get_status(self):
        """Get current RGA status with per-core load and frequency.

        'source' is 'debugfs' when per-core load % is available, otherwise
        'runtime' (busy=100 / idle=0 from platform runtime PM).
        """
        status = {
            'online': False,
            'active': False,
            'load': 0,
            'cores': [],
            'core_names': [],
            'freq': {},
            'version': '',
            'source': None,
        }

        parsed = self._read_debugfs_load()
        if parsed:
            status.update(parsed)
            status['source'] = 'debugfs'
            status['freq'] = self._read_freq()
            return status

        if self._apply_runtime_status(status):
            status['freq'] = self._read_freq()
            return status

        if self._debug_path or os.path.exists(RGA_DEVICE):
            # Hardware is present but neither load file nor runtime PM worked.
            status['load'] = -1
        status['freq'] = self._read_freq()
        return status

    def _read_debugfs_load(self):
        """Parse /sys/kernel/debug/rkrga/load. Return a status fragment or None."""
        if not self._debug_path:
            return None
        try:
            raw = open(self._debug_path, 'r').read()
        except (IOError, PermissionError, OSError):
            logger.debug("Cannot read RGA load from debugfs (needs root)")
            return None

        sched_loads = {}
        sched_names = {}
        for m in RGA_SCHED_REG.finditer(raw):
            idx = int(m.group(1))
            sched_names[idx] = m.group(2)
            sched_loads[idx] = int(m.group(3))

        if sched_loads:
            ordered = sorted(sched_loads)
            cores = [sched_loads[k] for k in ordered]
            names = [sched_names[k] for k in ordered]
            return {
                'cores': cores,
                'core_names': names,
                'load': max(cores),
                'online': True,
                'active': any(v > 0 for v in cores),
                'version': _version_from_names(names),
            }

        ver_match = RGA_VERSION_REG.search(raw)
        version = ver_match.group(1).upper() if ver_match else 'RGA'
        core_loads = {}
        for m in RGA_CORE_REG.finditer(raw):
            core_loads[int(m.group(1))] = int(m.group(2))
        if core_loads:
            cores = [core_loads[k] for k in sorted(core_loads)]
            return {
                'cores': cores,
                'core_names': ['core{}'.format(k) for k in sorted(core_loads)],
                'load': max(cores),
                'online': True,
                'active': any(v > 0 for v in cores),
                'version': version,
            }

        bare = re.search(r'(\d+)%', raw)
        if bare:
            v = int(bare.group(1))
            return {
                'cores': [v],
                'core_names': ['core0'],
                'load': v,
                'online': True,
                'active': v > 0,
                'version': version,
            }
        return None

    def _apply_runtime_status(self, status):
        """Fill status from platform runtime PM. Return True if cores exist."""
        if not self._platform_cores:
            return False
        loads = []
        names = []
        any_busy = False
        for core in self._platform_cores:
            name = core.get('name') or os.path.basename(core.get('path', ''))
            path = core.get('path')
            pm = read_runtime_pm(path)
            prev = self._prev_active_time.get(path)
            busy = runtime_pm_busy(pm, prev)
            if pm is not None:
                self._prev_active_time[path] = int(pm.get('active_time') or 0)
            names.append(name)
            loads.append(100 if busy else 0)
            any_busy = any_busy or busy
        status['online'] = True
        status['active'] = any_busy
        status['cores'] = loads
        status['core_names'] = names
        status['load'] = max(loads) if loads else 0
        status['version'] = _version_from_names(names)
        status['source'] = 'runtime'
        return True

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
