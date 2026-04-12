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
Test configuration and fixtures for rtop tests.
"""

import os
import sys
import pytest
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from rtop.core.common import GenericInterface
from rtop.core.exceptions import RtopException


@pytest.fixture
def mock_sysfs(tmp_path):
    """Create a mock sysfs directory structure for testing."""
    # CPU
    cpu_dir = tmp_path / "sys" / "devices" / "system" / "cpu"
    for i in range(4):
        cpu_freq_dir = cpu_dir / f"cpu{i}" / "cpufreq"
        cpu_freq_dir.mkdir(parents=True)
        (cpu_freq_dir / "scaling_cur_freq").write_text(f"{1800000 + i * 100000}")
        (cpu_freq_dir / "scaling_min_freq").write_text("408000")
        (cpu_freq_dir / "scaling_max_freq").write_text("2400000")
        (cpu_freq_dir / "scaling_governor").write_text("ondemand")
        (cpu_freq_dir / "scaling_available_governors").write_text("conservative ondemand userspace powersave performance schedutil")

    # GPU devfreq
    gpu_dir = tmp_path / "sys" / "class" / "devfreq" / "fb000000.gpu"
    gpu_dir.mkdir(parents=True)
    (gpu_dir / "load").write_text("0@800000000")
    (gpu_dir / "cur_freq").write_text("800000000")
    (gpu_dir / "min_freq").write_text("200000000")
    (gpu_dir / "max_freq").write_text("1000000000")
    (gpu_dir / "governor").write_text("simple_ondemand")
    (gpu_dir / "available_governors").write_text("simple_ondemand performance powersave")

    # NPU devfreq
    npu_dir = tmp_path / "sys" / "class" / "devfreq" / "fdab0000.npu"
    npu_dir.mkdir(parents=True)
    (npu_dir / "cur_freq").write_text("1000000000")

    # NPU debugfs load
    npu_debug = tmp_path / "sys" / "kernel" / "debug" / "rknpu"
    npu_debug.mkdir(parents=True)
    (npu_debug / "load").write_text("Core0:  0%\nCore1:  0%\nCore2:  0%")

    # Thermal zones
    thermal_dir = tmp_path / "sys" / "class" / "thermal"
    for i, name in enumerate(["cpu-thermal", "gpu-thermal"]):
        tz_dir = thermal_dir / f"thermal_zone{i}"
        tz_dir.mkdir(parents=True)
        (tz_dir / "temp").write_text(f"{45000 + i * 5000}")
        (tz_dir / "type").write_text(name)

    # Cooling devices
    for i in range(2):
        cd_dir = thermal_dir / f"cooling_device{i}"
        cd_dir.mkdir(parents=True)
        (cd_dir / "cur_state").write_text("0")
        (cd_dir / "max_state").write_text("10")
        (cd_dir / "type").write_text("fan" if i == 0 else "cpu")

    # Device tree compatible
    dt_dir = tmp_path / "sys" / "firmware" / "devicetree" / "base"
    dt_dir.mkdir(parents=True)
    (dt_dir / "compatible").write_text("rockchip,rk3588-evb\0rockchip,rk3588")

    return tmp_path


@pytest.fixture
def generic_interface():
    """Create a GenericInterface for testing."""
    return GenericInterface(
        name="test",
        data={
            "key1": "value1",
            "key2": 42,
            "nested": {"a": 1, "b": 2},
        }
    )


@pytest.fixture
def mock_procfs(tmp_path):
    """Create a mock procfs directory structure."""
    proc_dir = tmp_path / "proc"
    proc_dir.mkdir()

    # /proc/stat
    (proc_dir / "stat").write_text(
        "cpu  2255 34 2290 22625563 6290 127 456\n"
        "cpu0 1130 17 1145 5656390 3145 63 228\n"
        "cpu1 1125 17 1145 5656390 3145 64 228\n"
    )

    # /proc/meminfo
    (proc_dir / "meminfo").write_text(
        "MemTotal:       8192000 kB\n"
        "MemFree:        4096000 kB\n"
        "MemAvailable:   5120000 kB\n"
        "Buffers:         256000 kB\n"
        "Cached:         1024000 kB\n"
        "SwapCached:           0 kB\n"
        "Active:         2048000 kB\n"
        "Inactive:       1024000 kB\n"
        "SwapTotal:      4096000 kB\n"
        "SwapFree:       4096000 kB\n"
        "Shmem:           128000 kB\n"
        "CmaTotal:        256000 kB\n"
        "CmaFree:         128000 kB\n"
    )

    # /proc/uptime
    (proc_dir / "uptime").write_text("12345.67 23456.89")

    return tmp_path
