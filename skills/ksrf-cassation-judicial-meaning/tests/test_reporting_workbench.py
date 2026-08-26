import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from judicial_meaning.reporting import derive_research_status, write_offline_report


class ReportingWorkbenchTests(unittest.TestCase):
    def test_derived_status_is_russian_and_fail_closed(self):
        incomplete = derive_research_status(
            {
                "plan_frozen": True,
                "collection_complete": False,
                "coding_complete": False,
                "adverse_review_complete": False,
                "coverage_review_complete": False,
                "human_approved": False,
                "candidate_approved": False,
                "approval_hashes_match": False,
            }
        )
        self.assertEqual(incomplete["code"], "collection_incomplete")
        self.assertEqual(incomplete["label"], "Сбор корпуса не завершён")
        self.assertFalse(incomplete["drafting_ready"])
        self.assertIn("Продолжить сбор", incomplete["next_action"])

        stale = derive_research_status(
            {
                "plan_frozen": True,
                "collection_complete": True,
                "coding_complete": True,
                "adverse_review_complete": True,
                "coverage_review_complete": True,
                "human_approved": True,
                "candidate_approved": True,
                "approval_hashes_match": False,
            }
        )
        self.assertEqual(stale["code"], "approval_stale")
        self.assertIn("устарело", stale["label"].casefold())
        self.assertFalse(stale["drafting_ready"])

        realistic_stale = derive_research_status(
            {
                "approval_exists": True,
                "plan_frozen": True,
                "collection_complete": True,
                "coding_complete": True,
                "adverse_review_complete": True,
                "coverage_review_complete": True,
                "human_approved": False,
                "candidate_approved": False,
                "approval_hashes_match": False,
            }
        )
        self.assertEqual("approval_stale", realistic_stale["code"])

        ready = derive_research_status(
            {
                "plan_frozen": True,
                "collection_complete": True,
                "coding_complete": True,
                "adverse_review_complete": True,
                "coverage_review_complete": True,
                "human_approved": True,
                "candidate_approved": True,
                "approval_hashes_match": True,
            }
        )
        self.assertEqual(ready["code"], "drafting_ready")
        self.assertTrue(ready["drafting_ready"])

        case_blocked = derive_research_status(
            {
                "plan_frozen": True,
                "case_fingerprint_ready": True,
                "collection_complete": True,
                "coding_complete": True,
                "comparison_review_complete": False,
                "applicant_relation_complete": False,
                "adverse_review_complete": False,
                "coverage_review_complete": False,
                "normative_bridge_complete": False,
                "analysis_complete": False,
                "human_approved": False,
                "candidate_approved": False,
                "approval_hashes_match": False,
                "validation_current": False,
                "pending_task_counts": {"comparisons": 2},
                "stale_artifacts": ["applicant-relations.jsonl"],
                "maximum_permitted_claim": "unproven_research_question",
            }
        )
        self.assertEqual("comparison_review_incomplete", case_blocked["code"])
        self.assertEqual(2, case_blocked["pending_task_counts"]["comparisons"])
        self.assertEqual(["applicant-relations.jsonl"], case_blocked["stale_artifacts"])

        temporal_blocked = derive_research_status(
            {
                "plan_frozen": True,
                "case_fingerprint_ready": True,
                "collection_complete": True,
                "coding_complete": True,
                "comparison_review_complete": True,
                "applicant_relation_complete": True,
                "adverse_review_complete": True,
                "coverage_review_complete": True,
                "normative_bridge_complete": True,
                "analysis_complete": True,
                "temporal_analysis_complete": False,
                "human_approved": False,
                "candidate_approved": False,
                "approval_hashes_match": False,
            }
        )
        self.assertEqual("temporal_analysis_incomplete", temporal_blocked["code"])

    def test_offline_report_is_deterministic_escaped_and_drillable(self):
        model = {
            "run_id": "run-2kas-premium",
            "plan_sha256": "a" * 64,
            "evidence_sha256": "b" * 64,
            "fingerprint_sha256": "d" * 64,
            "title": "Премии <script>alert('x')</script>",
            "state": {
                "plan_frozen": True,
                "collection_complete": False,
                "coding_complete": False,
                "adverse_review_complete": False,
                "coverage_review_complete": False,
                "human_approved": False,
                "candidate_approved": False,
                "approval_hashes_match": False,
            },
            "coverage_gaps": [
                {
                    "id": "gap-2019",
                    "label": "2019: недоступная выдача",
                    "reason": "pagination_unresolved",
                }
            ],
            "findings": [
                {
                    "id": "family-proportionality",
                    "title": "Пропорциональное снижение",
                    "count": 1,
                    "denominator": 2,
                    "denominator_scope": "approved_independent_coded_chains",
                    "chains": [
                        {
                            "chain_id": "chain-88-1",
                            "court": "2 КСОЮ",
                            "decision_date": "2025-12-04",
                            "case_number": "88-25649/2025",
                            "official_url": "https://2kas.sudrf.ru/example",
                            "document_id": "doc-1",
                            "document_sha256": "c" * 64,
                            "speaker": "court",
                            "quote": "Суд указал: <script>alert(1)</script>",
                            "quote_locator": "абз. 42",
                            "relation": "supports",
                            "position_card_id": "position-1",
                            "materiality": "necessary_to_outcome",
                            "comparability": "matched",
                            "adverse_status": "reviewed_supporting",
                            "outcome": "частичное удовлетворение",
                            "remedy": "взыскание премии",
                        }
                    ],
                }
            ],
            "safe_wording": {
                "allowed": "В раскрытом корпусе наблюдается ограниченная линия.",
                "forbidden": ["Вся практика единообразна."],
                "next_steps": ["Закрыть пробел охвата за 2019 год."],
            },
        }

        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            first_root = Path(first_tmp)
            second_root = Path(second_tmp)
            first_manifest = write_offline_report(
                model,
                first_root / "research-report.html",
                first_root / "report-manifest.json",
            )
            second_manifest = write_offline_report(
                model,
                second_root / "research-report.html",
                second_root / "report-manifest.json",
            )

            first_html = (first_root / "research-report.html").read_text(encoding="utf-8")
            second_html = (second_root / "research-report.html").read_text(encoding="utf-8")
            self.assertEqual(first_html, second_html)
            self.assertEqual(first_manifest, second_manifest)
            self.assertEqual(
                first_manifest["html_sha256"],
                hashlib.sha256(first_html.encode("utf-8")).hexdigest(),
            )
            self.assertEqual(
                json.loads((first_root / "report-manifest.json").read_text(encoding="utf-8")),
                first_manifest,
            )

            self.assertNotIn("<script>alert", first_html)
            self.assertIn("&lt;script&gt;alert", first_html)
            self.assertNotIn("<script src=", first_html)
            self.assertNotIn("<link ", first_html)
            self.assertNotIn("@import", first_html)
            self.assertIn("Состояние исследования", first_html)
            self.assertIn("Пробелы охвата", first_html)
            self.assertIn("gap-2019", first_html)
            self.assertIn("chain-88-1", first_html)
            self.assertIn("approved_independent_coded_chains", first_html)
            self.assertIn("Знаменатель: 2", first_html)
            self.assertIn("Максимально допустимый вывод", first_html)
            self.assertIn("необходимо для результата", first_html)
            self.assertIn("Позиции и доказательства", first_html)
            self.assertNotIn("доказательственный drilldown", first_html)
            self.assertEqual("d" * 64, first_manifest["fingerprint_sha256"])
            self.assertIn('href="https://2kas.sudrf.ru/example"', first_html)
            self.assertFalse(list(first_root.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
