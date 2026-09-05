from __future__ import annotations

import argparse
import ast
import builtins
import contextlib
import io
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

import judicial_meaning.cli as cli_module

if __package__:
    from . import test_native_coding_audit_finalization_cli as finalization_harness
    from . import test_native_coding_review_import_cli as import_harness
else:
    import test_native_coding_audit_finalization_cli as finalization_harness
    import test_native_coding_review_import_cli as import_harness


PARENT_IDENTITY = (101, 202)
DIRECTORY_IDENTITY = (303, 404)
CREATED_FILE_IDENTITIES = {"result.json": (505, 606)}

COMMAND_ARGUMENTS = {
    "coding-audit-prepare": [
        "quality",
        "coding-audit-prepare",
        "--workspace",
        "/private/workspace",
        "--codebook-version",
        "1.0",
        "--sample-size",
        "1",
        "--exclusion-sample-size",
        "1",
        "--output-dir",
        "/private/output",
    ],
    "coding-audit-review-import": [
        "quality",
        "coding-audit-review-import",
        "--bundle",
        "/private/bundle",
        "--expected-manifest-sha256",
        "a" * 64,
        "--expected-secondary-coder",
        "reviewer",
        "--secondary-coding",
        "/private/secondary.jsonl",
        "--output-dir",
        "/private/import",
    ],
    "coding-audit-finalize": [
        "quality",
        "coding-audit-finalize",
        "--bundle",
        "/private/bundle",
        "--expected-manifest-sha256",
        "a" * 64,
        "--audit-import",
        "/private/import",
        "--expected-import-receipt-sha256",
        "b" * 64,
        "--output-dir",
        "/private/finalization",
    ],
}

EXPECTED_SCOPE = {
    "diagnostic_only": True,
    "same_destination_retry_allowed": False,
    "recovery_eligibility_verified": False,
    "recovery_action_authorized": False,
    "downstream_use_allowed": False,
    "automatic_retry_performed": False,
    "automatic_delete_performed": False,
    "automatic_quarantine_performed": False,
    "diagnostic_provenance_authenticated": False,
    "publication_safe": False,
    "legal_readiness": False,
    "filing_authorized": False,
}


class _ParserStub:
    def __init__(self, namespace: argparse.Namespace):
        self._namespace = namespace

    def parse_args(self, argv: list[str] | None) -> argparse.Namespace:
        return self._namespace


class _TrackedStderr(io.StringIO):
    def __init__(self, *, short_write: bool = False, fail_flush: bool = False):
        super().__init__()
        self.short_write = short_write
        self.fail_flush = fail_flush
        self.write_calls = 0
        self.flush_calls = 0

    def write(self, value: str) -> int:
        self.write_calls += 1
        if self.short_write:
            prefix = value[: max(0, len(value) - 1)]
            super().write(prefix)
            return len(prefix)
        return super().write(value)

    def flush(self) -> None:
        self.flush_calls += 1
        if self.fail_flush:
            raise BrokenPipeError("simulated stderr flush failure")
        super().flush()


class PublicationRecoveryDiagnosticCliTests(unittest.TestCase):
    maxDiff = None

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
    _finalization_arguments = staticmethod(
        finalization_harness.NativeCodingAuditFinalizationCliTests._finalization_arguments
    )

    @staticmethod
    def _run_main(arguments: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            return_code = cli_module.main(arguments)
        return return_code, stdout.getvalue(), stderr.getvalue()

    @staticmethod
    def _published_file_bytes(destination: Path) -> dict[str, bytes]:
        return {
            path.relative_to(destination).as_posix(): path.read_bytes()
            for path in sorted(destination.rglob("*"))
            if path.is_file()
        }

    def _assert_success_flag_parity(
        self,
        arguments: list[str],
        *,
        destination: Path,
    ) -> None:
        default = self._run_main(arguments)
        default_files = self._published_file_bytes(destination)
        shutil.rmtree(destination)
        structured = self._run_main(
            [*arguments, "--recovery-diagnostic-json"]
        )

        self.assertEqual(0, default[0], default[2])
        self.assertEqual(0, structured[0], structured[2])
        self.assertEqual(default[1], structured[1])
        self.assertEqual("", default[2])
        self.assertEqual(default[2], structured[2])
        self.assertEqual(
            default_files,
            self._published_file_bytes(destination),
        )

    def test_prepare_success_is_byte_identical_with_structured_flag(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = self._seed_workspace(root, candidate_count=1)
            destination = root / "prepare-output"
            self._assert_success_flag_parity(
                [
                    "quality",
                    "coding-audit-prepare",
                    "--workspace",
                    str(state["workspace"]),
                    "--codebook-version",
                    "1.0",
                    "--sample-size",
                    "1",
                    "--exclusion-sample-size",
                    "1",
                    "--output-dir",
                    str(destination),
                ],
                destination=destination,
            )

    def test_review_import_success_is_byte_identical_with_structured_flag(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, bundle, manifest_sha256 = self._prepare_bundle(
                root,
                candidate_count=1,
            )
            secondary = self._write_secondary(
                root,
                self._secondary_records(bundle),
            )
            destination = root / "import-output"
            self._assert_success_flag_parity(
                self._import_arguments(
                    bundle,
                    secondary,
                    destination,
                    manifest_sha256,
                ),
                destination=destination,
            )

    def test_finalizer_success_is_byte_identical_with_structured_flag(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, bundle, manifest_sha256 = self._prepare_bundle(
                root,
                candidate_count=1,
            )
            secondary = self._write_secondary(
                root,
                self._secondary_records(bundle),
            )
            audit_import = root / "native-import"
            import_code, import_stdout, import_stderr = self._run_main(
                self._import_arguments(
                    bundle,
                    secondary,
                    audit_import,
                    manifest_sha256,
                )
            )
            self.assertEqual(0, import_code, import_stderr)
            import_receipt_sha256 = json.loads(import_stdout)["receipt_sha256"]

            destination = root / "finalization-output"
            self._assert_success_flag_parity(
                self._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    import_receipt_sha256,
                    destination,
                ),
                destination=destination,
            )

    def test_finalizer_incomplete_is_byte_identical_with_structured_flag(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, bundle, manifest_sha256 = self._prepare_bundle(
                root,
                candidate_count=1,
            )
            secondary_records = self._secondary_records(bundle)
            secondary_records[0]["proposition"] = (
                "Иная проверяемая формулировка для неполной финализации."
            )
            secondary_records[0]["relation"] = "neutral"
            secondary = self._write_secondary(root, secondary_records)
            audit_import = root / "native-import"
            import_code, import_stdout, import_stderr = self._run_main(
                self._import_arguments(
                    bundle,
                    secondary,
                    audit_import,
                    manifest_sha256,
                )
            )
            self.assertEqual(0, import_code, import_stderr)
            import_receipt_sha256 = json.loads(import_stdout)["receipt_sha256"]

            destination = root / "incomplete-output"
            default_arguments = self._finalization_arguments(
                bundle,
                manifest_sha256,
                audit_import,
                import_receipt_sha256,
                destination,
            )
            default = self._run_main(default_arguments)
            self.assertFalse(destination.exists())
            self.assertEqual(
                [],
                list(root.glob(f".{destination.name}.staging-*")),
            )
            structured = self._run_main(
                [*default_arguments, "--recovery-diagnostic-json"]
            )

            self.assertEqual(3, default[0], default[2])
            self.assertEqual(default, structured)
            self.assertEqual("", default[2])
            self.assertFalse(destination.exists())
            self.assertEqual(
                [],
                list(root.glob(f".{destination.name}.staging-*")),
            )

    @staticmethod
    def _errors() -> tuple[tuple[BaseException, str, str, str], ...]:
        return (
            (
                cli_module._staging_cleanup_uncertain_error(
                    PARENT_IDENTITY,
                    ".output.staging-fixed",
                    DIRECTORY_IDENTITY,
                    CREATED_FILE_IDENTITIES,
                ),
                "staging_cleanup_uncertain",
                "administrator_only",
                "empty_invalid",
            ),
            (
                cli_module._publication_state_uncertain_error(
                    PARENT_IDENTITY,
                    "output",
                    DIRECTORY_IDENTITY,
                    CREATED_FILE_IDENTITIES,
                ),
                "publication_state_uncertain",
                "administrator_only",
                "empty_invalid",
            ),
            (
                cli_module._publication_durability_uncertain_error(),
                "publication_durability_uncertain",
                "repeat_then_compare_candidate",
                "empty_invalid",
            ),
            (
                cli_module._publication_finalization_uncertain_error(
                    PARENT_IDENTITY,
                    "output",
                    DIRECTORY_IDENTITY,
                ),
                "publication_finalization_uncertain",
                "repeat_then_compare_candidate",
                "empty_invalid",
            ),
            (
                cli_module._publication_confirmation_delivery_error(
                    PARENT_IDENTITY,
                    "output",
                    DIRECTORY_IDENTITY,
                ),
                "confirmation_delivery_uncertain",
                "repeat_then_compare_candidate",
                "empty_partial_or_apparent_complete_invalid",
            ),
        )

    @staticmethod
    def _main_namespace(
        handler: object,
        *,
        structured: bool,
        command: str = "coding-audit-review-import",
    ) -> argparse.Namespace:
        return argparse.Namespace(
            func=handler,
            command="quality",
            quality_command=command,
            recovery_diagnostic_json=structured,
        )

    def test_all_factories_carry_closed_code_route_and_stdout_contract(self) -> None:
        expected_top_level = {
            "schema_version",
            "artifact_type",
            "command",
            "error_code",
            "recovery_route",
            "stdout_disposition",
            "message_ru",
            "exit_code",
            "scope",
        }
        for error, code, route, stdout_disposition in self._errors():
            with self.subTest(code=code):
                self.assertIsInstance(error, cli_module._PublicationRecoveryError)
                self.assertEqual(code, error.error_code)
                line = cli_module._publication_recovery_diagnostic_line(
                    error,
                    command="coding-audit-review-import",
                )
                payload = json.loads(line)
                self.assertEqual(expected_top_level, set(payload))
                self.assertEqual("1.0", payload["schema_version"])
                self.assertEqual(
                    "coding_audit_publication_recovery_diagnostic",
                    payload["artifact_type"],
                )
                self.assertEqual("coding-audit-review-import", payload["command"])
                self.assertEqual(code, payload["error_code"])
                self.assertEqual(route, payload["recovery_route"])
                self.assertEqual(
                    stdout_disposition,
                    payload["stdout_disposition"],
                )
                self.assertEqual(str(error), payload["message_ru"])
                self.assertEqual(2, payload["exit_code"])
                self.assertEqual(EXPECTED_SCOPE, payload["scope"])

    def test_diagnostic_line_is_compact_ascii_canonical_single_line(self) -> None:
        error = cli_module._publication_state_uncertain_error(
            PARENT_IDENTITY,
            'hostile\n{"forged":true}\x1b[31m\u202e',
            DIRECTORY_IDENTITY,
            CREATED_FILE_IDENTITIES,
        )
        line = cli_module._publication_recovery_diagnostic_line(
            error,
            command="coding-audit-prepare",
        )
        payload = json.loads(line)

        self.assertEqual(1, line.count("\n"))
        self.assertTrue(line.endswith("\n"))
        line.encode("ascii")
        self.assertNotIn("\x1b", line)
        self.assertNotIn("\u202e", line)
        self.assertNotIn("\n", payload["message_ru"])
        self.assertIn("\\n", payload["message_ru"])
        self.assertIn("\\u001b", payload["message_ru"])
        self.assertIn("\\u202e", payload["message_ru"])
        self.assertEqual(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n",
            line,
        )

    def test_exception_cause_and_absolute_inputs_are_not_serialized(self) -> None:
        secret = "SECRET-CAUSE-/private/client/case-123"
        try:
            raise cli_module._publication_durability_uncertain_error() from OSError(
                secret
            )
        except cli_module._PublicationRecoveryError as error:
            line = cli_module._publication_recovery_diagnostic_line(
                error,
                command="coding-audit-finalize",
            )

        self.assertNotIn(secret, line)
        self.assertNotIn("/private/client", line)
        self.assertNotIn("traceback", line.lower())

    def test_unknown_error_code_and_command_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            cli_module._PublicationRecoveryError(
                "unknown recovery",
                error_code="unknown_recovery_state",
            )

        error = cli_module._publication_durability_uncertain_error()
        with self.assertRaises(ValueError):
            cli_module._publication_recovery_diagnostic_line(
                error,
                command="quality-from-user-input",
            )

    def test_default_main_error_is_byte_identical_human_text(self) -> None:
        error = cli_module._publication_state_uncertain_error(
            PARENT_IDENTITY,
            "output",
            DIRECTORY_IDENTITY,
            CREATED_FILE_IDENTITIES,
        )

        def fail(_args: argparse.Namespace) -> int:
            raise error

        namespace = self._main_namespace(fail, structured=False)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(cli_module, "build_parser", return_value=_ParserStub(namespace)),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            return_code = cli_module.main([])

        self.assertEqual(2, return_code)
        self.assertEqual("", stdout.getvalue())
        self.assertEqual(f"Ошибка: {error}\n", stderr.getvalue())

    def test_structured_main_branch_is_exact_for_all_three_commands(self) -> None:
        for command in COMMAND_ARGUMENTS:
            with self.subTest(command=command):
                error = cli_module._publication_finalization_uncertain_error(
                    PARENT_IDENTITY,
                    "output",
                    DIRECTORY_IDENTITY,
                )

                def fail(_args: argparse.Namespace, selected: BaseException = error) -> int:
                    raise selected

                namespace = self._main_namespace(
                    fail,
                    structured=True,
                    command=command,
                )
                stdout = io.StringIO()
                stderr = io.StringIO()
                with (
                    patch.object(
                        cli_module,
                        "build_parser",
                        return_value=_ParserStub(namespace),
                    ),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main([])

                self.assertEqual(2, return_code)
                self.assertEqual("", stdout.getvalue())
                payload = json.loads(stderr.getvalue())
                self.assertEqual(command, payload["command"])
                self.assertEqual(
                    "publication_finalization_uncertain",
                    payload["error_code"],
                )

    def _run_real_parent_close_failure(
        self,
        arguments: list[str],
        *,
        expected_command: str,
        destination: Path,
    ) -> None:
        real_close = cli_module._close_command_parent_descriptor
        close_calls = 0

        def close_then_fail(descriptor: int) -> None:
            nonlocal close_calls
            close_calls += 1
            real_close(descriptor)
            raise OSError("simulated parent close failure after publication")

        stdout = io.StringIO()
        stderr = io.StringIO()
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
                [*arguments, "--recovery-diagnostic-json"]
            )

        self.assertEqual(2, return_code)
        self.assertEqual(1, close_calls)
        self.assertEqual("", stdout.getvalue())
        self.assertTrue(destination.is_dir())
        self.assertTrue(any(destination.iterdir()))
        payload = json.loads(stderr.getvalue())
        self.assertEqual(expected_command, payload["command"])
        self.assertEqual(
            "publication_finalization_uncertain",
            payload["error_code"],
        )
        self.assertEqual(
            "repeat_then_compare_candidate",
            payload["recovery_route"],
        )
        self.assertEqual("empty_invalid", payload["stdout_disposition"])
        self.assertFalse(payload["scope"]["recovery_action_authorized"])

    def test_real_publishers_emit_structured_parent_close_diagnostic(self) -> None:
        with self.subTest(command="coding-audit-prepare"), tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = self._seed_workspace(root, candidate_count=1)
            destination = root / "prepare-recovery"
            arguments = [
                "quality",
                "coding-audit-prepare",
                "--workspace",
                str(state["workspace"]),
                "--codebook-version",
                "1.0",
                "--sample-size",
                "1",
                "--exclusion-sample-size",
                "1",
                "--output-dir",
                str(destination),
            ]
            self._run_real_parent_close_failure(
                arguments,
                expected_command="coding-audit-prepare",
                destination=destination,
            )

        with self.subTest(command="coding-audit-review-import"), tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, bundle, manifest_sha256 = self._prepare_bundle(
                root,
                candidate_count=1,
            )
            secondary = self._write_secondary(
                root,
                self._secondary_records(bundle),
            )
            destination = root / "import-recovery"
            self._run_real_parent_close_failure(
                self._import_arguments(
                    bundle,
                    secondary,
                    destination,
                    manifest_sha256,
                ),
                expected_command="coding-audit-review-import",
                destination=destination,
            )

        with self.subTest(command="coding-audit-finalize"), tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, bundle, manifest_sha256 = self._prepare_bundle(
                root,
                candidate_count=1,
            )
            secondary = self._write_secondary(
                root,
                self._secondary_records(bundle),
            )
            audit_import = root / "native-import"
            import_stdout = io.StringIO()
            import_stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(import_stdout),
                contextlib.redirect_stderr(import_stderr),
            ):
                import_code = cli_module.main(
                    self._import_arguments(
                        bundle,
                        secondary,
                        audit_import,
                        manifest_sha256,
                    )
                )
            self.assertEqual(0, import_code, import_stderr.getvalue())
            import_receipt_sha256 = json.loads(import_stdout.getvalue())[
                "receipt_sha256"
            ]
            destination = root / "finalization-recovery"
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
            self._run_real_parent_close_failure(
                arguments,
                expected_command="coding-audit-finalize",
                destination=destination,
            )

    def test_real_double_fault_keeps_publication_state_administrator_route(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            destination = root / "double-fault-output"
            files = {"result.json": b'{"private":"payload"}\n'}
            real_assert = cli_module._assert_published_audit_bundle
            real_close = cli_module.os.close
            assertion_calls = 0
            state_failure_started = False
            close_failure_raised = False

            def fail_second_published_state_check(*args: object, **kwargs: object) -> None:
                nonlocal assertion_calls, state_failure_started
                assertion_calls += 1
                if assertion_calls == 2:
                    state_failure_started = True
                    raise OSError("simulated published state drift")
                real_assert(*args, **kwargs)

            def fail_one_final_close(descriptor: int) -> None:
                nonlocal close_failure_raised
                real_close(descriptor)
                if state_failure_started and not close_failure_raised:
                    close_failure_raised = True
                    raise OSError("simulated concurrent descriptor close failure")

            with (
                patch.object(
                    cli_module,
                    "_assert_published_audit_bundle",
                    side_effect=fail_second_published_state_check,
                ),
                patch.object(cli_module.os, "close", side_effect=fail_one_final_close),
                self.assertRaises(cli_module._PublicationRecoveryError) as raised,
            ):
                cli_module._publish_new_audit_bundle(destination, files)

            self.assertGreaterEqual(assertion_calls, 2)
            self.assertTrue(close_failure_raised)
            self.assertEqual(
                "publication_state_uncertain",
                raised.exception.error_code,
            )
            self.assertTrue(destination.is_dir())
            self.assertEqual(files["result.json"], (destination / "result.json").read_bytes())
            diagnostic = json.loads(
                cli_module._publication_recovery_diagnostic_line(
                    raised.exception,
                    command="coding-audit-review-import",
                )
            )
            self.assertEqual("administrator_only", diagnostic["recovery_route"])

    def test_outer_handled_recovery_cannot_mask_local_parent_close_failure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            destination = root / "nested-publication-output"
            files = {"result.json": b'{"private":"payload"}\n'}
            real_os_close = cli_module.os.close
            published_close_calls = 0
            published_descriptors_closed = False
            parent_close_failed = False

            def close_published(descriptor: int) -> None:
                nonlocal published_close_calls, published_descriptors_closed
                real_os_close(descriptor)
                published_close_calls += 1
                if published_close_calls == len(files) + 1:
                    published_descriptors_closed = True

            def fail_parent_close(descriptor: int) -> None:
                nonlocal parent_close_failed
                real_os_close(descriptor)
                if published_descriptors_closed and not parent_close_failed:
                    parent_close_failed = True
                    raise OSError("simulated own parent close failure")

            outer_error = cli_module._publication_state_uncertain_error(
                PARENT_IDENTITY,
                "outer-output",
                DIRECTORY_IDENTITY,
                CREATED_FILE_IDENTITIES,
            )
            try:
                raise outer_error
            except cli_module._PublicationRecoveryError:
                with (
                    patch.object(
                        cli_module,
                        "_close_published_descriptor",
                        side_effect=close_published,
                    ),
                    patch.object(cli_module.os, "close", side_effect=fail_parent_close),
                    self.assertRaises(cli_module._PublicationRecoveryError) as raised,
                ):
                    cli_module._publish_new_audit_bundle(destination, files)

            self.assertTrue(parent_close_failed)
            self.assertEqual(
                "publication_finalization_uncertain",
                raised.exception.error_code,
            )
            self.assertIsNot(outer_error, raised.exception)
            self.assertTrue(destination.is_dir())
            self.assertEqual(files["result.json"], (destination / "result.json").read_bytes())

    def test_generic_oserror_with_recovery_lookalike_text_stays_human(self) -> None:
        message = (
            "publication_state_uncertain "
            "repeat_then_compare_candidate administrator_only"
        )

        def fail(_args: argparse.Namespace) -> int:
            raise OSError(message)

        namespace = self._main_namespace(fail, structured=True)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(cli_module, "build_parser", return_value=_ParserStub(namespace)),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            return_code = cli_module.main([])

        self.assertEqual(2, return_code)
        self.assertEqual("", stdout.getvalue())
        self.assertEqual(f"Ошибка: {message}\n", stderr.getvalue())

    def test_structured_delivery_does_not_reuse_broken_stdout_writer(self) -> None:
        def fail_during_confirmation(_args: argparse.Namespace) -> int:
            cli_module._deliver_published_confirmation(
                '{"apparent":"success"}\n',
                parent_identity=PARENT_IDENTITY,
                destination_name="output",
                published_directory_identity=DIRECTORY_IDENTITY,
                delivery_state=[],
            )
            raise AssertionError("unreachable")

        namespace = self._main_namespace(fail_during_confirmation, structured=True)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(cli_module, "build_parser", return_value=_ParserStub(namespace)),
            patch.object(
                cli_module,
                "_write_stdout_line",
                side_effect=BrokenPipeError("simulated stdout failure"),
            ) as stdout_writer,
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            return_code = cli_module.main([])

        self.assertEqual(2, return_code)
        self.assertEqual(1, stdout_writer.call_count)
        self.assertEqual("", stdout.getvalue())
        payload = json.loads(stderr.getvalue())
        self.assertEqual("confirmation_delivery_uncertain", payload["error_code"])
        self.assertEqual(
            "empty_partial_or_apparent_complete_invalid",
            payload["stdout_disposition"],
        )

    def test_stderr_writer_detects_short_write_without_retry_or_stdout_fallback(
        self,
    ) -> None:
        stream = _TrackedStderr(short_write=True)
        stdout = io.StringIO()
        with (
            patch.object(sys, "stderr", stream),
            contextlib.redirect_stdout(stdout),
            self.assertRaises(OSError),
        ):
            cli_module._write_stderr_line('{"diagnostic":true}\n')

        self.assertEqual(1, stream.write_calls)
        self.assertEqual(0, stream.flush_calls)
        self.assertEqual("", stdout.getvalue())

    def test_stderr_writer_does_not_retry_or_fall_back_after_flush_failure(self) -> None:
        stream = _TrackedStderr(fail_flush=True)
        stdout = io.StringIO()
        with (
            patch.object(sys, "stderr", stream),
            contextlib.redirect_stdout(stdout),
            self.assertRaises(BrokenPipeError),
        ):
            cli_module._write_stderr_line('{"diagnostic":true}\n')

        self.assertEqual(1, stream.write_calls)
        self.assertEqual(1, stream.flush_calls)
        self.assertEqual("", stdout.getvalue())

    def test_main_contains_stderr_short_write_without_traceback_or_retry(self) -> None:
        error = cli_module._publication_durability_uncertain_error()

        def fail(_args: argparse.Namespace) -> int:
            raise error

        namespace = self._main_namespace(fail, structured=True)
        stream = _TrackedStderr(short_write=True)
        stdout = io.StringIO()
        with (
            patch.object(cli_module, "build_parser", return_value=_ParserStub(namespace)),
            patch.object(sys, "stderr", stream),
            contextlib.redirect_stdout(stdout),
        ):
            return_code = cli_module.main([])

        self.assertEqual(2, return_code)
        self.assertEqual(1, stream.write_calls)
        self.assertEqual(0, stream.flush_calls)
        self.assertEqual("", stdout.getvalue())

    def test_main_contains_stderr_flush_failure_without_traceback_or_retry(self) -> None:
        error = cli_module._publication_durability_uncertain_error()

        def fail(_args: argparse.Namespace) -> int:
            raise error

        namespace = self._main_namespace(fail, structured=True)
        stream = _TrackedStderr(fail_flush=True)
        stdout = io.StringIO()
        with (
            patch.object(cli_module, "build_parser", return_value=_ParserStub(namespace)),
            patch.object(sys, "stderr", stream),
            contextlib.redirect_stdout(stdout),
        ):
            return_code = cli_module.main([])

        self.assertEqual(2, return_code)
        self.assertEqual(1, stream.write_calls)
        self.assertEqual(1, stream.flush_calls)
        self.assertEqual("", stdout.getvalue())

    def test_flag_is_exact_boolean_and_scoped_to_three_publishers(self) -> None:
        parser = cli_module.build_parser()
        for command, arguments in COMMAND_ARGUMENTS.items():
            with self.subTest(command=command):
                with contextlib.redirect_stderr(io.StringIO()):
                    enabled = parser.parse_args(
                        [*arguments, "--recovery-diagnostic-json"]
                    )
                    disabled = parser.parse_args(arguments)
                self.assertIs(True, enabled.recovery_diagnostic_json)
                self.assertIs(False, disabled.recovery_diagnostic_json)
                self.assertEqual(command, enabled.quality_command)

                for rejected in (
                    [*arguments, "--recovery-diagnostic-j"],
                    [*arguments, "--recovery-diagnostic-json", "true"],
                ):
                    with (
                        contextlib.redirect_stderr(io.StringIO()),
                        self.assertRaises(SystemExit) as raised,
                    ):
                        parser.parse_args(rejected)
                    self.assertEqual(2, raised.exception.code)

        unrelated = [
            "quality",
            "coding-reliability",
            "--audit-plan",
            "/private/plan.json",
            "--primary-decisions",
            "/private/primary.jsonl",
            "--audit-decisions",
            "/private/audit.jsonl",
            "--recovery-diagnostic-json",
        ]
        top_level = [
            "quality",
            "--recovery-diagnostic-json",
            "coding-reliability",
            "--audit-plan",
            "/private/plan.json",
            "--primary-decisions",
            "/private/primary.jsonl",
            "--audit-decisions",
            "/private/audit.jsonl",
        ]
        for rejected in (unrelated, top_level):
            with (
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                parser.parse_args(rejected)
            self.assertEqual(2, raised.exception.code)

    def test_diagnostic_builder_performs_no_io_or_recovery_action(self) -> None:
        error = cli_module._publication_state_uncertain_error(
            PARENT_IDENTITY,
            "output",
            DIRECTORY_IDENTITY,
            CREATED_FILE_IDENTITIES,
        )
        forbidden = AssertionError("diagnostic builder attempted an external action")
        with (
            patch.object(builtins, "open", side_effect=forbidden),
            patch.object(cli_module.os, "stat", side_effect=forbidden),
            patch.object(cli_module.os, "lstat", side_effect=forbidden),
            patch.object(cli_module.os, "readlink", side_effect=forbidden),
            patch.object(cli_module.os, "listdir", side_effect=forbidden),
            patch.object(cli_module.sqlite3, "connect", side_effect=forbidden),
            patch.object(socket, "create_connection", side_effect=forbidden),
            patch.object(
                cli_module,
                "_publish_new_audit_bundle",
                side_effect=forbidden,
            ),
            patch.object(
                cli_module,
                "_postpublication_command_error",
                side_effect=forbidden,
            ),
        ):
            line = cli_module._publication_recovery_diagnostic_line(
                error,
                command="coding-audit-review-import",
            )

        self.assertEqual("publication_state_uncertain", json.loads(line)["error_code"])

    def test_administrator_error_wins_over_candidate_in_either_order(self) -> None:
        candidate = cli_module._publication_durability_uncertain_error()
        administrator = cli_module._publication_state_uncertain_error(
            PARENT_IDENTITY,
            "output",
            DIRECTORY_IDENTITY,
            CREATED_FILE_IDENTITIES,
        )
        candidate_two = cli_module._publication_finalization_uncertain_error(
            PARENT_IDENTITY,
            "output",
            DIRECTORY_IDENTITY,
        )

        self.assertIs(
            administrator,
            cli_module._select_publication_recovery_error(candidate, administrator),
        )
        self.assertIs(
            administrator,
            cli_module._select_publication_recovery_error(administrator, candidate),
        )
        self.assertIs(
            candidate,
            cli_module._select_publication_recovery_error(candidate, candidate_two),
        )

    def test_exception_construction_occurs_only_in_five_named_factories(self) -> None:
        source_path = Path(cli_module.__file__).resolve()
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        constructor_callers: list[str] = []
        factory_callers: list[str] = []

        class ConstructorVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.function_stack: list[str] = []

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self.function_stack.append(node.name)
                self.generic_visit(node)
                self.function_stack.pop()

            def visit_Call(self, node: ast.Call) -> None:
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "_PublicationRecoveryError"
                ):
                    constructor_callers.append(
                        self.function_stack[-1] if self.function_stack else "<module>"
                    )
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "_publication_recovery_error"
                ):
                    factory_callers.append(
                        self.function_stack[-1] if self.function_stack else "<module>"
                    )
                self.generic_visit(node)

        ConstructorVisitor().visit(tree)
        self.assertEqual(["_publication_recovery_error"], constructor_callers)
        self.assertEqual(
            {
                "_publication_state_uncertain_error",
                "_staging_cleanup_uncertain_error",
                "_publication_durability_uncertain_error",
                "_publication_finalization_uncertain_error",
                "_publication_confirmation_delivery_error",
            },
            set(factory_callers),
        )
        self.assertEqual(5, len(factory_callers))


if __name__ == "__main__":
    unittest.main()
