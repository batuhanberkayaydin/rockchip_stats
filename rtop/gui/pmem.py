# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Memory page - RAM, Swap, CMA with jtop-style gauges, clear cache button,
and swap management (create/delete/resize).
"""

import os
import subprocess
import logging
import curses
from .rtopgui import Page
from .lib.colors import NColors
from .lib.common import check_curses, size_to_string
from .lib.linear_gauge import basic_gauge
from .lib.smallbutton import SmallButton

logger = logging.getLogger(__name__)

# Default swap file path (same as jtop convention)
_SWAP_FILE = '/mnt/swapfile'
_SWAP_MIN_GB = 1
_SWAP_MAX_GB = 16


def compact_memory(stdscr, pos_y, pos_x, width, height, client):
    """Draw compact memory gauges for ALL page."""
    mem = client.memory
    if not mem:
        return 0
    line = 0
    ram = mem.get('ram', {})
    if ram:
        total = ram.get('total', 0)
        used = ram.get('used', 0)
        if total > 0:
            value = int(float(used) / float(total) * 100.0)
            used_str = size_to_string(used)
            total_str = size_to_string(total)
            data = {
                'name': 'RAM',
                'color': NColors.green(),
                'values': [(value, NColors.green())],
                'online': True,
                'mright': "{}/{}".format(used_str, total_str),
            }
            basic_gauge(stdscr, pos_y + line, pos_x + 1, width - 3, data, bar='|')
            line += 1
    swap = mem.get('swap', {})
    if swap and swap.get('total', 0) > 0:
        total = swap.get('total', 0)
        used = swap.get('used', 0)
        value = int(float(used) / float(total) * 100.0) if total > 0 else 0
        used_str = size_to_string(used)
        total_str = size_to_string(total)
        data = {
            'name': 'SWP',
            'color': NColors.yellow(),
            'values': [(value, NColors.yellow())],
            'online': True,
            'mright': "{}/{}".format(used_str, total_str),
        }
        basic_gauge(stdscr, pos_y + line, pos_x + 1, width - 3, data, bar='|')
        line += 1
    return max(line, 1)


def _run_as_root(cmd):
    """Run a shell command with sudo (non-interactive, may fail without NOPASSWD)."""
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
    """Drop page/dentries/inode caches (needs root)."""
    # Try direct write first (if running as root), then sudo
    try:
        with open('/proc/sys/vm/drop_caches', 'w') as f:
            f.write('3\n')
        return True, ''
    except PermissionError:
        return _run_as_root(['sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'])
    except Exception as e:
        return False, str(e)


def _create_swap(size_gb, path=_SWAP_FILE):
    """Create and enable a swap file of given GB."""
    cmds = [
        ['dd', 'if=/dev/zero', 'of={}'.format(path),
         'bs=1M', 'count={}'.format(size_gb * 1024)],
        ['chmod', '600', path],
        ['mkswap', path],
        ['swapon', path],
    ]
    for cmd in cmds:
        ok, err = _run_as_root(cmd)
        if not ok:
            return False, err
    return True, ''


def _disable_swap(path=_SWAP_FILE):
    """Disable and remove a swap file."""
    ok, err = _run_as_root(['swapoff', path])
    if not ok:
        return False, err
    try:
        os.remove(path)
    except OSError:
        pass
    return True, ''


class MEM(Page):

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
        # Detect if swap file exists on boot
        self._btn_boot._state = os.path.exists('/etc/fstab') and self._fstab_has_swap()

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
        """Add or remove swap file entry from /etc/fstab."""
        entry = '{} none swap sw 0 0\n'.format(_SWAP_FILE)
        try:
            with open('/etc/fstab', 'r') as f:
                lines = f.readlines()
            if enable:
                if entry not in lines:
                    lines.append(entry)
            else:
                lines = [l for l in lines if _SWAP_FILE not in l]
            # Write via sudo tee
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

    @check_curses
    def draw(self, key, mouse):
        height, width, first = self.size_page()
        line = first + 1
        mem = self.rtop.memory
        if not mem:
            self.stdscr.addstr(line, 1, "Memory information not available", curses.A_BOLD)
            return

        # RAM gauge
        ram = mem.get('ram', {})
        if ram:
            total = ram.get('total', 0)
            used = ram.get('used', 0)
            if total > 0:
                value = int(float(used) / float(total) * 100.0)
                used_str = size_to_string(used)
                total_str = size_to_string(total)
                data = {
                    'name': 'RAM',
                    'color': NColors.green(),
                    'values': [(value, NColors.green())],
                    'online': True,
                    'mright': "{}/{}".format(used_str, total_str),
                }
                basic_gauge(self.stdscr, line, 1, width - 2, data, bar='|')
                line += 1
            # Detailed breakdown
            free = ram.get('free', 0)
            buffers = ram.get('buffers', 0)
            cached = ram.get('cached', 0)
            half_w = (width - 2) // 2
            col1_x = 3
            col2_x = col1_x + half_w
            row = line
            for label, val, col_x in [("Used", used, col1_x), ("Free", free, col2_x),
                                       ("Buffers", buffers, col1_x), ("Cached", cached, col2_x)]:
                if val:
                    try:
                        self.stdscr.addstr(row, col_x, label + ":", curses.A_BOLD)
                        self.stdscr.addstr(row, col_x + len(label) + 2, size_to_string(val))
                    except curses.error:
                        pass
                if col_x == col2_x:
                    row += 1
            line = row + 1

        # Clear cache button
        if height > line:
            triggered = self._btn_cache.update(
                self.stdscr, line, 1, 'clear cache', key, mouse)
            if triggered:
                ok, err = _drop_caches()
                self._show_status(ok, err)
            # Status message next to button
            if self._status_msg:
                try:
                    self.stdscr.addstr(line, 20, self._status_msg, self._status_color)
                except curses.error:
                    pass
            line += 2

        # Swap gauge
        swap = mem.get('swap', {})
        swap_total = swap.get('total', 0) if swap else 0
        if swap_total > 0:
            used = swap.get('used', 0)
            value = int(float(used) / float(swap_total) * 100.0)
            used_str = size_to_string(used)
            total_str = size_to_string(swap_total)
            data = {
                'name': 'SWP',
                'color': NColors.yellow(),
                'values': [(value, NColors.yellow())],
                'online': True,
                'mright': "{}/{}".format(used_str, total_str),
            }
            basic_gauge(self.stdscr, line, 1, width - 2, data, bar='|')
            line += 1

        # Swap controller
        if height > line + 1:
            try:
                self.stdscr.addstr(line, 1, "Swap:", curses.A_BOLD)
            except curses.error:
                pass
            # Size: [- | dec]  N GB  [+ | inc]
            cx = 8
            dec_t = self._btn_decrease.update(self.stdscr, line, cx, '-', key, mouse)
            if dec_t and self._swap_size_gb > _SWAP_MIN_GB:
                self._swap_size_gb -= 1
            cx += 6  # len('[- | -]') + 1 ~ 7
            size_str = '{} GB'.format(self._swap_size_gb)
            try:
                self.stdscr.addstr(line, cx, size_str, curses.A_BOLD)
            except curses.error:
                pass
            cx += len(size_str) + 1
            inc_t = self._btn_increase.update(self.stdscr, line, cx, '+', key, mouse)
            if inc_t and self._swap_size_gb < _SWAP_MAX_GB:
                self._swap_size_gb += 1
            cx += 6

            # Create new swap button
            create_t = self._btn_create.update(self.stdscr, line, cx, 'Create new', key, mouse)
            if create_t:
                ok, err = _create_swap(self._swap_size_gb)
                self._show_status(ok, err)
            cx += len('[s| Create new]') + 1

            # On-boot toggle
            boot_t = self._btn_boot.update(self.stdscr, line, cx, 'on boot', key, mouse)
            if boot_t:
                ok, err = self._set_boot_swap(self._btn_boot.state)
                if not ok:
                    self._btn_boot._state = not self._btn_boot._state  # revert
                    self._show_status(ok, err)
            line += 1

            # Disable swap button (only if swap is active)
            if swap_total > 0 and height > line:
                disable_t = self._btn_disable.update(
                    self.stdscr, line, 1, 'Disable swap', key, mouse)
                if disable_t:
                    ok, err = _disable_swap()
                    self._show_status(ok, err)
                line += 1

        line += 1

        # CMA
        cma = mem.get('cma', {})
        if cma and cma.get('total', 0) > 0 and height > line:
            total = cma.get('total', 0)
            used = cma.get('used', 0)
            value = int(float(used) / float(total) * 100.0) if total > 0 else 0
            used_str = size_to_string(used)
            total_str = size_to_string(total)
            data = {
                'name': 'CMA',
                'color': NColors.cyan(),
                'values': [(value, NColors.cyan())],
                'online': True,
                'mright': "{}/{}".format(used_str, total_str),
            }
            basic_gauge(self.stdscr, line, 1, width - 2, data, bar='|')
            line += 2
