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
Control page - Temperatures, uptime, board info with jtop-style gauges and box borders.
"""

import curses
from .rtopgui import Page
from .lib.colors import NColors
from .lib.common import check_curses, strfdelta, plot_name_info
from .lib.linear_gauge import basic_gauge


def compact_temperatures(stdscr, pos_y, pos_x, width, height, client):
    """Draw compact temperature info for ALL page bottom panel."""
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
        if temp_c > 70:
            color = NColors.red()
        elif temp_c > 50:
            color = NColors.yellow()
        else:
            color = NColors.green()
        # Draw compact temp gauge
        gauge_w = width - 4
        if gauge_w > 8:
            temp_val = min(temp_c, 100)
            data = {
                'name': name[:8],
                'color': color | curses.A_BOLD,
                'online': True,
                'values': [(temp_val, color)],
                'mright': "{:.0f}C".format(temp_c),
            }
            try:
                basic_gauge(stdscr, pos_y + line, pos_x + 2, gauge_w, data)
            except curses.error:
                pass
        line += 1


class CTRL(Page):

    def __init__(self, stdscr, client):
        super(CTRL, self).__init__("CTRL", stdscr, client)

    @check_curses
    def draw(self, key, mouse):
        height, width, first = self.size_page()
        line = first + 1

        # Temperatures section with gauges
        temps = self.rtop.temperature
        if temps:
            try:
                self.stdscr.addstr(line, 1, "Temperatures", curses.A_BOLD | NColors.cyan())
                line += 1
            except curses.error:
                pass
            for name, value in temps.items():
                if not isinstance(value, (int, float)):
                    continue
                temp_c = value / 1000
                if temp_c > 70:
                    color = NColors.red()
                elif temp_c > 50:
                    color = NColors.yellow()
                else:
                    color = NColors.green()
                # Temperature gauge (out of 100C range)
                temp_val = min(temp_c, 100)
                data = {
                    'name': '{:<12}'.format(name[:12]),
                    'color': curses.A_BOLD,
                    'online': True,
                    'values': [(temp_val, color)],
                    'mright': "{:.1f}C".format(temp_c),
                }
                basic_gauge(self.stdscr, line, 3, width - 6, data)
                line += 1
            line += 1

        # Uptime
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            uptime_str = strfdelta(uptime_seconds)
            plot_name_info(self.stdscr, line, 1, "Uptime", uptime_str, NColors.green())
            line += 2
        except (IOError, OSError):
            pass

        # Board info section
        hardware = self.rtop.hardware
        if hardware and isinstance(hardware, dict):
            try:
                self.stdscr.addstr(line, 1, "Board Information", curses.A_BOLD | NColors.cyan())
                line += 1
            except curses.error:
                pass
            for key_name in ['board', 'model', 'soc', 'cpu']:
                val = hardware.get(key_name, '')
                if val:
                    plot_name_info(self.stdscr, line, 3, key_name.title(), str(val))
                    line += 1
