import argparse
import json
import tempfile
import unittest
from pathlib import Path

from judicial_meaning.cli import (
    _validation_state,
    cmd_analyze,
    cmd_review,
    cmd_screen,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)
from judicial_meaning.collection import FixtureTransport, run_collection
from judicial_meaning.plan import freeze_plan


SKILL = Path(__file__).resolve().parents[1]
FIXTURES = SKILL / "tests" / "fixtures"


class ApprovalHashInvalidationTests(unittest.TestCase):
    def test_material_evidence_change_revokes_drafting_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            plan = json.loads((FIXTURES / "research-plan-valid.json").read_text(encoding="utf-8"))
            frozen = freeze_plan(plan, workspace)
            run_collection(
                workspace,
                plan=frozen,
                transport=FixtureTransport(FIXTURES),
                resume=False,
            )
            write_json(
                workspace / "applicant-chain.json",
                {
                    "propositions": [
                        {
                            "speaker": "court",
                            "meaning": "срок подлежит восстановлению",
                            "outcome_link": "акт отменён",
                        }
                    ]
                },
            )
            cmd_screen(argparse.Namespace(workspace=str(workspace)))
            source = next(
                record
                for record in read_jsonl(workspace / "exports" / "sources.jsonl")
                if record.get("kind") == "doc" and "срок подлежит восстановлению" in record.get("text", "")
            )
            coding = {
                "chain_id": source["chain_id"],
                "document_id": source["document_id"],
                "court_code": source["court_code"],
                "decision_date": "2024-03-07",
                "label": "core_merits",
                "speaker": "court",
                "proposition": "Спорный срок подлежит восстановлению.",
                "quote": "срок подлежит восстановлению",
                "quote_locator": "абзац fixture",
                "quote_verified": True,
                "full_text_reviewed": True,
                "norm_edition_id": "edition-fixture",
                "material_facts": ["уважительная причина"],
                "material_facts_group": "fixture",
                "reasoning_to_outcome": "Этот мотив повлёк отмену.",
                "alternative_grounds": [],
                "remedy": "отмена",
                "reading_family": "restore",
                "relation": "supports",
                "coder": "fixture-reviewer",
                "codebook_version": "1.0",
                "human_review": "approved",
            }
            write_jsonl(workspace / "coding-decisions.jsonl", [coding])
            cmd_analyze(argparse.Namespace(workspace=str(workspace)))
            self.assertEqual([], read_jsonl(workspace / "thesis-candidates.jsonl"))
            adverse_template = read_json(workspace / "adverse-review.json")
            self.assertFalse(adverse_template["completed"])
            result_run_id = adverse_template["run_id"]
            self.assertTrue(result_run_id)

            adverse_input = workspace / "adverse-input.json"
            write_json(
                adverse_input,
                {
                    "schema_version": "1.0",
                    "run_id": result_run_id,
                    "lanes": ["adverse"],
                    "completed": True,
                    "queries": ["отказ в восстановлении срока"],
                    "reviewer": "fixture-reviewer",
                    "results": [],
                    "limitations": ["Ноль находок относится только к раскрытому корпусу."],
                },
            )
            cmd_review(
                argparse.Namespace(
                    workspace=str(workspace),
                    thesis_file=None,
                    adverse_file=str(adverse_input),
                    decision="evidence_reviewed",
                    reviewer="fixture-reviewer",
                    adverse_complete=True,
                    coverage_complete=True,
                    notes="fixture evidence review",
                )
            )
            cmd_analyze(argparse.Namespace(workspace=str(workspace)))
            candidates = read_jsonl(workspace / "thesis-candidates.jsonl")
            candidates[0]["normative_defect_bridge"] = (
                "Текст нормы допускает несовместимые исходозначимые прочтения в сопоставимых делах."
            )
            candidates[0]["human_review"] = "approved"
            thesis_input = workspace / "thesis-reviewed.jsonl"
            write_jsonl(thesis_input, candidates)
            cmd_review(
                argparse.Namespace(
                    workspace=str(workspace),
                    thesis_file=str(thesis_input),
                    adverse_file=str(adverse_input),
                    decision="approved",
                    reviewer="fixture-reviewer",
                    adverse_complete=True,
                    coverage_complete=True,
                    notes="fixture approval",
                )
            )
            self.assertTrue(_validation_state(workspace)["candidate_approved"])
            coding["proposition"] = "Материально изменённая позиция."
            write_jsonl(workspace / "coding-decisions.jsonl", [coding])
            state = _validation_state(workspace)
            self.assertFalse(state["approval_hashes_match"])
            self.assertFalse(state["human_approved"])
            self.assertFalse(state["candidate_approved"])


if __name__ == "__main__":
    unittest.main()
