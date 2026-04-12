# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Process reader - reads top processes from /proc.
Returns list of dicts sorted by CPU usage.
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

# Cached page size
_PAGE_SIZE = os.sysconf('SC_PAGE_SIZE') if hasattr(os, 'sysconf') else 4096
_CLK_TCK = os.sysconf('SC_CLK_TCK') if hasattr(os, 'sysconf') else 100

# Cache for previous CPU times to calculate delta
_prev_times = {}  # pid -> (utime + stime, timestamp)


def _read_file(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except (IOError, OSError):
        return ''


def _get_uid_name(uid):
    """Convert UID to username."""
    try:
        import pwd
        return pwd.getpwuid(int(uid)).pw_name
    except Exception:
        return str(uid)


def get_processes(max_count=10):
    """Read top processes from /proc, return list of dicts.

    Each dict has: pid, user, pri, stat, cpu, mem, mem_str, cmd
    """
    import time
    now = time.time()

    try:
        pids = [p for p in os.listdir('/proc') if p.isdigit()]
    except OSError:
        return []

    # Read total memory once
    mem_total_kb = 0
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    mem_total_kb = int(line.split()[1])
                    break
    except (IOError, OSError):
        pass

    procs = []
    for pid_str in pids:
        pid = int(pid_str)
        stat_path = '/proc/{}/stat'.format(pid_str)
        status_path = '/proc/{}/status'.format(pid_str)
        cmdline_path = '/proc/{}/cmdline'.format(pid_str)

        stat = _read_file(stat_path)
        if not stat:
            continue

        # Parse /proc/pid/stat
        # Format: pid (comm) state ppid ... utime stime ... priority nice ... starttime vsize rss
        try:
            # Find comm between first ( and last ) to handle spaces in name
            m = re.match(r'^(\d+)\s+\((.+)\)\s+(\S+)\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)\s+(\d+)\s+\S+\s+\S+\s+(-?\d+)\s+(-?\d+)\s+\S+\s+\S+\s+\S+\s+(\d+)\s+\S+\s+(\d+)', stat)
            if not m:
                continue
            comm = m.group(2)
            state = m.group(3)
            utime = int(m.group(4))
            stime = int(m.group(5))
            priority = int(m.group(6))
            # nice = int(m.group(7))
            rss = int(m.group(9))   # in pages
        except Exception:
            continue

        # CPU%: delta of (utime+stime) / elapsed wall time
        total_ticks = utime + stime
        prev = _prev_times.get(pid)
        if prev is not None:
            prev_ticks, prev_time = prev
            elapsed = now - prev_time
            if elapsed > 0:
                cpu_pct = (total_ticks - prev_ticks) / _CLK_TCK / elapsed * 100.0
            else:
                cpu_pct = 0.0
        else:
            cpu_pct = 0.0
        _prev_times[pid] = (total_ticks, now)

        # Memory in KB
        mem_kb = rss * _PAGE_SIZE // 1024
        if mem_total_kb > 0:
            mem_pct = mem_kb / mem_total_kb * 100.0
        else:
            mem_pct = 0.0

        # Format mem_str
        if mem_kb >= 1024 * 1024:
            mem_str = '{:.1f}G'.format(mem_kb / 1024 / 1024)
        elif mem_kb >= 1024:
            mem_str = '{:.1f}M'.format(mem_kb / 1024)
        else:
            mem_str = '{}K'.format(mem_kb)

        # Get UID from status
        uid = 0
        status = _read_file(status_path)
        for line in status.splitlines():
            if line.startswith('Uid:'):
                parts = line.split()
                if len(parts) >= 2:
                    uid = parts[1]
                break
        user = _get_uid_name(uid)

        # Command line
        cmdline = _read_file(cmdline_path)
        if cmdline:
            cmd = cmdline.replace('\x00', ' ').strip()
            if not cmd:
                cmd = '[{}]'.format(comm)
        else:
            cmd = '[{}]'.format(comm)

        procs.append({
            'pid':     pid,
            'user':    user,
            'pri':     priority,
            'stat':    state,
            'cpu':     max(0.0, cpu_pct),
            'mem':     mem_pct,
            'mem_str': mem_str,
            'cmd':     cmd,
        })

    # Sort by CPU descending, take top max_count
    procs.sort(key=lambda p: p['cpu'], reverse=True)
    return procs[:max_count]
