#!/usr/bin/env bash
# test-syntax.sh — syntax checks for CLI + Perl module (safe, read-only)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
bash -n "$ROOT/sbin/virtualmin-go" && echo "PASS: bash -n sbin/virtualmin-go" || fail=1
WEBMIN_ROOT="$(grep '^root=' /etc/webmin/miniserv.conf 2>/dev/null | cut -d= -f2-)"
WEBMIN_ROOT="${WEBMIN_ROOT:-/usr/share/webmin}"
for pl in virtual_feature.pl virtualmin-go-lib.pl; do
    if perl -I"$WEBMIN_ROOT" -c "$ROOT/webmin-module/virtualmin-go/$pl"; then
        echo "PASS: perl -c $pl"
    else
        echo "FAIL: perl -c $pl"; fail=1
    fi
done
for cgi in index.cgi status.cgi validate.cgi action.cgi edit_config.cgi deploy.cgi toolchains.cgi logs.cgi operations.cgi backup.cgi; do
    if perl -I"$WEBMIN_ROOT" -c "$ROOT/webmin-module/virtualmin-go/$cgi" 2>&1 | grep -q "syntax OK"; then
        echo "PASS: perl -c $cgi"
    else
        echo "FAIL: perl -c $cgi"; fail=1
    fi
done
"$ROOT/sbin/virtualmin-go" help | grep -q "deploy" && echo "PASS: help lists deploy" || { echo "FAIL: help"; fail=1; }
exit $fail
