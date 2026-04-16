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
from rtop.core.hw_detect import detect_soc, has_gpu, has_npu, has_mpp, get_npu_devfreq_paths


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
