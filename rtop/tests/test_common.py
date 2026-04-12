# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Tests for core.common module.
"""

import os
import pytest
from rtop.core.common import GenericInterface, cat, check_file, get_key


class TestGenericInterface:
    """Tests for GenericInterface class."""

    def test_create_empty(self):
        gi = GenericInterface(name="test")
        assert gi.name == "test"

    def test_create_with_data(self, generic_interface):
        assert generic_interface.name == "test"
        assert generic_interface["key1"] == "value1"
        assert generic_interface["key2"] == 42

    def test_dict_access(self, generic_interface):
        assert generic_interface["key1"] == "value1"
        with pytest.raises(KeyError):
            _ = generic_interface["nonexistent"]

    def test_attribute_access(self, generic_interface):
        assert generic_interface.key1 == "value1"
        assert generic_interface.key2 == 42

    def test_set_item(self, generic_interface):
        generic_interface["new_key"] = "new_value"
        assert generic_interface["new_key"] == "new_value"

    def test_get_method(self, generic_interface):
        assert generic_interface.get("key1") == "value1"
        assert generic_interface.get("missing", "default") == "default"

    def test_contains(self, generic_interface):
        assert "key1" in generic_interface
        assert "missing" not in generic_interface

    def test_keys(self, generic_interface):
        assert "key1" in generic_interface.keys()
        assert "key2" in generic_interface.keys()

    def test_items(self, generic_interface):
        items = dict(generic_interface.items())
        assert items["key1"] == "value1"

    def test_len(self, generic_interface):
        assert len(generic_interface) == 3


class TestCat:
    """Tests for cat() file reading function."""

    def test_read_existing_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        assert cat(str(test_file)) == "hello world"

    def test_read_missing_file(self):
        assert cat("/nonexistent/path/file.txt") == ""

    def test_read_file_with_whitespace(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("  hello world  \n")
        assert cat(str(test_file)) == "  hello world  \n"


class TestCheckFile:
    """Tests for check_file() function."""

    def test_existing_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        assert check_file(str(test_file)) is True

    def test_missing_file(self):
        assert check_file("/nonexistent/path/file.txt") is False


class TestGetKey:
    """Tests for get_key() function."""

    def test_existing_key(self):
        data = {"key1": "value1", "key2": "value2"}
        assert get_key(data, "key1") == "value1"

    def test_missing_key_default(self):
        data = {"key1": "value1"}
        assert get_key(data, "missing", "default") == "default"

    def test_none_value(self):
        data = {"key1": None}
        assert get_key(data, "key1", "fallback") == "fallback"
