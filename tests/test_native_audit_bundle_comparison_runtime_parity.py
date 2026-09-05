from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
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
sys.path.insert(0, str(SOURCE_SKILL / "tests"))

import test_native_coding_review_import_cli as producer_harness  # noqa: E402


def _snapshot(root: Path) -> dict[str, tuple[object, ...]]:
    result = {}
    for path in (root, *sorted(root.rglob("*"))):
        metadata = path.lstat()
        payload = (
            os.readlink(path).encode("utf-8")
            if stat.S_ISLNK(metadata.st_mode)
            else path.read_bytes() if stat.S_ISREG(metadata.st_mode) else None
        )
        result[path.relative_to(root).as_posix()] = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_uid,
            metadata.st_gid,
            metadata.st_nlink,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
            payload,
        )
    return result


class NativeAuditBundleComparisonRuntimeParityTests(unittest.TestCase):
    maxDiff = None

    def _prepare_pair(self, root: Path) -> tuple[Path, Path, str, str]:
        harness = producer_harness.NativeCodingReviewImportCliTests(
            methodName="runTest"
        )
        state = harness._seed_workspace(root / "producer")
        destinations = (root / "uncertain-bundle", root / "repeated-bundle")
        confirmations = []
        for destination in destinations:
            run = harness._run(
                REPO / "skills" / SCRIPT,
                [
                    "quality", "coding-audit-prepare",
                    "--workspace", str(state["workspace"]),
                    "--codebook-version", "1.0",
                    "--sample-size", "5",
                    "--exclusion-sample-size", "5",
                    "--output-dir", str(destination),
                ],
                cwd=root,
            )
            self.assertEqual(0, run.returncode, run.stderr)
            confirmations.append(json.loads(run.stdout))
        repeated_confirmation = confirmations[1]
        for field in ("manifest_sha256", "independent_review_packet_sha256"):
            self.assertEqual(confirmations[0][field], repeated_confirmation[field])
        return (
            *destinations,
            repeated_confirmation["manifest_sha256"],
            repeated_confirmation["independent_review_packet_sha256"],
        )

    def test_clean_install_has_identical_read_only_states_help_and_exact_options(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            install = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(installed)],
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, install.returncode, install.stderr)
            uncertain, repeated, manifest_sha, packet_sha = self._prepare_pair(root)

            ambient = root / "ambient"
            ambient_package = ambient / "judicial_meaning"
            ambient_package.mkdir(parents=True)
            (ambient_package / "__init__.py").write_text(
                "raise RuntimeError('ambient package must not load')\n",
                encoding="utf-8",
            )
            launch_env = {
                **os.environ,
                "PYTHONIOENCODING": "ascii",
                "PYTHONPATH": str(ambient),
            }
            launch_env.pop("PYTHONDONTWRITEBYTECODE", None)

            def arguments(
                first: Path = uncertain,
                expected_manifest: str = manifest_sha,
                expected_packet: str = packet_sha,
            ) -> list[str]:
                return [
                    "quality", "native-reliability", "compare-audit-bundles",
                    "--uncertain-audit-bundle-dir", str(first),
                    "--repeated-audit-bundle-dir", str(repeated),
                    "--expected-manifest-sha256", expected_manifest,
                    "--expected-independent-review-packet-sha256", expected_packet,
                ]

            wrong_sha = hashlib.sha256(b"different saved repeat anchor").hexdigest()
            cases = (
                ("match", arguments(), 0, "match"),
                (
                    "manifest mismatch",
                    arguments(expected_manifest=wrong_sha), 3, "mismatch",
                ),
                (
                    "packet mismatch",
                    arguments(expected_packet=wrong_sha), 3, "mismatch",
                ),
                (
                    "invalid", arguments(expected_manifest="НЕВЕРНЫЙ-SHA"),
                    2, "invalid",
                ),
                (
                    "unreadable", arguments(first=root / "absent-bundle"),
                    2, "unreadable",
                ),
            )
            launchers = (
                ("source", SOURCE_SKILL / "scripts" / "judicial_meaning.py"),
                ("installed", installed / SCRIPT),
            )
            source_bytecode_before = {
                path for path in SOURCE_SKILL.rglob("*")
                if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}
            }
            for name, invocation, expected_code, expected_status in cases:
                observed = {}
                for location, script in launchers:
                    with self.subTest(case=name, location=location):
                        before = _snapshot(root)
                        run = subprocess.run(
                            [sys.executable, str(script), *invocation],
                            cwd=root, env=launch_env,
                            capture_output=True, check=False,
                        )
                        self.assertEqual(expected_code, run.returncode, run.stderr)
                        self.assertEqual(b"", run.stderr)
                        report = json.loads(run.stdout)
                        self.assertEqual(
                            "native_audit_bundle_comparison_report",
                            report["artifact_type"],
                        )
                        self.assertEqual(expected_status, report["status"])
                        self.assertIs(
                            expected_status == "match",
                            report["recovery_comparison_valid"],
                        )
                        skill_root = SOURCE_SKILL if location == "source" else installed / SKILL
                        schema = json.loads(
                            (skill_root / "schemas" / "practice-quality.v1.json")
                            .read_text(encoding="utf-8")
                        )
                        Draft202012Validator(schema).validate(report)
                        canonical = (
                            json.dumps(
                                report, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":"), allow_nan=False,
                            ) + "\n"
                        ).encode("utf-8")
                        self.assertEqual(canonical, run.stdout)
                        for sensitive in (str(root), manifest_sha, packet_sha, wrong_sha):
                            self.assertNotIn(sensitive.encode(), run.stdout)
                        self.assertEqual(before, _snapshot(root))
                        observed[location] = (run.returncode, run.stdout, run.stderr)
                if set(observed) == {"source", "installed"}:
                    self.assertEqual(observed["source"], observed["installed"])

            shortened = arguments()
            shortened[3] = "--uncertain-audit-bundle-d"
            for name, invocation, expected_code in (
                ("help", ["quality", "native-reliability", "compare-audit-bundles", "--help"], 0),
                ("abbreviated option", shortened, 2),
            ):
                observed = {}
                for location, script in launchers:
                    with self.subTest(case=name, location=location):
                        before = _snapshot(root)
                        run = subprocess.run(
                            [sys.executable, str(script), *invocation],
                            cwd=root,
                            env={**launch_env, "PYTHONIOENCODING": "utf-8"},
                            capture_output=True, check=False,
                        )
                        self.assertEqual(expected_code, run.returncode, run.stderr)
                        if name == "help":
                            self.assertEqual(b"", run.stderr)
                            rendered = " ".join(run.stdout.decode("utf-8").split())
                            for required in (
                                "СОМНИТЕЛЬНАЯ_ПАПКА_ПАКЕТА",
                                "ПОВТОРНАЯ_ПАПКА_ПАКЕТА",
                                "SHA256_МАНИФЕСТА_УСПЕШНОГО_ПОВТОРА",
                                "SHA256_ZIP_УСПЕШНОГО_ПОВТОРА",
                                "из одной полной строки стандартного вывода",
                                "нормального возврата с кодом 0",
                                "0 — match; 3 — mismatch; 2 — invalid или unreadable",
                            ):
                                self.assertIn(required, rendered)
                        else:
                            self.assertEqual(b"", run.stdout)
                            self.assertNotEqual(b"", run.stderr)
                        self.assertEqual(before, _snapshot(root))
                        observed[location] = (run.returncode, run.stdout, run.stderr)
                if set(observed) == {"source", "installed"}:
                    self.assertEqual(observed["source"], observed["installed"])

            self.assertEqual(
                source_bytecode_before,
                {
                    path for path in SOURCE_SKILL.rglob("*")
                    if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}
                },
            )
            forbidden_parts = {"tests", "evals", "openspec", "__pycache__"}
            for path in installed.rglob("*"):
                self.assertFalse(forbidden_parts.intersection(path.relative_to(installed).parts))
                self.assertNotIn(path.suffix, {".pyc", ".pyo"})


if __name__ == "__main__":
    unittest.main()
