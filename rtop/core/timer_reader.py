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
Timer-based data collection reader.

Provides periodic data collection at a configured interval.
"""

import time
import logging
from threading import Thread, Event

logger = logging.getLogger(__name__)


class TimerReader(Thread):
    """Timer-based periodic reader that calls a callback at regular intervals."""

    def __init__(self, callback, interval=1.0):
        super(TimerReader, self).__init__()
        self._callback = callback
        self._interval = interval
        self._stop_event = Event()
        self.daemon = True

    def run(self):
        """Main loop that periodically calls the callback."""
        while not self._stop_event.is_set():
            try:
                self._callback()
            except Exception as e:
                logger.error("Timer callback error: %s", e)
            self._stop_event.wait(self._interval)

    def stop(self):
        """Stop the timer reader."""
        self._stop_event.set()

    @property
    def interval(self):
        """Return the current interval."""
        return self._interval

    @interval.setter
    def interval(self, value):
        """Set the interval."""
        self._interval = float(value)
