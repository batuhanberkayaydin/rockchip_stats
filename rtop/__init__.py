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

from .core.exceptions import RtopException
from .core.gpu import GPU
from .core.npu import NPUService as NPU
from .core.memory import Memory
from .core.fan import Fan
from .rtop import rtop

__author__ = "Batuhan Berkay Aydın"
__email__ = "batuhanberkayaydin@gmail.com"
__copyright__ = "(c) 2026, Batuhan Berkay Aydın"
__cr__ = "(c) 2026, BBA"
# Version package
__version__ = "0.1.0"
