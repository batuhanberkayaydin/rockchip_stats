# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Process table reading for monitoring system processes.
"""

import os
import logging

logger = logging.getLogger(__name__)


def read_process_table():
    """Read the system process table from /proc.

    Returns a list of dicts with process information.
    """
    processes = []
    try:
        for pid_dir in os.listdir("/proc"):
            if not pid_dir.isdigit():
                continue
            try:
                pid = int(pid_dir)
                # Read command line
                cmdline_path = os.path.join("/proc", pid_dir, "cmdline")
                if os.path.isfile(cmdline_path):
                    with open(cmdline_path, 'r') as f:
                        cmdline = f.read().replace('\x00', ' ').strip()
                    if cmdline:
                        # Read stat for CPU and memory info
                        stat_path = os.path.join("/proc", pid_dir, "stat")
                        stat_info = {}
                        if os.path.isfile(stat_path):
                            with open(stat_path, 'r') as f:
                                stat_parts = f.read().split()
                                if len(stat_parts) >= 24:
                                    stat_info = {
                                        'pid': pid,
                                        'comm': stat_parts[1].strip('()'),
                                        'state': stat_parts[2],
                                        'utime': int(stat_parts[13]),
                                        'stime': int(stat_parts[14]),
                                        'rss': int(stat_parts[23]),  # in pages
                                    }
                        stat_info['cmdline'] = cmdline
                        stat_info['pid'] = pid
                        processes.append(stat_info)
            except (IOError, ValueError, PermissionError):
                continue
    except OSError:
        logger.warning("Cannot read /proc for process table")
    return processes


class ProcessService(object):
    """Service for collecting process information."""

    def __init__(self):
        pass

    def get_status(self):
        """Get current process table."""
        return read_process_table()
