# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
GPU monitoring for Rockchip SoCs (Mali GPU via devfreq).

Reads GPU load, frequency, and governor from sysfs devfreq interface.
"""

import os
import logging
from .common import cat, GenericInterface
from .hw_detect import get_gpu_path

logger = logging.getLogger(__name__)


class GPU(GenericInterface):
    """Mali GPU statistics interface."""

    def __init__(self):
        super(GPU, self).__init__()
        self._gpu_path = get_gpu_path()
        if self._gpu_path:
            logger.info("GPU devfreq path: %s", self._gpu_path)
        else:
            logger.warning("No GPU devfreq path found")

    @property
    def available(self):
        """Check if GPU monitoring is available."""
        return self._gpu_path is not None

    def get_status(self):
        """Get current GPU status."""
        if not self._gpu_path:
            return {}

        status = {}
        # GPU load (percentage)
        load_path = os.path.join(self._gpu_path, "load")
        if os.path.isfile(load_path):
            try:
                load_val = cat(load_path).strip()
                # Mali devfreq load format: "0@00000000" or just a number
                # Some drivers report "load@freq" format
                if '@' in load_val:
                    status['load'] = int(load_val.split('@')[0])
                else:
                    status['load'] = int(load_val)
            except (ValueError, IOError):
                status['load'] = 0
        else:
            status['load'] = 0

        # Current frequency (Hz -> MHz)
        cur_freq_path = os.path.join(self._gpu_path, "cur_freq")
        if os.path.isfile(cur_freq_path):
            try:
                freq = int(cat(cur_freq_path).strip())
                status['freq'] = {'cur': freq // 1000000}  # Hz to MHz
            except (ValueError, IOError):
                status['freq'] = {'cur': 0}
        else:
            status['freq'] = {'cur': 0}

        # Min/Max frequency
        min_freq_path = os.path.join(self._gpu_path, "min_freq")
        max_freq_path = os.path.join(self._gpu_path, "max_freq")
        try:
            if os.path.isfile(min_freq_path):
                status['freq']['min'] = int(cat(min_freq_path).strip()) // 1000000
            if os.path.isfile(max_freq_path):
                status['freq']['max'] = int(cat(max_freq_path).strip()) // 1000000
        except (ValueError, IOError):
            pass

        # Governor
        gov_path = os.path.join(self._gpu_path, "governor")
        if os.path.isfile(gov_path):
            try:
                status['governor'] = cat(gov_path).strip()
            except IOError:
                status['governor'] = "unknown"
        else:
            status['governor'] = "unknown"

        # Available governors
        avail_gov_path = os.path.join(self._gpu_path, "available_governors")
        if os.path.isfile(avail_gov_path):
            try:
                status['available_governors'] = cat(avail_gov_path).strip().split()
            except IOError:
                status['available_governors'] = []

        return status


class GPUService(object):
    """Service for collecting GPU statistics."""

    def __init__(self):
        self._gpu = GPU()

    def get_status(self):
        """Get current GPU status."""
        return self._gpu.get_status()

    @property
    def available(self):
        """Check if GPU monitoring is available."""
        return self._gpu.available
