#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

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
