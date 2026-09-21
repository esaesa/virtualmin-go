# Changelog — virtualmin-go

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
- systemd `virtualmin-go-<domain>.service` (domain owner, `Restart=on-failure`,
  `LimitNOFILE=65535`, `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=full`
  + `ReadWritePaths=$APP_ROOT`).
- Transactional Apache `/` proxy coexisting with PocketBase `/pb/`
  (own markers only, configtest-or-restore, `/.well-known` untouched).
- `status --json` (5-state model, no secrets) and `validate` PASS/WARN/FAIL.
- `backup`/`restore` of `$APP_ROOT` (excludes `tmp/`), `prune-releases`
  (default keep 5, never current/previous), guarded `remove`.

## 0.1.2 (2026-09-21)

- Global Settings page (`edit_config.cgi`) parity with PocketBase: validated
  atomic update of `/etc/virtualmin-go/config` with backup + audit trail.
  Guardrails: loopback-only listener, no overlap with PB 18000–18999,
  retention >= 2. Never touches instance secrets.
