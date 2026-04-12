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

import curses
import logging

from .rtopgui import RTOPGUI, Page
from .pall import ALL
from .pcpu import CPU
from .pgpu import GPU
from .pnpu import NPU
from .pengine import ENG
from .pmem import MEM
from .pcontrol import CTRL
from .pinfo import INFO

logger = logging.getLogger(__name__)

# All available pages in order
PAGES = [ALL, CPU, GPU, NPU, ENG, MEM, CTRL, INFO]


def run_rtop(interval=1.0, no_service=False):
    """Main entry point for the rtop curses GUI."""
    import sys
    from ..rtop import StandaloneRtop
    from ..core.hw_detect import is_rockchip

    # Check for TTY
    if not sys.stdout.isatty():
        print("Error: rtop requires an interactive terminal (TTY).")
        print("Run 'rtop' directly from a terminal, not via a pipe or non-interactive shell.")
        sys.exit(1)

    if not is_rockchip():
        print("WARNING: No Rockchip SoC detected. Some features may not work.")

    def curses_main(stdscr, client):
        # Initialize colors
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
        # Create the GUI with all pages (jtop-style architecture)
        gui = RTOPGUI(stdscr, client, PAGES, init_page=1)
        gui.run()

    try:
        # Use standalone mode (reads directly from sysfs/procfs)
        with StandaloneRtop(interval=interval) as rockchip:
            curses.wrapper(curses_main, rockchip)
    except KeyboardInterrupt:
        pass
