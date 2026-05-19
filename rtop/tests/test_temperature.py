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
Tests for core.temperature module.
"""

import pytest

from rtop.core import temperature as temp_mod
from rtop.core.temperature import (
    TEMPERATURE_OFFLINE,
    TemperatureService,
    _discover_trip_point_paths,
    _read_trip_points,
    get_thermal_zones,
    read_temperature,
    snapshot_zone_trips_millidegrees,
)


@pytest.fixture
def thermal_sysfs(tmp_path):
    """Minimal mock thermal sysfs tree with one zone and two trip points."""
    thermal_dir = tmp_path / "sys" / "class" / "thermal"
    zone_dir = thermal_dir / "thermal_zone0"
    zone_dir.mkdir(parents=True)
    (zone_dir / "type").write_text("soc-thermal")
    (zone_dir / "temp").write_text("52000")
    (zone_dir / "trip_point_0_temp").write_text("70000")
    (zone_dir / "trip_point_0_type").write_text("passive")
    (zone_dir / "trip_point_0_hyst").write_text("2000")
    (zone_dir / "trip_point_1_temp").write_text("95000")
    (zone_dir / "trip_point_1_type").write_text("critical")
    return tmp_path, str(thermal_dir), str(zone_dir)


class TestReadTemperature:
    def test_reads_millidegrees_as_celsius(self, thermal_sysfs):
        _, _, zone_dir = thermal_sysfs
        values = read_temperature({"soc": zone_dir + "/temp"})
        assert values["soc"] == pytest.approx(52.0)

    def test_missing_file_returns_offline(self, tmp_path):
        missing = str(tmp_path / "missing" / "temp")
        values = read_temperature({"soc": missing})
        assert values["soc"] == TEMPERATURE_OFFLINE


class TestTripPointDiscovery:
    def test_discovers_sorted_trip_paths(self, thermal_sysfs):
        _, _, zone_dir = thermal_sysfs
        trips = _discover_trip_point_paths(zone_dir)
        assert len(trips) == 2
        assert trips[0]["index"] == 0
        assert trips[1]["index"] == 1
        assert trips[0]["temp"].endswith("trip_point_0_temp")

    def test_empty_for_missing_zone(self, tmp_path):
        assert _discover_trip_point_paths(str(tmp_path / "nope")) == []


class TestReadTripPoints:
    def test_reads_type_temp_hyst_in_celsius(self, thermal_sysfs):
        _, _, zone_dir = thermal_sysfs
        meta = _discover_trip_point_paths(zone_dir)
        trips = _read_trip_points(meta)
        assert trips == [
            {"type": "passive", "temp": 70.0, "hyst": 2.0},
            {"type": "critical", "temp": 95.0, "hyst": 0.0},
        ]


class TestGetThermalZones:
    def test_discovers_zones_with_trips(self, thermal_sysfs):
        _, thermal_dir, _ = thermal_sysfs
        zones = get_thermal_zones(thermal_dir)
        assert "soc" in zones
        assert zones["soc"]["temp"].endswith("temp")
        assert len(zones["soc"]["trips"]) == 2

    def test_missing_path_returns_empty(self, tmp_path):
        assert get_thermal_zones(str(tmp_path / "missing")) == {}


class TestTemperatureService:
    def test_get_status_includes_trip_points(self, thermal_sysfs):
        _, thermal_dir, _ = thermal_sysfs
        svc = TemperatureService.__new__(TemperatureService)
        svc._zones = get_thermal_zones(thermal_dir)
        status = svc.get_status()
        assert "soc" in status
        row = status["soc"]
        assert row["soc"] == pytest.approx(52.0)
        assert row["temp"] == pytest.approx(52.0)
        assert row["online"] is True
        assert row["trip_points"] == [
            {"type": "passive", "temp": 70.0, "hyst": 2.0},
            {"type": "critical", "temp": 95.0, "hyst": 0.0},
        ]


class TestSnapshotZoneTrips:
    def test_returns_millidegree_trip_points(self, thermal_sysfs, monkeypatch):
        _, thermal_dir, _ = thermal_sysfs
        temp_mod._TRIPS_SYSFS_CACHE = (None, 0.0)
        monkeypatch.setattr(temp_mod, "get_thermal_zones", lambda path="/sys/class/thermal": get_thermal_zones(thermal_dir))
        data = snapshot_zone_trips_millidegrees(ttl_sec=0.0)
        assert data["soc"][0]["type"] == "passive"
        assert data["soc"][0]["temp"] == pytest.approx(70000.0)
        assert data["soc"][1]["type"] == "critical"
        assert data["soc"][1]["temp"] == pytest.approx(95000.0)
