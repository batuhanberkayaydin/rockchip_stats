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
rtop CLI entry point - curses-based terminal system monitor for Rockchip SoCs.
"""

import os
import sys
import argparse
import logging
import curses

from .core.exceptions import RtopException
from .core.common import get_var
from .terminal_colors import bcolors

logger = logging.getLogger(__name__)

LOOP_SECONDS = 5
RTOP_LOG_NAME = 'rtop-error.log'


def _is_virtualenv():
    has_real_prefix = hasattr(sys, 'real_prefix')
    has_base_prefix = hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    return bool(has_real_prefix or has_base_prefix)


def _is_docker():
    if os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv'):
        return True
    if os.environ.get('container'):
        return True
    cgroup = '/proc/self/cgroup'
    if os.path.isfile(cgroup):
        with open(cgroup) as f:
            for line in f:
                if any(tok in line for tok in ('/docker/', '/buildkit/', '/containerd/')):
                    return True
    return False


def _auto_install_if_needed():
    """Ensure the rtop system service is installed and the current shell can
    reach it. Returns True to proceed with the GUI, False if the caller should
    exit after printing guidance."""
    service_path = '/etc/systemd/system/rtop.service'
    socket_path = '/run/rtop.sock'

    service_installed = os.path.isfile(service_path)

    if os.getuid() == 0 and not _is_docker() and not _is_virtualenv():
        # Running as root — install or repair the service automatically.
        try:
            from .service import install_service, set_service_permission
            if not service_installed:
                logger.info("rtop service not found, installing...")
                set_service_permission()
                install_service()
            elif not os.path.exists(socket_path):
                import subprocess
                subprocess.call(['systemctl', 'start', 'rtop.service'])
        except Exception as e:
            logger.warning("Failed to auto-install service: %s", e)
        return True

    if os.getuid() != 0:
        # Non-root: catch the two common post-install problems and guide the
        # user instead of letting the GUI render empty NPU/RGA panels.
        if not os.path.exists(socket_path):
            print(bcolors.yellow("Warning:") + " rtop service is not running.")
            print("Install with: " + bcolors.bold("sudo pip3 install -U rockchip-stats"))
            print("Or start manually: " + bcolors.bold("sudo systemctl start rtop"))
            return False
        # Socket is 660 root:rtop — the user needs the rtop gid in their
        # active credentials. A shell that predates the install will not have
        # it until a reboot (same UX as jetson_stats).
        try:
            import grp
            rtop_gid = grp.getgrnam('rtop').gr_gid
            if rtop_gid not in os.getgroups():
                print(bcolors.yellow("Warning:") + " rtop was just installed.")
                print("Please " + bcolors.bold("reboot") + " your system to finish the setup.")
                return False
        except (KeyError, OSError):
            pass
    return True


def main():
    """Main entry point for the rtop command."""
    parser = argparse.ArgumentParser(
        description='rtop - System monitor for Rockchip SoC devices'
    )
    parser.add_argument('--force', action='store_true', help='Force start as server')
    parser.add_argument('--no-service', action='store_true', help='Run without service')
    parser.add_argument('--interval', type=float, default=1.0, help='Update interval in seconds')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')

    # Check if running as service
    is_service = os.environ.get('RTOP_SERVICE', False) or args.force

    if is_service:
        # Start as background service
        logger.info("Starting rtop service...")
        try:
            from .service import RtopServer
            server = RtopServer(interval=args.interval)
            server.serve()
        except Exception as e:
            logger.error("Service error: %s", e)
            sys.exit(1)
    else:
        # Start as interactive TUI
        if not args.no_service:
            if not _auto_install_if_needed():
                sys.exit(0)

        try:
            from .gui import run_rtop
            run_rtop(interval=args.interval)
        except Exception as e:
            logger.error("GUI error: %s", e)
            print(f"{bcolors.red('Error:')} {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()
