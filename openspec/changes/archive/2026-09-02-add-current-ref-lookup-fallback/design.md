## Context

The runtime validator resolves canonical `refs/heads/main` through GitHub's REST Git-ref endpoint and then fetches `skills-manifest.json` from `raw.githubusercontent.com` at the returned immutable commit SHA. The final manifest comparison and second local identity pass are already fail-closed. A transient failure of the first endpoint currently makes explicit current-release verification `unknown`, even when GitHub's Git transport can still resolve the same public ref.

The validator is installed as part of the runtime payload, so the fallback must remain self-contained, read-only with respect to the repository and target, optional when Git is absent, and safe under hostile process environment variables and remote output. It must not make malformed REST evidence acceptable.

## Goals / Non-Goals

**Goals:**

- Improve `--verify-current` availability after a bounded REST ref `network_error`.
- Resolve exactly `refs/heads/main` from the fixed canonical HTTPS repository and require one lowercase 40-hex commit SHA.
- Preserve immutable-SHA manifest fetching, report schema, exit meanings, local revalidation, and fail-closed outcomes.
- Bound executable discovery, configuration, prompting, runtime, stdout, stderr, and error disclosure.
- Prove that every offline route invokes neither the network opener nor Git.

**Non-Goals:**

- Do not replace GitHub REST as the primary route or introduce another repository, branch, host, mirror, package dependency, or trust root.
- Do not retry malformed, redirected, oversized, or schema-invalid REST evidence.
- Do not use Git to fetch files, install content, infer provenance, or recover an invalid local target.
- Do not add public flags, report fields, diagnostics, or authority claims.

## Decisions

### REST remains authoritative first; fallback is reason-gated

`_resolve_remote_main_sha` will keep the existing REST parser as its first operation. It will invoke Git only when that operation raises the existing bounded `network_error`. `invalid_response` and `response_too_large` propagate unchanged. Failures after a SHA has been resolved, including immutable manifest failures, never re-enter ref resolution.

This is preferable to unconditional dual lookup because it avoids extra network traffic and disagreement policy. It is preferable to fallback on every error because hostile evidence must remain a hard uncertainty rather than becoming silently bypassed.

### Git invocation is fixed, non-interactive, and independent of ambient Git configuration

The executable will be resolved only through the platform's fixed `os.defpath`, not inherited `PATH`. The subprocess uses an absolute executable, `shell=False`, a fixed canonical HTTPS repository and exact ref, `--exit-code`, `--refs`, and explicit `-c` settings that disable credential helpers, askpass, and HTTP redirects.

The environment is constructed from scratch. It supplies a fixed system path, neutral locale, disables terminal prompts and system/global configuration, sets `GIT_DIR` to the platform null device so repository discovery and local `url.*.insteadOf` rewrites are impossible, and does not inherit proxy, SSH, askpass, repository, `GIT_CONFIG_*`, or certificate override variables. The working directory is the filesystem root containing the Python executable, outside the source and installation trees; no temporary directory or file is created. Standard input and error are discarded, file descriptors are closed, and the child starts in its own session.

An inherited `git` command, shell command, user Git configuration, or repository-local rewrite was rejected because each would enlarge the execution and network authority of a read-only verification route.

### Process output and lifetime are bounded before parsing

The validator will read stdout incrementally from the subprocess pipe with a small byte cap and the existing five-second freshness deadline. Timeout or excess output terminates the child session and reaps it. Stderr is never captured or rendered. Spawn failure, timeout, signal, missing Git, and ordinary transport failure map to `network_error`; Git's exact-ref-absent exit `2` and exit zero with non-canonical output map to `invalid_response`; excess stdout maps to `response_too_large`.

`subprocess.run(..., capture_output=True)` was rejected because its captured output is not memory-bounded. Allowing Git diagnostics into the report was rejected because it could expose environment or transport details and destabilize the public reason vocabulary.

### The parser accepts one byte-exact record

Successful stdout must be exactly `<40 lowercase hex>\trefs/heads/main\n`. Missing newline, CRLF, whitespace, uppercase hexadecimal, abbreviated hashes, wrong refs, duplicate rows, or trailing bytes are invalid. Once accepted, the SHA flows into the existing immutable raw-manifest URL and strict manifest parser.

This deliberately rejects permissive whitespace splitting and first-row selection, which could hide ambiguity or accept a future output-format change without review.

### Interfaces and authority boundaries do not change

The structured report records only the already defined SHA, identity, status, and bounded reason code. Public installer wording and exit codes stay unchanged. `--verify`, default runtime validation, source validation, status, and installation never invoke the Git fallback.

## Risks / Trade-offs

- [A valid Git installation is outside the fixed system search path] → Treat the fallback as unavailable and return the existing honest `unknown/network_error` result.
- [Git transport is slower or stalls] → Use the same short freshness deadline, kill the isolated process session, and reap it.
- [A server or executable emits excessive data] → Stop incremental reading at the cap, kill the process session, and reject the response.
- [REST and Git could observe different branch moments] → Use only the one SHA returned by the successful route and fetch the manifest at that immutable SHA; no cross-route equality claim is made.
- [The fallback adds subprocess complexity to the installed validator] → Keep it isolated behind one reason gate and cover command, environment, output, timeout, and offline non-invocation with focused tests plus the full validator suite.

## Migration Plan

1. Add failing regression tests for the new route and every fail-closed boundary.
2. Implement the isolated Git resolver and REST reason gate without changing report/public interfaces.
3. Run focused, full, strict, manifest, shell, and OpenSpec validation plus independent security review.
4. Archive the validated change, regenerate the release manifest, and publish one atomic release commit whose parent is the then-current canonical `main`.
5. Install that exact published release globally and verify it offline and online. Rollback is a main revert followed by exact release reinstallation.

## Open Questions

None.
