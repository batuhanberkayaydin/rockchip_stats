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
Hardware capability detection for Rockchip SoCs.

Auto-detects which accelerators and features are available by
checking for the existence of sysfs/debugfs paths.
"""

import os
import re
import glob
import logging

from .common import cat

logger = logging.getLogger(__name__)

# Known Rockchip SoC compatible strings
ROCKCHIP_SOCS = {
    'rk3588': {'name': 'RK3588', 'cpu_cores': 8, 'big_little': True, 'npu_cores': 3, 'npu_tops': 6.0},
    'rk3588s': {'name': 'RK3588S', 'cpu_cores': 8, 'big_little': True, 'npu_cores': 3, 'npu_tops': 6.0},
    'rk3576': {'name': 'RK3576', 'cpu_cores': 8, 'big_little': True, 'npu_cores': 3, 'npu_tops': 6.0},
    'rk3568': {'name': 'RK3568', 'cpu_cores': 4, 'big_little': False, 'npu_cores': 1, 'npu_tops': 1.0},
    'rk3566': {'name': 'RK3566', 'cpu_cores': 4, 'big_little': False, 'npu_cores': 1, 'npu_tops': 1.0},
    'rk3562': {'name': 'RK3562', 'cpu_cores': 4, 'big_little': False, 'npu_cores': 1, 'npu_tops': 1.0},
    'rk3399pro': {'name': 'RK3399Pro', 'cpu_cores': 6, 'big_little': True, 'npu_cores': 1, 'npu_tops': 3.0},
    'rk3399': {'name': 'RK3399', 'cpu_cores': 6, 'big_little': True, 'npu_cores': 0, 'npu_tops': 0},
    'rk3288': {'name': 'RK3288', 'cpu_cores': 4, 'big_little': False, 'npu_cores': 0, 'npu_tops': 0},
    'rk3308': {'name': 'RK3308', 'cpu_cores': 4, 'big_little': False, 'npu_cores': 0, 'npu_tops': 0},
    'rk3328': {'name': 'RK3328', 'cpu_cores': 4, 'big_little': False, 'npu_cores': 0, 'npu_tops': 0},
}

# Base paths for Rockchip hardware
DEVFREQ_PATH = "/sys/class/devfreq"
DEBUGFS_PATH = "/sys/kernel/debug"
MPP_PATH = "/proc/mpp_service"
RGA_DEVICE = "/dev/rga"
PLATFORM_DEVICES = "/sys/devices/platform"
PLATFORM_DRIVERS = "/sys/bus/platform/drivers"

# Driver directory names under /sys/bus/platform/drivers for RGA cores.
# rockchip-rga is the parent driver and is skipped in favour of per-core nodes.
RGA_DRIVER_NAMES = ('rga3_core0', 'rga3_core1', 'rga2', 'rga2e')

_MPP_CORE_INDEX = re.compile(r'^(.+?)(\d+)$')
_PLATFORM_SKIP = frozenset(('bind', 'unbind', 'uevent', 'drivers_autoprobe'))


def _find_devfreq_device(pattern):
    """Find a devfreq device by pattern in /sys/class/devfreq/."""
    if not os.path.isdir(DEVFREQ_PATH):
        return None
    for entry in sorted(os.listdir(DEVFREQ_PATH)):
        full_path = os.path.join(DEVFREQ_PATH, entry)
        if os.path.isdir(full_path) and pattern in entry.lower():
            return full_path
    return None


def _find_all_devfreq_devices(pattern):
    """Find all devfreq devices matching a pattern."""
    if not os.path.isdir(DEVFREQ_PATH):
        return []
    results = []
    for entry in sorted(os.listdir(DEVFREQ_PATH)):
        full_path = os.path.join(DEVFREQ_PATH, entry)
        if os.path.isdir(full_path) and pattern in entry.lower():
            results.append(full_path)
    return results


def detect_soc():
    """Detect the Rockchip SoC from device tree compatible string."""
    compatible_path = "/sys/firmware/devicetree/base/compatible"
    if not os.path.isfile(compatible_path):
        return None
    try:
        with open(compatible_path, 'r') as f:
            compatible = f.read().replace('\x00', ' ').strip().lower()
        for soc_id in ROCKCHIP_SOCS:
            if soc_id in compatible:
                return soc_id
    except (IOError, PermissionError):
        pass
    return None


def get_soc_info(soc_id=None):
    """Get information about the detected SoC."""
    if soc_id is None:
        soc_id = detect_soc()
    if soc_id and soc_id in ROCKCHIP_SOCS:
        return {'id': soc_id, **ROCKCHIP_SOCS[soc_id]}
    return {'id': soc_id or 'unknown', 'name': 'Unknown Rockchip'}


def has_gpu():
    return _find_devfreq_device('gpu') is not None


def get_gpu_path():
    return _find_devfreq_device('gpu')


def has_npu():
    if _find_devfreq_device('npu'):
        return True
    return os.path.isdir(os.path.join(DEBUGFS_PATH, 'rknpu'))


def get_npu_devfreq_path():
    """Get the first NPU devfreq path."""
    return _find_devfreq_device('npu')


def get_npu_devfreq_paths():
    """Get ALL NPU devfreq paths (some SoCs expose multiple)."""
    return _find_all_devfreq_devices('npu')


def get_npu_debug_path():
    """Get the debugfs path for NPU load (single combined file)."""
    npu_load = os.path.join(DEBUGFS_PATH, 'rknpu', 'load')
    if os.path.isfile(npu_load):
        return npu_load
    return None


def list_platform_devices_by_suffix(suffix, devices_root=None):
    """Return sorted platform device paths whose name ends with '.<suffix>'.

    Example: suffix 'jpegd' matches /sys/devices/platform/fdb90000.jpegd
    but not a hypothetical *.jpegd-extra node.
    """
    root = devices_root or PLATFORM_DEVICES
    if not suffix or not os.path.isdir(root):
        return []
    needle = '.' + suffix
    found = []
    try:
        for entry in os.listdir(root):
            if entry.endswith(needle):
                found.append(os.path.join(root, entry))
    except (IOError, PermissionError):
        return []
    return sorted(found)


def read_runtime_pm(dev_path):
    """Read world-accessible runtime PM counters for a platform device.

    Returns a dict with 'status', 'usage', 'active_time', or None if the
    power/runtime_status file is missing (device has no runtime PM).
    """
    if not dev_path:
        return None
    power = os.path.join(dev_path, 'power')
    status_path = os.path.join(power, 'runtime_status')
    if not os.path.isfile(status_path):
        return None
    result = {'status': None, 'usage': 0, 'active_time': 0}
    try:
        result['status'] = cat(status_path).strip()
    except (IOError, OSError, PermissionError):
        return None
    for key, name in (('usage', 'runtime_usage'), ('active_time', 'runtime_active_time')):
        try:
            raw = cat(os.path.join(power, name)).strip()
            result[key] = int(raw) if raw else 0
        except (IOError, OSError, PermissionError, ValueError):
            pass
    return result


def runtime_pm_busy(pm, prev_active_time=None):
    """True if runtime PM data shows the device is (or was recently) in use.

    Instantaneous 'active' / usage>0 catches a poll that lands during a
    burst. An increasing runtime_active_time catches short bursts between
    samples (typical for JPEG decode / RGA blit at camera frame rate).
    """
    if not pm:
        return False
    status = (pm.get('status') or '').strip().lower()
    if status == 'active' or int(pm.get('usage') or 0) > 0:
        return True
    active_time = int(pm.get('active_time') or 0)
    if prev_active_time is not None and active_time > prev_active_time:
        return True
    return False


def get_rga_platform_cores(drivers_root=None, devices_root=None):
    """Discover RGA cores from platform drivers (world-readable, no debugfs).

    Returns a list of {'name': driver_name, 'path': sysfs_path} dicts,
    ordered rga3_core0, rga3_core1, rga2, …
    """
    root = drivers_root or PLATFORM_DRIVERS
    cores = []
    for drv in RGA_DRIVER_NAMES:
        drv_path = os.path.join(root, drv)
        if not os.path.isdir(drv_path):
            continue
        try:
            entries = sorted(os.listdir(drv_path))
        except (IOError, PermissionError):
            continue
        for entry in entries:
            if entry in _PLATFORM_SKIP:
                continue
            full = os.path.join(drv_path, entry)
            if os.path.islink(full) or os.path.isdir(full):
                cores.append({'name': drv, 'path': os.path.realpath(full)})
    if cores:
        return cores
    # Fallback: devices whose OF name ends with .rga
    for path in list_platform_devices_by_suffix('rga', devices_root):
        cores.append({'name': os.path.basename(path), 'path': path})
    return cores


def get_mpp_platform_devices(core_name, devices_root=None):
    """Map an MPP procfs core name to platform device path(s).

    Indexed names such as jpege-core0 / rkvdec-core1 pick the Nth
    device whose OF name ends with .jpege-core / .rkvdec-core.
    Bare names such as jpegd match *.jpegd.
    """
    if not core_name:
        return []
    match = _MPP_CORE_INDEX.match(core_name)
    if match and match.group(1).endswith('-core'):
        suffix = match.group(1)
        index = int(match.group(2))
        devices = list_platform_devices_by_suffix(suffix, devices_root)
        if 0 <= index < len(devices):
            return [devices[index]]
        return []
    return list_platform_devices_by_suffix(core_name, devices_root)


def has_rga():
    """True if RGA hardware is present.

    /sys/kernel/debug/rkrga is typically 0700, so isdir() fails for
    unprivileged users even when /dev/rga exists. Prefer the device node
    and platform cores, then fall back to debugfs.
    """
    if os.path.exists(RGA_DEVICE):
        return True
    if get_rga_platform_cores():
        return True
    return os.path.isdir(os.path.join(DEBUGFS_PATH, 'rkrga'))


def get_rga_debug_path():
    """Get the debugfs path for RGA load (root-only on most kernels)."""
    rga_load = os.path.join(DEBUGFS_PATH, 'rkrga', 'load')
    if os.path.isfile(rga_load):
        return rga_load
    return None


def get_rga_devfreq_path():
    """Get devfreq path for RGA if available (some kernels expose it)."""
    # RGA may be exposed under devfreq with various names
    for pattern in ('rga', 'rkrga'):
        path = _find_devfreq_device(pattern)
        if path:
            return path
    return None


def has_mpp():
    return os.path.isdir(MPP_PATH)


def get_mpp_path():
    if has_mpp():
        return MPP_PATH
    return None


def get_mpp_cores():
    """Discover available MPP video cores dynamically from /proc/mpp_service/."""
    cores = {}
    if not has_mpp():
        return cores
    # All known MPP codec core name prefixes (ordered for display)
    known_cores = [
        'rkvdec-core0', 'rkvdec-core1',     # H.264/H.265 decoder
        'rkvenc-core0', 'rkvenc-core1',     # H.264/H.265 encoder
        'jpege-core0', 'jpege-core1',       # JPEG encoder
        'jpege-core2', 'jpege-core3',
        'jpegd',                            # JPEG decoder
        'av1d',                             # AV1 decoder
        'vdpu',                             # Video decoder (legacy)
        'vepu',                             # Video encoder (legacy)
        'iep',                              # Image enhancement
    ]
    for core_name in known_cores:
        core_path = os.path.join(MPP_PATH, core_name)
        if os.path.isdir(core_path):
            cores[core_name] = core_path
    # Also scan for any unknown cores present on the filesystem
    try:
        for entry in sorted(os.listdir(MPP_PATH)):
            core_path = os.path.join(MPP_PATH, entry)
            if os.path.isdir(core_path) and entry not in cores and entry != 'sessions-summary':
                cores[entry] = core_path
    except (IOError, PermissionError):
        pass
    return cores


def is_rockchip():
    return detect_soc() is not None


def get_board_model():
    """Get the board model from device tree."""
    model_path = "/sys/firmware/devicetree/base/model"
    if os.path.isfile(model_path):
        try:
            with open(model_path, 'rb') as f:
                return f.read().replace(b'\x00', b'').decode('utf-8', errors='replace').strip()
        except (IOError, PermissionError):
            pass
    return "Unknown"


def get_board_serial():
    """Get the board serial number from device tree."""
    serial_path = "/sys/firmware/devicetree/base/serial-number"
    if os.path.isfile(serial_path):
        try:
            with open(serial_path, 'rb') as f:
                return f.read().replace(b'\x00', b'').decode('utf-8', errors='replace').strip()
        except (IOError, PermissionError):
            pass
    return "Unknown"
