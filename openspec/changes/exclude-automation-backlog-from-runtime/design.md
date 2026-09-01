# Design: Source-only automation backlog

## Context

`automation-backlog.md` целиком сформулирован как maintainer plan: каждый раздел начинается с «Сделать», «Поддерживать», «Собирать», «Проверять» или «Строить» будущий инструмент. Ни один раздел не является исполняемым контрактом. Два runtime-файла ссылаются на backlog как на «идеи инструментов» и «автоматические проверки», что смешивает план и доступный runtime.

## Decision

1. Добавить exact package-qualified identity в оба source-only contract без basename/glob overmatch.
2. Сохранить source-файл tracked и неизменным; source security и reverse-sync preservation остаются release blockers.
3. Заменить runtime-backlinks:
   - `ksrf-live-argument-patterns.md` ведёт к `argument-package-builder.md`, `evidence-maps.md` и исполняемым QA skills;
   - `ksrf-court-request-motion/SKILL.md` ведёт к `pattern-matrix.md`, `evidence-maps.md` и собственному `workflow-reference.md`, не подменяя маршрут ходатайства проверками индивидуальной жалобы.
4. Не создавать новый «сокращённый backlog»: пользователю нужны готовые routes, а не каталог будущих функций.

## Ownership map

| Backlog item | Classification | Retained owner or disposition |
|---|---|---|
| `practice-split` | user method, proposed automation | `evidence-maps.md` — practice split map |
| `legal-certainty` | user method, proposed automation | `evidence-maps.md` — legal-certainty map |
| `constitutional-meaning` | user method, proposed automation | `evidence-maps.md` — constitutional-meaning map |
| `proportionality and interest-balance` | user method, proposed automation | `evidence-maps.md` — proportionality and balance maps |
| `effective-remedy and procedural-guarantees` | user method, proposed automation | `evidence-maps.md` — remedy/procedural maps |
| `legitimate-expectations and retroactivity` | user method, proposed automation | `evidence-maps.md` — expectations/retroactivity maps |
| `non-mechanical-application and liability-fairness` | user method, proposed automation | `evidence-maps.md` — individualization/fairness maps |
| `property-compensation` | user method, proposed automation | `evidence-maps.md` — property-compensation map |
| `reconsideration-execution` | user method, proposed automation | `evidence-maps.md`; `offline-practice-core.md` — execution audit |
| `complaint-methodology-gate` | duplicated future checker | `ksrf-case-triage`; `ksrf-complaint-cycle`; `ksrf-formal-filing-check` |
| `secretariat-return-precheck` | duplicated future checker | `ksrf-complaint-qa`; `ksrf-formal-filing-check` |
| `constitutional-record-preservation-checker` | duplicated future checker | `ksrf-complaint-cycle`; `evidence-maps.md` |
| `complaint-attachments-checker` | duplicated future checker | `ksrf-formal-filing-check` |
| `ksrf-publication-radar` | maintainer/discovery automation | source-only plan; `position-retrieval-architecture.md` preserves official-source discovery route |
| `telegram-practice-claim-validator` | maintainer ingestion automation | source-only plan; `ksrf-live-argument-patterns.md` preserves claim-level source boundary |
| `bill-history-passport-builder` | mixed future automation | source-only plan; `offline-practice-core.md` and `source-proof-impact-patterns.md` preserve the passport method |
| `academic-training-source-ingestor` | maintainer ingestion automation | source-only plan; `source-authority-and-route.md` preserves training-only rule |
| `institutional-currentness-checker` | user method, proposed automation | `offline-practice-core.md` — institutional currentness |
| `course-transcript-methodology-ingestor` | maintainer ingestion automation | source-only plan; `source-authority-and-route.md` preserves transcript boundary |
| `complaint-qa-assertion-ledger` | duplicated future checker | `brief-trace-and-citation-qa.md` — assertion/evidence trace |
| `secretariat-red-team-simulator` | duplicated future checker | `ksrf-complaint-qa`; `counterargument-playbook.md` |
| `complaint-argument-scoring-rubric` | maintainer scoring proposal | intentionally not transferred: `ksrf-complaint-qa` forbids scalar score as legal readiness |
| `ksrf-skill-eval-loop` | maintainer evaluation plan | source `evals/`, tests and `position-retrieval-architecture.md` release boundary; never user runtime |

## Verification

- RED must prove exact exclusion, stale installed removal, reverse-sync byte preservation, portable/canonical parity and no overmatch for same basename in another package or similar basename in the same package.
- Source validation must continue scanning the backlog for secrets, local paths, symlinks and complaint-like artifacts.
- Clean-room runtime must contain neither the file nor its basename in user-facing Markdown/JSON; the portable validator may retain the exact policy literal.
- Every replacement route must exist inside the installed payload and the ownership map receives independent semantic review.
- Manifest regeneration must record exact final counters and hashes from frozen base.

## Risks and controls

- **Loss of a useful checklist.** Controlled by the complete ownership map and route-existence tests; duplicated ideas remain in executable skills/references.
- **False claim that planned automation exists.** Reduced by routing users only to shipped skills and references.
- **Overbroad Markdown exclusion.** Controlled by exact package-qualified equality and two no-overmatch controls.
- **Source-only file escapes security checks.** Controlled by dedicated canonical and portable source-profile tests.
- **Stale global copy survives.** Controlled by install test and clean-room/global exact tree validation.
