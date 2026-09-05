from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import unittest

from judicial_meaning import cli

if __package__:
    from . import test_native_audit_bundle_comparison_cli as comparison_harness
else:
    import test_native_audit_bundle_comparison_cli as comparison_harness


class _BinaryBuffer:
    def __init__(self, mode: str, error_text: str) -> None:
        self.mode = mode
        self.error_text = error_text
        self.writes: list[bytes] = []
        self.accepted = bytearray()
        self.flush_calls = 0

    def write(self, content: bytes) -> int | None:
        self.writes.append(content)
        if self.mode == "broken_pipe":
            raise BrokenPipeError(self.error_text)
        stream_errors = {
            "interrupted": InterruptedError,
            "runtime_error": RuntimeError,
            "attribute_error": AttributeError,
            "not_implemented": NotImplementedError,
        }
        if self.mode in stream_errors:
            raise stream_errors[self.mode](self.error_text)
        if self.mode in {"zero", "none"}:
            return 0 if self.mode == "zero" else None
        if self.mode == "short":
            self.accepted.extend(content[:-1])
            return len(content) - 1
        self.accepted.extend(content)
        return len(content)

    def flush(self) -> None:
        self.flush_calls += 1
        if self.mode == "flush_error":
            raise OSError(self.error_text)


class _BinaryOutput:
    encoding = "ascii"

    def __init__(self, mode: str, error_text: str) -> None:
        self.buffer = _BinaryBuffer(mode, error_text)
        self.text_writes = 0

    def write(self, content: str) -> int:
        self.text_writes += 1
        raise AssertionError("The binary stdout path must not fall back to text.")


class _TextOutput:
    def __init__(self, mode: str, error_text: str) -> None:
        self.mode = mode
        self.error_text = error_text
        self.writes: list[str] = []
        self.accepted = ""
        self.flush_calls = 0

    def write(self, content: str) -> int:
        self.writes.append(content)
        if self.mode == "broken_pipe":
            raise BrokenPipeError(self.error_text)
        if self.mode == "ascii":
            content.encode("ascii", errors="strict")
        if self.mode == "short":
            self.accepted += content[:-1]
            return len(content) - 1
        self.accepted += content
        return len(content)

    def flush(self) -> None:
        self.flush_calls += 1
        if self.mode == "flush_error":
            raise OSError(self.error_text)


class NativeAuditBundleComparisonOutputTests(unittest.TestCase):
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
        self.addCleanup(self.harness.tearDown)
        self.error_text = (
            "PRIVATE-STDOUT-FAILURE "
            + str(self.harness.root)
            + " "
            + self.harness.expected_manifest_sha256
        )

    def snapshot(self) -> dict[Path, tuple[object, ...]]:
        paths = [self.harness.root]
        for directory in (self.harness.uncertain, self.harness.repeated):
            paths.append(directory)
            paths.extend(directory.iterdir())
        paths.append(
            Path(cli.__file__).resolve().parents[2]
            / "references"
            / cli._AUDIT_CODEBOOK_PATHS["1.0"]
        )
        snapshot = {}
        for path in paths:
            state = path.stat(follow_symlinks=False)
            payload = (
                tuple(sorted(child.name for child in path.iterdir()))
                if path.is_dir()
                else path.read_bytes()
            )
            snapshot[path] = (
                state.st_dev,
                state.st_ino,
                state.st_mode,
                state.st_nlink,
                state.st_uid,
                state.st_gid,
                state.st_size,
                state.st_mtime_ns,
                state.st_ctime_ns,
                payload,
            )
        return snapshot

    def run_output(self, output, *, russian_report: bool = False):
        before = self.snapshot()
        stderr = io.StringIO()
        argv = (
            self.harness.argv(manifest_sha256="0" * 64)
            if russian_report
            else self.harness.argv()
        )
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(stderr):
            code = cli.main(argv)
        self.assertEqual(before, self.snapshot())
        return code, stderr.getvalue()

    def assert_failure_is_value_free(self, code: int, accepted: str, stderr: str):
        self.assertEqual(2, code)
        self.assertEqual("", stderr)
        combined = accepted + stderr
        self.assertNotIn("PRIVATE-STDOUT-FAILURE", combined)
        self.assertNotIn(str(self.harness.root), combined)
        self.assertNotIn(self.harness.expected_manifest_sha256, combined)
        self.assertNotIn(self.harness.expected_packet_sha256, combined)
        self.assertNotIn("Traceback", combined)
        self.assertNotIn("native_audit_bundle_comparison_report", stderr)

    def test_binary_short_zero_and_unconfirmed_writes_return_two(self) -> None:
        for mode in ("short", "zero", "none"):
            with self.subTest(mode=mode):
                output = _BinaryOutput(mode, self.error_text)
                code, stderr = self.run_output(output)
                self.assert_failure_is_value_free(
                    code, output.buffer.accepted.decode("utf-8"), stderr
                )
                self.assertEqual(1, len(output.buffer.writes))
                self.assertEqual(0, output.buffer.flush_calls)
                self.assertEqual(0, output.text_writes)

    def test_binary_flush_failure_returns_two_without_retry_or_leak(self) -> None:
        output = _BinaryOutput("flush_error", self.error_text)
        code, stderr = self.run_output(output)
        self.assert_failure_is_value_free(
            code, output.buffer.accepted.decode("utf-8"), stderr
        )
        self.assertEqual(1, len(output.buffer.writes))
        self.assertEqual(1, output.buffer.flush_calls)
        self.assertEqual(0, output.text_writes)

    def test_binary_broken_pipe_returns_two_without_retry_or_leak(self) -> None:
        output = _BinaryOutput("broken_pipe", self.error_text)
        code, stderr = self.run_output(output)
        self.assert_failure_is_value_free(code, "", stderr)
        self.assertEqual(b"", output.buffer.accepted)
        self.assertEqual(1, len(output.buffer.writes))
        self.assertEqual(0, output.buffer.flush_calls)
        self.assertEqual(0, output.text_writes)

    def test_binary_interruption_returns_two_without_retry_or_leak(self) -> None:
        for mode in ("interrupted", "runtime_error", "attribute_error", "not_implemented"):
            with self.subTest(mode=mode):
                output = _BinaryOutput(mode, self.error_text)
                code, stderr = self.run_output(output)
                self.assert_failure_is_value_free(code, "", stderr)
                self.assertEqual(b"", output.buffer.accepted)
                self.assertEqual(1, len(output.buffer.writes))
                self.assertEqual(0, output.buffer.flush_calls)
                self.assertEqual(0, output.text_writes)

    def test_text_short_write_returns_two_without_second_report(self) -> None:
        output = _TextOutput("short", self.error_text)
        code, stderr = self.run_output(output)
        self.assert_failure_is_value_free(code, output.accepted, stderr)
        self.assertEqual(1, len(output.writes))
        self.assertEqual(0, output.flush_calls)

    def test_text_flush_failure_returns_two_without_retry_or_leak(self) -> None:
        output = _TextOutput("flush_error", self.error_text)
        code, stderr = self.run_output(output)
        self.assert_failure_is_value_free(code, output.accepted, stderr)
        self.assertEqual(1, len(output.writes))
        self.assertEqual(1, output.flush_calls)

    def test_text_broken_pipe_returns_two_without_retry_or_leak(self) -> None:
        output = _TextOutput("broken_pipe", self.error_text)
        code, stderr = self.run_output(output)
        self.assert_failure_is_value_free(code, output.accepted, stderr)
        self.assertEqual(1, len(output.writes))
        self.assertEqual(0, output.flush_calls)

    def test_text_encoding_error_returns_two_without_retry(self) -> None:
        output = _TextOutput("ascii", self.error_text)
        code, stderr = self.run_output(output, russian_report=True)
        self.assert_failure_is_value_free(code, output.accepted, stderr)
        self.assertEqual(1, len(output.writes))
        self.assertEqual(0, output.flush_calls)

    def test_ascii_text_stream_uses_binary_utf8_for_russian_report(self) -> None:
        output = _BinaryOutput("ok", self.error_text)
        code, stderr = self.run_output(output, russian_report=True)
        self.assertEqual(3, code)
        self.assertEqual("", stderr)
        accepted = bytes(output.buffer.accepted)
        report = json.loads(accepted.decode("utf-8"))
        self.assertEqual("mismatch", report["status"])
        self.assertTrue(
            any(ord(character) > 127 for character in accepted.decode("utf-8"))
        )
        expected = (
            json.dumps(
                report,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        self.assertEqual(expected, accepted)
        self.assertEqual(1, len(output.buffer.writes))
        self.assertEqual(1, output.buffer.flush_calls)
        self.assertEqual(0, output.text_writes)


if __name__ == "__main__":
    unittest.main()
