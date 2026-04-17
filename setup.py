#!/usr/bin/env python3
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
setup.py exists only so that `pip install` from an sdist can run our custom
install command and auto-install the systemd service. All package metadata
lives in pyproject.toml (PEP 621).
"""

from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
import os
import sys
import shutil
import subprocess as sp_mod
import logging

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger()


def _is_virtualenv():
    has_real_prefix = hasattr(sys, 'real_prefix')
    has_base_prefix = hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    return bool(has_real_prefix or has_base_prefix)


def _is_docker():
    # Only trust unambiguous signals. /proc/self/mountinfo is NOT reliable on a
    # Docker host (it sees every container's overlay mount), so we avoid it.
    if os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv'):
        return True
    if os.environ.get('container'):
        return True
    # cgroup of THIS process — the host's own cgroup won't contain 'docker'
    # unless the process is literally inside a container.
    path = '/proc/self/cgroup'
    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                if any(tok in line for tok in ('/docker/', '/buildkit/', '/containerd/')):
                    return True
    return False


def _is_superuser():
    return os.getuid() == 0


def _systemctl(*args):
    if shutil.which('systemctl'):
        return sp_mod.call(['systemctl'] + list(args))
    return 1


def _install_service(source_folder):
    """Install the rtop systemd unit, env script, group, and start the service."""
    service_src = os.path.join(source_folder, 'services', 'rtop.service')
    service_dst = '/etc/systemd/system/rtop.service'
    env_src = os.path.join(source_folder, 'scripts', 'rtop_env.sh')
    env_dst = '/etc/profile.d/rtop_env.sh'
    pipe_path = '/run/rtop.sock'

    # Stop / remove any previous install
    if os.path.isfile(service_dst) or os.path.islink(service_dst):
        _systemctl('stop', 'rtop.service')
        _systemctl('disable', 'rtop.service')
        try:
            os.remove(service_dst)
        except OSError:
            pass
        _systemctl('daemon-reload')
    if os.path.exists(pipe_path):
        try:
            if os.path.isdir(pipe_path):
                shutil.rmtree(pipe_path)
            else:
                os.remove(pipe_path)
        except OSError:
            pass
    if os.path.isfile(env_dst):
        try:
            os.remove(env_dst)
        except OSError:
            pass

    # Group first, so the socket can be chgrp'd when the service starts
    sp_mod.call(['groupadd', '-f', 'rtop'])
    user = os.environ.get('SUDO_USER', '') or 'root'
    sp_mod.call(['usermod', '-a', '-G', 'rtop', user])

    if os.path.isfile(service_src):
        shutil.copy2(service_src, service_dst)
        log.info("Installed %s -> %s", service_src, service_dst)
        _systemctl('daemon-reload')
        _systemctl('enable', 'rtop.service')
        _systemctl('start', 'rtop.service')
    else:
        log.warning("rtop.service source not found at %s", service_src)

    if os.path.isfile(env_src):
        shutil.copy2(env_src, env_dst)
        log.info("Installed %s -> %s", env_src, env_dst)


def _maybe_install_service():
    """Only run service install on a real host, as root, outside containers."""
    if _is_virtualenv() or _is_docker() or not _is_superuser():
        log.info("Skip rtop service install (virtualenv/docker/non-root)")
        return
    folder = os.path.dirname(os.path.realpath(__file__))
    log.info("Installing rtop systemd service...")
    _install_service(folder)


class RTOPInstall(install):
    def run(self):
        install.run(self)
        _maybe_install_service()


class RTOPDevelop(develop):
    def run(self):
        develop.run(self)
        _maybe_install_service()


# Read version from rtop/__init__.py without importing it.
def _read_version():
    import re
    here = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(here, 'rtop', '__init__.py')) as f:
        m = re.search(r"""^__version__\s*=\s*["'](.+?)["']""", f.read(), re.M)
        return m.group(1) if m else '0.0.0'


def _read_long_description():
    here = os.path.dirname(os.path.realpath(__file__))
    readme = os.path.join(here, 'README.md')
    if os.path.isfile(readme):
        with open(readme, encoding='utf-8') as f:
            return f.read()
    return ''


setup(
    name='rockchip-stats',
    version=_read_version(),
    description='Interactive system-monitor and process viewer for Rockchip SoC devices [RK3588, RK3588S, RK3568, RK3566, RK3399]',
    long_description=_read_long_description(),
    long_description_content_type='text/markdown',
    author='Batuhan Berkay Aydın',
    author_email='batuhanberkayaydin@gmail.com',
    url='https://github.com/batuhanberkayaydin/rockchip_stats',
    license='AGPL-3.0-or-later',
    python_requires='>=3.9',
    packages=['rtop', 'rtop.core', 'rtop.gui', 'rtop.gui.lib'],
    include_package_data=True,
    install_requires=['distro'],
    entry_points={
        'console_scripts': [
            'rtop = rtop.__main__:main',
            'rockchip_release = rtop.rockchip_release:main',
        ],
    },
    data_files=[('share/rockchip_stats', ['services/rtop.service', 'scripts/rtop_env.sh'])],
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: System :: Monitoring',
    ],
    cmdclass={
        'install': RTOPInstall,
        'develop': RTOPDevelop,
    },
)
