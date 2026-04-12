# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

# flake8: noqa

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
