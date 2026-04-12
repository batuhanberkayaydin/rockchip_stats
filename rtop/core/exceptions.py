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
