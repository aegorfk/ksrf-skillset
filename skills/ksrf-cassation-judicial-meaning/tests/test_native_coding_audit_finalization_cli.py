from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from judicial_meaning.cli import read_json, read_jsonl, write_jsonl
import judicial_meaning.cli as cli_module
from judicial_meaning.practice_quality import canonical_digest

if __package__:
    from . import test_native_coding_review_import_cli as import_harness
else:
    import test_native_coding_review_import_cli as import_harness


REPO = import_harness.REPO
SCRIPT = import_harness.SCRIPT
SKILL_ROOT = import_harness.SKILL_ROOT


FINALIZATION_FILES = {
    "resolved-review-decisions.jsonl",
    "adjudications.jsonl",
    "coding-reliability.json",
    "coding-audit-finalization-receipt.json",
}


class NativeCodingAuditFinalizationCliTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.install_tmp = tempfile.TemporaryDirectory()
        cls.installed = Path(cls.install_tmp.name) / "installed skills"
        completed = subprocess.run(
            [str(REPO / "install.sh"), "--target", str(cls.installed)],
            cwd=REPO,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        schema = json.loads(
            (SKILL_ROOT / "schemas" / "practice-quality.v1.json").read_text(
                encoding="utf-8"
            )
        )
        cls.schema_validator = Draft202012Validator(schema)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.install_tmp.cleanup()

    _run = staticmethod(import_harness.NativeCodingReviewImportCliTests._run)
    _seed_workspace = import_harness.NativeCodingReviewImportCliTests._seed_workspace
    _prepare_bundle = import_harness.NativeCodingReviewImportCliTests._prepare_bundle
    _secondary_records = staticmethod(
        import_harness.NativeCodingReviewImportCliTests._secondary_records
    )
    _write_secondary = staticmethod(
        import_harness.NativeCodingReviewImportCliTests._write_secondary
    )
    _import_arguments = staticmethod(
        import_harness.NativeCodingReviewImportCliTests._import_arguments
    )

    def _assert_schema_valid(self, value: object) -> None:
        errors = sorted(
            self.schema_validator.iter_errors(value),
            key=lambda error: list(error.absolute_path),
        )
        self.assertEqual([], [error.message for error in errors])

    def _import_review(
        self,
        root: Path,
        bundle: Path,
        manifest_sha256: str,
        secondary_records: list[dict[str, object]],
    ) -> tuple[Path, dict[str, object]]:
        secondary = self._write_secondary(root, secondary_records)
        destination = root / "native-import"
        completed = self._run(
            REPO / SCRIPT,
            self._import_arguments(
                bundle,
                secondary,
                destination,
                manifest_sha256,
            ),
            cwd=root,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        return destination, json.loads(completed.stdout)

    @staticmethod
    def _finalization_arguments(
        bundle: Path,
        manifest_sha256: str,
        audit_import: Path,
        import_receipt_sha256: str,
        destination: Path,
        *,
        resolutions: Path | None = None,
    ) -> list[str]:
        arguments = [
            "quality",
            "coding-audit-finalize",
            "--bundle",
            str(bundle),
            "--expected-manifest-sha256",
            manifest_sha256,
            "--audit-import",
            str(audit_import),
            "--expected-import-receipt-sha256",
            import_receipt_sha256,
            "--output-dir",
            str(destination),
        ]
        if resolutions is not None:
            arguments.extend(["--resolutions", str(resolutions)])
        return arguments

    @staticmethod
    def _resolution_rows(
        bundle: Path,
        audit_import: Path,
        import_receipt_sha256: str,
    ) -> list[dict[str, object]]:
        receipt = read_json(
            audit_import / "coding-audit-review-import-receipt.json"
        )
        decisions = {
            row["candidate_id"]: row
            for row in read_jsonl(audit_import / "audit-decisions.jsonl")
        }
        fields_by_candidate: dict[str, list[str]] = {}
        for map_name in (
            "audited_field_differences",
            "non_audited_content_differences",
        ):
            for item in receipt[map_name]:
                fields_by_candidate.setdefault(item["candidate_id"], []).extend(
                    item["fields"]
                )
        primary = {
            row["candidate_id"]: row
            for row in read_jsonl(bundle / "primary-decisions.audit.jsonl")
        }
        return [
            {
                "schema_version": "1.0",
                "import_receipt_sha256": import_receipt_sha256,
                "candidate_id": candidate_id,
                "difference_fields": fields,
                "primary_coding_sha256": canonical_digest(primary[candidate_id]),
                "secondary_coding_sha256": decisions[candidate_id][
                    "secondary_coding_sha256"
                ],
                "field_resolutions": [
                    {"field": field, "choice": "primary"} for field in fields
                ],
                "reviewer_pseudonym": "resolver-pseudonym",
                "reviewed_at": "2025-09-04T12:00:00+03:00",
                "human_review": "approved",
                "full_text_reviewed": True,
                "quote_locators_reviewed": True,
                "final_coding_approved": True,
            }
            for candidate_id, fields in fields_by_candidate.items()
        ]

    def test_no_difference_finalization_publishes_exact_private_four_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            secondary = self._secondary_records(bundle)
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                secondary,
            )
            destination = root / "finalized"
            completed = self._run(
                REPO / SCRIPT,
                self._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    import_result["receipt_sha256"],
                    destination,
                ),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual("coding_audit_finalization_receipt", payload["artifact_type"])
            self.assertTrue(payload["difference_resolution_bijection_verified"])
            self.assertTrue(payload["reliability_complete"])
            self.assertFalse(payload["quote_locator_verified"])
            self.assertNotIn(str(root), completed.stdout)
            self.assertEqual(FINALIZATION_FILES, {path.name for path in destination.iterdir()})
            self.assertEqual(0o700, stat.S_IMODE(destination.stat().st_mode))
            for path in destination.iterdir():
                self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode), path.name)

            receipt = read_json(
                destination / "coding-audit-finalization-receipt.json"
            )
            self._assert_schema_valid(receipt)
            for decision in read_jsonl(
                destination / "resolved-review-decisions.jsonl"
            ):
                self._assert_schema_valid(decision)
            unsigned = {
                key: value for key, value in receipt.items() if key != "receipt_sha256"
            }
            self.assertEqual(canonical_digest(unsigned), receipt["receipt_sha256"])
            self.assertEqual(payload["receipt_sha256"], receipt["receipt_sha256"])
            self.assertFalse(receipt["resolutions_present"])
            self.assertIsNone(receipt["resolutions_file_sha256"])
            self.assertFalse(receipt["quote_locator_review_declared"])
            self.assertTrue(read_json(destination / "coding-reliability.json")["complete"])
            self.assertEqual([], read_jsonl(destination / "adjudications.jsonl"))
            receipt_text = json.dumps(receipt, ensure_ascii=False)
            self.assertNotIn("primary-reviewer", receipt_text)
            self.assertNotIn("secondary-reviewer", receipt_text)
            self.assertNotIn("срок подлежит восстановлению", receipt_text)

    def test_missing_resolutions_is_readable_incomplete_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            secondary = self._secondary_records(bundle)
            secondary[0]["proposition"] = "Иная проверяемая формулировка."
            secondary[0]["relation"] = "neutral"
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                secondary,
            )
            destination = root / "incomplete-finalization"
            completed = self._run(
                REPO / SCRIPT,
                self._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    import_result["receipt_sha256"],
                    destination,
                ),
                cwd=root,
            )
            self.assertEqual(3, completed.returncode, completed.stderr)
            self.assertEqual("", completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertFalse(payload["complete"])
            self.assertFalse(payload["output_created"])
            self.assertEqual(
                {
                    "artifact_type",
                    "complete",
                    "incomplete_reason",
                    "missing_difference_pairs",
                    "output_created",
                    "publication_safe",
                    "legal_readiness",
                },
                set(payload),
            )
            self.assertEqual("resolution_incomplete", payload["incomplete_reason"])
            self.assertTrue(payload["missing_difference_pairs"])
            self.assertFalse(destination.exists())
            self.assertEqual([], list(root.glob(f".{destination.name}.staging-*")))
            self.assertNotIn("Иная проверяемая формулировка", completed.stdout)

    def test_unresolved_reliability_returns_only_value_free_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                self._secondary_records(bundle),
            )
            destination = root / "unresolved-reliability"
            real_builder = cli_module.build_native_coding_audit_finalization

            def force_unresolved(*args: object, **kwargs: object) -> dict[str, object]:
                result = dict(real_builder(*args, **kwargs))
                report = dict(result["coding_reliability"])
                candidate_id = report["required_candidate_ids"][0]
                report["complete"] = False
                report["unresolved_candidate_ids"] = [candidate_id]
                report["false_exclusion_diagnostics"] = [
                    {
                        "candidate_id": candidate_id,
                        "primary_label": "private-primary-value",
                        "secondary_label": "private-secondary-value",
                        "resolved": False,
                    }
                ]
                result["complete"] = False
                result["incomplete_reason"] = "reliability_unresolved"
                result["coding_reliability"] = report
                result["reliability_complete"] = False
                return result

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(
                    cli_module,
                    "build_native_coding_audit_finalization",
                    side_effect=force_unresolved,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._finalization_arguments(
                        bundle,
                        manifest_sha256,
                        audit_import,
                        import_result["receipt_sha256"],
                        destination,
                    )
                )
            self.assertEqual(3, return_code, stderr.getvalue())
            self.assertEqual("", stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual("reliability_unresolved", payload["incomplete_reason"])
            self.assertFalse(payload["reliability_complete"])
            candidate_id = payload["reliability_diagnostics"][
                "required_candidate_ids"
            ][0]
            self.assertEqual(
                [candidate_id],
                payload["reliability_diagnostics"]["unresolved_candidate_ids"],
            )
            self.assertEqual(
                [candidate_id],
                payload["reliability_diagnostics"][
                    "false_exclusion_candidate_ids"
                ],
            )
            self.assertNotIn("private-primary-value", stdout.getvalue())
            self.assertNotIn("private-secondary-value", stdout.getvalue())
            self.assertFalse(destination.exists())

    def test_complete_resolutions_publish_derived_decisions_and_bind_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            secondary = self._secondary_records(bundle)
            secondary[0]["proposition"] = "Иная проверяемая формулировка."
            secondary[0]["quote"] = "статья 10 применяется"
            secondary[0]["quote_locator"] = "другой абзац"
            secondary[0]["material_facts"] = ["иной видимый факт"]
            secondary[0]["relation"] = "neutral"
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                secondary,
            )
            rows = self._resolution_rows(
                bundle,
                audit_import,
                import_result["receipt_sha256"],
            )
            resolutions = root / "resolutions.jsonl"
            write_jsonl(resolutions, rows)
            os.chmod(resolutions, 0o600)
            destination = root / "resolved-finalization"
            completed = self._run(
                REPO / SCRIPT,
                self._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    import_result["receipt_sha256"],
                    destination,
                    resolutions=resolutions,
                ),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            decisions = read_jsonl(destination / "resolved-review-decisions.jsonl")
            first = decisions[0]
            self.assertEqual("supports", first["final_coding"]["relation"])
            self.assertEqual(
                "Суд связал восстановление срока с исходом дела.",
                first["final_coding"]["proposition"],
            )
            self.assertEqual("resolver-pseudonym", first["final_coding"]["coder"])
            self.assertEqual(canonical_digest(first["final_coding"]), first["final_coding_sha256"])
            receipt = read_json(
                destination / "coding-audit-finalization-receipt.json"
            )
            self._assert_schema_valid(receipt)
            for decision in decisions:
                self._assert_schema_valid(decision)
            self.assertTrue(receipt["resolutions_present"])
            self.assertEqual(
                hashlib.sha256(resolutions.read_bytes()).hexdigest(),
                receipt["resolutions_file_sha256"],
            )
            for filename, receipt_field in (
                (
                    "resolved-review-decisions.jsonl",
                    "resolved_review_decisions_file_sha256",
                ),
                ("adjudications.jsonl", "adjudications_file_sha256"),
                ("coding-reliability.json", "coding_reliability_file_sha256"),
            ):
                self.assertEqual(
                    hashlib.sha256((destination / filename).read_bytes()).hexdigest(),
                    receipt[receipt_field],
                )
            self.assertTrue(receipt["quote_locator_review_declared"])
            self.assertFalse(receipt["quote_locator_verified"])

    def test_source_and_clean_install_publish_identical_validated_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                self._secondary_records(bundle),
            )
            installed_script = (
                self.installed
                / "ksrf-cassation-judicial-meaning"
                / "scripts"
                / "judicial_meaning.py"
            )
            observed: list[tuple[str, dict[str, bytes]]] = []
            for label, script in (
                ("source", REPO / SCRIPT),
                ("installed", installed_script),
            ):
                destination = root / f"finalized-{label}"
                completed = self._run(
                    script,
                    self._finalization_arguments(
                        bundle,
                        manifest_sha256,
                        audit_import,
                        import_result["receipt_sha256"],
                        destination,
                    ),
                    cwd=root,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertEqual(
                    read_json(
                        destination / "coding-audit-finalization-receipt.json"
                    )["receipt_sha256"],
                    payload["receipt_sha256"],
                )
                receipt = read_json(
                    destination / "coding-audit-finalization-receipt.json"
                )
                self._assert_schema_valid(receipt)
                for decision in read_jsonl(
                    destination / "resolved-review-decisions.jsonl"
                ):
                    self._assert_schema_valid(decision)
                observed.append(
                    (
                        completed.stdout,
                        {
                            filename: (destination / filename).read_bytes()
                            for filename in FINALIZATION_FILES
                        },
                    )
                )
            self.assertEqual(observed[0], observed[1])

    def test_wrong_external_import_anchor_and_unsafe_import_mode_are_code_two(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                self._secondary_records(bundle),
            )
            wrong_destination = root / "wrong-anchor"
            wrong = self._run(
                REPO / SCRIPT,
                self._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    "0" * 64,
                    wrong_destination,
                ),
                cwd=root,
            )
            self.assertEqual(2, wrong.returncode, wrong.stdout)
            self.assertEqual("", wrong.stdout)
            self.assertIn("отдельно сохранённым", wrong.stderr)
            self.assertFalse(wrong_destination.exists())

            os.chmod(audit_import, 0o755)
            unsafe_destination = root / "unsafe-import"
            unsafe = self._run(
                REPO / SCRIPT,
                self._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    import_result["receipt_sha256"],
                    unsafe_destination,
                ),
                cwd=root,
            )
            self.assertEqual(2, unsafe.returncode, unsafe.stdout)
            self.assertEqual("", unsafe.stdout)
            self.assertIn("режимом 0700", unsafe.stderr)
            self.assertFalse(unsafe_destination.exists())

    def test_import_recapture_drift_is_code_two_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                self._secondary_records(bundle),
            )
            destination = root / "import-drift"
            arguments = self._finalization_arguments(
                bundle,
                manifest_sha256,
                audit_import,
                import_result["receipt_sha256"],
                destination,
            )
            real_capture = cli_module._capture_audit_review_import_at
            capture_calls = 0

            def mutate_before_recapture(
                parent_descriptor: int,
                import_name: str,
            ) -> dict[str, object]:
                nonlocal capture_calls
                capture_calls += 1
                if capture_calls == 2:
                    receipt_path = (
                        audit_import / "coding-audit-review-import-receipt.json"
                    )
                    observed = receipt_path.stat()
                    os.utime(
                        receipt_path,
                        ns=(observed.st_atime_ns, observed.st_mtime_ns + 1_000_000_000),
                    )
                return real_capture(parent_descriptor, import_name)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(
                    cli_module,
                    "_capture_audit_review_import_at",
                    side_effect=mutate_before_recapture,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(arguments)
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("Входы изменились", stderr.getvalue())
            self.assertFalse(destination.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX file modes required")
    def test_resolutions_must_be_private_owned_sibling_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            secondary = self._secondary_records(bundle)
            secondary[0]["relation"] = "neutral"
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                secondary,
            )
            rows = self._resolution_rows(
                bundle,
                audit_import,
                import_result["receipt_sha256"],
            )
            resolutions = root / "resolutions.jsonl"
            write_jsonl(resolutions, rows)
            os.chmod(resolutions, 0o644)

            destination = root / "unsafe-resolution-mode"
            completed = self._run(
                REPO / SCRIPT,
                self._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    import_result["receipt_sha256"],
                    destination,
                    resolutions=resolutions,
                ),
                cwd=root,
            )
            self.assertEqual(2, completed.returncode)
            self.assertEqual("", completed.stdout)
            self.assertIn("режима 0600", completed.stderr)
            self.assertFalse(destination.exists())

            nested = root / "nested"
            nested.mkdir()
            nested_resolutions = nested / resolutions.name
            nested_resolutions.write_bytes(resolutions.read_bytes())
            os.chmod(nested_resolutions, 0o600)
            sibling_destination = root / "wrong-resolution-parent"
            completed = self._run(
                REPO / SCRIPT,
                self._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    import_result["receipt_sha256"],
                    sibling_destination,
                    resolutions=nested_resolutions,
                ),
                cwd=root,
            )
            self.assertEqual(2, completed.returncode)
            self.assertEqual("", completed.stdout)
            self.assertIn("приватным соседним файлом", completed.stderr)
            self.assertFalse(sibling_destination.exists())

            os.chmod(resolutions, 0o600)
            unsafe_resolution_inputs: list[Path] = []
            hardlink = root / "resolutions-hardlink.jsonl"
            os.link(resolutions, hardlink)
            unsafe_resolution_inputs.append(hardlink)
            symlink = root / "resolutions-symlink.jsonl"
            symlink.symlink_to(resolutions.name)
            unsafe_resolution_inputs.append(symlink)
            fifo = root / "resolutions-fifo.jsonl"
            os.mkfifo(fifo, 0o600)
            unsafe_resolution_inputs.append(fifo)
            for unsafe_resolutions in unsafe_resolution_inputs:
                unsafe_destination = root / f"unsafe-{unsafe_resolutions.stem}"
                completed = self._run(
                    REPO / SCRIPT,
                    self._finalization_arguments(
                        bundle,
                        manifest_sha256,
                        audit_import,
                        import_result["receipt_sha256"],
                        unsafe_destination,
                        resolutions=unsafe_resolutions,
                    ),
                    cwd=root,
                )
                self.assertEqual(2, completed.returncode)
                self.assertEqual("", completed.stdout)
                self.assertFalse(unsafe_destination.exists())
            self.assertEqual([], list(root.glob(f".{destination.name}.staging-*")))

    def test_confirmation_failure_preserves_four_files_and_invalidates_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                self._secondary_records(bundle),
            )
            destination = root / "confirmation-failure"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(
                    cli_module,
                    "_write_stdout_line",
                    side_effect=BrokenPipeError("имитация закрытого stdout"),
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._finalization_arguments(
                        bundle,
                        manifest_sha256,
                        audit_import,
                        import_result["receipt_sha256"],
                        destination,
                    )
                )
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(
                FINALIZATION_FILES,
                {path.name for path in destination.iterdir()},
            )
            diagnostic = stderr.getvalue()
            self.assertIn("машиночитаемое подтверждение", diagnostic)
            self.assertIn("недействительным", diagnostic)
            self.assertIn("другую отсутствующую соседнюю папку", diagnostic)

    def test_short_write_and_full_looking_flush_failure_are_confirmation_uncertain(
        self,
    ) -> None:
        class ShortWrite(io.StringIO):
            def write(self, value: str) -> int:
                prefix = value[: max(1, len(value) // 2)]
                super().write(prefix)
                return len(prefix)

        class FlushFailure(io.StringIO):
            def flush(self) -> None:
                raise BrokenPipeError("имитация отказа flush")

        for phase in ("short-write", "flush"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as raw_root:
                root = Path(raw_root)
                _, bundle, manifest_sha256 = self._prepare_bundle(root)
                audit_import, import_result = self._import_review(
                    root,
                    bundle,
                    manifest_sha256,
                    self._secondary_records(bundle),
                )
                destination = root / f"confirmation-{phase}"
                stdout = ShortWrite() if phase == "short-write" else FlushFailure()
                stderr = io.StringIO()
                with (
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main(
                        self._finalization_arguments(
                            bundle,
                            manifest_sha256,
                            audit_import,
                            import_result["receipt_sha256"],
                            destination,
                        )
                    )
                self.assertEqual(2, return_code)
                self.assertEqual(
                    FINALIZATION_FILES,
                    {path.name for path in destination.iterdir()},
                )
                if phase == "short-write":
                    self.assertTrue(stdout.getvalue().startswith("{"))
                    self.assertNotIn("\n", stdout.getvalue())
                else:
                    self.assertEqual(
                        "coding_audit_finalization_receipt",
                        json.loads(stdout.getvalue())["artifact_type"],
                    )
                self.assertIn("считайте его недействительным", stderr.getvalue())

    def test_parent_close_failure_after_publish_is_finalization_uncertain(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                self._secondary_records(bundle),
            )
            destination = root / "parent-close-failure"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_close = cli_module._close_command_parent_descriptor

            def close_then_fail(descriptor: int) -> None:
                real_close(descriptor)
                raise OSError("имитация отказа после фактического close")

            with (
                patch.object(
                    cli_module,
                    "_close_command_parent_descriptor",
                    side_effect=close_then_fail,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._finalization_arguments(
                        bundle,
                        manifest_sha256,
                        audit_import,
                        import_result["receipt_sha256"],
                        destination,
                    )
                )
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(
                FINALIZATION_FILES,
                {path.name for path in destination.iterdir()},
            )
            diagnostic = stderr.getvalue()
            self.assertIn("до начала формирования", diagnostic)
            self.assertIn("стандартный вывод ещё не формировался", diagnostic)

    def test_interrupt_after_inner_publication_uses_registered_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                self._secondary_records(bundle),
            )
            destination = root / "inner-return-interrupt"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_inner = cli_module._cmd_quality_coding_audit_finalize

            def publish_then_interrupt(
                *args: object,
                **kwargs: object,
            ) -> tuple[str, tuple[int, int] | None]:
                real_inner(*args, **kwargs)
                self.assertEqual(1, len(kwargs["publication_state"]))
                raise KeyboardInterrupt("имитация прерывания после inner")

            with (
                patch.object(
                    cli_module,
                    "_cmd_quality_coding_audit_finalize",
                    side_effect=publish_then_interrupt,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._finalization_arguments(
                        bundle,
                        manifest_sha256,
                        audit_import,
                        import_result["receipt_sha256"],
                        destination,
                    )
                )
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(
                FINALIZATION_FILES,
                {path.name for path in destination.iterdir()},
            )
            self.assertIn("до начала формирования", stderr.getvalue())
            self.assertNotIn("KeyboardInterrupt", stderr.getvalue())

    def test_interrupt_after_complete_confirmation_invalidates_apparent_success(
        self,
    ) -> None:
        for ordinal, interruption in enumerate(
            (
                KeyboardInterrupt("имитация KeyboardInterrupt перед return"),
                SystemExit("имитация SystemExit перед return"),
            ),
            start=1,
        ):
            with (
                self.subTest(kind=type(interruption).__name__),
                tempfile.TemporaryDirectory() as raw_root,
            ):
                root = Path(raw_root)
                _, bundle, manifest_sha256 = self._prepare_bundle(root)
                audit_import, import_result = self._import_review(
                    root,
                    bundle,
                    manifest_sha256,
                    self._secondary_records(bundle),
                )
                destination = root / f"after-confirmation-{ordinal}"
                stdout = io.StringIO()
                stderr = io.StringIO()
                with (
                    patch.object(
                        cli_module,
                        "_complete_published_command",
                        side_effect=interruption,
                    ),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main(
                        self._finalization_arguments(
                            bundle,
                            manifest_sha256,
                            audit_import,
                            import_result["receipt_sha256"],
                            destination,
                        )
                    )
                self.assertEqual(2, return_code)
                self.assertEqual(
                    "coding_audit_finalization_receipt",
                    json.loads(stdout.getvalue())["artifact_type"],
                )
                self.assertEqual(
                    FINALIZATION_FILES,
                    {path.name for path in destination.iterdir()},
                )
                diagnostic = stderr.getvalue()
                self.assertIn("после начала передачи", diagnostic)
                self.assertIn("выглядеть как полная строка JSON", diagnostic)
                self.assertNotIn(type(interruption).__name__, diagnostic)

    def test_import_must_be_same_actual_parent_and_exact_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root, tempfile.TemporaryDirectory() as raw_other:
            root = Path(raw_root)
            other = Path(raw_other)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                self._secondary_records(bundle),
            )
            moved_import = other / "native-import"
            audit_import.rename(moved_import)
            different_parent = self._run(
                REPO / SCRIPT,
                self._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    moved_import,
                    import_result["receipt_sha256"],
                    root / "different-parent",
                ),
                cwd=root,
            )
            self.assertEqual(2, different_parent.returncode)
            self.assertEqual("", different_parent.stdout)
            self.assertIn("одного фактического родителя", different_parent.stderr)

            moved_import.rename(audit_import)
            unexpected = audit_import / "unexpected.txt"
            unexpected.write_text("не должно приниматься", encoding="utf-8")
            os.chmod(unexpected, 0o600)
            extra_entry = self._run(
                REPO / SCRIPT,
                self._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    import_result["receipt_sha256"],
                    root / "extra-entry",
                ),
                cwd=root,
            )
            self.assertEqual(2, extra_entry.returncode)
            self.assertEqual("", extra_entry.stdout)
            self.assertIn("слишком много записей", extra_entry.stderr)

    @unittest.skipUnless(os.name == "posix", "POSIX file kinds and modes required")
    def test_import_files_reject_mode_hardlink_symlink_and_fifo(self) -> None:
        for unsafe_kind in ("mode", "hardlink", "symlink", "fifo"):
            with (
                self.subTest(unsafe_kind=unsafe_kind),
                tempfile.TemporaryDirectory() as raw_root,
            ):
                root = Path(raw_root)
                _, bundle, manifest_sha256 = self._prepare_bundle(root)
                audit_import, import_result = self._import_review(
                    root,
                    bundle,
                    manifest_sha256,
                    self._secondary_records(bundle),
                )
                receipt_path = (
                    audit_import / "coding-audit-review-import-receipt.json"
                )
                if unsafe_kind == "mode":
                    os.chmod(receipt_path, 0o644)
                elif unsafe_kind == "hardlink":
                    os.link(receipt_path, root / "escaped-receipt-link.json")
                else:
                    receipt_content = receipt_path.read_bytes()
                    receipt_path.unlink()
                    if unsafe_kind == "symlink":
                        shadow = root / "receipt-shadow.json"
                        shadow.write_bytes(receipt_content)
                        os.chmod(shadow, 0o600)
                        receipt_path.symlink_to(shadow)
                    else:
                        os.mkfifo(receipt_path, 0o600)
                destination = root / f"unsafe-{unsafe_kind}"
                completed = self._run(
                    REPO / SCRIPT,
                    self._finalization_arguments(
                        bundle,
                        manifest_sha256,
                        audit_import,
                        import_result["receipt_sha256"],
                        destination,
                    ),
                    cwd=root,
                    timeout=5,
                )
                self.assertEqual(2, completed.returncode)
                self.assertEqual("", completed.stdout)
                self.assertFalse(destination.exists())

    def test_import_receipt_rejects_duplicate_nonfinite_and_oversized_json(self) -> None:
        for invalid_kind in ("duplicate", "nonfinite", "oversized"):
            with (
                self.subTest(invalid_kind=invalid_kind),
                tempfile.TemporaryDirectory() as raw_root,
            ):
                root = Path(raw_root)
                _, bundle, manifest_sha256 = self._prepare_bundle(root)
                audit_import, import_result = self._import_review(
                    root,
                    bundle,
                    manifest_sha256,
                    self._secondary_records(bundle),
                )
                receipt_path = (
                    audit_import / "coding-audit-review-import-receipt.json"
                )
                if invalid_kind == "oversized":
                    with receipt_path.open("r+b") as stream:
                        stream.truncate(
                            cli_module._AUDIT_REVIEW_IMPORT_FILE_LIMITS[
                                "coding-audit-review-import-receipt.json"
                            ]
                            + 1
                        )
                else:
                    original = receipt_path.read_text(encoding="utf-8").rstrip("\n")
                    suffix = (
                        ',"schema_version":"1.0"}'
                        if invalid_kind == "duplicate"
                        else ',"unexpected":NaN}'
                    )
                    receipt_path.write_text(
                        original[:-1] + suffix + "\n",
                        encoding="utf-8",
                    )
                    os.chmod(receipt_path, 0o600)
                destination = root / f"invalid-{invalid_kind}"
                completed = self._run(
                    REPO / SCRIPT,
                    self._finalization_arguments(
                        bundle,
                        manifest_sha256,
                        audit_import,
                        import_result["receipt_sha256"],
                        destination,
                    ),
                    cwd=root,
                )
                self.assertEqual(2, completed.returncode)
                self.assertEqual("", completed.stdout)
                self.assertFalse(destination.exists())

    def test_import_acl_probe_failure_is_fail_closed_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            _, bundle, manifest_sha256 = self._prepare_bundle(root)
            audit_import, import_result = self._import_review(
                root,
                bundle,
                manifest_sha256,
                self._secondary_records(bundle),
            )
            destination = root / "acl-probe-failure"
            real_acl_guard = cli_module._assert_darwin_fd_has_no_extended_acl

            def fail_import_acl(descriptor: int, *, object_label: str) -> None:
                if "штатного импорта" in object_label:
                    raise OSError("отсутствие ACL не подтверждено")
                real_acl_guard(descriptor, object_label=object_label)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(
                    cli_module,
                    "_assert_darwin_fd_has_no_extended_acl",
                    side_effect=fail_import_acl,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._finalization_arguments(
                        bundle,
                        manifest_sha256,
                        audit_import,
                        import_result["receipt_sha256"],
                        destination,
                    )
                )
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("ACL не подтверждено", stderr.getvalue())
            self.assertFalse(destination.exists())

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "geteuid"),
        "effective UID checks require POSIX",
    )
    def test_published_directory_and_file_must_keep_effective_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "published"
            destination.mkdir(mode=0o700)
            payload = destination / "payload.json"
            payload.write_bytes(b"{}\n")
            os.chmod(payload, 0o600)
            directory_stat = destination.stat()
            file_stat = payload.stat()
            parent_descriptor = os.open(
                root,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                arguments = (
                    parent_descriptor,
                    destination.name,
                    (directory_stat.st_dev, directory_stat.st_ino),
                    {payload.name: b"{}\n"},
                    {payload.name: (file_stat.st_dev, file_stat.st_ino)},
                )
                with (
                    patch.object(
                        cli_module.os,
                        "geteuid",
                        return_value=directory_stat.st_uid + 1,
                    ),
                    self.assertRaises(ValueError),
                ):
                    cli_module._assert_published_audit_bundle(*arguments)

                real_stat = os.stat

                def wrong_file_owner(
                    path: object, *args: object, **kwargs: object
                ) -> os.stat_result:
                    observed = real_stat(path, *args, **kwargs)
                    if path == payload.name and kwargs.get("dir_fd") is not None:
                        fields = list(observed)
                        fields[4] = observed.st_uid + 1
                        return os.stat_result(fields)
                    return observed

                with (
                    patch.object(cli_module.os, "stat", side_effect=wrong_file_owner),
                    self.assertRaisesRegex(ValueError, "небезопасный файл"),
                ):
                    cli_module._assert_published_audit_bundle(*arguments)
            finally:
                os.close(parent_descriptor)

    @unittest.skipUnless(os.name == "posix", "POSIX ownership checks required")
    def test_foreign_owner_after_open_blocks_sensitive_write(self) -> None:
        for target in ("staging", "file"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                destination = root / "published"
                real_open = os.open
                real_fstat = os.fstat
                real_write = os.write
                tracked_descriptors: set[int] = set()
                sensitive_writes: list[bytes] = []

                def open_probe(
                    path: object,
                    flags: int,
                    *args: object,
                    **kwargs: object,
                ) -> int:
                    descriptor = real_open(path, flags, *args, **kwargs)
                    is_staging = (
                        target == "staging"
                        and isinstance(path, str)
                        and path.startswith(".published.staging-")
                        and bool(flags & getattr(os, "O_DIRECTORY", 0))
                    )
                    is_file = (
                        target == "file"
                        and path == "secret.bin"
                        and bool(flags & os.O_WRONLY)
                    )
                    if is_staging or is_file:
                        tracked_descriptors.add(descriptor)
                    return descriptor

                def fstat_probe(descriptor: int) -> os.stat_result:
                    observed = real_fstat(descriptor)
                    if descriptor in tracked_descriptors:
                        fields = list(observed)
                        fields[4] = observed.st_uid + 1
                        return os.stat_result(fields)
                    return observed

                def write_probe(descriptor: int, content: bytes) -> int:
                    if descriptor in tracked_descriptors:
                        sensitive_writes.append(bytes(content))
                    return real_write(descriptor, content)

                with (
                    patch.object(cli_module.os, "open", side_effect=open_probe),
                    patch.object(cli_module.os, "fstat", side_effect=fstat_probe),
                    patch.object(cli_module.os, "write", side_effect=write_probe),
                    patch.object(
                        cli_module,
                        "_assert_darwin_fd_has_no_extended_acl",
                        return_value=None,
                    ),
                    self.assertRaises(OSError),
                ):
                    cli_module._publish_new_audit_bundle(
                        destination,
                        {"secret.bin": b"SECRET"},
                    )
                self.assertEqual([], sensitive_writes)
                self.assertFalse(destination.exists())
                self.assertEqual(
                    1,
                    len(list(root.glob(".published.staging-*"))),
                )

    def test_parse_errors_are_actionable_russian_without_argparse_scaffolding(
        self,
    ) -> None:
        missing = self._run(
            REPO / SCRIPT,
            ["quality", "coding-audit-finalize"],
            cwd=REPO,
        )
        self.assertEqual(2, missing.returncode)
        self.assertEqual("", missing.stdout)
        self.assertIn("Использование:", missing.stderr)
        self.assertIn("ошибка:", missing.stderr)
        self.assertIn("не указаны обязательные аргументы:", missing.stderr)

        unknown = self._run(
            REPO / SCRIPT,
            [
                *self._finalization_arguments(
                    Path("bundle"),
                    "0" * 64,
                    Path("audit-import"),
                    "1" * 64,
                    Path("output"),
                ),
                "--неизвестный-параметр",
            ],
            cwd=REPO,
        )
        self.assertEqual(2, unknown.returncode)
        self.assertEqual("", unknown.stdout)
        self.assertIn("неизвестные аргументы: --неизвестный-параметр", unknown.stderr)
        for forbidden in (
            "usage:",
            "error:",
            "the following arguments are required",
            "unrecognized arguments",
        ):
            self.assertNotIn(forbidden, missing.stderr + unknown.stderr)

    def test_help_exposes_native_chain_outputs_limits_and_exit_codes(self) -> None:
        completed = self._run(
            REPO / SCRIPT,
            ["quality", "coding-audit-finalize", "--help"],
            cwd=REPO,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        for fragment in (
            "--expected-import-receipt-sha256",
            "--resolutions",
            "primary|secondary",
            "resolved-review-decisions.jsonl",
            "coding-audit-finalization-receipt.json",
            "quote_locator_verified всегда false",
            "Код 3",
            "Код 2",
            "Код 0",
            "chmod сам по себе не доказывает",
            "не юридическое",
        ):
            self.assertIn(fragment, completed.stdout)


if __name__ == "__main__":
    unittest.main()
