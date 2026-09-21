# Virtualmin Go — versioned Go application deployments per Virtualmin server

Sibling of `virtualmin-pocketbase`. Reference implementation for Virtualmin
integration mechanics (SERVER_HOME resolution, ownership, port allocation,
systemd generation, transactional Apache edits, status/validate framework);
Go-specific in release artifacts (`releases/` + `current`/`previous`
symlinks), executable validation, Go port range, `/health` + `/ready`, and
root `/` proxy coexisting with PocketBase `/pb/`.

## Frozen architecture

For any Virtualmin server, resolve `SERVER_HOME` from Virtualmin metadata
(never guess from `/home/<user>`), then own:

```text
$SERVER_HOME/apps/go/
├── releases/<id>/bin/<app>   # versioned binaries (never overwritten in place)
├── current -> releases/<id>  # live release
├── previous -> releases/<id> # last known-good (rollback target)
├── config/production.env     # secrets, 0600, never rolled back
├── data/uploads, data/results
├── models/
├── tmp/
└── .virtualmin-go.env        # module metadata only (no secrets)
```

- Ports: `18100–18199` (PocketBase keeps `18000–18099`). Bind `127.0.0.1` only.
- systemd: `virtualmin-go-<domain>.service`, runs as the Virtualmin domain
  owner, `EnvironmentFile=.../config/production.env`.
- Apache: managed `BEGIN/END VIRTUALMIN-GO <domain>` block for `/` only.
  Never touches `/pb/`, `/.well-known`, redirects, or SSL directives. The
  specific `/pb/` block must sort before the `/` catch-all.
- TLS stays with Virtualmin/Apache. Go listens plain HTTP on localhost.
- States: `disabled | configured | deployed | running | degraded`.
- Enabling is non-destructive: no proxy until a valid release exists.
- No DB provisioning or auto-migrations in v1. No Go compiler needed on VPS.

## Layout

```text
sbin/virtualmin-go                  # root CLI lifecycle manager
webmin-module/virtualmin-go/        # Virtualmin feature + Webmin UI
etc/virtualmin-go/config.default    # global defaults (port range, etc.)
scripts/{install,uninstall,precheck,postinstall}.sh
tests/                              # syntax + lifecycle tests
docs/                               # milestone notes
```

## CLI lifecycle

```text
virtualmin-go enable | disable | deploy | rollback
virtualmin-go start | stop | restart
virtualmin-go status | validate | remove
virtualmin-go logs | releases | prune-releases | list | backup | restore
```

## License

GPL-3.0-or-later.
