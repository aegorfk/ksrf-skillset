from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from judicial_meaning import cli

if __package__:
    from . import test_native_coding_review_import_cli as producer_harness
else:
    import test_native_coding_review_import_cli as producer_harness


REPO = producer_harness.REPO
SCRIPT = producer_harness.SCRIPT


class NativeAuditBundleComparisonCliTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_tmp = tempfile.TemporaryDirectory()
        fixture_root = Path(cls.fixture_tmp.name)
        harness = producer_harness.NativeCodingReviewImportCliTests(
            methodName="runTest"
        )
        state = harness._seed_workspace(fixture_root / "producer")
        cls.fixture_directories: list[Path] = []
        results: list[dict[str, object]] = []
        for name in ("uncertain-audit-bundle", "repeated-audit-bundle"):
            destination = fixture_root / name
            completed = harness._run(
                REPO / SCRIPT,
                [
                    "quality",
                    "coding-audit-prepare",
                    "--workspace",
                    str(state["workspace"]),
                    "--codebook-version",
                    "1.0",
                    "--sample-size",
                    "5",
                    "--exclusion-sample-size",
                    "5",
                    "--output-dir",
                    str(destination),
                ],
                cwd=fixture_root,
            )
            if completed.returncode != 0:
                raise AssertionError(completed.stderr)
            cls.fixture_directories.append(destination)
            results.append(json.loads(completed.stdout))
        if results[0]["manifest_sha256"] != results[1]["manifest_sha256"]:
            raise AssertionError("Fixture bundle manifests are not identical.")
        if (
            results[0]["independent_review_packet_sha256"]
            != results[1]["independent_review_packet_sha256"]
        ):
            raise AssertionError("Fixture review packets are not identical.")
        cls.expected_manifest_sha256 = str(results[1]["manifest_sha256"])
        cls.expected_packet_sha256 = str(
            results[1]["independent_review_packet_sha256"]
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_tmp.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        os.chmod(self.root, 0o700)
        self.uncertain = self.root / "uncertain-audit-bundle"
        self.repeated = self.root / "repeated-audit-bundle"
        shutil.copytree(self.fixture_directories[0], self.uncertain)
        shutil.copytree(self.fixture_directories[1], self.repeated)
        for directory in (self.uncertain, self.repeated):
            os.chmod(directory, 0o700)
            for path in directory.iterdir():
                os.chmod(path, 0o600)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def argv(
        self,
        *,
        uncertain: Path | None = None,
        repeated: Path | None = None,
        manifest_sha256: str | None = None,
        packet_sha256: str | None = None,
    ) -> list[str]:
        return [
            "quality",
            "native-reliability",
            "compare-audit-bundles",
            "--uncertain-audit-bundle-dir",
            str(uncertain or self.uncertain),
            "--repeated-audit-bundle-dir",
            str(repeated or self.repeated),
            "--expected-manifest-sha256",
            manifest_sha256 or self.expected_manifest_sha256,
            "--expected-independent-review-packet-sha256",
            packet_sha256 or self.expected_packet_sha256,
        ]

    def run_cli(self, argv: list[str] | None = None) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = cli.main(argv or self.argv())
            except SystemExit as exc:
                code = int(exc.code)
        return code, stdout.getvalue(), stderr.getvalue()

    def run_handler(self) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        args = argparse.Namespace(
            uncertain_audit_bundle_dir=str(self.uncertain),
            repeated_audit_bundle_dir=str(self.repeated),
            expected_manifest_sha256=self.expected_manifest_sha256,
            expected_independent_review_packet_sha256=self.expected_packet_sha256,
        )
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.cmd_quality_native_reliability_compare_audit_bundles(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_match_is_canonical_value_free_and_read_only(self) -> None:
        before = {
            path: path.read_bytes()
            for directory in (self.uncertain, self.repeated)
            for path in directory.iterdir()
        }
        code, stdout, stderr = self.run_cli()
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        report = json.loads(stdout)
        self.assertEqual("native_audit_bundle_comparison_report", report["artifact_type"])
        self.assertEqual("match", report["status"])
        self.assertTrue(report["recovery_comparison_valid"])
        self.assertEqual(stdout, json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
        self.assertNotIn(str(self.root), stdout)
        self.assertNotIn(self.expected_manifest_sha256, stdout)
        self.assertNotIn(self.expected_packet_sha256, stdout)
        self.assertEqual(
            before,
            {
                path: path.read_bytes()
                for directory in (self.uncertain, self.repeated)
                for path in directory.iterdir()
            },
        )

    def test_each_well_formed_external_anchor_mismatch_returns_three(self) -> None:
        wrong_manifest = hashlib.sha256(b"wrong-manifest").hexdigest()
        wrong_packet = hashlib.sha256(b"wrong-packet").hexdigest()
        for kwargs, reason in (
            ({"manifest_sha256": wrong_manifest}, "external_manifest_digest_mismatch"),
            ({"packet_sha256": wrong_packet}, "external_independent_review_packet_digest_mismatch"),
        ):
            with self.subTest(reason=reason):
                code, stdout, stderr = self.run_cli(self.argv(**kwargs))
                self.assertEqual(3, code)
                self.assertEqual("", stderr)
                report = json.loads(stdout)
                self.assertEqual("mismatch", report["status"])
                self.assertIn(reason, report["reason_codes"])

    def test_invalid_anchor_syntax_returns_two(self) -> None:
        code, stdout, stderr = self.run_cli(
            self.argv(manifest_sha256="A" * 64)
        )
        self.assertEqual(2, code)
        self.assertEqual("", stderr)
        report = json.loads(stdout)
        self.assertEqual("invalid", report["status"])
        self.assertIn("expected_manifest_sha256_invalid", report["reason_codes"])

    def test_different_parent_is_invalid(self) -> None:
        other_root = self.root / "other"
        other_root.mkdir(mode=0o700)
        moved = other_root / "repeated"
        self.repeated.rename(moved)
        code, stdout, stderr = self.run_cli(self.argv(repeated=moved))
        self.assertEqual(2, code)
        self.assertEqual("", stderr)
        report = json.loads(stdout)
        self.assertEqual("invalid", report["status"])
        self.assertIn("comparison_topology_invalid", report["reason_codes"])

    def test_parser_requires_all_four_exact_options(self) -> None:
        for option in (
            "--uncertain-audit-bundle-dir",
            "--repeated-audit-bundle-dir",
            "--expected-manifest-sha256",
            "--expected-independent-review-packet-sha256",
        ):
            argv = self.argv()
            index = argv.index(option)
            del argv[index : index + 2]
            with self.subTest(option=option):
                code, stdout, stderr = self.run_cli(argv)
                self.assertEqual(2, code)
                self.assertEqual("", stdout)
                self.assertNotEqual("", stderr)
        abbreviated = self.argv()
        abbreviated[3] = "--uncertain-audit-bundle-d"
        code, stdout, stderr = self.run_cli(abbreviated)
        self.assertEqual(2, code)
        self.assertEqual("", stdout)
        self.assertNotEqual("", stderr)

    def test_identity_read_failure_keeps_distinct_check_unavailable(self) -> None:
        original_fstat = os.fstat
        failed = False

        def fail_directory_identity_once(descriptor: int):
            nonlocal failed
            caller = sys._getframe(1)
            in_identity_check = False
            while caller is not None:
                if caller.f_code.co_name == "observed_directory_identity":
                    in_identity_check = True
                    break
                caller = caller.f_back
            if (
                not failed
                and in_identity_check
            ):
                failed = True
                raise OSError("PRIVATE-IDENTITY-FAILURE")
            return original_fstat(descriptor)

        with mock.patch.object(cli.os, "fstat", side_effect=fail_directory_identity_once):
            code, stdout, stderr = self.run_cli()
        self.assertTrue(failed)
        self.assertEqual(2, code)
        self.assertEqual("", stderr)
        report = json.loads(stdout)
        self.assertEqual("unreadable", report["status"])
        self.assertIsNone(report["checks"]["directories_distinct"])
        self.assertNotIn("PRIVATE-IDENTITY-FAILURE", stdout)

    def test_later_read_failure_clears_obsolete_codebook_reason(self) -> None:
        original_capture = cli._secure_codebook_capture
        calls = 0

        def fail_first_codebook_capture(version: str):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("PRIVATE-CODEBOOK-FAILURE")
            return original_capture(version)

        with (
            mock.patch.object(cli, "_secure_codebook_capture", side_effect=fail_first_codebook_capture),
            mock.patch.object(
                cli,
                "_comparison_directory_bytes_equal",
                side_effect=cli._FinalizationComparisonCaptureError("changed", side="uncertain"),
            ),
        ):
            code, stdout, stderr = self.run_cli()
        self.assertEqual(2, code)
        self.assertEqual("", stderr)
        report = json.loads(stdout)
        self.assertEqual("unreadable", report["status"])
        self.assertIn("comparison_input_changed", report["reason_codes"])
        self.assertNotIn("uncertain_installed_codebook_unreadable", report["reason_codes"])
        self.assertIsNone(report["checks"]["uncertain_installed_codebook_readable"])
        self.assertNotIn("PRIVATE-CODEBOOK-FAILURE", stdout)

    def test_help_is_russian_and_exposes_no_output_option(self) -> None:
        code, stdout, stderr = self.run_cli(
            ["quality", "native-reliability", "compare-audit-bundles", "--help"]
        )
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        self.assertIn("СОМНИТЕЛЬНАЯ_ПАПКА_ПАКЕТА", stdout)
        self.assertIn("ПОВТОРНАЯ_ПАПКА_ПАКЕТА", stdout)
        self.assertIn("SHA256_МАНИФЕСТА_УСПЕШНОГО_ПОВТОРА", stdout)
        self.assertIn("SHA256_ZIP_УСПЕШНОГО_ПОВТОРА", stdout)
        self.assertNotIn("--output", stdout)


if __name__ == "__main__":
    unittest.main()
