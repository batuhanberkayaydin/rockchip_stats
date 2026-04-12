# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

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
