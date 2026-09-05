from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator


REPO = Path(__file__).resolve().parents[1]
SKILL = "ksrf-cassation-judicial-meaning"
SOURCE_SKILL = REPO / "skills" / SKILL
SOURCE_TESTS = SOURCE_SKILL / "tests"
SCRIPT = Path(SKILL) / "scripts" / "judicial_meaning.py"

sys.path.insert(0, str(SOURCE_SKILL / "lib"))
sys.path.insert(0, str(SOURCE_TESTS))

from judicial_meaning.cli import read_json  # noqa: E402
from test_native_coding_audit_finalization_cli import (  # noqa: E402
    NativeCodingAuditFinalizationCliTests,
)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


SnapshotEntry = tuple[str, int, int, int, int, int, int, int, bytes | None]


def _snapshot_entry(path: Path, kind: str, payload: bytes | None) -> SnapshotEntry:
    metadata = path.lstat()
    return (
        kind,
        stat.S_IMODE(metadata.st_mode),
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        payload,
    )


def _tree_snapshot(root: Path) -> dict[str, SnapshotEntry]:
    result: dict[str, SnapshotEntry] = {
        ".": _snapshot_entry(root, "dir", None),
    }
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = _snapshot_entry(
                path,
                "symlink",
                os.readlink(path).encode("utf-8"),
            )
        elif path.is_dir():
            result[relative] = _snapshot_entry(path, "dir", None)
        elif path.is_file():
            result[relative] = _snapshot_entry(path, "file", path.read_bytes())
        else:
            result[relative] = _snapshot_entry(path, "other", None)
    return result


def _tree_content_snapshot(root: Path) -> dict[str, tuple[str, bytes | None]]:
    return {
        relative: (entry[0], entry[-1])
        for relative, entry in _tree_snapshot(root).items()
    }


class NativeFinalizationComparisonRuntimeParityTests(unittest.TestCase):
    maxDiff = None

    def _make_matching_finalizations(
        self,
        root: Path,
    ) -> tuple[Path, Path, str, str]:
        harness = NativeCodingAuditFinalizationCliTests(methodName="runTest")
        _, bundle, manifest_sha256 = harness._prepare_bundle(root)
        audit_import, import_result = harness._import_review(
            root,
            bundle,
            manifest_sha256,
            harness._secondary_records(bundle),
        )

        destinations = (
            root / "uncertain-finalization",
            root / "repeated-finalization",
        )
        results: list[dict[str, object]] = []
        for destination in destinations:
            completed = harness._run(
                REPO / "skills" / SCRIPT,
                harness._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    import_result["receipt_sha256"],
                    destination,
                ),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            results.append(json.loads(completed.stdout))

        self.assertEqual(results[0]["receipt_sha256"], results[1]["receipt_sha256"])
        self.assertEqual(
            _tree_content_snapshot(destinations[0]),
            _tree_content_snapshot(destinations[1]),
        )
        reliability = read_json(destinations[0] / "coding-reliability.json")
        return (
            destinations[0],
            destinations[1],
            str(results[1]["receipt_sha256"]),
            str(reliability["required_candidate_ids"][0]),
        )

    def test_source_and_clean_install_match_for_all_read_only_utf8_states(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            completed = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(installed)],
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)

            uncertain, repeated, expected, candidate_id = (
                self._make_matching_finalizations(root)
            )
            mismatch_uncertain = root / "mismatch-uncertain-finalization"
            mismatch_repeated = root / "mismatch-repeated-finalization"
            shutil.copytree(uncertain, mismatch_uncertain, copy_function=shutil.copy2)
            shutil.copytree(repeated, mismatch_repeated, copy_function=shutil.copy2)
            mismatched_file = mismatch_repeated / "resolved-review-decisions.jsonl"
            mismatched_file.write_bytes(mismatched_file.read_bytes() + b" ")

            ambient = root / "ambient"
            ambient_package = ambient / "judicial_meaning"
            ambient_package.mkdir(parents=True)
            (ambient_package / "__init__.py").write_text(
                "raise RuntimeError('ambient package must not load')\n",
                encoding="utf-8",
            )

            def arguments(first: Path, second: Path, digest: str) -> list[str]:
                return [
                    "quality",
                    "native-reliability",
                    "compare-finalizations",
                    "--uncertain-finalization-dir",
                    str(first),
                    "--repeated-finalization-dir",
                    str(second),
                    "--expected-finalization-receipt-sha256",
                    digest,
                ]

            cases = (
                ("match", arguments(uncertain, repeated, expected), 0, "match"),
                (
                    "mismatch",
                    arguments(mismatch_uncertain, mismatch_repeated, expected),
                    3,
                    "mismatch",
                ),
                (
                    "invalid",
                    arguments(uncertain, repeated, "НЕВЕРНЫЙ-SHA"),
                    2,
                    "invalid",
                ),
                (
                    "unreadable",
                    arguments(root / "absent-finalization", repeated, expected),
                    2,
                    "unreadable",
                ),
            )

            for case_name, invocation, expected_code, expected_status in cases:
                observed: dict[str, bytes] = {}
                for location, script in (
                    ("source", SOURCE_SKILL / "scripts" / "judicial_meaning.py"),
                    ("installed", installed / SCRIPT),
                ):
                    with self.subTest(case=case_name, location=location):
                        before = _tree_snapshot(root)
                        run = subprocess.run(
                            [sys.executable, str(script), *invocation],
                            cwd=root,
                            env={
                                **os.environ,
                                "PYTHONDONTWRITEBYTECODE": "1",
                                "PYTHONIOENCODING": "ascii",
                                "PYTHONPATH": str(ambient),
                            },
                            capture_output=True,
                            check=False,
                        )
                        self.assertEqual(expected_code, run.returncode, run.stderr)
                        self.assertEqual(b"", run.stderr)
                        report = json.loads(run.stdout)
                        skill_root = (
                            SOURCE_SKILL if location == "source" else installed / SKILL
                        )
                        schema = json.loads(
                            (
                                skill_root
                                / "schemas"
                                / "practice-quality.v1.json"
                            ).read_text(encoding="utf-8")
                        )
                        Draft202012Validator(schema).validate(report)
                        self.assertEqual(expected_status, report["status"])
                        self.assertIs(
                            report["recovery_comparison_valid"],
                            expected_status == "match",
                        )
                        self.assertEqual(_canonical_bytes(report), run.stdout)
                        self.assertEqual(before, _tree_snapshot(root))
                        decoded = run.stdout.decode("utf-8")
                        self.assertNotIn(str(root), decoded)
                        self.assertNotIn(expected, decoded)
                        self.assertNotIn(candidate_id, decoded)
                        observed[location] = run.stdout
                if set(observed) == {"source", "installed"}:
                    self.assertEqual(observed["source"], observed["installed"])

            installed_skill = installed / SKILL
            self.assertFalse((installed_skill / "tests").exists())
            self.assertFalse((installed_skill / "evals").exists())


if __name__ == "__main__":
    unittest.main()
