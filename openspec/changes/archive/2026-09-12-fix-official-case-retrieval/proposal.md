## Why

An applicant can provide a higher-court PDF with enough identifiers to retrieve earlier acts, yet the current entrypoints activate UID collection only when a UID is explicitly supplied. A failed search index or Python HTTP client can also be mistaken for exhaustion of official retrieval. A verified live investigation found complete official first-instance and appellate acts through court search, case cards and inventory links.

## What Changes

- Activate autonomous official retrieval from a supplied court act, case number, link or UID.
- Add a Moscow-portal reference covering independent number/UID/participant queries, related case cards, inventory dates, native DOC/RTF downloads and transport-specific failures.
- Preserve contradictory identifiers and distinguish act date from preparation/upload dates; verify identity using several independent fields.
- Require a bounded usable transport fallback and a documented retrieval disposition before requesting already published acts.
- Add synthetic scenario coverage and record a private live retrieval receipt; keep all real case material outside publication.
- Release plugin patch version 1.0.2 so the generated marketplace and installed plugin receive the same corrected skills after canonical publication.

## Capabilities

### New Capabilities
- `official-case-retrieval`: evidence-led autonomous retrieval of full court acts from identifiers available in applicant materials.

### Modified Capabilities

None. Legal admissibility and filing authority semantics do not change.

## Impact

Global ksrf-case-triage and ksrf-complaint-cycle instructions/references, the existing runtime scenario contract, plugin manifest, release manifest and this OpenSpec capability. The generated companion marketplace and local plugin installation are refreshed from the verified canonical release. No parser service, credential, deployment, network configuration or automated legal decision is added.
