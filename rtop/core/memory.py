# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Memory monitoring for Rockchip SoCs.

Reads RAM, Swap, CMA memory, and DMA-BUF usage from /proc/meminfo
and other kernel interfaces.
"""

import os
import re
import logging
from .common import cat, GenericInterface

logger = logging.getLogger(__name__)

# Memory info regex
MEMINFO_REG = re.compile(r'(?P<key>[^:]+):\s+(?P<value>.+)\s+(?P<unit>.)B')


def meminfo():
    """Read memory info from /proc/meminfo."""
    status_mem = {}
    try:
        with open("/proc/meminfo", 'r') as fp:
            for line in fp:
                match = re.search(MEMINFO_REG, line.strip())
                if match:
                    parsed_line = match.groupdict()
                    status_mem[parsed_line['key']] = int(parsed_line['value'])
    except IOError:
        logger.warning("Cannot read /proc/meminfo")
    return status_mem


class Memory(GenericInterface):
    """Memory statistics interface."""

    def __init__(self):
        super(Memory, self).__init__()

    def get_status(self):
        """Get current memory status."""
        info = meminfo()
        status = {}

        # Total RAM
        if 'MemTotal' in info:
            status['total'] = info['MemTotal']
        if 'MemFree' in info:
            status['free'] = info['MemFree']
        if 'MemAvailable' in info:
            status['available'] = info['MemAvailable']
        if 'Buffers' in info:
            status['buffers'] = info['Buffers']
        if 'Cached' in info:
            status['cached'] = info['Cached']

        # Calculate used
        if 'MemTotal' in info and 'MemAvailable' in info:
            status['used'] = info['MemTotal'] - info['MemAvailable']

        # Swap
        if 'SwapTotal' in info:
            status['swap_total'] = info['SwapTotal']
        if 'SwapFree' in info:
            status['swap_free'] = info['SwapFree']
            if 'SwapTotal' in info:
                status['swap_used'] = info['SwapTotal'] - info['SwapFree']

        # CMA memory (Contiguous Memory Allocator - important for Rockchip VPU)
        if 'CmaTotal' in info:
            status['cma_total'] = info['CmaTotal']
        if 'CmaFree' in info:
            status['cma_free'] = info['CmaFree']
            if 'CmaTotal' in info:
                status['cma_used'] = info['CmaTotal'] - info['CmaFree']

        # Shmem (shared memory, includes DMA-BUF)
        if 'Shmem' in info:
            status['shmem'] = info['Shmem']

        # Unit is KB
        status['unit'] = 'kB'

        return status


class MemoryService(object):
    """Service for collecting memory statistics."""

    def __init__(self):
        self._memory = Memory()

    def get_status(self):
        """Get current memory status."""
        return self._memory.get_status()
