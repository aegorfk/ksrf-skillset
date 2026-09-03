# Change: Pin bundled libraries in KSRF runtime launchers

## Why

The four portable Python launchers currently prepend their bundled `lib/`
directory only when its exact path is absent from `sys.path`. If a user already
has that directory in `PYTHONPATH`, Python leaves the launcher `scripts/`
directory or another ambient package ahead of it. The two same-named launchers
then import themselves instead of their package, while the other launchers can
import an unrelated ambient `ksrf` package. A valid user environment therefore
turns documented installed commands into import failures or the wrong runtime.

## What Changes

- Make every launcher that owns a sibling `lib/` put that resolved directory at
  the front of `sys.path` before importing its package.
- Remove duplicate occurrences of that exact bundled directory while preserving
  the relative order and values of all other path entries.
- Cover both the same-name module collision and an earlier unrelated ambient
  package with real subprocess regressions.
- Preserve command tokens, help, stdout/stderr, exit codes, package contents,
  and all legal, evidence, human-review, and filing gates.
- Make no broader claim that arbitrary `PYTHONPATH` values or Python startup are
  sandboxed; this change only makes ownership of the launcher's bundled package
  deterministic after bootstrap begins.

## Impact

- Affected runtime files:
  - `ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py`
  - `ksrf-complaint-cycle/scripts/ksrf.py`
  - `ksrf-complaint-cycle/scripts/ksrf_filing_pack.py`
  - `ksrf-complaint-cycle/scripts/ksrf_setup_doctor.py`
- Affected source QA: focused subprocess launcher regressions and the existing
  full root/skill/runtime/install checks.
- User-visible benefit: installed commands continue to start from another
  working directory when `PYTHONPATH` already mentions the bundled library or
  contains another checkout with a colliding package name.
