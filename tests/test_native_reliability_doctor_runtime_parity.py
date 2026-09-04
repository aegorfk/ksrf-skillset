from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator


REPO = Path(__file__).resolve().parents[1]
SKILL = "ksrf-cassation-judicial-meaning"
SOURCE_SKILL = REPO / "skills" / SKILL
SCRIPT = Path(SKILL) / "scripts" / "judicial_meaning.py"
sys.path.insert(0, str(SOURCE_SKILL / "lib"))

from judicial_meaning import practice_quality  # noqa: E402


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


def _tree_snapshot(root: Path) -> dict[str, tuple[str, bytes | None]]:
    result: dict[str, tuple[str, bytes | None]] = {".": ("dir", None)}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = ("symlink", os.readlink(path).encode("utf-8"))
        elif path.is_dir():
            result[relative] = ("dir", None)
        elif path.is_file():
            result[relative] = ("file", path.read_bytes())
        else:
            result[relative] = ("other", None)
    return result


class NativeReliabilityDoctorRuntimeParityTests(unittest.TestCase):
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

            fixture_spec = importlib.util.spec_from_file_location(
                "_native_reliability_doctor_fixture",
                SOURCE_SKILL / "tests" / "test_practice_quality.py",
            )
            self.assertIsNotNone(fixture_spec)
            self.assertIsNotNone(fixture_spec.loader)
            fixture_module = importlib.util.module_from_spec(fixture_spec)
            fixture_spec.loader.exec_module(fixture_module)
            fixture = fixture_module.PracticeQualityTests(methodName="runTest")
            reliability, receipt, expected = fixture.native_reliability_inputs(
                practice_quality
            )

            reliability_path = root / "coding-reliability.json"
            receipt_path = root / "coding-audit-finalization-receipt.json"
            reliability_path.write_bytes(_canonical_bytes(reliability))
            receipt_path.write_bytes(_canonical_bytes(receipt))
            self_mismatch_receipt = copy.deepcopy(receipt)
            self_mismatch_receipt["plan_sha256"] = "0" * 64
            self_mismatch_receipt_path = root / "self-mismatch-receipt.json"
            self_mismatch_receipt_path.write_bytes(
                _canonical_bytes(self_mismatch_receipt)
            )
            ambient = root / "ambient"
            ambient_package = ambient / "judicial_meaning"
            ambient_package.mkdir(parents=True)
            (ambient_package / "__init__.py").write_text(
                "raise RuntimeError('ambient package must not load')\n",
                encoding="utf-8",
            )

            valid_arguments = [
                "quality",
                "native-reliability",
                "doctor",
                "--coding-reliability",
                str(reliability_path),
                "--coding-audit-finalization-receipt",
                str(receipt_path),
                "--expected-finalization-receipt-sha256",
                expected,
            ]
            cases = (
                ("valid", valid_arguments, 0, "valid"),
                (
                    "incomplete",
                    ["quality", "native-reliability", "doctor"],
                    3,
                    "incomplete",
                ),
                (
                    "mismatch",
                    [*valid_arguments[:-1], "0" * 64],
                    3,
                    "mismatch",
                ),
                (
                    "self-mismatch",
                    [
                        *valid_arguments[:6],
                        str(self_mismatch_receipt_path),
                        *valid_arguments[7:],
                    ],
                    3,
                    "mismatch",
                ),
                (
                    "invalid",
                    [*valid_arguments[:-1], "НЕВЕРНЫЙ-SHA"],
                    2,
                    "invalid",
                ),
                (
                    "unreadable",
                    [
                        "quality",
                        "native-reliability",
                        "doctor",
                        "--coding-reliability",
                        str(root / "private-absent.json"),
                    ],
                    2,
                    "unreadable",
                ),
            )
            before = _tree_snapshot(root)
            for case_name, arguments, expected_code, expected_status in cases:
                observed: dict[str, bytes] = {}
                for location, script in (
                    ("source", SOURCE_SKILL / "scripts" / "judicial_meaning.py"),
                    ("installed", installed / SCRIPT),
                ):
                    with self.subTest(case=case_name, location=location):
                        run = subprocess.run(
                            [sys.executable, str(script), *arguments],
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
                            SOURCE_SKILL
                            if location == "source"
                            else installed / SKILL
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
                            report["native_relation_valid"],
                            expected_status == "valid",
                        )
                        self.assertEqual(_canonical_bytes(report), run.stdout)
                        self.assertEqual(before, _tree_snapshot(root))
                        decoded = run.stdout.decode("utf-8")
                        self.assertNotIn(str(root), decoded)
                        self.assertNotIn(expected, decoded)
                        self.assertNotIn(
                            reliability["required_candidate_ids"][0],
                            decoded,
                        )
                        observed[location] = run.stdout
                self.assertEqual(observed["source"], observed["installed"])

            installed_skill = installed / SKILL
            self.assertFalse((installed_skill / "tests").exists())
            self.assertFalse((installed_skill / "evals").exists())


if __name__ == "__main__":
    unittest.main()
