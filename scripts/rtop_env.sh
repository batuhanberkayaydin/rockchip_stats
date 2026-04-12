#!/bin/bash
# This file is part of the rockchip_stats package.
#
# Environment setup script for rtop.
# Installed to /etc/profile.d/rtop_env.sh to set up environment
# variables for all users.

# Add rtop group check
if groups $(whoami) 2>/dev/null | grep -q '\brtop\b'; then
    export RTOP_GROUP=1
fi

# Set default socket path
export RTOP_SOCK=${RTOP_SOCK:-/run/rtop.sock}
