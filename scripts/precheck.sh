#!/usr/bin/env bash
# precheck.sh — Read-only environment precheck for virtualmin-go-app
set -euo pipefail
TS="$(date +%F-%H%M%S)"
REPORT="/root/virtualmin-go-app-precheck-$TS.txt"
{
  echo "===== Virtualmin Go precheck ====="
  date
  echo
  echo "===== OS ====="
  cat /etc/os-release 2>/dev/null || true
  uname -a
  echo
  echo "===== Webmin root ====="
  grep '^root=' /etc/webmin/miniserv.conf 2>/dev/null || true
  echo
  echo "===== Virtualmin ====="
  virtualmin --version 2>&1 || true
  echo
  echo "===== Apache ====="
  apachectl -v 2>&1 | head -3 || true
  apachectl configtest 2>&1 || true
  echo
  echo "===== systemd ====="
  systemctl --version 2>&1 | head -2 || true
  echo
  echo "===== Ports 18100-18199 ====="
  ss -ltn 2>/dev/null | awk '$4 ~ /:181[0-9][0-9]$/ {print}' || echo "(none in Go range)"
  echo
  echo "===== PocketBase coexistence ====="
  ls /etc/virtualmin-pocketbase/instances.d/ 2>/dev/null || echo "(no PB instances)"
  echo
  echo "===== Tools ====="
  for t in python3 curl tar sha256sum file; do command -v $t >/dev/null && echo "OK: $t" || echo "MISSING: $t"; done
} | tee "$REPORT"
echo "Report: $REPORT"
