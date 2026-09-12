"""Check forward-input provenance/separation; semantic grading is independent."""
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "skills/constitutional-comparative-research/evals"


class SemanticReviewAssetTests(unittest.TestCase):
    def setUp(self):
        self.inputs = json.loads((EVALS / "semantic-review-inputs.json").read_text())
        self.rubric = json.loads((EVALS / "semantic-review-rubric.json").read_text())

    def test_case_family_identity_and_text_hashes_are_frozen(self):
        cases = self.inputs["cases"]
        self.assertEqual(len(cases), 6)
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        self.assertEqual(len({c["case_family"] for c in cases}), len(cases))
        self.assertGreaterEqual(len({c["subject"] for c in cases}), 5)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["synthetic"])
                self.assertEqual(hashlib.sha256(case["text"].encode()).hexdigest(), case["text_sha256"])
                self.assertNotEqual(case["task"].strip(), "")

    def test_forward_assets_do_not_contain_evaluator_fields(self):
        forbidden = {"criteria", "expected_output", "expectations", "decision", "evidence", "adoption", "speaker"}
        for case in self.inputs["cases"]:
            self.assertFalse(forbidden.intersection(case))
        self.assertEqual(self.rubric["access_scope"], "evaluator_only")
        self.assertEqual({c["id"] for c in self.inputs["cases"]}, {c["id"] for c in self.rubric["cases"]})

    def test_rubric_evidence_resolves_to_the_exact_input_version(self):
        inputs = {c["id"]: c for c in self.inputs["cases"]}
        for case in self.rubric["cases"]:
            source = inputs[case["id"]]
            self.assertEqual(source["text_sha256"], case["text_sha256"])
            for evidence in case["evidence"]:
                spans = [evidence, *evidence.get("adoption_evidence", [])]
                for span in spans:
                    with self.subTest(case=case["id"], start=span["char_start"]):
                        self.assertGreater(span["char_end"], span["char_start"])
                        self.assertEqual(source["text"][span["char_start"]:span["char_end"]], span["quote"])
                if evidence["speaker"] != "court" and evidence["adoption"] in {"accepted", "rejected"}:
                    self.assertTrue(evidence.get("adoption_evidence"))

    def test_source_evals_preserve_the_same_forward_materials(self):
        packaged = json.loads((EVALS / "evals.json").read_text())["evals"]
        for case, evaluation in zip(self.inputs["cases"], packaged[-6:]):
            self.assertIn(case["text"], evaluation["prompt"])
            self.assertIn(case["task"], evaluation["prompt"])
            self.assertTrue(evaluation["expectations"])
        # Negative outcomes and unknown attribution are intentional evaluation
        # targets, not missing positives or successful methodological additions.
        self.assertGreaterEqual(sum(c["decision"] == "no_change" for c in self.rubric["cases"]), 2)
        self.assertTrue(any(e["speaker"] == "unknown" for c in self.rubric["cases"] for e in c["evidence"]))


if __name__ == "__main__":
    unittest.main()
