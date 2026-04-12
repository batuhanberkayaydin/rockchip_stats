# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
rockchip_release - Display Rockchip board information.

Analogous to jetson_release for NVIDIA Jetson devices.
"""

import sys
import logging
from .core.hardware import get_hardware, get_platform_variables
from .core.hw_detect import detect_soc, get_soc_info, has_gpu, has_npu, has_rga, has_mpp
from .terminal_colors import bcolors

logger = logging.getLogger(__name__)


def get_release_info():
    """Gather all board information for display."""
    info = {}
    # Platform info
    info.update(get_platform_variables())
    # Hardware info
    hardware = get_hardware()
    info.update(hardware)
    # Feature detection
    info['GPU'] = 'Yes (Mali)' if has_gpu() else 'No'
    info['NPU'] = 'Yes (rknpu)' if has_npu() else 'No'
    info['RGA'] = 'Yes' if has_rga() else 'No'
    info['MPP'] = 'Yes' if has_mpp() else 'No'
    return info


def print_release():
    """Print formatted board information."""
    info = get_release_info()
    print(bcolors.header("=== Rockchip Board Info ==="))
    print()
    for key, value in sorted(info.items()):
        print(f"  {bcolors.bold(key + ':'):30s} {value}")
    print()


def main():
    """Entry point for rockchip_release command."""
    logging.basicConfig(level=logging.WARNING)
    print_release()


if __name__ == '__main__':
    main()
