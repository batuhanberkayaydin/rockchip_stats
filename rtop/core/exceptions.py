# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Custom exceptions for rtop.
"""


class RtopException(Exception):
    """Base exception for all rtop errors."""
    pass


class ServiceNotRunning(RtopException):
    """Raised when the rtop service is not running."""
    pass


class HardwareNotFound(RtopException):
    """Raised when no Rockchip hardware is detected."""
    pass


class FanControlError(RtopException):
    """Raised when fan control fails."""
    pass


class PermissionDenied(RtopException):
    """Raised when access to a sysfs/debugfs path is denied."""
    pass
