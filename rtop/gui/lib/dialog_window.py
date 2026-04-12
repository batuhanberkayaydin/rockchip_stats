# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Dialog window component for curses GUI.
"""

import curses


class DialogWindow:
    """A simple dialog window for user interaction."""

    def __init__(self, stdscr, height=10, width=50):
        self.stdscr = stdscr
        self.height = height
        self.width = width

    def show(self, title, message, options=None):
        """Show a dialog window with title and message."""
        max_y, max_x = self.stdscr.getmaxyx()
        start_y = (max_y - self.height) // 2
        start_x = (max_x - self.width) // 2

        # Draw window border
        win = curses.newwin(self.height, self.width, start_y, start_x)
        win.box()
        win.refresh()

        # Draw title
        try:
            win.addstr(0, 2, f" {title} ", curses.A_BOLD)
        except curses.error:
            pass

        # Draw message lines
        lines = message.split('\n')
        for i, line in enumerate(lines):
            try:
                win.addstr(2 + i, 2, line[:self.width - 4])
            except curses.error:
                pass

        # Draw options
        if options:
            opt_text = "  ".join(f"[{k}]{v}" for k, v in options.items())
            try:
                win.addstr(self.height - 2, 2, opt_text[:self.width - 4], curses.A_BOLD)
            except curses.error:
                pass

        win.refresh()
        return win

    def confirm(self, title, message):
        """Show a yes/no confirmation dialog."""
        options = {"y": "Yes", "n": "No"}
        win = self.show(title, message, options)
        while True:
            key = self.stdscr.getch()
            if key == ord('y') or key == ord('Y'):
                if win:
                    win.erase()
                    win.refresh()
                return True
            elif key == ord('n') or key == ord('N') or key == 27:  # ESC
                if win:
                    win.erase()
                    win.refresh()
                return False
