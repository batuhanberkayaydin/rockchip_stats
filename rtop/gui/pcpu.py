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
CPU page - Detailed per-core CPU information with charts, matching jtop style.
"""

import curses
from .rtopgui import Page
from .lib.chart import Chart
from .lib.colors import NColors
from .lib.common import check_curses, unit_to_string
from .lib.linear_gauge import freq_gauge, basic_gauge


def cpu_gauge(stdscr, idx, cpu, pos_y, pos_x, _, size_w):
    """Draw a single CPU core gauge matching jtop style."""
    online = cpu.get('online', True)
    name = cpu.get('name', str(idx + 1) + (" " if idx < 9 else ""))
    # Build stacked values for user/system breakdown
    load = cpu.get('load', 0) if online else 0
    values = [(load, NColors.green())] if online else []
    # Draw gauge
    data = {
        'name': name,
        'color': NColors.cyan(),
        'online': online,
        'values': values,
    }
    if size_w < 16:
        basic_gauge(stdscr, pos_y, pos_x, size_w - 1, data)
        return
    elif 'freq' in cpu and cpu['freq']:
        # Draw current frequency
        freq = cpu['freq']
        if isinstance(freq, dict):
            curr_string = unit_to_string(freq.get('cur', 0), 'k', 'Hz')
        else:
            curr_string = unit_to_string(freq, 'k', 'Hz')
        stdscr.addstr(pos_y, pos_x + size_w - 6, curr_string, NColors.italic())
    # Draw gauge
    basic_gauge(stdscr, pos_y, pos_x, size_w - 8, data)


def cpu_grid(stdscr, list_cpu, print_cpu, start_y, start_x, size_height=0, size_width=0):
    """Arrange CPU cores in a grid like jtop."""
    num_cpu = len(list_cpu)
    if num_cpu == 0:
        return size_height, size_width, 0, 0
    size_columns = 4 if num_cpu > 6 else 2
    size_rows = int(num_cpu / size_columns) + bool((num_cpu / size_columns) % 1)
    size_columns = int(num_cpu / size_rows) + bool((num_cpu / size_rows) % 1)
    step_height = int(round(size_height / size_rows)) if size_height > 0 else 1
    step_width = int(size_width / size_columns) if size_width > 0 else 1
    # Build Grid
    idx_row = 0
    idx_column = 0
    for idx, cpu in enumerate(list_cpu):
        if idx_row >= size_rows:
            idx_row = 0
            idx_column += 1
        try:
            print_cpu(stdscr, idx, cpu, start_y + idx_row * step_height, start_x + idx_column * step_width, step_height - 1, step_width - 1)
        except curses.error:
            pass
        idx_row += 1
    return step_height, step_width, size_columns, size_rows


def compact_cpus(stdscr, pos_y, pos_x, width, client):
    """Draw compact CPU gauges for the ALL page."""
    cpu = client.cpu
    if not cpu:
        return 0
    cores = cpu.get('cores', [])
    if not cores:
        return 0
    _, _, _, size_rows = cpu_grid(stdscr, cores, cpu_gauge, pos_y, pos_x + 1, size_width=width - 2)
    return size_rows


class CPU(Page):

    def __init__(self, stdscr, client):
        super(CPU, self).__init__("CPU", stdscr, client)
        # Create charts for each CPU core
        cpu = client.cpu
        cores = cpu.get('cores', []) if cpu else []
        self._chart_cpus = []
        for idx in range(len(cores)):
            chart = Chart(str(idx + 1), self.update_chart, client=client,
                          color_text=curses.COLOR_BLUE, color_chart=[curses.COLOR_BLUE])
            self._chart_cpus.append(chart)

    def update_chart(self, client, name):
        cpu = client.cpu
        if not cpu:
            return {'active': False, 'value': [0]}
        cores = cpu.get('cores', [])
        idx = int(name) - 1
        if idx < len(cores):
            core = cores[idx]
            if isinstance(core, dict):
                return {
                    'active': core.get('online', True),
                    'value': [core.get('load', 0)],
                }
        return {'active': False, 'value': [0]}

    def print_cpu(self, stdscr, idx, cpu, pos_y, pos_x, size_h, size_w):
        """Print a single CPU cell with chart."""
        load = cpu.get('load', 0) if isinstance(cpu, dict) else 0
        online = cpu.get('online', True) if isinstance(cpu, dict) else True
        governor = cpu.get('governor', '') if isinstance(cpu, dict) else ''
        if isinstance(governor, str):
            governor = governor.capitalize()
        label_chart_cpu = "{percent: >3.0f}% {governor}".format(percent=load, governor=governor)
        # Update and draw chart
        if idx < len(self._chart_cpus):
            chart = self._chart_cpus[idx]
            chart.update(self.rtop)
            chart.draw(stdscr, [pos_x, pos_x + size_w], [pos_y, pos_y + size_h - 2], label=label_chart_cpu, y_label=False)
        # Print CPU model
        model = cpu.get('model', '') if isinstance(cpu, dict) else ''
        if model:
            model = model[:size_w]
            try:
                stdscr.addstr(pos_y + size_h - 1, pos_x, model, curses.A_NORMAL)
            except curses.error:
                pass
        # Print frequency gauge
        if isinstance(cpu, dict) and 'freq' in cpu and cpu['freq']:
            freq = cpu['freq']
            if isinstance(freq, dict):
                freq['online'] = cpu.get('online', True)
                freq['name'] = "Frq"
                try:
                    freq_gauge(stdscr, pos_y + size_h, pos_x, size_w, freq)
                except curses.error:
                    pass
            else:
                # freq is just a number
                try:
                    curr_string = unit_to_string(freq, 'k', 'Hz')
                    stdscr.addstr(pos_y + size_h, pos_x, "Frq " + curr_string, NColors.italic())
                except curses.error:
                    pass

    @check_curses
    def draw(self, key, mouse):
        height, width, first = self.size_page()
        cpu = self.rtop.cpu
        if not cpu:
            self.stdscr.addstr(first + 1, 1, "CPU information not available", curses.A_BOLD)
            return
        # Print total CPU gauge
        total_load = cpu.get('total', 0)
        total_data = {
            'name': 'ALL',
            'online': True,
            'values': [(total_load, NColors.green())],
        }
        cpu_gauge(self.stdscr, 0, {'name': 'ALL', 'load': total_load, 'online': True}, first + 1, 1, '', width)
        # Print CPU grid with charts
        cores = cpu.get('cores', [])
        if cores:
            step_height, step_width, size_columns, size_rows = cpu_grid(
                self.stdscr, cores, self.print_cpu, first + 2, 1,
                size_height=height - 4, size_width=width - 8)
            # Print Y axis
            if self._chart_cpus:
                chart = self._chart_cpus[0]
                for i in range(size_rows):
                    chart.draw_y_axis(self.stdscr, first + 2 + i * step_height, 1 + step_width * size_columns, step_height - 3)
