from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_argument_research.py"


def valid_payload() -> dict[str, object]:
    return {
        "case_id": "case-1",
        "findings": [
            {
                "finding_id": "finding-1",
                "case_id": "case-1",
                "direction": "normative",
                "thesis": "Проверяемое утверждение.",
                "source_anchor": "official-source-1",
                "locator": "p. 1",
                "relation": "supports",
                "hypothesis_ids": ["hypothesis-1"],
                "verification_status": "candidate",
                "confidence": "medium",
                "limitations": "Ограничение вывода.",
                "contains_sensitive_data": False,
            }
        ],
        "hypotheses": [
            {
                "hypothesis_id": "hypothesis-1",
                "title": "Проверяемая гипотеза",
                "status": "active",
                "normative_mechanism": "Механизм нормы.",
                "constitutional_harm": "Предполагаемый вред.",
                "review_line": "Линия проверки.",
                "supporting_finding_ids": ["finding-1"],
                "adverse_finding_ids": [],
                "falsifier": "Опровергающее наблюдение.",
                "fact_dispute_risk": "Средний.",
                "refusal_model": "Модель отказа.",
                "primary_relief": "Основное требование.",
                "narrower_relief": "Узкое требование.",
                "missing_materials": [],
            }
        ],
        "portfolio": {
            "hard_gates": {},
            "principal_hypothesis_id": None,
            "reserve_hypothesis_ids": ["hypothesis-1"],
            "experimental_hypothesis_ids": [],
            "rejected_hypothesis_ids": [],
            "dimension_comparison": {},
            "critic_findings": [],
            "human_approval": "pending",
            "approval_reason": "Ожидается решение.",
            "approved_by": None,
        },
    }


class ArgumentResearchValidatorTests(unittest.TestCase):
    def run_validator(self, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "research.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def assert_malformed_payload_is_controlled(self, payload: dict[str, object]) -> None:
        result = self.run_validator(payload)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("ERROR:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_valid_payload_remains_accepted(self) -> None:
        result = self.run_validator(valid_payload())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "OK: adaptive KSRF research artifact is valid")
        self.assertEqual(result.stderr, "")

    def test_unhashable_enums_and_ids_are_reported_without_traceback(self) -> None:
        mutations = {
            "finding_relation": ("findings", 0, "relation", []),
            "finding_verification_status": ("findings", 0, "verification_status", {}),
            "finding_confidence": ("findings", 0, "confidence", []),
            "finding_hypothesis_ids": ("findings", 0, "hypothesis_ids", [{}]),
            "hypothesis_status": ("hypotheses", 0, "status", {}),
            "supporting_finding_ids": ("hypotheses", 0, "supporting_finding_ids", [1, "finding-1"]),
            "adverse_finding_ids": ("hypotheses", 0, "adverse_finding_ids", [[]]),
            "human_approval": ("portfolio", None, "human_approval", []),
            "principal_hypothesis_id": ("portfolio", None, "principal_hypothesis_id", {}),
            "reserve_hypothesis_ids": ("portfolio", None, "reserve_hypothesis_ids", [[]]),
            "experimental_hypothesis_ids": ("portfolio", None, "experimental_hypothesis_ids", [{}]),
            "rejected_hypothesis_ids": ("portfolio", None, "rejected_hypothesis_ids", [1, "hypothesis-1"]),
        }
        for name, (section, index, field, value) in mutations.items():
            with self.subTest(name=name):
                payload = valid_payload()
                target = payload[section]
                if index is None:
                    assert isinstance(target, dict)
                    target[field] = value
                else:
                    assert isinstance(target, list)
                    assert isinstance(target[index], dict)
                    target[index][field] = value
                self.assert_malformed_payload_is_controlled(payload)


if __name__ == "__main__":
    unittest.main()
