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
Memory page — mirrors jetson_stats jtop 6MEM layout.

Top-left:     color-segmented Mem gauge (used/shared/buffers/cached)
Top-right:    RAM legend block (Used / Shared / Buffers / Cached / Free / TOT)
Middle-left:  CMA gauge + on-board storage gauges (eMMC / SD / NVMe)
Middle-right: [c| clear cache] button + swap controller
Bottom:       Swap table (active swap entries)
"""

import os
import subprocess
import logging
import curses

from .rtopgui import Page
from .lib.colors import NColors
from .lib.common import check_curses, size_to_string, plot_name_info
from .lib.linear_gauge import basic_gauge
from .lib.smallbutton import SmallButton

logger = logging.getLogger(__name__)

_SWAP_FILE = '/mnt/swapfile'
_SWAP_MIN_GB = 1
_SWAP_MAX_GB = 16


# ── Helper: convert bytes to kB for jtop's size_to_string('k') expectation ────

def _b_to_kb(v):
    return int(v // 1024) if v else 0


# ── Gauges ────────────────────────────────────────────────────────────────────

def mem_gauge(stdscr, pos_y, pos_x, size, ram):
    """jtop-style RAM gauge with color-segmented used/shared/buffers/cached."""
    total = ram.get('total', 0) or 1
    used = ram.get('used', 0)
    buffers = ram.get('buffers', 0)
    cached = ram.get('cached', 0)
    shared = ram.get('shared', 0)

    # `used` from /proc/meminfo already reflects what the kernel calls used
    # (MemTotal - MemAvailable). To show the segmented bar similarly to jtop we
    # carve "used" into shared / app-used components.
    app_used = max(used - shared, 0)

    values = [
        (app_used / total * 100.0, NColors.cyan()),
        (shared / total * 100.0, NColors.green() | curses.A_BOLD),
        (buffers / total * 100.0, NColors.blue()),
        (cached / total * 100.0, NColors.yellow()),
    ]
    data = {
        'name': 'Mem',
        'color': NColors.cyan(),
        'values': values,
        'mright': "{used}/{tot}".format(
            used=size_to_string(used, 'k'),
            tot=size_to_string(total, 'k'),
        ),
    }
    basic_gauge(stdscr, pos_y, pos_x, size - 1, data)


def swap_gauge(stdscr, pos_y, pos_x, size, swap):
    total = swap.get('total', 0)
    used = swap.get('used', 0)
    values = [
        (used / total * 100.0 if total > 0 else 0.0, NColors.red()),
    ] if total > 0 else []
    data = {
        'name': 'Swp',
        'color': NColors.cyan(),
        'values': values,
        'online': total > 0,
        'mright': "{used}/{tot}".format(
            used=size_to_string(used, 'k'),
            tot=size_to_string(total, 'k'),
        ) if total > 0 else 'no swap',
    }
    basic_gauge(stdscr, pos_y, pos_x, size - 1, data)


def cma_gauge(stdscr, pos_y, pos_x, size, cma):
    """Draw CMA gauge. CMA plays the role of EMC/IRAM on jtop for Rockchip."""
    total = cma.get('total', 0) or 0
    used = cma.get('used', 0)
    if total <= 0:
        return False
    values = [(used / total * 100.0, NColors.cyan())]
    data = {
        'name': 'Cma',
        'color': NColors.cyan(),
        'values': values,
        'mright': "{used}/{tot}".format(
            used=size_to_string(used, 'k'),
            tot=size_to_string(total, 'k'),
        ),
    }
    basic_gauge(stdscr, pos_y, pos_x, size - 1, data, bar=':')
    return True


def storage_gauge(stdscr, pos_y, pos_x, size, entry):
    """Draw a gauge for an on-board storage device (eMMC / SD / NVMe)."""
    total = entry.get('total', 0) or 0
    used = entry.get('used', 0)
    if total <= 0:
        return
    pct = used / total * 100.0
    if pct > 90:
        bar_color = NColors.red()
    elif pct > 70:
        bar_color = NColors.yellow()
    else:
        bar_color = NColors.green()
    data = {
        'name': '{:<4}'.format(entry.get('name', 'Disk')[:4]),
        'color': NColors.cyan(),
        'values': [(pct, bar_color)],
        'mright': "{used}/{tot}".format(
            used=size_to_string(used, ''),
            tot=size_to_string(total, ''),
        ),
    }
    basic_gauge(stdscr, pos_y, pos_x, size - 1, data)


# ── Compact memory (ALL page shares this) ─────────────────────────────────────

def compact_memory(stdscr, pos_y, pos_x, width, height, client):
    """Compact memory gauges used by the ALL overview page."""
    mem = client.memory
    if not mem:
        return 0
    line = 0
    ram = mem.get('ram', {})
    if ram and ram.get('total', 0) > 0:
        try:
            mem_gauge(stdscr, pos_y + line, pos_x + 1, width - 3, ram)
        except curses.error:
            pass
        line += 1
    swap = mem.get('swap', {})
    if swap and swap.get('total', 0) > 0:
        try:
            swap_gauge(stdscr, pos_y + line, pos_x + 1, width - 3, swap)
        except curses.error:
            pass
        line += 1
    return max(line, 1)


# ── Root helpers (cache + swap management) ────────────────────────────────────

def _run_as_root(cmd):
    try:
        result = subprocess.run(
            ['sudo', '-n'] + cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        return result.returncode == 0, result.stderr.decode('utf-8', errors='replace').strip()
    except Exception as e:
        return False, str(e)


def _drop_caches():
    try:
        with open('/proc/sys/vm/drop_caches', 'w') as f:
            f.write('3\n')
        return True, ''
    except PermissionError:
        return _run_as_root(['sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'])
    except Exception as e:
        return False, str(e)


def _create_swap(size_gb, path=_SWAP_FILE):
    for cmd in (
        ['dd', 'if=/dev/zero', 'of={}'.format(path),
         'bs=1M', 'count={}'.format(size_gb * 1024)],
        ['chmod', '600', path],
        ['mkswap', path],
        ['swapon', path],
    ):
        ok, err = _run_as_root(cmd)
        if not ok:
            return False, err
    return True, ''


def _disable_swap(path=_SWAP_FILE):
    ok, err = _run_as_root(['swapoff', path])
    if not ok:
        return False, err
    try:
        os.remove(path)
    except OSError:
        pass
    return True, ''


# ── MEM page ──────────────────────────────────────────────────────────────────

class MEM(Page):

    LEGEND_WIDTH = 18    # right-hand RAM legend column

    def __init__(self, stdscr, client):
        super(MEM, self).__init__("MEM", stdscr, client)
        self._btn_cache = SmallButton(trigger_key='c', toggle=False)
        self._btn_create = SmallButton(trigger_key='s', toggle=False)
        self._btn_boot = SmallButton(trigger_key='b', toggle=True, default=False)
        self._btn_decrease = SmallButton(trigger_key='-', toggle=False)
        self._btn_increase = SmallButton(trigger_key='+', toggle=False)
        self._btn_disable = SmallButton(trigger_key='d', toggle=False)
        self._swap_size_gb = 4
        self._status_msg = ''
        self._status_color = curses.A_NORMAL
        self._btn_boot._state = self._fstab_has_swap()

    # ── persistence helpers ──────────────────────────────────────────────────

    def _fstab_has_swap(self):
        try:
            with open('/etc/fstab', 'r') as f:
                for line in f:
                    if _SWAP_FILE in line and 'swap' in line and not line.strip().startswith('#'):
                        return True
        except Exception:
            pass
        return False

    def _set_boot_swap(self, enable):
        entry = '{} none swap sw 0 0\n'.format(_SWAP_FILE)
        try:
            with open('/etc/fstab', 'r') as f:
                lines = f.readlines()
            if enable:
                if entry not in lines:
                    lines.append(entry)
            else:
                lines = [l for l in lines if _SWAP_FILE not in l]
            content = ''.join(lines)
            result = subprocess.run(
                ['sudo', '-n', 'tee', '/etc/fstab'],
                input=content.encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            return result.returncode == 0, ''
        except Exception as e:
            return False, str(e)

    def _show_status(self, ok, msg=''):
        if ok:
            self._status_msg = 'OK'
            self._status_color = NColors.green()
        else:
            self._status_msg = 'FAILED: {}'.format(msg[:40]) if msg else 'FAILED'
            self._status_color = NColors.red()

    # ── sub-panels ───────────────────────────────────────────────────────────

    def _draw_ram_legend(self, pos_y, pos_x, ram):
        """Right-hand RAM legend panel (mirrors jtop.draw_ram_legend)."""
        try:
            self.stdscr.addstr(pos_y, pos_x + 1, "     RAM     ", curses.A_REVERSE)
        except curses.error:
            pass
        rows = [
            ('Used', ram.get('used', 0), NColors.cyan()),
            ('Shared', ram.get('shared', 0), NColors.green()),
            ('Buffers', ram.get('buffers', 0), NColors.blue()),
            ('Cached', ram.get('cached', 0), NColors.yellow()),
            ('Free', ram.get('free', 0), curses.A_NORMAL),
            ('TOT', ram.get('total', 0), curses.A_BOLD),
        ]
        for i, (label, value, color) in enumerate(rows):
            plot_name_info(self.stdscr, pos_y + 1 + i, pos_x + 2, label,
                           size_to_string(value, 'k'), color=color)

    def _draw_swap_controller(self, pos_y, pos_x, key, mouse, has_swap):
        """Right-hand swap controller block (create/resize/boot/disable)."""
        # Cache-clear button
        if self._btn_cache.update(self.stdscr, pos_y, pos_x, 'clear cache', key, mouse):
            ok, err = _drop_caches()
            self._show_status(ok, err)
        if self._status_msg:
            try:
                self.stdscr.addstr(pos_y, pos_x + 16, self._status_msg, self._status_color)
            except curses.error:
                pass

        # "Create new" button
        if self._btn_create.update(self.stdscr, pos_y + 2, pos_x, 'Create new', key, mouse):
            ok, err = _create_swap(self._swap_size_gb)
            self._show_status(ok, err)

        # "on boot" toggle
        if self._btn_boot.update(self.stdscr, pos_y + 3, pos_x, 'on boot', key, mouse):
            ok, err = self._set_boot_swap(self._btn_boot.state)
            if not ok:
                self._btn_boot._state = not self._btn_boot._state
                self._show_status(ok, err)

        # Size line:  [- |]  N GB  [+ |]
        dec = self._btn_decrease.update(self.stdscr, pos_y + 4, pos_x, '', key, mouse)
        if dec and self._swap_size_gb > _SWAP_MIN_GB:
            self._swap_size_gb -= 1
        try:
            self.stdscr.addstr(pos_y + 4, pos_x + 5, "{:>2}".format(self._swap_size_gb), curses.A_BOLD)
            self.stdscr.addstr(pos_y + 4, pos_x + 8, "GB", curses.A_BOLD)
        except curses.error:
            pass
        inc = self._btn_increase.update(self.stdscr, pos_y + 4, pos_x + 11, '', key, mouse)
        if inc and self._swap_size_gb < _SWAP_MAX_GB:
            self._swap_size_gb += 1

        # "Disable swap" available only when a swap is active
        if has_swap:
            if self._btn_disable.update(self.stdscr, pos_y + 6, pos_x, 'Disable swap', key, mouse):
                ok, err = _disable_swap()
                self._show_status(ok, err)

    # ── main draw ────────────────────────────────────────────────────────────

    @check_curses
    def draw(self, key, mouse):
        height, width, first = self.size_page()
        line = first + 1

        mem = self.rtop.memory
        if not mem:
            self.stdscr.addstr(line, 1, "Memory information not available", curses.A_BOLD)
            return

        ram = mem.get('ram', {})
        swap = mem.get('swap', {})
        cma = mem.get('cma', {})
        shmem = mem.get('shmem', {})
        storage = mem.get('storage', []) or []

        # Synthesize "shared" from shmem for the segmented gauge & legend.
        if ram:
            ram = dict(ram)
            ram.setdefault('shared', shmem.get('total', 0))

        legend_x = width - self.LEGEND_WIDTH
        gauge_w = max(20, legend_x - 2)

        # ── Main RAM gauge (top-left) ──
        if ram and ram.get('total', 0) > 0:
            mem_gauge(self.stdscr, line, 1, gauge_w, ram)
            # Right-hand legend (shares vertical space with gauge + next lines)
            self._draw_ram_legend(line, legend_x, ram)
            line += 1

        # ── CMA gauge ──
        if cma and cma.get('total', 0) > 0 and height > line:
            cma_gauge(self.stdscr, line, 1, gauge_w, cma)
            line += 1

        # ── Storage gauges (eMMC / SD / NVMe) ──
        if storage and height > line + len(storage):
            try:
                self.stdscr.addstr(line, 1, "Storage", curses.A_BOLD | NColors.cyan())
            except curses.error:
                pass
            line += 1
            for entry in storage:
                if height <= line:
                    break
                storage_gauge(self.stdscr, line, 1, gauge_w, entry)
                line += 1

        # Controller column grows downwards to the right of the gauges; we
        # start it right under the legend so it doesn't overlap.
        ctrl_y = first + 1 + 7  # RAM legend is 7 rows (title + 6 fields)
        if height > ctrl_y + 4:
            self._draw_swap_controller(ctrl_y, legend_x, key, mouse,
                                       has_swap=swap.get('total', 0) > 0)

        # ── Swap gauge + table (bottom span) ──
        if height > line + 1:
            line += 1
            try:
                self.stdscr.addstr(line, 1, "SWAP", curses.A_BOLD | NColors.cyan())
            except curses.error:
                pass
            line += 1
            swap_gauge(self.stdscr, line, 1, width - 2, swap)
            line += 1
