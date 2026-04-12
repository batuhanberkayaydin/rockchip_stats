# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
GPU page - Mali GPU detailed information with chart, matching jtop style.
"""

import curses
from .rtopgui import Page
from .lib.chart import Chart
from .lib.colors import NColors
from .lib.common import check_curses, unit_to_string, plot_name_info
from .lib.linear_gauge import basic_gauge, freq_gauge


def compact_gpu(stdscr, pos_y, pos_x, width, client):
    """Draw compact GPU gauge for ALL page."""
    gpu = client.gpu
    if not gpu:
        return 0
    load = gpu.get('load', 0)
    freq = gpu.get('freq', 0)
    data = {
        'name': 'GPU',
        'color': NColors.magenta(),
        'online': True,
        'values': [(load, NColors.magenta())],
    }
    if freq:
        curr_string = unit_to_string(freq, 'k', 'Hz')
        try:
            stdscr.addstr(pos_y, pos_x + width - 8, curr_string, NColors.italic())
        except curses.error:
            pass
    basic_gauge(stdscr, pos_y, pos_x + 1, width - 10, data)
    return 1


class GPU(Page):

    def __init__(self, stdscr, client):
        super(GPU, self).__init__("GPU", stdscr, client)
        # Create GPU load chart
        self._chart = Chart("GPU", self.update_chart, client=client,
                            color_text=curses.COLOR_MAGENTA,
                            color_chart=[curses.COLOR_MAGENTA])

    def update_chart(self, client, name):
        gpu = client.gpu
        if not gpu:
            return {'active': False, 'value': [0]}
        return {
            'active': True,
            'value': [gpu.get('load', 0)],
        }

    @check_curses
    def draw(self, key, mouse):
        height, width, first = self.size_page()
        gpu = self.rtop.gpu
        if not gpu:
            self.stdscr.addstr(first + 1, 1, "No Mali GPU detected", curses.A_BOLD)
            return
        # Update chart data
        self._chart.update(self.rtop)
        # GPU load gauge
        load = gpu.get('load', 0)
        data = {
            'name': 'GPU',
            'color': NColors.magenta(),
            'online': True,
            'values': [(load, NColors.magenta())],
        }
        basic_gauge(self.stdscr, first + 1, 1, width - 2, data)
        # Frequency gauge
        freq = gpu.get('freq', 0)
        min_freq = gpu.get('min_freq', 0)
        max_freq = gpu.get('max_freq', 0)
        if freq and min_freq and max_freq:
            freq_data = {
                'name': 'Frq',
                'cur': freq,
                'min': min_freq,
                'max': max_freq,
                'online': True,
            }
            freq_gauge(self.stdscr, first + 2, 1, width - 2, freq_data)
        elif freq:
            curr_string = unit_to_string(freq, 'k', 'Hz')
            plot_name_info(self.stdscr, first + 2, 1, "Frequency", curr_string)
        # Governor
        governor = gpu.get('governor', '')
        if governor:
            plot_name_info(self.stdscr, first + 3, 1, "Governor", governor)
        # Draw chart
        chart_start_y = first + 5
        chart_height = height - chart_start_y - 3
        if chart_height > 3:
            self._chart.draw(self.stdscr, [1, width - 2], [chart_start_y, chart_start_y + chart_height])
        # GPU temperature at bottom
        temps = self.rtop.temperature
        temp_y = height - 2
        for name, val in temps.items():
            if 'gpu' in name.lower() and isinstance(val, (int, float)):
                temp_c = val / 1000
                if temp_c > 70:
                    color = NColors.red()
                elif temp_c > 50:
                    color = NColors.yellow()
                else:
                    color = NColors.green()
                plot_name_info(self.stdscr, temp_y, 1, "Temp", "{:.1f}C".format(temp_c), color)
                break
