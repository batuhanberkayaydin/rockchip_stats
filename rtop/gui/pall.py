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
ALL page - Overview dashboard matching jtop's compact layout with
box-bordered sections, stacked gauges, and info columns.
"""

import curses
from .rtopgui import Page
from .lib.colors import NColors
from .lib.common import check_curses, strfdelta, plot_name_info, size_to_string
from .lib.linear_gauge import basic_gauge
from .pcpu import compact_cpus
from .pgpu import compact_gpu
from .pnpu import compact_npu
from .pmem import compact_memory
from .pcontrol import compact_temperatures
from .pengine import compact_engines
from .lib.process_table import ProcessTable


def compact_status(stdscr, pos_y, pos_x, width, height, client):
    """Draw compact status info (uptime, etc) in a column."""
    line_counter = 0
    # Uptime
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        uptime_str = strfdelta(uptime_seconds)
        plot_name_info(stdscr, pos_y + line_counter, pos_x + 1, "Uptime", uptime_str)
        line_counter += 1
    except (IOError, OSError):
        pass
    # Hardware info
    hardware = client.hardware if hasattr(client, 'hardware') else {}
    if hardware and isinstance(hardware, dict):
        soc = hardware.get('soc', '')
        if soc:
            plot_name_info(stdscr, pos_y + line_counter, pos_x + 1, "SoC", str(soc))
            line_counter += 1
    return max(line_counter, 1)


def disk_gauge(stdscr, pos_y, pos_x, size, client):
    """Draw disk usage gauge like jtop."""
    try:
        import shutil
        usage = shutil.disk_usage('/')
        value = int(float(usage.used) / float(usage.total) * 100.0)
        used = size_to_string(usage.used)
        total = size_to_string(usage.total)
        data = {
            'name': 'Dsk',
            'color': NColors.yellow(),
            'values': [(value, NColors.yellow())],
            'mright': "{used}/{total}".format(used=used, total=total)
        }
        basic_gauge(stdscr, pos_y, pos_x, size - 2, data, bar="#")
    except Exception:
        pass
    return 1


def _engine_rows(rga, mpp):
    """Calculate how many rows the compact_engines column needs."""
    rows = 0
    if rga and isinstance(rga, dict):
        rows += 1  # "RGA" header
        cores = rga.get('cores', [])
        rows += max(len(cores), 1)   # per-core gauges (or single gauge)
    if mpp and isinstance(mpp, dict):
        decoders = mpp.get('decoders', {})
        encoders = mpp.get('encoders', {})
        others = mpp.get('others', {})
        if decoders:
            rows += 1 + len(decoders)   # header + one row each
        if encoders:
            rows += 1 + len(encoders)
        if others:
            rows += 1 + len(others)
    return max(rows, 3)


class ALL(Page):

    def __init__(self, stdscr, client):
        super(ALL, self).__init__("ALL", stdscr, client)
        self._proc_table = ProcessTable()
        # Build column list for bottom info panels
        self._columns = []
        self._max_height_menu = 0
        # Engine column (RGA per-core + all MPP decoder/encoder/other)
        rga = client.rga if hasattr(client, 'rga') else {}
        mpp = client.mpp if hasattr(client, 'mpp') else {}
        if rga or mpp:
            self._columns.append(compact_engines)
            eng_rows = _engine_rows(rga, mpp)
            self._max_height_menu = max(self._max_height_menu, eng_rows)
        # Temperature column
        temps = client.temperature if hasattr(client, 'temperature') else {}
        if temps:
            self._columns.append(compact_temperatures)
            self._max_height_menu = max(self._max_height_menu, len(temps) + 1)
        # Border rows top + bottom
        self._max_height_menu += 2

    @check_curses
    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        line_counter = first + 1
        # Plot CPU gauges (compact, one line per core)
        line_counter += compact_cpus(self.stdscr, line_counter, 0, width, self.rtop)
        # Plot memory (left half) and status (right half)
        size_memory = compact_memory(self.stdscr, line_counter, 0, width // 2, height, self.rtop)
        size_status = compact_status(self.stdscr, line_counter, width // 2, width // 2, height, self.rtop)
        line_counter += max(size_memory, size_status)
        # GPU gauge
        if height > line_counter:
            line_counter += compact_gpu(self.stdscr, line_counter, 0, width, self.rtop)
        # NPU gauge
        if height > line_counter:
            line_counter += compact_npu(self.stdscr, line_counter, 0, width, self.rtop)
        # Disk gauge
        if height > line_counter:
            line_counter += disk_gauge(self.stdscr, line_counter, 0, width, self.rtop)
        # Process table (top 4 processes)
        if height > line_counter + 2:
            procs = self.rtop.processes if hasattr(self.rtop, 'processes') else []
            if procs:
                drawn = self._proc_table.draw(
                    self.stdscr, line_counter, 1, width - 2, 5, procs[:4], mouse)
                line_counter += drawn

        # Bottom info panels with box borders (like jtop)
        n_columns = len(self._columns)
        if n_columns == 0:
            return
        pos_y_mini_menu = line_counter
        # If there's enough space, push to bottom
        if height - line_counter > self._max_height_menu + 1:
            pos_y_mini_menu = height - self._max_height_menu - 1
        column_height = height - pos_y_mini_menu
        if column_height <= 1:
            return
        # Draw box border - upper line
        try:
            self.stdscr.addch(pos_y_mini_menu, 0, curses.ACS_ULCORNER)
            self.stdscr.addch(pos_y_mini_menu, width - 1, curses.ACS_URCORNER)
            self.stdscr.hline(pos_y_mini_menu, 1, curses.ACS_HLINE, width - 2)
        except curses.error:
            pass
        # Vertical lines
        if column_height > 3:
            self.stdscr.vline(pos_y_mini_menu + 1, 0, curses.ACS_VLINE, column_height - 3)
            self.stdscr.vline(pos_y_mini_menu + 1, width - 1, curses.ACS_VLINE, column_height - 3)
        # Lower line
        try:
            self.stdscr.addch(pos_y_mini_menu + self._max_height_menu - 1, 0, curses.ACS_LLCORNER)
            self.stdscr.addch(pos_y_mini_menu + self._max_height_menu - 1, width - 1, curses.ACS_LRCORNER)
            self.stdscr.hline(pos_y_mini_menu + self._max_height_menu - 1, 1, curses.ACS_HLINE, width - 2)
        except curses.error:
            pass
        # Adjust column count based on width
        n_print = n_columns
        if width < 49 and n_columns > 1:
            n_print -= 1
        # Draw columns
        column_width = width // n_print
        for nline in range(n_print):
            func = self._columns[nline]
            func(self.stdscr, pos_y_mini_menu, column_width * nline, column_width, column_height, self.rtop)
            if nline < n_print - 1:
                self.stdscr.addch(pos_y_mini_menu, column_width * (nline + 1), curses.ACS_TTEE)
                if column_height > 3:
                    self.stdscr.vline(pos_y_mini_menu + 1, column_width * (nline + 1), curses.ACS_VLINE, column_height - 3)
                try:
                    self.stdscr.addch(pos_y_mini_menu + column_height - 2, column_width * (nline + 1), curses.ACS_BTEE)
                except curses.error:
                    pass
