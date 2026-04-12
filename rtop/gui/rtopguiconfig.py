# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
GUI configuration page for rtop settings.
"""

import curses
from .lib.colors import NColors
from .rtopgui import Page


class PageConfig(Page):
    """Configuration page for rtop GUI settings."""

    def __init__(self, rtop_gui):
        super().__init__(rtop_gui)

    def draw(self):
        """Draw the configuration page."""
        stdscr = self.stdscr
        max_y, max_x = stdscr.getmaxyx()
        y = self.start_y

        try:
            stdscr.addstr(y, 1, "rtop Configuration", curses.A_BOLD)
            y += 2

            # Color settings
            stdscr.addstr(y, 1, "Display", curses.A_BOLD)
            y += 1
            stdscr.addstr(y, 3, f"  Terminal size: {max_x}x{max_y}")
            y += 1
            stdscr.addstr(y, 3, "  [c] Toggle color scheme")
            y += 2

            # Refresh rate
            stdscr.addstr(y, 1, "Refresh Rate", curses.A_BOLD)
            y += 1
            interval = self.rtop_gui.interval if hasattr(self.rtop_gui, 'interval') else 1.0
            stdscr.addstr(y, 3, f"  Current interval: {interval:.1f}s")
            y += 1
            stdscr.addstr(y, 3, "  [+/-] Adjust refresh interval")
            y += 2

            # Pages info
            stdscr.addstr(y, 1, "Pages", curses.A_BOLD)
            y += 1
            pages = [
                ("1", "ALL", "Overview dashboard"),
                ("2", "CPU", "Per-core CPU details"),
                ("3", "GPU", "Mali GPU details"),
                ("4", "NPU", "NPU per-core details"),
                ("5", "ENG", "RGA, MPP, VPU engines"),
                ("6", "MEM", "RAM, Swap, CMA memory"),
                ("7", "CTRL", "Fan and governor control"),
                ("8", "INFO", "Board and system info"),
            ]
            for key, name, desc in pages:
                if y >= max_y - 2:
                    break
                try:
                    stdscr.addstr(y, 3, f"[{key}]", curses.A_BOLD)
                    stdscr.addstr(y, 7, f" {name:5s} - {desc}")
                except curses.error:
                    pass
                y += 1

            y += 1
            try:
                stdscr.addstr(y, 1, "Keys: [q] Quit  [h] Help  [arrows] Scroll", curses.A_DIM)
            except curses.error:
                pass

        except curses.error:
            pass
