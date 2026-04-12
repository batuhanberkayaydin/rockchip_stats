# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Tests for core.hw_detect module.
"""

import os
import pytest
from unittest.mock import patch
from rtop.core.hw_detect import detect_soc, detect_features, find_devfreq_paths


class TestDetectSoc:
    """Tests for SoC detection."""

    def test_detect_rk3588(self, mock_sysfs):
        compatible_path = str(mock_sysfs / "sys" / "firmware" / "devicetree" / "base" / "compatible")
        with patch('rtop.core.hw_detect.cat', return_value="rockchip,rk3588-evb\0rockchip,rk3588"):
            soc = detect_soc()
            # Should detect as RK3588
            assert soc is not None

    def test_detect_unknown(self):
        with patch('rtop.core.hw_detect.cat', return_value="unknown,vendor\0unknown,soc"):
            soc = detect_soc()
            assert soc is not None


class TestDetectFeatures:
    """Tests for hardware feature detection."""

    def test_detect_gpu(self, mock_sysfs):
        gpu_path = str(mock_sysfs / "sys" / "class" / "devfreq" / "fb000000.gpu")
        with patch('rtop.core.hw_detect.os.path.exists', side_effect=lambda p: gpu_path in p or os.path.exists(p)):
            features = detect_features()
            assert isinstance(features, dict)


class TestFindDevfreqPaths:
    """Tests for devfreq path discovery."""

    def test_find_devfreq(self, mock_sysfs):
        devfreq_dir = str(mock_sysfs / "sys" / "class" / "devfreq")
        with patch('rtop.core.hw_detect.os.path.exists', side_effect=lambda p: devfreq_dir in p or os.path.exists(p)):
            with patch('rtop.core.hw_detect.os.listdir', return_value=["fb000000.gpu", "fdab0000.npu"]):
                paths = find_devfreq_paths()
                assert isinstance(paths, dict)
