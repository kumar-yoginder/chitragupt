#!/bin/sh
set -e

# Ensure writable directories exist with correct ownership.
# Bind-mounted volumes override build-time permissions, so we
# fix ownership at runtime before dropping to the non-root user.
mkdir -p /app/data /app/logs /app/temp
chmod 755 /app/data /app/logs /app/temp
chown chitragupt_user:chitragupt_group /app/data /app/logs /app/temp

# Drop privileges and exec the CMD (default: python main.py)
exec su-exec chitragupt_user "$@"
