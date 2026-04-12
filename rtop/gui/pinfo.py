# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Info page - Board and system information with jtop-style dictionary layout.
"""

import curses
from .rtopgui import Page
from .lib.colors import NColors
from .lib.common import check_curses, plot_dictionary, _safe_str


class INFO(Page):

    def __init__(self, stdscr, client):
        super(INFO, self).__init__("INFO", stdscr, client)

    @check_curses
    def draw(self, key, mouse):
        height, width, first = self.size_page()
        line = first + 1

        # Hardware info section
        hardware = self.rtop.hardware
        if hardware and isinstance(hardware, dict):
            hw_data = {}
            for key, value in hardware.items():
                if value:
                    hw_data[key] = _safe_str(value)
            if hw_data:
                line = plot_dictionary(self.stdscr, line, 1, "Hardware", hw_data, size=width - 4)
                line += 1

        # OS info section
        try:
            import platform
            os_data = {}
            os_data["System"] = _safe_str(platform.system())
            os_data["Release"] = _safe_str(platform.release())
            os_data["Machine"] = _safe_str(platform.machine())
            os_data["Hostname"] = _safe_str(platform.node())
            # Get distribution info
            try:
                with open('/etc/os-release', 'r') as f:
                    for fline in f:
                        fline = fline.strip()
                        if fline.startswith('PRETTY_NAME='):
                            os_data["Distribution"] = fline.split('=', 1)[1].strip('"')
                            break
            except (IOError, OSError):
                pass
            line = plot_dictionary(self.stdscr, line, 1, "Operating System", os_data, size=width - 4)
            line += 1
        except Exception:
            pass

        # Python info section
        try:
            import sys
            py_data = {}
            py_data["Version"] = "{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
            py_data["Executable"] = sys.executable
            line = plot_dictionary(self.stdscr, line, 1, "Python", py_data, size=width - 4)
            line += 1
        except Exception:
            pass

        # Kernel info
        try:
            import platform
            kernel_data = {}
            kernel_data["Version"] = _safe_str(platform.version())
            line = plot_dictionary(self.stdscr, line, 1, "Kernel", kernel_data, size=width - 4)
        except Exception:
            pass
