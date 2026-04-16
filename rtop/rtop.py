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
rtop client - connects to the rtop background service and provides
a Python API for reading Rockchip hardware statistics.
"""

import logging
import json
from datetime import datetime, timedelta
from multiprocessing import Event
from threading import Thread
from .service import RtopManager
from .core.hardware import get_platform_variables
from .core.memory import Memory
from .core.fan import Fan
from .core.gpu import GPU
from .core.npu import NPUService as NPU
from .core.exceptions import RtopException

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

try:
    PermissionError
except NameError:
    PermissionError = OSError

logger = logging.getLogger(__name__)

TIMEOUT_GAIN = 3


class DateTimeEncoder(json.JSONEncoder):
    def default(self, z):
        if isinstance(z, datetime):
            return str(z)
        elif isinstance(z, timedelta):
            return str(z)
        else:
            return super().default(z)


class rtop(Thread):
    """
    Main client class for accessing Rockchip hardware statistics.

    Usage:
        with rtop() as rockchip:
            while rockchip.ok():
                print(rockchip.stats)
    """

    def __init__(self, interval=1.0):
        super(rtop, self).__init__()
        self._trigger = Event()
        self._error = None
        self._running = False
        self._interval = float(interval)
        self._observers = set()
        self._stats = {}
        # Register manager methods
        RtopManager.register('get_queue')
        RtopManager.register("sync_data")
        RtopManager.register('sync_event')
        self._broadcaster = RtopManager()

    def run(self):
        """Main thread loop - connect to service and read stats."""
        self._running = True
        try:
            self._broadcaster.connect()
            # Get the data queue
            queue = self._broadcaster.get_queue()
            while self._running:
                try:
                    # Read stats from service
                    data = queue.get(timeout=self._interval)
                    self._stats = data
                    # Notify observers
                    for callback in self._observers:
                        try:
                            callback(self._stats)
                        except Exception as e:
                            logger.error("Observer callback error: %s", e)
                except Exception:
                    # Timeout - continue loop
                    pass
        except Exception as e:
            self._error = e
            logger.error("rtop client error: %s", e)
        finally:
            self._running = False

    def ok(self):
        """Check if the client is running and return the update interval delay.

        Returns False when the client should stop.
        """
        if self._error is not None:
            raise self._error
        self._trigger.wait(self._interval)
        return self._running

    @property
    def stats(self):
        """Return the current stats dictionary."""
        return self._stats

    @property
    def cpu(self):
        """Return CPU stats."""
        return self._stats.get('cpu', {})

    @property
    def gpu(self):
        """Return GPU stats."""
        return self._stats.get('gpu', {})

    @property
    def npu(self):
        """Return NPU stats."""
        return self._stats.get('npu', {})

    @property
    def rga(self):
        """Return RGA stats."""
        return self._stats.get('rga', {})

    @property
    def mpp(self):
        """Return MPP stats."""
        return self._stats.get('mpp', {})

    @property
    def memory(self):
        """Return memory stats."""
        return self._stats.get('memory', {})

    @property
    def temperature(self):
        """Return temperature stats."""
        return self._stats.get('temperature', {})

    @property
    def fan(self):
        """Return fan stats."""
        return self._stats.get('fan', {})

    @property
    def power(self):
        """Return power stats (None when the board exposes no sensors)."""
        return self._stats.get('power', {})

    @property
    def hardware(self):
        """Return hardware info."""
        return self._stats.get('hardware', {})

    @property
    def platform(self):
        """Return platform info."""
        return self._stats.get('platform', {})

    @property
    def interval(self):
        """Return the update interval."""
        return self._interval

    def register_observer(self, callback):
        """Register a callback to be called on each stats update."""
        self._observers.add(callback)

    def unregister_observer(self, callback):
        """Unregister an observer callback."""
        self._observers.discard(callback)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._running = False
        self._trigger.set()
        self.join(timeout=TIMEOUT_GAIN)
        return False


class StandaloneRtop(object):
    """
    Standalone client that reads Rockchip hardware stats directly
    from sysfs/procfs, without requiring the background service.

    Usage:
        with StandaloneRtop() as rockchip:
            while rockchip.ok():
                print(rockchip.cpu)
    """

    def __init__(self, interval=1.0):
        self._interval = float(interval)
        self._running = False
        self._stats = {}
        # Initialize direct-reading services
        self._cpu_svc = None
        self._gpu_svc = None
        self._npu_svc = None
        self._rga_svc = None
        self._mpp_svc = None
        self._memory_svc = None
        self._temperature_svc = None
        self._fan_svc = None
        self._power_svc = None
        self._hardware = {}
        self._platform = {}
        # Lazy-init flag
        self._initialized = False
        self._processes = []

    def _init_services(self):
        """Initialize all monitoring services (lazy, on first use)."""
        if self._initialized:
            return
        try:
            from .core.cpu import CPUService
            self._cpu_svc = CPUService()
        except Exception as e:
            logger.warning("CPU service init failed: %s", e)
        try:
            from .core.gpu import GPUService
            self._gpu_svc = GPUService()
        except Exception as e:
            logger.warning("GPU service init failed: %s", e)
        try:
            from .core.npu import NPUService
            self._npu_svc = NPUService()
        except Exception as e:
            logger.warning("NPU service init failed: %s", e)
        try:
            from .core.rga import RGAService
            self._rga_svc = RGAService()
        except Exception as e:
            logger.warning("RGA service init failed: %s", e)
        try:
            from .core.mpp import MPPService
            self._mpp_svc = MPPService()
        except Exception as e:
            logger.warning("MPP service init failed: %s", e)
        try:
            from .core.memory import MemoryService
            self._memory_svc = MemoryService()
        except Exception as e:
            logger.warning("Memory service init failed: %s", e)
        try:
            from .core.temperature import TemperatureService
            self._temperature_svc = TemperatureService()
        except Exception as e:
            logger.warning("Temperature service init failed: %s", e)
        try:
            from .core.fan import FanService
            self._fan_svc = FanService()
        except Exception as e:
            logger.warning("Fan service init failed: %s", e)
        try:
            from .core.power import PowerService
            self._power_svc = PowerService()
        except Exception as e:
            logger.warning("Power service init failed: %s", e)
        try:
            from .core.hardware import get_hardware, get_platform_variables
            self._hardware = get_hardware()
            self._platform = get_platform_variables()
        except Exception as e:
            logger.warning("Hardware detection failed: %s", e)
        self._initialized = True

    def _collect(self):
        """Collect all stats directly from services and transform for GUI."""
        raw = {}
        try:
            from .core.common import get_uptime
            raw['uptime'] = get_uptime()
        except Exception:
            raw['uptime'] = 0

        if self._cpu_svc:
            try:
                raw['cpu'] = self._cpu_svc.get_status()
            except Exception as e:
                logger.debug("CPU read error: %s", e)
        if self._gpu_svc:
            try:
                raw['gpu'] = self._gpu_svc.get_status()
            except Exception as e:
                logger.debug("GPU read error: %s", e)
        if self._npu_svc:
            try:
                raw['npu'] = self._npu_svc.get_status()
            except Exception as e:
                logger.debug("NPU read error: %s", e)
        if self._rga_svc:
            try:
                raw['rga'] = self._rga_svc.get_status()
            except Exception as e:
                logger.debug("RGA read error: %s", e)
        if self._mpp_svc:
            try:
                raw['mpp'] = self._mpp_svc.get_status()
            except Exception as e:
                logger.debug("MPP read error: %s", e)
        if self._memory_svc:
            try:
                raw['memory'] = self._memory_svc.get_status()
            except Exception as e:
                logger.debug("Memory read error: %s", e)
        if self._temperature_svc:
            try:
                raw['temperature'] = self._temperature_svc.get_status()
            except Exception as e:
                logger.debug("Temperature read error: %s", e)
        if self._fan_svc:
            try:
                raw['fan'] = self._fan_svc.get_status()
            except Exception as e:
                logger.debug("Fan read error: %s", e)
        if self._power_svc:
            try:
                raw['power'] = self._power_svc.get_status()
            except Exception as e:
                logger.debug("Power read error: %s", e)

        raw['hardware'] = self._hardware
        raw['platform'] = self._platform

        # Read processes
        try:
            from .core.process import get_processes
            self._processes = get_processes(max_count=8)
        except Exception as e:
            logger.debug("Process read error: %s", e)

        # Transform raw service data into GUI-friendly format
        self._stats = self._transform(raw)

    @staticmethod
    def _transform(raw):
        """Transform raw service data into the format expected by GUI pages."""
        stats = {}

        # === CPU ===
        cpu_raw = raw.get('cpu', {})
        cpu = {}
        cores = []
        for key, val in cpu_raw.items():
            if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
                # Per-core data
                core_info = {}
                core_info['load'] = val.get('load', 0) if isinstance(val, dict) else 0
                freq = val.get('freq', {})
                if isinstance(freq, dict):
                    core_info['freq'] = freq.get('cur', 0)
                    core_info['min_freq'] = freq.get('min', 0)
                    core_info['max_freq'] = freq.get('max', 0)
                else:
                    core_info['freq'] = freq
                core_info['governor'] = val.get('governor', 'N/A') if isinstance(val, dict) else 'N/A'
                core_info['online'] = val.get('online', True) if isinstance(val, dict) else True
                cores.append(core_info)
            elif key == 'total':
                total = val
                if isinstance(val, dict):
                    total = val.get('load', 0)
                cpu['total'] = total
        cpu['cores'] = cores
        cpu['number'] = len(cores)
        if 'total' not in cpu and cores:
            cpu['total'] = sum(c.get('load', 0) for c in cores) / len(cores)
        stats['cpu'] = cpu

        # === GPU ===
        gpu_raw = raw.get('gpu', {})
        if gpu_raw:
            gpu = dict(gpu_raw) if isinstance(gpu_raw, dict) else {}
            freq = gpu.get('freq', {})
            if isinstance(freq, dict):
                gpu['freq'] = freq.get('cur', 0)
                gpu['min_freq'] = freq.get('min', 0)
                gpu['max_freq'] = freq.get('max', 0)
            stats['gpu'] = gpu
        else:
            stats['gpu'] = {}

        # === NPU ===
        npu_raw = raw.get('npu', {})
        if npu_raw and isinstance(npu_raw, dict):
            npu = {}
            # cores: list of per-core load % (already produced by NPUService)
            npu_cores_raw = npu_raw.get('cores', [])
            if isinstance(npu_cores_raw, list):
                npu['cores'] = [{'load': v, 'online': True} for v in npu_cores_raw]
            elif isinstance(npu_cores_raw, dict):
                npu['cores'] = [{'load': npu_cores_raw.get(i, 0), 'online': True}
                                for i in sorted(npu_cores_raw.keys())]
            else:
                npu['cores'] = []
            npu['load'] = npu_raw.get('load', 0)
            npu['online'] = npu_raw.get('online', False)
            npu['active'] = npu_raw.get('active', False)
            npu['tops'] = npu_raw.get('tops', 0)
            npu['governor'] = npu_raw.get('governor', '')
            # freq: keep as Hz dict for GUI freq_gauge
            freq_raw = npu_raw.get('freq', {})
            if isinstance(freq_raw, dict):
                npu['freq'] = freq_raw      # {'cur': Hz, 'min': Hz, 'max': Hz}
            else:
                npu['freq'] = {}
            stats['npu'] = npu
        else:
            stats['npu'] = {}

        # === RGA ===
        rga_raw = raw.get('rga', {})
        if rga_raw and isinstance(rga_raw, dict):
            rga = {}
            rga['online'] = rga_raw.get('online', False)
            rga['active'] = rga_raw.get('active', False)
            rga['load'] = rga_raw.get('load', 0)
            rga['cores'] = rga_raw.get('cores', [])  # list of per-core %
            rga['version'] = rga_raw.get('version', '')
            # freq in Hz dict
            freq_raw = rga_raw.get('freq', {})
            rga['freq'] = freq_raw if isinstance(freq_raw, dict) else {}
            stats['rga'] = rga
        else:
            stats['rga'] = {}

        # === MPP ===
        mpp_raw = raw.get('mpp', {})
        if mpp_raw and isinstance(mpp_raw, dict):
            # Pass through the structured data from MPPService.get_status()
            stats['mpp'] = {
                'decoders': mpp_raw.get('decoders', {}),
                'encoders': mpp_raw.get('encoders', {}),
                'others': mpp_raw.get('others', {}),
                'any_active': mpp_raw.get('any_active', False),
            }
        else:
            stats['mpp'] = {}

        # === Memory ===
        mem_raw = raw.get('memory', {})
        if mem_raw:
            mem = {}
            mem['ram'] = {
                'total': mem_raw.get('total', 0),
                'used': mem_raw.get('used', 0),
                'free': mem_raw.get('free', 0),
                'available': mem_raw.get('available', 0),
                'buffers': mem_raw.get('buffers', 0),
                'cached': mem_raw.get('cached', 0),
            }
            mem['swap'] = {
                'total': mem_raw.get('swap_total', 0),
                'used': mem_raw.get('swap_used', 0),
                'free': mem_raw.get('swap_free', 0),
            }
            mem['cma'] = {
                'total': mem_raw.get('cma_total', 0),
                'used': mem_raw.get('cma_used', 0),
                'free': mem_raw.get('cma_free', 0),
            }
            mem['shmem'] = {'total': mem_raw.get('shmem', 0)}
            mem['storage'] = mem_raw.get('storage', [])
            stats['memory'] = mem
        else:
            stats['memory'] = {}

        # === Temperature ===
        temp_raw = raw.get('temperature', {})
        if temp_raw:
            temp = {}
            for name, val in temp_raw.items():
                if isinstance(val, dict):
                    # Flatten nested dicts like {'bigcore0': {'bigcore0': 52.692, 'online': True}}
                    inner_val = val.get(name, val)
                    if isinstance(inner_val, (int, float)):
                        temp[name] = inner_val * 1000  # Convert to millidegrees for GUI
                    else:
                        # Try to find a numeric value
                        for k, v in val.items():
                            if isinstance(v, (int, float)) and k != 'online':
                                temp[name] = v * 1000
                                break
                elif isinstance(val, (int, float)):
                    temp[name] = val * 1000  # Convert to millidegrees
            stats['temperature'] = temp
        else:
            stats['temperature'] = {}

        # === Fan ===
        fan_raw = raw.get('fan', {})
        if fan_raw:
            fan = {}
            if isinstance(fan_raw, dict):
                for name, val in fan_raw.items():
                    if isinstance(val, dict):
                        fan[name] = val
                    elif isinstance(val, (int, float)):
                        fan[name] = {'speed': val}
                    else:
                        fan[name] = val
            stats['fan'] = fan
        else:
            stats['fan'] = {}

        # === Power ===
        stats['power'] = raw.get('power') or {}

        # === Static data ===
        stats['uptime'] = raw.get('uptime', 0)
        stats['hardware'] = raw.get('hardware', {})
        stats['platform'] = raw.get('platform', {})
        stats['disk'] = {}
        stats['network'] = {}

        return stats

    def ok(self):
        """Collect stats and return True to continue the loop.

        Returns False on KeyboardInterrupt.
        """
        try:
            self._collect()
            import time
            time.sleep(self._interval)
            return self._running
        except KeyboardInterrupt:
            return False

    @property
    def stats(self):
        """Return the current stats dictionary."""
        return self._stats

    @property
    def cpu(self):
        return self._stats.get('cpu', {})

    @property
    def gpu(self):
        return self._stats.get('gpu', {})

    @property
    def npu(self):
        return self._stats.get('npu', {})

    @property
    def rga(self):
        return self._stats.get('rga', {})

    @property
    def mpp(self):
        return self._stats.get('mpp', {})

    @property
    def memory(self):
        return self._stats.get('memory', {})

    @property
    def temperature(self):
        return self._stats.get('temperature', {})

    @property
    def fan(self):
        return self._stats.get('fan', {})

    @property
    def power(self):
        return self._stats.get('power', {})

    @property
    def hardware(self):
        return self._stats.get('hardware', {})

    @property
    def platform(self):
        return self._stats.get('platform', {})

    @property
    def processes(self):
        return self._processes

    @property
    def interval(self):
        return self._interval

    def __enter__(self):
        self._init_services()
        self._collect()
        self._running = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._running = False
        return False
