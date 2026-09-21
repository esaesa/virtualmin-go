#!/usr/bin/env bash
# uninstall.sh — Remove virtualmin-go (keeps instance data + registries)
set -euo pipefail
[[ "$(id -u)" -eq 0 ]] || { echo "ERROR: This script must run as root." >&2; exit 1; }
WEBMIN_ROOT="$(grep '^root=' /etc/webmin/miniserv.conf 2>/dev/null | cut -d= -f2-)"
WEBMIN_ROOT="${WEBMIN_ROOT:-/usr/share/webmin}"
rm -f /usr/local/sbin/virtualmin-go
rm -rf "$WEBMIN_ROOT/virtualmin-go"
rm -rf /etc/webmin/virtualmin-go
systemctl restart webmin || true
echo "virtualmin-go removed (registries + app data kept under /etc/virtualmin-go and SERVER_HOME/apps/go)."
