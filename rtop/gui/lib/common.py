# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.
# Ported from jetson_stats GUI library (AGPL-3.0)

import os
import sys
import curses
from functools import wraps
from .colors import NColors


def check_curses(func):
    """Decorator to catch curses errors gracefully."""
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except curses.error:
            pass
    return wrapped


def set_xterm_title(title):
    """Set XTerm title using escape sequences."""
    if os.environ.get('TERM') in ('xterm', 'xterm-color', 'xterm-256color',
                                   'linux', 'screen', 'screen-256color', 'screen-bce'):
        sys.stdout.write('\33]0;' + title + '\a')
        sys.stdout.flush()


def strfdelta(tdelta):
    """Format a time delta (seconds or timedelta) to a human-readable string."""
    if isinstance(tdelta, (int, float)):
        seconds = int(tdelta)
    else:
        seconds = int(tdelta.total_seconds())
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def find_unit(size, power, divider=1.0, n=0, start=''):
    n = 0
    power_labels = ['m', '', 'k', 'M', 'G', 'T']
    if size is None:
        size = 0
    while size > power - 1:
        divider *= power
        size /= power
        n += 1
    idx = power_labels.index(start) if start in power_labels else 1
    return round(size, 1), divider, power_labels[n + idx]


def size_min(num, divider=1.0, n=0, start=''):
    return find_unit(num, 1024.0, divider, n, start)


def unit_min(num, divider=1.0, n=0, start=''):
    return find_unit(num, 1000.0, divider, n, start)


def size_to_string(value, unit=''):
    return value_to_string(value, unit, "", size_min)


def unit_to_string(value, unit='', type_str=''):
    return value_to_string(value, unit, type_str, unit_min)


def value_to_string(value, unit, type_str, func):
    value, _, unit_out = func(value, start=unit)
    value_string = str(value)
    if value >= 100:
        value_string = value_string[:4].rstrip('.')
    return "{value}{unit}{type}".format(value=value_string, unit=unit_out, type=type_str)


def label_freq(frq, start='k'):
    szw, _, k_unit = size_min(frq, start=start)
    if szw >= 100:
        label = '{tot:2.0f}{unit}Hz'.format(tot=szw, unit=k_unit)
    elif szw >= 10:
        label = '{tot:2.0f} {unit}Hz'.format(tot=szw, unit=k_unit)
    else:
        label = '{tot:2.1f}{unit}Hz'.format(tot=szw, unit=k_unit)
    return label


def _safe_str(value):
    """Convert value to string and strip null bytes for curses safety."""
    s = str(value)
    return s.replace('\x00', '')


def plot_name_info(stdscr, offset, start, name, value, color=curses.A_NORMAL, spacing=0):
    """Draw a labeled info line: 'Name: value'."""
    value = _safe_str(value)
    try:
        stdscr.addstr(offset, start, name + ":", curses.A_BOLD)
        stdscr.addstr(offset, start + len(name) + 2 + spacing, value, color)
    except curses.error:
        pass
    return len(name) + len(value) + 2


def plot_dictionary(stdscr, pos_y, pos_x, name_or_data, data=None, size=None):
    """Draw a dictionary as a labeled table.

    Can be called as:
        plot_dictionary(stdscr, y, x, dict_data)  - no section header
        plot_dictionary(stdscr, y, x, "Title", dict_data)  - with header
    Returns the new y position after the last line.
    """
    if isinstance(name_or_data, dict):
        # Called as plot_dictionary(stdscr, pos_y, pos_x, data_dict)
        data = name_or_data
        header = None
    else:
        # Called as plot_dictionary(stdscr, pos_y, pos_x, name, data)
        header = name_or_data
    y = pos_y
    if header:
        try:
            stdscr.addstr(y, pos_x, header, curses.A_BOLD)
        except curses.error:
            pass
        y += 1
    for key, value in data.items():
        try:
            stdscr.addstr(y, pos_x + 1, _safe_str(key) + ":", curses.A_BOLD)
        except curses.error:
            pass
        color = curses.A_NORMAL if value else NColors.red()
        if not value:
            value = "MISSING"
        str_val = _safe_str(value)
        if size and len(str(key)) + len(str_val) + 3 > size:
            str_val = str_val[:size - len(str(key)) - 3]
        try:
            stdscr.addstr(y, pos_x + 3 + len(_safe_str(key)), str_val, color)
        except curses.error:
            pass
        y += 1
    return y


def draw_bar(stdscr, y, x, width, value, max_value, label=""):
    """Draw a horizontal bar gauge with an optional label.

    Args:
        stdscr: curses window
        y: row position
        x: column position
        width: bar width in characters
        value: current value
        max_value: maximum value (used to compute percentage)
        label: optional label text drawn before the bar
    """
    if width <= 0:
        return
    percentage = (value / max_value * 100) if max_value > 0 else 0
    # Draw label
    if label:
        try:
            stdscr.addstr(y, x, f"{label}: ")
            x += len(label) + 2
        except curses.error:
            pass
    # Choose color based on percentage
    if percentage > 80:
        color = NColors.RED
    elif percentage > 50:
        color = NColors.YELLOW
    else:
        color = NColors.GREEN
    filled = int(width * min(percentage, 100) / 100)
    try:
        stdscr.addstr(y, x, "[" + "█" * filled + "░" * (width - filled) + "]", curses.color_pair(color))
    except curses.error:
        pass
