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
NPU monitoring example - Monitor Rockchip NPU usage.
"""

from rtop import rtop


def main():
    print("Monitoring NPU... Press Ctrl+C to stop")
    try:
        with rtop() as rockchip:
            while rockchip.ok():
                npu = rockchip.npu
                if not npu:
                    print("No NPU detected on this device")
                    break

                cores = npu.get('cores', [])
                freq = npu.get('freq', 0)

                if cores:
                    core_str = " ".join(f"Core{i}:{c.get('load', 0):3d}%" for i, c in enumerate(cores))
                    avg = sum(c.get('load', 0) for c in cores) / len(cores)
                    print(f"\rNPU Avg: {avg:5.1f}% | {core_str} | Freq: {freq / 1e6:.0f} MHz", end="", flush=True)
                else:
                    load = npu.get('total_load', 0)
                    print(f"\rNPU Load: {load:5.1f}% | Freq: {freq / 1e6:.0f} MHz", end="", flush=True)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
