#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

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
