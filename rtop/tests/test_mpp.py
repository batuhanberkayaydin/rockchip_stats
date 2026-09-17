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
Tests for MPP monitoring, including jpegd runtime PM fallback.
"""

from rtop.core.mpp import MPPService


def _write_runtime(dev, status='suspended', usage=0, active_time=0):
    power = dev / 'power'
    power.mkdir(parents=True, exist_ok=True)
    (power / 'runtime_status').write_text('{}\n'.format(status))
    (power / 'runtime_usage').write_text('{}\n'.format(usage))
    (power / 'runtime_active_time').write_text('{}\n'.format(active_time))


def _make_mpp_service(monkeypatch, cores, platform_map):
    mpp_root = next(iter(cores.values())).rsplit('/', 1)[0] if cores else '/proc/mpp_service'

    def _devices(name, devices_root=None):
        path = platform_map.get(name)
        return [path] if path else []

    monkeypatch.setattr('rtop.core.mpp.get_mpp_path', lambda: mpp_root)
    monkeypatch.setattr('rtop.core.mpp.get_mpp_cores', lambda: cores)
    monkeypatch.setattr('rtop.core.mpp.get_mpp_platform_devices', _devices)
    return MPPService()


class TestMPPRuntimeFallback:
    def test_jpegd_idle_without_task_count(self, tmp_path, monkeypatch):
        core_dir = tmp_path / 'proc' / 'mpp_service' / 'jpegd'
        core_dir.mkdir(parents=True)
        jpegd = tmp_path / 'fdb90000.jpegd'
        _write_runtime(jpegd, 'suspended', 0, 100)
        svc = _make_mpp_service(monkeypatch, {'jpegd': str(core_dir)}, {'jpegd': str(jpegd)})
        st = svc.get_status()
        info = st['decoders']['jpegd']
        assert info['active'] is False
        assert info['task_count'] is None
        assert info['source'] is None
        assert st['any_active'] is False

    def test_jpegd_runtime_status_active(self, tmp_path, monkeypatch):
        core_dir = tmp_path / 'proc' / 'mpp_service' / 'jpegd'
        core_dir.mkdir(parents=True)
        jpegd = tmp_path / 'fdb90000.jpegd'
        _write_runtime(jpegd, 'active', 1, 200)
        svc = _make_mpp_service(monkeypatch, {'jpegd': str(core_dir)}, {'jpegd': str(jpegd)})
        st = svc.get_status()
        info = st['decoders']['jpegd']
        assert info['active'] is True
        assert info['source'] == 'runtime'
        assert st['any_active'] is True

    def test_jpegd_active_time_delta(self, tmp_path, monkeypatch):
        core_dir = tmp_path / 'proc' / 'mpp_service' / 'jpegd'
        core_dir.mkdir(parents=True)
        jpegd = tmp_path / 'fdb90000.jpegd'
        _write_runtime(jpegd, 'suspended', 0, 1000)
        svc = _make_mpp_service(monkeypatch, {'jpegd': str(core_dir)}, {'jpegd': str(jpegd)})
        assert svc.get_status()['decoders']['jpegd']['active'] is False
        _write_runtime(jpegd, 'suspended', 0, 1080)
        st = svc.get_status()
        assert st['decoders']['jpegd']['active'] is True
        assert st['decoders']['jpegd']['source'] == 'runtime'

    def test_task_count_delta_still_wins(self, tmp_path, monkeypatch):
        core_dir = tmp_path / 'proc' / 'mpp_service' / 'rkvdec-core0'
        core_dir.mkdir(parents=True)
        (core_dir / 'task_count').write_text('10\n')
        rkvdec = tmp_path / 'fdc38100.rkvdec-core'
        _write_runtime(rkvdec, 'suspended', 0, 1)
        svc = _make_mpp_service(
            monkeypatch,
            {'rkvdec-core0': str(core_dir)},
            {'rkvdec-core0': str(rkvdec)},
        )
        first = svc.get_status()['decoders']['rkvdec-core0']
        assert first['active'] is False
        (core_dir / 'task_count').write_text('14\n')
        second = svc.get_status()['decoders']['rkvdec-core0']
        assert second['active'] is True
        assert second['source'] == 'task_count'
        assert second['task_count'] == 14
