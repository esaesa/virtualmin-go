# Changelog — virtualmin-go-app

## Unreleased (final-arch refinements + rename, 2026-09-22)

- **Rename `virtualmin-go` → `virtualmin-go-app`** (module manages deployed
  Go applications). New paths: CLI `/usr/local/sbin/virtualmin-go-app`,
  config `/etc/virtualmin-go-app`, Webmin module `virtualmin-go-app`,
  units `virtualmin-go-app-<escaped-domain>.service`, Apache markers
  `VIRTUALMIN-GO-APP`, toolchains `/opt/virtualmin-go-app/toolchains`
  (old path symlinked). Both live instances (`api`, `go-test`) migrated
  with `scripts/migrate-from-virtualmin-go.sh`, validated 0 failures;
  old registries archived, old units kept disabled for rollback.
- **journald by default**: units use `StandardOutput/StandardError=journal`
  (+ `SyslogIdentifier=%N`); no `go.log` file is created. `logs` reads
  journalctl (legacy file as fallback only). Audit/event logs belong
  under `data/` if required.
- **Safe artifact extraction**: `validate_artifact_listing` rejects
  absolute paths, `..` traversal, device/fifo nodes, and escaping
  symlinks BEFORE extraction, using raw tar headers via python tarfile
  (GNU tar sanitizes `tzf` output, so listing text alone is insufficient).
  Evil archives rejected with zero mutation (proven).
- **previous-after-health**: `previous` is updated only after the new
  release passes the health gate; failed deploys restore `current` and
  leave `previous` untouched. Also fixed health-path poisoning: a failed
  candidate no longer overwrites registry `HEALTH_PATH` (restored to old
  value on rollback; proven with broken-health deploy).
- **systemd-escape naming**: `go_unit_name_for` escapes via
  `systemd-escape --escape` (sed fallback); normal domains still render
  naturally (`virtualmin-go-app-api.novel-co.com.service`).
- **`/health` vs `/ready`**: deploy gates on `/health` (alive), then
  warns (not fails) if local `/ready` (deps) is not yet OK; `validate`
  checks both (health FAIL, ready WARN) with a local curl hint.
- **`remove --purge-data`** alias for `--delete-data` (confirmation flag
  likewise aliased). `disable` now also runs `systemctl disable` (unit
  file + registry + data kept).
- **Backup proof**: native `virtualmin backup-domain` includes
  `SERVER_HOME/apps/go` (3262 entries on `go-test`, incl. releases,
  config, data); module `backup` covers releases+config+data+symlinks
  with `tmp/*` contents excluded. Same tree mechanism covers
  `apps/pocketbase`.

## 0.2.0 (2026-09-22)

T1–T4 per locked scope. Toolchain store, source builds, dev mode, owner UI,
observability — all disposable-proven on `go-test`, production untouched
(`api` sample intact, PB intact).

- Shared toolchain store `/opt/virtualmin-go-app/toolchains/<ver>/` + `current`
  (compilers are shared tooling like the PB runtime; app binaries stay in
  `apps/go`). Commands: `install-toolchain` (official tarball + SHA-256 vs
  `go.dev/dl/?mode=json`, offline by default), `list-toolchains`,
  `set-current-toolchain`, `remove-toolchain` (refuses pins + current),
  `check-updates`, `pin-toolchain`/`--follow-default`, `enable --toolchain`.
- Build-from-source deploy: `--source <git-url> [--branch] [--commit]` and
  `--source-dir`, built as the domain user with pinned toolchain,
  instance-scoped `GOCACHE`/`GOMODCACHE`, `GOTOOLCHAIN=local`,
  `CGO_ENABLED=0`; then the identical atomic releases/health-gated flow.
  Registry: `SOURCE_URL/BRANCH/COMMIT`, `GO_MODE`, per-release `deploy.json`
  carries mode/toolchain/package/commit.
- Dev mode (`--mode dev`): unit runs `<toolchain>/bin/go run <pkg>` from
  `current/src` with cache env; rollback always rewrites the unit (mode/tc
  drift safe).
- Hardened health gate (stale-process lesson): stop-first, port-free wait,
  listener must be the unit MainPID or its child (`go run` supervisor),
  combined verify+health loop with longer dev retries.
- Fixes along the way: `^(go)?` version regex, `releases/<id>` symlink
  targets (recurring), `-L` with trailing slash, prune dedupe, grep `-H`,
  pipefail guards, corrupt-unit newline, pre-T1 registry field healing.

## 0.1.1 (2026-09-21)

- Ownership contract (AGENTS.md/README.md): module owns only its marker
  blocks, registries, units, and `apps/go/**`. Vhost structure, `:80`,
  redirects, SSL stay Virtualmin-owned. Reverted a manual `:80` redirect on
  `api.novel-co.com`, replaced with Virtualmin's native `create-redirect`
  (the mechanism PocketBase relies on).
- `validate`: new WARN when the `/` proxy is live but no native http→https
  redirect exists (detection only, with the native fix command).
- sysinfo dashboard parity with PocketBase: per-instance table now shows
  Domain, Version, Port, and live State (registry-first, cheap systemd
  check only — same rendering practice as the reference).
- `install.sh` grants the module in `/etc/webmin/webmin.acl` next to
  `virtualmin-pocketbase` (fixes "Access denied" for root on first install).

- Initial sibling module of `virtualmin-pocketbase` (G1–G10 scope).
- Canonical `SERVER_HOME` resolution from Virtualmin metadata;
  `GO_APP_ROOT=$SERVER_HOME/apps/go` (no `/home/<user>` guessing).
- Independent port allocator `18100–18199` (registry + `ss` conflict check).
- Non-destructive `enable`: secure dirs, `production.env` (0600), metadata,
  port reservation, registry. No Apache proxy until a release is deployed.
- Artifact deploys (`manifest.json` + `bin/`) into new `releases/<id>` with
  SHA-256 record, executable/arch check, `current`/`previous` rotation,
  systemd rewrite, health-gated promotion, automatic restore-on-failure.
- `rollback` swaps `current`/`previous` without touching secrets.
- systemd `virtualmin-go-app-<domain>.service` (domain owner, `Restart=on-failure`,
  `LimitNOFILE=65535`, `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=full`
  + `ReadWritePaths=$APP_ROOT`).
- Transactional Apache `/` proxy coexisting with PocketBase `/pb/`
  (own markers only, configtest-or-restore, `/.well-known` untouched).
- `status --json` (5-state model, no secrets) and `validate` PASS/WARN/FAIL.
- `backup`/`restore` of `$APP_ROOT` (excludes `tmp/`), `prune-releases`
  (default keep 5, never current/previous), guarded `remove`.

## 0.1.2 (2026-09-21)

- Global Settings page (`edit_config.cgi`) parity with PocketBase: validated
  atomic update of `/etc/virtualmin-go-app/config` with backup + audit trail.
  Guardrails: loopback-only listener, no overlap with PB 18000–18999,
  retention >= 2. Never touches instance secrets.
