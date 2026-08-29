from __future__ import annotations

from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[2]

AFFECTED_DIRECT_SKILLS = (
    "ksrf-complaint-cycle",
    "ksrf-complaint-facts-demands",
    "ksrf-rights-argument-builder",
    "ksrf-practice-authority-builder",
    "ksrf-cassation-judicial-meaning",
    "ksrf-explore-arguments",
    "ksrf-complaint-qa",
    "ksrf-formal-filing-check",
    "ksrf-echr-argumentation",
)


def test_every_direct_filing_or_practice_skill_exposes_host_attested_boundary() -> None:
    for package in AFFECTED_DIRECT_SKILLS:
        skill_file = SKILLS_ROOT / package / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8")
        assert "host-attested approval" in text, package


def test_practice_compatibility_states_are_research_only() -> None:
    reference = (
        SKILLS_ROOT
        / "ksrf-complaint-cycle"
        / "references"
        / "practice-analysis-integration.md"
    ).read_text(encoding="utf-8")
    assert "не являются filing authority" in reference
    assert "research_bundle_ready_for_central_gate" in reference
    assert "filesystem anchor не является host attestation" in reference
    assert "Не называть обычный SHA-256 электронной подписью" in reference


def test_legacy_plain_human_promotion_phrase_does_not_return() -> None:
    forbidden = "полный pack после human review даёт `implicitly_applied_proven`"
    for package in AFFECTED_DIRECT_SKILLS:
        text = (SKILLS_ROOT / package / "SKILL.md").read_text(encoding="utf-8")
        assert forbidden not in text, package


def test_behavior_eval_requires_host_attested_approval() -> None:
    evals = (
        SKILLS_ROOT / "ksrf-complaint-cycle" / "evals" / "evals.json"
    ).read_text(encoding="utf-8")
    assert "pre-existing host-attested approval" in evals
    assert "named human approval before" not in evals


def test_user_facing_corpus_promotion_does_not_offer_plain_named_approval() -> None:
    workflow = (
        SKILLS_ROOT
        / "ksrf-complaint-cycle"
        / "lib"
        / "ksrf"
        / "filing"
        / "workflow.py"
    ).read_text(encoding="utf-8")
    assert "host-attested approval точного производного материала" in workflow
    assert "именованное одобрение производного материала" not in workflow
