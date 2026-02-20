#!/bin/sh
set -e

# Ensure writable directories exist.
mkdir -p /app/data /app/logs /app/temp

# Best-effort ownership/mode — bind-mounted dirs (data/, logs/) inherit host
# permissions and may not support POSIX chmod/chown (e.g. Windows/NTFS mounts).
# temp/ is set at build time but we try again here for safety.
chown chitragupt_user:chitragupt_group /app/data /app/logs /app/temp 2>/dev/null || true
chmod 755 /app/data /app/logs /app/temp 2>/dev/null || true

# Drop privileges and exec the CMD (default: python main.py)
exec su-exec chitragupt_user "$@"
