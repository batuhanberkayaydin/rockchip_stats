#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Minimal setup.py for backward compatibility and custom install commands.
Main configuration is in pyproject.toml (PEP 517/518/621 compliant).
"""

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools.command.build_py import build_py
import os
import sys
import shutil
import subprocess as sp_mod
import logging

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger()


def is_virtualenv():
    has_real_prefix = hasattr(sys, 'real_prefix')
    has_base_prefix = (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    return bool(has_real_prefix or has_base_prefix)


def is_docker():
    if os.path.exists('/.dockerenv'):
        return True
    if os.path.exists('/run/.containerenv'):
        return True
    if os.environ.get('container'):
        return True
    path = '/proc/self/cgroup'
    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                if 'docker' in line or 'buildkit' in line or 'containerd' in line:
                    return True
    mountinfo = '/proc/self/mountinfo'
    if os.path.isfile(mountinfo):
        with open(mountinfo) as f:
            for line in f:
                if '/docker/' in line or '/buildkit/' in line or '/containerd/' in line:
                    return True
    if not shutil.which('systemctl'):
        return True
    return False


def is_superuser():
    return os.getuid() == 0


def _systemctl(*args):
    """Run systemctl if available, otherwise log and skip."""
    if shutil.which('systemctl'):
        return sp_mod.call(['systemctl'] + list(args))
    log.warning("systemctl not found, skipping: systemctl %s", ' '.join(args))
    return 1


def _run_service_install(source_folder):
    """Install rtop system service and config files."""
    service_src = os.path.join(source_folder, 'services', 'rtop.service')
    service_dst = '/etc/systemd/system/rtop.service'
    env_src = os.path.join(source_folder, 'scripts', 'rtop_env.sh')
    env_dst = '/etc/profile.d/rtop_env.sh'
    pipe_path = '/run/rtop.sock'

    # Uninstall previous service
    if os.path.isfile(service_dst) or os.path.islink(service_dst):
        _systemctl('stop', 'rtop.service')
        _systemctl('disable', 'rtop.service')
        os.remove(service_dst)
        _systemctl('daemon-reload')
    if os.path.isdir(pipe_path):
        shutil.rmtree(pipe_path)
    elif os.path.exists(pipe_path):
        os.remove(pipe_path)
    if os.path.isfile(env_dst):
        os.remove(env_dst)

    # Install service file
    if os.path.isfile(service_src):
        shutil.copy2(service_src, service_dst)
        log.info("Installed %s -> %s", service_src, service_dst)
        _systemctl('daemon-reload')
        _systemctl('enable', 'rtop.service')
        _systemctl('start', 'rtop.service')

    # Install env script
    if os.path.isfile(env_src):
        shutil.copy2(env_src, env_dst)
        log.info("Installed %s -> %s", env_src, env_dst)

    # Set permissions
    user = os.environ.get('SUDO_USER', '') or 'root'
    sp_mod.call(['groupadd', 'rtop'])
    sp_mod.call(['usermod', '-a', '-G', 'rtop', user])


class RTOPBuildPy(build_py):
    """Extend build_py to install system service during PEP 517 builds."""

    def run(self):
        build_py.run(self)
        if is_superuser() and not is_docker():
            folder = os.path.dirname(os.path.realpath(__file__))
            log.info("Installing rtop system service...")
            _run_service_install(folder)


def pypi_installer(installer, obj, copy):
    """Main installation function for rtop services."""
    try:
        from rtop.service import status_service, remove_service_pipe, uninstall_service, set_service_permission, install_service
        from rtop.terminal_colors import bcolors
    except ImportError:
        installer.run(obj)
        return

    log.info("Install status:")
    log.info(f" - [{'X' if is_superuser() else ' '}] super_user")
    log.info(f" - [{'X' if is_virtualenv() else ' '}] virtualenv")
    log.info(f" - [{'X' if is_docker() else ' '}] docker")

    if not is_virtualenv() and not is_docker():
        if is_superuser():
            uninstall_service()
            remove_service_pipe()
        else:
            log.info("----------------------------------------")
            log.info("Install on your host using superuser permission, like:")
            log.info(bcolors.bold("sudo pip3 install -U rockchip-stats"))
            sys.exit(1)
    elif is_docker():
        log.info("Skip uninstall in docker")
    else:
        if not is_superuser() and not status_service():
            log.info("----------------------------------------")
            log.info("Please, before install in your virtual environment, install rockchip-stats on your host with superuser permission:")
            log.info(bcolors.bold("sudo pip3 install -U rockchip-stats"))
            sys.exit(1)

    installer.run(obj)

    if not is_virtualenv() and not is_docker() and is_superuser():
        folder, _ = os.path.split(os.path.realpath(__file__))
        set_service_permission()
        install_service(folder, copy=copy)
    else:
        log.info("Skip install service")


class RTOPInstallCommand(install):
    """Custom installation command for production install."""
    def run(self):
        pypi_installer(install, self, True)


class RTOPDevelopCommand(develop):
    """Custom installation command for development mode."""
    def run(self):
        pypi_installer(develop, self, False)


if __name__ == '__main__':
    setup(
        cmdclass={
            'build_py': RTOPBuildPy,
            'develop': RTOPDevelopCommand,
            'install': RTOPInstallCommand,
        },
        data_files=[('rockchip_stats', ['services/rtop.service', 'scripts/rtop_env.sh'])],
    )
