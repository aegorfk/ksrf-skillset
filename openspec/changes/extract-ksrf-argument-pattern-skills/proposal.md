# Extract KSRF Argument Pattern Skills

## Why

The project now has a local corpus of 997 KSRF Постановления. We need to turn that corpus into reusable drafting and diagnostic workflows for new constitutional complaints and court requests.

The key product need is not a citation dump. The system should identify admissible constitutional-law argument patterns, show where those patterns appear in KSRF rulings, and tell the user what facts, lower-court acts, and automation checks are needed to support the argument in a new case.

## What Changes

- Add a corpus extraction script that reads all local KSRF ruling PDFs and produces text/index artifacts.
- Add a Codex skill `ksrf-argument-patterns` with:
  - a concise workflow;
  - a matrix of admissible constitutional-law argument families;
  - an index of KSRF Постановления where each pattern appears;
  - an automation backlog for tools that can support each pattern on new cases.
- Preserve generated corpus artifacts in `analysis_results/ksrf_argument_patterns` for review and iteration.

## Scope

In scope:

- corpus pass over local PDFs;
- drafting-oriented taxonomy;
- skill and references;
- automation ideas/spec.

Out of scope for this change:

- production lower-court practice crawler for every pattern;
- database schema changes;
- UI integration;
- LLM benchmark/evaluation pipeline.

