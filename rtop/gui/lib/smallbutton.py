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
Small button component for curses GUI - jtop-style.
"""

import curses
import time
from .colors import NColors


class SmallButton(object):
    """A small clickable/key-triggered button.

    Usage:
        btn = SmallButton(trigger_key='c', toggle=False)
        # In draw():
        triggered = btn.update(stdscr, y, x, label, key, mouse)
        if triggered:
            do_action()
    """

    def __init__(self, trigger_key='', toggle=False, default=False):
        self._trigger_key = trigger_key
        self._toggle = toggle
        self._state = default
        self._flash_until = 0.0   # momentary highlight end time

    @property
    def state(self):
        return self._state

    def update(self, stdscr, y, x, label, key, mouse=()):
        """Draw the button and detect trigger. Returns True if activated this frame."""
        # Build display text: "[k| label]"
        if self._trigger_key:
            text = '[{}| {}]'.format(self._trigger_key, label)
        else:
            text = '[ {} ]'.format(label)
        width = len(text)

        # Determine if triggered this frame
        triggered = False

        # Keyboard trigger
        if self._trigger_key and key == ord(self._trigger_key):
            triggered = True

        # Mouse trigger: left click on button area
        if mouse and len(mouse) >= 3:
            bstate, my, mx = mouse[0], mouse[1], mouse[2]
            if my == y and mx >= x and mx < x + width:
                if bstate & curses.BUTTON1_CLICKED:
                    triggered = True

        if triggered:
            if self._toggle:
                self._state = not self._state
            else:
                self._state = False
            self._flash_until = time.time() + 0.3

        # Render
        now = time.time()
        flashing = now < self._flash_until
        if flashing or (self._toggle and self._state):
            attr = NColors.igreen() | curses.A_BOLD
        else:
            attr = curses.A_BOLD

        try:
            stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass

        return triggered


class HideButton(object):
    """Button that hides its payload text until the user presses the key
    (or clicks the bracketed prompt). Used for the Serial Number reveal on
    the INFO page — mirrors jtop's HideButton behavior.
    """

    HIDE_PROMPT = "XX CLICK TO READ XXX"

    def __init__(self, trigger_key='s', text=''):
        self._trigger_key = trigger_key
        self._text = text
        self._revealed = False

    def update(self, stdscr, y, x, key, mouse=()):
        width = len('[{}| {}]'.format(self._trigger_key, self.HIDE_PROMPT))

        # Keyboard reveal
        if self._trigger_key and key == ord(self._trigger_key):
            self._revealed = True

        # Mouse reveal
        if mouse and len(mouse) >= 3:
            bstate, my, mx = mouse[0], mouse[1], mouse[2]
            if my == y and mx >= x and mx < x + width:
                if bstate & curses.BUTTON1_CLICKED:
                    self._revealed = True

        try:
            if self._revealed:
                stdscr.addstr(y, x, self._text, curses.A_NORMAL)
            else:
                stdscr.addstr(y, x,
                              '[{}| {}]'.format(self._trigger_key, self.HIDE_PROMPT),
                              curses.A_BOLD)
        except curses.error:
            pass
        return self._revealed


class ButtonList(object):
    """A row of SmallButtons."""

    def __init__(self, buttons):
        """buttons: list of (SmallButton, label)"""
        self._buttons = buttons  # list of (SmallButton, label)

    def update(self, stdscr, y, x, key, mouse=()):
        """Draw all buttons in a row, return list of triggered buttons."""
        cx = x
        triggered = []
        for btn, label in self._buttons:
            t = btn.update(stdscr, y, cx, label, key, mouse)
            if t:
                triggered.append(btn)
            if btn._trigger_key:
                w = len('[{}| {}]'.format(btn._trigger_key, label))
            else:
                w = len('[ {} ]'.format(label))
            cx += w + 1
        return triggered
