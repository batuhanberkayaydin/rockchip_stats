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
MPP (Media Process Platform) monitoring for Rockchip SoCs.

Monitors video encoder/decoder core sessions and task counts via
/proc/mpp_service/<core_name>/.

MPP cores detected on RK3588:
  rkvdec-core0/1   – H.264/H.265 decoder
  rkvenc-core0/1   – H.264/H.265/H.264 encoder
  jpege-core0..3   – JPEG encoder
  jpegd            – JPEG decoder
  av1d             – AV1 decoder
  iep              – Image Enhancement Processor
  vdpu / vepu      – legacy VPU (older SoCs)

Active/idle is determined by task_count > 0 and/or sessions-info showing
at least one active entry.
"""

import os
import re
import logging
from .common import cat
from .hw_detect import get_mpp_path, get_mpp_cores

logger = logging.getLogger(__name__)

# task_count file contains just a number (e.g. "3")
TASK_COUNT_RE = re.compile(r'(\d+)')

# Codec type from core name
DECODER_PREFIXES = ('rkvdec', 'jpegd', 'av1d', 'vdpu')
ENCODER_PREFIXES = ('rkvenc', 'jpege', 'vepu')
OTHER_PREFIXES   = ('iep',)

# Human-readable codec labels
CODEC_LABELS = {
    'rkvdec': 'RKVDEC',   # H.264/H.265 decode
    'rkvenc': 'RKVENC',   # H.264/H.265 encode
    'jpege':  'JPEGE',    # JPEG encode
    'jpegd':  'JPEGD',    # JPEG decode
    'av1d':   'AV1D',     # AV1 decode
    'vdpu':   'VDPU',     # Legacy decode
    'vepu':   'VEPU',     # Legacy encode
    'iep':    'IEP',      # Image Enhancement
}


def _codec_type(core_name):
    """Return 'decoder', 'encoder', or 'other' for a core name."""
    lo = core_name.lower()
    for p in DECODER_PREFIXES:
        if lo.startswith(p):
            return 'decoder'
    for p in ENCODER_PREFIXES:
        if lo.startswith(p):
            return 'encoder'
    return 'other'


def _codec_label(core_name):
    lo = core_name.lower()
    for prefix, label in CODEC_LABELS.items():
        if lo.startswith(prefix):
            return label
    return core_name.upper()


def _read_task_count(core_path):
    """Read task_count as integer; return 0 on failure."""
    p = os.path.join(core_path, 'task_count')
    if not os.path.isfile(p):
        return None   # file absent → no info
    try:
        raw = cat(p).strip()
        m = TASK_COUNT_RE.search(raw)
        return int(m.group(1)) if m else 0
    except (IOError, PermissionError):
        return -1     # permission denied


def _has_active_sessions(core_path):
    """Return True if sessions-info suggests at least one active session."""
    p = os.path.join(core_path, 'sessions-info')
    if not os.path.isfile(p):
        return False
    try:
        with open(p, 'r') as f:
            content = f.read(4096)
        # An active session has numeric data lines beyond the header
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        return len(lines) > 1
    except (IOError, PermissionError):
        return False


class MPPService(object):
    """Service for collecting MPP video core statistics."""

    def __init__(self):
        self._mpp_path = get_mpp_path()
        self._cores = get_mpp_cores()
        if self._mpp_path:
            logger.info("MPP path: %s  cores: %s", self._mpp_path, list(self._cores.keys()))
        else:
            logger.info("No MPP service found")

    @property
    def available(self):
        return self._mpp_path is not None

    @property
    def cores(self):
        return self._cores

    def get_status(self):
        """Get current MPP status.

        Returns a dict with:
          'decoders'  – ordered dict of decoder core info
          'encoders'  – ordered dict of encoder core info
          'others'    – ordered dict of other core info
          'any_active'– bool, True if at least one core is active
        Each core entry:
          {
            'label':      str   human-readable name
            'task_count': int   current task count (or -1=no permission, None=no file)
            'active':     bool  task_count > 0 or sessions active
            'online':     bool  core present in sysfs
          }
        """
        status = {'decoders': {}, 'encoders': {}, 'others': {}, 'any_active': False}

        if not self._mpp_path:
            return status

        for core_name, core_path in self._cores.items():
            tc = _read_task_count(core_path)
            active = (tc is not None and tc > 0) or _has_active_sessions(core_path)
            if active:
                status['any_active'] = True

            info = {
                'label':       _codec_label(core_name),
                'task_count':  tc,
                'active':      active,
                'online':      True,
            }
            ctype = _codec_type(core_name)
            if ctype == 'decoder':
                status['decoders'][core_name] = info
            elif ctype == 'encoder':
                status['encoders'][core_name] = info
            else:
                status['others'][core_name] = info

        return status
