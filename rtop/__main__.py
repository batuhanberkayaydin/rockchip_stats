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
    if os.path.exists('/.dockerenv'):
        return True
    cgroup = '/proc/self/cgroup'
    if os.path.isfile(cgroup):
        with open(cgroup) as f:
            for line in f:
                if 'docker' in line or 'buildkit' in line:
                    return True
    return False


def _auto_install_if_needed():
    """Ensure the rtop system service is installed and running."""
    service_path = '/etc/systemd/system/rtop.service'
    socket_path = '/run/rtop.sock'

    # Service already running
    if os.path.exists(socket_path):
        return

    if os.getuid() == 0 and not _is_docker() and not _is_virtualenv():
        # Running as root — install service automatically
        if not os.path.isfile(service_path):
            logger.info("rtop service not found, installing...")
            try:
                from .service import install_service, set_service_permission
                folder = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
                set_service_permission()
                install_service(folder, copy=True)
            except Exception as e:
                logger.warning("Failed to auto-install service: %s", e)
        else:
            try:
                import subprocess
                subprocess.call(['systemctl', 'start', 'rtop.service'])
            except Exception:
                pass
    elif os.getuid() != 0:
        print(bcolors.yellow("Warning:") + " rtop service is not running.")
        print("Start it with: " + bcolors.bold("sudo systemctl start rtop"))
        print("Or install with: " + bcolors.bold("sudo pip3 install -U rockchip-stats"))


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
            _auto_install_if_needed()

        try:
            from .gui import run_rtop
            run_rtop(interval=args.interval)
        except Exception as e:
            logger.error("GUI error: %s", e)
            print(f"{bcolors.red('Error:')} {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()
