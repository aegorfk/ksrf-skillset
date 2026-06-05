---
name: ksrf-argument-patterns
description: Use when analyzing, checking, or drafting constitutional-law arguments for a Russian Constitutional Court complaint or court request using patterns extracted from KSRF Постановления; also use when deciding what lower-court practice, facts, timelines, or evidence to collect to support a new constitutional argument.
metadata:
  short-description: Build KSRF-style constitutional arguments
---

# KSRF Argument Patterns

This skill turns a new case into constitutional-law argument hypotheses grounded in the corpus of KSRF Постановления.

## Corpus

Source corpus: `/Users/aegorfk/Documents/ks_parser_lower_court_marker/ТЗ/Постановления КС РФ`

Corpus pass artifacts:

- `/Users/aegorfk/Documents/ks_parser_lower_court_marker/analysis_results/ksrf_argument_patterns/summary.json`
- `/Users/aegorfk/Documents/ks_parser_lower_court_marker/analysis_results/ksrf_argument_patterns/expanded_pattern_registry.json`
- `/Users/aegorfk/Documents/ks_parser_lower_court_marker/analysis_results/ksrf_argument_patterns/pattern_hits.json`

The corpus pass processed 997 PDFs, extracted text from 997, and had 0 text failures.

## Required Workflow

1. Identify the target norm, rights, factual harm, procedural posture, and what the ordinary courts did.
2. Read `references/pattern-matrix.md` to select all plausible argument patterns, not only the strongest one.
3. For selected patterns, read `references/decision-index.md` and cite the KSRF Постановления listed for that pattern as corpus anchors.
4. Read `references/argument-package-builder.md` and turn the selected patterns into a package:
   - primary pattern;
   - reinforcing pattern;
   - saving / constitutional-meaning pattern;
   - remedy pattern.
5. Read `references/evidence-maps.md` to convert each selected pattern into a case-specific check:
   - what must be true in the new case;
   - what documents or court acts must be collected;
   - what would falsify or weaken the pattern;
   - what lower-court automation could support it.
6. Read `references/counterargument-playbook.md` and answer the likely Secretariat objections before drafting final text.
7. Read `references/language-formulas.md` when drafting the question, demand, or requested constitutional-law meaning.
8. Use `references/constitutional-graph.md` and `references/constitutional_graph.json` when facts are known but the best pattern package is unclear.
9. Draft argument blocks in this order:
   - constitutional principle;
   - how KSRF has accepted/used this reasoning pattern;
   - how the new case matches the pattern;
   - evidence still needed;
   - answer to admissibility/counterargument risks;
   - requested constitutional meaning or remedy.

## Pattern Families

The current taxonomy has 20 admissible argument families:

- practice-split
- legal-certainty
- constitutional-meaning
- proportionality
- interest-balance
- effective-remedy
- procedural-guarantees
- equality-differentiation
- legitimate-expectations
- retroactivity
- non-mechanical-application
- liability-fairness
- property-compensation
- social-state-positive-obligation
- federalism-competence
- legislative-gap
- good-faith-abuse
- constitutional-identity-human-dignity
- international-standards
- reconsideration-execution

## Automation Ideas

When the user asks what tools to build, read `references/automation-backlog.md`.

Typical useful tools:

- lower-court practice split finder;
- norm ambiguity detector;
- proportionality worksheet;
- ignored-dovod checker;
- timeline and retroactivity checker;
- КС remedy / post-decision reconsideration planner.

## Enrichment References

- Read `references/argument-package-builder.md` to avoid one-pattern arguments and assemble primary/reinforcing/saving/remedy packages.
- Read `references/counterargument-playbook.md` before QA or final drafting.
- Read `references/evidence-maps.md` when deciding what facts, court acts, lower-court practice, or expert materials to collect.
- Read `references/language-formulas.md` when drafting the question, demand, or constitutional-law meaning.
- Read `references/constitutional-graph.md` for the portable graph overview and `references/constitutional_graph.json` when structured traversal is useful.

## Output Shape

For discussion with the user, prefer this concise shape:

```markdown
**Паттерн:** ...
**Почему допустим:** ...
**Постановления КС РФ:** ...
**Что проверить в новом деле:** ...
**Какие материалы собрать:** ...
**Автоматизация:** ...
**Контраргументы Секретариата:** ...
**Формула языка КС РФ:** ...
**Риск/слабое место:** ...
```

Do not present the registry as exhaustive legal advice. Treat it as a drafting and diagnostic map that still needs lawyer review.
