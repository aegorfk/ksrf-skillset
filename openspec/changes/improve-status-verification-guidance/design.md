## Context

`--status` is a bounded structural observation. Its clean recommendation was
designed before the public offline `--verify` command existed, so it currently
skips directly to the slower network comparison. The existing report schema,
shell-safety guard, exact-target quoting, and non-clean guidance are already
stable and should remain intact.

## Goals / Non-Goals

**Goals:**

- Make the offline check the first discoverable next step after clean status.
- Keep optional online freshness as an explicit second step.
- Preserve one stable `recommended_action` string in both human and JSON output.
- Preserve exact target bytes, executable repo-side entry point checks, and the
  fallback for unsafe display values.

**Non-Goals:**

- Do not run either verification command from status.
- Do not change status keys, exit codes, classification, observation budgets,
  or installation behavior.
- Do not add JSON action objects or arrays.
- Do not change the assurance boundary of `--verify` or `--verify-current`.

## Decisions

1. **Keep the schema and replace only the action text.** The existing
   `recommended_action` string will contain two ordered, separately labelled
   shell commands. This avoids a schema migration and remains readable in both
   human and JSON output.
2. **Render both commands from one validated entry point and exact target.** The
   current printable-value, symlink, regular-file, and executable guards apply
   once before either command is emitted. Both commands use `shlex.join`.
3. **Put offline integrity first.** Step 1 is `--verify`; step 2 is
   `--verify-current` and explicitly says that it uses the network. The status
   process itself invokes neither command.
4. **Leave non-clean actions untouched.** An incomplete, unsafe, or recoverable
   installation should still direct the user to installation/recovery rather
   than content verification.

## Risks / Trade-offs

- **Longer JSON string** → keep it bounded and deterministic; do not add fields.
- **Users may confuse the two checks** → label the first as local/offline and
  the second as optional/networked, and preserve the legal-readiness boundary.
- **A path cannot be rendered safely** → emit the existing fixed fallback and
  no partial command.

## Migration Plan

Publish as an additive guidance update, regenerate the release manifest,
install the exact release, and verify both human and JSON snapshots. Rollback is
the previous one-command recommendation; no target data migration is required.

## Open Questions

None.
