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
Command execution wrapper for running system commands safely.
"""

import subprocess as sp
import logging

logger = logging.getLogger(__name__)

COMMAND_TIMEOUT = 4.0


class Command(object):
    """Wrapper around subprocess for executing system commands."""

    def __init__(self, command, timeout=COMMAND_TIMEOUT):
        self._command = command
        self._timeout = timeout

    def run(self):
        """Run the command and return stdout, stderr, returncode."""
        try:
            proc = sp.Popen(
                self._command,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                shell=isinstance(self._command, str)
            )
            stdout, stderr = proc.communicate(timeout=self._timeout)
            return stdout.decode('utf-8').strip(), stderr.decode('utf-8').strip(), proc.returncode
        except sp.TimeoutExpired:
            proc.kill()
            logger.warning("Command timed out: %s", self._command)
            return "", "Timeout", -1
        except Exception as e:
            logger.error("Command failed: %s - %s", self._command, e)
            return "", str(e), -1

    @staticmethod
    def run_command(command, timeout=COMMAND_TIMEOUT):
        """Static helper to run a command."""
        cmd = Command(command, timeout)
        return cmd.run()
