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
Tests for RGA monitoring, including platform runtime PM fallback.
"""

from unittest.mock import patch

from rtop.core.rga import RGAService, _version_from_names


def _write_runtime(dev, status='suspended', usage=0, active_time=0):
    power = dev / 'power'
    power.mkdir(parents=True, exist_ok=True)
    (power / 'runtime_status').write_text('{}\n'.format(status))
    (power / 'runtime_usage').write_text('{}\n'.format(usage))
    (power / 'runtime_active_time').write_text('{}\n'.format(active_time))


def _make_rga_service(cores, debug_path=None):
    with patch('rtop.core.rga.get_rga_debug_path', return_value=debug_path):
        with patch('rtop.core.rga.get_rga_devfreq_path', return_value=None):
            with patch('rtop.core.rga.get_rga_platform_cores', return_value=cores):
                return RGAService()


class TestVersionFromNames:
    def test_rga3_and_rga2(self):
        assert _version_from_names(['rga3_core0', 'rga3_core1', 'rga2']) == 'RGA3+RGA2'

    def test_empty(self):
        assert _version_from_names([]) == 'RGA'


class TestRGARuntimeFallback:
    def test_online_idle_without_debugfs(self, tmp_path):
        c0 = tmp_path / 'fdb60000.rga'
        c1 = tmp_path / 'fdb70000.rga'
        _write_runtime(c0, 'suspended', 0, 10)
        _write_runtime(c1, 'suspended', 0, 20)
        cores = [
            {'name': 'rga3_core0', 'path': str(c0)},
            {'name': 'rga3_core1', 'path': str(c1)},
        ]
        svc = _make_rga_service(cores)
        assert svc.available is True
        st = svc.get_status()
        assert st['online'] is True
        assert st['active'] is False
        assert st['source'] == 'runtime'
        assert st['cores'] == [0, 0]
        assert st['version'] == 'RGA3'

    def test_active_status(self, tmp_path):
        c0 = tmp_path / 'fdb60000.rga'
        _write_runtime(c0, 'active', 1, 100)
        svc = _make_rga_service([{'name': 'rga3_core0', 'path': str(c0)}])
        st = svc.get_status()
        assert st['active'] is True
        assert st['load'] == 100
        assert st['cores'] == [100]

    def test_active_time_delta(self, tmp_path):
        c0 = tmp_path / 'fdb60000.rga'
        _write_runtime(c0, 'suspended', 0, 1000)
        svc = _make_rga_service([{'name': 'rga3_core0', 'path': str(c0)}])
        first = svc.get_status()
        assert first['active'] is False
        _write_runtime(c0, 'suspended', 0, 1500)
        second = svc.get_status()
        assert second['active'] is True
        assert second['cores'] == [100]

    def test_debugfs_preferred(self, tmp_path):
        load = tmp_path / 'load'
        load.write_text(
            "scheduler[0]: rga3_core0\n"
            "    load = 7%\n"
            "scheduler[1]: rga2\n"
            "    load = 0%\n"
        )
        c0 = tmp_path / 'fdb60000.rga'
        _write_runtime(c0, 'active', 1, 1)
        svc = _make_rga_service(
            [{'name': 'rga3_core0', 'path': str(c0)}],
            debug_path=str(load),
        )
        st = svc.get_status()
        assert st['source'] == 'debugfs'
        assert st['cores'] == [7, 0]
        assert st['load'] == 7
        assert st['version'] == 'RGA3+RGA2'
