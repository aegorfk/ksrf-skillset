from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path
from typing import Any


VALIDATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "validate_authority_ledger.py"
)
SPEC = importlib.util.spec_from_file_location("validate_authority_ledger", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR_MODULE)


def _valid_drafting_ledger(authority_hypothesis_ids: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "case_id": "case-hypothesis-binding",
        "mode": "drafting",
        "query_profile": {
            "hypothesis_id": "H1",
            "challenged_norm": "ст. X",
            "norm_version": "V1",
            "applied_meaning": "meaning",
            "constitutional_rights": ["ст. 46"],
            "harm_mechanism": "harm",
            "judicial_application_evidence_ids": ["E1"],
            "desired_remedy": "remedy",
            "unknowns": [],
        },
        "query_log": [
            {
                "query_id": "Q1",
                "lane": "adverse",
                "tool": "offline",
                "query": "adverse",
                "executed_at": "2026-09-01T00:00:00+03:00",
                "status": "completed",
                "result_ids": ["A1"],
                "coverage_note": "bounded fixture",
            }
        ],
        "authorities": [
            {
                "authority_id": "A1",
                "hypothesis_ids": authority_hypothesis_ids,
                "court": "КС РФ",
                "act_type": "Постановление",
                "date": "2026-01-01",
                "number": "1-П",
                "case_number": None,
                "title": "fixture",
                "roles": ["constitutional_doctrine"],
                "relation": "supports",
                "proposition": "proposition",
                "position_summary": "summary",
                "source": {
                    "casuslegal_url": None,
                    "official_url": None,
                    "full_text_opened": True,
                    "official_verified": False,
                    "checked_at": "2026-09-01",
                },
                "quote": {
                    "text": "",
                    "locator": None,
                    "key_quote": False,
                    "verified_against_official": False,
                },
                "transfer": {
                    "matches": ["mechanism"],
                    "differences": [],
                    "norm_fit": "direct",
                    "norm_version_fit": "yes",
                    "temporal_fit": "current",
                    "remedy_fit": "direct",
                    "limit": "bounded fixture",
                },
                "risks": [],
                "verification_status": "full_text_opened",
                "drafting_ready": True,
            }
        ],
        "adverse_pass": {
            "performed": True,
            "query_ids": ["Q1"],
            "authority_ids": [],
            "no_result_note": "no adverse authority in bounded fixture",
        },
        "drafting_blocks": [
            {
                "block_id": "B1",
                "hypothesis_id": "H1",
                "authority_ids": ["A1"],
                "thesis": "thesis",
                "applicability_bridge": "bridge",
                "conclusion": "conclusion",
                "adverse_response": "response",
                "status": "ready",
            }
        ],
        "human_approval": {
            "status": "approved",
            "approved_by": "fixture-reviewer",
            "reason": "fixture approval",
        },
    }


class AuthorityLedgerHypothesisBindingTests(unittest.TestCase):
    def _validate(
        self,
        ledger: dict[str, Any],
        *,
        require_drafting: bool = True,
    ) -> list[str]:
        validator = VALIDATOR_MODULE.Validator(
            public=False,
            require_drafting=require_drafting,
        )
        validator.validate(ledger)
        return validator.errors

    def test_rejects_authority_not_bound_to_block_hypothesis(self) -> None:
        errors = self._validate(_valid_drafting_ledger(["H2"]))

        self.assertTrue(
            any(
                error.startswith("$.drafting_blocks[0].authority_ids[0]:")
                and "'A1'" in error
                and "'H1'" in error
                for error in errors
            ),
            errors,
        )

    def test_accepts_multi_hypothesis_authority_containing_block_hypothesis(
        self,
    ) -> None:
        errors = self._validate(_valid_drafting_ledger(["H1", "H2"]))

        self.assertEqual(errors, [])

    def test_checks_every_referenced_authority(self) -> None:
        ledger = _valid_drafting_ledger(["H1"])
        second = copy.deepcopy(ledger["authorities"][0])
        second["authority_id"] = "A2"
        second["hypothesis_ids"] = ["H2"]
        ledger["authorities"].append(second)
        ledger["drafting_blocks"][0]["authority_ids"] = ["A1", "A2"]

        errors = self._validate(ledger)

        self.assertTrue(
            any(
                error.startswith("$.drafting_blocks[0].authority_ids[1]:")
                and "'A2'" in error
                and "'H1'" in error
                for error in errors
            ),
            errors,
        )

    def test_unknown_authority_keeps_existing_error(self) -> None:
        ledger = _valid_drafting_ledger(["H1"])
        ledger["drafting_blocks"][0]["authority_ids"] = ["missing"]

        errors = self._validate(ledger)

        self.assertEqual(
            errors,
            [
                "$.drafting_blocks[0].authority_ids[0]: "
                "unknown authority id 'missing'"
            ],
        )

    def test_research_without_drafting_blocks_remains_valid(self) -> None:
        ledger = _valid_drafting_ledger(["H1"])
        ledger["mode"] = "research"
        ledger["authorities"][0]["drafting_ready"] = False
        ledger["drafting_blocks"] = []

        errors = self._validate(ledger, require_drafting=False)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
