from __future__ import annotations

import argparse
import contextlib
import errno
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from judicial_meaning import cli
from judicial_meaning.practice_quality import canonical_digest

if __package__:
    from . import test_native_coding_audit_finalization_cli as finalization_harness
else:
    import test_native_coding_audit_finalization_cli as finalization_harness


REPO = Path(__file__).resolve().parents[3]
SCRIPT = (
    REPO
    / "skills"
    / "ksrf-cassation-judicial-meaning"
    / "scripts"
    / "judicial_meaning.py"
)
FINALIZATION_FILES = (
    "resolved-review-decisions.jsonl",
    "adjudications.jsonl",
    "coding-reliability.json",
    "coding-audit-finalization-receipt.json",
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
            path.read_bytes() if path.is_file() else None,
        )
    return snapshot


class NativeFinalizationComparisonCliTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_tmp = tempfile.TemporaryDirectory()
        fixture_root = Path(cls.fixture_tmp.name)
        harness = finalization_harness.NativeCodingAuditFinalizationCliTests(
            methodName="runTest"
        )
        _, bundle, manifest_sha256 = harness._prepare_bundle(fixture_root)
        audit_import, import_result = harness._import_review(
            fixture_root,
            bundle,
            manifest_sha256,
            harness._secondary_records(bundle),
        )
        cls.fixture_directories: list[Path] = []
        results: list[dict[str, object]] = []
        for name in ("uncertain-finalization", "repeated-finalization"):
            destination = fixture_root / name
            completed = harness._run(
                SCRIPT,
                harness._finalization_arguments(
                    bundle,
                    manifest_sha256,
                    audit_import,
                    import_result["receipt_sha256"],
                    destination,
                ),
                cwd=fixture_root,
            )
            if completed.returncode != 0:
                raise AssertionError(completed.stderr)
            results.append(json.loads(completed.stdout))
            cls.fixture_directories.append(destination)
        if results[0]["receipt_sha256"] != results[1]["receipt_sha256"]:
            raise AssertionError("Fixture finalizations are not identical.")
        cls.expected_receipt_sha256 = str(results[1]["receipt_sha256"])
        reliability = json.loads(
            (
                cls.fixture_directories[0] / "coding-reliability.json"
            ).read_text(encoding="utf-8")
        )
        cls.private_candidate_id = reliability["required_candidate_ids"][0]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_tmp.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.uncertain = self.root / "uncertain-finalization"
        self.repeated = self.root / "repeated-finalization"
        shutil.copytree(
            self.fixture_directories[0],
            self.uncertain,
            copy_function=shutil.copy2,
        )
        shutil.copytree(
            self.fixture_directories[1],
            self.repeated,
            copy_function=shutil.copy2,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def argv(
        self,
        *,
        uncertain: Path | None = None,
        repeated: Path | None = None,
        expected: str | None = None,
    ) -> list[str]:
        return [
            "quality",
            "native-reliability",
            "compare-finalizations",
            "--uncertain-finalization-dir",
            str(uncertain or self.uncertain),
            "--repeated-finalization-dir",
            str(repeated or self.repeated),
            "--expected-finalization-receipt-sha256",
            expected or self.expected_receipt_sha256,
        ]

    def run_cli(self, argv: list[str] | None = None) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(argv or self.argv())
        return code, stdout.getvalue(), stderr.getvalue()

    def run_handler(self) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        args = argparse.Namespace(
            uncertain_finalization_dir=str(self.uncertain),
            repeated_finalization_dir=str(self.repeated),
            expected_finalization_receipt_sha256=self.expected_receipt_sha256,
        )
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.cmd_quality_native_reliability_compare_finalizations(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def fresh_pair(self, label: str) -> tuple[Path, Path]:
        parent = self.root / label
        parent.mkdir(mode=0o700)
        uncertain = parent / "uncertain"
        repeated = parent / "repeated"
        shutil.copytree(self.uncertain, uncertain, copy_function=shutil.copy2)
        shutil.copytree(self.repeated, repeated, copy_function=shutil.copy2)
        return uncertain, repeated

    def assert_report(self, result: tuple[int, str, str]) -> dict[str, object]:
        _, stdout, stderr = result
        self.assertEqual("", stderr)
        self.assertTrue(stdout.endswith("\n"))
        self.assertFalse(stdout.endswith("\n\n"))
        report = json.loads(stdout)
        self.assertEqual(_canonical_bytes(report), stdout.encode("utf-8"))
        self.assertEqual(
            {
                "schema_version",
                "artifact_type",
                "status",
                "recovery_comparison_valid",
                "reason_codes",
                "checks",
                "remediation",
                "scope",
            },
            set(report),
        )
        return report

    def test_match_is_canonical_bounded_read_only_and_value_free(self) -> None:
        before = {
            "uncertain": _directory_snapshot(self.uncertain),
            "repeated": _directory_snapshot(self.repeated),
        }
        real_read = cli.os.read
        requested_sizes: list[int] = []

        def bounded_read(descriptor: int, size: int) -> bytes:
            requested_sizes.append(size)
            return real_read(descriptor, size)

        forbidden = AssertionError("comparison attempted a side effect")
        patches = (
            mock.patch.object(cli.os, "read", side_effect=bounded_read),
            *(
                mock.patch.object(owner, name, side_effect=forbidden)
                for owner, name in (
                    (cli, "write_json"),
                    (cli, "write_jsonl"),
                    (cli.os, "replace"),
                    (cli.os, "rename"),
                    (cli.os, "unlink"),
                    (cli.os, "mkdir"),
                    (cli.os, "chmod"),
                    (cli.os, "chown"),
                    (cli.os, "link"),
                    (cli.os, "symlink"),
                    (cli.os, "mkfifo"),
                    (cli.os, "system"),
                    (cli.tempfile, "mkdtemp"),
                    (cli.tempfile, "mkstemp"),
                    (cli.tempfile, "TemporaryDirectory"),
                    (cli.shutil, "copyfile"),
                    (cli.shutil, "copytree"),
                    (cli.sqlite3, "connect"),
                    (cli, "import_handoff"),
                    (cli, "create_handoff"),
                    (cli, "promote_enumerator"),
                    (subprocess, "run"),
                    (subprocess, "Popen"),
                    (socket, "socket"),
                    (cli, "build_native_coding_audit_finalization"),
                )
            ),
        )
        with contextlib.ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            first = self.run_cli()
            second = self.run_cli()

        self.assertEqual(first, second)
        self.assertEqual(0, first[0])
        report = self.assert_report(first)
        self.assertEqual("match", report["status"])
        self.assertTrue(report["recovery_comparison_valid"])
        self.assertEqual([], report["reason_codes"])
        self.assertTrue(all(report["checks"].values()))
        self.assertLessEqual(
            max(requested_sizes),
            cli._FINALIZATION_COMPARISON_CHUNK_BYTES,
        )
        self.assertEqual(before["uncertain"], _directory_snapshot(self.uncertain))
        self.assertEqual(before["repeated"], _directory_snapshot(self.repeated))
        self.assertNotIn(str(self.root), first[1])
        self.assertNotIn(self.expected_receipt_sha256, first[1])
        self.assertNotIn(self.private_candidate_id, first[1])
        self.assertIsNone(re.search(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", first[1]))

    def test_parser_requires_exact_long_options_and_rejects_extra_inputs(self) -> None:
        complete = self.argv()
        cases = (
            complete[:-2],
            complete[:3] + complete[5:],
            complete[:5] + complete[7:],
            [
                *complete[:3],
                "--uncertain-finalization",
                str(self.uncertain),
                *complete[5:],
            ],
            [*complete, "--output", str(self.root / "report.json")],
            [*complete, str(self.root / "positional")],
        )
        for argv in cases:
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as raised:
                with contextlib.redirect_stderr(io.StringIO()):
                    cli.build_parser().parse_args(argv)
            self.assertEqual(2, raised.exception.code)

    def test_external_digest_syntax_and_value_have_distinct_invalid_states(self) -> None:
        invalid = self.run_cli(self.argv(expected="A" * 64))
        self.assertEqual(2, invalid[0])
        invalid_report = self.assert_report(invalid)
        self.assertEqual("invalid", invalid_report["status"])
        self.assertFalse(invalid_report["checks"]["expected_receipt_sha256_valid"])
        self.assertIsNone(
            invalid_report["checks"]["repeated_external_receipt_digest_valid"]
        )

        mismatch = self.run_cli(self.argv(expected="0" * 64))
        self.assertEqual(3, mismatch[0])
        mismatch_report = self.assert_report(mismatch)
        self.assertEqual("mismatch", mismatch_report["status"])
        self.assertTrue(mismatch_report["checks"]["expected_receipt_sha256_valid"])
        self.assertFalse(
            mismatch_report["checks"]["repeated_external_receipt_digest_valid"]
        )

    def test_one_unreadable_path_does_not_hide_independent_repeat(self) -> None:
        result = self.run_cli(
            self.argv(uncertain=self.root / "missing-parent" / "missing")
        )
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["uncertain_directory_readable"])
        self.assertTrue(report["checks"]["repeated_directory_readable"])
        self.assertIn("uncertain_finalization_unreadable", report["reason_codes"])
        self.assertNotIn("repeated_finalization_unreadable", report["reason_codes"])

    def test_same_directory_and_cross_parent_are_topology_invalid(self) -> None:
        same = self.run_cli(self.argv(repeated=self.uncertain))
        self.assertEqual(2, same[0])
        same_report = self.assert_report(same)
        self.assertEqual("invalid", same_report["status"])
        self.assertFalse(same_report["checks"]["directories_distinct"])

        other_parent = self.root / "other-parent"
        other_parent.mkdir(mode=0o700)
        other_repeat = other_parent / "repeated-finalization"
        shutil.copytree(self.repeated, other_repeat, copy_function=shutil.copy2)
        cross_parent = self.run_cli(self.argv(repeated=other_repeat))
        self.assertEqual(2, cross_parent[0])
        cross_report = self.assert_report(cross_parent)
        self.assertEqual("invalid", cross_report["status"])
        self.assertFalse(cross_report["checks"]["common_parent_valid"])

    def test_child_device_must_match_held_parent_device(self) -> None:
        real_identity = cli._stable_finalization_directory_identity
        child_inodes = {
            self.uncertain.stat().st_ino,
            self.repeated.stat().st_ino,
        }

        def mounted_child_identity(value: os.stat_result) -> tuple[int, ...]:
            identity = list(real_identity(value))
            if value.st_ino in child_inodes:
                identity[0] += 1
            return tuple(identity)

        with mock.patch.object(
            cli,
            "_stable_finalization_directory_identity",
            side_effect=mounted_child_identity,
        ):
            result = self.run_cli()
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertFalse(report["checks"]["common_parent_valid"])
        self.assertTrue(report["checks"]["uncertain_directory_readable"])
        self.assertTrue(report["checks"]["repeated_directory_readable"])
        self.assertIsNone(report["checks"]["directories_distinct"])
        self.assertIn("comparison_topology_invalid", report["reason_codes"])
        remediation = {item["code"] for item in report["remediation"]}
        self.assertIn("administrator_quarantine", remediation)
        self.assertNotIn("repeat_after_mismatch", remediation)

    def test_extra_fifo_symlink_and_mode_are_never_opened_as_content(self) -> None:
        mutations = {
            "extra": lambda root: (root / "extra.txt").write_text(
                "private", encoding="utf-8"
            ),
            "fifo": lambda root: (
                (root / FINALIZATION_FILES[0]).unlink(),
                os.mkfifo(root / FINALIZATION_FILES[0], mode=0o600),
            ),
            "symlink": lambda root: (
                (root / FINALIZATION_FILES[0]).unlink(),
                (root / FINALIZATION_FILES[0]).symlink_to(
                    self.uncertain / FINALIZATION_FILES[0]
                ),
            ),
            "mode": lambda root: os.chmod(root / FINALIZATION_FILES[0], 0o640),
        }
        for label, mutate in mutations.items():
            case_parent = self.root / f"case-{label}"
            case_parent.mkdir(mode=0o700)
            uncertain = case_parent / "uncertain"
            repeated = case_parent / "repeated"
            shutil.copytree(self.uncertain, uncertain, copy_function=shutil.copy2)
            shutil.copytree(self.repeated, repeated, copy_function=shutil.copy2)
            mutate(repeated)
            result = self.run_cli(self.argv(uncertain=uncertain, repeated=repeated))
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                check = (
                    "repeated_inventory_exact"
                    if label == "extra"
                    else "repeated_directory_private"
                )
                self.assertFalse(report["checks"][check])

    def test_cross_directory_hardlink_is_privacy_invalid_not_raw_match(self) -> None:
        linked = self.repeated / FINALIZATION_FILES[0]
        linked.unlink()
        os.link(self.uncertain / FINALIZATION_FILES[0], linked)
        result = self.run_cli()
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertFalse(report["checks"]["uncertain_directory_private"])
        self.assertFalse(report["checks"]["repeated_directory_private"])
        self.assertIsNone(report["checks"]["directory_file_bytes_equal"])

    def test_receipt_file_binding_mismatch_is_value_free_mismatch(self) -> None:
        receipt_path = self.uncertain / "coding-audit-finalization-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["resolved_review_decisions_file_sha256"] = "0" * 64
        unsigned = {
            key: value for key, value in receipt.items() if key != "receipt_sha256"
        }
        receipt["receipt_sha256"] = canonical_digest(unsigned)
        receipt_path.write_bytes(_canonical_bytes(receipt))

        result = self.run_cli()
        self.assertEqual(3, result[0])
        report = self.assert_report(result)
        self.assertEqual("mismatch", report["status"])
        self.assertTrue(report["checks"]["uncertain_receipt_self_digest_valid"])
        self.assertFalse(report["checks"]["uncertain_receipt_file_bindings_valid"])
        self.assertFalse(report["checks"]["directory_file_bytes_equal"])
        self.assertNotIn("0" * 64, result[1])

    def test_stable_file_open_failure_is_side_specific_unreadable(self) -> None:
        real_open = cli.os.open
        injected = False

        def hostile_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            nonlocal injected
            if (
                not injected
                and path == FINALIZATION_FILES[0]
                and kwargs.get("dir_fd") is not None
            ):
                injected = True
                raise PermissionError(errno.EACCES, "private path marker")
            return real_open(path, flags, *args, **kwargs)

        with mock.patch.object(cli.os, "open", side_effect=hostile_open):
            result = self.run_cli()
        self.assertTrue(injected)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["uncertain_directory_readable"])
        self.assertTrue(report["checks"]["repeated_directory_readable"])
        self.assertNotIn("private path marker", result[1])

    def test_distinct_fstat_fault_returns_report_instead_of_traceback(self) -> None:
        real_capture = cli._capture_private_finalization_descriptor
        real_fstat = cli.os.fstat
        state: dict[str, object] = {"calls": 0, "armed": False, "raised": False}

        def capture(
            descriptor: int,
            **kwargs: object,
        ) -> dict[str, object]:
            result = real_capture(descriptor, **kwargs)
            state["calls"] = int(state["calls"]) + 1
            if state["calls"] == 1:
                state["uncertain_descriptor"] = descriptor
            elif state["calls"] == 2:
                state["armed"] = True
            return result

        def hostile_fstat(descriptor: int) -> os.stat_result:
            if (
                state["armed"]
                and not state["raised"]
                and descriptor == state.get("uncertain_descriptor")
            ):
                state["raised"] = True
                raise OSError(errno.EMFILE, "descriptor marker")
            return real_fstat(descriptor)

        with (
            mock.patch.object(
                cli,
                "_capture_private_finalization_descriptor",
                side_effect=capture,
            ),
            mock.patch.object(cli.os, "fstat", side_effect=hostile_fstat),
        ):
            result = self.run_cli()
        self.assertTrue(state["raised"])
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["uncertain_directory_readable"])
        self.assertNotIn("descriptor marker", result[1])

    def test_missing_dir_fd_capability_is_closed_and_attempts_both_sides(
        self,
    ) -> None:
        real_stat = cli.os.stat
        attempted: list[str] = []

        def unsupported_stat(
            path: object,
            *args: object,
            **kwargs: object,
        ) -> os.stat_result:
            if (
                kwargs.get("dir_fd") is not None
                and path in {self.uncertain.name, self.repeated.name}
            ):
                attempted.append(str(path))
                raise NotImplementedError("private capability marker")
            return real_stat(path, *args, **kwargs)

        with mock.patch.object(cli.os, "stat", side_effect=unsupported_stat):
            result = self.run_cli()
        self.assertEqual(
            {self.uncertain.name, self.repeated.name},
            set(attempted),
        )
        self.assertEqual(2, result[0])
        self.assertEqual("", result[2])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["uncertain_directory_readable"])
        self.assertFalse(report["checks"]["repeated_directory_readable"])
        self.assertNotIn("private capability marker", result[1])

    def test_unsupported_platform_capabilities_stop_before_input_access(
        self,
    ) -> None:
        for label, attribute, value in (
            ("non-posix", "name", "nt"),
            ("no-no-follow", "O_NOFOLLOW", 0),
        ):
            forbidden_open = mock.Mock(
                side_effect=AssertionError("input open must not run")
            )
            forbidden_evaluation = mock.Mock(
                side_effect=AssertionError("evaluation must not run")
            )
            with (
                mock.patch.object(cli.os, attribute, value),
                mock.patch.object(cli.os, "open", forbidden_open),
                mock.patch.object(
                    cli,
                    "_evaluate_finalization_comparison_capture",
                    forbidden_evaluation,
                ),
            ):
                result = self.run_handler()
            with self.subTest(label=label):
                forbidden_open.assert_not_called()
                forbidden_evaluation.assert_not_called()
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(
                    report["checks"]["uncertain_directory_readable"]
                )
                self.assertFalse(
                    report["checks"]["repeated_directory_readable"]
                )
                self.assertIsNone(
                    report["checks"]["final_recapture_valid"]
                )
                self.assertEqual(
                    [
                        "uncertain_finalization_unreadable",
                        "repeated_finalization_unreadable",
                    ],
                    report["reason_codes"],
                )
                self.assertEqual("", result[2])

    def test_missing_os_primitive_stops_before_input_access(self) -> None:
        for primitive in ("open", "stat", "scandir", "fstat", "read", "close"):
            forbidden_path_access = mock.Mock(
                side_effect=AssertionError("input path access must not run")
            )
            with (
                mock.patch.object(cli.os, primitive, None),
                mock.patch.object(
                    cli,
                    "_finalization_comparison_path_info",
                    forbidden_path_access,
                ),
            ):
                result = self.run_handler()
            with self.subTest(primitive=primitive):
                forbidden_path_access.assert_not_called()
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(
                    report["checks"]["uncertain_directory_readable"]
                )
                self.assertFalse(
                    report["checks"]["repeated_directory_readable"]
                )
                self.assertIsNone(
                    report["checks"]["final_recapture_valid"]
                )
                self.assertEqual("", result[2])

    def test_os_primitive_faults_are_closed_and_descriptors_are_released(
        self,
    ) -> None:
        real_open = cli.os.open
        real_fstat = cli.os.fstat
        primitives = ("open", "stat", "scandir", "fstat", "read", "close")
        for index, primitive in enumerate(primitives):
            real_primitive = getattr(cli.os, primitive)
            opened: list[int] = []
            injected = False
            marker = f"private {primitive} primitive marker"
            error_type = TypeError if index % 2 == 0 else AttributeError

            def fault_once(*args: object, **kwargs: object) -> object:
                nonlocal injected
                if not injected:
                    injected = True
                    if primitive == "close":
                        real_primitive(*args, **kwargs)
                    raise error_type(marker)
                return real_primitive(*args, **kwargs)

            def tracking_open(*args: object, **kwargs: object) -> int:
                descriptor = real_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            with contextlib.ExitStack() as stack:
                if primitive != "open":
                    stack.enter_context(
                        mock.patch.object(
                            cli.os,
                            "open",
                            side_effect=tracking_open,
                        )
                    )
                stack.enter_context(
                    mock.patch.object(
                        cli.os,
                        primitive,
                        side_effect=fault_once,
                    )
                )
                result = self.run_handler()
            with self.subTest(primitive=primitive):
                self.assertTrue(injected)
                self.assertEqual(2, result[0])
                self.assert_report(result)
                self.assertEqual("", result[2])
                self.assertNotIn(marker, result[1])
                for descriptor in set(opened):
                    with self.assertRaises(OSError) as raised:
                        real_fstat(descriptor)
                    self.assertEqual(errno.EBADF, raised.exception.errno)

    def test_descriptor_scandir_type_error_is_closed_and_attempts_both_sides(
        self,
    ) -> None:
        attempts = 0

        def unsupported_scandir(descriptor: int) -> object:
            nonlocal attempts
            attempts += 1
            raise TypeError("private scandir marker")

        with mock.patch.object(
            cli.os,
            "scandir",
            side_effect=unsupported_scandir,
        ):
            result = self.run_cli()
        self.assertEqual(2, attempts)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["uncertain_directory_readable"])
        self.assertFalse(report["checks"]["repeated_directory_readable"])
        self.assertIsNone(report["checks"]["final_recapture_valid"])
        self.assertEqual(
            [
                "uncertain_finalization_unreadable",
                "repeated_finalization_unreadable",
            ],
            report["reason_codes"],
        )
        self.assertEqual("", result[2])
        self.assertNotIn("private scandir marker", result[1])

    def test_descriptor_scandir_type_errors_are_closed_in_secondary_passes(
        self,
    ) -> None:
        real_scandir = cli.os.scandir
        for boundary in ("invalid-observation", "inventory-recapture"):
            uncertain, repeated = self.fresh_pair(f"scandir-{boundary}")
            if boundary == "invalid-observation":
                extra = uncertain / "extra-entry"
                extra.write_bytes(b"private")
                os.chmod(extra, 0o600)
            scans = 0

            def unsupported_second_scan(descriptor: int) -> object:
                nonlocal scans
                scans += 1
                if scans == 2:
                    raise TypeError("private secondary scandir marker")
                return real_scandir(descriptor)

            real_stat = cli.os.stat
            leaf_fault_injected = False

            def maybe_fail_first_leaf_stat(
                path: object,
                *args: object,
                **kwargs: object,
            ) -> os.stat_result:
                nonlocal leaf_fault_injected
                if (
                    boundary == "inventory-recapture"
                    and not leaf_fault_injected
                    and kwargs.get("dir_fd") is not None
                    and path == FINALIZATION_FILES[0]
                ):
                    leaf_fault_injected = True
                    raise PermissionError(errno.EACCES, "private leaf marker")
                return real_stat(path, *args, **kwargs)

            with (
                mock.patch.object(
                    cli.os,
                    "scandir",
                    side_effect=unsupported_second_scan,
                ),
                mock.patch.object(
                    cli.os,
                    "stat",
                    side_effect=maybe_fail_first_leaf_stat,
                ),
            ):
                result = self.run_cli(
                    self.argv(uncertain=uncertain, repeated=repeated)
                )
            with self.subTest(boundary=boundary):
                self.assertGreaterEqual(scans, 3)
                self.assertEqual(
                    boundary == "inventory-recapture",
                    leaf_fault_injected,
                )
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertTrue(
                    report["checks"]["repeated_native_relation_valid"]
                )
                self.assertNotIn("private secondary scandir marker", result[1])
                self.assertNotIn("private leaf marker", result[1])

    def test_initial_and_evaluation_drift_are_explicit_input_change_reports(self) -> None:
        cases = (
            ("initial", "_capture_private_finalization_descriptor"),
            ("evaluation", "_evaluate_finalization_comparison_capture"),
        )
        for label, target in cases:
            error = cli._FinalizationComparisonCaptureError(
                "changed",
                inventory_exact=True,
            )
            with mock.patch.object(cli, target, side_effect=error):
                result = self.run_cli()
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(report["checks"]["final_recapture_valid"])
                self.assertIn("comparison_input_changed", report["reason_codes"])

    def test_raw_acl_or_identity_drift_never_invents_byte_mismatch(self) -> None:
        for kind in ("privacy", "changed"):
            error = cli._FinalizationComparisonCaptureError(
                kind,
                inventory_exact=True,
                side="uncertain",
            )
            with mock.patch.object(
                cli,
                "_finalization_directory_bytes_equal",
                side_effect=error,
            ):
                result = self.run_cli()
            with self.subTest(kind=kind):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertIsNone(report["checks"]["directory_file_bytes_equal"])
                self.assertFalse(report["checks"]["final_recapture_valid"])
                self.assertIn("comparison_input_changed", report["reason_codes"])
                self.assertNotIn(
                    "finalization_directory_bytes_mismatch",
                    report["reason_codes"],
                )
                self.assertNotIn(
                    "repeat_after_mismatch",
                    {item["code"] for item in report["remediation"]},
                )

    def test_swap_and_restore_is_caught_by_final_recapture(self) -> None:
        real_capture = cli._capture_private_finalization_descriptor
        calls = 0

        def swap(left: Path, right: Path, temporary: Path) -> None:
            left.rename(temporary)
            right.rename(left)
            temporary.rename(right)

        def capture(
            descriptor: int,
            **kwargs: object,
        ) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 3:
                first_temporary = self.root / "swap-one"
                second_temporary = self.root / "swap-two"
                swap(self.uncertain, self.repeated, first_temporary)
                swap(self.uncertain, self.repeated, second_temporary)
            return real_capture(descriptor, **kwargs)

        with mock.patch.object(
            cli,
            "_capture_private_finalization_descriptor",
            side_effect=capture,
        ):
            result = self.run_cli()
        self.assertGreaterEqual(calls, 3)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertTrue(report["checks"]["directory_file_bytes_equal"])
        self.assertIn("comparison_input_changed", report["reason_codes"])

    def test_final_recapture_attempts_both_sides_after_independent_faults(self) -> None:
        real_capture = cli._capture_private_finalization_descriptor

        calls = 0

        def third_capture_fails(
            descriptor: int,
            **kwargs: object,
        ) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 3:
                raise cli._FinalizationComparisonCaptureError("changed")
            return real_capture(descriptor, **kwargs)

        with mock.patch.object(
            cli,
            "_capture_private_finalization_descriptor",
            side_effect=third_capture_fails,
        ):
            third_failure = self.run_cli()
        self.assertEqual(4, calls)
        third_report = self.assert_report(third_failure)
        self.assertFalse(third_report["checks"]["final_recapture_valid"])
        self.assertTrue(third_report["checks"]["directory_file_bytes_equal"])

        calls = 0
        real_evaluate = cli._evaluate_finalization_comparison_capture
        evaluation_calls = 0

        def counted_capture(
            descriptor: int,
            **kwargs: object,
        ) -> dict[str, object]:
            nonlocal calls
            calls += 1
            return real_capture(descriptor, **kwargs)

        def first_evaluation_unreadable(
            descriptor: int,
            capture: object,
            *,
            expected_receipt_sha256: str | None,
        ) -> dict[str, bool | None]:
            nonlocal evaluation_calls
            evaluation_calls += 1
            if evaluation_calls == 1:
                raise cli._FinalizationComparisonCaptureError(
                    "unreadable",
                    side="uncertain",
                )
            return real_evaluate(
                descriptor,
                capture,
                expected_receipt_sha256=expected_receipt_sha256,
            )

        with (
            mock.patch.object(
                cli,
                "_capture_private_finalization_descriptor",
                side_effect=counted_capture,
            ),
            mock.patch.object(
                cli,
                "_evaluate_finalization_comparison_capture",
                side_effect=first_evaluation_unreadable,
            ),
        ):
            evaluation_failure = self.run_cli()
        self.assertEqual(4, calls)
        evaluation_report = self.assert_report(evaluation_failure)
        self.assertEqual("unreadable", evaluation_report["status"])
        self.assertFalse(evaluation_report["checks"]["final_recapture_valid"])
        self.assertIn(
            "comparison_input_changed",
            evaluation_report["reason_codes"],
        )

        calls = 0
        with (
            mock.patch.object(
                cli,
                "_capture_private_finalization_descriptor",
                side_effect=counted_capture,
            ),
            mock.patch.object(
                cli,
                "_finalization_directory_bytes_equal",
                side_effect=cli._FinalizationComparisonCaptureError(
                    "changed",
                    side="uncertain",
                ),
            ),
        ):
            raw_failure = self.run_cli()
        self.assertEqual(4, calls)
        raw_report = self.assert_report(raw_failure)
        self.assertFalse(raw_report["checks"]["final_recapture_valid"])
        self.assertIsNone(raw_report["checks"]["directory_file_bytes_equal"])

    def test_leaf_seal_catches_mutation_after_first_full_recapture(self) -> None:
        real_capture = cli._capture_private_finalization_descriptor
        calls = 0
        mutated = False

        def capture(
            descriptor: int,
            **kwargs: object,
        ) -> dict[str, object]:
            nonlocal calls, mutated
            calls += 1
            result = real_capture(descriptor, **kwargs)
            if calls == 3:
                leaf = self.uncertain / FINALIZATION_FILES[0]
                original = leaf.read_bytes()
                replacement = bytes((byte ^ 1) for byte in original)
                self.assertEqual(len(original), len(replacement))
                leaf.write_bytes(replacement)
                mutated = True
            return result

        with mock.patch.object(
            cli,
            "_capture_private_finalization_descriptor",
            side_effect=capture,
        ):
            result = self.run_cli()
        self.assertTrue(mutated)
        self.assertEqual(4, calls)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertTrue(report["checks"]["directory_file_bytes_equal"])
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertIn("comparison_input_changed", report["reason_codes"])

    def test_directory_close_uncertainty_invalidates_completed_comparison(self) -> None:
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
                raise cli._FinalizationComparisonCaptureError("changed")

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
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertTrue(report["checks"]["directory_file_bytes_equal"])
        self.assertIn("comparison_input_changed", report["reason_codes"])

    def test_every_file_size_limit_is_fail_closed_before_parsing(self) -> None:
        for name in FINALIZATION_FILES:
            uncertain, repeated = self.fresh_pair(f"size-{name}")
            oversized = repeated / name
            with oversized.open("r+b") as stream:
                stream.truncate(cli._AUDIT_FINALIZATION_FILE_LIMITS[name] + 1)
            result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
            with self.subTest(name=name):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(report["checks"]["repeated_directory_readable"])
                self.assertIn(
                    "repeated_finalization_unreadable",
                    report["reason_codes"],
                )

    def test_canonical_json_structural_limits_are_unreadable_not_invalid(self) -> None:
        deep: object = 0
        for _ in range(cli._AUDIT_IMPORT_MAX_JSON_DEPTH + 2):
            deep = [deep]
        cases = {
            "depth": {"x": deep},
            "collection": {
                "x": [0] * (cli._AUDIT_IMPORT_MAX_COLLECTION_ITEMS + 1)
            },
            "nonmapping-collection": [
                0
            ] * (cli._AUDIT_IMPORT_MAX_COLLECTION_ITEMS + 1),
            "nodes": {"x": [[0] * 2_000 for _ in range(201)]},
        }
        for label, value in cases.items():
            uncertain, repeated = self.fresh_pair(f"structure-{label}")
            reliability = uncertain / "coding-reliability.json"
            content = _canonical_bytes(value)
            self.assertLess(
                len(content),
                cli._AUDIT_FINALIZATION_FILE_LIMITS["coding-reliability.json"],
            )
            reliability.write_bytes(content)
            result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(report["checks"]["uncertain_directory_readable"])
                self.assertIsNone(report["checks"]["final_recapture_valid"])
                self.assertEqual(
                    ["uncertain_finalization_unreadable"],
                    report["reason_codes"],
                )
                self.assertEqual(
                    ["check_local_read_access"],
                    [item["code"] for item in report["remediation"]],
                )
                self.assertNotIn(
                    "uncertain_finalization_artifact_contract_invalid",
                    report["reason_codes"],
                )

        malformed = self.uncertain / "coding-reliability.json"
        malformed.write_bytes(b'{"not":"closed"}\n')
        invalid = self.run_cli()
        self.assertEqual(2, invalid[0])
        invalid_report = self.assert_report(invalid)
        self.assertEqual("invalid", invalid_report["status"])
        self.assertFalse(
            invalid_report["checks"]["uncertain_artifact_contracts_valid"]
        )

        for label, content in (
            ("infinite", b'{"x":1e400}\n'),
            ("surrogate", b'{"x":"\\ud800"}\n'),
        ):
            uncertain, repeated = self.fresh_pair(f"canonical-{label}")
            (uncertain / "coding-reliability.json").write_bytes(content)
            result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                self.assertFalse(
                    report["checks"]["uncertain_artifact_contracts_valid"]
                )

        uncertain, repeated = self.fresh_pair("numeric-resource-limit")
        configured_limit = (
            sys.get_int_max_str_digits()
            if hasattr(sys, "get_int_max_str_digits")
            else 4300
        )
        digits = max(configured_limit + 1, 5000)
        (uncertain / "coding-reliability.json").write_bytes(
            b'{"x":' + (b"9" * digits) + b"}\n"
        )
        numeric_limit = self.run_cli(
            self.argv(uncertain=uncertain, repeated=repeated)
        )
        self.assertEqual(2, numeric_limit[0])
        numeric_report = self.assert_report(numeric_limit)
        self.assertEqual("unreadable", numeric_report["status"])
        self.assertFalse(
            numeric_report["checks"]["uncertain_directory_readable"]
        )
        self.assertIsNone(
            numeric_report["checks"]["final_recapture_valid"]
        )
        self.assertEqual(
            ["uncertain_finalization_unreadable"],
            numeric_report["reason_codes"],
        )
        self.assertEqual(
            ["check_local_read_access"],
            [item["code"] for item in numeric_report["remediation"]],
        )
        self.assertNotIn(
            "uncertain_finalization_artifact_contract_invalid",
            numeric_report["reason_codes"],
        )

    def test_stable_evaluation_memory_bound_is_not_input_drift(self) -> None:
        real_resource_guard = cli._assert_json_resource_limits
        injected = False

        def memory_bound(
            value: object,
            *,
            label: str,
        ) -> None:
            nonlocal injected
            if not injected and label == "coding-reliability.json":
                injected = True
                raise MemoryError("private resource marker")
            real_resource_guard(value, label=label)

        with mock.patch.object(
            cli,
            "_assert_json_resource_limits",
            side_effect=memory_bound,
        ):
            result = self.run_cli()
        self.assertTrue(injected)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["uncertain_directory_readable"])
        self.assertTrue(report["checks"]["repeated_native_relation_valid"])
        self.assertIsNone(report["checks"]["final_recapture_valid"])
        self.assertEqual(
            ["uncertain_finalization_unreadable"],
            report["reason_codes"],
        )
        self.assertEqual(
            ["check_local_read_access"],
            [item["code"] for item in report["remediation"]],
        )
        self.assertNotIn("private resource marker", result[1])

    def test_lexical_resource_preflight_runs_before_json_materialization(self) -> None:
        uncertain, repeated = self.fresh_pair("lexical-resource-preflight")
        array = b"[" + b",".join([b"0"] * 20) + b"]"
        members = [
            (f'"k{index:05d}":'.encode("ascii") + array)
            for index in range(cli._AUDIT_IMPORT_MAX_COLLECTION_ITEMS)
        ]
        content = b"{" + b",".join(members) + b"}\n"
        self.assertLess(
            len(content),
            cli._AUDIT_FINALIZATION_FILE_LIMITS["coding-reliability.json"],
        )
        (uncertain / "coding-reliability.json").write_bytes(content)

        real_loads = cli.json.loads
        normal_loads = 0

        def guarded_loads(value: object, *args: object, **kwargs: object) -> object:
            nonlocal normal_loads
            if isinstance(value, str) and value.startswith('{"k00000":'):
                self.fail("oversized JSON reached json.loads")
            normal_loads += 1
            return real_loads(value, *args, **kwargs)

        with mock.patch.object(cli.json, "loads", side_effect=guarded_loads):
            result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertGreaterEqual(normal_loads, 2)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["uncertain_directory_readable"])
        self.assertTrue(report["checks"]["repeated_native_relation_valid"])

    def test_directory_mode_and_owner_are_privacy_invalid(self) -> None:
        uncertain, repeated = self.fresh_pair("directory-mode")
        os.chmod(repeated, 0o750)
        mode_result = self.run_cli(
            self.argv(uncertain=uncertain, repeated=repeated)
        )
        self.assertEqual(2, mode_result[0])
        mode_report = self.assert_report(mode_result)
        self.assertFalse(mode_report["checks"]["repeated_directory_private"])

        real_capture = cli._capture_private_finalization_descriptor
        calls = 0

        def foreign_owner_capture(
            descriptor: int,
            **kwargs: object,
        ) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls != 2:
                return real_capture(descriptor, **kwargs)
            owner = cli.os.fstat(descriptor).st_uid
            with mock.patch.object(cli.os, "geteuid", return_value=owner + 1):
                return real_capture(descriptor, **kwargs)

        with mock.patch.object(
            cli,
            "_capture_private_finalization_descriptor",
            side_effect=foreign_owner_capture,
        ):
            owner_result = self.run_cli()
        self.assertEqual(2, owner_result[0])
        owner_report = self.assert_report(owner_result)
        self.assertEqual("invalid", owner_report["status"])
        self.assertFalse(owner_report["checks"]["repeated_directory_private"])

    def test_directory_mode_change_after_open_is_input_change(self) -> None:
        uncertain, repeated = self.fresh_pair("directory-mode-after-open")
        real_open = cli._open_finalization_comparison_directory_at
        calls = 0

        def open_then_chmod(
            parent_descriptor: int,
            directory_name: str,
        ) -> tuple[int, tuple[int, ...]]:
            nonlocal calls
            descriptor, identity = real_open(parent_descriptor, directory_name)
            calls += 1
            if calls == 2:
                os.fchmod(descriptor, 0o755)
            return descriptor, identity

        with mock.patch.object(
            cli,
            "_open_finalization_comparison_directory_at",
            side_effect=open_then_chmod,
        ):
            result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
        self.assertEqual(2, calls)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertIn("comparison_input_changed", report["reason_codes"])
        self.assertNotIn(
            "repeated_finalization_privacy_invalid",
            report["reason_codes"],
        )

    def test_file_owner_subdirectory_and_device_are_privacy_invalid(self) -> None:
        class StatView:
            def __init__(self, source: os.stat_result, **changes: object) -> None:
                self._source = source
                self._changes = changes

            def __getattr__(self, name: str) -> object:
                if name in self._changes:
                    return self._changes[name]
                return getattr(self._source, name)

        real_capture = cli._capture_private_finalization_descriptor
        real_stat = cli.os.stat

        for label in ("owner", "device"):
            uncertain, repeated = self.fresh_pair(f"file-{label}")
            calls = 0
            hostile_descriptor: int | None = None
            case = label

            def capture(
                descriptor: int,
                **kwargs: object,
            ) -> dict[str, object]:
                nonlocal calls, hostile_descriptor
                calls += 1
                if calls == 2:
                    hostile_descriptor = descriptor
                return real_capture(descriptor, **kwargs)

            def hostile_stat(
                path: object,
                *args: object,
                **kwargs: object,
            ) -> os.stat_result:
                observed = real_stat(path, *args, **kwargs)
                if (
                    path == FINALIZATION_FILES[0]
                    and kwargs.get("dir_fd") == hostile_descriptor
                ):
                    if case == "owner":
                        return StatView(
                            observed,
                            st_uid=observed.st_uid + 1,
                        )  # type: ignore[return-value]
                    return StatView(
                        observed,
                        st_mode=stat.S_IFCHR | 0o600,
                    )  # type: ignore[return-value]
                return observed

            with (
                mock.patch.object(
                    cli,
                    "_capture_private_finalization_descriptor",
                    side_effect=capture,
                ),
                mock.patch.object(cli.os, "stat", side_effect=hostile_stat),
            ):
                result = self.run_cli(
                    self.argv(uncertain=uncertain, repeated=repeated)
                )
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                self.assertFalse(
                    report["checks"]["repeated_directory_private"]
                )

        uncertain, repeated = self.fresh_pair("file-subdirectory")
        leaf = repeated / FINALIZATION_FILES[0]
        leaf.unlink()
        leaf.mkdir(mode=0o700)
        subdirectory = self.run_cli(
            self.argv(uncertain=uncertain, repeated=repeated)
        )
        self.assertEqual(2, subdirectory[0])
        subdirectory_report = self.assert_report(subdirectory)
        self.assertFalse(
            subdirectory_report["checks"]["repeated_directory_private"]
        )

    def test_same_inode_rewrite_and_leaf_replacement_are_input_changes(self) -> None:
        real_evaluate = cli._evaluate_finalization_comparison_capture
        rewritten = False
        original_inode = (self.uncertain / FINALIZATION_FILES[0]).stat().st_ino

        def rewrite_then_evaluate(
            descriptor: int,
            capture: object,
            *,
            expected_receipt_sha256: str | None,
        ) -> dict[str, bool | None]:
            nonlocal rewritten
            if not rewritten:
                rewritten = True
                path = self.uncertain / FINALIZATION_FILES[0]
                content = path.read_bytes()
                path.write_bytes(content)
                self.assertEqual(original_inode, path.stat().st_ino)
            return real_evaluate(
                descriptor,
                capture,
                expected_receipt_sha256=expected_receipt_sha256,
            )

        with mock.patch.object(
            cli,
            "_evaluate_finalization_comparison_capture",
            side_effect=rewrite_then_evaluate,
        ):
            rewrite_result = self.run_cli()
        self.assertEqual(2, rewrite_result[0])
        rewrite_report = self.assert_report(rewrite_result)
        self.assertIn("comparison_input_changed", rewrite_report["reason_codes"])

        uncertain, repeated = self.fresh_pair("leaf-replacement")
        real_compare = cli._finalization_directory_bytes_equal
        replaced = False

        def replace_then_compare(*args: object, **kwargs: object) -> bool:
            nonlocal replaced
            replaced = True
            leaf = repeated / FINALIZATION_FILES[0]
            retained = self.root / "retained-original-leaf"
            leaf.rename(retained)
            shutil.copy2(retained, leaf)
            return real_compare(*args, **kwargs)

        with mock.patch.object(
            cli,
            "_finalization_directory_bytes_equal",
            side_effect=replace_then_compare,
        ):
            replacement_result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
        self.assertTrue(replaced)
        self.assertEqual(2, replacement_result[0])
        replacement_report = self.assert_report(replacement_result)
        self.assertIsNone(
            replacement_report["checks"]["directory_file_bytes_equal"]
        )
        self.assertIn(
            "comparison_input_changed",
            replacement_report["reason_codes"],
        )

    def test_add_or_unlink_during_listing_is_input_change_not_inventory(self) -> None:
        real_scandir = cli.os.scandir

        class SnapshotScandir:
            def __init__(self, descriptor: int, mutate: object) -> None:
                iterator = real_scandir(descriptor)
                try:
                    self.entries = list(iterator)
                finally:
                    iterator.close()
                mutate()

            def __enter__(self) -> object:
                return iter(self.entries)

            def __exit__(self, *args: object) -> None:
                return None

        for operation in ("add", "unlink"):
            uncertain, repeated = self.fresh_pair(f"listing-{operation}")
            injected = False

            def hostile_scandir(descriptor: int) -> object:
                nonlocal injected
                if injected:
                    return real_scandir(descriptor)
                injected = True

                def mutate() -> None:
                    if operation == "add":
                        extra = uncertain / "late-extra"
                        extra.write_bytes(b"private")
                        os.chmod(extra, 0o600)
                    else:
                        (uncertain / FINALIZATION_FILES[0]).unlink()

                return SnapshotScandir(descriptor, mutate)

            with mock.patch.object(
                cli.os,
                "scandir",
                side_effect=hostile_scandir,
            ):
                result = self.run_cli(
                    self.argv(uncertain=uncertain, repeated=repeated)
                )
            with self.subTest(operation=operation):
                self.assertTrue(injected)
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertIn(
                    "comparison_input_changed",
                    report["reason_codes"],
                )
                self.assertNotIn(
                    "uncertain_finalization_inventory_invalid",
                    report["reason_codes"],
                )
                self.assertIn(
                    "administrator_quarantine",
                    {item["code"] for item in report["remediation"]},
                )

    def test_fifo_replacement_between_listing_and_stat_is_input_change(self) -> None:
        uncertain, repeated = self.fresh_pair("listing-fifo-replacement")
        real_capture = cli._capture_private_finalization_descriptor
        real_stat = cli.os.stat
        capture_calls = 0
        injected = False

        def capture(
            descriptor: int,
            **kwargs: object,
        ) -> dict[str, object]:
            nonlocal capture_calls
            capture_calls += 1
            if capture_calls != 2:
                return real_capture(descriptor, **kwargs)

            def replacing_stat(
                path: object,
                *args: object,
                **kwargs: object,
            ) -> os.stat_result:
                nonlocal injected
                if (
                    not injected
                    and path == FINALIZATION_FILES[0]
                    and kwargs.get("dir_fd") == descriptor
                ):
                    injected = True
                    leaf = repeated / FINALIZATION_FILES[0]
                    leaf.unlink()
                    os.mkfifo(leaf, mode=0o600)
                return real_stat(path, *args, **kwargs)

            with mock.patch.object(cli.os, "stat", side_effect=replacing_stat):
                return real_capture(descriptor, **kwargs)

        with mock.patch.object(
            cli,
            "_capture_private_finalization_descriptor",
            side_effect=capture,
        ):
            result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
        self.assertTrue(injected)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertIn("comparison_input_changed", report["reason_codes"])
        self.assertNotIn(
            "repeated_finalization_privacy_invalid",
            report["reason_codes"],
        )

    def test_invalid_inventory_or_privacy_drift_is_final_recapture_failure(
        self,
    ) -> None:
        real_observe = cli._capture_finalization_comparison_invalid_observation
        for label in ("inventory-delete", "privacy-chmod"):
            uncertain, repeated = self.fresh_pair(f"invalid-drift-{label}")
            if label == "inventory-delete":
                target = repeated / "extra-private"
                target.write_bytes(b"private")
                os.chmod(target, 0o600)
            else:
                target = repeated / FINALIZATION_FILES[0]
                os.chmod(target, 0o640)
            observation_calls = 0

            def observe(
                descriptor: int,
                *,
                expected_directory_identity: tuple[int, ...],
            ) -> dict[str, object]:
                nonlocal observation_calls
                observation_calls += 1
                if observation_calls == 2:
                    if label == "inventory-delete":
                        target.unlink()
                    else:
                        os.chmod(target, 0o600)
                return real_observe(
                    descriptor,
                    expected_directory_identity=expected_directory_identity,
                )

            with mock.patch.object(
                cli,
                "_capture_finalization_comparison_invalid_observation",
                side_effect=observe,
            ):
                result = self.run_cli(
                    self.argv(uncertain=uncertain, repeated=repeated)
                )
            with self.subTest(label=label):
                self.assertGreaterEqual(observation_calls, 2)
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(report["checks"]["final_recapture_valid"])
                self.assertFalse(
                    report["checks"]["repeated_directory_readable"]
                )
                self.assertIn(
                    "comparison_input_changed",
                    report["reason_codes"],
                )
                self.assertIn(
                    "administrator_quarantine",
                    {item["code"] for item in report["remediation"]},
                )

    def test_invalid_inventory_observes_fixed_leaf_omitted_by_bounded_listing(
        self,
    ) -> None:
        uncertain, repeated = self.fresh_pair("invalid-omitted-fixed-leaf")
        extra = repeated / "000-extra-private"
        extra.write_bytes(b"private")
        os.chmod(extra, 0o600)
        target = repeated / sorted(FINALIZATION_FILES)[-1]
        real_scandir = cli.os.scandir
        real_observe = cli._capture_finalization_comparison_invalid_observation
        observation_calls = 0

        class OrderedScandir:
            def __init__(self, descriptor: int) -> None:
                iterator = real_scandir(descriptor)
                try:
                    self.entries = sorted(
                        list(iterator),
                        key=lambda entry: entry.name,
                    )
                finally:
                    iterator.close()

            def __enter__(self) -> object:
                return iter(self.entries)

            def __exit__(self, *args: object) -> None:
                return None

        def ordered_scandir(descriptor: int) -> OrderedScandir:
            return OrderedScandir(descriptor)

        def observe(
            descriptor: int,
            *,
            expected_directory_identity: tuple[int, ...],
        ) -> dict[str, object]:
            nonlocal observation_calls
            observation_calls += 1
            result = real_observe(
                descriptor,
                expected_directory_identity=expected_directory_identity,
            )
            if observation_calls == 1:
                self.assertNotIn(target.name, result["names"])
                self.assertIn(target.name, result["file_identities"])
                target.write_bytes(target.read_bytes())
            return result

        with (
            mock.patch.object(cli.os, "scandir", side_effect=ordered_scandir),
            mock.patch.object(
                cli,
                "_capture_finalization_comparison_invalid_observation",
                side_effect=observe,
            ),
        ):
            result = self.run_cli(
                self.argv(uncertain=uncertain, repeated=repeated)
            )
        self.assertGreaterEqual(observation_calls, 2)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertIn("comparison_input_changed", report["reason_codes"])

    def test_open_identity_fallback_detects_drift_after_unreadable_capture(
        self,
    ) -> None:
        real_capture = cli._capture_private_finalization_descriptor
        real_evaluate = cli._evaluate_finalization_comparison_capture
        for operation in ("chmod", "rebind"):
            uncertain, repeated = self.fresh_pair(f"fallback-{operation}")
            capture_calls = 0
            mutated = False
            moved = repeated.with_name(f"{repeated.name}-retained")

            def capture(
                descriptor: int,
                **kwargs: object,
            ) -> dict[str, object]:
                nonlocal capture_calls
                capture_calls += 1
                if capture_calls == 2:
                    raise cli._FinalizationComparisonCaptureError("unreadable")
                return real_capture(descriptor, **kwargs)

            def evaluate_then_mutate(
                descriptor: int,
                capture_value: object,
                *,
                expected_receipt_sha256: str | None,
            ) -> dict[str, bool | None]:
                nonlocal mutated
                if not mutated:
                    mutated = True
                    if operation == "chmod":
                        os.chmod(repeated, 0o755)
                    else:
                        repeated.rename(moved)
                        shutil.copytree(moved, repeated, copy_function=shutil.copy2)
                return real_evaluate(
                    descriptor,
                    capture_value,
                    expected_receipt_sha256=expected_receipt_sha256,
                )

            try:
                with (
                    mock.patch.object(
                        cli,
                        "_capture_private_finalization_descriptor",
                        side_effect=capture,
                    ),
                    mock.patch.object(
                        cli,
                        "_capture_finalization_comparison_invalid_observation",
                        side_effect=cli._FinalizationComparisonCaptureError(
                            "unreadable"
                        ),
                    ),
                    mock.patch.object(
                        cli,
                        "_evaluate_finalization_comparison_capture",
                        side_effect=evaluate_then_mutate,
                    ),
                ):
                    result = self.run_cli(
                        self.argv(uncertain=uncertain, repeated=repeated)
                    )
            finally:
                if operation == "chmod" and repeated.exists():
                    os.chmod(repeated, 0o700)
                if moved.exists():
                    shutil.rmtree(repeated)
                    moved.rename(repeated)
            with self.subTest(operation=operation):
                self.assertTrue(mutated)
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(report["checks"]["final_recapture_valid"])
                self.assertIn(
                    "comparison_input_changed",
                    report["reason_codes"],
                )

    def test_fault_baselines_cannot_be_reset_before_handler_recapture(self) -> None:
        repeated_true_checks = (
            "repeated_directory_readable",
            "repeated_directory_private",
            "repeated_inventory_exact",
            "repeated_artifact_contracts_valid",
            "repeated_receipt_self_digest_valid",
            "repeated_external_receipt_digest_valid",
            "repeated_receipt_file_bindings_valid",
            "repeated_native_relation_valid",
        )
        for case in (
            "privacy-restored",
            "oversize-restored",
            "open-eacces-then-chmod",
            "directory-open-eacces-then-chmod",
        ):
            uncertain, repeated = self.fresh_pair(f"fault-baseline-{case}")
            target = uncertain / FINALIZATION_FILES[0]
            real_capture = cli._capture_private_finalization_descriptor
            capture_calls = 0
            injected = False

            def capture(
                descriptor: int,
                **kwargs: object,
            ) -> dict[str, object]:
                nonlocal capture_calls
                capture_calls += 1
                try:
                    return real_capture(descriptor, **kwargs)
                except cli._FinalizationComparisonCaptureError:
                    if capture_calls == 1:
                        if case == "privacy-restored":
                            os.chmod(target, 0o600)
                        elif case == "oversize-restored":
                            target.write_bytes(original_content)
                            os.chmod(target, 0o600)
                        elif case == "open-eacces-then-chmod":
                            os.chmod(target, 0o640)
                            os.chmod(target, 0o600)
                    raise

            if case == "privacy-restored":
                os.chmod(target, 0o640)
                context = contextlib.ExitStack()
                context.enter_context(
                    mock.patch.object(
                        cli,
                        "_capture_private_finalization_descriptor",
                        side_effect=capture,
                    )
                )
            elif case == "oversize-restored":
                original_content = target.read_bytes()
                with target.open("r+b") as stream:
                    stream.truncate(
                        cli._AUDIT_FINALIZATION_FILE_LIMITS[
                            FINALIZATION_FILES[0]
                        ]
                        + 1
                    )
                context = contextlib.ExitStack()
                context.enter_context(
                    mock.patch.object(
                        cli,
                        "_capture_private_finalization_descriptor",
                        side_effect=capture,
                    )
                )
            elif case == "open-eacces-then-chmod":
                real_open = cli.os.open

                def child_open(
                    path: object,
                    flags: int,
                    *args: object,
                    **kwargs: object,
                ) -> int:
                    nonlocal injected
                    if (
                        not injected
                        and path == FINALIZATION_FILES[0]
                        and kwargs.get("dir_fd") is not None
                    ):
                        injected = True
                        raise PermissionError(errno.EACCES, "closed marker")
                    return real_open(path, flags, *args, **kwargs)

                context = contextlib.ExitStack()
                context.enter_context(
                    mock.patch.object(cli.os, "open", side_effect=child_open)
                )
                context.enter_context(
                    mock.patch.object(
                        cli,
                        "_capture_private_finalization_descriptor",
                        side_effect=capture,
                    )
                )
            else:
                real_directory_open = (
                    cli._open_finalization_comparison_directory_at
                )
                real_open = cli.os.open

                def directory_open(
                    path: object,
                    flags: int,
                    *args: object,
                    **kwargs: object,
                ) -> int:
                    nonlocal injected
                    if (
                        not injected
                        and path == uncertain.name
                        and kwargs.get("dir_fd") is not None
                    ):
                        injected = True
                        raise PermissionError(errno.EACCES, "closed marker")
                    return real_open(path, flags, *args, **kwargs)

                def observe_directory_open(
                    parent_descriptor: int,
                    directory_name: str,
                ) -> tuple[int, tuple[int, ...]]:
                    try:
                        return real_directory_open(
                            parent_descriptor,
                            directory_name,
                        )
                    except cli._FinalizationComparisonCaptureError:
                        if directory_name == uncertain.name:
                            os.chmod(uncertain, 0o711)
                            os.chmod(uncertain, 0o700)
                        raise

                context = contextlib.ExitStack()
                context.enter_context(
                    mock.patch.object(cli.os, "open", side_effect=directory_open)
                )
                context.enter_context(
                    mock.patch.object(
                        cli,
                        "_open_finalization_comparison_directory_at",
                        side_effect=observe_directory_open,
                    )
                )

            with context:
                result = self.run_cli(
                    self.argv(uncertain=uncertain, repeated=repeated)
                )
            with self.subTest(case=case):
                if "eacces" in case:
                    self.assertTrue(injected)
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertEqual(
                    [
                        "uncertain_finalization_unreadable",
                        "comparison_input_changed",
                    ],
                    report["reason_codes"],
                )
                self.assertTrue(report["checks"]["common_parent_valid"])
                self.assertTrue(
                    report["checks"]["expected_receipt_sha256_valid"]
                )
                self.assertFalse(
                    report["checks"]["uncertain_directory_readable"]
                )
                self.assertFalse(report["checks"]["final_recapture_valid"])
                self.assertIsNone(report["checks"]["directories_distinct"])
                self.assertIsNone(
                    report["checks"]["directory_file_bytes_equal"]
                )
                for check in repeated_true_checks:
                    self.assertTrue(report["checks"][check], check)

    def test_parent_replacement_is_caught_with_held_descriptors(self) -> None:
        real_capture = cli._capture_private_finalization_descriptor
        calls = 0
        moved = self.root.with_name(f"{self.root.name}-retained")

        def replace_parent_then_capture(
            descriptor: int,
            **kwargs: object,
        ) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 3:
                self.root.rename(moved)
                self.root.mkdir(mode=0o700)
            return real_capture(descriptor, **kwargs)

        try:
            with mock.patch.object(
                cli,
                "_capture_private_finalization_descriptor",
                side_effect=replace_parent_then_capture,
            ):
                result = self.run_cli()
        finally:
            if moved.exists():
                shutil.rmtree(self.root)
                moved.rename(self.root)
        self.assertGreaterEqual(calls, 3)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertTrue(report["checks"]["directory_file_bytes_equal"])
        self.assertIn("comparison_input_changed", report["reason_codes"])

    def test_same_parent_inode_with_metadata_drift_is_not_topology_mismatch(self) -> None:
        real_path_info = cli._finalization_comparison_path_info
        calls = 0

        def drifting_path_info(raw_value: str) -> dict[str, object]:
            nonlocal calls
            calls += 1
            result = dict(real_path_info(raw_value))
            if calls == 2:
                identity = list(result["parent_identity"])
                identity[-1] += 1
                result["parent_identity"] = tuple(identity)
            return result

        with mock.patch.object(
            cli,
            "_finalization_comparison_path_info",
            side_effect=drifting_path_info,
        ):
            result = self.run_cli()
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertIsNone(report["checks"]["common_parent_valid"])
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertIn("comparison_input_changed", report["reason_codes"])
        self.assertNotIn("comparison_topology_invalid", report["reason_codes"])

    def test_empty_nul_and_unencodable_paths_return_closed_value_free_reports(
        self,
    ) -> None:
        real_stat = cli.os.stat
        cwd_path = os.fspath(Path.cwd())
        for label, hostile in (
            ("empty", ""),
            ("nul", "private\x00path"),
            ("surrogate", "private-\ud800-path"),
        ):
            cwd_stat_count = 0

            def track_stat(
                path: object,
                *args: object,
                **kwargs: object,
            ) -> os.stat_result:
                nonlocal cwd_stat_count
                try:
                    rendered_path = os.fspath(path)
                except TypeError:
                    rendered_path = None
                if kwargs.get("dir_fd") is None and rendered_path == cwd_path:
                    cwd_stat_count += 1
                return real_stat(path, *args, **kwargs)

            argv = self.argv()
            argv[4] = hostile
            with mock.patch.object(cli.os, "stat", side_effect=track_stat):
                result = self.run_cli(argv)
            with self.subTest(label=label):
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertIn(report["status"], {"invalid", "unreadable"})
                self.assertFalse(
                    report["checks"]["uncertain_directory_readable"]
                )
                self.assertEqual(0, cwd_stat_count)
                if hostile:
                    self.assertNotIn(hostile, result[1])

    def test_parent_open_disappearance_is_changed_but_stable_fault_is_unreadable(
        self,
    ) -> None:
        real_open = cli.os.open
        expected_parent = self.root.resolve()
        stable_injected = False

        def stable_failure(path: object, flags: int, *args: object, **kwargs: object) -> int:
            nonlocal stable_injected
            if not stable_injected and os.fspath(path) == os.fspath(expected_parent):
                stable_injected = True
                raise PermissionError(errno.EACCES, "stable parent marker")
            return real_open(path, flags, *args, **kwargs)

        with mock.patch.object(cli.os, "open", side_effect=stable_failure):
            stable = self.run_cli()
        self.assertTrue(stable_injected)
        self.assertEqual(2, stable[0])
        stable_report = self.assert_report(stable)
        self.assertEqual("unreadable", stable_report["status"])
        self.assertNotIn("comparison_input_changed", stable_report["reason_codes"])

        moved = self.root.with_name(f"{self.root.name}-disappeared")
        injected = False

        def disappearing_open(
            path: object,
            flags: int,
            *args: object,
            **kwargs: object,
        ) -> int:
            nonlocal injected
            if not injected and os.fspath(path) == os.fspath(expected_parent):
                injected = True
                self.root.rename(moved)
                raise FileNotFoundError(errno.ENOENT, "parent disappeared")
            return real_open(path, flags, *args, **kwargs)

        try:
            with mock.patch.object(cli.os, "open", side_effect=disappearing_open):
                disappeared = self.run_cli()
        finally:
            if moved.exists():
                moved.rename(self.root)
        self.assertTrue(injected)
        self.assertEqual(2, disappeared[0])
        disappeared_report = self.assert_report(disappeared)
        self.assertIn(
            "comparison_input_changed",
            disappeared_report["reason_codes"],
        )

    def test_stdout_interruption_is_code_two_without_promised_report(self) -> None:
        before = {
            "uncertain": _directory_snapshot(self.uncertain),
            "repeated": _directory_snapshot(self.repeated),
        }
        with mock.patch.object(
            cli,
            "_write_stdout_bytes",
            side_effect=BrokenPipeError("стандартный вывод недоступен"),
        ):
            result = self.run_cli()
        self.assertEqual(2, result[0])
        self.assertEqual("", result[1])
        self.assertIn("Ошибка:", result[2])
        self.assertEqual(before["uncertain"], _directory_snapshot(self.uncertain))
        self.assertEqual(before["repeated"], _directory_snapshot(self.repeated))

    def test_acl_failure_after_open_closes_file_descriptor(self) -> None:
        directory_descriptor = os.open(
            self.uncertain,
            cli._no_follow_open_flags() | getattr(os, "O_DIRECTORY", 0),
        )
        path = self.uncertain / FINALIZATION_FILES[0]
        expected = {
            "identity": cli._stable_file_identity(path.stat()),
            "sha256": "unused",
        }
        opened: list[int] = []
        real_open = cli.os.open

        def recording_open(
            name: object,
            flags: int,
            *args: object,
            **kwargs: object,
        ) -> int:
            descriptor = real_open(name, flags, *args, **kwargs)
            opened.append(descriptor)
            return descriptor

        try:
            with (
                mock.patch.object(cli.os, "open", side_effect=recording_open),
                mock.patch.object(
                    cli,
                    "_assert_finalization_comparison_acl",
                    side_effect=cli._FinalizationComparisonCaptureError(
                        "privacy",
                        inventory_exact=True,
                    ),
                ),
                self.assertRaises(cli._FinalizationComparisonCaptureError),
            ):
                cli._open_captured_finalization_file(
                    directory_descriptor,
                    FINALIZATION_FILES[0],
                    expected,
                )
            self.assertEqual(1, len(opened))
            with self.assertRaises(OSError) as raised:
                os.fstat(opened[0])
            self.assertEqual(errno.EBADF, raised.exception.errno)
        finally:
            os.close(directory_descriptor)


if __name__ == "__main__":
    unittest.main()
