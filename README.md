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
└── .virtualmin-go-app.env        # module metadata only (no secrets)
```

- Ports: `18100–18199` (PocketBase keeps `18000–18099`). Bind `127.0.0.1` only.
- systemd: `virtualmin-go-app-<domain>.service`, runs as the Virtualmin domain
  owner, `EnvironmentFile=.../config/production.env`.
- Apache: managed `BEGIN/END VIRTUALMIN-GO-APP <domain>` block for `/` only.
  Never touches `/pb/`, `/.well-known`, redirects, or SSL directives. The
  specific `/pb/` block must sort before the `/` catch-all.
- TLS stays with Virtualmin/Apache. Go listens plain HTTP on localhost.
- States: `disabled | configured | deployed | running | degraded`.
- Enabling is non-destructive: no proxy until a valid release exists.
- No DB provisioning or auto-migrations in v1. No Go compiler needed on VPS.

## Layout

```text
sbin/virtualmin-go-app                  # root CLI lifecycle manager
webmin-module/virtualmin-go-app/        # Virtualmin feature + Webmin UI
etc/virtualmin-go-app/config.default    # global defaults (port range, etc.)
scripts/{install,uninstall,precheck,postinstall}.sh
tests/                              # syntax + lifecycle tests
docs/                               # milestone notes
```

## Ownership boundary (shared with virtualmin-pocketbase)

The module owns only: `apps/go/**`, its registries, its systemd units, and
the lines between `BEGIN/END VIRTUALMIN-GO-APP <domain>` in the `:443` vhost.
Vhost structure, `:80` content, scheme/host redirects, and SSL directives are
Virtualmin-owned — the module detects gaps (e.g. missing http→https redirect)
as `validate` WARNs with the native fix, never hand-edits them.

Shared Go toolchains live in `/opt/virtualmin-go-app/toolchains/<ver>/`:
compilers are shared tooling (same category as the PocketBase runtime);
application binaries always stay per-instance under `apps/go`.

## Deploy paths

1. **Prebuilt artifact** (`manifest.json` + `bin/` tarball) — built anywhere.
2. **Build from source** (`--source <git-url> [--branch] [--commit]` or
   `--source-dir`): compiled on the VPS as the domain user with the pinned
   toolchain, instance-scoped `GOCACHE`/`GOMODCACHE`, `GOTOOLCHAIN=local`.
3. **Dev mode** (`--mode dev`): unit runs `<toolchain>/bin/go run <pkg>`
   from the release source tree. Manual restart/redeploy (no watcher).

All paths converge on the same atomic releases + health-gated promotion +
rollback. UI (`deploy.cgi`) offers upload + git + dev to domain owners
(scoped to their own instances; toolchain-global ops are master-only).

## CLI lifecycle

```text
virtualmin-go-app enable | disable | deploy | rollback
virtualmin-go-app start | stop | restart
virtualmin-go-app status | validate | remove
virtualmin-go-app logs | releases | prune-releases | list | backup | restore
```

## License

GPL-3.0-or-later.
