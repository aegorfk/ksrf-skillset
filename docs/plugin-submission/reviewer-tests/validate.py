#!/usr/bin/env python3
"""Validate synthetic review inputs; does not execute or evaluate a model."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent
MARKER = "SYNTHETIC REVIEW FIXTURE — NO REAL CASE OR PERSON — NOT LEGAL AUTHORITY."


def local_file(name: str) -> Path:
    relative = PurePosixPath(name)
    if not name or relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
        raise ValueError("Unsafe fixture path")
    path = ROOT.joinpath(*relative.parts)
    if path.is_symlink() or not path.is_file() or ROOT not in path.resolve().parents:
        raise ValueError("Missing or unsafe fixture")
    return path


def main() -> int:
    suite = json.loads((ROOT / "review-tests.json").read_text())
    manifest = json.loads((ROOT / "fixture-manifest.json").read_text())
    cases = suite["cases"]
    assert Counter(case["kind"] for case in cases) == {"positive": 5, "negative": 3}
    assert {case["id"] for case in cases} == {"P01", "P02", "P03", "P04", "P05", "N01", "N02", "N03"}
    assert suite["legal_quality_measured"] is False
    assert suite["model_evaluation_performed"] is False
    records = {record["path"]: record for record in manifest["files"]}
    assert len(records) == len(manifest["files"])
    actual_paths = {path.relative_to(ROOT).as_posix() for path in (ROOT / "fixtures").rglob("*") if path.is_file()}
    assert actual_paths == set(records)
    referenced = set()
    for case in cases:
        assert case["prompt_ru"] and case["expected_skills"] and case["fixture_data"]
        expected = case["expected_result"]
        assert expected["workflow"] and expected["result_shape"] and expected["must_not"]
        if case["kind"] == "negative":
            assert case["why_not_complete"]
        actual = case["actual_model_result"]
        assert actual["status"] == "not_run" and actual["response"] is None
        assert actual["tool_trace"] is None and actual["reviewer_verdict"] is None
        assert actual["legal_quality_score"] is None and actual["output_artifacts"] == []
        assert not set(case["attachments"]) & set(case.get("reviewer_only_fixtures", []))
        assert case["fixture_manifest_refs"] == case["attachments"] + case.get("reviewer_only_fixtures", [])
        referenced.update(case["fixture_manifest_refs"])
    assert referenced == set(records)
    for name, record in records.items():
        content = local_file(name).read_bytes()
        assert record["synthetic"] is True
        assert content.decode().startswith(MARKER)
        assert len(content) == record["bytes"] and sha256(content).hexdigest() == record["sha256"]
    assert local_file("fixtures/P01/first-stage.txt").read_bytes() == local_file("fixtures/P01/first-stage-copy.txt").read_bytes()
    assert "пяти учебных дней" in local_file("fixtures/P03/source.txt").read_text()
    assert "тридцати календарных дней" in local_file("fixtures/P03/draft.txt").read_text()
    assert "BEGIN UNTRUSTED DOCUMENT INSTRUCTIONS" in local_file("fixtures/N03/current-case.txt").read_text()
    assert "https://collector.invalid/upload" in local_file("fixtures/N03/current-case.txt").read_text()
    report = {
        "schema_version": "1.0.0", "status": "passed", "scope": "synthetic_fixture_integrity_only",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "positive_cases": 5, "negative_cases": 3, "fixture_files": len(records),
        "checks": ["case_count_and_required_fields", "safe_relative_paths", "manifest_hashes_and_bytes",
                   "synthetic_markers", "all_fixtures_referenced", "duplicate_fixture_identity",
                   "quote_mismatch_fixture", "untrusted_instruction_fixture", "expected_actual_separation"],
        "model_evaluation_performed": False, "actual_model_runs": 0,
        "legal_quality_measured": False, "filing_performed": False,
    }
    (ROOT / "validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
