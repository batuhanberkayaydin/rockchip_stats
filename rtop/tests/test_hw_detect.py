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
Tests for core.hw_detect module.
"""

import os
import pytest
from unittest.mock import patch
from rtop.core.hw_detect import (
    detect_soc, has_gpu, has_npu, has_mpp, has_rga, get_npu_devfreq_paths,
    list_platform_devices_by_suffix, get_mpp_platform_devices,
    get_rga_platform_cores, read_runtime_pm, runtime_pm_busy,
)


class TestDetectSoc:
    """Tests for SoC detection."""

    def test_detect_rk3588(self, tmp_path):
        compatible = tmp_path / "compatible"
        compatible.write_text("rockchip,rk3588-evb\x00rockchip,rk3588")
        with patch('rtop.core.hw_detect.os.path.isfile', return_value=True):
            with patch('builtins.open', return_value=compatible.open('r')):
                soc = detect_soc()
                assert soc == 'rk3588'

    def test_detect_unknown(self):
        with patch('rtop.core.hw_detect.os.path.isfile', return_value=False):
            soc = detect_soc()
            assert soc is None


class TestDetectFeatures:
    """Tests for hardware feature detection."""

    def test_detect_gpu(self, mock_sysfs):
        gpu_path = str(mock_sysfs / "sys" / "class" / "devfreq" / "fb000000.gpu")
        with patch('rtop.core.hw_detect.os.path.exists', side_effect=lambda p: gpu_path in p or os.path.exists(p)):
            result = has_gpu()
            assert isinstance(result, bool)


class TestFindDevfreqPaths:
    """Tests for devfreq path discovery."""

    def test_find_devfreq(self, mock_sysfs):
        with patch('rtop.core.hw_detect.os.path.exists', return_value=True):
            with patch('rtop.core.hw_detect.os.listdir', return_value=["fdab0000.npu"]):
                paths = get_npu_devfreq_paths()
                assert isinstance(paths, list)


def _write_runtime(dev, status='suspended', usage=0, active_time=0):
    power = dev / 'power'
    power.mkdir(parents=True, exist_ok=True)
    (power / 'runtime_status').write_text('{}\n'.format(status))
    (power / 'runtime_usage').write_text('{}\n'.format(usage))
    (power / 'runtime_active_time').write_text('{}\n'.format(active_time))


class TestPlatformRuntimePm:
    def test_list_by_suffix(self, tmp_path):
        (tmp_path / 'fdb90000.jpegd').mkdir()
        (tmp_path / 'fdba0000.jpege-core').mkdir()
        (tmp_path / 'fdba4000.jpege-core').mkdir()
        (tmp_path / 'jpege-ccu').mkdir()
        jpegd = list_platform_devices_by_suffix('jpegd', str(tmp_path))
        assert len(jpegd) == 1
        assert jpegd[0].endswith('fdb90000.jpegd')
        jpege = list_platform_devices_by_suffix('jpege-core', str(tmp_path))
        assert len(jpege) == 2
        assert list_platform_devices_by_suffix('jpege-ccu', str(tmp_path)) == []

    def test_mpp_indexed_cores(self, tmp_path):
        (tmp_path / 'fdba0000.jpege-core').mkdir()
        (tmp_path / 'fdba4000.jpege-core').mkdir()
        (tmp_path / 'fdb90000.jpegd').mkdir()
        c0 = get_mpp_platform_devices('jpege-core0', str(tmp_path))
        c1 = get_mpp_platform_devices('jpege-core1', str(tmp_path))
        assert c0[0].endswith('fdba0000.jpege-core')
        assert c1[0].endswith('fdba4000.jpege-core')
        assert get_mpp_platform_devices('jpege-core9', str(tmp_path)) == []
        jpegd = get_mpp_platform_devices('jpegd', str(tmp_path))
        assert jpegd[0].endswith('fdb90000.jpegd')

    def test_rga_platform_cores_from_drivers(self, tmp_path):
        devices = tmp_path / 'devices'
        drivers = tmp_path / 'drivers'
        c0 = devices / 'fdb60000.rga'
        c0.mkdir(parents=True)
        drv = drivers / 'rga3_core0'
        drv.mkdir(parents=True)
        (drv / 'bind').write_text('')
        (drv / 'fdb60000.rga').symlink_to(c0)
        cores = get_rga_platform_cores(str(drivers), str(devices))
        assert len(cores) == 1
        assert cores[0]['name'] == 'rga3_core0'
        assert cores[0]['path'] == str(c0.resolve())

    def test_runtime_pm_busy(self, tmp_path):
        dev = tmp_path / 'fdb90000.jpegd'
        _write_runtime(dev, 'suspended', 0, 50)
        pm = read_runtime_pm(str(dev))
        assert pm['status'] == 'suspended'
        assert runtime_pm_busy(pm, None) is False
        assert runtime_pm_busy(pm, 40) is True
        _write_runtime(dev, 'active', 1, 50)
        pm = read_runtime_pm(str(dev))
        assert runtime_pm_busy(pm, 50) is True

    def test_has_rga_via_device_node(self, tmp_path):
        node = tmp_path / 'rga'
        node.write_text('')
        with patch('rtop.core.hw_detect.RGA_DEVICE', str(node)):
            assert has_rga() is True

    def test_has_rga_false_without_hardware(self, tmp_path):
        with patch('rtop.core.hw_detect.RGA_DEVICE', str(tmp_path / 'missing')):
            with patch('rtop.core.hw_detect.get_rga_platform_cores', return_value=[]):
                with patch('rtop.core.hw_detect.DEBUGFS_PATH', str(tmp_path / 'debug')):
                    assert has_rga() is False
