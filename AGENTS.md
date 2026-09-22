# Agents Guide — virtualmin-go-app

## Source of truth

- Code lives in `/root/virtualmin-go-app`. Production copies:
  - CLI: `/usr/local/sbin/virtualmin-go-app` (0750, root:root)
  - Webmin module: `/usr/share/webmin/virtualmin-go-app`
  - Registries: `/etc/virtualmin-go-app/instances.d/*.conf`

## After completing tasks

### Deploy to production

```bash
cp /root/virtualmin-go-app/sbin/virtualmin-go-app /usr/local/sbin/virtualmin-go-app
chmod 0750 /usr/local/sbin/virtualmin-go-app

WEBMIN="/usr/share/webmin/virtualmin-go-app"
SRC="/root/virtualmin-go-app/webmin-module/virtualmin-go-app"
mkdir -p "$WEBMIN"
cp "$SRC/"*.cgi "$SRC/"*.pl "$WEBMIN/" 2>/dev/null
cp "$SRC/module.info" "$SRC/config.info" "$WEBMIN/"
mkdir -p "$WEBMIN/lang" && cp "$SRC/lang/en" "$WEBMIN/lang/en"
chmod 0755 "$WEBMIN/"*.cgi

bash -n /usr/local/sbin/virtualmin-go-app
perl -I/usr/share/webmin -c "$WEBMIN/virtual_feature.pl"
perl -I/usr/share/webmin -c "$WEBMIN/virtualmin-go-app-lib.pl"
systemctl restart webmin
```

### Ownership contract (never violate)

The module owns ONLY these, and changes them only through module code:
- `$SERVER_HOME/apps/go/**` (via CLI, guarded by `assert_safe_app_root`)
- `/etc/virtualmin-go-app/instances.d/*.conf` (registries)
- `/etc/systemd/system/virtualmin-go-app-*.service` (units)
- Lines between `BEGIN/END VIRTUALMIN-GO-APP <domain>` inside the `:443` vhost
- `/opt/virtualmin-go-app/toolchains/**` (shared compilers — same category as
  the PocketBase runtime; official tarballs + SHA-256 verified)

Everything else is Virtualmin-owned: vhost structure, `:80` content,
scheme/host redirects, SSL directives, `/.well-known`, webmail/admin rules.
The module MUST NOT hand-edit those — not even "one small rule" (2026-09-21
lesson: a manual `:80` redirect was reverted and replaced with Virtualmin's
native `create-redirect`, the same mechanism PocketBase relies on).
Missing Virtualmin-side configuration is reported as a `validate` WARN with
the native fix command, never silently patched.

- Never derive paths from `/home/<user>` or domain dots. Always
  `get_server_home_field` → `resolve_domain` → `GO_APP_ROOT=$SERVER_HOME/apps/go`.
- `assert_safe_app_dir`: only ever operate inside `$SERVER_HOME/apps/go`.
  `remove --delete-data` requires the explicit confirmation flag.
- Apache: only touch lines between `BEGIN/END VIRTUALMIN-GO-APP <domain>`.
  Always `apachectl configtest` before reload; restore on failure.
- Never print `production.env` values in status/validate/logs.
- Never deploy to `api.novel-co.com` until the disposable-domain cycle
  (go-test) is fully green including reboot + rollback + removal.

### Update CHANGELOG.md

Add a summary of all changes to `/root/virtualmin-go-app/CHANGELOG.md` and the
task log `/root/task-logs/2026-09-21_virtualmin-go-app-sibling-module.md` after
each session.
