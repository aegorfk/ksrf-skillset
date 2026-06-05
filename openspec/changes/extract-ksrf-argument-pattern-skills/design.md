# Design

## Corpus Pass

The corpus pass is intentionally deterministic and local-first:

- source: `ТЗ/Постановления КС РФ`;
- script: `scripts/extract_ksrf_argument_patterns.py`;
- output: `analysis_results/ksrf_argument_patterns`;
- PDF text extraction: PyPDF2 first, pdfplumber fallback;
- ordering: old to new by year and ruling number.

The first pass uses marker families rather than LLM classification. This makes the output reproducible and cheap, while still giving a corpus-grounded map for later human/legal review.

## Skill Shape

One primary skill is used initially:

- `ksrf-argument-patterns`

This keeps the workflow coherent while taxonomy is still under discussion. The references are separated so the skill can later be split into narrower skills, for example:

- practice-split-finder;
- proportionality-builder;
- effective-remedy-checker;
- constitutional-meaning-drafter.

## Pattern Registry

The current registry contains 20 families:

- practice-split;
- legal-certainty;
- constitutional-meaning;
- proportionality;
- interest-balance;
- effective-remedy;
- procedural-guarantees;
- equality-differentiation;
- legitimate-expectations;
- retroactivity;
- non-mechanical-application;
- liability-fairness;
- property-compensation;
- social-state-positive-obligation;
- federalism-competence;
- legislative-gap;
- good-faith-abuse;
- constitutional-identity-human-dignity;
- international-standards;
- reconsideration-execution.

## Automation Direction

Each pattern should eventually expose a case-supporting tool, not just a drafting instruction. Examples:

- lower-court practice split finder for `practice-split`;
- norm ambiguity detector for `legal-certainty`;
- ignored-dovod checker for `effective-remedy` and `procedural-guarantees`;
- timeline checker for `legitimate-expectations` and `retroactivity`;
- individualization checker for `non-mechanical-application` and `liability-fairness`.

## Enrichment Layer

The enrichment layer turns the pattern registry into drafting infrastructure:

- argument packages: primary, reinforcing, saving, and remedial pattern combinations;
- Secretariat counterarguments: predictable admissibility objections and safer fallback framings;
- evidence maps: required facts, documents, court-act checks, falsifiers, and automation hooks per pattern;
- language formulas: reusable KSRF-style demand and constitutional-meaning formulas extracted from corpus text by deterministic regex markers;
- constitutional graph: a portable JSON/Markdown graph connecting patterns, constitutional articles, norm types, harm types, decisions, evidence maps, automation hooks, and formula families.

The first implementation uses plain JSON and Markdown rather than an external graph database. This keeps the system local-first, reviewable, and easy to import into Neo4j, SQLite, NetworkX, or another graph layer later.
