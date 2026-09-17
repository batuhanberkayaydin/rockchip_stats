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

            # Print RGA / MPP engines
            rga = rockchip.rga
            if rga:
                print(f"\nRGA online={rga.get('online')} active={rga.get('active')} "
                      f"load={rga.get('load')} source={rga.get('source')}")
                for i, core in enumerate(rga.get('cores', [])):
                    name = (rga.get('core_names') or [])
                    label = name[i] if i < len(name) else f"C{i}"
                    print(f"  {label}: {core}%")

            mpp = rockchip.mpp
            if mpp:
                print(f"MPP any_active={mpp.get('any_active')}")
                for group in ('decoders', 'encoders', 'others'):
                    for name, info in (mpp.get(group) or {}).items():
                        print(f"  {name}: active={info.get('active')} "
                              f"source={info.get('source')} tasks={info.get('task_count')}")
            temps = rockchip.temperature
            for name, val in temps.items():
                if isinstance(val, (int, float)):
                    print(f"Temp {name}: {val / 1000:.1f}°C")

            # Print thermal trip points (millidegrees from API)
            thermal = rockchip.thermal
            for zone, data in thermal.items():
                print(f"\nThermal {zone}: {data['temp'] / 1000:.1f}°C")
                for tp in data.get('trip_points', []):
                    print(f"  {tp['type']}: {tp['temp'] / 1000:.1f}°C")

            # Print cpufreq/devfreq throttle state (cur_state / max_state)
            fan = rockchip.fan or {}
            throttle_types = ('thermal-cpufreq', 'thermal-devfreq', 'cpufreq', 'devfreq')
            for name, info in fan.items():
                if not isinstance(info, dict):
                    continue
                dev_type = str(info.get('type', '')).lower()
                if dev_type in throttle_types or 'cpufreq' in dev_type or 'devfreq' in dev_type:
                    cur = info.get('cur_state', 0)
                    mx = info.get('max_state', 0)
                    print(f"Throttle {name}: {cur}/{mx}")


if __name__ == "__main__":
    main()
