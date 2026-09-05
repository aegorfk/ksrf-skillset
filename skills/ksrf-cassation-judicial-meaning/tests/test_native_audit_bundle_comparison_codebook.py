from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest
from unittest import mock

from judicial_meaning import cli

if __package__:
    from . import test_native_audit_bundle_comparison_cli as comparison_harness
else:
    import test_native_audit_bundle_comparison_cli as comparison_harness


class NativeAuditBundleComparisonCodebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        comparison_harness.NativeAuditBundleComparisonCliTests.setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        comparison_harness.NativeAuditBundleComparisonCliTests.tearDownClass()

    def setUp(self) -> None:
        self.harness = comparison_harness.NativeAuditBundleComparisonCliTests(
            methodName="runTest"
        )
        self.harness.setUp()
        self.runtime = self.harness.root / "temporary-runtime"
        self.references = self.runtime / "references"
        self.replacement = self.runtime / "replacement"
        self.references.mkdir(parents=True)
        self.replacement.mkdir()
        self.filename = cli._AUDIT_CODEBOOK_PATHS["1.0"]
        self.source = (
            Path(cli.__file__).resolve().parents[2] / "references" / self.filename
        )
        shutil.copyfile(self.source, self.references / self.filename)
        shutil.copyfile(
            self.harness.uncertain / "coding-audit-inputs-manifest.json",
            self.replacement / self.filename,
        )
        self.module_path_patch = mock.patch.object(
            cli,
            "__file__",
            str(self.runtime / "lib" / "judicial_meaning" / "cli.py"),
        )
        self.module_path_patch.start()
        self.addCleanup(self.harness.tearDown)
        self.addCleanup(self.module_path_patch.stop)

    def swap_references(self) -> None:
        self.references.rename(self.runtime / "old-references")
        self.replacement.rename(self.references)

    def assert_changed_report(self) -> dict[str, object]:
        code, stdout, stderr = self.harness.run_cli()
        self.assertEqual(2, code)
        self.assertEqual("", stderr)
        report = json.loads(stdout)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertIn("comparison_input_changed", report["reason_codes"])
        self.assertIn(
            "administrator_quarantine",
            [item["code"] for item in report["remediation"]],
        )
        self.assertNotIn(str(self.runtime), stdout)
        self.assertNotIn(self.filename, stdout)
        self.assertNotIn(self.harness.expected_manifest_sha256, stdout)
        return report

    def test_unchanged_installed_binding_matches(self) -> None:
        code, stdout, stderr = self.harness.run_cli()
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        self.assertEqual("match", json.loads(stdout)["status"])

    def test_parent_swap_during_last_codebook_read_is_changed(self) -> None:
        original = cli._read_bounded_regular_fd
        calls = 0

        def read_then_swap(*args, **kwargs):
            nonlocal calls
            result = original(*args, **kwargs)
            if kwargs.get("label") == "штатный справочник кодирования":
                calls += 1
                if calls == 4:
                    self.swap_references()
            return result

        with mock.patch.object(
            cli, "_read_bounded_regular_fd", side_effect=read_then_swap
        ):
            self.assert_changed_report()
        self.assertEqual(4, calls)
        self.assertNotEqual(
            self.source.read_bytes(), (self.references / self.filename).read_bytes()
        )

    def test_leaf_replacement_during_last_codebook_read_is_changed(self) -> None:
        original = cli._read_bounded_regular_fd
        calls = 0

        def read_then_replace(*args, **kwargs):
            nonlocal calls
            result = original(*args, **kwargs)
            if kwargs.get("label") == "штатный справочник кодирования":
                calls += 1
                if calls == 4:
                    (self.replacement / self.filename).replace(
                        self.references / self.filename
                    )
            return result

        with mock.patch.object(
            cli, "_read_bounded_regular_fd", side_effect=read_then_replace
        ):
            self.assert_changed_report()
        self.assertEqual(4, calls)

    def test_parent_swap_between_recaptures_is_changed(self) -> None:
        original = cli._secure_audit_bundle_comparison_codebook_capture
        calls = 0

        def capture_then_swap(version):
            nonlocal calls
            result = original(version)
            calls += 1
            if calls == 3:
                self.swap_references()
            return result

        with mock.patch.object(
            cli,
            "_secure_audit_bundle_comparison_codebook_capture",
            side_effect=capture_then_swap,
        ):
            self.assert_changed_report()
        self.assertEqual(4, calls)

    def test_parent_swap_after_last_recapture_is_caught_by_final_seal(self) -> None:
        original = cli._secure_audit_bundle_comparison_codebook_capture
        calls = 0

        def capture_then_swap(version):
            nonlocal calls
            result = original(version)
            calls += 1
            if calls == 4:
                self.swap_references()
            return result

        with mock.patch.object(
            cli,
            "_secure_audit_bundle_comparison_codebook_capture",
            side_effect=capture_then_swap,
        ):
            self.assert_changed_report()
        self.assertEqual(4, calls)

    def test_parent_swap_during_late_bundle_seal_is_changed(self) -> None:
        original = cli._assert_comparison_leaf_seal
        swapped = False

        def seal_then_swap(*args, **kwargs):
            nonlocal swapped
            result = original(*args, **kwargs)
            if not swapped:
                swapped = True
                self.swap_references()
            return result

        with mock.patch.object(
            cli, "_assert_comparison_leaf_seal", side_effect=seal_then_swap
        ):
            self.assert_changed_report()
        self.assertTrue(swapped)

    def test_initial_read_failure_preserves_codebook_unreadable_state(self) -> None:
        with mock.patch.object(
            cli, "_secure_codebook_capture", side_effect=OSError("private-marker")
        ):
            code, stdout, stderr = self.harness.run_cli()
        self.assertEqual(2, code)
        self.assertEqual("", stderr)
        report = json.loads(stdout)
        self.assertEqual("unreadable", report["status"])
        self.assertEqual(
            [
                "uncertain_installed_codebook_unreadable",
                "repeated_installed_codebook_unreadable",
            ],
            report["reason_codes"],
        )
        self.assertIsNone(report["checks"]["final_recapture_valid"])
        self.assertNotIn("private-marker", stdout)

    def test_initial_read_failure_with_parent_swap_preserves_drift(self) -> None:
        original = cli._secure_codebook_capture
        first = True

        def fail_after_swap(version):
            nonlocal first
            if first:
                first = False
                self.swap_references()
                raise OSError("private-marker")
            return original(version)

        with mock.patch.object(
            cli, "_secure_codebook_capture", side_effect=fail_after_swap
        ):
            self.assert_changed_report()

    def test_symlinked_codebook_parent_is_unreadable_without_following_it(self) -> None:
        original = self.runtime / "old-references"
        self.references.rename(original)
        self.references.symlink_to(original, target_is_directory=True)
        with mock.patch.object(cli, "_secure_codebook_capture") as reader:
            code, stdout, stderr = self.harness.run_cli()
        self.assertEqual(2, code)
        self.assertEqual("", stderr)
        self.assertEqual("unreadable", json.loads(stdout)["status"])
        reader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
