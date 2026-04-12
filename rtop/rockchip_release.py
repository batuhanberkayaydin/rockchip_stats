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
