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
NPU monitoring for Rockchip SoCs (rknpu driver).

Reads per-core NPU load from debugfs and frequency from devfreq.

Load file: /sys/kernel/debug/rknpu/load
  Format:  "NPU load:  Core0: 12%, Core1: 5%, Core2: 0%"
  (RK3588/RK3576: 3 cores;  RK3568/RK3566/RK3562: 1 core)

Frequency: /sys/class/devfreq/<addr>.npu/cur_freq  (Hz)
"""

import os
import re
import logging
from .common import cat
from .hw_detect import (
    get_npu_devfreq_path, get_npu_devfreq_paths, get_npu_debug_path,
    get_soc_info, detect_soc
)

logger = logging.getLogger(__name__)

# Matches "Core0: 12%", "Core1: 0%", …
NPU_CORE_REG = re.compile(r'Core(\d+):\s*(\d+)%', re.IGNORECASE)


class NPUService(object):
    """Service for collecting RKNPU statistics."""

    def __init__(self):
        self._debug_path = get_npu_debug_path()
        # All NPU devfreq paths (some SoCs expose one per core)
        self._devfreq_paths = get_npu_devfreq_paths()
        # Determine expected core count from SoC info
        soc_info = get_soc_info(detect_soc())
        self._expected_cores = soc_info.get('npu_cores', 0)
        self._npu_tops = soc_info.get('npu_tops', 0)
        logger.info(
            "NPU: debug=%s  devfreq=%s  expected_cores=%d  tops=%.1f",
            self._debug_path, self._devfreq_paths,
            self._expected_cores, self._npu_tops
        )

    @property
    def available(self):
        return self._debug_path is not None or bool(self._devfreq_paths)

    def get_status(self):
        """Get current NPU status.

        Returns:
            dict with keys:
              'cores'  – list of per-core load % (index = core id)
              'load'   – average load across active cores (0-100)
              'online' – True if NPU is present and readable
              'active' – True if any core > 0 %
              'freq'   – dict with 'cur', 'min', 'max' (Hz)
              'governor' – string
              'tops'   – float, theoretical tops (0 if unknown)
        """
        status = {
            'online': False,
            'active': False,
            'load': 0,
            'cores': [],
            'freq': {},
            'governor': '',
            'tops': self._npu_tops,
        }

        # ── Per-core load from debugfs ──────────────────────────────────────
        if self._debug_path:
            try:
                raw = open(self._debug_path, 'r').read()
                core_map = {}
                for m in NPU_CORE_REG.finditer(raw):
                    core_map[int(m.group(1))] = int(m.group(2))

                if core_map:
                    # Build ordered list; pad to expected_cores if needed
                    n = max(max(core_map.keys()) + 1, self._expected_cores)
                    status['cores'] = [core_map.get(i, 0) for i in range(n)]
                    status['load'] = sum(status['cores']) // len(status['cores'])
                    status['online'] = True
                    status['active'] = any(v > 0 for v in status['cores'])
                else:
                    # Single-core SoC: bare integer on some kernels
                    bare = re.search(r'(\d+)', raw)
                    if bare:
                        v = int(bare.group(1))
                        status['cores'] = [v]
                        status['load'] = v
                        status['online'] = True
                        status['active'] = v > 0
            except (IOError, PermissionError):
                logger.debug("Cannot read NPU load (needs root)")
                status['load'] = -1   # Permission flag; GUI shows "N/A"

        # ── Frequency & governor from devfreq ───────────────────────────────
        # Use first devfreq path for freq display (they share a clock on RK3588)
        devfreq = self._devfreq_paths[0] if self._devfreq_paths else None
        if devfreq:
            status['online'] = True
            freq = {}
            for fname, key in (('cur_freq', 'cur'), ('min_freq', 'min'), ('max_freq', 'max')):
                fpath = os.path.join(devfreq, fname)
                if os.path.isfile(fpath):
                    try:
                        freq[key] = int(cat(fpath).strip())   # Hz
                    except (ValueError, IOError):
                        pass
            status['freq'] = freq
            gov_path = os.path.join(devfreq, 'governor')
            if os.path.isfile(gov_path):
                try:
                    status['governor'] = cat(gov_path).strip()
                except IOError:
                    pass

        return status
