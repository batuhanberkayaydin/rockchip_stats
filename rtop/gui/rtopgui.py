# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Main GUI framework for rtop curses-based terminal interface.
Modeled after jetson_stats jtopgui architecture.
"""

import re
import abc
import curses
import logging
import time
from .lib.colors import NColors
from .lib.common import check_curses, set_xterm_title

logger = logging.getLogger(__name__)

ABC = abc.ABCMeta('ABC', (object,), {})
GUI_REFRESH = 1000 // 20  # 50ms screen refresh
DATA_REFRESH = 1.0  # 1 second data collection interval


class Page(ABC):
    """Abstract base class for GUI pages."""

    def __init__(self, name, stdscr, client):
        self.name = name
        self.stdscr = stdscr
        self.client = client
        self.rtop = client
        self.dialog_window = None

    def setcontroller(self, controller):
        self.controller = controller

    def size_page(self):
        height, width = self.stdscr.getmaxyx()
        first = 0
        if hasattr(self, 'controller') and self.controller and self.controller.message:
            height -= 1
            first = 1
        return height, width, first

    def register_dialog_window(self, dialog_window_object):
        self.dialog_window = dialog_window_object

    @abc.abstractmethod
    @check_curses
    def draw(self, key, mouse):
        pass

    def keyboard(self, key):
        pass


class RTOPGUI:
    """Main curses-based GUI controller for rtop, matching jtop architecture."""

    def __init__(self, stdscr, client, pages, init_page=0, color_filter=False):
        # Initialize colors
        NColors(color_filter)
        # Set curses reference
        self.stdscr = stdscr
        self.client = client
        self.message = False
        # Initialize all page objects (reuse, don't recreate each frame)
        self.pages = []
        for obj in pages:
            page = obj(stdscr, client)
            page.setcontroller(self)
            self.pages.append(page)
        # Set default page
        self.n_page = 0
        self.set(init_page)
        # Initialize keyboard/mouse state
        self.key = -1
        self.old_key = -1
        self.mouse = ()
        self._running = True

    def run(self):
        """Main GUI loop."""
        # Setup curses
        curses.noecho()
        curses.cbreak()
        if hasattr(curses, 'curs_set'):
            try:
                curses.curs_set(0)
            except Exception:
                pass
        self.stdscr.keypad(True)
        _, _ = curses.mousemask(curses.BUTTON1_CLICKED)
        self.stdscr.nodelay(1)
        # Data collection timer
        last_collect = 0
        # Main loop
        while self._running:
            try:
                # Throttle data collection
                now = time.monotonic()
                if self.client and hasattr(self.client, '_collect') and (now - last_collect) >= DATA_REFRESH:
                    try:
                        self.client._collect()
                        last_collect = now
                    except Exception:
                        pass
                # Handle events
                if self.events():
                    break
                # Get current page
                page = self.pages[self.n_page]
                # Check if dialog window is open
                record_mouse = self.mouse
                if page.dialog_window and hasattr(page.dialog_window, 'enable_dialog_window') and page.dialog_window.enable_dialog_window:
                    self.mouse = ()
                # Draw
                self.draw(page)
                self.mouse = record_mouse
                # Draw dialog window if exists
                if page.dialog_window:
                    page.dialog_window.show(self.stdscr, self.key, self.mouse)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("GUI error: %s", e)

    def draw(self, page):
        """Draw a single frame."""
        self.stdscr.erase()
        # Draw header
        self.header()
        # Draw current page content
        page.draw(self.key, self.mouse)
        # Draw menu bar at bottom
        self.menu()
        # Refresh screen
        self.stdscr.refresh()
        self.stdscr.timeout(GUI_REFRESH)

    def increase(self, loop=False):
        if loop and self.n_page >= len(self.pages) - 1:
            idx = 0
        else:
            idx = self.n_page + 1
        self.set(idx + 1)

    def decrease(self, loop=False):
        if loop and self.n_page <= 0:
            idx = len(self.pages) + 1
        else:
            idx = self.n_page + 1
        self.set(idx - 1)

    def set(self, idx):
        if idx <= len(self.pages) and idx > 0:
            self.n_page = idx - 1

    def title_terminal(self):
        status = []
        # CPU status
        if self.client:
            cpu = self.client.cpu
            if cpu:
                total = cpu.get('total', 0)
                status.append("CPU {:.1f}%".format(total))
            gpu = self.client.gpu
            if gpu:
                load = gpu.get('load', 0)
                status.append("GPU {:.1f}%".format(load))
        str_xterm = '|'.join(status)
        set_xterm_title("rtop {name}".format(name=str_xterm))

    @check_curses
    def header(self):
        self.title_terminal()
        # Show board/SoC information
        hardware = self.client.hardware if self.client else {}
        if hardware and isinstance(hardware, dict):
            model = str(hardware.get('model', '') or hardware.get('board', '')).replace('\x00', '')
            soc = str(hardware.get('soc', '')).replace('\x00', '')
            head_string = ""
            if model:
                head_string += "Model: {model}".format(model=model)
            if soc:
                if head_string:
                    head_string += " - "
                head_string += "SoC: {soc}".format(soc=soc)
            if head_string:
                self.stdscr.addstr(0, 0, head_string, curses.A_BOLD)
            else:
                self.stdscr.addstr(0, 0, "Rockchip System Monitor", curses.A_BOLD)
        else:
            self.stdscr.addstr(0, 0, "Rockchip System Monitor", curses.A_BOLD)

    @check_curses
    def menu(self):
        """Draw the bottom menu bar matching jtop style."""
        height, width = self.stdscr.getmaxyx()
        # Set background for full menu line
        self.stdscr.addstr(height - 1, 0, ("{0:<" + str(width - 1) + "}").format(" "), curses.A_REVERSE)
        position = 1
        for idx, page in enumerate(self.pages):
            # Current page is normal (stands out), others are reversed
            color = curses.A_NORMAL if self.n_page == idx else curses.A_REVERSE
            self.stdscr.addstr(height - 1, position, str(idx + 1), color | curses.A_BOLD)
            self.stdscr.addstr(height - 1, position + 1, page.name + " ", color)
            position += len(page.name) + 3
        # Quit button
        self.stdscr.addstr(height - 1, position, "Q", curses.A_REVERSE | curses.A_BOLD)
        self.stdscr.addstr(height - 1, position + 1, "uit ", curses.A_REVERSE)
        # Author info on far right
        name_author = "rockchip_stats "
        self.stdscr.addstr(height - 1, width - len(name_author), name_author, curses.A_REVERSE)

    def event_menu(self, mx, my):
        """Handle mouse clicks on the menu bar."""
        height, _ = self.stdscr.getmaxyx()
        if my == height - 1:
            position = 1
            for idx, page in enumerate(self.pages):
                size = len(page.name) + 3
                if mx >= position and mx < position + size:
                    self.set(idx + 1)
                    return False
                position += size
            # Quit button
            if mx >= position and mx < position + 4:
                return True
        return False

    def events(self):
        event = self.stdscr.getch()
        status_mouse = False
        status_keyboard = self.keyboard(event)
        # Clear mouse
        self.mouse = ()
        # Check mouse event
        if event == curses.KEY_MOUSE:
            try:
                _, mx, my, _, _ = curses.getmouse()
                status_mouse = self.event_menu(mx, my)
                self.mouse = (mx, my)
            except curses.error:
                pass
        return status_keyboard or status_mouse

    def keyboard(self, event):
        self.key = event
        if self.old_key != self.key:
            if self.key == curses.KEY_LEFT:
                self.decrease(loop=True)
            elif self.key == curses.KEY_RIGHT or self.key == ord('\t'):
                self.increase(loop=True)
            elif self.key in [ord(str(n)) for n in range(10)]:
                num = int(chr(self.key))
                self.set(num)
            elif self.key == ord('q') or self.key == ord('Q') or self.ESC_BUTTON(self.key):
                return True
            else:
                page = self.pages[self.n_page]
                page.keyboard(self.key)
            self.old_key = self.key
        return False

    def ESC_BUTTON(self, key):
        if key == 27:
            n = self.stdscr.getch()
            if n == -1:
                return True
        return False
