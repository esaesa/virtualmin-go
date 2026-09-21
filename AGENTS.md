# Agents Guide — virtualmin-go

## Source of truth

- Code lives in `/root/virtualmin-go`. Production copies:
  - CLI: `/usr/local/sbin/virtualmin-go` (0750, root:root)
  - Webmin module: `/usr/share/webmin/virtualmin-go`
  - Registries: `/etc/virtualmin-go/instances.d/*.conf`

## After completing tasks

### Deploy to production

```bash
cp /root/virtualmin-go/sbin/virtualmin-go /usr/local/sbin/virtualmin-go
chmod 0750 /usr/local/sbin/virtualmin-go

WEBMIN="/usr/share/webmin/virtualmin-go"
SRC="/root/virtualmin-go/webmin-module/virtualmin-go"
mkdir -p "$WEBMIN"
cp "$SRC/"*.cgi "$SRC/"*.pl "$WEBMIN/" 2>/dev/null
cp "$SRC/module.info" "$SRC/config.info" "$WEBMIN/"
mkdir -p "$WEBMIN/lang" && cp "$SRC/lang/en" "$WEBMIN/lang/en"
chmod 0755 "$WEBMIN/"*.cgi

bash -n /usr/local/sbin/virtualmin-go
perl -I/usr/share/webmin -c "$WEBMIN/virtual_feature.pl"
perl -I/usr/share/webmin -c "$WEBMIN/virtualmin-go-lib.pl"
systemctl restart webmin
```

### Safety rules (never violate)

- Never derive paths from `/home/<user>` or domain dots. Always
  `get_server_home_field` → `resolve_domain` → `GO_APP_ROOT=$SERVER_HOME/apps/go`.
- `assert_safe_app_dir`: only ever operate inside `$SERVER_HOME/apps/go`.
  `remove --delete-data` requires the explicit confirmation flag.
- Apache: only touch lines between `BEGIN/END VIRTUALMIN-GO <domain>`.
  Always `apachectl configtest` before reload; restore on failure.
- Never print `production.env` values in status/validate/logs.
- Never deploy to `api.novel-co.com` until the disposable-domain cycle
  (go-test) is fully green including reboot + rollback + removal.

### Update CHANGELOG.md

Add a summary of all changes to `/root/virtualmin-go/CHANGELOG.md` and the
task log `/root/task-logs/2026-09-21_virtualmin-go-sibling-module.md` after
each session.
