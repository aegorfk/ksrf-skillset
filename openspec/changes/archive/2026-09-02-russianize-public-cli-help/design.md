## Context

`doctrine_research.py` and `validate_authority_ledger.py` are invoked from their owning `SKILL.md` files. Their public `--help` output is partly English because both use the default `argparse.ArgumentParser`; doctrine also exposes an undocumented `--offline-fixtures` test switch in that help.

## Goals / Non-Goals

**Goals:**

- Make root and doctrine-subcommand help understandable in Russian.
- Keep executable command and option tokens stable.
- Keep stdout/stderr placement and exit code `0` for every help route.
- Hide the test-only fixture switch from help while preserving its callable behavior.
- Verify the exact installed runtime rather than only source literals.

**Non-Goals:**

- Do not translate machine identifiers, JSON keys, provider names, or filesystem values.
- Do not remove the fixture path or alter search/auth/provenance behavior.
- Do not change non-help runtime error payloads in this release.
- Do not change the six other documented runtime CLI entry points in this release.
- Do not impose a global word-based language detector on legal text or internal CLIs.

## Decisions

### Local bounded parser class

Each standalone entry point receives a small local `ArgumentParser` subclass. It translates only stable `argparse` help scaffolding (`usage`, `positional arguments`, `options`, and the built-in help action). Keeping the helper local avoids a new cross-skill runtime dependency.

### Explicit public descriptions

Every public doctrine subcommand and option receives a concise Russian description. Subcommand names and option tokens remain unchanged. `--offline-fixtures` uses `argparse.SUPPRESS`: tests may still invoke it, but a user is not invited into an unsupported replay harness.

### Installed-runtime forward test

A root-level test installs the canonical payload into a temporary directory, invokes both root help routes and all five doctrine subcommand help routes, and asserts exit `0`, empty stderr, required Russian anchors, stable command/option tokens, no default English scaffolding, and no fixture switch. The test also proves that the hidden switch remains registered in the parser so this release does not delete behavior.

## Risks / Trade-offs

- [String replacement drifts with Python] → Assert complete subprocess output on the supported runtime and keep replacements limited to stable headings/action text.
- [Translation renames the executable contract] → Assert exact English command and option tokens remain visible where public.
- [Fixture suppression is mistaken for removal] → Assert parser acceptance/registration separately and state the non-goal explicitly.
- [Source output differs from installation] → Run the forward test against a clean canonical installation.

## Migration Plan

1. Add red installed-runtime help tests for the two documented entry points.
2. Add the local parser helpers and Russian descriptions.
3. Run focused, full, strict source/runtime, clean-room, OpenSpec, quick-validation, shell, and independent review checks.
4. Archive, regenerate the manifest from exact live `main`, publish one atomic commit, and install the exact release.
