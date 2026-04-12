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
Quick read example - Read all stats once and print them.
"""

from rtop import rtop


def main():
    with rtop() as rockchip:
        if rockchip.ok():
            # Print CPU info
            cpu = rockchip.cpu
            print(f"CPU Total Load: {cpu.get('total', 0):.1f}%")
            for i, core in enumerate(cpu.get('cores', [])):
                print(f"  CPU{i}: {core.get('load', 0):.1f}% @ {core.get('freq', 0) / 1000:.0f} MHz")

            # Print GPU info
            gpu = rockchip.gpu
            if gpu:
                print(f"\nGPU Load: {gpu.get('load', 0)}%")
                print(f"GPU Freq: {gpu.get('freq', 0) / 1e6:.0f} MHz")

            # Print NPU info
            npu = rockchip.npu
            if npu:
                cores = npu.get('cores', [])
                if cores:
                    for i, core in enumerate(cores):
                        print(f"NPU Core{i}: {core.get('load', 0)}%")
                print(f"NPU Freq: {npu.get('freq', 0) / 1e6:.0f} MHz")

            # Print Memory info
            mem = rockchip.memory
            if mem:
                ram = mem.get('ram', {})
                print(f"\nRAM: {ram.get('used', 0) / 1e6:.0f} / {ram.get('total', 0) / 1e6:.0f} MB")

            # Print Temperature
            temps = rockchip.temperature
            for name, val in temps.items():
                if isinstance(val, (int, float)):
                    print(f"Temp {name}: {val / 1000:.1f}°C")


if __name__ == "__main__":
    main()
