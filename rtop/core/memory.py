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
Memory monitoring for Rockchip SoCs.

Reads RAM, Swap, CMA memory, and DMA-BUF usage from /proc/meminfo
and other kernel interfaces.
"""

import os
import re
import logging
import shutil
from .common import cat, GenericInterface

logger = logging.getLogger(__name__)

# Known block-device prefixes for on-board storage on Rockchip platforms.
#   mmcblk* -> eMMC or SD card (sys/block/mmcblk*/device/type tells them apart)
#   nvme*   -> NVMe SSD over PCIe (RK3588/RK3576)
#   sd*     -> USB mass storage / SATA
_STORAGE_DEV_PREFIXES = ('mmcblk', 'nvme', 'sd')

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


def _mmcblk_kind(dev_name):
    """Distinguish eMMC vs SD card for an mmcblk device.

    /sys/block/mmcblkX/device/type returns "MMC" (eMMC) or "SD".
    Falls back to the raw name if the sysfs entry is absent.
    """
    sys_type = '/sys/block/{}/device/type'.format(dev_name)
    if os.path.isfile(sys_type):
        try:
            t = cat(sys_type).strip()
            if t == 'SD':
                return 'SD'
            if t == 'MMC':
                return 'eMMC'
        except (IOError, PermissionError):
            pass
    return 'MMC'


def _storage_label(device):
    """Return a short human label for a /dev/... block device path."""
    base = os.path.basename(device)
    # Strip partition suffix: mmcblk0p1 -> mmcblk0, nvme0n1p1 -> nvme0n1, sda1 -> sda
    if base.startswith('mmcblk'):
        dev = base.split('p')[0]
        return _mmcblk_kind(dev)
    if base.startswith('nvme'):
        return 'NVMe'
    if base.startswith('sd'):
        return 'Disk'
    return base


def storage_info():
    """Return a list of dicts describing on-board storage usage.

    Each entry:
        {'name': 'eMMC' | 'SD' | 'NVMe' | 'Disk',
         'device': '/dev/mmcblk0p1', 'mount': '/', 'total': bytes,
         'used': bytes, 'free': bytes}

    Only mounted real block devices are reported (we skip tmpfs / overlay / proc
    pseudo-filesystems).
    """
    entries = []
    seen = set()
    try:
        with open('/proc/mounts', 'r') as f:
            lines = f.readlines()
    except (IOError, OSError):
        return entries

    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        device, mount, fstype = parts[0], parts[1], parts[2]
        if not device.startswith('/dev/'):
            continue
        base = os.path.basename(device)
        if not base.startswith(_STORAGE_DEV_PREFIXES):
            continue
        # Deduplicate multiple mounts of same device
        if device in seen:
            continue
        seen.add(device)
        try:
            usage = shutil.disk_usage(mount)
        except (OSError, PermissionError):
            continue
        entries.append({
            'name': _storage_label(device),
            'device': device,
            'mount': mount,
            'fstype': fstype,
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
        })
    return entries


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

        # Storage devices (eMMC / SD / NVMe) — bytes, not kB
        try:
            status['storage'] = storage_info()
        except Exception as e:
            logger.debug("storage_info failed: %s", e)
            status['storage'] = []

        return status


class MemoryService(object):
    """Service for collecting memory statistics."""

    def __init__(self):
        self._memory = Memory()

    def get_status(self):
        """Get current memory status."""
        return self._memory.get_status()
