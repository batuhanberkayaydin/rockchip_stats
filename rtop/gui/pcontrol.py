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
  Temperatures  – gauge per thermal zone with color-coded bands
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


TEMP_WARN = 70
TEMP_HOT = 50


# ── Compact temp panel (shared with the ALL overview page) ────────────────────

def compact_temperatures(stdscr, pos_y, pos_x, width, height, client):
    temps = client.temperature
    if not temps:
        return
    line = 1
    try:
        stdscr.addstr(pos_y + line, pos_x + 2, "Temp", curses.A_BOLD)
        line += 1
    except curses.error:
        pass
    for name, value in temps.items():
        if not isinstance(value, (int, float)):
            continue
        if line >= height - 2:
            break
        temp_c = value / 1000
        if temp_c > TEMP_WARN:
            color = NColors.red()
        elif temp_c > TEMP_HOT:
            color = NColors.yellow()
        else:
            color = NColors.green()
        gauge_w = width - 4
        if gauge_w > 8:
            data = {
                'name': name[:8],
                'color': color | curses.A_BOLD,
                'online': True,
                'values': [(min(temp_c, 100), color)],
                'mright': "{:.0f}C".format(temp_c),
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
        return (
            'pwm',
            float(info.get('speed', 0)),
            info.get('rpm', None),
            None,
            None,
        )
    if 'cur_state' in info and 'max_state' in info:
        dev_type = str(info.get('type', '')).lower()
        if any(dev_type.startswith(t) for t in _NON_FAN_COOLING_TYPES):
            return None  # CPU/GPU governor — not a fan
        cur = int(info.get('cur_state', 0) or 0)
        mx = max(int(info.get('max_state', 0) or 0), 1)
        return ('cooling', cur * 100.0 / mx, None, cur, mx)
    return None


# ── Panel drawers ────────────────────────────────────────────────────────────

def draw_temperatures(stdscr, y, x, width, temps):
    y = _draw_section(stdscr, y, x, "Temperatures")
    for name, value in temps.items():
        if not isinstance(value, (int, float)):
            continue
        temp_c = value / 1000
        if temp_c > TEMP_WARN:
            color = NColors.red()
        elif temp_c > TEMP_HOT:
            color = NColors.yellow()
        else:
            color = NColors.green()
        data = {
            'name': '{:<12}'.format(name[:12]),
            'color': curses.A_BOLD,
            'online': True,
            'values': [(min(temp_c, 100), color)],
            'mright': "{:.1f}C".format(temp_c),
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
    y = _draw_section(stdscr, y, x, "Fans")
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

        temps = self.rtop.temperature
        if temps:
            line = draw_temperatures(self.stdscr, line, 1, width - 2, temps)

        fan = self.rtop.fan
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
