#!/usr/bin/env python3
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
CPU monitoring example - Continuously monitor CPU stats.
"""

import time
from rtop import rtop


def main():
    print("Monitoring CPU... Press Ctrl+C to stop")
    try:
        with rtop() as rockchip:
            while rockchip.ok():
                cpu = rockchip.cpu
                total = cpu.get('total', 0)
                cores = cpu.get('cores', [])

                # Build status line
                core_loads = " ".join(f"C{i}:{c.get('load', 0):4.0f}%" for i, c in enumerate(cores))
                print(f"\rTotal: {total:5.1f}% | {core_loads}", end="", flush=True)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
