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
Engine page - RGA and MPP hardware accelerators.

Layout matches jtop's engine page style:
  - RGA section: per-core load gauges + frequency
  - MPP Decoders section: per-core RUNNING/OFF indicators + task counts
  - MPP Encoders section: same
  - MPP Others (IEP, etc): same

jtop uses basic_gauge_simple to show RUNNING/OFF for each engine.
We do the same for MPP codec cores.
"""

import curses
from .rtopgui import Page
from .lib.colors import NColors
from .lib.common import check_curses, unit_to_string, plot_name_info
from .lib.linear_gauge import basic_gauge, basic_gauge_simple, freq_gauge


# ── helpers ────────────────────────────────────────────────────────────────────

def _draw_section_header(stdscr, y, x, width, title):
    """Draw a bold cyan section title, returns next y."""
    try:
        stdscr.addstr(y, x, title, curses.A_BOLD | NColors.cyan())
    except curses.error:
        pass
    return y + 1


def _draw_rga_core(stdscr, y, x, width, core_idx, load, online=True):
    """Draw one RGA core gauge."""
    data = {
        'name': 'C{}'.format(core_idx),
        'color': NColors.cyan(),
        'online': online,
        'values': [(load, NColors.cyan())],
    }
    basic_gauge(stdscr, y, x, width, data)


def _draw_mpp_core(stdscr, y, x, size, name, info, show_tasks=False):
    """Draw one MPP codec core as RUNNING/OFF indicator (jtop engine style).

    When ``show_tasks`` is True (ENG page), the center label shows the current
    task count; otherwise (ALL page) it shows a plain "ON"/"OFF" state like
    jtop's HW engines overview.
    """
    task_count = info.get('task_count', None)
    active = info.get('active', False)
    label = info.get('label', name.upper())

    if active:
        if show_tasks and isinstance(task_count, int) and task_count > 0:
            center_label = '{} task{}'.format(task_count, 's' if task_count != 1 else '')
        else:
            center_label = 'ON'
        color = NColors.green()
        try:
            name_part = '{:<8}'.format(label[:8])
            stdscr.addstr(y, x, name_part, NColors.cyan())
            bar_x = x + len(name_part) + 1
            bar_w = size - len(name_part) - 2
            if bar_w > 4:
                stdscr.hline(y, bar_x, curses.ACS_HLINE, bar_w)
                stdscr.addch(y, bar_x + bar_w, curses.ACS_DIAMOND, curses.A_BOLD)
                label_pos = bar_x + max(0, (bar_w - len(center_label) - 2)) // 2
                stdscr.addstr(y, label_pos, ' {} '.format(center_label), color | curses.A_BOLD)
        except curses.error:
            pass
    else:
        try:
            name_part = '{:<8}'.format(label[:8])
            stdscr.addstr(y, x, name_part, NColors.cyan())
            bar_x = x + len(name_part) + 1
            bar_w = size - len(name_part) - 2
            if bar_w > 3:
                stdscr.hline(y, bar_x, curses.ACS_BULLET, bar_w)
                off_str = ' OFF '
                off_pos = bar_x + (bar_w - len(off_str)) // 2
                stdscr.addstr(y, off_pos, off_str, NColors.red())
        except curses.error:
            pass


def compact_engines(stdscr, pos_y, pos_x, width, height, client):
    """Draw full engine detail in the ALL page bottom panel column.

    Shows RGA per-core gauges and every MPP decoder/encoder/other core
    as a compact RUNNING/OFF indicator — exactly like the full ENG page
    but fitted into the available column height.
    """
    # usable rows: skip border row (0) and leave border row at end
    line = 1
    max_line = height - 2   # last usable row inside the box border

    def _fits(n=1):
        return (line + n) <= max_line

    inner_w = width - 4   # 2 chars indent each side inside the column border

    # ── Section header helper ─────────────────────────────────────────────────
    def _header(title):
        nonlocal line
        if not _fits():
            return False
        try:
            stdscr.addstr(pos_y + line, pos_x + 2, title, curses.A_BOLD | NColors.cyan())
        except curses.error:
            pass
        line += 1
        return True

    # ── RGA ───────────────────────────────────────────────────────────────────
    rga = client.rga
    if rga and isinstance(rga, dict) and _fits():
        version = rga.get('version', 'RGA') or 'RGA'
        cores = rga.get('cores', [])
        online = rga.get('online', False)
        load = rga.get('load', 0)

        if not _header(version):
            return

        if online and cores and len(cores) > 1:
            # Per-core gauges
            for ci, cl in enumerate(cores):
                if not _fits():
                    break
                _draw_rga_core(stdscr, pos_y + line, pos_x + 2, inner_w, ci, cl)
                line += 1
        else:
            # Single gauge (offline or single-core)
            if _fits():
                msg = 'NO ACCESS' if load == -1 else 'OFFLINE'
                data = {
                    'name': 'RGA',
                    'color': NColors.cyan(),
                    'online': online,
                    'values': [(load, NColors.cyan())] if online else [],
                    'message': msg,
                    'coffline': NColors.ired(),
                }
                try:
                    basic_gauge(stdscr, pos_y + line, pos_x + 2, inner_w, data)
                except curses.error:
                    pass
                line += 1

    # ── MPP ───────────────────────────────────────────────────────────────────
    mpp = client.mpp
    if mpp and isinstance(mpp, dict):
        decoders = mpp.get('decoders', {})
        encoders = mpp.get('encoders', {})
        others = mpp.get('others', {})

        if decoders and _fits():
            if not _header("Decoders"):
                return
            for core_name, info in decoders.items():
                if not _fits():
                    break
                _draw_mpp_core(stdscr, pos_y + line, pos_x + 2, inner_w, core_name, info)
                line += 1

        if encoders and _fits():
            if not _header("Encoders"):
                return
            for core_name, info in encoders.items():
                if not _fits():
                    break
                _draw_mpp_core(stdscr, pos_y + line, pos_x + 2, inner_w, core_name, info)
                line += 1

        if others and _fits():
            if not _header("Other"):
                return
            for core_name, info in others.items():
                if not _fits():
                    break
                _draw_mpp_core(stdscr, pos_y + line, pos_x + 2, inner_w, core_name, info)
                line += 1


# ── Main ENG page ──────────────────────────────────────────────────────────────

class ENG(Page):

    def __init__(self, stdscr, client):
        super(ENG, self).__init__("ENG", stdscr, client)

    @check_curses
    def draw(self, key, mouse):
        height, width, first = self.size_page()
        line = first + 1
        has_content = False

        # ── RGA ──────────────────────────────────────────────────────────────
        rga = self.rtop.rga
        if rga and isinstance(rga, dict):
            has_content = True
            version = rga.get('version', 'RGA') or 'RGA'
            cores = rga.get('cores', [])
            online = rga.get('online', False)
            load = rga.get('load', 0)
            freq = rga.get('freq', {})

            title = '{} (2D Accelerator)'.format(version)
            line = _draw_section_header(self.stdscr, line, 1, width, title)

            if online:
                # Per-core gauges
                if len(cores) > 1:
                    for ci, cl in enumerate(cores):
                        _draw_rga_core(self.stdscr, line, 3, width - 6, ci, cl, online=True)
                        line += 1
                else:
                    # Single RGA or no per-core data: show overall gauge
                    data = {
                        'name': 'RGA',
                        'color': NColors.cyan(),
                        'online': True,
                        'values': [(load, NColors.cyan())],
                    }
                    basic_gauge(self.stdscr, line, 3, width - 6, data)
                    line += 1

                # Frequency
                cur_hz = freq.get('cur', 0)
                if cur_hz:
                    freq_str = unit_to_string(cur_hz, '', 'Hz') if cur_hz < 1000 else unit_to_string(cur_hz, 'k', 'Hz')
                    plot_name_info(self.stdscr, line, 3, "Freq", freq_str)
                    line += 1
            else:
                # Permission denied or offline
                perm_msg = 'NO ACCESS (needs root)' if load == -1 else 'OFFLINE'
                data = {
                    'name': 'RGA',
                    'color': NColors.cyan(),
                    'online': False,
                    'message': perm_msg,
                    'coffline': NColors.ired(),
                }
                basic_gauge(self.stdscr, line, 3, width - 6, data)
                line += 1
            line += 1

        # ── MPP ───────────────────────────────────────────────────────────────
        mpp = self.rtop.mpp
        if mpp and isinstance(mpp, dict):
            has_content = True
            decoders = mpp.get('decoders', {})
            encoders = mpp.get('encoders', {})
            others = mpp.get('others', {})

            gauge_w = width - 6

            # Decoders
            if decoders:
                line = _draw_section_header(self.stdscr, line, 1, width, "MPP Decoders")
                for core_name, info in decoders.items():
                    _draw_mpp_core(self.stdscr, line, 3, gauge_w, core_name, info, show_tasks=True)
                    line += 1
                line += 1

            # Encoders
            if encoders:
                line = _draw_section_header(self.stdscr, line, 1, width, "MPP Encoders")
                for core_name, info in encoders.items():
                    _draw_mpp_core(self.stdscr, line, 3, gauge_w, core_name, info, show_tasks=True)
                    line += 1
                line += 1

            # Other (IEP, etc.)
            if others:
                line = _draw_section_header(self.stdscr, line, 1, width, "MPP Other")
                for core_name, info in others.items():
                    _draw_mpp_core(self.stdscr, line, 3, gauge_w, core_name, info, show_tasks=True)
                    line += 1
                line += 1

        if not has_content:
            try:
                self.stdscr.addstr(line, 1, "No hardware engines detected", curses.A_BOLD)
            except curses.error:
                pass
