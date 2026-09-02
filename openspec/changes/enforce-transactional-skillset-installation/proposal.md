## Why

The installer verifies every private staging directory before publication, but it publishes the fifteen KSRF skill directories one at a time by deleting the current destination and then renaming the staged directory. If the third rename fails, the target can contain two new skills, twelve old skills, and one missing skill. The error path removes staging but does not restore the target. Two installers can also interleave those per-skill operations, both exit successfully, and leave a mixed-version tree because there is no target-scoped lock or final aggregate verification.

For a user, a failed or concurrent upgrade must not silently damage the previously working installation. The achievable near-term contract is a serialized, rollback-safe writer with durable recovery. The current flat directory layout cannot make all fifteen paths change in one atomic filesystem operation for lock-free readers, so this change must not claim snapshot atomicity that it does not provide.

## What Changes

- Add one target-scoped, non-blocking single-writer lock shared by canonical installs, custom-target installs, and reverse synchronization through `tools/install_skillset.py`.
- Stage and verify the complete incoming runtime payload before changing any managed skill directory.
- Before the first managed-directory rename, persist and fsync a transaction journal with exact old identities, presence or absence records, and fixed planned backup slots for all fifteen managed destinations; each present old directory becomes its exact backup by same-filesystem rename immediately before replacement.
- Replace managed skills under the lock, verify the final aggregate target, and publish a durable commit marker before deleting backups.
- On an ordinary exception or `KeyboardInterrupt`, roll back every managed destination to its exact pre-install state in reverse order and preserve recovery evidence if rollback itself cannot complete.
- On the next invocation after process death, acquire the same lock and deterministically recover any valid unfinished transaction before accepting a new installation. A committed transaction may only be cleaned up after its final target is reverified.
- Refuse to guess when the journal, backup set, transaction identity, or filesystem type is corrupt, ambiguous, missing, duplicated, or unsafe. Report the retained recovery path without further mutation.
- Leave every unmanaged sibling in the target untouched and preserve the existing development-file behavior when that mode is explicitly used.
- Keep `install.sh` as a thin caller: it propagates lock/recovery failures and prints the shell export only after a successful committed installation.
- Document and test the consistency boundary: cooperating writers are serialized and completed/rolled-back states are exact, while lock-free readers may briefly observe the per-directory commit in progress under the current flat layout.

## Capabilities

### New Capabilities

- `ksrf-skillset-install-transaction`: serialized, rollback-safe KSRF skillset installation with durable interrupted-transaction recovery and fail-closed corruption handling.

### Modified Capabilities

None.

## Impact

- Runtime tooling: `tools/install_skillset.py`; `install.sh` only if a small propagation or messaging correction is required.
- Tests: deterministic exception, `KeyboardInterrupt`, process-death recovery, corrupt-journal, concurrency, successful-upgrade, unmanaged-sibling, preserved-development, and shell-wrapper cases.
- Release evidence: `skills-manifest.json` must be regenerated because the installer is a release-covered tool; the installed skill payload is otherwise unchanged.
- No network or model calls, no legal workflow change, and no permission to overwrite non-KSRF skills.
- Successful installation means an exact verified target after commit. It does not mean a lock-free runtime reader saw an atomic fifteen-directory snapshot during the short commit window.
