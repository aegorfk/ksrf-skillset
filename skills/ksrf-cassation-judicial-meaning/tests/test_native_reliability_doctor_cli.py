import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from judicial_meaning import cli, practice_quality
from tests import test_practice_quality


def _canonical_bytes(value):
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


class NativeReliabilityDoctorCliTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        fixture = test_practice_quality.PracticeQualityTests(methodName="runTest")
        self.reliability, self.receipt, self.expected = (
            fixture.native_reliability_inputs(practice_quality)
        )
        self.reliability_path = self.root / "coding-reliability.json"
        self.receipt_path = self.root / "coding-audit-finalization-receipt.json"
        self.reliability_path.write_bytes(_canonical_bytes(self.reliability))
        self.receipt_path.write_bytes(_canonical_bytes(self.receipt))

    def tearDown(self):
        self.temporary.cleanup()

    def argv(self, *, reliability=True, receipt=True, expected=True):
        result = ["quality", "native-reliability", "doctor"]
        if reliability:
            result.extend(["--coding-reliability", str(self.reliability_path)])
        if receipt:
            result.extend(
                [
                    "--coding-audit-finalization-receipt",
                    str(self.receipt_path),
                ]
            )
        if expected:
            result.extend(
                ["--expected-finalization-receipt-sha256", self.expected]
            )
        return result

    def run_cli(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def assert_report(self, stdout):
        self.assertTrue(stdout.endswith("\n"))
        self.assertFalse(stdout.endswith("\n\n"))
        report = json.loads(stdout)
        self.assertEqual(
            stdout,
            json.dumps(
                report,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n",
        )
        self.assertEqual(
            {
                "schema_version",
                "artifact_type",
                "status",
                "native_relation_valid",
                "reason_codes",
                "checks",
                "remediation",
                "scope",
            },
            set(report),
        )
        return report

    def test_valid_triple_is_deterministic_read_only_and_value_free(self):
        before = {
            path.name: path.read_bytes()
            for path in sorted(self.root.iterdir())
            if path.is_file()
        }
        before_names = sorted(path.name for path in self.root.iterdir())
        with mock.patch.object(
            cli, "write_json", side_effect=AssertionError("doctor wrote a file")
        ), mock.patch.object(
            cli.os, "replace", side_effect=AssertionError("doctor replaced a file")
        ), mock.patch.object(
            cli.os, "mkdir", side_effect=AssertionError("doctor created a directory")
        ), mock.patch.object(
            cli.os, "unlink", side_effect=AssertionError("doctor removed a file")
        ), mock.patch.object(
            cli.tempfile,
            "mkdtemp",
            side_effect=AssertionError("doctor created a temporary directory"),
        ), mock.patch.object(
            cli.tempfile,
            "mkstemp",
            side_effect=AssertionError("doctor created a temporary file"),
        ), mock.patch.object(
            cli.shutil,
            "copyfile",
            side_effect=AssertionError("doctor copied a file"),
        ), mock.patch.object(
            cli.PublicCorpus,
            "open_read_only",
            side_effect=AssertionError("doctor opened the corpus"),
        ), mock.patch.object(
            cli,
            "import_handoff",
            side_effect=AssertionError("doctor imported an artifact"),
        ), mock.patch.object(
            cli.sqlite3,
            "connect",
            side_effect=AssertionError("doctor opened a database"),
        ):
            first = self.run_cli(self.argv())
            second = self.run_cli(self.argv())

        self.assertEqual(first, second)
        code, stdout, stderr = first
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        report = self.assert_report(stdout)
        self.assertEqual("valid", report["status"])
        self.assertTrue(report["native_relation_valid"])
        self.assertEqual([], report["reason_codes"])
        self.assertTrue(all(value is True for value in report["checks"].values()))
        self.assertEqual([], report["remediation"])
        self.assertEqual(before_names, sorted(path.name for path in self.root.iterdir()))
        self.assertEqual(
            before,
            {
                path.name: path.read_bytes()
                for path in sorted(self.root.iterdir())
                if path.is_file()
            },
        )
        self.assertNotIn(str(self.root), stdout)
        self.assertNotIn(self.expected, stdout)
        self.assertNotIn("audit-candidate", stdout)
        self.assertNotRegex(stdout, r"[0-9a-f]{64}")

    def test_each_partial_input_combination_is_incomplete(self):
        for reliability in (False, True):
            for receipt in (False, True):
                for expected in (False, True):
                    if reliability and receipt and expected:
                        continue
                    with self.subTest(
                        reliability=reliability,
                        receipt=receipt,
                        expected=expected,
                    ):
                        code, stdout, stderr = self.run_cli(
                            self.argv(
                                reliability=reliability,
                                receipt=receipt,
                                expected=expected,
                            )
                        )
                        self.assertEqual(3, code)
                        self.assertEqual("", stderr)
                        report = self.assert_report(stdout)
                        self.assertEqual("incomplete", report["status"])
                        self.assertFalse(report["native_relation_valid"])

    def test_stdout_is_exact_utf8_under_ascii_process_encoding(self):
        script = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "judicial_meaning.py"
        )
        completed = subprocess.run(
            [sys.executable, str(script), "quality", "native-reliability", "doctor"],
            cwd=self.root,
            env={**os.environ, "PYTHONIOENCODING": "ascii"},
            capture_output=True,
            check=False,
        )

        self.assertEqual(3, completed.returncode)
        self.assertEqual(b"", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual("incomplete", report["status"])
        self.assertEqual(_canonical_bytes(report), completed.stdout)
        self.assertIn("Передайте", completed.stdout.decode("utf-8"))

    def test_relation_mismatches_return_three(self):
        def receipt_self():
            self.receipt["plan_sha256"] = "0" * 64
            self.receipt_path.write_bytes(_canonical_bytes(self.receipt))

        def receipt_field(field, value):
            unsigned = copy.deepcopy(self.receipt)
            unsigned.pop("receipt_sha256")
            unsigned[field] = value
            candidate = {
                **unsigned,
                "receipt_sha256": practice_quality.canonical_digest(unsigned),
            }
            self.receipt_path.write_bytes(_canonical_bytes(candidate))
            return candidate["receipt_sha256"]

        for label in (
            "receipt-self",
            "file-digest",
            "plan-digest",
            "candidate-population",
        ):
            with self.subTest(label=label):
                self.receipt_path.write_bytes(_canonical_bytes(self.receipt))
                expected = self.expected
                if label == "receipt-self":
                    receipt_self()
                elif label == "file-digest":
                    expected = receipt_field(
                        "coding_reliability_file_sha256", "0" * 64
                    )
                elif label == "plan-digest":
                    expected = receipt_field("audit_plan_sha256", "0" * 64)
                else:
                    expected = receipt_field(
                        "candidate_ids",
                        ["audit-candidate-sha256:" + "b" * 64],
                    )
                argv = self.argv()
                argv[-1] = expected
                code, stdout, stderr = self.run_cli(argv)
                self.assertEqual(3, code)
                self.assertEqual("", stderr)
                report = self.assert_report(stdout)
                self.assertEqual("mismatch", report["status"])

        argv = self.argv()
        argv[-1] = "0" * 64
        code, stdout, stderr = self.run_cli(argv)
        self.assertEqual(3, code)
        self.assertEqual("", stderr)
        self.assertEqual("mismatch", self.assert_report(stdout)["status"])

    def test_invalid_and_unreadable_inputs_return_closed_code_two_reports(self):
        hostile = "СЕКРЕТНЫЙ_ТЕКСТ_НЕ_ПЕЧАТАТЬ"
        cases = []

        malformed = self.root / f"{hostile}.json"
        malformed.write_text('{"private":"' + hostile + '"', encoding="utf-8")
        malformed_argv = self.argv()
        malformed_argv[4] = str(malformed)
        cases.append(("malformed", malformed_argv, "invalid"))

        noncanonical = self.root / "noncanonical.json"
        noncanonical.write_text(
            json.dumps(self.reliability, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        noncanonical_argv = self.argv()
        noncanonical_argv[4] = str(noncanonical)
        cases.append(("noncanonical", noncanonical_argv, "invalid"))

        invalid_sha_argv = self.argv()
        invalid_sha_argv[-1] = hostile
        cases.append(("invalid-sha", invalid_sha_argv, "invalid"))

        absent_argv = self.argv()
        absent_path = self.root / f"{hostile}-absent.json"
        absent_argv[4] = str(absent_path)
        cases.append(("absent", absent_argv, "unreadable"))

        for label, argv, status in cases:
            with self.subTest(label=label):
                code, stdout, stderr = self.run_cli(argv)
                self.assertEqual(2, code)
                self.assertEqual("", stderr)
                report = self.assert_report(stdout)
                self.assertEqual(status, report["status"])
                self.assertFalse(report["native_relation_valid"])
                self.assertNotIn(hostile, stdout)
                self.assertNotIn(str(self.root), stdout)
                if label == "noncanonical":
                    self.assertIsNone(
                        report["checks"]["coding_reliability_file_digest_valid"]
                    )

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO is required")
    def test_bounded_reader_rejects_special_symlink_and_oversize_without_blocking(self):
        directory_argv = self.argv()
        directory_argv[4] = str(self.root)

        symlink = self.root / "reliability-link.json"
        symlink.symlink_to(self.reliability_path)
        symlink_argv = self.argv()
        symlink_argv[4] = str(symlink)

        fifo = self.root / "reliability.fifo"
        os.mkfifo(fifo)
        fifo_argv = self.argv()
        fifo_argv[4] = str(fifo)

        completed = subprocess.run(
            [
                sys.executable,
                str(
                    Path(__file__).resolve().parents[1]
                    / "scripts"
                    / "judicial_meaning.py"
                ),
                *fifo_argv,
            ],
            cwd=self.root,
            timeout=2,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(2, completed.returncode)
        self.assertEqual("", completed.stderr)
        fifo_report = self.assert_report(completed.stdout)
        self.assertEqual("unreadable", fifo_report["status"])
        self.assertIn("coding_reliability_unreadable", fifo_report["reason_codes"])

        oversized = self.root / "oversized.json"
        oversized.write_bytes(b"x" * 17)
        oversized_argv = self.argv()
        oversized_argv[4] = str(oversized)

        boundary = self.root / "boundary.json"
        boundary.write_bytes(b"x" * 16)
        boundary_argv = self.argv(receipt=False, expected=False)
        boundary_argv[4] = str(boundary)

        with mock.patch.object(
            cli, "_NATIVE_RELIABILITY_DOCTOR_MAX_INPUT_BYTES", 16
        ):
            for label, argv in (
                ("directory", directory_argv),
                ("symlink", symlink_argv),
                ("oversized", oversized_argv),
            ):
                with self.subTest(label=label):
                    code, stdout, stderr = self.run_cli(argv)
                    self.assertEqual(2, code)
                    self.assertEqual("", stderr)
                    report = self.assert_report(stdout)
                    self.assertEqual("unreadable", report["status"])
                    self.assertIn(
                        "coding_reliability_unreadable",
                        report["reason_codes"],
                    )

            code, stdout, stderr = self.run_cli(boundary_argv)
            self.assertEqual(2, code)
            self.assertEqual("", stderr)
            report = self.assert_report(stdout)
            self.assertEqual("invalid", report["status"])
            self.assertNotIn("coding_reliability_unreadable", report["reason_codes"])

    def test_bounded_reader_rejects_same_inode_rewrite_during_read(self):
        original_read = os.read
        original_inode = self.reliability_path.stat().st_ino
        mutated = False

        def mutate_after_first_read(descriptor, amount):
            nonlocal mutated
            chunk = original_read(descriptor, amount)
            if chunk and not mutated:
                mutated = True
                changed = bytearray(self.reliability_path.read_bytes())
                changed[0] = ord("[")
                self.reliability_path.write_bytes(changed)
                self.assertEqual(original_inode, self.reliability_path.stat().st_ino)
            return chunk

        with mock.patch.object(cli.os, "read", side_effect=mutate_after_first_read):
            code, stdout, stderr = self.run_cli(self.argv())

        self.assertTrue(mutated)
        self.assertEqual(2, code)
        self.assertEqual("", stderr)
        report = self.assert_report(stdout)
        self.assertEqual("unreadable", report["status"])
        self.assertIn("coding_reliability_unreadable", report["reason_codes"])


if __name__ == "__main__":
    unittest.main()
