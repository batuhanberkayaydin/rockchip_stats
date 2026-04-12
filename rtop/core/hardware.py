# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Rockchip board detection and hardware identification.
"""

import os
import platform
import logging

try:
    import distro
except ImportError:
    distro = platform

from .common import cat
from .hw_detect import detect_soc, get_soc_info, get_board_model, get_board_serial

logger = logging.getLogger(__name__)


def get_parameter(path):
    """Read a parameter from a sysfs path."""
    if os.path.isfile(path):
        try:
            return cat(path).strip()
        except (IOError, PermissionError):
            return None
    return None


def get_platform_variables():
    """Get platform information."""
    return {
        'Machine': platform.machine(),
        'System': platform.system(),
        'Distribution': " ".join(distro.linux_distribution()) if hasattr(distro, 'linux_distribution') else "Unknown",
        'Release': platform.release(),
        'Python': platform.python_version(),
    }


def get_rockchip_variables():
    """Get Rockchip-specific hardware variables."""
    soc_id = detect_soc()
    soc_info = get_soc_info(soc_id)

    hardware = {
        'SoC': soc_info.get('name', 'Unknown'),
        'SoC ID': soc_id or 'Unknown',
        'Board': get_board_model(),
        'Serial': get_board_serial(),
        'Compatible': get_parameter("/sys/firmware/devicetree/base/compatible") or 'Unknown',
    }

    # Add CPU info
    cpuinfo = _read_cpuinfo()
    if cpuinfo:
        hardware.update(cpuinfo)

    # Add kernel version
    hardware['Kernel'] = platform.release()

    return hardware


def _read_cpuinfo():
    """Read CPU information from /proc/cpuinfo."""
    info = {}
    try:
        with open("/proc/cpuinfo", 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith('Hardware'):
                    info['Hardware'] = line.split(':')[1].strip()
                elif line.startswith('model name'):
                    info['CPU Model'] = line.split(':')[1].strip()
                    break
    except IOError:
        pass
    return info


def get_hardware():
    """Get hardware information for the current board."""
    platform_board = platform.machine()
    logger.info("Hardware detected: %s", platform_board)

    if platform_board == 'aarch64':
        rockchip = get_rockchip_variables()
        soc_id = rockchip.get('SoC ID', 'unknown')
        if soc_id != 'unknown':
            logger.info("Rockchip SoC detected: %s", rockchip.get('SoC'))
        else:
            logger.warning("No Rockchip SoC detected!")
        return rockchip
    elif platform_board == 'armv7l':
        rockchip = get_rockchip_variables()
        logger.info("Rockchip ARM32 detected: %s", rockchip.get('SoC'))
        return rockchip
    else:
        logger.warning("Unrecognized board: %s", platform_board)
        return get_platform_variables()
