#!/usr/bin/env bash
# install.sh — Install virtualmin-go-app on a server
set -euo pipefail

NAME="virtualmin-go-app"
VERSION="$(cat "$(dirname "$0")/../VERSION" | tr -d '[:space:]')"

echo "=== Virtualmin Go $VERSION Installer ==="

[[ "$(id -u)" -eq 0 ]] || { echo "ERROR: This script must run as root." >&2; exit 1; }

WEBMIN_ROOT="$(grep '^root=' /etc/webmin/miniserv.conf 2>/dev/null | cut -d= -f2-)"
if [[ -z "$WEBMIN_ROOT" ]]; then
    WEBMIN_ROOT="/usr/share/webmin"
    [[ -d "$WEBMIN_ROOT" ]] || { echo "ERROR: Cannot detect Webmin root." >&2; exit 1; }
fi
echo "Webmin root: $WEBMIN_ROOT"

echo "Creating directories..."
mkdir -p /etc/virtualmin-go-app/{instances.d,locks,backups}
mkdir -p /root/service-reports/virtualmin-go-app /root/service-backups/virtualmin-go-app
mkdir -p /var/log/virtualmin-go-app

echo "Installing CLI manager..."
cp "$(dirname "$0")/../sbin/virtualmin-go-app" /usr/local/sbin/virtualmin-go-app
chown root:root /usr/local/sbin/virtualmin-go-app
chmod 0750 /usr/local/sbin/virtualmin-go-app

echo "Installing config defaults..."
cp "$(dirname "$0")/../etc/virtualmin-go-app/config.default" /etc/virtualmin-go-app/config.default
if [[ ! -f /etc/virtualmin-go-app/config ]]; then
    cp /etc/virtualmin-go-app/config.default /etc/virtualmin-go-app/config
fi

echo "Setting permissions..."
chown -R root:root /etc/virtualmin-go-app
chmod 0750 /etc/virtualmin-go-app
chmod 0750 /etc/virtualmin-go-app/instances.d
chmod 0750 /etc/virtualmin-go-app/locks
chmod 0750 /etc/virtualmin-go-app/backups
chmod 0640 /etc/virtualmin-go-app/config /etc/virtualmin-go-app/config.default

echo "Installing Webmin module..."
SRC="$(dirname "$0")/../webmin-module/virtualmin-go-app"
DEST="$WEBMIN_ROOT/virtualmin-go-app"
mkdir -p "$DEST"
cp -a "$SRC/"* "$DEST/" 2>/dev/null || true
chown -R root:root "$DEST"
find "$DEST" -name '*.cgi' -exec chmod 0755 {} \;
find "$DEST" -name '*.pl' -exec chmod 0644 {} \;
mkdir -p /etc/webmin/virtualmin-go-app
cp "$SRC/config" /etc/webmin/virtualmin-go-app/config
chmod 0640 /etc/webmin/virtualmin-go-app/config

echo "Enabling required Apache modules..."
for mod in proxy proxy_http headers ssl rewrite remoteip; do
    a2enmod "$mod" 2>/dev/null || true
done

echo "Registering Virtualmin plugin feature..."
VSCONF="/etc/webmin/virtual-server/config"
if grep -q "^plugins=.*virtualmin-go-app" "$VSCONF" 2>/dev/null; then
    echo "Already registered in $VSCONF"
else
    cp -a "$VSCONF" "${VSCONF}.bak-virtualmin-go-app-$(date +%F-%H%M%S)"
    if grep -q "^plugins=" "$VSCONF"; then
        sed -i 's/^plugins=\(.*\)$/plugins=\1 virtualmin-go-app/' "$VSCONF"
    else
        echo "plugins=virtualmin-go-app" >> "$VSCONF"
    fi
    grep "^plugins=" "$VSCONF"
fi

echo "Granting module to Webmin users holding virtualmin-pocketbase..."
for acl in /etc/webmin/webmin.acl; do
    if [[ -f "$acl" ]] && grep -q "virtualmin-pocketbase" "$acl" && ! grep -q "virtualmin-go-app" "$acl"; then
        cp -a "$acl" "${acl}.bak-virtualmin-go-app-$(date +%F-%H%M%S)"
        sed -i 's/ virtualmin-pocketbase / virtualmin-pocketbase virtualmin-go-app /;s/ virtualmin-pocketbase$/ virtualmin-pocketbase virtualmin-go-app/' "$acl"
        echo "Granted in $acl"
    fi
done

bash -n /usr/local/sbin/virtualmin-go-app && echo "CLI syntax OK"
for pl in virtual_feature.pl virtualmin-go-app-lib.pl; do
    perl -I"$WEBMIN_ROOT" -c "$DEST/$pl" || { echo "ERROR: $pl failed compile check"; exit 1; }
done

echo "Restarting webmin..."
systemctl restart webmin || true

echo "=== virtualmin-go-app $VERSION installed ==="
echo "Next: virtualmin-go-app enable --domain <server>"
