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
Process table component - jtop-style with igreen header and click-to-sort.
"""

import curses
from .colors import NColors


# Column definitions: (header_text, width, key_in_proc, right_align, format_fn)
_COLUMNS = [
    ('PID',     7,  'pid',     True,  lambda v: str(v)),
    ('USER',    9,  'user',    False, lambda v: str(v)[:9]),
    ('PRI',     4,  'pri',     True,  lambda v: str(v)),
    ('S',       2,  'stat',    False, lambda v: str(v)[:1]),
    ('CPU%',    6,  'cpu',     True,  lambda v: '{:.1f}'.format(float(v) if v else 0)),
    ('MEM',     8,  'mem_str', False, lambda v: str(v)),
    ('Command', 0,  'cmd',     False, lambda v: str(v)),   # 0 = fill remaining
]


class ProcessTable(object):
    """jtop-style process table with igreen header and click-to-sort columns."""

    def __init__(self):
        self._sort_col = 4   # default sort by CPU%
        self._sort_asc = False

    def _col_widths(self, total_w):
        """Calculate column widths given total available width."""
        fixed = sum(c[1] + 1 for c in _COLUMNS if c[1] > 0)  # +1 for space separator
        fill = max(total_w - fixed, 4)
        widths = []
        for c in _COLUMNS:
            widths.append(c[1] if c[1] > 0 else fill)
        return widths

    def draw_header(self, stdscr, y, x, width, mouse=()):
        """Draw the column header row with igreen background."""
        widths = self._col_widths(width)
        # Fill entire line with igreen reverse
        try:
            stdscr.addstr(y, x, ' ' * width, NColors.igreen())
        except curses.error:
            pass

        cx = x
        for idx, col in enumerate(_COLUMNS):
            name = col[0]
            right = col[3]
            w = widths[idx]
            if idx == self._sort_col:
                text = '[{}]'.format(name)
            else:
                text = name
            if right:
                cell = text.rjust(w)
            else:
                cell = text.ljust(w)
            cell = cell[:w]
            try:
                stdscr.addstr(y, cx, cell, NColors.igreen() | curses.A_BOLD)
            except curses.error:
                pass
            # Check for mouse click on this column header
            if mouse and len(mouse) >= 3:
                my, mx = mouse[1], mouse[2]
                if my == y and cx <= mx < cx + w:
                    if self._sort_col == idx:
                        self._sort_asc = not self._sort_asc
                    else:
                        self._sort_col = idx
                        self._sort_asc = False
            cx += w + 1

    def draw_rows(self, stdscr, y, x, width, height, processes):
        """Draw process rows (up to height rows)."""
        widths = self._col_widths(width)
        # Sort processes
        sort_key = _COLUMNS[self._sort_col][2]
        try:
            def _sort_val(p):
                v = p.get(sort_key, 0)
                return v if isinstance(v, (int, float)) else str(v)
            procs = sorted(processes, key=_sort_val, reverse=not self._sort_asc)
        except Exception:
            procs = list(processes)

        for row_idx in range(min(height, len(procs))):
            proc = procs[row_idx]
            cx = x
            py = y + row_idx
            for idx, col in enumerate(_COLUMNS):
                _, _, key, right, fmt = col
                w = widths[idx]
                raw = proc.get(key, '')
                try:
                    text = fmt(raw) if raw != '' else ''
                except Exception:
                    text = str(raw)
                if right:
                    cell = text.rjust(w)
                else:
                    cell = text.ljust(w)
                cell = cell[:w]
                try:
                    stdscr.addstr(py, cx, cell)
                except curses.error:
                    pass
                cx += w + 1

    def draw(self, stdscr, y, x, width, height, processes, mouse=()):
        """Draw header + rows. Returns number of rows drawn (including header)."""
        if height < 2:
            return 0
        self.draw_header(stdscr, y, x, width, mouse)
        n = min(height - 1, len(processes))
        self.draw_rows(stdscr, y + 1, x, width, n, processes)
        return 1 + n
