# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Terminal color helpers for rtop CLI output.
"""


class bcolors:
    """ANSI color codes for terminal output."""

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def bold(text):
        """Return text in bold."""
        return f"{bcolors.BOLD}{text}{bcolors.ENDC}"

    @staticmethod
    def green(text):
        """Return text in green."""
        return f"{bcolors.OKGREEN}{text}{bcolors.ENDC}"

    @staticmethod
    def red(text):
        """Return text in red."""
        return f"{bcolors.FAIL}{text}{bcolors.ENDC}"

    @staticmethod
    def yellow(text):
        """Return text in yellow."""
        return f"{bcolors.WARNING}{text}{bcolors.ENDC}"

    @staticmethod
    def blue(text):
        """Return text in blue."""
        return f"{bcolors.OKBLUE}{text}{bcolors.ENDC}"

    @staticmethod
    def header(text):
        """Return text as header."""
        return f"{bcolors.HEADER}{text}{bcolors.ENDC}"
