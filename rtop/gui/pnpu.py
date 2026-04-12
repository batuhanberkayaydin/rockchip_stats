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
NPU page - RKNPU detailed information.

Shows per-core loads (RK3588 has 3 cores) + frequency gauge + live chart.
The number of cores is determined at runtime from the data; no hard-coded count.
"""

import curses
from .rtopgui import Page
from .lib.chart import Chart
from .lib.colors import NColors
from .lib.common import check_curses, unit_to_string, plot_name_info
from .lib.linear_gauge import basic_gauge, freq_gauge


def compact_npu(stdscr, pos_y, pos_x, width, client):
    """Draw compact NPU gauge for ALL page."""
    npu = client.npu
    if not npu:
        return 0
    online = npu.get('online', False)
    load = npu.get('load', 0)
    freq = npu.get('freq', {})
    cur_hz = freq.get('cur', 0) if isinstance(freq, dict) else 0

    data = {
        'name': 'NPU',
        'color': NColors.blue(),
        'online': online,
        'values': [(load, NColors.blue())] if online else [],
        'coffline': NColors.iblue(),
        'message': 'NO ACCESS' if load == -1 else 'OFFLINE',
    }
    if cur_hz:
        curr_string = unit_to_string(cur_hz, 'k', 'Hz')
        try:
            stdscr.addstr(pos_y, pos_x + width - 8, curr_string, NColors.italic())
        except curses.error:
            pass
    basic_gauge(stdscr, pos_y, pos_x + 1, width - 10, data)
    return 1


class NPU(Page):

    def __init__(self, stdscr, client):
        super(NPU, self).__init__("NPU", stdscr, client)
        # Build one chart per NPU core; we discover core count dynamically
        # on first draw and recreate if needed
        self._charts = []
        self._chart_core_count = 0

    def _ensure_charts(self, n_cores):
        """Create/recreate charts if core count changed."""
        if n_cores == self._chart_core_count:
            return
        self._charts = []
        for i in range(n_cores):
            chart = Chart(
                'C{}'.format(i),
                self._make_callback(i),
                client=self.rtop,
                color_text=curses.COLOR_BLUE,
                color_chart=[curses.COLOR_BLUE],
            )
            self._charts.append(chart)
        self._chart_core_count = n_cores

    def _make_callback(self, core_idx):
        def _cb(client, name):
            npu = client.npu
            if not npu:
                return {'active': False, 'value': [0]}
            cores = npu.get('cores', [])
            if core_idx < len(cores):
                c = cores[core_idx]
                load = c.get('load', 0) if isinstance(c, dict) else 0
                return {'active': True, 'value': [load]}
            return {'active': False, 'value': [0]}
        return _cb

    @check_curses
    def draw(self, key, mouse):
        height, width, first = self.size_page()
        line = first + 1
        npu = self.rtop.npu

        if not npu:
            self.stdscr.addstr(line, 1, "No RKNPU detected", curses.A_BOLD)
            return

        online = npu.get('online', False)
        load = npu.get('load', 0)
        cores = npu.get('cores', [])  # list of {'load': %, 'online': bool}
        freq = npu.get('freq', {})
        tops = npu.get('tops', 0)
        governor = npu.get('governor', '')

        # ── Overall load gauge ────────────────────────────────────────────────
        data = {
            'name': 'NPU',
            'color': NColors.blue(),
            'online': online,
            'values': [(load, NColors.blue())] if online else [],
            'coffline': NColors.iblue(),
            'message': 'NO ACCESS (needs root)' if load == -1 else 'OFFLINE',
        }
        basic_gauge(self.stdscr, line, 1, width - 2, data)
        line += 1

        # ── Per-core gauges ───────────────────────────────────────────────────
        n_cores = len(cores)
        if n_cores > 1 and online:
            for ci, core in enumerate(cores):
                core_load = core.get('load', 0) if isinstance(core, dict) else core
                core_online = core.get('online', True) if isinstance(core, dict) else True
                core_data = {
                    'name': ' C{}'.format(ci),
                    'color': NColors.cyan(),
                    'online': core_online,
                    'values': [(core_load, NColors.blue())] if core_online else [],
                    'coffline': NColors.iblue(),
                    'message': 'OFFLINE',
                }
                basic_gauge(self.stdscr, line, 1, width - 2, core_data)
                line += 1

        # ── Frequency gauge ───────────────────────────────────────────────────
        if isinstance(freq, dict) and freq.get('cur'):
            cur_hz = freq.get('cur', 0)
            min_hz = freq.get('min', 0)
            max_hz = freq.get('max', 0)
            if min_hz and max_hz:
                freq_data = {
                    'name': 'Frq',
                    'cur': cur_hz,
                    'min': min_hz,
                    'max': max_hz,
                    'online': online,
                }
                try:
                    freq_gauge(self.stdscr, line, 1, width - 2, freq_data)
                except curses.error:
                    pass
            else:
                plot_name_info(self.stdscr, line, 1, "Freq", unit_to_string(cur_hz, 'k', 'Hz'))
            line += 1

        # ── Info: governor and TOPS ───────────────────────────────────────────
        if governor:
            plot_name_info(self.stdscr, line, 1, "Governor", governor)
            line += 1
        if tops:
            plot_name_info(self.stdscr, line, 1, "Performance", "{:.1f} TOPS".format(tops))
            line += 1

        # ── Charts ────────────────────────────────────────────────────────────
        chart_cores = max(n_cores, 1)
        self._ensure_charts(chart_cores)

        chart_start = line + 1
        # Split available height among all charts
        available_h = height - chart_start - 2
        if available_h >= 4 and self._charts:
            per_chart_h = available_h // len(self._charts)
            for i, chart in enumerate(self._charts):
                chart.update(self.rtop)
                cy = chart_start + i * per_chart_h
                if cy + per_chart_h <= height - 1:
                    chart.draw(self.stdscr, [1, width - 2],
                               [cy, cy + per_chart_h - 1],
                               y_label=(i == 0))

        # ── NPU temperature ───────────────────────────────────────────────────
        temps = self.rtop.temperature
        for tname, val in temps.items():
            if 'npu' in tname.lower() and isinstance(val, (int, float)):
                temp_c = val / 1000
                color = NColors.red() if temp_c > 70 else NColors.yellow() if temp_c > 50 else NColors.green()
                plot_name_info(self.stdscr, height - 2, 1, "Temp", "{:.1f}C".format(temp_c), color)
                break
