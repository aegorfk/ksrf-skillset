## Context

`urllib` receives a socket inactivity timeout, but that timeout is reset by progress. Clock checks around one blocking `read()` therefore do not establish an aggregate deadline against a slow trickle, and they do not cover DNS, connect, TLS, or header parsing as one operation.

The validator already has a parent-side monotonic subprocess runner that caps stdout, starts a separate process group, kills the group on timeout or oversize output, suppresses stderr, and performs bounded reap/handle cleanup. Reusing that boundary for fixed HTTP requests gives a real cancellation mechanism without adding a dependency.

## Goals / Non-Goals

**Goals:**

- Bound every permitted freshness HTTP attempt from before helper spawn through complete bounded response delivery.
- Ensure deadline expiry leaves no live helper or descendant able to continue network work.
- Keep every accepted URL, header, status, payload, schema, fallback, report, and exit contract unchanged.
- Preserve the existing system-CA fallback and direct no-proxy HTTPS behavior on macOS and Linux.

**Non-Goals:**

- Do not impose one shared deadline over the complete REST/Git/raw/Contents fallback chain.
- Do not add retries, caches, authentication, user-configurable URLs, proxy support, threads, signals, or third-party HTTP clients.
- Do not expose helper diagnostics, timing fields, route fields, or a new reason code.

## Decisions

### One isolated helper per fixed HTTP attempt

The parent maps the existing three internal request shapes to closed route identifiers: canonical REST ref, immutable raw manifest, and immutable Contents manifest. The helper accepts no arbitrary URL, host, header, method, output path, or mutable branch input. Raw and Contents accept only one lowercase 40-hex SHA, from which the existing exact URL is reconstructed.

The helper performs the current direct HTTPS operation and writes only successful raw response bytes to stdout. It retains the empty `ProxyHandler`, fixed CA handling, no redirects, exact final coordinate and status checks, route-specific HTTP classification, and `cap + 1` read. Strict UTF-8, duplicate-key/non-finite JSON, manifest schema, counts, and hashes remain parent-side acceptance gates.

### Parent-enforced monotonic process boundary

The helper is launched with the absolute current Python executable and current validator file using `-I -S -B`, `shell=False`, filesystem-root working directory, closed stdin, suppressed stderr, and a minimal fixed environment. No `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, credential, Python-path, or CA-override variable is inherited.

The existing bounded runner starts the process in its own process group, measures one immutable 10-second execution deadline with a private monotonic-clock callable bound to `time.monotonic()` in production, reads at most the route cap, and kills the complete group on timeout, oversize output, selector failure, or protocol failure. The first clock sample occurs before `Popen`; the runner rechecks the same deadline after process creation, after every selector wake and before reading, after every read including EOF, and after `wait()`. Equality with the deadline is late: deadline expiry wins over ready bytes, output-cap classification, and exit `0`, and partial output is discarded.

The runner owns the private process group until the leader and protocol result have been observed. On supported POSIX hosts it observes leader exit with `waitid(P_PID, ..., WEXITED | WNOHANG | WNOWAIT)`, so the zombie leader keeps its numeric PID/PGID reserved; the runner then terminates the group and only afterward reaps the leader with `Popen.wait()`. It never signals a group after reaping its leader, avoiding a stale-PGID race. This cleanup occurs before every return, including when the leader exits successfully after spawning a same-group descendant whose stdio is closed. It guarantees no live member remains in the helper process group; a descendant that deliberately escapes the group is outside this mechanism's threat model. Selector and stdout handles are then closed once. Cleanup is bounded separately and occurs before the validator returns; deadline expiry is `network_error`, while an exceeded stdout cap before the deadline remains `response_too_large`. A POSIX runtime without the required non-reaping wait primitives fails closed rather than weakening this boundary.

The child retains the existing socket timeout as defense in depth. The parent deadline, not socket progress, is authoritative and includes interpreter startup, DNS, connection, TLS, headers, and body delivery.

### Closed exit protocol

Exit `0` means stdout contains only the response bytes within the route cap. Three private fixed helper exit codes represent `network_error`, `invalid_response`, and `response_too_large`; all other nonzero, signaled, malformed, or non-byte outcomes fail closed without exposing diagnostics. The public reason vocabulary, report schema, and renderer do not change.

### Explicit test seam without weakening production

Production always uses the subprocess transport. Existing request-security tests may inject the already internal opener seam to exercise child-side URL/header/finality logic without a real network. Separate parent tests use the private process-runner seam and the private monotonic-clock seam to verify exact argv/environment/cwd/deadline/cap, deadline-before-spawn ordering, exact-boundary rejection, timeout and completed-leader cleanup, route/exit mapping, and non-invocation from offline paths. No production branch selects an inline transport by inspecting a mock or mutable opener global.

Threads were rejected because a timed-out worker cannot be killed safely and can outlive the result. Signals were rejected because they are process-global and main-thread/platform constrained. Manual nonblocking DNS/TLS/HTTP was rejected as a much larger parser and trust-surface change.

## Risks / Trade-offs

- [Python startup adds latency] → Start helpers only for explicitly requested online checks and only for routes actually used.
- [Isolated startup changes CA discovery] → Retain the explicit system certificate fallback and add direct online smoke coverage on supported hosts.
- [A helper crashes] → Treat unknown exit/protocol outcomes as bounded `network_error`, never as current evidence.
- [A same-group descendant attempts to survive its leader] → Retain group ownership and terminate the entire private process group before any result returns; explicitly do not claim containment of a descendant that deliberately calls `setsid()` to escape that group.
- [Several permitted fallbacks each consume their own deadline] → Keep each attempt bounded and preserve the existing honest fallback lattice; do not claim a single end-to-end deadline.

## Migration Plan

1. Add deterministic red tests for trickle, exact helper protocol, environment isolation, cleanup, and fallback routing.
2. Split direct fixed-route HTTP retrieval from strict JSON acceptance and add the isolated helper transport.
3. Run focused and full suites, strict source/runtime and clean-room install checks, online smoke, OpenSpec, and independent security review.
4. Archive and synchronize both modified requirements, then publish one atomic release commit on the exact current `main` parent.
5. Install and verify the exact published runtime; roll back by reverting the release commit and reinstalling its predecessor.

## Open Questions

None.
