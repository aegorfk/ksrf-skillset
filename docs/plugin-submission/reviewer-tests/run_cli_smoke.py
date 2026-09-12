#!/usr/bin/env python3
"""Optional packaged TXT intake smoke. No model, setup, signing or submission."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent


def invoke(arguments: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(arguments, text=True, capture_output=True, timeout=45, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-root", required=True, type=Path)
    args = parser.parse_args()
    plugin = args.plugin_root.resolve()
    manifest_path = plugin / "distribution-manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    verify_command = [sys.executable, "-I", "-B", str(plugin / "verify.py"), "--json"]
    before = invoke(verify_command)
    if before.returncode:
        raise ValueError("Packaged integrity check failed before smoke; raw output not published")
    suite = json.loads((ROOT / "review-tests.json").read_text())
    case = next(case for case in suite["cases"] if case["id"] == "P01")
    paths = [ROOT / name for name in case["attachments"]]
    initial = {path.name: sha256(path.read_bytes()).hexdigest() for path in paths}
    wrapper = plugin / "skills/ksrf-complaint-cycle/scripts/plugin_runtime.py"
    with tempfile.TemporaryDirectory(prefix="ksrf-review-smoke-") as temporary:
        command = [sys.executable, "-I", "-B", str(wrapper), "--state-dir", str(Path(temporary).resolve() / "state"),
                   "collect", "--", *(str(path) for path in paths), "--no-ocr"]
        collected = invoke(command)
    if collected.returncode:
        raise ValueError("Packaged intake failed; raw output not published")
    payload = json.loads(collected.stdout)
    assert payload["schema"] == "ksrf.casefile.v3" and payload["document_count"] == 4
    assert len(payload["documents"]) == 4
    assert {document["name"] for document in payload["documents"]} == set(initial)
    for document in payload["documents"]:
        assert document["sha256"] == initial[document["name"]]
        assert document["text_chars"] > 0
    assert initial == {path.name: sha256(path.read_bytes()).hexdigest() for path in paths}
    after = invoke(verify_command)
    if after.returncode:
        raise ValueError("Packaged integrity check failed after smoke")
    report = {
        "schema_version": "1.0.0", "status": "passed", "scope": "packaged_txt_intake_software_smoke",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(), "case_id": "P01",
        "plugin_version": manifest["version"], "source_commit": manifest["source"]["commit"],
        "source_working_tree_modified": manifest["source"]["working_tree_modified"],
        "published_source_verified": manifest.get("published_source_verified", False),
        "distribution_manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "python_version": sys.version.split()[0],
        "command_template": ["python3", "-I", "-B", "skills/ksrf-complaint-cycle/scripts/plugin_runtime.py",
                             "--state-dir", "<temporary-state>", "collect", "--", *case["attachments"], "--no-ocr"],
        "exit_codes": {"integrity_before": before.returncode, "collect": collected.returncode,
                       "integrity_after": after.returncode},
        "collector_schema": payload["schema"], "document_count": payload["document_count"],
        "documents": [{key: document[key] for key in ("name", "sha256", "size_bytes", "text_chars")}
                      for document in payload["documents"]],
        "original_fixtures_unchanged": True,
        "raw_collector_stdout_sha256": sha256(collected.stdout.encode()).hexdigest(),
        "raw_output_saved": False,
        "raw_output_note": "Absolute local paths omitted; report preserves the observed fields above and stdout digest.",
        "classification_accuracy_measured": False, "model_evaluation_performed": False,
        "actual_model_runs": 0, "legal_quality_measured": False,
        "signing_performed": False, "payment_performed": False, "filing_performed": False,
    }
    (ROOT / "cli-smoke-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "scope", "plugin_version", "document_count", "exit_codes", "actual_model_runs")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
