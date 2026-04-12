# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Background service for rtop data collection.

Uses multiprocessing manager to share data between the service process
and client connections (GUI, API, etc.).
"""

import os
import sys
import logging
from copy import deepcopy
from multiprocessing import Process, Queue, Event
from multiprocessing.managers import SyncManager

from .core.common import get_uptime
from .core.hardware import get_hardware, get_platform_variables
from .core.config import Config
from .core.cpu import CPUService
from .core.memory import MemoryService
from .core.processes import ProcessService
from .core.gpu import GPUService
from .core.npu import NPUService
from .core.rga import RGAService
from .core.mpp import MPPService
from .core.temperature import TemperatureService
from .core.fan import FanService

import multiprocessing
multiprocessing.set_start_method("fork", force=True)

logger = logging.getLogger(__name__)

# Service socket path
SERVICE_SOCKET = '/run/rtop.sock'

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

try:
    import queue
except ImportError:
    import Queue as queue


class RtopServer(object):
    """Background server that collects all Rockchip hardware stats."""

    def __init__(self, interval=1.0):
        self._interval = interval
        self._config = Config()
        # Initialize all services
        self._cpu = CPUService()
        self._gpu = GPUService()
        self._npu = NPUService()
        self._rga = RGAService()
        self._mpp = MPPService()
        self._memory = MemoryService()
        self._temperature = TemperatureService()
        self._fan = FanService()
        self._processes = ProcessService()
        # Hardware info (static, read once)
        self._hardware = get_hardware()
        self._platform = get_platform_variables()
        logger.info("RtopServer initialized")

    def _collect(self):
        """Collect all stats from all services."""
        stats = {}
        stats['uptime'] = get_uptime()
        stats['cpu'] = self._cpu.get_status()
        stats['gpu'] = self._gpu.get_status()
        stats['npu'] = self._npu.get_status()
        stats['rga'] = self._rga.get_status()
        stats['mpp'] = self._mpp.get_status()
        stats['memory'] = self._memory.get_status()
        stats['temperature'] = self._temperature.get_status()
        stats['fan'] = self._fan.get_status()
        stats['processes'] = self._processes.get_status()
        stats['hardware'] = self._hardware
        stats['platform'] = self._platform
        return stats

    def serve(self, pipe_path=SERVICE_SOCKET):
        """Start serving stats via a Unix socket."""
        logger.info("Starting rtop server on %s", pipe_path)
        # Collect initial data
        data = self._collect()

        class StatsManager(SyncManager):
            pass

        StatsManager.register('get_stats', callable=lambda: data)
        StatsManager.register('get_queue', callable=lambda: Queue())
        StatsManager.register('get_event', callable=lambda: Event())

        manager = StatsManager(address=pipe_path)
        server = manager.get_server()
        server.serve_forever()


class RtopManager(SyncManager):
    """Client-side manager for connecting to the rtop service."""
    pass


def status_service():
    """Check if the rtop service is running."""
    return os.path.exists(SERVICE_SOCKET)


def remove_service_pipe():
    """Remove the service socket file."""
    if os.path.exists(SERVICE_SOCKET):
        try:
            os.remove(SERVICE_SOCKET)
        except OSError:
            pass


def uninstall_service():
    """Uninstall the rtop systemd service."""
    import subprocess as sp
    if shutil.which('systemctl'):
        sp.call(['systemctl', 'stop', 'rtop.service'])
        sp.call(['systemctl', 'disable', 'rtop.service'])
        service_path = '/etc/systemd/system/rtop.service'
        if os.path.isfile(service_path):
            os.remove(service_path)
        sp.call(['systemctl', 'daemon-reload'])


def install_service(folder, copy=True):
    """Install the rtop systemd service."""
    import shutil
    service_src = os.path.join(folder, 'services', 'rtop.service')
    service_dst = '/etc/systemd/system/rtop.service'
    if os.path.isfile(service_src):
        shutil.copy2(service_src, service_dst)
        import subprocess as sp
        sp.call(['systemctl', 'daemon-reload'])
        sp.call(['systemctl', 'enable', 'rtop.service'])
        sp.call(['systemctl', 'start', 'rtop.service'])


def set_service_permission():
    """Set permissions for the service socket."""
    import subprocess as sp
    sp.call(['groupadd', 'rtop'])
    user = os.environ.get('SUDO_USER', '') or 'root'
    sp.call(['usermod', '-a', '-G', 'rtop', user])
