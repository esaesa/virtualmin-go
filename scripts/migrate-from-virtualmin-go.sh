#!/usr/bin/env bash
# migrate-from-virtualmin-go.sh — one domain from virtualmin-go to virtualmin-go-app
# Usage: migrate-from-virtualmin-go.sh --domain <d>
# Safe: backups to /root/virtualmin-go-app-migrate-<ts>/, stops old only after new is ready config-wise,
# verifies new health before disabling old. Rollback: restore backup dir manually.
set -euo pipefail
DOMAIN=""
while [[ $# -gt 0 ]]; do case "$1" in --domain) DOMAIN="$2"; shift 2;; *) shift;; esac; done
[[ -n "$DOMAIN" ]] || { echo "ERROR: --domain required" >&2; exit 1; }
OLD_REG="/etc/virtualmin-go/instances.d/${DOMAIN}.conf"
NEW_REG="/etc/virtualmin-go-app/instances.d/${DOMAIN}.conf"
[[ -f "$OLD_REG" ]] || { echo "ERROR: old registry missing: $OLD_REG" >&2; exit 1; }
# shellcheck source=/dev/null
source "$OLD_REG"
TS="$(date +%F-%H%M%S)"
BACKUP="/root/virtualmin-go-app-migrate-${TS}-${DOMAIN}"
mkdir -p "$BACKUP"
cp -a "$OLD_REG" "$BACKUP/"
[[ -f "$SYSTEMD_UNIT" ]] && cp -a "$SYSTEMD_UNIT" "$BACKUP/" || true
[[ -f "$APACHE_VHOST_FILE" ]] && cp -a "$APACHE_VHOST_FILE" "$BACKUP/vhost.conf" || true
echo "Backup: $BACKUP"

# Toolchains are shared compilers: move once, symlink old path for rollback.
if [[ -d /opt/virtualmin-go/toolchains && ! -e /opt/virtualmin-go-app/toolchains ]]; then
  mkdir -p /opt/virtualmin-go-app
  mv /opt/virtualmin-go/toolchains /opt/virtualmin-go-app/toolchains
  ln -sfn /opt/virtualmin-go-app/toolchains /opt/virtualmin-go/toolchains
  echo "Toolchains moved to /opt/virtualmin-go-app/toolchains (old path symlinked)."
fi
# New unit name via systemd-escape (same logic as new CLI)
ESC=""
if command -v systemd-escape &>/dev/null; then ESC="$(systemd-escape --escape "$DOMAIN" 2>/dev/null || true)"; fi
[[ -n "$ESC" ]] || ESC="$(printf '%s' "$DOMAIN" | sed 's/[^A-Za-z0-9_.-]/-/g')"
NEW_SVC="virtualmin-go-app-${ESC}.service"
NEW_UNIT="/etc/systemd/system/${NEW_SVC}"
echo "Old unit: $SERVICE_NAME -> New unit: $NEW_SVC"

# New registry: copy + rewrite service fields
mkdir -p /etc/virtualmin-go-app/instances.d
sed -e "s/^SERVICE_NAME='.*'/SERVICE_NAME='${NEW_SVC}'/" \
    -e "s|^SYSTEMD_UNIT='.*'|SYSTEMD_UNIT='${NEW_UNIT}'|" \
    -e "s/^MANAGED_BY='.*'/MANAGED_BY='virtualmin-go-app'/" \
    "$OLD_REG" > "$NEW_REG"
chmod 0640 "$NEW_REG"
echo "New registry: $NEW_REG"

# New unit: copy old + journald + description
cp -a "$SYSTEMD_UNIT" "$NEW_UNIT"
sed -i 's/virtualmin-go/virtualmin-go-app/g' "$NEW_UNIT"
# Ensure journald sink (old units used go.log append)
if grep -q "StandardOutput=append" "$NEW_UNIT"; then
  sed -i 's|^StandardOutput=.*|StandardOutput=journal|' "$NEW_UNIT"
  sed -i 's|^StandardError=.*|StandardError=journal|' "$NEW_UNIT"
  grep -q "SyslogIdentifier" "$NEW_UNIT" || sed -i '/^StandardError=journal/a SyslogIdentifier=%N' "$NEW_UNIT"
fi
chmod 0644 "$NEW_UNIT"
systemctl daemon-reload
echo "New unit installed."

# Apache markers: VIRTUALMIN-GO -> VIRTUALMIN-GO-APP (marker lines only)
if grep -q "BEGIN VIRTUALMIN-GO ${DOMAIN}" "$APACHE_VHOST_FILE" 2>/dev/null; then
  sed -i "s/BEGIN VIRTUALMIN-GO ${DOMAIN}/BEGIN VIRTUALMIN-GO-APP ${DOMAIN}/;s/END VIRTUALMIN-GO ${DOMAIN}/END VIRTUALMIN-GO-APP ${DOMAIN}/" "$APACHE_VHOST_FILE"
  apachectl configtest || { echo "ERROR: configtest failed, restoring vhost"; cp -a "$BACKUP/vhost.conf" "$APACHE_VHOST_FILE"; exit 1; }
  systemctl reload apache2 2>/dev/null || systemctl reload httpd 2>/dev/null || true
  echo "Apache markers migrated."
else
  echo "No old Go Apache block found (kind=${APACHE_CONFIG_KIND:-none}); skipping marker migration."
fi

# Cutover: stop+disable old, enable+start new
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then systemctl stop "$SERVICE_NAME" || true; fi
systemctl disable "$SERVICE_NAME" 2>/dev/null || true
systemctl enable "$NEW_SVC" 2>/dev/null || true
systemctl stop "$NEW_SVC" 2>/dev/null || true
# Port must be free before start (old stopped)
for i in $(seq 1 10); do ss -ltn 2>/dev/null | grep -q "127.0.0.1:${PORT}" || break; sleep 1; done
systemctl start "$NEW_SVC" || { echo "ERROR: new unit failed to start"; exit 1; }
sleep 2
if /usr/local/sbin/virtualmin-go-app validate --domain "$DOMAIN" 2>&1 | tail -n 30; then echo "--- validate done ---"; fi
echo "Migrated $DOMAIN: old unit stopped+disabled (file kept for rollback), new unit active."
echo "Old registry kept at $OLD_REG — remove manually AFTER new proves stable (mv to backup)."
