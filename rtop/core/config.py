# -*- coding: UTF-8 -*-
# This file is part of the rockchip_stats package.

"""
Configuration management for rtop.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

# Default configuration paths
CONFIG_DIR = os.path.expanduser("~/.config/rtop")
CONFIG_FILE = os.path.join(CONFIG_DIR, "rtop.conf")

DEFAULT_CONFIG = {
    "interval": 1.0,
    "fan_mode": "auto",
    "color_scheme": "default",
}


class Config(object):
    """Configuration manager for rtop."""

    def __init__(self, config_file=None):
        self._config_file = config_file or CONFIG_FILE
        self._config = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        """Load configuration from file."""
        if os.path.isfile(self._config_file):
            try:
                with open(self._config_file, 'r') as f:
                    loaded = json.load(f)
                    self._config.update(loaded)
                logger.info("Loaded config from %s", self._config_file)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load config: %s", e)

    def _save(self):
        """Save configuration to file."""
        try:
            os.makedirs(os.path.dirname(self._config_file), exist_ok=True)
            with open(self._config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info("Saved config to %s", self._config_file)
        except IOError as e:
            logger.warning("Failed to save config: %s", e)

    def get(self, key, default=None):
        """Get a configuration value."""
        return self._config.get(key, default)

    def set(self, key, value):
        """Set a configuration value and save."""
        self._config[key] = value
        self._save()

    @property
    def config(self):
        """Return the full configuration dictionary."""
        return dict(self._config)
