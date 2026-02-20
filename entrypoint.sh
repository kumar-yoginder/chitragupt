#!/bin/sh
set -e

# Ensure writable directories exist.
# Bind-mounted volumes (data/, logs/) inherit host permissions and may not
# support POSIX chmod/chown (e.g. Windows/NTFS mounts), so those calls are
# best-effort.  Container-local dirs (temp/) are fixed strictly.
mkdir -p /app/data /app/logs /app/temp

# Best-effort ownership/mode for bind-mounted dirs (may fail on NTFS mounts)
chown chitragupt_user:chitragupt_group /app/data /app/logs 2>/dev/null || true
chmod 755 /app/data /app/logs 2>/dev/null || true

# Strict fix for container-local dirs
chown chitragupt_user:chitragupt_group /app/temp
chmod 755 /app/temp

# Drop privileges and exec the CMD (default: python main.py)
exec su-exec chitragupt_user "$@"
