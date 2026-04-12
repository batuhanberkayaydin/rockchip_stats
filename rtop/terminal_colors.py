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
