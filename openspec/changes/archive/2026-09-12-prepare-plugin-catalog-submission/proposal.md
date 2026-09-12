# Prepare the applicant plugin for directory review

## Why
The published GitHub distribution is installed locally but is absent from the
universal OpenAI directory. The user explicitly requests submission to that
directory. Its skills-only upload requires shorter listing text and packaged
branding assets; portal access additionally requires verified publisher identity.

## What changes
- Prepare version 1.0.1 with directory-compatible listing fields and original
  square SVG branding, preserving all 16 skills and runtime behavior.
- Add reproducible reviewer examples, public support/privacy/terms material and
  a submission handoff that separates preparation, upload, review and publication.
- Validate the final package against documented local upload constraints, then
  publish canonical source and exact generated artifacts.
- Attempt the authorized submission in the official portal, recording its real
  state. Identity verification and unavailable portal controls remain explicit
  external dependencies rather than inferred success.

## Impact
Affected: plugin metadata/assets, package builder checks, submission documents,
focused tests and source manifest. No parser, legal methodology, filing authority
or document renderer behavior changes.
