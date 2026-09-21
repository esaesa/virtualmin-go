# Changelog — virtualmin-go

## 0.1.0 (2026-09-21)

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
