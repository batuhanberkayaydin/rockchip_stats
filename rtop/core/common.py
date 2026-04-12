# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Shared utilities for rtop core modules.
"""

import re
import os
from random import choice
from string import ascii_letters
from base64 import b64encode
import subprocess as sp
import logging
import socket
import fcntl
import struct
import array

AUTH_RE = re.compile(r""".*__author__ = ["'](.*?)['"]""", re.S)
logger = logging.getLogger(__name__)


class GenericInterface(object):
    """Generic dictionary-like interface for stats data."""

    def __init__(self):
        self._controller = None
        self._init = None
        self._data = {}

    def _initialize(self, controller, init={}):
        self._controller = controller
        self._init = init

    def _update(self, data):
        self._data = data

    def items(self):
        return self._data.items()

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __reversed__(self):
        return reversed(self._data)

    def __missing__(self, key):
        raise KeyError(key)

    def __eq__(self, other):
        if isinstance(other, GenericInterface):
            return self._data == other._data
        elif isinstance(other, dict):
            return self._data == other
        else:
            return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        else:
            return not result

    def __str__(self):
        return str(self._data)

    def __repr__(self):
        return repr(self._data)


def compare_versions(source_version, get_version):
    source_major_minor = '.'.join(source_version.split('.')[:2])
    get_major_minor = '.'.join(get_version.split('.')[:2])
    return source_major_minor == get_major_minor


def check_file(path):
    """Check if a file exists and is readable."""
    return os.path.isfile(path) and os.access(path, os.R_OK)


def cat(path):
    """Read the first line of a file, stripping null bytes and newlines."""
    with open(path, 'r') as f:
        return f.readline().rstrip('\x00')


def locate_commands(name, commands):
    """Find the first existing command in a list of paths."""
    for cmd in commands:
        if os.path.exists(cmd):
            return cmd
    return None


def get_uptime():
    """Read system uptime in seconds from /proc/uptime."""
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return uptime_seconds


def status_disk(folder="/var/"):
    """Get disk usage statistics for a folder."""
    disk = os.statvfs(folder)
    totalSpace = float(disk.f_bsize * disk.f_blocks) / 1024 / 1024 / 1024
    totalUsedSpace = float(disk.f_bsize * (disk.f_blocks - disk.f_bfree)) / 1024 / 1024 / 1024
    totalAvailSpace = float(disk.f_bsize * disk.f_bfree) / 1024 / 1024 / 1024
    totalAvailSpaceNonRoot = float(disk.f_bsize * disk.f_bavail) / 1024 / 1024 / 1024
    return {'total': totalSpace,
            'used': totalUsedSpace,
            'available': totalAvailSpace,
            'available_no_root': totalAvailSpaceNonRoot,
            'unit': 'G'
            }


def get_local_interfaces():
    """Returns a dictionary of network interface name:ip key value pairs."""
    MAX_BYTES = 4096
    FILL_CHAR = b'\0'
    SIOCGIFCONF = 0x8912
    hostname = socket.gethostname()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', MAX_BYTES * FILL_CHAR)
    names_address, names_length = names.buffer_info()
    mutable_byte_buffer = struct.pack('iL', MAX_BYTES, names_address)
    mutated_byte_buffer = fcntl.ioctl(sock.fileno(), SIOCGIFCONF, mutable_byte_buffer)
    sock.close()
    max_bytes_out, names_address_out = struct.unpack('iL', mutated_byte_buffer)
    namestr = bytearray(names)
    ip_dict = {}
    for i in range(0, max_bytes_out, 40):
        name = namestr[i: i + 16].split(FILL_CHAR, 1)[0]
        name = name.decode('utf-8')
        ip_bytes = namestr[i + 20:i + 24]
        full_addr = []
        for netaddr in ip_bytes:
            if isinstance(netaddr, int):
                full_addr.append(str(netaddr))
            elif isinstance(netaddr, str):
                full_addr.append(str(ord(netaddr)))
        ip_dict[name] = '.'.join(full_addr)
    if 'lo' in ip_dict:
        del ip_dict['lo']
    return {"hostname": hostname, "interfaces": ip_dict}


def get_var(MATCH_RE):
    """Extract a variable value from the package __init__.py."""
    with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../', "__init__.py")) as fp:
        match = MATCH_RE.match(fp.read())
        value = match.group(1) if match else ''.join(choice(ascii_letters) for i in range(16))
    return value


def get_key():
    return str(b64encode(get_var(AUTH_RE).encode("utf-8")))
