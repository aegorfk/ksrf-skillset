import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/ksrf-argument-patterns"
SPEC = importlib.util.spec_from_file_location("check_transfer", SKILL / "scripts/check_transfer.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
LIBRARY = json.loads((SKILL / "references/transfer-methods.json").read_text())


def condition(value):
    return {"value": value, "evidence": [{"source_sha256": "a"*64, "locator": "synthetic p1", "source_role": "synthetic", "source_checked": True}]}


def request(method):
    return {"method_id": method["id"], "as_of": "2026-09-05", "mode": "prospective",
            "conditions": {**{k: condition(True) for k in method["necessary"]}, **{k: condition(False) for k in method["defeaters"]}}}


class TransferTests(unittest.TestCase):
    def test_all_methods_positive_and_every_independent_condition(self):
        self.assertEqual(len(LIBRARY["methods"]), 12)
        for method in LIBRARY["methods"]:
            with self.subTest(method=method["id"]):
                good = MODULE.assess(LIBRARY, request(method))
                self.assertEqual(good["status"], "candidate")
                self.assertFalse(good["filing_ready"])
                for key in method["necessary"]:
                    item = request(method); item["conditions"][key] = condition(False)
                    self.assertEqual(MODULE.assess(LIBRARY, item)["status"], "not_applicable")
                for key in method["defeaters"]:
                    item = request(method); item["conditions"][key] = condition(True)
                    self.assertEqual(MODULE.assess(LIBRARY, item)["status"], "blocked")
                for key in (*method["necessary"], *method["defeaters"]):
                    item = request(method); del item["conditions"][key]
                    self.assertEqual(MODULE.assess(LIBRARY, item)["status"], "needs_evidence")

    def test_evidence_cannot_be_empty_fake_or_unchecked(self):
        for evidence in (None, [], [{}], [{"source_sha256": "x", "locator": "p1"}], [None]):
            self.assertIsNone(MODULE.evidence_bound({"value": True, "evidence": evidence}))
        for value in (None, "true", 1, 0):
            self.assertIsNone(MODULE.evidence_bound(condition(value)))

    def test_future_release_and_historical_anonymization(self):
        item = request(LIBRARY["methods"][0]); item["as_of"] = "2026-09-04"
        self.assertEqual(MODULE.assess(LIBRARY, item)["status"], "blocked")
        item["as_of"] = "2027-01-01"; item["mode"] = "historical"
        self.assertEqual(MODULE.assess(LIBRARY, item)["status"], "blocked")

    def test_unknown_condition_method_and_date(self):
        item = request(LIBRARY["methods"][0]); item["conditions"]["typo"] = condition(True)
        self.assertEqual(MODULE.assess(LIBRARY, item)["status"], "blocked")
        item = request(LIBRARY["methods"][0]); item["method_id"] = "not-real"
        self.assertEqual(MODULE.assess(LIBRARY, item)["status"], "blocked")
        for date in (None, "2026-02-30", "20260905", ""):
            item = request(LIBRARY["methods"][0]); item["as_of"] = date
            self.assertEqual(MODULE.assess(LIBRARY, item)["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
