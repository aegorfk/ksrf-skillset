from __future__ import annotations

from copy import deepcopy
import importlib.util
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_argument_research.py"


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "validate_argument_research", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


class FindingHypothesisMembershipTest(unittest.TestCase):
    def test_rejects_finding_bound_only_to_another_hypothesis(self) -> None:
        payload = self._payload(
            finding_hypothesis_ids=["H1"],
            hypothesis_references={"H1": [], "H2": ["F1"]},
        )

        self.assertIn(
            "hypotheses[1] references findings outside finding.hypothesis_ids: ['F1']",
            VALIDATOR.validate(payload),
        )

    def test_accepts_finding_bound_to_the_referencing_hypothesis(self) -> None:
        payload = self._payload(
            finding_hypothesis_ids=["H1"],
            hypothesis_references={"H1": ["F1"]},
        )

        self.assertEqual([], VALIDATOR.validate(payload))

    def test_accepts_finding_explicitly_bound_to_multiple_hypotheses(self) -> None:
        payload = self._payload(
            finding_hypothesis_ids=["H1", "H2"],
            hypothesis_references={"H1": ["F1"], "H2": ["F1"]},
        )

        self.assertEqual([], VALIDATOR.validate(payload))

    def test_rejects_referenced_finding_when_hypothesis_id_is_invalid(self) -> None:
        valid_payload = self._payload(
            finding_hypothesis_ids=["H1"],
            hypothesis_references={"H1": ["F1"]},
        )

        for invalid_hypothesis_id in (None, 7, ""):
            with self.subTest(hypothesis_id=invalid_hypothesis_id):
                payload = deepcopy(valid_payload)
                payload["hypotheses"][0]["hypothesis_id"] = invalid_hypothesis_id
                self.assertIn(
                    "hypotheses[0] references findings outside "
                    "finding.hypothesis_ids: ['F1']",
                    VALIDATOR.validate(payload),
                )

    def test_applies_membership_gate_to_adverse_references(self) -> None:
        payload = self._payload(
            finding_hypothesis_ids=["H1"],
            hypothesis_references={"H1": [], "H2": []},
        )
        payload["hypotheses"][1]["adverse_finding_ids"] = ["F1"]

        self.assertIn(
            "hypotheses[1] references findings outside finding.hypothesis_ids: ['F1']",
            VALIDATOR.validate(payload),
        )

    def _payload(
        self,
        *,
        finding_hypothesis_ids: list[str],
        hypothesis_references: dict[str, list[str]],
    ) -> dict[str, Any]:
        return {
            "case_id": "C1",
            "findings": [self._finding(finding_hypothesis_ids)],
            "hypotheses": [
                self._hypothesis(hypothesis_id, references)
                for hypothesis_id, references in hypothesis_references.items()
            ],
            "portfolio": {
                "human_approval": "pending",
                "principal_hypothesis_id": None,
                "reserve_hypothesis_ids": [],
                "experimental_hypothesis_ids": [],
                "rejected_hypothesis_ids": [],
            },
        }

    def _finding(self, hypothesis_ids: list[str]) -> dict[str, Any]:
        return {
            "finding_id": "F1",
            "case_id": "C1",
            "direction": "official_practice",
            "thesis": "Проверяемый тезис",
            "source_anchor": "evidence:E1",
            "locator": "paragraph:1",
            "relation": "supports",
            "hypothesis_ids": hypothesis_ids,
            "verification_status": "verified",
            "confidence": "high",
            "limitations": "Только в пределах проверенной гипотезы",
            "contains_sensitive_data": False,
        }

    def _hypothesis(
        self, hypothesis_id: str, supporting_finding_ids: list[str]
    ) -> dict[str, Any]:
        return {
            "hypothesis_id": hypothesis_id,
            "title": hypothesis_id,
            "status": "active",
            "normative_mechanism": "Механизм",
            "constitutional_harm": "Вред",
            "review_line": "Линия проверки",
            "supporting_finding_ids": supporting_finding_ids,
            "adverse_finding_ids": [],
            "falsifier": "Опровергающий источник",
            "fact_dispute_risk": "low",
            "refusal_model": "Модель отказа",
            "primary_relief": "Основное средство",
            "narrower_relief": "Узкое средство",
            "missing_materials": [],
        }


if __name__ == "__main__":
    unittest.main()
