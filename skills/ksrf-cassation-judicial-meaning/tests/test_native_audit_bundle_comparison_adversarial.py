from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import shutil
import stat
import unittest
from unittest import mock

from judicial_meaning import cli

if __package__:
    from . import test_native_audit_bundle_comparison_cli as fixture_module
else:
    import test_native_audit_bundle_comparison_cli as fixture_module


AUDIT_BUNDLE_FILES = (
    "screening-candidates.audit.jsonl",
    "primary-decisions.audit.jsonl",
    "coding-audit-plan.json",
    "secondary-review-queue.jsonl",
    "secondary-coding-template.jsonl",
    "independent-review-packet.zip",
    "coding-audit-inputs-manifest.json",
)
SENSITIVE_MARKER = "СЕКРЕТНЫЙ-ПУТЬ-ДАЙДЖЕСТ-И-КАНДИДАТ"


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


def _directory_snapshot(root: Path) -> dict[str, tuple[object, ...]]:
    snapshot: dict[str, tuple[object, ...]] = {}
    for path in sorted(root.iterdir()):
        path_stat = path.lstat()
        snapshot[path.name] = (
            stat.S_IFMT(path_stat.st_mode),
            stat.S_IMODE(path_stat.st_mode),
            path_stat.st_uid,
            path_stat.st_gid,
            path_stat.st_nlink,
            path.read_bytes() if path.is_file() and not path.is_symlink() else None,
        )
    return snapshot


class NativeAuditBundleComparisonAdversarialTests(unittest.TestCase):
    """Hostile cases composed from the normal fixture without inherited tests."""

    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        fixture_module.NativeAuditBundleComparisonCliTests.setUpClass.__func__(
            cls
        )

    @classmethod
    def tearDownClass(cls) -> None:
        fixture_module.NativeAuditBundleComparisonCliTests.tearDownClass.__func__(
            cls
        )

    def setUp(self) -> None:
        fixture_module.NativeAuditBundleComparisonCliTests.setUp(self)

    def tearDown(self) -> None:
        fixture_module.NativeAuditBundleComparisonCliTests.tearDown(self)

    def argv(
        self,
        *,
        uncertain: Path | None = None,
        repeated: Path | None = None,
        manifest_sha256: str | None = None,
        packet_sha256: str | None = None,
    ) -> list[str]:
        return fixture_module.NativeAuditBundleComparisonCliTests.argv(
            self,
            uncertain=uncertain,
            repeated=repeated,
            manifest_sha256=manifest_sha256,
            packet_sha256=packet_sha256,
        )

    def run_cli(self, argv: list[str] | None = None) -> tuple[int, str, str]:
        return fixture_module.NativeAuditBundleComparisonCliTests.run_cli(
            self,
            argv,
        )

    def fresh_pair(self, label: str) -> tuple[Path, Path]:
        parent = self.root / label
        parent.mkdir(mode=0o700)
        uncertain = parent / "uncertain"
        repeated = parent / "repeated"
        shutil.copytree(self.uncertain, uncertain, copy_function=shutil.copy2)
        shutil.copytree(self.repeated, repeated, copy_function=shutil.copy2)
        return uncertain, repeated

    def assert_report(
        self,
        result: tuple[int, str, str],
        *,
        sensitive: str = SENSITIVE_MARKER,
    ) -> dict[str, object]:
        _, stdout, stderr = result
        self.assertEqual("", stderr)
        self.assertTrue(stdout.endswith("\n"))
        self.assertFalse(stdout.endswith("\n\n"))
        report = json.loads(stdout)
        self.assertEqual(_canonical_bytes(report), stdout.encode("utf-8"))
        self.assertEqual(
            "native_audit_bundle_comparison_report",
            report["artifact_type"],
        )
        self.assertNotIn(str(self.root), stdout)
        self.assertNotIn(self.expected_manifest_sha256, stdout)
        self.assertNotIn(self.expected_packet_sha256, stdout)
        self.assertNotIn(sensitive, stdout)
        return report

    def test_inventory_nonregular_links_and_modes_fail_closed(self) -> None:
        def missing(root: Path, _: Path) -> None:
            (root / AUDIT_BUNDLE_FILES[0]).unlink()

        def extra(root: Path, _: Path) -> None:
            path = root / "extra-private-value.txt"
            path.write_text(SENSITIVE_MARKER, encoding="utf-8")
            os.chmod(path, 0o600)

        def directory(root: Path, _: Path) -> None:
            path = root / AUDIT_BUNDLE_FILES[0]
            path.unlink()
            path.mkdir(mode=0o700)

        def fifo(root: Path, _: Path) -> None:
            path = root / AUDIT_BUNDLE_FILES[0]
            path.unlink()
            os.mkfifo(path, mode=0o600)

        def symlink(root: Path, uncertain: Path) -> None:
            path = root / AUDIT_BUNDLE_FILES[0]
            path.unlink()
            path.symlink_to(uncertain / AUDIT_BUNDLE_FILES[0])

        def file_mode(root: Path, _: Path) -> None:
            os.chmod(root / AUDIT_BUNDLE_FILES[0], 0o640)

        def directory_mode(root: Path, _: Path) -> None:
            os.chmod(root, 0o750)

        for label, mutate, failed_check in (
            ("missing", missing, "repeated_inventory_exact"),
            ("extra", extra, "repeated_inventory_exact"),
            ("directory", directory, "repeated_bundle_private"),
            ("fifo", fifo, "repeated_bundle_private"),
            ("symlink", symlink, "repeated_bundle_private"),
            ("file-mode", file_mode, "repeated_bundle_private"),
            ("directory-mode", directory_mode, "repeated_bundle_private"),
        ):
            uncertain, repeated = self.fresh_pair(f"case-{label}")
            mutate(repeated, uncertain)
            result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                self.assertIs(report["checks"][failed_check], False)
                self.assertIsNone(
                    report["checks"]["audit_bundle_file_bytes_equal"]
                )
                remediation = {
                    item["code"] for item in report["remediation"]
                }
                self.assertIn("administrator_quarantine", remediation)
                self.assertNotIn("investigate_without_selection", remediation)

        uncertain, repeated = self.fresh_pair("case-parent-mode")
        os.chmod(uncertain.parent, 0o777)
        result = self.run_cli(self.argv(uncertain=uncertain, repeated=repeated))
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertIs(report["checks"]["common_parent_valid"], False)

    def test_intra_and_cross_bundle_hardlinks_are_privacy_invalid(self) -> None:
        for label, link_cross_bundle in (
            ("intra", False),
            ("cross", True),
        ):
            uncertain, repeated = self.fresh_pair(f"hardlink-{label}")
            target = repeated / AUDIT_BUNDLE_FILES[1]
            target.unlink()
            source_root = uncertain if link_cross_bundle else repeated
            os.link(source_root / AUDIT_BUNDLE_FILES[0], target)
            result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                self.assertIs(report["checks"]["repeated_bundle_private"], False)
                if link_cross_bundle:
                    self.assertIs(
                        report["checks"]["uncertain_bundle_private"],
                        False,
                    )
                self.assertIsNone(
                    report["checks"]["audit_bundle_file_bytes_equal"]
                )

    def test_cross_device_leaf_is_rejected_before_content_evaluation(self) -> None:
        target_inode = (self.repeated / AUDIT_BUNDLE_FILES[0]).stat().st_ino
        real_identity = cli._stable_file_identity

        def foreign_device(value: os.stat_result) -> tuple[int, ...]:
            identity = list(real_identity(value))
            if value.st_ino == target_inode:
                identity[0] += 1
            return tuple(identity)

        with mock.patch.object(
            cli,
            "_stable_file_identity",
            side_effect=foreign_device,
        ):
            result = self.run_cli()
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertIs(report["checks"]["repeated_bundle_private"], False)
        self.assertIsNone(report["checks"]["repeated_bundle_contract_valid"])

    def test_malformed_noncanonical_and_broken_zip_are_contract_invalid(self) -> None:
        def malformed_manifest(root: Path) -> None:
            (root / "coding-audit-inputs-manifest.json").write_bytes(
                ("{\"private\":\"" + SENSITIVE_MARKER + "\"\n").encode(
                    "utf-8"
                )
            )

        def noncanonical_plan(root: Path) -> None:
            path = root / "coding-audit-plan.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            path.write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        def malformed_jsonl(root: Path) -> None:
            path = root / "primary-decisions.audit.jsonl"
            with path.open("ab") as stream:
                stream.write(("{]" + SENSITIVE_MARKER + "\n").encode("utf-8"))

        def broken_zip(root: Path) -> None:
            (root / "independent-review-packet.zip").write_bytes(
                ("not-a-zip-" + SENSITIVE_MARKER).encode("utf-8")
            )

        for label, mutate in (
            ("malformed-manifest", malformed_manifest),
            ("noncanonical-plan", noncanonical_plan),
            ("malformed-jsonl", malformed_jsonl),
            ("broken-zip", broken_zip),
        ):
            uncertain, repeated = self.fresh_pair(f"contract-{label}")
            mutate(uncertain)
            result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                self.assertIs(
                    report["checks"]["uncertain_bundle_contract_valid"],
                    False,
                )
                self.assertIn(
                    "uncertain_audit_bundle_artifact_contract_invalid",
                    report["reason_codes"],
                )
                self.assertNotIn(
                    "investigate_without_selection",
                    {item["code"] for item in report["remediation"]},
                )

    def test_file_json_and_zip_resource_bounds_are_unreadable(self) -> None:
        patches = (
            (
                "file-size",
                mock.patch.dict(
                    cli._AUDIT_IMPORT_FILE_LIMITS,
                    {"coding-audit-inputs-manifest.json": 1},
                ),
            ),
            (
                "json-depth",
                mock.patch.object(cli, "_AUDIT_IMPORT_MAX_JSON_DEPTH", 1),
            ),
            (
                "zip-total",
                mock.patch.object(cli, "_AUDIT_IMPORT_ZIP_TOTAL_LIMIT", 1),
            ),
        )
        for label, patcher in patches:
            with patcher:
                result = self.run_cli()
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertIn(
                    "uncertain_audit_bundle_unreadable",
                    report["reason_codes"],
                )
                self.assertIn(
                    "repeated_audit_bundle_unreadable",
                    report["reason_codes"],
                )

    def test_two_independently_valid_different_bundles_are_mismatch(self) -> None:
        shutil.rmtree(self.uncertain)
        producer = fixture_module.producer_harness.NativeCodingReviewImportCliTests(
            methodName="runTest"
        )
        state = producer._seed_workspace(
            self.root / "variant-source",
            candidate_count=3,
        )
        completed = producer._run(
            fixture_module.REPO / fixture_module.SCRIPT,
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
                str(self.uncertain),
            ],
            cwd=self.root,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

        result = self.run_cli()
        self.assertEqual(3, result[0])
        report = self.assert_report(result)
        self.assertEqual("mismatch", report["status"])
        self.assertIs(report["checks"]["uncertain_bundle_contract_valid"], True)
        self.assertIs(report["checks"]["repeated_bundle_contract_valid"], True)
        self.assertIs(
            report["checks"]["uncertain_installed_codebook_binding_valid"],
            True,
        )
        self.assertIs(
            report["checks"]["repeated_installed_codebook_binding_valid"],
            True,
        )
        self.assertIs(report["checks"]["audit_bundle_file_bytes_equal"], False)
        self.assertEqual(
            ["audit_bundle_directory_bytes_mismatch"],
            report["reason_codes"],
        )
        self.assertEqual(
            ["preserve_and_stop", "investigate_without_selection"],
            [item["code"] for item in report["remediation"]],
        )

    def test_codebook_unreadable_binding_mismatch_and_drift_are_closed(self) -> None:
        real_capture = cli._secure_codebook_capture
        calls = 0

        def first_codebook_unreadable(version: str) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError(SENSITIVE_MARKER)
            return real_capture(version)

        with mock.patch.object(
            cli,
            "_secure_codebook_capture",
            side_effect=first_codebook_unreadable,
        ):
            unreadable = self.run_cli()
        self.assertEqual(2, unreadable[0])
        unreadable_report = self.assert_report(unreadable)
        self.assertEqual("unreadable", unreadable_report["status"])
        self.assertEqual(
            ["uncertain_installed_codebook_unreadable"],
            unreadable_report["reason_codes"],
        )
        self.assertIs(
            unreadable_report["checks"][
                "repeated_installed_codebook_binding_valid"
            ],
            True,
        )

        with mock.patch.object(
            cli,
            "_native_coding_audit_bundle_installed_codebook_matches",
            side_effect=(False, True),
        ):
            mismatch = self.run_cli()
        self.assertEqual(2, mismatch[0])
        mismatch_report = self.assert_report(mismatch)
        self.assertEqual("invalid", mismatch_report["status"])
        self.assertEqual(
            ["uncertain_installed_codebook_binding_mismatch"],
            mismatch_report["reason_codes"],
        )
        self.assertIs(mismatch_report["checks"]["final_recapture_valid"], True)

        calls = 0

        def drifting_codebook(version: str) -> dict[str, object]:
            nonlocal calls
            calls += 1
            captured = real_capture(version)
            if calls == 3:
                captured = dict(captured)
                captured["content"] = bytes(captured["content"]) + b"drift"
            return captured

        with mock.patch.object(
            cli,
            "_secure_codebook_capture",
            side_effect=drifting_codebook,
        ):
            drift = self.run_cli()
        self.assertEqual(2, drift[0])
        drift_report = self.assert_report(drift)
        self.assertEqual("unreadable", drift_report["status"])
        self.assertIs(drift_report["checks"]["final_recapture_valid"], False)
        self.assertIn("comparison_input_changed", drift_report["reason_codes"])

    def test_capture_and_raw_comparison_drift_never_become_mismatch(self) -> None:
        real_capture = cli._capture_private_comparison_descriptor
        calls = 0

        def third_capture_changes(
            descriptor: int,
            **kwargs: object,
        ) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 3:
                raise cli._FinalizationComparisonCaptureError(
                    "changed",
                    side="uncertain",
                )
            return real_capture(descriptor, **kwargs)

        with mock.patch.object(
            cli,
            "_capture_private_comparison_descriptor",
            side_effect=third_capture_changes,
        ):
            capture_result = self.run_cli()
        self.assertGreaterEqual(calls, 4)
        self.assertEqual(2, capture_result[0])
        capture_report = self.assert_report(capture_result)
        self.assertEqual("unreadable", capture_report["status"])
        self.assertIs(capture_report["checks"]["final_recapture_valid"], False)
        self.assertIn("comparison_input_changed", capture_report["reason_codes"])

        error = cli._FinalizationComparisonCaptureError(
            "changed",
            inventory_exact=True,
            side="uncertain",
        )
        with mock.patch.object(
            cli,
            "_comparison_directory_bytes_equal",
            side_effect=error,
        ):
            raw_result = self.run_cli()
        self.assertEqual(2, raw_result[0])
        raw_report = self.assert_report(raw_result)
        self.assertEqual("unreadable", raw_report["status"])
        self.assertIsNone(raw_report["checks"]["audit_bundle_file_bytes_equal"])
        self.assertIs(raw_report["checks"]["final_recapture_valid"], False)
        self.assertNotIn(
            "audit_bundle_directory_bytes_mismatch",
            raw_report["reason_codes"],
        )

    def test_parent_and_leaf_mutation_are_caught_by_final_recapture(self) -> None:
        for label, target in (
            ("parent", "_assert_finalization_comparison_parent_bindings"),
            ("supplied-path", "_assert_finalization_comparison_supplied_path"),
            ("leaf", "_assert_comparison_leaf_seal"),
        ):
            with mock.patch.object(
                cli,
                target,
                side_effect=cli._FinalizationComparisonCaptureError(
                    "changed",
                    side="uncertain",
                ),
            ):
                result = self.run_cli()
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertIs(report["checks"]["final_recapture_valid"], False)
                self.assertIn("comparison_input_changed", report["reason_codes"])

        real_capture = cli._capture_private_comparison_descriptor
        calls = 0
        mutated = False

        def mutate_after_first_recapture(
            descriptor: int,
            **kwargs: object,
        ) -> dict[str, object]:
            nonlocal calls, mutated
            calls += 1
            result = real_capture(descriptor, **kwargs)
            if calls == 3:
                path = self.uncertain / "coding-audit-plan.json"
                original = path.read_bytes()
                replacement = bytes((byte ^ 1) for byte in original)
                self.assertEqual(len(original), len(replacement))
                path.write_bytes(replacement)
                mutated = True
            return result

        with mock.patch.object(
            cli,
            "_capture_private_comparison_descriptor",
            side_effect=mutate_after_first_recapture,
        ):
            actual_mutation = self.run_cli()
        self.assertTrue(mutated)
        self.assertEqual(2, actual_mutation[0])
        mutation_report = self.assert_report(actual_mutation)
        self.assertEqual("unreadable", mutation_report["status"])
        self.assertIs(mutation_report["checks"]["final_recapture_valid"], False)
        self.assertIn("comparison_input_changed", mutation_report["reason_codes"])

    def test_descriptor_close_uncertainty_invalidates_completed_match(self) -> None:
        real_close = cli._close_finalization_comparison_descriptor
        injected = False

        def hostile_close(descriptor: int) -> None:
            nonlocal injected
            try:
                is_directory = stat.S_ISDIR(cli.os.fstat(descriptor).st_mode)
            except OSError:
                is_directory = False
            real_close(descriptor)
            if is_directory and not injected:
                injected = True
                raise cli._FinalizationComparisonCaptureError(
                    "changed",
                    side="uncertain",
                )

        with mock.patch.object(
            cli,
            "_close_finalization_comparison_descriptor",
            side_effect=hostile_close,
        ):
            result = self.run_cli()
        self.assertTrue(injected)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertIs(report["checks"]["final_recapture_valid"], False)
        self.assertIs(report["checks"]["audit_bundle_file_bytes_equal"], True)
        self.assertIn("comparison_input_changed", report["reason_codes"])

    def test_sensitive_paths_contents_and_exceptions_never_leak(self) -> None:
        missing = self.root / SENSITIVE_MARKER
        path_result = self.run_cli(self.argv(uncertain=missing))
        self.assertEqual(2, path_result[0])
        self.assert_report(path_result)

        path = self.uncertain / "coding-audit-inputs-manifest.json"
        path.write_bytes(("{\"" + SENSITIVE_MARKER + "\":").encode("utf-8"))
        content_result = self.run_cli()
        self.assertEqual(2, content_result[0])
        self.assert_report(content_result)

        with mock.patch.object(
            cli,
            "_secure_codebook_capture",
            side_effect=OSError(SENSITIVE_MARKER),
        ):
            exception_result = self.run_cli()
        self.assertEqual(2, exception_result[0])
        self.assert_report(exception_result)

    def test_hostile_failures_do_not_mutate_the_other_bundle(self) -> None:
        before = _directory_snapshot(self.repeated)
        (self.uncertain / "extra.txt").write_text(
            SENSITIVE_MARKER,
            encoding="utf-8",
        )
        os.chmod(self.uncertain / "extra.txt", 0o600)
        forbidden = AssertionError("adversarial comparison attempted a write")
        with contextlib.ExitStack() as stack:
            for owner, name in (
                (cli.os, "replace"),
                (cli.os, "rename"),
                (cli.os, "unlink"),
                (cli.os, "mkdir"),
                (cli.os, "chmod"),
                (cli.os, "chown"),
                (cli.os, "link"),
                (cli.os, "symlink"),
                (cli.shutil, "copyfile"),
                (cli.shutil, "copytree"),
            ):
                stack.enter_context(
                    mock.patch.object(owner, name, side_effect=forbidden)
                )
            result = self.run_cli()
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertEqual(before, _directory_snapshot(self.repeated))


if __name__ == "__main__":
    unittest.main()
