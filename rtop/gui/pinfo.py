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
INFO page — mirrors jtop's 8INFO layout.

Left column:
    Platform  — system/release/machine/distribution/python
    Libraries — RKNN / RGA / MPP / RKLLM / VPU / GStreamer / OpenCV
Right column:
    Hardware  — board identity, SoC, kernel, etc.
    Serial Number — hidden behind a HideButton (press 's')
    Hostname + Interfaces table
"""

import sys
import platform
import curses

from .rtopgui import Page
from .lib.colors import NColors
from .lib.common import check_curses, plot_name_info, plot_dictionary, _safe_str
from .lib.smallbutton import HideButton

try:
    from ..core.rockchip_libraries import get_libraries, get_local_interfaces
except Exception:  # pragma: no cover — defensive fallback
    def get_libraries():
        return {}

    def get_local_interfaces():
        import socket
        return {'hostname': socket.gethostname(), 'interfaces': {}}


SERIAL_KEYS = ('Serial', 'serial', 'SerialNumber', 'Serial Number')


def _extract_serial(hardware):
    for k in SERIAL_KEYS:
        val = hardware.get(k)
        if val:
            return str(val)
    return ''


def _build_platform_dict():
    """Mirror jtop's Platform block (OS / release / machine / python / distro)."""
    data = {
        'System': _safe_str(platform.system()),
        'Release': _safe_str(platform.release()),
        'Machine': _safe_str(platform.machine()),
        'Python': '{}.{}.{}'.format(*sys.version_info[:3]),
    }
    try:
        with open('/etc/os-release', 'r') as f:
            for ln in f:
                ln = ln.strip()
                if ln.startswith('PRETTY_NAME='):
                    data['Distribution'] = ln.split('=', 1)[1].strip('"')
                    break
    except (IOError, OSError):
        pass
    return data


class INFO(Page):

    def __init__(self, stdscr, client):
        super(INFO, self).__init__("INFO", stdscr, client)
        self._hide_serial = None
        self._libraries_cache = None
        self._net_cache = None

    # ── cached static data ──

    def _libraries(self):
        if self._libraries_cache is None:
            self._libraries_cache = get_libraries() or {}
        return self._libraries_cache

    def _network(self):
        if self._net_cache is None:
            self._net_cache = get_local_interfaces() or {}
        return self._net_cache

    # ── draw ──

    @check_curses
    def draw(self, key, mouse):
        height, width, first = self.size_page()
        start_y = first + 1

        # Author / version line (parallels jtop banner)
        try:
            self.stdscr.addstr(first, 0,
                               "rtop — System monitor for Rockchip SoC devices",
                               curses.A_BOLD)
        except curses.error:
            pass

        # ── Left column: Platform + Libraries ──
        left_x = 1
        plat = _build_platform_dict()
        y_after_plat = plot_dictionary(self.stdscr, start_y + 1, left_x, "Platform", plat)

        libs = self._libraries()
        # Colour-code empty/missing libraries inside plot_dictionary (already
        # does this via its default "MISSING" rendering).
        y_after_libs = plot_dictionary(self.stdscr, y_after_plat + 1, left_x,
                                       "Libraries", libs)

        # ── Right column: Hardware + Serial + Hostname + Interfaces ──
        hardware = self.rtop.hardware or {}
        right_x = max(40, width // 2)

        serial = _extract_serial(hardware)

        # Hardware dict without the serial — it's drawn separately via HideButton
        hw_display = {k: v for k, v in hardware.items() if k not in SERIAL_KEYS}
        y = plot_dictionary(self.stdscr, start_y + 1, right_x, "Hardware", hw_display)

        # Serial line
        if serial:
            try:
                self.stdscr.addstr(y, right_x + 1, "Serial Number:", curses.A_BOLD)
            except curses.error:
                pass
            if self._hide_serial is None:
                self._hide_serial = HideButton(trigger_key='s', text=serial)
            self._hide_serial.update(self.stdscr, y, right_x + 16, key, mouse)
            y += 1

        # Hostname + Interfaces
        net = self._network()
        hostname = net.get('hostname', '')
        ifaces = net.get('interfaces', {})
        if hostname:
            y += 1
            plot_name_info(self.stdscr, y, right_x + 1, "Hostname", hostname,
                           color=NColors.cyan())
            y += 1
        if ifaces:
            plot_dictionary(self.stdscr, y, right_x, "Interfaces", ifaces)
