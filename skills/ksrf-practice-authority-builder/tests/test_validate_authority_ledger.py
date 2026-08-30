#!/usr/bin/env python3
"""Regression tests for the standalone authority-ledger validator."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    REPO_ROOT
    / "skills"
    / "ksrf-practice-authority-builder"
    / "scripts"
    / "validate_authority_ledger.py"
)


def valid_ledger() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "case_id": "case-001",
        "mode": "drafting",
        "query_profile": {
            "hypothesis_id": "H1",
            "challenged_norm": "ч. 1 ст. 15 Конституции РФ",
            "norm_version": "2024-01-01",
            "applied_meaning": "проверяемый смысл",
            "harm_mechanism": "непосредственный вред",
            "desired_remedy": "узкое устранение нарушения",
            "constitutional_rights": ["ст. 46 Конституции РФ"],
            "judicial_application_evidence_ids": ["E1"],
            "unknowns": [],
        },
        "query_log": [
            {
                "query_id": "Q1",
                "lane": "norm_and_meaning",
                "tool": "offline-fixture",
                "query": "проверяемый запрос",
                "executed_at": "2024-01-01T00:00:00Z",
                "status": "completed",
                "result_ids": ["A1"],
                "coverage_note": "локальная проверка",
            }
        ],
        "authorities": [
            {
                "authority_id": "A1",
                "hypothesis_ids": ["H1"],
                "court": "КС РФ",
                "act_type": "Постановление",
                "date": "2024-01-01",
                "number": "1",
                "case_number": None,
                "title": "Проверенный акт",
                "roles": ["constitutional_doctrine"],
                "relation": "supports",
                "proposition": "ограниченное утверждение",
                "position_summary": "краткое содержание",
                "source": {
                    "official_url": "https://example.test/act",
                    "full_text_opened": True,
                    "official_verified": True,
                    "checked_at": "2024-01-01",
                },
                "quote": {
                    "text": "",
                    "locator": None,
                    "key_quote": False,
                    "verified_against_official": False,
                },
                "transfer": {
                    "matches": ["совпадение механизма"],
                    "differences": ["иная отрасль"],
                    "norm_fit": "direct",
                    "norm_version_fit": "yes",
                    "temporal_fit": "current",
                    "remedy_fit": "direct",
                    "limit": "чего акт не доказывает",
                },
                "risks": [],
                "verification_status": "official_verified",
                "drafting_ready": True,
            }
        ],
        "adverse_pass": {
            "performed": True,
            "query_ids": ["Q1"],
            "authority_ids": ["A1"],
        },
        "drafting_blocks": [
            {
                "block_id": "B1",
                "hypothesis_id": "H1",
                "thesis": "тезис",
                "applicability_bridge": "мост применимости",
                "conclusion": "вывод",
                "adverse_response": "ответ на adverse",
                "status": "candidate",
                "authority_ids": ["A1"],
            }
        ],
        "human_approval": {
            "status": "approved",
            "approved_by": "reviewer",
            "reason": "проверка",
        },
    }


class AuthorityLedgerValidatorTests(unittest.TestCase):
    def run_validator(self, limit: object) -> tuple[subprocess.CompletedProcess[str], bytes, Path]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "authority-ledger.json"
            payload = valid_ledger()
            payload["authorities"] = copy.deepcopy(payload["authorities"])
            authority = payload["authorities"][0]
            assert isinstance(authority, dict)
            transfer = authority["transfer"]
            assert isinstance(transfer, dict)
            transfer["limit"] = limit
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            before = path.read_bytes()
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(path)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                env={"PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertEqual(before, path.read_bytes())
            return result, before, path

    def test_non_string_drafting_transfer_limits_are_controlled(self) -> None:
        for value in (None, [], {}, False, 1, 1.5):
            with self.subTest(value=value):
                result, _, _ = self.run_validator(value)
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertIn(
                    "ERROR: $.authorities[0].transfer.limit: expected string",
                    result.stderr,
                )
                self.assertNotIn("Traceback", result.stderr)

    def test_string_drafting_transfer_limit_preserves_success(self) -> None:
        result, _, _ = self.run_validator("чего акт не доказывает")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("Authority ledger is structurally valid (1 authority record(s)).", result.stdout)


if __name__ == "__main__":
    unittest.main()
