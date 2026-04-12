#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

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
