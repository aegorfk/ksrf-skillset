import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from judicial_meaning.analysis import (
    ALLOWED_CONCLUSIONS,
    analyze_reviewed_chains,
    build_thesis_candidates,
    screen_text,
    validate_coding_against_text,
    validate_coding_record,
    validate_thesis_candidate,
    validate_thesis_readiness,
)


SKILL = Path(__file__).resolve().parents[1]


class AnalysisAndCliTests(unittest.TestCase):
    def test_screening_uses_plan_lanes_not_a_built_in_subject(self):
        lanes = {
            "exact_norm": ["статья 10"],
            "synonyms": ["разумный срок"],
            "mechanisms": ["формальный отказ"],
            "opposite_readings": ["срок восстановлен"],
            "other_grounds": [],
            "later_authority": [],
        }
        matches = screen_text("Суд восстановил разумный срок, хотя ранее был формальный отказ.", lanes)
        self.assertEqual({"synonyms", "mechanisms"}, {m["lane"] for m in matches})

    def test_coding_requires_full_text_quote_speaker_and_outcome_link(self):
        record = {
            "chain_id": "chain-1",
            "document_id": "document-1",
            "label": "core_merits",
            "speaker": "court",
            "proposition": "Норма допускает восстановление срока.",
            "quote": "срок подлежит восстановлению",
            "quote_locator": "абзац 12",
            "quote_verified": True,
            "full_text_reviewed": True,
            "norm_edition_id": "edition-1",
            "reasoning_to_outcome": "Этот вывод повлёк отмену определения.",
            "material_facts": ["срок пропущен по уважительной причине"],
            "alternative_grounds": [],
            "remedy": "отмена",
            "reading_family": "reading-a",
            "relation": "supports",
            "coder": "reviewer-1",
            "codebook_version": "1.0",
            "human_review": "approved",
        }
        self.assertEqual([], validate_coding_record(record))
        self.assertEqual(
            [],
            validate_coding_against_text(record, "Суд указал: срок подлежит восстановлению. Определение отменено."),
        )
        self.assertTrue(validate_coding_against_text(record, "Такой цитаты в документе нет."))
        record["speaker"] = "party"
        self.assertTrue(validate_coding_record(record))

    def test_analysis_counts_independent_chains_and_can_find_split(self):
        records = [
            {"chain_id": "a", "reading_family": "wide", "relation": "supports", "human_review": "approved"},
            {"chain_id": "a", "reading_family": "wide", "relation": "supports", "human_review": "approved"},
            {"chain_id": "b", "reading_family": "narrow", "relation": "adverse", "human_review": "approved"},
        ]
        result = analyze_reviewed_chains(records, coverage_status="closed_official_population_observed")
        self.assertEqual(2, result["independent_chain_count"])
        self.assertEqual("material_split_candidate", result["status"])
        self.assertIn(result["status"], ALLOWED_CONCLUSIONS)

    def test_consistent_reading_is_bounded_to_observed_corpus(self):
        records = [
            {"chain_id": "a", "reading_family": "wide", "relation": "supports", "human_review": "approved"},
            {"chain_id": "b", "reading_family": "wide", "relation": "supports", "human_review": "approved"},
        ]
        closed = analyze_reviewed_chains(records, coverage_status="closed_official_population_observed")
        incomplete = analyze_reviewed_chains(records, coverage_status="observed_corpus_only")
        self.assertEqual("corroborated_observed_corpus", closed["status"])
        self.assertEqual("insufficient_coverage", incomplete["status"])

    def test_temporal_circuit_and_fact_sensitive_divergence_are_separate(self):
        temporal = [
            {"chain_id": "a", "reading_family": "wide", "relation": "supports", "human_review": "approved", "decision_date": "2020-01-01", "court_code": "1kas", "norm_edition_id": "e1", "material_facts_group": "same"},
            {"chain_id": "b", "reading_family": "wide", "relation": "supports", "human_review": "approved", "decision_date": "2021-01-01", "court_code": "2kas", "norm_edition_id": "e1", "material_facts_group": "same"},
            {"chain_id": "c", "reading_family": "narrow", "relation": "adverse", "human_review": "approved", "decision_date": "2024-01-01", "court_code": "1kas", "norm_edition_id": "e1", "material_facts_group": "same"},
            {"chain_id": "d", "reading_family": "narrow", "relation": "adverse", "human_review": "approved", "decision_date": "2025-01-01", "court_code": "2kas", "norm_edition_id": "e1", "material_facts_group": "same"},
        ]
        self.assertEqual(
            "temporal_shift_candidate",
            analyze_reviewed_chains(temporal, coverage_status="closed_official_population_observed")["status"],
        )
        circuit = [
            {**temporal[0], "chain_id": "e", "decision_date": "2024-01-01", "court_code": "1kas", "reading_family": "wide"},
            {**temporal[1], "chain_id": "f", "decision_date": "2024-02-01", "court_code": "2kas", "reading_family": "narrow"},
        ]
        self.assertEqual(
            "circuit_divergence_candidate",
            analyze_reviewed_chains(circuit, coverage_status="closed_official_population_observed")["status"],
        )
        fact_sensitive = [
            {**circuit[0], "chain_id": "g", "court_code": "1kas", "material_facts_group": "notice_given", "reading_family": "wide"},
            {**circuit[1], "chain_id": "h", "court_code": "1kas", "material_facts_group": "no_notice", "reading_family": "narrow"},
        ]
        self.assertEqual(
            "fact_sensitive_divergence",
            analyze_reviewed_chains(fact_sensitive, coverage_status="closed_official_population_observed")["status"],
        )

    def test_cross_edition_aggregation_needs_explicit_comparability(self):
        records = [
            {"chain_id": "a", "reading_family": "wide", "relation": "supports", "human_review": "approved", "norm_edition_id": "old"},
            {"chain_id": "b", "reading_family": "narrow", "relation": "adverse", "human_review": "approved", "norm_edition_id": "new"},
        ]
        result = analyze_reviewed_chains(records, coverage_status="closed_official_population_observed")
        self.assertEqual("needs_human_resolution", result["status"])

    def test_thesis_candidate_is_built_only_from_post_corpus_result(self):
        plan = {
            "plan_sha256": "a" * 64,
            "research_questions": [{"id": "rq-1", "norm_refs": ["ст. 10 Примерного кодекса"]}],
        }
        applicant_chain = {
            "propositions": [
                {"speaker": "court", "meaning": "формальный отказ препятствует рассмотрению", "outcome_link": "требование отклонено"}
            ]
        }
        records = [
            {"chain_id": "a", "document_id": "d1", "norm_edition_id": "e1", "reading_family": "wide", "relation": "supports", "human_review": "approved"},
            {"chain_id": "b", "document_id": "d2", "norm_edition_id": "e1", "reading_family": "narrow", "relation": "adverse", "human_review": "approved"},
        ]
        self.assertEqual(
            [],
            build_thesis_candidates(
                plan, applicant_chain, records, {"status": "insufficient_coverage", "coverage_status": "observed_corpus_only"}
            ),
        )
        candidates = build_thesis_candidates(
            plan,
            applicant_chain,
            records,
            {"status": "material_split_candidate", "coverage_status": "closed_official_population_observed"},
        )
        self.assertEqual(1, len(candidates))
        self.assertEqual(["a"], candidates[0]["supportive_chain_ids"])
        self.assertEqual(["b"], candidates[0]["adverse_chain_ids"])
        self.assertFalse(candidates[0]["drafting_ready"])
        self.assertIsNone(candidates[0]["normative_defect_bridge"])

    def test_thesis_is_blocked_before_corpus_adverse_coverage_and_human_review(self):
        state = {
            "plan_frozen": True,
            "collection_complete": False,
            "coding_complete": False,
            "adverse_review_complete": False,
            "coverage_review_complete": False,
            "human_approved": False,
            "candidate_approved": False,
            "maximum_permitted_claim": "insufficient_coverage",
        }
        errors = validate_thesis_readiness(state, "Судебный хаос доказывает неконституционность нормы")
        self.assertGreaterEqual(len(errors), 5)
        self.assertTrue(any("хаос" in error.lower() for error in errors))

    def test_bounded_language_remains_blocked_even_after_counts(self):
        state = {
            "plan_frozen": True,
            "collection_complete": True,
            "coding_complete": True,
            "adverse_review_complete": True,
            "coverage_review_complete": True,
            "human_approved": True,
            "candidate_approved": True,
            "maximum_permitted_claim": "corroborated_observed_corpus",
        }
        errors = validate_thesis_readiness(state, "Вся судебная практика единообразна и закон не работает")
        self.assertTrue(errors)
        safe = validate_thesis_readiness(
            state,
            "В наблюдаемом корпусе выявлено одно из толкований; вывод ограничен раскрытым охватом.",
        )
        self.assertEqual([], safe)

    def test_stability_trend_and_law_dysfunction_boilerplate_are_blocked(self):
        state = {
            "plan_frozen": True,
            "collection_complete": True,
            "coding_complete": True,
            "adverse_review_complete": True,
            "coverage_review_complete": True,
            "human_approved": True,
            "candidate_approved": True,
            "maximum_permitted_claim": "corroborated_observed_corpus",
        }
        thesis = "Устойчивая практика за десять лет показывает тренд: закон в целом не работает."
        errors = validate_thesis_readiness(state, thesis)
        self.assertGreaterEqual(len(errors), 2)

    def test_candidate_requires_normative_bridge_and_case_meaning_before_approval(self):
        candidate = {
            "status": "corroborated_observed_corpus",
            "norm_refs": ["ст. 10 Примерного кодекса"],
            "norm_edition_ids": ["e1"],
            "applicant_case_meaning": None,
            "supportive_chain_ids": ["a"],
            "adverse_chain_ids": [],
            "coverage_status": "closed_official_population_observed",
            "limitations": ["Вывод ограничен раскрытым охватом"],
            "normative_defect_bridge": None,
            "human_review": "pending",
        }
        self.assertTrue(validate_thesis_candidate(candidate))
        candidate["applicant_case_meaning"] = "формальный отказ препятствует рассмотрению"
        candidate["normative_defect_bridge"] = "Открытый текст нормы допускает исходозначимые несовместимые прочтения в сопоставимых делах."
        candidate["human_review"] = "approved"
        self.assertEqual([], validate_thesis_candidate(candidate))

    def test_cli_help_runs_outside_skill_with_empty_pythonpath(self):
        script = SKILL / "scripts" / "judicial_meaning.py"
        with tempfile.TemporaryDirectory() as cwd:
            env = dict(os.environ)
            env["PYTHONPATH"] = ""
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                cwd=cwd,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        for command in ("intake", "ocr", "plan", "collect", "screen", "code", "analyze", "review", "validate", "export"):
            self.assertIn(command, result.stdout)

    def test_package_contains_no_project_or_service_dependencies(self):
        forbidden = (
            "import requests",
            "from requests",
            "psycopg",
            "ks_parser",
            "casuslegal",
            "firecrawl",
            "POLZA_API_KEY",
            "/Users/aegorfk",
        )
        inspected = []
        for path in list((SKILL / "scripts").rglob("*.py")) + list((SKILL / "lib").rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            inspected.append(path)
            for token in forbidden:
                self.assertNotIn(token, text, f"{token} in {path}")
        self.assertTrue(inspected)


if __name__ == "__main__":
    unittest.main()
