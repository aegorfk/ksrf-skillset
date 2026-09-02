# Enforce a hard freshness HTTP deadline

## Why

Current-release verification limits each socket operation, but a peer can keep a response alive indefinitely by delivering small fragments before every inactivity timeout. That makes an explicitly read-only check operationally unbounded even though its response size is capped. Each permitted freshness HTTP attempt needs one parent-enforced wall-clock boundary that covers process startup, DNS, TCP/TLS, headers, and the complete bounded body.

## What Changes

- Execute each fixed freshness HTTP route in an isolated Python helper process selected only by a closed route identifier and, where required, one validated immutable SHA.
- Bound the helper from the parent with the existing monotonic, output-capped process runner; kill its process group and perform bounded cleanup when the deadline, output cap, or process protocol is violated.
- Run the helper with isolated Python startup, a minimal environment, no ambient proxy discovery, no shell, no stdin, and no diagnostic stream exposed to the report.
- Preserve all current URL, header, redirect, status, byte-cap, strict JSON, schema, SHA-pinning, fallback, local-race, report, wording, and exit-code behavior.
- Classify an aggregate HTTP deadline as the existing bounded `network_error`: REST may use Git once, raw may use Contents once, and Contents remains terminal.

## Impact

- A continuously trickling endpoint can no longer hold `--verify-current` indefinitely.
- Offline validation, status, installation, runtime files, and public report shape remain unchanged.
- Online verification pays one short isolated-process startup per actually used HTTP route.
