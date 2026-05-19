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
Control page — temperatures, fans and power, mirroring jtop's 7CTRL layout.

Sections (from top, each only drawn when the underlying data is available):
  Temperatures  – per-zone bar 0..critical °C with trip markers; status after ]
  Throttle      – cpufreq / devfreq cooling (shown under Temp on ALL page too)
  Fans          – PWM %, RPM and cooling-device state from hwmon / thermal
  Power         – per-rail power / voltage / current (INA2xx hwmon) + total
  Board info    – uptime and hardware identification

The layout is defensive: a board without INA telemetry simply hides the power
panel instead of showing empty columns.
"""

import curses

from .rtopgui import Page
from .lib.colors import NColors
from .lib.common import check_curses, strfdelta, plot_name_info, unit_to_string
from .lib.linear_gauge import basic_gauge
from ..core.temperature import TEMPERATURE_OFFLINE, snapshot_zone_trips_millidegrees


_DEFAULT_SCALE_CRIT_C = 115.0


def _throttle_short_label(dev_type):
    d = dev_type.lower()
    if d.startswith('cpufreq-'):
        return d.replace('cpufreq-', '')[:12]
    if d.startswith('devfreq-'):
        rest = d.replace('devfreq-', '')
        if 'gpu' in rest:
            return 'gpu'
        if 'dmc' in rest:
            return 'dmc'
        if '.' in rest:
            return rest.split('.')[-1][:12]
        return rest[:12]
    return dev_type[:12]


def _throttle_gauge_entries(fan):
    """Sorted (label, cur_state, max_state) for cpufreq / devfreq cooling devices."""
    if not fan:
        return []
    out = []
    for _key, info in fan.items():
        if not isinstance(info, dict):
            continue
        dev_type = str(info.get('type', '')).lower()
        if not (dev_type.startswith('cpufreq-') or dev_type.startswith('devfreq-')):
            continue
        mx = int(info.get('max_state', 0) or 0)
        if mx <= 0:
            continue
        cur = int(info.get('cur_state', 0) or 0)
        out.append((_throttle_short_label(dev_type), cur, mx))
    return sorted(out, key=lambda e: e[0])


def throttle_sidebar_row_count(fan):
    """Extra rows under Temp on ALL page (0, or 1 header + one row per device)."""
    n = len(_throttle_gauge_entries(fan))
    return (1 + n) if n else 0


def _thermal_trips_celsius(trip_points_md):
    out = []
    for tp in trip_points_md or []:
        if not isinstance(tp, dict):
            continue
        try:
            t_c = float(tp['temp']) / 1000.0
        except (TypeError, ValueError, KeyError):
            continue
        out.append({
            'type': str(tp.get('type', 'unknown')).lower(),
            'temp': t_c,
        })
    return out


def _scale_max_celsius(trips_c):
    crit = [t['temp'] for t in trips_c if t['type'] == 'critical']
    if crit:
        return max(crit)
    return _DEFAULT_SCALE_CRIT_C


def _thermal_status_label(temp_c, trips_c):
    crit_vals = [t['temp'] for t in trips_c if t['type'] == 'critical']
    if crit_vals and temp_c + 1e-6 >= max(crit_vals):
        return 'Cr'
    passives = sorted([t['temp'] for t in trips_c if t['type'] == 'passive'])
    best = 0
    for i, p in enumerate(passives, start=1):
        if temp_c + 1e-6 >= p:
            best = i
    if best:
        return 'P{}'.format(best)
    return 'OK'


def _fill_color_for_temp(temp_c, trips_c):
    crit_vals = [t['temp'] for t in trips_c if t['type'] == 'critical']
    if crit_vals and temp_c + 1e-6 >= max(crit_vals):
        return NColors.red()
    passives = sorted([t['temp'] for t in trips_c if t['type'] == 'passive'])
    if passives and temp_c + 1e-6 >= passives[-1]:
        return NColors.orange()
    if passives and temp_c + 1e-6 >= passives[0]:
        return NColors.yellow()
    return NColors.green()


def _marker_color_for_trip(trip, passives_sorted):
    ttype = trip['type']
    ttemp = trip['temp']
    if ttype == 'critical':
        return NColors.red()
    if ttype == 'passive' and passives_sorted:
        if abs(ttemp - passives_sorted[-1]) < 1e-3:
            return NColors.orange()
        return NColors.yellow()
    return NColors.yellow()


def draw_temp_gauge(stdscr, y, x, width, name, temp_md, trip_points_md,
                    name_width=12, decimals=0):
    """Bar scaled 0..critical °C; fill | ; empty spaces; trip | markers; ] XXC STATUS."""
    try:
        temp_c = float(temp_md) / 1000.0
    except (TypeError, ValueError):
        temp_c = float(TEMPERATURE_OFFLINE)

    if temp_c <= TEMPERATURE_OFFLINE + 1e-6:
        name_pad = '{:<{w}}'.format(str(name)[:name_width], w=name_width)
        try:
            stdscr.addstr(y, x, name_pad, curses.A_DIM | curses.A_BOLD)
            stdscr.addstr(y, x + len(name_pad), " OFF", NColors.ired())
        except curses.error:
            pass
        return

    trips_raw = trip_points_md or snapshot_zone_trips_millidegrees().get(name) or []
    trips_c = _thermal_trips_celsius(trips_raw)
    scale_max = _scale_max_celsius(trips_c)
    if scale_max <= 0:
        scale_max = _DEFAULT_SCALE_CRIT_C

    status = _thermal_status_label(temp_c, trips_c)
    if decimals:
        temp_str = "{:.1f}C".format(temp_c)
    else:
        temp_str = "{:.0f}C".format(temp_c)
    # One space before temp value; strip trailing whitespace after status
    suffix = (" " + temp_str + " " + status).rstrip()

    # Fixed-width name column so every `[` lines up; one space then bar
    name_pad = '{:<{w}}'.format(str(name)[:name_width], w=name_width)
    # name_pad + ' ' + '[' + inner + ']' + suffix
    inner = width - len(name_pad) - 1 - 1 - 1 - len(suffix)
    inner = max(4, inner)

    fill_c = _fill_color_for_temp(temp_c, trips_c)
    n_fill = int(round(min(max(temp_c / scale_max, 0.0), 1.0) * inner))
    n_fill = max(0, min(n_fill, inner))

    passives_sorted = sorted([t['temp'] for t in trips_c if t['type'] == 'passive'])
    marker_cols = {}
    for trip in sorted(trips_c, key=lambda t: 1 if t['type'] == 'critical' else 0):
        col = int(round(min(max(trip['temp'] / scale_max, 0.0), 1.0) * (inner - 1)))
        col = max(0, min(col, inner - 1))
        marker_cols[col] = _marker_color_for_trip(trip, passives_sorted)

    x_after_pad = x + len(name_pad)
    x_open = x_after_pad + 1
    x_bar = x_open + 1
    try:
        stdscr.addstr(y, x, name_pad, curses.A_BOLD)
        stdscr.addstr(y, x_after_pad, " ", curses.A_BOLD)
        stdscr.addstr(y, x_open, "[", curses.A_BOLD)
        for i in range(inner):
            if i < n_fill:
                stdscr.addch(y, x_bar + i, ord('|'), fill_c | curses.A_BOLD)
            else:
                stdscr.addch(y, x_bar + i, ord(' '), curses.A_NORMAL)
        for col, mcolor in marker_cols.items():
            stdscr.addch(y, x_bar + col, ord('|'), mcolor | curses.A_BOLD)
        stdscr.addstr(y, x_bar + inner, "]" + suffix, curses.A_BOLD)
    except curses.error:
        pass


def _thermal_from_client(client):
    thermal = getattr(client, 'thermal', None) or {}
    if thermal:
        return thermal
    temps = getattr(client, 'temperature', None) or {}
    return {
        n: {'temp': v, 'trip_points': []}
        for n, v in temps.items()
        if isinstance(v, (int, float))
    }


# ── Compact temp panel (shared with the ALL overview page) ────────────────────

def compact_temperatures(stdscr, pos_y, pos_x, width, height, client):
    thermal = _thermal_from_client(client)
    if not thermal:
        return
    line = 1
    gauge_w = max(0, width - 4)
    try:
        stdscr.addstr(pos_y + line, pos_x + 2, "Temp", curses.A_BOLD)
        line += 1
    except curses.error:
        pass
    for name, row in thermal.items():
        if line >= height - 2:
            break
        if not isinstance(row, dict):
            continue
        temp_md = row.get('temp')
        if not isinstance(temp_md, (int, float)):
            continue
        if gauge_w > 12:
            try:
                draw_temp_gauge(
                    stdscr, pos_y + line, pos_x + 2, gauge_w,
                    name, temp_md, row.get('trip_points', []),
                    name_width=8, decimals=0,
                )
            except curses.error:
                pass
        line += 1

    # Throttle — same column as Temp on ALL page (fills space below temps)
    thr = _throttle_gauge_entries(getattr(client, 'fan', None) or {})
    if thr:
        if line < height - 2:
            line += 1
        if line < height - 2:
            try:
                stdscr.addstr(pos_y + line, pos_x + 2, "Throttle", curses.A_BOLD)
                line += 1
            except curses.error:
                pass
            for label, cur, mx in thr:
                if line >= height - 2:
                    break
                if gauge_w <= 8:
                    break
                pct = cur * 100.0 / mx if mx else 0.0
                pct = max(0.0, min(pct, 100.0))
                if cur == 0:
                    bar_color = NColors.green()
                elif pct < 80:
                    bar_color = NColors.yellow()
                else:
                    bar_color = NColors.red()
                right = '{}/{}'.format(cur, mx)
                if cur > 0:
                    right += ' !!'
                data = {
                    'name': str(label)[:8],
                    'color': curses.A_BOLD,
                    'online': True,
                    'values': [(pct, bar_color)],
                    'mright': right,
                }
                try:
                    basic_gauge(stdscr, pos_y + line, pos_x + 2, gauge_w, data)
                except curses.error:
                    pass
                line += 1


# ── Helpers ──────────────────────────────────────────────────────────────────

def _draw_section(stdscr, y, x, title):
    try:
        stdscr.addstr(y, x, title, curses.A_BOLD | NColors.cyan())
    except curses.error:
        pass
    return y + 1


_NON_FAN_COOLING_TYPES = ('thermal-cpufreq', 'thermal-devfreq', 'cpufreq', 'devfreq')
_FAN_COOLING_TYPES = ('fan', 'pwm-fan', 'gpio-fan')


def _classify_fan_entry(name, info):
    """Return (kind, speed_pct, rpm, state, max_state) or None.

    kind is 'pwm' for hwmon PWM fans (speed in percent), or 'cooling' for
    kernel cooling_device entries that represent real fan hardware.
    CPU/GPU frequency-scaling cooling devices are excluded — they're governor
    states, not fans.
    """
    if not isinstance(info, dict):
        return None
    if 'speed' in info or 'pwm' in info:
        rpm = info.get('rpm', None)
        level = info.get('level', None)  # MCU fan level (0-3)
        return (
            'pwm',
            float(info.get('speed', 0)),
            rpm,
            level,
            None,
        )
    if 'cur_state' in info or 'max_state' in info:
        dev_type = str(info.get('type', '')).lower()
        if any(dev_type.startswith(t) for t in _NON_FAN_COOLING_TYPES):
            return None  # CPU/GPU governor — not a fan
        cur = int(info.get('cur_state', 0) or 0)
        mx = max(int(info.get('max_state', 0) or 0), 1)
        return ('cooling', cur * 100.0 / mx, None, cur, mx)
    # cooling_device with only 'type' key (no state yet) — show if it looks like a fan
    dev_type = str(info.get('type', '')).lower()
    if any(dev_type.startswith(t) for t in _FAN_COOLING_TYPES):
        return ('cooling', 0.0, None, 0, 1)
    return None


# ── Panel drawers ────────────────────────────────────────────────────────────

def draw_temperatures(stdscr, y, x, width, thermal, temps_fallback=None):
    rows = thermal if thermal else {}
    if not rows and temps_fallback:
        rows = {
            n: {'temp': v, 'trip_points': []}
            for n, v in temps_fallback.items()
            if isinstance(v, (int, float))
        }
    if not rows:
        return y
    y = _draw_section(stdscr, y, x, "Temperatures")
    for name, row in rows.items():
        if not isinstance(row, dict):
            continue
        temp_md = row.get('temp')
        if not isinstance(temp_md, (int, float)):
            continue
        try:
            draw_temp_gauge(
                stdscr, y, x + 2, width - 4, name, temp_md,
                row.get('trip_points', []), name_width=12, decimals=1,
            )
        except curses.error:
            pass
        y += 1
    return y + 1


def draw_throttle(stdscr, y, x, width, fan):
    """ cpufreq / devfreq cooling states (cur_state / max_state). """
    entries = _throttle_gauge_entries(fan)
    if not entries:
        return y
    y = _draw_section(stdscr, y, x, "Throttle")
    for label, cur, mx in entries:
        pct = cur * 100.0 / mx if mx else 0.0
        pct = max(0.0, min(pct, 100.0))
        if cur == 0:
            bar_color = NColors.green()
        elif pct < 80:
            bar_color = NColors.yellow()
        else:
            bar_color = NColors.red()
        right = '{}/{}'.format(cur, mx)
        if cur > 0:
            right += ' !!'
        data = {
            'name': '{:<12}'.format(str(label)[:12]),
            'color': curses.A_BOLD,
            'online': True,
            'values': [(pct, bar_color)],
            'mright': right,
        }
        try:
            basic_gauge(stdscr, y, x + 2, width - 4, data)
        except curses.error:
            pass
        y += 1
    return y + 1


def draw_fans(stdscr, y, x, width, fan):
    """Render every detected fan/cooling device with a speed gauge + RPM."""
    if not fan:
        return y
    entries = [(n, _classify_fan_entry(n, i)) for n, i in fan.items()]
    entries = [(n, k) for n, k in entries if k is not None]
    if not entries:
        return y  # nothing real to show — skip the section entirely

    y = _draw_section(stdscr, y, x, "Fans")
    for name, klass in entries:
        kind, pct, rpm, state, max_state = klass
        pct = max(0.0, min(pct, 100.0))
        bar_color = NColors.green() if pct < 60 else (NColors.yellow() if pct < 85 else NColors.red())

        right = ''
        if kind == 'pwm':
            right = '{:.0f}%'.format(pct)
            if isinstance(rpm, (int, float)) and rpm > 0:
                right += ' / {}RPM'.format(int(rpm))
            elif isinstance(state, int):
                right += ' / Lv{}'.format(state)
        else:
            right = '{}/{}'.format(state, max_state)

        data = {
            'name': '{:<12}'.format(str(name)[:12]),
            'color': curses.A_BOLD,
            'online': True,
            'values': [(pct, bar_color)],
            'mright': right,
        }
        try:
            basic_gauge(stdscr, y, x + 2, width - 4, data)
        except curses.error:
            pass
        y += 1
    return y + 1


def draw_power(stdscr, y, x, width, power):
    """jtop-style power table: [Name] [Power] [Volt] [Curr], plus totals."""
    if not power or 'rail' not in power:
        return y
    rails = power['rail']
    if not rails:
        return y

    table_w = min(width, 53)

    # Header bar
    try:
        stdscr.addch(y, x, curses.ACS_ULCORNER)
        stdscr.addch(y, x + table_w - 1, curses.ACS_URCORNER)
        stdscr.hline(y, x + 1, curses.ACS_HLINE, table_w - 2)
        stdscr.addstr(y, x + 5, " Power ", curses.A_BOLD | NColors.cyan())
    except curses.error:
        pass
    y += 1
    try:
        stdscr.addstr(y, x, "[Name]", curses.A_BOLD)
        stdscr.addstr(y, x + 18, "[Power]", curses.A_BOLD)
        stdscr.addstr(y, x + 28, "[Volt]", curses.A_BOLD)
        stdscr.addstr(y, x + 38, "[Curr]", curses.A_BOLD)
    except curses.error:
        pass
    y += 1

    for name, value in rails.items():
        try:
            stdscr.addstr(y, x, str(name)[:17])
        except curses.error:
            pass
        if 'power' in value:
            try:
                stdscr.addstr(y, x + 18, unit_to_string(value['power'], 'm', 'W'))
            except curses.error:
                pass
        if 'volt' in value:
            try:
                stdscr.addstr(y, x + 28, unit_to_string(value['volt'], 'm', 'V'))
            except curses.error:
                pass
        if 'curr' in value:
            try:
                stdscr.addstr(y, x + 38, unit_to_string(value['curr'], 'm', 'A'))
            except curses.error:
                pass
        y += 1

    total = power.get('tot', {})
    if total:
        try:
            stdscr.addstr(y, x, total.get('name', 'ALL'), curses.A_BOLD)
            if 'power' in total:
                stdscr.addstr(y, x + 18, unit_to_string(total['power'], 'm', 'W'), curses.A_BOLD)
            if 'volt' in total:
                stdscr.addstr(y, x + 28, unit_to_string(total['volt'], 'm', 'V'), curses.A_BOLD)
            if 'curr' in total:
                stdscr.addstr(y, x + 38, unit_to_string(total['curr'], 'm', 'A'), curses.A_BOLD)
        except curses.error:
            pass
        y += 1
    return y + 1


# ── CTRL page ────────────────────────────────────────────────────────────────

class CTRL(Page):

    def __init__(self, stdscr, client):
        super(CTRL, self).__init__("CTRL", stdscr, client)

    @check_curses
    def draw(self, key, mouse):
        height, width, first = self.size_page()
        line = first + 1

        thermal = getattr(self.rtop, 'thermal', None) or {}
        temps = self.rtop.temperature
        if thermal or temps:
            line = draw_temperatures(
                self.stdscr, line, 1, width - 2, thermal, temps_fallback=temps)

        fan = self.rtop.fan
        if fan:
            line = draw_throttle(self.stdscr, line, 1, width - 2, fan)
        if fan:
            line = draw_fans(self.stdscr, line, 1, width - 2, fan)

        power = self.rtop.power
        if power:
            line = draw_power(self.stdscr, line, 1, width - 2, power)

        # Uptime
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            plot_name_info(self.stdscr, line, 1, "Uptime",
                           strfdelta(uptime_seconds), NColors.green())
            line += 2
        except (IOError, OSError):
            pass

        hardware = self.rtop.hardware
        if hardware and isinstance(hardware, dict):
            line = _draw_section(self.stdscr, line, 1, "Board Information")
            for key_name in ('board', 'Board', 'model', 'Model', 'soc', 'SoC', 'cpu', 'CPU Model'):
                val = hardware.get(key_name, '')
                if val:
                    plot_name_info(self.stdscr, line, 3, key_name, str(val))
                    line += 1
