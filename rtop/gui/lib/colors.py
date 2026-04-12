# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.
# Ported from jetson_stats GUI library (AGPL-3.0)

import curses


def init_colorscale_pair(num, fg, bg):
    curses.init_pair(num, fg if curses.COLORS >= 256 else curses.COLOR_WHITE,
                     bg if curses.COLORS >= 256 else curses.COLOR_BLACK)


class NColors:
    """Named color constants for curses GUI."""

    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6

    iRED = 7
    iGREEN = 8
    iYELLOW = 9
    iBLUE = 10
    iMAGENTA = 11
    iCYAN = 12

    def __init__(self, color_filter=False):
        curses.init_pair(NColors.RED, curses.COLOR_RED if not color_filter else curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(NColors.GREEN, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(NColors.YELLOW, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(NColors.BLUE, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(NColors.MAGENTA, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(NColors.CYAN, curses.COLOR_CYAN, curses.COLOR_BLACK)
        # Inverted (background colors)
        curses.init_pair(NColors.iRED, curses.COLOR_WHITE, curses.COLOR_RED if not color_filter else curses.COLOR_BLUE)
        curses.init_pair(NColors.iGREEN, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.init_pair(NColors.iYELLOW, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(NColors.iBLUE, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(NColors.iMAGENTA, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
        curses.init_pair(NColors.iCYAN, curses.COLOR_WHITE, curses.COLOR_CYAN)

    @staticmethod
    def init_grey(num):
        init_colorscale_pair(num, 240, curses.COLOR_BLACK)

    @staticmethod
    def italic():
        return curses.A_ITALIC if hasattr(curses, 'A_ITALIC') else curses.A_NORMAL

    @staticmethod
    def red():
        return curses.color_pair(NColors.RED)

    @staticmethod
    def green():
        return curses.color_pair(NColors.GREEN)

    @staticmethod
    def yellow():
        return curses.color_pair(NColors.YELLOW)

    @staticmethod
    def blue():
        return curses.color_pair(NColors.BLUE)

    @staticmethod
    def magenta():
        return curses.color_pair(NColors.MAGENTA)

    @staticmethod
    def cyan():
        return curses.color_pair(NColors.CYAN)

    @staticmethod
    def ired():
        return curses.color_pair(NColors.iRED)

    @staticmethod
    def igreen():
        return curses.color_pair(NColors.iGREEN)

    @staticmethod
    def iyellow():
        return curses.color_pair(NColors.iYELLOW)

    @staticmethod
    def iblue():
        return curses.color_pair(NColors.iBLUE)

    @staticmethod
    def imagenta():
        return curses.color_pair(NColors.iMAGENTA)

    @staticmethod
    def icyan():
        return curses.color_pair(NColors.iCYAN)
