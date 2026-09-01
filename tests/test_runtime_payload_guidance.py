from __future__ import annotations

import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class RuntimePayloadGuidanceTests(unittest.TestCase):
    def test_position_retrieval_guide_does_not_require_absent_eval_assets(self) -> None:
        guide = (
            REPO
            / "skills"
            / "ksrf-argument-patterns"
            / "references"
            / "position-retrieval-architecture.md"
        ).read_text(encoding="utf-8")

        self.assertNotIn("evals/ksrf_retrieval_golden.jsonl", guide)
        self.assertNotIn("scripts/evaluate_ksrf_retrieval.py", guide)
        self.assertIn("пользовательской runtime-установке", guide)


if __name__ == "__main__":
    unittest.main()
