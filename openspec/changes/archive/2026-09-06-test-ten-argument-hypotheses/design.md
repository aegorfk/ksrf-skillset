## Context and scope

This is experiment `ksrf-ten-method-development-v1`, distinct from the existing outcome-blind full-complaint protocol. The real records were used in method development and may reveal outcomes. Results are retrospective model diagnostics, not held-out prediction, independent human legal assessment, statistical effect estimates or evidence that a complaint will be accepted. Frozen diagnostic-only corpus records remain excluded.

## Frozen hypotheses (run in this order)

| ID | One candidate intervention relative to the common task |
| --- | --- |
| H1 | Identify the minimum material premise distinguishing two strong readings and test both outcomes of that premise. |
| H2 | Accept the strongest adverse position conditionally, preserve its source role and conditions, and derive the surviving request. |
| H3 | Isolate the incremental contribution and burden of the disputed element while retaining the supported goal; test a feasible alternative. |
| H4 | Freeze the proposed general rule and relevance conditions, then test inclusion and exclusion against distinct real records; mark incomparable records and untested boundaries. |
| H5 | Separate the legally necessary guarantee from the preferred mechanism and test lawful substitutes for effectiveness. |
| H6 | Split norm × request × consequence × application-source rows; prevent a conclusion from transferring to an unsupported neighbouring row. |
| H7 | Identify the exact rule assigning the consequence of uncertainty; distinguish not proved, opposite proved and proof unavailable. |
| H8 | Preserve the logical signature of the source: actor, negation, automaticity, necessary/sufficient conditions, exceptions and scope. |
| H9 | Separate validity, application and continuing-consequence time rows; test whether removing present validity actually defeats the argument. |
| H10 | Remove another applicant's dossier and recheck each individual factual/application premise, retaining genuinely common law only. |

H6–H10 are narrow incremental operations on existing coverage, not claims of wholly new doctrine. A baseline may already implement them. Null effects must not trigger gratuitous runtime text growth.

## Inputs and comparison

Freeze ten private packets before any trial. Each contains one neutral task, exact source bytes with SHA-256, source role, page/section locators, known coverage gaps and one intervention. Baseline and candidate receive identical bounded real-source extracts, common safeguards, task and output budget; candidate receives only the registered intervention. They do not receive a gold answer, expected failure, judge prompt or hidden label. Use the user's existing authenticated Codex configuration (`gpt-6-astra`, `xhigh`, `priority`) explicitly when isolation ignores config. No new provider or production-prompt labels. Fix a per-call timeout and do not rerun legal failures to select a better answer; transport/infrastructure failures may be retained and retried explicitly.

Produce 20 outputs in H1–H10 order, with one writer and atomic per-call checkpoints. Prompt/source/model/tool hashes bind each receipt. Private records include usage, latency and nullable cost; unknown price is not zero. CLI responses are not proof of independent network isolation unless a sandbox receipt confirms it. Disable tools/network for text-only trials when supported; otherwise enforce the documented sandbox and report its scope honestly.

## Review and metrics

Fresh model review receives raw source packet, neutral task and concealed A/B outputs but not intervention, hypothesis expected answer or arm key. Review scores source fidelity, inferential validity, strongest-objection handling, lawful/effective relief and calibrated uncertainty on 0–2 scales, citing exact supporting or contradicting source locators. A material invented fact, party-to-court promotion, unsupported legal necessity or remedy outside established competence is a critical defect. Missing applicable source coverage is unknown rather than an invented score. Review the reversed A/B order in a second fresh call; disagreement/order sensitivity defeats a robust preference claim. This same-model panel is not independent human review.

DeepEval uses explicit custom BaseMetric/LLMTestCase diagnostics to validate source-ID/locator integrity and consume the frozen source-bound judge dimensions. No metric silently invokes another provider/model. Mechanical locator integrity is not semantic grounding. Candidate is provisionally promising only if both orderings prefer it with no new critical defect; ties, order disagreements, baseline wins and insufficient coverage are reported separately. One pair per hypothesis cannot establish population effect or legal validity.

## Observability and privacy

Before model calls, authenticate a Langfuse experiment trace write and read it back from the local service. Record every generation/review using a unique experiment namespace and private in-process credentials. Log hashes and non-reconstructive metadata rather than source texts, case-identifying outputs or credentials. Flush and read back generation/score metadata; unavailable trace/readback means incomplete instrumentation, never a completed quality experiment. Source PDFs, images, extracts, prompts and model answers stay in a permission-restricted private run directory outside Git. Public results contain only aggregate counts, method-level findings and provenance hashes that cannot reconstruct documents.

## Validation and completion

Add offline tests for packet validation, exact arm separation, concealed/reversed review, failure retention, nullable price and non-semantic metric boundaries. Run live preflight, all ten pairs and both reviews where infrastructure permits, then DeepEval and Langfuse readback. Audit failures before any runtime edit. Validate and archive OpenSpec, run release checks, regenerate the manifest, publish one atomic commit and verify live SHA. Report exact incomplete stages if blocked; never claim ten tests from a source audit alone.
