# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

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

# Match: "core0: 12%", "core1: 0%", etc. (case-insensitive)
RGA_CORE_REG = re.compile(r'core(\d+):\s*(\d+)%', re.IGNORECASE)

# Match a version tag like "RGA2" or "RGA3" before "load:"
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
            # Parse version tag (RGA2 / RGA3)
            ver_match = RGA_VERSION_REG.search(raw)
            if ver_match:
                status['version'] = ver_match.group(1).upper()

            # Parse per-core loads
            core_loads = {}
            for m in RGA_CORE_REG.finditer(raw):
                core_loads[int(m.group(1))] = int(m.group(2))

            if core_loads:
                status['cores'] = [core_loads[k] for k in sorted(core_loads)]
                status['load'] = max(status['cores'])
                status['online'] = True
                status['active'] = any(v > 0 for v in status['cores'])
            else:
                # Fallback: try single bare percentage
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
