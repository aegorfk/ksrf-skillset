## Context

Successful preparation publishes exactly seven private files and emits one complete
stdout JSON line containing both `manifest_sha256` and
`independent_review_packet_sha256`. The first is the manifest object's canonical
unsigned self-digest used by downstream import; it is not the manifest file digest.
The second is the raw ZIP SHA-256 passed independently to the reviewer. Although the
first transitively binds the ZIP through the closed manifest, reconstructing the
second from the package would weaken the existing two-anchor handoff contract.

Some post-publication failures preserve a possibly complete package while invalidating
stdout. Their documented recovery is available only when the original structured
diagnostic classified the event as `repeat_then_compare_candidate`, the inputs remain
unchanged, the external problem is repaired, a repeat into a new absent sibling
returns normally with code `0`, and both stdout anchors are retained. Staging,
cleanup, location, integrity, ACL, hardlink, escaped-object, or unaccounted-inode
uncertainty stays administrator-only. This later comparator cannot observe the
historical error or authenticate how the anchors were obtained.

## Goals / Non-Goals

**Goals:**

- Close the installed comparison gap for eligible preparation recovery.
- Require both successful-repeat stdout anchors and validate them only against the
  repeated package.
- Validate both packages independently, bind each to the installed codebook, compare
  all corresponding raw bytes, and fully recapture every input before success.
- Produce a deterministic value-free report with actionable fixed Russian routes.
- Preserve source/installed parity without shipping tests, evals, or OpenSpec files.

**Non-Goals:**

- Do not decide whether the original failure was eligible or whether the repeat
  actually returned normally.
- Do not infer either expected digest from either package, rerun preparation, reread
  the source workspace, select a package for downstream use, or send the ZIP.
- Do not repair, normalize, chmod, copy, move, delete, quarantine, extract to disk,
  persist, import, finalize, promote, access the network/database, or spawn a process.
- Do not authenticate anchor provenance, reviewer identity, source truth, legal
  correctness, current law, publication permission, complaint readiness, or filing.

## Decisions

### 1. Require two directories and both successful-repeat anchors

The exact route is:

```text
judicial_meaning.py quality native-reliability compare-audit-bundles \
  --uncertain-audit-bundle-dir DIR \
  --repeated-audit-bundle-dir DIR \
  --expected-manifest-sha256 SAVED_REPEAT_MANIFEST_SHA256 \
  --expected-independent-review-packet-sha256 SAVED_REPEAT_PACKET_SHA256
```

All four options are required at argparse level. There are no positional, stdin,
default, discovery, output, diagnostic-token, or abbreviated-option forms. Both
digests must be lowercase 64-hex retained outside the package from the same complete
successful repeat stdout followed by normal code-`0` return. The comparator never
reads an expectation from the manifest or ZIP and never applies an external
expectation to the uncertain package.

The packet anchor is cryptographically redundant after full manifest validation but
procedurally necessary. Requiring it preserves the established reviewer-transfer
anchor instead of legitimizing reconstruction from a possibly uncertain package.

### 2. Admit exactly two complete private sibling packages

Both paths must name different direct siblings under one actual parent opened once
with no-follow directory semantics and held throughout. The parent must be owned by
the effective user, not group/world writable, and have no extended ACL on Darwin.
Both directories must be owned by the effective user, mode `0700`, ACL-free on
Darwin, distinct by device/inode, and on the parent's device.

Each inventory is exactly:

```text
screening-candidates.audit.jsonl
primary-decisions.audit.jsonl
coding-audit-plan.json
secondary-review-queue.jsonl
secondary-coding-template.jsonl
independent-review-packet.zip
coding-audit-inputs-manifest.json
```

Every entry must be a regular effective-user-owned mode-`0600` single-link file,
ACL-free on Darwin, on its directory's device, and distinct from every other input
file across both packages. Enumeration stops on an eighth entry. Established limits
remain: 2 MiB manifest, 4 MiB plan, 64 MiB per JSONL, 256 MiB ZIP, bounded JSON/JSONL
structures, and the existing strict canonical six-member ZIP contract. ZIP contents
are never extracted to disk. Missing required no-follow or ACL-inspection capability
fails closed; no Linux ACL inspection is claimed.

### 3. Reuse the established package contract and codebook binding

Each capture independently passes the existing resource preflight and strict native
package loader without an external expectation. This verifies canonical closed JSON
and JSONL, manifest self-digest, member sizes and byte digests, exact candidate and
plan relations, deterministic review ZIP, and the negative authority fields. Only
after that validation does the manifest select a supported installed codebook
version; it grants no authority. That codebook is securely captured, compared to the
embedded packet codebook, and finally recaptured. Comparator-specific observations
bind the fixed installed `references` directory and codebook leaf before and after
each read; final seals detect rebinding after the last recapture. The existing
codebook helper and other consumers keep their established behavior.

The repeated package additionally must match both separately supplied expectations:
its recomputed manifest self-digest equals `--expected-manifest-sha256`, and the raw
ZIP bytes hash equals `--expected-independent-review-packet-sha256`. A syntactically
valid disagreement is a mismatch, never a replacement expectation. Both packages
may use different supported codebook versions only long enough to be independently
classified; they cannot byte-match, and each installed version is captured and
recaptured independently without arbitrary path search.

Success also requires raw byte-for-byte equality of all seven corresponding files,
not only equal digests, parsed objects, or selected fields.

### 4. Hold descriptors, bound memory, and fully recapture

The implementation reuses the profile-driven descriptor machinery from the existing
comparators. It uses no-follow stat/open-at through the held parent and directory
descriptors; verifies device, inode, type, mode, owner, group, link count, size,
nanosecond modification/change times, ACL, and path binding around every bounded
read; compares bytes in bounded chunks; and rejects cross-package inode aliases.

Bundles are materialized and validated sequentially so two maximum-size ZIPs are not
retained together. After semantic and raw equality checks, both directories and all
needed installed codebooks are fully recaptured, leaf and supplied paths rebound to
the held identities, and raw equality repeated. Any drift, failed repeated
inspection, resource failure, or unconfirmed close yields
`comparison_input_changed` or another unreadable state; no initial snapshot can
survive as `match`.

### 5. Emit a closed value-free four-state report

Every handler outcome emits exactly one canonical JSON line with root keys
`schema_version`, `artifact_type`, `status`, `recovery_comparison_valid`,
`reason_codes`, `checks`, `remediation`, and `scope`. `artifact_type` is
`native_audit_bundle_comparison_report`; status priority is
`unreadable > invalid > mismatch > match`; exit codes are respectively `2`, `2`,
`3`, and `0`.

`checks` has exactly these twenty ordered members:

```text
common_parent_valid
directories_distinct
uncertain_bundle_readable
repeated_bundle_readable
uncertain_bundle_private
repeated_bundle_private
uncertain_inventory_exact
repeated_inventory_exact
expected_manifest_sha256_valid
expected_independent_review_packet_sha256_valid
uncertain_bundle_contract_valid
repeated_bundle_contract_valid
uncertain_installed_codebook_readable
repeated_installed_codebook_readable
uncertain_installed_codebook_binding_valid
repeated_installed_codebook_binding_valid
repeated_external_manifest_digest_valid
repeated_external_independent_review_packet_digest_valid
audit_bundle_file_bytes_equal
final_recapture_valid
```

Reasons are deduplicated and ordered by state priority:

```text
uncertain_audit_bundle_unreadable
repeated_audit_bundle_unreadable
uncertain_installed_codebook_unreadable
repeated_installed_codebook_unreadable
comparison_input_changed
comparison_topology_invalid
uncertain_audit_bundle_privacy_invalid
repeated_audit_bundle_privacy_invalid
uncertain_audit_bundle_inventory_invalid
repeated_audit_bundle_inventory_invalid
expected_manifest_sha256_invalid
expected_independent_review_packet_sha256_invalid
uncertain_audit_bundle_artifact_contract_invalid
repeated_audit_bundle_artifact_contract_invalid
uncertain_installed_codebook_binding_mismatch
repeated_installed_codebook_binding_mismatch
external_manifest_digest_mismatch
external_independent_review_packet_digest_mismatch
audit_bundle_directory_bytes_mismatch
```

Fixed remediation codes, in order, are `check_local_read_access`,
`preserve_and_stop`, `use_safe_complete_siblings`,
`retain_successful_repeat_anchors`, `use_exact_installed_codebook`,
`administrator_quarantine`, and `investigate_without_selection`. The last route
preserves differing packages for separate investigation and explicitly neither
selects one nor authorizes another repeat.

The report contains only closed enums, booleans/null, and fixed Russian remediation.
It never exposes paths, basenames, digest values, candidate IDs, counts, sizes,
device/inode coordinates, timestamps, codebook version, contents, exceptions, errno,
or environment. Its fixed scope says the comparison is technical only; original
eligibility and durability are unverified; normal repeat return and both external
anchor provenances are unauthenticated; the source workspace was not reverified;
input provenance is unauthenticated; no recovery action or result selection is
authorized; downstream use is not authorized; consumer revalidation remains
required; and no reviewer authentication, publication, legal-readiness, or filing
authority is created.

### 6. Preserve state precedence and administrator routes

Unreadable covers path/read/inspection/codebook/ACL capability failure, bounded
resource rejection, memory/recursion failure, drift, recapture, or close uncertainty.
Invalid covers stable syntax, topology, privacy, inventory, canonical/ZIP/closed
contract, or codebook-binding violations. Mismatch is reserved for syntactically
valid external anchors that disagree or two independently valid packages whose raw
files differ. Match requires all checks true.

Input drift or topology/privacy/inventory/contract faults suppress any suggestion to
repeat and retain only preserve/administrator guidance. Anchor or raw-byte mismatch
may recommend investigation without selection only when no administrator-only fault
was observed; it never authorizes a new repeat. A short or interrupted stdout
write/flush returns code `2` without stderr or exception text and is never retried
or followed by a second report. This containment belongs only to the new handler;
the shared writer and legacy handlers remain unchanged.

## Risks / Trade-offs

- Requiring two external hashes adds one copy/paste value, but preserves both
  downstream trust boundaries already presented by the producer.
- Full recapture costs another linear read of private packages, but closes mutable
  name and in-place rewrite races.
- Rejecting cross-device/bind-mount layouts narrows portability, but makes the one
  held-parent containment claim auditable.
- The command cannot authenticate history; this limitation is explicit rather than
  encoded as an unsafe recovery token inferred after the fact.
