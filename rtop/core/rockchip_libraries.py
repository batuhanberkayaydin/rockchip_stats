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
Detect userspace libraries commonly shipped on Rockchip boards.

Returned keys (matching jtop's ``libraries`` convention, value = detected
version string or empty when missing):

    RKNN        – librknnrt.so (NPU runtime, RKNN Toolkit Lite)
    RGA         – librga.so    (2D/3D RGA accelerator wrapper)
    MPP         – librockchip_mpp.so (video enc/dec multimedia plugin)
    RKLLM       – librkllmrt.so (RKNN LLM runtime, 3588-only so far)
    VPU         – librockchip_vpu.so (legacy VPU API)
    GStreamer   – gst-inspect presence + rockchip plugins detected
    OpenCV      – python `cv2` import version

On boards where a library is absent the corresponding value is empty so the
GUI can highlight it as MISSING.
"""

import os
import re
import logging
import subprocess

logger = logging.getLogger(__name__)

# Common /usr/lib paths to probe, in order of preference. We include both the
# multi-arch libdir (Debian/Ubuntu) and the flat /usr/lib layout (Buildroot,
# RK vendor BSPs).
_LIB_DIRS = (
    '/usr/lib/aarch64-linux-gnu',
    '/usr/lib',
    '/usr/local/lib',
    '/usr/lib/arm-linux-gnueabihf',
)

# Regex that matches most Rockchip runtime version banners:
#   "librknnrt version: 1.6.0 (commit@date)"
#   "librga version 2.1.0"
#   "rknn_api version: 1.4.0"
_VERSION_RE = re.compile(
    rb'(?:version[:\s]+)?v?(\d+\.\d+(?:\.\d+)?(?:[.\-][A-Za-z0-9]+)*)',
    re.IGNORECASE,
)


def _first_existing(filenames):
    """Return the first /usr/... path whose candidate file exists."""
    for d in _LIB_DIRS:
        for fname in filenames:
            p = os.path.join(d, fname)
            if os.path.isfile(p) or os.path.islink(p):
                return p
    return None


def _extract_version_blob(path, hint):
    """Grep a shared-object for an embedded ``<hint> version: X.Y.Z`` banner.

    We require the literal word ``version`` after the hint so we don't pick
    up adjacent soname numbers. mmap lets us scan multi-megabyte .rodata
    sections without slurping the whole library into memory.
    """
    import mmap
    pattern = re.compile(
        hint.encode() + rb'\s+version[:\s]+v?(\d+\.\d+(?:\.\d+)?(?:[.\-][A-Za-z0-9]+)*)',
        re.IGNORECASE,
    )
    try:
        with open(path, 'rb') as f:
            size = os.fstat(f.fileno()).st_size
            if size == 0:
                return ''
            with mmap.mmap(f.fileno(), length=size, prot=mmap.PROT_READ) as mm:
                m = pattern.search(mm)
                return m.group(1).decode(errors='replace') if m else ''
    except (IOError, OSError, ValueError):
        return ''


def _pkgconfig_version(pc_file):
    """Read a ``Version: x.y.z`` line from a .pc file (or empty)."""
    try:
        with open(pc_file, 'r') as f:
            for line in f:
                if line.lower().startswith('version:'):
                    return line.split(':', 1)[1].strip()
    except (IOError, OSError):
        pass
    return ''


def _soname_version(so_path):
    """Resolve ``libfoo.so`` → ``libfoo.so.2.1.0`` and return ``2.1.0``.

    A bare single-digit SOVERSION (``0`` / ``1``) is just the ABI slot number
    and carries no meaningful release info, so we return '' to allow the caller
    to fall back to 'detected'.
    """
    try:
        real = os.path.realpath(so_path)
    except OSError:
        return ''
    base = os.path.basename(real)
    parts = base.split('.so.')
    if len(parts) >= 2:
        ver = parts[1]
        # Single-component integer (e.g. "0", "1") = ABI slot, not a real version
        if re.fullmatch(r'\d', ver):
            return ''
        return ver
    return ''


def _detect_rknn():
    p = _first_existing(['librknnrt.so', 'librknn_api.so'])
    if not p:
        return ''
    v = _extract_version_blob(p, 'librknnrt')
    if not v:
        v = _extract_version_blob(p, 'rknn_api')
    return v or _soname_version(p) or 'detected'


def _detect_rga():
    # Prefer pkg-config, it's unambiguous
    pc = _first_existing(['pkgconfig/librga.pc'])
    if pc:
        v = _pkgconfig_version(pc)
        if v:
            return v
    p = _first_existing(['librga.so', 'librga.so.2'])
    if not p:
        return ''
    return _soname_version(p) or _extract_version_blob(p, 'librga') or 'detected'


def _detect_mpp():
    p = _first_existing(['librockchip_mpp.so', 'librockchip_mpp.so.1',
                         'librockchip_mpp.so.0'])
    if not p:
        return ''
    return _soname_version(p) or _extract_version_blob(p, 'mpp_version') or 'detected'


def _detect_vpu():
    p = _first_existing(['librockchip_vpu.so', 'librockchip_vpu.so.1',
                         'librockchip_vpu.so.0'])
    if not p:
        return ''
    return _soname_version(p) or 'detected'


def _detect_rkllm():
    """RKNN LLM runtime (ships separately; common on RK3588/3576 vendor BSPs)."""
    p = _first_existing(['librkllmrt.so', 'librkllm_api.so'])
    if not p:
        return ''
    return _extract_version_blob(p, 'rkllmrt') or _soname_version(p) or 'detected'


def _detect_gstreamer():
    """Check if gst-inspect is installed and if any rockchip plugin is present."""
    try:
        result = subprocess.run(
            ['gst-inspect-1.0', '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ''
    if result.returncode != 0:
        return ''
    first = result.stdout.decode(errors='replace').splitlines()
    version = first[0].split()[-1] if first else 'detected'

    # Detect common rockchip plugins.
    plugins = []
    for pat in ('mpp', 'rockchip', 'rga'):
        try:
            sub = subprocess.run(
                ['gst-inspect-1.0', pat],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            if sub.returncode == 0 and sub.stdout.strip():
                plugins.append(pat)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    if plugins:
        version += ' [' + ','.join(plugins) + ']'
    return version


def _detect_opencv():
    try:
        import cv2  # noqa: F401
        return getattr(cv2, '__version__', 'detected')
    except Exception:
        return ''


def get_libraries():
    """Return an ordered dict of detected Rockchip-related libraries."""
    libs = {
        'RKNN': _detect_rknn(),
        'RGA': _detect_rga(),
        'MPP': _detect_mpp(),
        'RKLLM': _detect_rkllm(),
        'VPU': _detect_vpu(),
        'GStreamer': _detect_gstreamer(),
        'OpenCV': _detect_opencv(),
    }
    return libs


# ── Local network interfaces (hostname + IP table) ───────────────────────────

def get_local_interfaces():
    """Return {'hostname': str, 'interfaces': {iface: ip}}."""
    import socket
    hostname = socket.gethostname()
    ifaces = {}
    try:
        # psutil is the cleanest path; fall back to /proc if it's missing.
        import psutil
        for name, addrs in psutil.net_if_addrs().items():
            if name == 'lo':
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ifaces[name] = addr.address
                    break
    except ImportError:
        # Minimal fallback: shell out to `ip -4 -o addr`.
        try:
            result = subprocess.run(
                ['ip', '-4', '-o', 'addr'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=2,
            )
            for line in result.stdout.decode(errors='replace').splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[1] != 'lo' and parts[2] == 'inet':
                    ifaces[parts[1]] = parts[3].split('/')[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return {'hostname': hostname, 'interfaces': ifaces}
