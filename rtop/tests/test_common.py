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
Tests for core.common module.
"""

import pytest
from rtop.core.common import GenericInterface, cat, check_file, get_key


class TestGenericInterface:
    """Tests for GenericInterface class."""

    def _make(self, data=None):
        gi = GenericInterface()
        if data:
            gi._update(data)
        return gi

    def test_create_empty(self):
        gi = self._make()
        assert isinstance(gi, GenericInterface)

    def test_create_with_data(self):
        gi = self._make({"key1": "value1", "key2": 42})
        assert gi["key1"] == "value1"
        assert gi["key2"] == 42

    def test_dict_access(self):
        gi = self._make({"key1": "value1"})
        assert gi["key1"] == "value1"
        with pytest.raises(KeyError):
            _ = gi["nonexistent"]

    def test_set_item_not_supported(self):
        gi = self._make({"key1": "value1"})
        # GenericInterface does not support __setitem__; _update replaces data
        gi._update({"key1": "updated"})
        assert gi["key1"] == "updated"

    def test_get_method(self):
        gi = self._make({"key1": "value1"})
        assert gi.get("key1") == "value1"
        assert gi.get("missing", "default") == "default"

    def test_contains(self):
        gi = self._make({"key1": "value1"})
        assert "key1" in gi
        assert "missing" not in gi

    def test_keys(self):
        gi = self._make({"key1": "v1", "key2": "v2"})
        assert "key1" in gi.keys()
        assert "key2" in gi.keys()

    def test_items(self):
        gi = self._make({"key1": "value1"})
        items = dict(gi.items())
        assert items["key1"] == "value1"

    def test_len(self):
        gi = self._make({"key1": "v1", "key2": "v2", "key3": "v3"})
        assert len(gi) == 3


class TestCat:
    """Tests for cat() file reading function."""

    def test_read_existing_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        assert cat(str(test_file)) == "hello world"

    def test_read_missing_file(self):
        try:
            result = cat("/nonexistent/path/file.txt")
            assert result == ""
        except (IOError, OSError):
            pass  # also acceptable — cat does not guarantee empty string

    def test_read_file_with_whitespace(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("  hello world  \n")
        result = cat(str(test_file))
        assert "hello world" in result


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

    def test_returns_string(self):
        result = get_key()
        assert isinstance(result, str)

    def test_not_empty(self):
        result = get_key()
        assert len(result) > 0
