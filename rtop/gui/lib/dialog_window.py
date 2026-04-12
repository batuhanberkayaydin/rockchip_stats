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
