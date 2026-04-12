# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

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
