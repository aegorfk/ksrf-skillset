from __future__ import annotations

import contextlib
import copy
from collections.abc import Callable
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

from judicial_meaning import cli

if __package__:
    from . import test_native_coding_review_import_cli as import_harness
else:
    import test_native_coding_review_import_cli as import_harness


REPO = Path(__file__).resolve().parents[3]
SCRIPT = (
    REPO
    / "skills"
    / "ksrf-cassation-judicial-meaning"
    / "scripts"
    / "judicial_meaning.py"
)
SOURCE_CODEBOOK = (
    REPO
    / "skills"
    / "ksrf-cassation-judicial-meaning"
    / "references"
    / "coding-audit-codebook-v1.md"
)
TOP_LEVEL_KEYS = {
    "schema_version",
    "artifact_type",
    "status",
    "recovery_comparison_valid",
    "reason_codes",
    "checks",
    "remediation",
    "scope",
}
CHECK_KEYS = {
    "common_parent_valid",
    "directories_distinct",
    "source_bundle_readable",
    "source_bundle_private",
    "source_bundle_inventory_exact",
    "expected_manifest_sha256_valid",
    "source_bundle_contract_valid",
    "source_bundle_external_manifest_digest_valid",
    "installed_codebook_readable",
    "installed_codebook_binding_valid",
    "uncertain_directory_readable",
    "repeated_directory_readable",
    "uncertain_directory_private",
    "repeated_directory_private",
    "uncertain_inventory_exact",
    "repeated_inventory_exact",
    "expected_import_receipt_sha256_valid",
    "uncertain_artifact_contracts_valid",
    "repeated_artifact_contracts_valid",
    "uncertain_receipt_self_digest_valid",
    "repeated_receipt_self_digest_valid",
    "repeated_external_receipt_digest_valid",
    "uncertain_receipt_file_binding_valid",
    "repeated_receipt_file_binding_valid",
    "uncertain_bundle_relation_valid",
    "repeated_bundle_relation_valid",
    "import_directory_file_bytes_equal",
    "final_recapture_valid",
}
SCOPE = {
    "technical_recovery_comparison_only": True,
    "original_recovery_eligibility_verified": False,
    "prepare_normal_return_verified": False,
    "repeat_normal_return_verified": False,
    "external_manifest_digest_provenance_authenticated": False,
    "external_import_receipt_digest_provenance_authenticated": False,
    "original_durability_verified": False,
    "source_workspace_reverified": False,
    "returned_secondary_file_reverified": False,
    "consumer_revalidation_required": True,
    "reviewer_identity_authenticated": False,
    "publication_safe": False,
    "legal_readiness": False,
    "filing_authorized": False,
}
REASON_CODES = (
    "source_bundle_unreadable",
    "installed_codebook_unreadable",
    "uncertain_review_import_unreadable",
    "repeated_review_import_unreadable",
    "comparison_input_changed",
    "comparison_topology_invalid",
    "source_bundle_privacy_invalid",
    "uncertain_review_import_privacy_invalid",
    "repeated_review_import_privacy_invalid",
    "source_bundle_inventory_invalid",
    "uncertain_review_import_inventory_invalid",
    "repeated_review_import_inventory_invalid",
    "expected_manifest_sha256_invalid",
    "expected_import_receipt_sha256_invalid",
    "source_bundle_artifact_contract_invalid",
    "uncertain_review_import_artifact_contract_invalid",
    "repeated_review_import_artifact_contract_invalid",
    "external_manifest_digest_mismatch",
    "uncertain_review_import_receipt_self_digest_mismatch",
    "repeated_review_import_receipt_self_digest_mismatch",
    "external_import_receipt_digest_mismatch",
    "uncertain_review_import_file_binding_mismatch",
    "repeated_review_import_file_binding_mismatch",
    "uncertain_review_import_bundle_relation_mismatch",
    "repeated_review_import_bundle_relation_mismatch",
    "review_import_directory_bytes_mismatch",
)
REMEDIATION_MESSAGES = {
    "check_local_read_access": (
        "Проверьте доступность указанных локальных папок и встроенного справочника, "
        "не изменяя их; команда не выполняет восстановление."
    ),
    "preserve_and_stop": (
        "Остановите использование обеих папок импорта и сохраните пакет и результаты "
        "неизменными; команда ничего не исправляет и не удаляет."
    ),
    "use_safe_complete_siblings": (
        "Передавайте один полный семифайловый пакет и две разные полные двухфайловые "
        "папки импорта у одного приватного родителя; небезопасное или неполное состояние "
        "передайте системному администратору."
    ),
    "retain_successful_prepare_digest": (
        "Передайте manifest_sha256 только из полного стандартного вывода успешно и "
        "нормально завершившейся подготовки пакета; не восстанавливайте его из манифеста."
    ),
    "retain_successful_repeat_digest": (
        "Передайте receipt_sha256 только из полного стандартного вывода успешно и "
        "нормально завершившегося повторного импорта; не восстанавливайте его из квитанции."
    ),
    "administrator_quarantine": (
        "При изменении inode, жёсткой ссылке, ACL, неучтённом или перемещённом объекте "
        "остановите автоматику и передайте состояние системному администратору для учёта "
        "всех ссылок и карантина."
    ),
    "repeat_import_after_mismatch": (
        "Не используйте несовпавшие результаты; проверьте пакет и внешние якоря, затем "
        "только для разрешённого маршрута снова выполните импорт тех же неизменённых "
        "входов в новую отсутствующую соседнюю папку."
    ),
}


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


def _tree_snapshot(root: Path) -> dict[str, tuple[object, ...]]:
    snapshot: dict[str, tuple[object, ...]] = {}
    for path in (root, *sorted(root.rglob("*"))):
        path_stat = path.lstat()
        relative = "." if path == root else path.relative_to(root).as_posix()
        snapshot[relative] = (
            stat.S_IFMT(path_stat.st_mode),
            stat.S_IMODE(path_stat.st_mode),
            path_stat.st_uid,
            path_stat.st_gid,
            path_stat.st_nlink,
            path.read_bytes() if stat.S_ISREG(path_stat.st_mode) else None,
        )
    return snapshot


def _file_snapshot(path: Path) -> tuple[object, ...]:
    path_stat = path.lstat()
    return (
        stat.S_IFMT(path_stat.st_mode),
        stat.S_IMODE(path_stat.st_mode),
        path_stat.st_uid,
        path_stat.st_gid,
        path_stat.st_nlink,
        path.read_bytes(),
    )


class NativeReviewImportComparisonCliTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_tmp = tempfile.TemporaryDirectory()
        fixture_root = Path(cls.fixture_tmp.name)
        harness = import_harness.NativeCodingReviewImportCliTests(methodName="runTest")
        _, bundle, manifest_sha256 = harness._prepare_bundle(fixture_root)

        secondary_records = harness._secondary_records(bundle)
        secondary = harness._write_secondary(
            fixture_root,
            secondary_records,
            name="returned-identical.jsonl",
        )
        identical_imports: list[Path] = []
        identical_results: list[dict[str, object]] = []
        for name in ("uncertain-review-import", "repeated-review-import"):
            destination = fixture_root / name
            completed = harness._run(
                SCRIPT,
                harness._import_arguments(
                    bundle,
                    secondary,
                    destination,
                    manifest_sha256,
                ),
                cwd=fixture_root,
            )
            if completed.returncode != 0:
                raise AssertionError(completed.stderr)
            identical_imports.append(destination)
            identical_results.append(json.loads(completed.stdout))

        if identical_results[0]["receipt_sha256"] != identical_results[1]["receipt_sha256"]:
            raise AssertionError("Fixture review imports are not identical.")
        for filename in import_harness.OUTPUT_FILES:
            if (identical_imports[0] / filename).read_bytes() != (
                identical_imports[1] / filename
            ).read_bytes():
                raise AssertionError(f"Fixture file is not identical: {filename}")

        different_records = copy.deepcopy(secondary_records)
        different_records[0]["label"] = "mentioned_only"
        different_records[0]["proposition"] = (
            "Независимая формулировка того же вывода."
        )
        different_secondary = harness._write_secondary(
            fixture_root,
            different_records,
            name="returned-different.jsonl",
        )
        different_import = fixture_root / "different-review-import"
        different_completed = harness._run(
            SCRIPT,
            harness._import_arguments(
                bundle,
                different_secondary,
                different_import,
                manifest_sha256,
            ),
            cwd=fixture_root,
        )
        if different_completed.returncode != 0:
            raise AssertionError(different_completed.stderr)
        different_result = json.loads(different_completed.stdout)
        if all(
            (identical_imports[0] / filename).read_bytes()
            == (different_import / filename).read_bytes()
            for filename in import_harness.OUTPUT_FILES
        ):
            raise AssertionError("Different fixture unexpectedly has equal raw files.")

        first_decision = json.loads(
            (identical_imports[0] / "audit-decisions.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        cls.bundle_fixture = bundle
        cls.uncertain_fixture = identical_imports[0]
        cls.repeated_fixture = identical_imports[1]
        cls.different_fixture = different_import
        cls.expected_manifest_sha256 = manifest_sha256
        cls.expected_receipt_sha256 = str(identical_results[1]["receipt_sha256"])
        cls.different_receipt_sha256 = str(different_result["receipt_sha256"])
        cls.private_candidate_id = str(first_decision["candidate_id"])

        cls.install_tmp = tempfile.TemporaryDirectory()
        cls.installed_root = Path(cls.install_tmp.name) / "installed skills"
        installed = subprocess.run(
            [str(REPO / "install.sh"), "--target", str(cls.installed_root)],
            cwd=REPO,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )
        if installed.returncode != 0:
            raise AssertionError(installed.stderr)
        cls.installed_script = (
            cls.installed_root
            / "ksrf-cassation-judicial-meaning"
            / "scripts"
            / "judicial_meaning.py"
        )
        cls.installed_codebook = (
            cls.installed_root
            / "ksrf-cassation-judicial-meaning"
            / "references"
            / "coding-audit-codebook-v1.md"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.install_tmp.cleanup()
        cls.fixture_tmp.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fresh_inputs(
        self,
        label: str,
        *,
        repeated_fixture: Path | None = None,
    ) -> tuple[Path, Path, Path, Path]:
        parent = self.root / label
        parent.mkdir(mode=0o700)
        bundle = parent / "source-bundle"
        uncertain = parent / "uncertain-review-import"
        repeated = parent / "repeated-review-import"
        shutil.copytree(self.bundle_fixture, bundle, copy_function=shutil.copy2)
        shutil.copytree(
            self.uncertain_fixture,
            uncertain,
            copy_function=shutil.copy2,
        )
        shutil.copytree(
            repeated_fixture or self.repeated_fixture,
            repeated,
            copy_function=shutil.copy2,
        )
        return parent, bundle, uncertain, repeated

    @staticmethod
    def replace_bundle_file_and_refresh_manifest(
        bundle: Path,
        filename: str,
        content: bytes,
    ) -> str:
        (bundle / filename).write_bytes(content)
        manifest_path = bundle / "coding-audit-inputs-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            member_content = (bundle / entry["path"]).read_bytes()
            entry["bytes"] = len(member_content)
            entry["sha256"] = hashlib.sha256(member_content).hexdigest()
        unsigned_manifest = {
            key: value
            for key, value in manifest.items()
            if key != "manifest_sha256"
        }
        manifest["manifest_sha256"] = cli.canonical_digest(unsigned_manifest)
        manifest_path.write_bytes(_canonical_bytes(manifest))
        return str(manifest["manifest_sha256"])

    @staticmethod
    def refresh_review_import_receipt_for_bundle(
        review_import: Path,
        bundle: Path,
    ) -> str:
        manifest_path = bundle / "coding-audit-inputs-manifest.json"
        manifest_content = manifest_path.read_bytes()
        manifest = json.loads(manifest_content)
        audit_plan = json.loads(
            (bundle / "coding-audit-plan.json").read_text(encoding="utf-8")
        )
        receipt_path = review_import / "coding-audit-review-import-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["audit_plan_sha256"] = audit_plan["audit_plan_sha256"]
        receipt["source_bundle_manifest_sha256"] = manifest["manifest_sha256"]
        receipt["expected_source_bundle_manifest_sha256"] = manifest[
            "manifest_sha256"
        ]
        receipt["source_bundle_manifest_file_sha256"] = hashlib.sha256(
            manifest_content
        ).hexdigest()
        receipt["receipt_sha256"] = cli.canonical_digest(
            {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        )
        receipt_path.write_bytes(_canonical_bytes(receipt))
        return str(receipt["receipt_sha256"])

    @staticmethod
    def mutate_uncertain_decisions_and_refresh_receipt(
        uncertain: Path,
        mutate: Callable[[list[dict[str, object]]], None],
    ) -> str:
        decisions_path = uncertain / "audit-decisions.jsonl"
        decisions = [
            json.loads(line)
            for line in decisions_path.read_text(encoding="utf-8").splitlines()
        ]
        mutate(decisions)
        decisions_content = b"".join(_canonical_bytes(record) for record in decisions)
        decisions_path.write_bytes(decisions_content)

        receipt_path = uncertain / "coding-audit-review-import-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["audit_decisions_file_sha256"] = hashlib.sha256(
            decisions_content
        ).hexdigest()
        receipt["receipt_sha256"] = cli.canonical_digest(
            {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        )
        receipt_path.write_bytes(_canonical_bytes(receipt))
        return str(receipt["receipt_sha256"])

    def assert_uncertain_decisions_contract_invalid(
        self,
        label: str,
        mutate: Callable[[list[dict[str, object]]], None],
        *private_values: str,
    ) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs(label)
        uncertain_receipt_sha256 = (
            self.mutate_uncertain_decisions_and_refresh_receipt(uncertain, mutate)
        )
        before = _tree_snapshot(parent)

        result = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertFalse(report["recovery_comparison_valid"])
        self.assertEqual(
            [
                "uncertain_review_import_artifact_contract_invalid",
                "review_import_directory_bytes_mismatch",
            ],
            report["reason_codes"],
        )
        self.assertFalse(report["checks"]["uncertain_artifact_contracts_valid"])
        for dependent_check in (
            "uncertain_receipt_self_digest_valid",
            "uncertain_receipt_file_binding_valid",
            "uncertain_bundle_relation_valid",
        ):
            self.assertIsNone(report["checks"][dependent_check], dependent_check)
        self.assertTrue(report["checks"]["repeated_artifact_contracts_valid"])
        self.assertTrue(report["checks"]["repeated_receipt_self_digest_valid"])
        self.assertTrue(report["checks"]["repeated_external_receipt_digest_valid"])
        self.assertTrue(report["checks"]["repeated_receipt_file_binding_valid"])
        self.assertTrue(report["checks"]["repeated_bundle_relation_valid"])
        self.assertFalse(report["checks"]["import_directory_file_bytes_equal"])
        self.assertTrue(report["checks"]["final_recapture_valid"])
        self.assertEqual(
            [
                "preserve_and_stop",
                "use_safe_complete_siblings",
                "administrator_quarantine",
            ],
            [entry["code"] for entry in report["remediation"]],
        )
        self.assertNotIn(
            "repeat_import_after_mismatch",
            [entry["code"] for entry in report["remediation"]],
        )
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(
            result[1],
            str(parent),
            str(bundle),
            str(uncertain),
            str(repeated),
            self.expected_manifest_sha256,
            self.expected_receipt_sha256,
            uncertain_receipt_sha256,
            self.private_candidate_id,
            "audit-decisions.jsonl",
            *private_values,
        )

    def argv(
        self,
        bundle: Path,
        uncertain: Path,
        repeated: Path,
        *,
        manifest_sha256: str | None = None,
        receipt_sha256: str | None = None,
    ) -> list[str]:
        return [
            "quality",
            "native-reliability",
            "compare-review-imports",
            "--bundle",
            str(bundle),
            "--expected-manifest-sha256",
            manifest_sha256 or self.expected_manifest_sha256,
            "--uncertain-review-import-dir",
            str(uncertain),
            "--repeated-review-import-dir",
            str(repeated),
            "--expected-import-receipt-sha256",
            receipt_sha256 or self.expected_receipt_sha256,
        ]

    @staticmethod
    def run_cli(argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                result = cli.main(argv)
            except SystemExit as raised:
                code = int(raised.code or 0)
            else:
                code = int(result or 0)
        return code, stdout.getvalue(), stderr.getvalue()

    @staticmethod
    def run_script(
        script: Path,
        argv: list[str],
        *,
        cwd: Path,
        pythonpath: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        if pythonpath is not None:
            environment["PYTHONPATH"] = str(pythonpath)
        return subprocess.run(
            [sys.executable, str(script), *argv],
            cwd=cwd,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_report(self, result: tuple[int, str, str]) -> dict[str, object]:
        _, stdout, stderr = result
        self.assertEqual("", stderr)
        self.assertTrue(stdout.endswith("\n"))
        self.assertFalse(stdout.endswith("\n\n"))
        report = json.loads(stdout)
        self.assertEqual(_canonical_bytes(report), stdout.encode("utf-8"))
        self.assertEqual(TOP_LEVEL_KEYS, set(report))
        self.assertEqual("1.0", report["schema_version"])
        self.assertEqual(
            "native_review_import_comparison_report",
            report["artifact_type"],
        )
        self.assertIn(report["status"], {"match", "mismatch", "invalid", "unreadable"})
        self.assertIs(
            report["recovery_comparison_valid"],
            report["status"] == "match",
        )
        self.assertEqual(CHECK_KEYS, set(report["checks"]))
        self.assertEqual(28, len(report["checks"]))
        for key, value in report["checks"].items():
            self.assertIn(value, (True, False, None), key)
        self.assertEqual(SCOPE, report["scope"])
        self.assertIsInstance(report["reason_codes"], list)
        self.assertEqual(26, len(REASON_CODES))
        self.assertEqual(len(report["reason_codes"]), len(set(report["reason_codes"])))
        self.assertTrue(set(report["reason_codes"]).issubset(REASON_CODES))
        self.assertEqual(
            sorted(report["reason_codes"], key=REASON_CODES.index),
            report["reason_codes"],
        )
        remediation_codes: list[str] = []
        for entry in report["remediation"]:
            self.assertEqual({"code", "message_ru"}, set(entry))
            code = entry["code"]
            self.assertIn(code, REMEDIATION_MESSAGES)
            self.assertEqual(REMEDIATION_MESSAGES[code], entry["message_ru"])
            remediation_codes.append(code)
        self.assertEqual(len(remediation_codes), len(set(remediation_codes)))
        return report

    def assert_value_free(self, stdout: str, *private_values: str) -> None:
        for value in private_values:
            self.assertNotIn(value, stdout)
        self.assertIsNone(
            re.search(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", stdout)
        )

    def test_match_route_is_canonical_read_only_and_value_free(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs("matching-inputs")
        before = _tree_snapshot(parent)
        forbidden = AssertionError("comparison attempted a side effect")
        targets = (
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
            (subprocess, "run"),
            (subprocess, "Popen"),
            (socket, "socket"),
            (cli, "cmd_quality_coding_audit_review_import"),
            (cli, "_cmd_quality_coding_audit_review_import"),
            (cli, "build_native_coding_review_import"),
        )
        with contextlib.ExitStack() as stack:
            for owner, name in targets:
                stack.enter_context(mock.patch.object(owner, name, side_effect=forbidden))
            first = self.run_cli(self.argv(bundle, uncertain, repeated))
            second = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertEqual(first, second)
        self.assertEqual(0, first[0])
        report = self.assert_report(first)
        self.assertEqual("match", report["status"])
        self.assertEqual([], report["reason_codes"])
        self.assertEqual([], report["remediation"])
        self.assertTrue(all(value is True for value in report["checks"].values()))
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(
            first[1],
            str(parent),
            str(bundle),
            str(uncertain),
            str(repeated),
            self.expected_manifest_sha256,
            self.expected_receipt_sha256,
            self.private_candidate_id,
            "secondary-reviewer",
            "audit-decisions.jsonl",
        )

    def test_self_consistent_queue_tampering_never_matches(self) -> None:
        cases = (
            (
                "extra-field",
                lambda queue: queue[0].__setitem__(
                    "private_extra_queue_field",
                    "private-extra-queue-value",
                ),
                "private-extra-queue-value",
            ),
            (
                "wrong-primary-binding",
                lambda queue: queue[0].__setitem__(
                    "primary_coding_sha256",
                    "f" * 64,
                ),
                "f" * 64,
            ),
        )
        for label, mutate, private_value in cases:
            with self.subTest(case=label):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"queue-{label}"
                )
                queue_path = bundle / "secondary-review-queue.jsonl"
                queue = [
                    json.loads(line)
                    for line in queue_path.read_text(encoding="utf-8").splitlines()
                ]
                mutate(queue)
                manifest_sha256 = self.replace_bundle_file_and_refresh_manifest(
                    bundle,
                    queue_path.name,
                    b"".join(_canonical_bytes(record) for record in queue),
                )
                uncertain_receipt_sha256 = (
                    self.refresh_review_import_receipt_for_bundle(uncertain, bundle)
                )
                repeated_receipt_sha256 = (
                    self.refresh_review_import_receipt_for_bundle(repeated, bundle)
                )
                self.assertEqual(
                    uncertain_receipt_sha256,
                    repeated_receipt_sha256,
                )
                before = _tree_snapshot(parent)

                result = self.run_cli(
                    self.argv(
                        bundle,
                        uncertain,
                        repeated,
                        manifest_sha256=manifest_sha256,
                        receipt_sha256=repeated_receipt_sha256,
                    )
                )

                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                self.assertFalse(report["recovery_comparison_valid"])
                self.assertEqual(
                    ["source_bundle_artifact_contract_invalid"],
                    report["reason_codes"],
                )
                self.assertFalse(report["checks"]["source_bundle_contract_valid"])
                self.assertIsNone(
                    report["checks"][
                        "source_bundle_external_manifest_digest_valid"
                    ]
                )
                for role in ("uncertain", "repeated"):
                    self.assertTrue(
                        report["checks"][f"{role}_artifact_contracts_valid"]
                    )
                    self.assertTrue(
                        report["checks"][f"{role}_receipt_self_digest_valid"]
                    )
                    self.assertTrue(
                        report["checks"][f"{role}_receipt_file_binding_valid"]
                    )
                    self.assertIsNone(
                        report["checks"][f"{role}_bundle_relation_valid"]
                    )
                self.assertTrue(
                    report["checks"]["repeated_external_receipt_digest_valid"]
                )
                self.assertTrue(
                    report["checks"]["import_directory_file_bytes_equal"]
                )
                self.assertIsNone(report["checks"]["final_recapture_valid"])
                self.assertEqual(
                    [
                        "preserve_and_stop",
                        "use_safe_complete_siblings",
                        "administrator_quarantine",
                    ],
                    [entry["code"] for entry in report["remediation"]],
                )
                self.assertNotIn(
                    "repeat_import_after_mismatch",
                    [entry["code"] for entry in report["remediation"]],
                )
                self.assertEqual(before, _tree_snapshot(parent))
                self.assert_value_free(
                    result[1],
                    str(parent),
                    str(bundle),
                    str(uncertain),
                    str(repeated),
                    manifest_sha256,
                    uncertain_receipt_sha256,
                    private_value,
                    self.private_candidate_id,
                )

    def test_primary_quote_swapcase_valid_imports_still_compare_as_match(self) -> None:
        parent = self.root / "primary-quote-swapcase"
        parent.mkdir(mode=0o700)
        harness = import_harness.NativeCodingReviewImportCliTests(
            methodName="runTest"
        )
        state = harness._seed_workspace(parent)
        workspace = Path(state["workspace"])
        primary_path = workspace / "coding-decisions.jsonl"
        primary_records = [
            json.loads(line)
            for line in primary_path.read_text(encoding="utf-8").splitlines()
        ]
        original_quote = str(primary_records[0]["quote"])
        mutated_chain_id = primary_records[0]["chain_id"]
        swapped_quote = original_quote.swapcase().replace(" ", "  ")
        self.assertNotEqual(original_quote, swapped_quote)
        self.assertEqual(
            " ".join(original_quote.casefold().split()),
            " ".join(swapped_quote.casefold().split()),
        )
        primary_records[0]["quote"] = swapped_quote
        primary_path.write_bytes(
            b"".join(_canonical_bytes(record) for record in primary_records)
        )

        bundle = parent / "source-bundle"
        prepared = self.run_script(
            SCRIPT,
            [
                "quality",
                "coding-audit-prepare",
                "--workspace",
                str(workspace),
                "--codebook-version",
                "1.0",
                "--sample-size",
                "5",
                "--exclusion-sample-size",
                "5",
                "--output-dir",
                str(bundle),
            ],
            cwd=parent,
        )
        self.assertEqual(0, prepared.returncode, prepared.stderr)
        self.assertEqual("", prepared.stderr)
        prepared_payload = json.loads(prepared.stdout)
        manifest_sha256 = str(prepared_payload["manifest_sha256"])

        secondary_records = harness._secondary_records(bundle)
        mutated_secondary = next(
            record
            for record in secondary_records
            if record["chain_id"] == mutated_chain_id
        )
        mutated_secondary["quote"] = original_quote
        secondary = harness._write_secondary(
            parent,
            secondary_records,
            name="returned-literal-case.jsonl",
        )
        imports: list[Path] = []
        receipt_sha256s: list[str] = []
        for name in ("uncertain-review-import", "repeated-review-import"):
            destination = parent / name
            imported = self.run_script(
                SCRIPT,
                harness._import_arguments(
                    bundle,
                    secondary,
                    destination,
                    manifest_sha256,
                ),
                cwd=parent,
            )
            self.assertEqual(0, imported.returncode, imported.stderr)
            self.assertEqual("", imported.stderr)
            receipt_sha256s.append(str(json.loads(imported.stdout)["receipt_sha256"]))
            imports.append(destination)

        self.assertEqual(receipt_sha256s[0], receipt_sha256s[1])
        for filename in import_harness.OUTPUT_FILES:
            self.assertEqual(
                (imports[0] / filename).read_bytes(),
                (imports[1] / filename).read_bytes(),
                filename,
            )
        before = _tree_snapshot(parent)
        result = self.run_cli(
            self.argv(
                bundle,
                imports[0],
                imports[1],
                manifest_sha256=manifest_sha256,
                receipt_sha256=receipt_sha256s[1],
            )
        )

        self.assertEqual(0, result[0])
        report = self.assert_report(result)
        self.assertEqual("match", report["status"])
        self.assertTrue(report["recovery_comparison_valid"])
        self.assertEqual([], report["reason_codes"])
        self.assertEqual([], report["remediation"])
        self.assertTrue(all(value is True for value in report["checks"].values()))
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(
            result[1],
            str(parent),
            str(bundle),
            str(imports[0]),
            str(imports[1]),
            manifest_sha256,
            receipt_sha256s[1],
            original_quote,
            swapped_quote,
        )

    def test_non_required_primary_codebook_mismatch_is_source_contract_invalid(
        self,
    ) -> None:
        parent = self.root / "non-required-primary-codebook"
        parent.mkdir(mode=0o700)
        harness = import_harness.NativeCodingReviewImportCliTests(
            methodName="runTest"
        )
        state = harness._seed_workspace(parent, candidate_count=2)
        workspace = Path(state["workspace"])
        bundle = parent / "source-bundle"
        prepared = self.run_script(
            SCRIPT,
            [
                "quality",
                "coding-audit-prepare",
                "--workspace",
                str(workspace),
                "--codebook-version",
                "1.0",
                "--sample-size",
                "1",
                "--exclusion-sample-size",
                "0",
                "--output-dir",
                str(bundle),
            ],
            cwd=parent,
        )
        self.assertEqual(0, prepared.returncode, prepared.stderr)
        self.assertEqual("", prepared.stderr)
        initial_manifest_sha256 = str(json.loads(prepared.stdout)["manifest_sha256"])

        audit_plan_path = bundle / "coding-audit-plan.json"
        audit_plan = json.loads(audit_plan_path.read_text(encoding="utf-8"))
        required_candidate_ids = set(audit_plan["required_candidate_ids"])
        self.assertEqual(1, len(required_candidate_ids))
        secondary_records = [
            record
            for record in harness._secondary_records(bundle)
            if record["candidate_id"] in required_candidate_ids
        ]
        self.assertEqual(1, len(secondary_records))
        secondary = harness._write_secondary(
            parent,
            secondary_records,
            name="returned-non-required-control.jsonl",
        )
        imports: list[Path] = []
        for name in ("uncertain-review-import", "repeated-review-import"):
            destination = parent / name
            imported = self.run_script(
                SCRIPT,
                harness._import_arguments(
                    bundle,
                    secondary,
                    destination,
                    initial_manifest_sha256,
                ),
                cwd=parent,
            )
            self.assertEqual(0, imported.returncode, imported.stderr)
            self.assertEqual("", imported.stderr)
            imports.append(destination)

        primary_path = bundle / "primary-decisions.audit.jsonl"
        primary_records = [
            json.loads(line)
            for line in primary_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(2, len(primary_records))
        non_required = next(
            record
            for record in primary_records
            if record["candidate_id"] not in required_candidate_ids
        )
        non_required["codebook_version"] = "2.0"
        primary_path.write_bytes(
            b"".join(_canonical_bytes(record) for record in primary_records)
        )
        screening_records = [
            json.loads(line)
            for line in (
                bundle / "screening-candidates.audit.jsonl"
            ).read_text(encoding="utf-8").splitlines()
        ]
        refreshed_plan = cli.build_coding_audit_plan(
            screening_records,
            primary_records,
            plan_sha256=audit_plan["plan_sha256"],
            sample_size=audit_plan["sample_size"],
            exclusion_sample_size=audit_plan["exclusion_sample_size"],
        )
        self.assertEqual(
            audit_plan["required_candidate_ids"],
            refreshed_plan["required_candidate_ids"],
        )
        manifest_sha256 = self.replace_bundle_file_and_refresh_manifest(
            bundle,
            audit_plan_path.name,
            _canonical_bytes(refreshed_plan),
        )
        receipt_sha256s = [
            self.refresh_review_import_receipt_for_bundle(review_import, bundle)
            for review_import in imports
        ]
        self.assertEqual(receipt_sha256s[0], receipt_sha256s[1])
        before = _tree_snapshot(parent)

        result = self.run_cli(
            self.argv(
                bundle,
                imports[0],
                imports[1],
                manifest_sha256=manifest_sha256,
                receipt_sha256=receipt_sha256s[1],
            )
        )

        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertFalse(report["recovery_comparison_valid"])
        self.assertEqual(
            ["source_bundle_artifact_contract_invalid"],
            report["reason_codes"],
        )
        self.assertFalse(report["checks"]["source_bundle_contract_valid"])
        self.assertIsNone(
            report["checks"]["source_bundle_external_manifest_digest_valid"]
        )
        for role in ("uncertain", "repeated"):
            self.assertTrue(
                report["checks"][f"{role}_artifact_contracts_valid"]
            )
            self.assertTrue(
                report["checks"][f"{role}_receipt_self_digest_valid"]
            )
            self.assertTrue(
                report["checks"][f"{role}_receipt_file_binding_valid"]
            )
            self.assertIsNone(
                report["checks"][f"{role}_bundle_relation_valid"]
            )
        self.assertTrue(report["checks"]["repeated_external_receipt_digest_valid"])
        self.assertTrue(report["checks"]["import_directory_file_bytes_equal"])
        self.assertIsNone(report["checks"]["final_recapture_valid"])
        self.assertEqual(
            [
                "preserve_and_stop",
                "use_safe_complete_siblings",
                "administrator_quarantine",
            ],
            [entry["code"] for entry in report["remediation"]],
        )
        self.assertNotIn(
            "repeat_import_after_mismatch",
            [entry["code"] for entry in report["remediation"]],
        )
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(
            result[1],
            str(parent),
            str(bundle),
            str(imports[0]),
            str(imports[1]),
            initial_manifest_sha256,
            manifest_sha256,
            receipt_sha256s[1],
            str(non_required["candidate_id"]),
            "2.0",
        )

    def test_source_and_installed_help_are_russian_complete_and_bounded(self) -> None:
        hostile_pythonpath = self.root / "conflicting-pythonpath"
        hostile_package = hostile_pythonpath / "judicial_meaning"
        hostile_package.mkdir(parents=True)
        (hostile_package / "__init__.py").write_text(
            "raise RuntimeError('ambient package must not load')\n",
            encoding="utf-8",
        )
        argv = ["quality", "native-reliability", "compare-review-imports", "--help"]
        source = self.run_script(
            SCRIPT,
            argv,
            cwd=self.root,
            pythonpath=hostile_pythonpath,
        )
        installed = self.run_script(
            self.installed_script,
            argv,
            cwd=self.root,
            pythonpath=hostile_pythonpath,
        )
        self.assertEqual(0, source.returncode, source.stderr)
        self.assertEqual(source.returncode, installed.returncode)
        self.assertEqual(source.stdout, installed.stdout)
        self.assertEqual("", source.stderr)
        self.assertEqual(source.stderr, installed.stderr)

        help_text = " ".join(source.stdout.split())
        folded = help_text.casefold()
        self.assertIn("quality native-reliability compare-review-imports", help_text)
        for option, metavar in (
            ("--bundle", "ПАПКА_ПАКЕТА_АУДИТА"),
            ("--expected-manifest-sha256", "СОХРАНЁННЫЙ_SHA256_МАНИФЕСТА"),
            ("--uncertain-review-import-dir", "СОМНИТЕЛЬНАЯ_ПАПКА_ИМПОРТА"),
            ("--repeated-review-import-dir", "ПОВТОРНАЯ_ПАПКА_ИМПОРТА"),
            ("--expected-import-receipt-sha256", "SHA256_УСПЕШНОГО_ПОВТОРА"),
        ):
            self.assertIn(f"{option} {metavar}", help_text)
        self.assertNotIn("--output", help_text)
        self.assertNotIn("--expected-secondary-coder", help_text)
        self.assertNotIn("--secondary-coding", help_text)
        self.assertNotIn("--recovery", help_text)

        for fragment in (
            "семифайлов",
            "две разные полные двухфайловые",
            "прям",
            "сосед",
            "полного стандартного вывода",
            "подготов",
            "повторного импорта",
            "не берите",
            "не передавайте отдельные файлы",
            "частичную папку",
            "staging-папку",
            "манифест",
            "квитанц",
            "пакет",
            "штатные проверки потребителя импорта",
            "сырые байты",
            "полный повторный снимок",
            "детерминированный",
            "без значений",
            "один код 2",
            "полная исходная диагностика",
            "staging",
            "inode",
            "жёстких ссылок",
            "acl",
            "карантин",
            "системному администратору",
            "не создаёт выходных файлов",
            "не изменяет",
            "не удаляет",
            "не помещает в карантин",
            "не запускает импорт",
            "не перечитывает исходный возвращённый файл вторичной разметки",
            "не аутентифицирует метку кодировщика",
            "не разрешает расхождения проверки",
            "сети",
            "базе данных",
            "original_recovery_eligibility_verified=false",
            "prepare_normal_return_verified=false",
            "repeat_normal_return_verified=false",
            "external_manifest_digest_provenance_authenticated=false",
            "external_import_receipt_digest_provenance_authenticated=false",
            "original_durability_verified=false",
            "source_workspace_reverified=false",
            "returned_secondary_file_reverified=false",
            "юридическ",
            "публикац",
            "готовность тезиса",
            "подач",
            "используйте только повторную папку",
            "отдельно сохранённый sha-256 квитанции",
            "получатель заново проверяет точный пакет",
            "внешний sha-256 манифеста",
            "текущие последующие входы",
            "флаги различий",
            "каждый независимый барьер",
        ):
            self.assertIn(fragment, folded, fragment)
        for code, status in ((0, "match"), (3, "mismatch"), (2, "invalid")):
            self.assertRegex(folded, rf"{code}\s*(?:=|—|-)\s*{status}")
        self.assertIn("unreadable", folded)

    def test_parser_requires_all_five_exact_long_options(self) -> None:
        bundle = self.root / "source-bundle"
        uncertain = self.root / "uncertain-review-import"
        repeated = self.root / "repeated-review-import"
        complete = self.argv(bundle, uncertain, repeated)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                parsed = cli.build_parser().parse_args(complete)
        except SystemExit as raised:
            self.fail(
                "expected registered compare-review-imports route, "
                f"parser exited with {raised.code}"
            )
        self.assertTrue(callable(parsed.func))
        self.assertEqual(str(bundle), parsed.bundle)
        self.assertEqual(self.expected_manifest_sha256, parsed.expected_manifest_sha256)
        self.assertEqual(
            str(uncertain),
            parsed.uncertain_review_import_dir,
        )
        self.assertEqual(str(repeated), parsed.repeated_review_import_dir)
        self.assertEqual(
            self.expected_receipt_sha256,
            parsed.expected_import_receipt_sha256,
        )
        self.assertNotIn("output", vars(parsed))

        cases = [
            complete[:index] + complete[index + 2 :]
            for index in (3, 5, 7, 9, 11)
        ]
        for index, abbreviated in (
            (3, "--bund"),
            (5, "--expected-manifest-sha"),
            (7, "--uncertain-review-import-d"),
            (9, "--repeated-review-import-d"),
            (11, "--expected-import-receipt-sha"),
        ):
            abbreviated_argv = complete.copy()
            abbreviated_argv[index] = abbreviated
            cases.append(abbreviated_argv)
        cases.extend(
            (
                [
                    *complete[:7],
                    "--uncertain-review-import",
                    str(uncertain),
                    *complete[9:],
                ],
                [*complete, "--output", str(self.root / "report.json")],
                [*complete, str(self.root / "positional")],
            )
        )
        for argv in cases:
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as raised:
                with contextlib.redirect_stderr(io.StringIO()):
                    cli.build_parser().parse_args(argv)
            self.assertEqual(2, raised.exception.code)

    def test_abbreviated_options_exit_before_handler_reads_inputs(self) -> None:
        bundle = self.root / "must-not-open-bundle"
        uncertain = self.root / "must-not-open-uncertain"
        repeated = self.root / "must-not-open-repeated"
        complete = self.argv(bundle, uncertain, repeated)
        for index, abbreviated in (
            (3, "--bund"),
            (5, "--expected-manifest-sha"),
            (7, "--uncertain-review-import-d"),
            (9, "--repeated-review-import-d"),
            (11, "--expected-import-receipt-sha"),
        ):
            argv = complete.copy()
            argv[index] = abbreviated
            with self.subTest(option=abbreviated), mock.patch.object(
                cli.os,
                "open",
                side_effect=AssertionError("parser entered the comparison handler"),
            ):
                result = self.run_cli(argv)
            self.assertEqual(2, result[0])
            self.assertEqual("", result[1])
            self.assertNotEqual("", result[2])

    def test_mismatched_repeated_external_receipt_is_closed_mismatch(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs("receipt-mismatch")
        before = _tree_snapshot(parent)
        result = self.run_cli(
            self.argv(
                bundle,
                uncertain,
                repeated,
                receipt_sha256="0" * 64,
            )
        )
        self.assertEqual(3, result[0])
        report = self.assert_report(result)
        self.assertEqual("mismatch", report["status"])
        self.assertFalse(report["recovery_comparison_valid"])
        self.assertEqual(
            ["external_import_receipt_digest_mismatch"],
            report["reason_codes"],
        )
        self.assertTrue(report["checks"]["expected_import_receipt_sha256_valid"])
        self.assertFalse(report["checks"]["repeated_external_receipt_digest_valid"])
        self.assertTrue(report["checks"]["import_directory_file_bytes_equal"])
        self.assertTrue(report["checks"]["final_recapture_valid"])
        self.assertEqual(
            ["preserve_and_stop", "retain_successful_repeat_digest"],
            [entry["code"] for entry in report["remediation"]],
        )
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(
            result[1],
            str(parent),
            self.expected_manifest_sha256,
            self.expected_receipt_sha256,
            "0" * 64,
            self.private_candidate_id,
        )

    def test_digest_syntax_is_invalid_without_suppressing_safe_checks(self) -> None:
        cases = (
            (
                "manifest",
                {"manifest_sha256": "A" * 64},
                "expected_manifest_sha256_invalid",
                "expected_manifest_sha256_valid",
                "source_bundle_external_manifest_digest_valid",
                ["preserve_and_stop", "retain_successful_prepare_digest"],
            ),
            (
                "receipt",
                {"receipt_sha256": "A" * 64},
                "expected_import_receipt_sha256_invalid",
                "expected_import_receipt_sha256_valid",
                "repeated_external_receipt_digest_valid",
                ["preserve_and_stop", "retain_successful_repeat_digest"],
            ),
        )
        for label, overrides, reason, syntax_check, dependent_check, remediation in cases:
            with self.subTest(digest=label):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"invalid-{label}-digest"
                )
                before = _tree_snapshot(parent)
                result = self.run_cli(
                    self.argv(bundle, uncertain, repeated, **overrides)
                )
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                self.assertEqual([reason], report["reason_codes"])
                self.assertFalse(report["checks"][syntax_check])
                self.assertIsNone(report["checks"][dependent_check])
                self.assertTrue(report["checks"]["installed_codebook_readable"])
                self.assertTrue(report["checks"]["uncertain_inventory_exact"])
                self.assertTrue(report["checks"]["repeated_inventory_exact"])
                self.assertTrue(
                    report["checks"]["import_directory_file_bytes_equal"]
                )
                self.assertEqual(
                    remediation,
                    [entry["code"] for entry in report["remediation"]],
                )
                self.assertEqual(before, _tree_snapshot(parent))
                self.assert_value_free(
                    result[1],
                    str(parent),
                    "A" * 64,
                    self.expected_manifest_sha256,
                    self.expected_receipt_sha256,
                    self.private_candidate_id,
                )

    def test_uncertain_decision_extra_outer_field_is_contract_invalid(self) -> None:
        private_field = "unexpected_private_outer_field"
        private_value = "PRIVATE-EXTRA-OUTER-VALUE"

        def mutate(records: list[dict[str, object]]) -> None:
            records[0][private_field] = private_value

        self.assert_uncertain_decisions_contract_invalid(
            "uncertain-extra-outer-decision-field",
            mutate,
            private_field,
            private_value,
        )

    def test_uncertain_decision_missing_outer_field_is_contract_invalid(self) -> None:
        def mutate(records: list[dict[str, object]]) -> None:
            records[0].pop("secondary_coding_sha256")

        self.assert_uncertain_decisions_contract_invalid(
            "uncertain-missing-outer-decision-field",
            mutate,
            "secondary_coding_sha256",
        )

    def test_uncertain_decision_nested_secondary_contract_is_invalid(self) -> None:
        private_field = "unexpected_private_secondary_field"
        private_value = "PRIVATE-NESTED-SECONDARY-VALUE"

        def mutate(records: list[dict[str, object]]) -> None:
            secondary = records[0]["secondary_coding"]
            if not isinstance(secondary, dict):
                raise AssertionError("fixture secondary_coding is not an object")
            secondary[private_field] = private_value
            records[0]["secondary_coding_sha256"] = cli.canonical_digest(secondary)

        self.assert_uncertain_decisions_contract_invalid(
            "uncertain-invalid-nested-secondary-contract",
            mutate,
            private_field,
            private_value,
        )

    def test_uncertain_decision_candidate_population_is_contract_invalid(self) -> None:
        def mutate(records: list[dict[str, object]]) -> None:
            records.append(copy.deepcopy(records[0]))

        self.assert_uncertain_decisions_contract_invalid(
            "uncertain-duplicate-decision-candidate",
            mutate,
        )

    def test_identifier_contract_helpers_never_scan_list_membership(self) -> None:
        class MembershipScanForbiddenList(list):
            def __contains__(self, item: object) -> bool:
                raise AssertionError(
                    "identifier contract attempted a linear list membership scan"
                )

        candidate_ids = [
            f"audit-candidate-sha256:{index:064x}" for index in range(1, 513)
        ]
        selected_ids = candidate_ids[::7]
        self.assertTrue(
            cli._native_review_import_ordered_identifier_subset(
                MembershipScanForbiddenList(selected_ids),
                MembershipScanForbiddenList(candidate_ids),
            )
        )

        allowed_fields = tuple(cli.AUDITED_CODING_FIELDS)
        expected_candidate_ids = candidate_ids[::11]
        ordinary_differences = [
            {"candidate_id": candidate_id, "fields": [allowed_fields[0]]}
            for candidate_id in expected_candidate_ids
        ]
        with self.subTest(contract_membership="candidate_ids"):
            self.assertTrue(
                cli._native_review_import_difference_list_contract_valid(
                    ordinary_differences,
                    candidate_ids=MembershipScanForbiddenList(candidate_ids),
                    expected_candidate_ids=expected_candidate_ids,
                    allowed_fields=allowed_fields,
                )
            )

        guarded_field_differences = [
            {
                "candidate_id": candidate_id,
                "fields": MembershipScanForbiddenList([allowed_fields[0]]),
            }
            for candidate_id in expected_candidate_ids
        ]
        with self.subTest(contract_membership="fields"):
            self.assertTrue(
                cli._native_review_import_difference_list_contract_valid(
                    guarded_field_differences,
                    candidate_ids=candidate_ids,
                    expected_candidate_ids=expected_candidate_ids,
                    allowed_fields=allowed_fields,
                )
            )

    def test_high_risk_topology_inventory_and_privacy_cases_are_invalid(self) -> None:
        cases: list[
            tuple[
                str,
                Path,
                Path,
                Path,
                Path,
                list[str],
                tuple[str, ...],
            ]
        ] = []

        parent, bundle, uncertain, _ = self.fresh_inputs("cross-parent")
        other_parent = self.root / "other-safe-parent"
        other_parent.mkdir(mode=0o700)
        cross_parent_repeated = other_parent / "repeated-review-import"
        shutil.copytree(
            self.repeated_fixture,
            cross_parent_repeated,
            copy_function=shutil.copy2,
        )
        cases.append(
            (
                "cross-parent",
                self.root,
                bundle,
                uncertain,
                cross_parent_repeated,
                ["comparison_topology_invalid"],
                ("common_parent_valid",),
            )
        )

        parent, bundle, uncertain, _ = self.fresh_inputs("directory-alias")
        cases.append(
            (
                "directory-alias",
                parent,
                bundle,
                uncertain,
                uncertain,
                ["comparison_topology_invalid"],
                ("directories_distinct",),
            )
        )

        parent, bundle, uncertain, repeated = self.fresh_inputs("extra-entry")
        extra = uncertain / "private-unexpected-entry"
        extra.write_bytes(b"private extra value\n")
        extra.chmod(0o600)
        cases.append(
            (
                "extra-entry",
                parent,
                bundle,
                uncertain,
                repeated,
                ["uncertain_review_import_inventory_invalid"],
                ("uncertain_inventory_exact",),
            )
        )

        parent, bundle, uncertain, repeated = self.fresh_inputs("cross-input-hardlink")
        repeated_decisions = repeated / "audit-decisions.jsonl"
        repeated_decisions.unlink()
        os.link(uncertain / "audit-decisions.jsonl", repeated_decisions)
        cases.append(
            (
                "cross-input-hardlink",
                parent,
                bundle,
                uncertain,
                repeated,
                [
                    "uncertain_review_import_privacy_invalid",
                    "repeated_review_import_privacy_invalid",
                ],
                ("uncertain_directory_private", "repeated_directory_private"),
            )
        )

        parent, bundle, uncertain, repeated = self.fresh_inputs("unsafe-file-mode")
        (repeated / "audit-decisions.jsonl").chmod(0o640)
        cases.append(
            (
                "unsafe-file-mode",
                parent,
                bundle,
                uncertain,
                repeated,
                ["repeated_review_import_privacy_invalid"],
                ("repeated_directory_private",),
            )
        )

        for label, snapshot_root, bundle, uncertain, repeated, reasons, false_checks in cases:
            with self.subTest(case=label):
                before = _tree_snapshot(snapshot_root)
                result = self.run_cli(self.argv(bundle, uncertain, repeated))
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                self.assertEqual(reasons, report["reason_codes"])
                for check in false_checks:
                    self.assertFalse(report["checks"][check], check)
                remediation_codes = [
                    entry["code"] for entry in report["remediation"]
                ]
                self.assertIn("preserve_and_stop", remediation_codes)
                self.assertIn("use_safe_complete_siblings", remediation_codes)
                self.assertIn("administrator_quarantine", remediation_codes)
                self.assertNotIn("repeat_import_after_mismatch", remediation_codes)
                self.assertEqual(before, _tree_snapshot(snapshot_root))
                self.assert_value_free(
                    result[1],
                    str(snapshot_root),
                    "private-unexpected-entry",
                    "private extra value",
                    self.expected_manifest_sha256,
                    self.expected_receipt_sha256,
                    self.private_candidate_id,
                )

    def test_unavailable_invalid_observation_fails_closed_as_input_changed(self) -> None:
        cases = (
            (
                "closed-unreadable",
                cli._FinalizationComparisonCaptureError("unreadable"),
                None,
            ),
            (
                "memory",
                MemoryError("private invalid-observer memory marker"),
                "private invalid-observer memory marker",
            ),
            (
                "recursion",
                RecursionError("private invalid-observer recursion marker"),
                "private invalid-observer recursion marker",
            ),
        )
        for label, failure, private_marker in cases:
            with self.subTest(failure=label):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"invalid-observation-unavailable-{label}"
                )
                extra = uncertain / "private-unexpected-entry"
                extra.write_bytes(b"private extra value\n")
                extra.chmod(0o600)
                before = _tree_snapshot(parent)

                with mock.patch.object(
                    cli,
                    "_capture_comparison_invalid_observation",
                    side_effect=failure,
                ):
                    result = self.run_cli(self.argv(bundle, uncertain, repeated))

                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertEqual(
                    [
                        "comparison_input_changed",
                        "uncertain_review_import_inventory_invalid",
                    ],
                    report["reason_codes"],
                )
                self.assertFalse(report["checks"]["uncertain_inventory_exact"])
                self.assertFalse(report["checks"]["final_recapture_valid"])
                self.assertEqual(before, _tree_snapshot(parent))
                self.assert_value_free(
                    result[1],
                    str(parent),
                    "private-unexpected-entry",
                    "private extra value",
                    *(private_marker,) if private_marker is not None else (),
                    self.private_candidate_id,
                )

    def test_initial_capture_resource_failure_is_value_free_unreadable(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs(
            "initial-capture-resource-failure"
        )
        before = _tree_snapshot(parent)
        private_marker = "PRIVATE-MEMORY-MARKER"
        real_capture = cli._capture_private_comparison_descriptor

        def capture_with_one_resource_failure(
            descriptor: int,
            *,
            profile: object,
            expected_initial_identity: object = None,
            invalid_observer: object = None,
        ) -> dict[str, object]:
            if profile is cli._AUDIT_BUNDLE_COMPARISON_PROFILE:
                raise MemoryError(private_marker)
            return real_capture(
                descriptor,
                profile=profile,
                expected_initial_identity=expected_initial_identity,
                invalid_observer=invalid_observer,
            )

        with mock.patch.object(
            cli,
            "_capture_private_comparison_descriptor",
            side_effect=capture_with_one_resource_failure,
        ):
            result = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertEqual(["source_bundle_unreadable"], report["reason_codes"])
        self.assertFalse(report["checks"]["source_bundle_readable"])
        self.assertTrue(report["checks"]["uncertain_inventory_exact"])
        self.assertTrue(report["checks"]["repeated_inventory_exact"])
        self.assertTrue(report["checks"]["uncertain_artifact_contracts_valid"])
        self.assertTrue(report["checks"]["repeated_artifact_contracts_valid"])
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(result[1], private_marker, str(parent))

    def test_source_bundle_import_contract_memory_error_is_role_local(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs(
            "source-import-contract-memory-error"
        )
        before = _tree_snapshot(parent)
        private_marker = "PRIVATE-SOURCE-IMPORT-CONTRACT-MEMORY-MARKER"

        with mock.patch.object(
            cli,
            "_native_coding_audit_bundle_import_contract_valid",
            side_effect=MemoryError(private_marker),
        ):
            result = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["recovery_comparison_valid"])
        self.assertEqual(["source_bundle_unreadable"], report["reason_codes"])
        self.assertNotIn("comparison_input_changed", report["reason_codes"])
        self.assertFalse(report["checks"]["source_bundle_readable"])
        for independent_check in (
            "common_parent_valid",
            "expected_manifest_sha256_valid",
            "uncertain_directory_readable",
            "repeated_directory_readable",
            "uncertain_directory_private",
            "repeated_directory_private",
            "uncertain_inventory_exact",
            "repeated_inventory_exact",
            "expected_import_receipt_sha256_valid",
            "uncertain_artifact_contracts_valid",
            "repeated_artifact_contracts_valid",
            "uncertain_receipt_self_digest_valid",
            "repeated_receipt_self_digest_valid",
            "repeated_external_receipt_digest_valid",
            "uncertain_receipt_file_binding_valid",
            "repeated_receipt_file_binding_valid",
        ):
            self.assertTrue(report["checks"][independent_check], independent_check)
        for dependent_check in (
            "directories_distinct",
            "source_bundle_private",
            "source_bundle_inventory_exact",
            "source_bundle_contract_valid",
            "source_bundle_external_manifest_digest_valid",
            "installed_codebook_readable",
            "installed_codebook_binding_valid",
            "uncertain_bundle_relation_valid",
            "repeated_bundle_relation_valid",
            "import_directory_file_bytes_equal",
            "final_recapture_valid",
        ):
            self.assertIsNone(report["checks"][dependent_check], dependent_check)
        self.assertEqual(
            ["check_local_read_access"],
            [entry["code"] for entry in report["remediation"]],
        )
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(
            result[1],
            private_marker,
            str(parent),
            str(bundle),
            str(uncertain),
            str(repeated),
            self.expected_manifest_sha256,
            self.expected_receipt_sha256,
            self.private_candidate_id,
        )

    def test_raw_comparison_resource_failure_keeps_input_changed_report(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs(
            "raw-comparison-resource-failure"
        )
        before = _tree_snapshot(parent)
        private_marker = "PRIVATE-RAW-COMPARISON-MEMORY-MARKER"

        with mock.patch.object(
            cli,
            "_comparison_directory_bytes_equal",
            side_effect=MemoryError(private_marker),
        ):
            result = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertEqual(["comparison_input_changed"], report["reason_codes"])
        self.assertIsNone(
            report["checks"]["import_directory_file_bytes_equal"]
        )
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertTrue(report["checks"]["source_bundle_contract_valid"])
        self.assertTrue(report["checks"]["uncertain_bundle_relation_valid"])
        self.assertTrue(report["checks"]["repeated_bundle_relation_valid"])
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(result[1], private_marker, str(parent))

    def test_unavailable_installed_codebook_has_distinct_unreadable_reason(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs("missing-codebook")
        before = _tree_snapshot(parent)
        missing_codebook = self.root / "private-missing-codebook-value"
        with mock.patch.dict(
            cli._AUDIT_CODEBOOK_PATHS,
            {"1.0": str(missing_codebook)},
            clear=True,
        ):
            result = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertFalse(report["recovery_comparison_valid"])
        self.assertEqual(["installed_codebook_unreadable"], report["reason_codes"])
        self.assertFalse(report["checks"]["installed_codebook_readable"])
        self.assertIsNone(report["checks"]["installed_codebook_binding_valid"])
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(
            result[1],
            str(parent),
            str(missing_codebook),
            self.expected_manifest_sha256,
            self.expected_receipt_sha256,
            self.private_candidate_id,
        )

    def test_codebook_change_during_final_recapture_is_unreadable(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs("codebook-drift")
        before = {
            "parent": _tree_snapshot(parent),
            "codebook": _file_snapshot(SOURCE_CODEBOOK),
        }
        real_capture = cli._secure_codebook_capture
        captured: list[dict[str, object]] = []

        def capture_then_change(codebook_version: str) -> dict[str, object]:
            result = real_capture(codebook_version)
            captured.append(result)
            if len(captured) == 1:
                return result
            return {**result, "content": result["content"] + b"\n"}

        with mock.patch.object(
            cli,
            "_secure_codebook_capture",
            side_effect=capture_then_change,
        ):
            result = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertGreaterEqual(len(captured), 2)
        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("unreadable", report["status"])
        self.assertEqual(["comparison_input_changed"], report["reason_codes"])
        self.assertTrue(report["checks"]["installed_codebook_readable"])
        self.assertTrue(report["checks"]["installed_codebook_binding_valid"])
        self.assertFalse(report["checks"]["final_recapture_valid"])
        self.assertEqual(
            ["preserve_and_stop", "administrator_quarantine"],
            [entry["code"] for entry in report["remediation"]],
        )
        self.assertNotIn(
            "repeat_import_after_mismatch",
            [entry["code"] for entry in report["remediation"]],
        )
        self.assertEqual(before["parent"], _tree_snapshot(parent))
        self.assertEqual(before["codebook"], _file_snapshot(SOURCE_CODEBOOK))

    def test_invalid_import_outweighs_independent_external_anchor_mismatch(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs(
            "invalid-and-anchor-mismatch"
        )
        extra = uncertain / "private-invalid-import-entry"
        extra.write_bytes(b"private invalid import value\n")
        extra.chmod(0o600)
        before = _tree_snapshot(parent)
        result = self.run_cli(
            self.argv(
                bundle,
                uncertain,
                repeated,
                manifest_sha256="0" * 64,
            )
        )

        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertEqual(
            [
                "uncertain_review_import_inventory_invalid",
                "external_manifest_digest_mismatch",
            ],
            report["reason_codes"],
        )
        self.assertFalse(report["checks"]["uncertain_inventory_exact"])
        self.assertFalse(
            report["checks"]["source_bundle_external_manifest_digest_valid"]
        )
        self.assertTrue(report["checks"]["repeated_inventory_exact"])
        self.assertTrue(report["checks"]["repeated_artifact_contracts_valid"])
        self.assertTrue(report["checks"]["repeated_external_receipt_digest_valid"])
        remediation_codes = [entry["code"] for entry in report["remediation"]]
        self.assertIn("administrator_quarantine", remediation_codes)
        self.assertIn("retain_successful_prepare_digest", remediation_codes)
        self.assertNotIn("repeat_import_after_mismatch", remediation_codes)
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(
            result[1],
            str(parent),
            "private-invalid-import-entry",
            "private invalid import value",
            "0" * 64,
            self.expected_receipt_sha256,
            self.private_candidate_id,
        )

    def test_stdout_interruption_returns_two_without_promised_report(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs("stdout-interruption")
        before = _tree_snapshot(parent)
        with mock.patch.object(
            cli,
            "_write_stdout_bytes",
            side_effect=BrokenPipeError("private stdout interruption"),
        ):
            result = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertEqual(2, result[0])
        self.assertEqual("", result[1])
        self.assertIn("Ошибка:", result[2])
        self.assertEqual(before, _tree_snapshot(parent))

    def test_two_valid_bundle_bound_imports_with_raw_difference_are_mismatch(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs(
            "raw-mismatch",
            repeated_fixture=self.different_fixture,
        )
        before = _tree_snapshot(parent)
        result = self.run_cli(
            self.argv(
                bundle,
                uncertain,
                repeated,
                receipt_sha256=self.different_receipt_sha256,
            )
        )
        self.assertEqual(3, result[0])
        report = self.assert_report(result)
        self.assertEqual("mismatch", report["status"])
        self.assertEqual(
            ["review_import_directory_bytes_mismatch"],
            report["reason_codes"],
        )
        for check in (
            "source_bundle_external_manifest_digest_valid",
            "uncertain_artifact_contracts_valid",
            "repeated_artifact_contracts_valid",
            "uncertain_receipt_self_digest_valid",
            "repeated_receipt_self_digest_valid",
            "repeated_external_receipt_digest_valid",
            "uncertain_receipt_file_binding_valid",
            "repeated_receipt_file_binding_valid",
            "uncertain_bundle_relation_valid",
            "repeated_bundle_relation_valid",
            "final_recapture_valid",
        ):
            self.assertTrue(report["checks"][check], check)
        self.assertFalse(report["checks"]["import_directory_file_bytes_equal"])
        self.assertEqual(
            ["preserve_and_stop", "repeat_import_after_mismatch"],
            [entry["code"] for entry in report["remediation"]],
        )
        self.assertEqual(before, _tree_snapshot(parent))
        self.assert_value_free(
            result[1],
            str(parent),
            self.expected_manifest_sha256,
            self.expected_receipt_sha256,
            self.different_receipt_sha256,
            self.private_candidate_id,
            "Независимая формулировка того же вывода.",
        )

    def test_each_input_role_same_inode_rewrite_after_first_compare_is_closed(self) -> None:
        targets = (
            ("source_bundle", "coding-audit-plan.json"),
            ("uncertain", "audit-decisions.jsonl"),
            ("repeated", "coding-audit-review-import-receipt.json"),
        )
        for role, filename in targets:
            with self.subTest(role=role):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"same-inode-rewrite-{role}"
                )
                role_paths = {
                    "source_bundle": bundle,
                    "uncertain": uncertain,
                    "repeated": repeated,
                }
                target = role_paths[role] / filename
                original_stat = target.stat()
                real_compare = cli._comparison_directory_bytes_equal
                rewritten = False

                def compare_then_rewrite(*args: object, **kwargs: object) -> bool:
                    nonlocal rewritten
                    result = real_compare(*args, **kwargs)
                    if not rewritten:
                        content = target.read_bytes()
                        with target.open("r+b") as stream:
                            stream.seek(0)
                            stream.write(content)
                            stream.truncate()
                            stream.flush()
                        os.utime(
                            target,
                            ns=(
                                original_stat.st_atime_ns,
                                original_stat.st_mtime_ns + 1_000_000_000,
                            ),
                            follow_symlinks=False,
                        )
                        self.assertEqual(original_stat.st_ino, target.stat().st_ino)
                        rewritten = True
                    return result

                with mock.patch.object(
                    cli,
                    "_comparison_directory_bytes_equal",
                    side_effect=compare_then_rewrite,
                ):
                    result = self.run_cli(self.argv(bundle, uncertain, repeated))

                self.assertTrue(rewritten)
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(report["checks"]["final_recapture_valid"])
                self.assertIn("comparison_input_changed", report["reason_codes"])
                self.assert_value_free(result[1], str(target), filename)

    def test_each_child_and_parent_name_rebinding_is_closed(self) -> None:
        for role in ("source_bundle", "uncertain", "repeated", "parent"):
            with self.subTest(role=role):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"name-rebinding-{role}"
                )
                role_paths = {
                    "source_bundle": bundle,
                    "uncertain": uncertain,
                    "repeated": repeated,
                }
                target = parent if role == "parent" else role_paths[role]
                retained = target.with_name(f"{target.name}-retained-private")
                real_compare = cli._comparison_directory_bytes_equal
                rebound = False

                def compare_then_rebind(*args: object, **kwargs: object) -> bool:
                    nonlocal rebound
                    result = real_compare(*args, **kwargs)
                    if not rebound:
                        target.rename(retained)
                        if role == "parent":
                            target.mkdir(mode=0o700)
                        else:
                            shutil.copytree(
                                retained,
                                target,
                                copy_function=shutil.copy2,
                            )
                        rebound = True
                    return result

                try:
                    with mock.patch.object(
                        cli,
                        "_comparison_directory_bytes_equal",
                        side_effect=compare_then_rebind,
                    ):
                        result = self.run_cli(self.argv(bundle, uncertain, repeated))
                finally:
                    if role == "parent" and retained.exists():
                        if target.exists():
                            shutil.rmtree(target)
                        retained.rename(target)

                self.assertTrue(rebound)
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(report["checks"]["final_recapture_valid"])
                self.assertIn("comparison_input_changed", report["reason_codes"])
                self.assert_value_free(result[1], str(target), str(retained))

    def test_close_uncertainty_for_every_held_directory_is_closed(self) -> None:
        for role in ("source_bundle", "uncertain", "repeated", "parent"):
            with self.subTest(role=role):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"close-uncertainty-{role}"
                )
                role_paths = {
                    "source_bundle": bundle,
                    "uncertain": uncertain,
                    "repeated": repeated,
                    "parent": parent,
                }
                target_stat = role_paths[role].stat()
                target_identity = (target_stat.st_dev, target_stat.st_ino)
                real_close = cli._close_finalization_comparison_descriptor
                injected = False

                def close_then_fail(descriptor: int) -> None:
                    nonlocal injected
                    try:
                        descriptor_stat = cli.os.fstat(descriptor)
                        identity = (descriptor_stat.st_dev, descriptor_stat.st_ino)
                    except OSError:
                        identity = None
                    real_close(descriptor)
                    if identity == target_identity and not injected:
                        injected = True
                        raise cli._FinalizationComparisonCaptureError("changed")

                with mock.patch.object(
                    cli,
                    "_close_finalization_comparison_descriptor",
                    side_effect=close_then_fail,
                ):
                    result = self.run_cli(self.argv(bundle, uncertain, repeated))

                self.assertTrue(injected)
                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(report["checks"]["final_recapture_valid"])
                self.assertIn("comparison_input_changed", report["reason_codes"])

    def test_all_eleven_leaf_slots_reject_cross_role_inode_aliases(self) -> None:
        bundle_names = tuple(cli._AUDIT_BUNDLE_COMPARISON_PROFILE["paths"])
        import_names = tuple(cli._REVIEW_IMPORT_COMPARISON_PROFILE["paths"])
        slots = (
            *(("source_bundle", name) for name in bundle_names),
            *(("uncertain", name) for name in import_names),
            *(("repeated", name) for name in import_names),
        )
        self.assertEqual(11, len(slots))

        for index, (role, filename) in enumerate(slots):
            with self.subTest(role=role, filename=filename):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"inode-alias-{index}"
                )
                role_paths = {
                    "source_bundle": bundle,
                    "uncertain": uncertain,
                    "repeated": repeated,
                }
                if role == "source_bundle":
                    anchor_role = "uncertain"
                    anchor = uncertain / import_names[0]
                elif role == "uncertain":
                    anchor_role = "repeated"
                    anchor = repeated / import_names[0]
                else:
                    anchor_role = "source_bundle"
                    anchor = bundle / bundle_names[0]
                target = role_paths[role] / filename
                target.unlink()
                os.link(anchor, target)

                result = self.run_cli(self.argv(bundle, uncertain, repeated))

                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                for implicated_role in (role, anchor_role):
                    check = (
                        "source_bundle_private"
                        if implicated_role == "source_bundle"
                        else f"{implicated_role}_directory_private"
                    )
                    self.assertFalse(report["checks"][check], check)
                self.assertNotIn("comparison_input_changed", report["reason_codes"])
                self.assert_value_free(result[1], filename, str(target), str(anchor))

    def test_each_directory_rejects_synthetic_cross_filesystem_identity(self) -> None:
        for role in ("source_bundle", "uncertain", "repeated"):
            with self.subTest(role=role):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"cross-filesystem-{role}"
                )
                role_paths = {
                    "source_bundle": bundle,
                    "uncertain": uncertain,
                    "repeated": repeated,
                }
                target_inode = role_paths[role].stat().st_ino
                real_identity = cli._stable_finalization_directory_identity

                def mounted_identity(value: os.stat_result) -> tuple[int, ...]:
                    identity = list(real_identity(value))
                    if value.st_ino == target_inode:
                        identity[0] += 1
                    return tuple(identity)

                with mock.patch.object(
                    cli,
                    "_stable_finalization_directory_identity",
                    side_effect=mounted_identity,
                ):
                    result = self.run_cli(self.argv(bundle, uncertain, repeated))

                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                self.assertFalse(report["checks"]["common_parent_valid"])
                self.assertIsNone(report["checks"]["directories_distinct"])
                self.assertIn("comparison_topology_invalid", report["reason_codes"])

    def test_all_seven_two_two_file_bounds_fail_before_materialization(self) -> None:
        bundle_limits = cli._AUDIT_BUNDLE_COMPARISON_PROFILE["file_limits"]
        import_limits = cli._REVIEW_IMPORT_COMPARISON_PROFILE["file_limits"]
        cases = (
            *(("source_bundle", name, limit) for name, limit in bundle_limits.items()),
            *(("uncertain", name, limit) for name, limit in import_limits.items()),
            *(("repeated", name, limit) for name, limit in import_limits.items()),
        )
        self.assertEqual(11, len(cases))

        for index, (role, filename, byte_limit) in enumerate(cases):
            with self.subTest(role=role, filename=filename):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"file-bound-{index}"
                )
                role_paths = {
                    "source_bundle": bundle,
                    "uncertain": uncertain,
                    "repeated": repeated,
                }
                target = role_paths[role] / filename
                with target.open("r+b") as stream:
                    stream.truncate(int(byte_limit) + 1)

                result = self.run_cli(self.argv(bundle, uncertain, repeated))

                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                readable_check = (
                    "source_bundle_readable"
                    if role == "source_bundle"
                    else f"{role}_directory_readable"
                )
                self.assertFalse(report["checks"][readable_check])
                self.assert_value_free(result[1], filename, str(target))

    def test_bundle_and_import_enumeration_stop_at_first_excess_entry(self) -> None:
        for role, expected_count in (("source_bundle", 7), ("uncertain", 2)):
            with self.subTest(role=role):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"bounded-enumeration-{role}"
                )
                target = bundle if role == "source_bundle" else uncertain
                target_identity = (target.stat().st_dev, target.stat().st_ino)
                for index in range(16):
                    extra = target / f"private-extra-{index:02d}"
                    extra.write_bytes(b"private extra value\n")
                    extra.chmod(0o600)

                real_scandir = cli.os.scandir
                scan_counts: list[int] = []

                class GuardedScandir:
                    def __init__(self, raw: object) -> None:
                        self.raw = raw
                        self.iterator: object | None = None
                        self.count = 0

                    def __enter__(self) -> "GuardedScandir":
                        entered = self.raw.__enter__()
                        self.iterator = iter(entered)
                        return self

                    def __exit__(self, *args: object) -> object:
                        scan_counts.append(self.count)
                        return self.raw.__exit__(*args)

                    def __iter__(self) -> "GuardedScandir":
                        return self

                    def __next__(self) -> object:
                        if self.count >= expected_count + 1:
                            raise AssertionError(
                                "comparison enumerated beyond first excess entry"
                            )
                        if self.iterator is None:
                            raise AssertionError("scandir iterator was not entered")
                        item = next(self.iterator)
                        self.count += 1
                        return item

                def bounded_scandir(path: object) -> object:
                    raw = real_scandir(path)
                    if isinstance(path, int):
                        descriptor_stat = cli.os.fstat(path)
                        if (
                            descriptor_stat.st_dev,
                            descriptor_stat.st_ino,
                        ) == target_identity:
                            return GuardedScandir(raw)
                    return raw

                with mock.patch.object(
                    cli.os,
                    "scandir",
                    side_effect=bounded_scandir,
                ):
                    result = self.run_cli(self.argv(bundle, uncertain, repeated))

                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                inventory_check = (
                    "source_bundle_inventory_exact"
                    if role == "source_bundle"
                    else "uncertain_inventory_exact"
                )
                self.assertFalse(report["checks"][inventory_check])
                self.assertTrue(scan_counts)
                self.assertEqual(expected_count + 1, max(scan_counts))

    def test_json_resource_limits_are_value_free_unreadable_for_all_roles(self) -> None:
        depth = cli._AUDIT_IMPORT_MAX_JSON_DEPTH + 2
        private_marker = "private-comparator-resource-marker"
        deep_json = (
            b"[" * depth
            + json.dumps(private_marker).encode("utf-8")
            + b"]" * depth
            + b"\n"
        )
        cases = (
            (
                "source_bundle",
                "coding-audit-inputs-manifest.json",
                "source_bundle_readable",
                "source_bundle_unreadable",
            ),
            (
                "uncertain",
                "audit-decisions.jsonl",
                "uncertain_directory_readable",
                "uncertain_review_import_unreadable",
            ),
            (
                "repeated",
                "coding-audit-review-import-receipt.json",
                "repeated_directory_readable",
                "repeated_review_import_unreadable",
            ),
        )
        for role, filename, readable_check, reason in cases:
            with self.subTest(role=role):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"json-resource-{role}"
                )
                role_paths = {
                    "source_bundle": bundle,
                    "uncertain": uncertain,
                    "repeated": repeated,
                }
                target = role_paths[role] / filename
                target.write_bytes(deep_json)
                before = _tree_snapshot(parent)

                result = self.run_cli(self.argv(bundle, uncertain, repeated))

                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(report["checks"][readable_check])
                self.assertIn(reason, report["reason_codes"])
                self.assert_value_free(
                    result[1],
                    private_marker,
                    self.private_candidate_id,
                    filename,
                    str(target),
                )
                self.assertEqual(before, _tree_snapshot(parent))

        def with_declared_central_directory_size(content: bytes) -> bytes:
            rewritten = bytearray(content)
            self.assertEqual(b"PK\x05\x06", rewritten[-22:-18])
            struct.pack_into(
                "<L",
                rewritten,
                len(rewritten) - 22 + 12,
                cli._AUDIT_IMPORT_ZIP_CENTRAL_DIRECTORY_LIMIT + 1,
            )
            return bytes(rewritten)

        def with_declared_entry_count(content: bytes, count: int) -> bytes:
            rewritten = bytearray(content)
            self.assertEqual(b"PK\x05\x06", rewritten[-22:-18])
            struct.pack_into("<H", rewritten, len(rewritten) - 22 + 8, count)
            struct.pack_into("<H", rewritten, len(rewritten) - 22 + 10, count)
            return bytes(rewritten)

        def with_declared_member_sizes(
            content: bytes,
            declared_sizes: tuple[int, ...],
        ) -> bytes:
            rewritten = bytearray(content)
            self.assertEqual(b"PK\x05\x06", rewritten[-22:-18])
            central_directory_offset = struct.unpack_from(
                "<L", rewritten, len(rewritten) - 22 + 16
            )[0]
            offset = central_directory_offset
            for declared_size in declared_sizes:
                self.assertEqual(b"PK\x01\x02", rewritten[offset : offset + 4])
                struct.pack_into("<L", rewritten, offset + 20, declared_size)
                struct.pack_into("<L", rewritten, offset + 24, declared_size)
                filename_size, extra_size, comment_size = struct.unpack_from(
                    "<3H", rewritten, offset + 28
                )
                offset += 46 + filename_size + extra_size + comment_size
            return bytes(rewritten)

        source_bundle_cases = (
            (
                "deep-plan-json",
                "coding-audit-plan.json",
                lambda original: deep_json,
            ),
            (
                "leaf-depth-boundary",
                "coding-audit-plan.json",
                lambda original: (
                    b"[" * cli._AUDIT_IMPORT_MAX_JSON_DEPTH
                    + b"0"
                    + b"]" * cli._AUDIT_IMPORT_MAX_JSON_DEPTH
                    + b"\n"
                ),
            ),
            (
                "deep-outer-jsonl",
                "screening-candidates.audit.jsonl",
                lambda original: deep_json,
            ),
            (
                "zip-central-directory-declared-limit",
                "independent-review-packet.zip",
                with_declared_central_directory_size,
            ),
            (
                "zip-member-declared-limit",
                "independent-review-packet.zip",
                lambda original: with_declared_member_sizes(
                    original,
                    (cli._AUDIT_IMPORT_ZIP_MEMBER_LIMIT + 1,),
                ),
            ),
            (
                "zip-total-declared-limit",
                "independent-review-packet.zip",
                lambda original: with_declared_member_sizes(
                    original,
                    (
                        cli._AUDIT_IMPORT_ZIP_TOTAL_LIMIT // 2 + 1,
                        cli._AUDIT_IMPORT_ZIP_TOTAL_LIMIT // 2 + 1,
                    ),
                ),
            ),
            (
                "zip-deep-json-member",
                "independent-review-packet.zip",
                lambda original: self._zip_with_replaced_member(
                    original,
                    "CODING-BRIEF.json",
                    deep_json,
                ),
            ),
        )
        for label, filename, rewrite in source_bundle_cases:
            with self.subTest(source_bundle_resource=label):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"json-resource-source-{label}"
                )
                target = bundle / filename
                rewritten = rewrite(target.read_bytes())
                manifest_sha256 = self.replace_bundle_file_and_refresh_manifest(
                    bundle,
                    filename,
                    rewritten,
                )
                before = _tree_snapshot(parent)

                result = self.run_cli(
                    self.argv(
                        bundle,
                        uncertain,
                        repeated,
                        manifest_sha256=manifest_sha256,
                    )
                )

                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("unreadable", report["status"])
                self.assertFalse(report["checks"]["source_bundle_readable"])
                self.assertIn("source_bundle_unreadable", report["reason_codes"])
                self.assert_value_free(
                    result[1],
                    private_marker,
                    self.private_candidate_id,
                    label,
                    filename,
                    str(target),
                    manifest_sha256,
                )
                self.assertEqual(before, _tree_snapshot(parent))

        with self.subTest(source_bundle_resource="zip-structural-control"):
            parent, bundle, uncertain, repeated = self.fresh_inputs(
                "json-resource-source-zip-structural-control"
            )
            filename = "independent-review-packet.zip"
            target = bundle / filename
            rewritten = with_declared_entry_count(target.read_bytes(), 5)
            manifest_sha256 = self.replace_bundle_file_and_refresh_manifest(
                bundle,
                filename,
                rewritten,
            )
            before = _tree_snapshot(parent)

            result = self.run_cli(
                self.argv(
                    bundle,
                    uncertain,
                    repeated,
                    manifest_sha256=manifest_sha256,
                )
            )

            self.assertEqual(2, result[0])
            report = self.assert_report(result)
            self.assertEqual("invalid", report["status"])
            self.assertTrue(report["checks"]["source_bundle_readable"])
            self.assertFalse(report["checks"]["source_bundle_contract_valid"])
            self.assertIn(
                "source_bundle_artifact_contract_invalid",
                report["reason_codes"],
            )
            self.assertNotIn("source_bundle_unreadable", report["reason_codes"])
            self.assert_value_free(
                result[1],
                self.private_candidate_id,
                "zip-structural-control",
                filename,
                str(target),
                manifest_sha256,
            )
            self.assertEqual(before, _tree_snapshot(parent))

        get_integer_limit = getattr(sys, "get_int_max_str_digits", None)
        set_integer_limit = getattr(sys, "set_int_max_str_digits", None)
        if callable(get_integer_limit) and callable(set_integer_limit):
            parent, bundle, uncertain, repeated = self.fresh_inputs(
                "json-resource-active-integer-limit"
            )
            filename = "coding-audit-plan.json"
            oversized_integer = b"1" * 641 + b"\n"
            manifest_sha256 = self.replace_bundle_file_and_refresh_manifest(
                bundle,
                filename,
                oversized_integer,
            )
            before = _tree_snapshot(parent)
            original_integer_limit = get_integer_limit()
            try:
                set_integer_limit(640)
                result = self.run_cli(
                    self.argv(
                        bundle,
                        uncertain,
                        repeated,
                        manifest_sha256=manifest_sha256,
                    )
                )
            finally:
                set_integer_limit(original_integer_limit)

            self.assertEqual(2, result[0])
            report = self.assert_report(result)
            self.assertEqual("unreadable", report["status"])
            self.assertFalse(report["checks"]["source_bundle_readable"])
            self.assertIn("source_bundle_unreadable", report["reason_codes"])
            self.assert_value_free(
                result[1],
                "1" * 128,
                self.private_candidate_id,
                filename,
                str(bundle / filename),
                manifest_sha256,
            )
            self.assertEqual(before, _tree_snapshot(parent))

    @staticmethod
    def _zip_with_replaced_member(
        content: bytes,
        filename: str,
        replacement: bytes,
    ) -> bytes:
        with zipfile.ZipFile(io.BytesIO(content), mode="r") as archive:
            members = {
                member: archive.read(member)
                for member in cli._BLINDED_REVIEW_PACKET_PATHS
            }
        members[filename] = replacement
        return cli._deterministic_flat_zip(members)

    def test_jsonl_unicode_blank_lines_do_not_become_resource_failure(self) -> None:
        unicode_blank_lines = ("\u00a0\n" * 10_001).encode("utf-8")
        cli._preflight_comparison_jsonl_resources(unicode_blank_lines)

        parent, bundle, uncertain, repeated = self.fresh_inputs(
            "jsonl-unicode-blank-lines"
        )
        target = uncertain / "audit-decisions.jsonl"
        target.write_bytes(unicode_blank_lines)
        before = _tree_snapshot(parent)

        result = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertTrue(report["checks"]["uncertain_directory_readable"])
        self.assertFalse(report["checks"]["uncertain_artifact_contracts_valid"])
        self.assertIn(
            "uncertain_review_import_artifact_contract_invalid",
            report["reason_codes"],
        )
        self.assertNotIn(
            "uncertain_review_import_unreadable",
            report["reason_codes"],
        )
        self.assert_value_free(
            result[1],
            "\u00a0",
            self.private_candidate_id,
            str(target),
        )
        self.assertEqual(before, _tree_snapshot(parent))

    def test_invalid_utf8_after_excess_json_nodes_remains_contract_invalid(self) -> None:
        invalid_utf8_after_excess_nodes = (
            b"["
            + b"0," * (cli._AUDIT_IMPORT_MAX_JSON_NODES + 1)
            + b"\xff]"
        )
        cli._preflight_finalization_comparison_json(
            invalid_utf8_after_excess_nodes,
            include_leaf_depth=True,
        )

        parent, bundle, uncertain, repeated = self.fresh_inputs(
            "invalid-utf8-after-excess-json-nodes"
        )
        target = uncertain / "coding-audit-review-import-receipt.json"
        target.write_bytes(invalid_utf8_after_excess_nodes)
        before = _tree_snapshot(parent)

        result = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertTrue(report["checks"]["uncertain_directory_readable"])
        self.assertFalse(report["checks"]["uncertain_artifact_contracts_valid"])
        self.assertIn(
            "uncertain_review_import_artifact_contract_invalid",
            report["reason_codes"],
        )
        self.assertNotIn(
            "uncertain_review_import_unreadable",
            report["reason_codes"],
        )
        self.assert_value_free(
            result[1],
            self.private_candidate_id,
            str(target),
        )
        self.assertEqual(before, _tree_snapshot(parent))

    def test_surrogate_lexical_parity_preserves_invalid_vs_resource_boundary(
        self,
    ) -> None:
        lone_surrogates = (b'"\\ud800"\n', b'"\\udc00"\n')
        paired_surrogate = b'"\\ud800\\udc00"\n'
        with mock.patch.object(cli, "_AUDIT_IMPORT_MAX_STRING_BYTES", 2):
            for content in lone_surrogates:
                with self.subTest(helper_lone_surrogate=content):
                    cli._preflight_finalization_comparison_json(
                        content,
                        include_leaf_depth=True,
                    )
            with self.assertRaises(cli._FinalizationComparisonJSONResourceError):
                cli._preflight_finalization_comparison_json(
                    paired_surrogate,
                    include_leaf_depth=True,
                )

        for index, content in enumerate(lone_surrogates):
            with self.subTest(handler_lone_surrogate=content):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"lone-surrogate-{index}"
                )
                target = uncertain / "coding-audit-review-import-receipt.json"
                target.write_bytes(content)
                before = _tree_snapshot(parent)

                result = self.run_cli(self.argv(bundle, uncertain, repeated))

                self.assertEqual(2, result[0])
                report = self.assert_report(result)
                self.assertEqual("invalid", report["status"])
                self.assertTrue(
                    report["checks"]["uncertain_directory_readable"]
                )
                self.assertFalse(
                    report["checks"]["uncertain_artifact_contracts_valid"]
                )
                self.assertIn(
                    "uncertain_review_import_artifact_contract_invalid",
                    report["reason_codes"],
                )
                self.assertNotIn(
                    "uncertain_review_import_unreadable",
                    report["reason_codes"],
                )
                self.assert_value_free(
                    result[1],
                    content.decode("ascii").strip(),
                    self.private_candidate_id,
                    str(target),
                )
                self.assertEqual(before, _tree_snapshot(parent))

    def test_large_corresponding_files_are_compared_only_in_bounded_chunks(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs("chunked-raw-compare")
        padding = "x" * (cli._FINALIZATION_COMPARISON_CHUNK_BYTES * 2 + 17)
        large_invalid_record = _canonical_bytes({"private_padding": padding})
        for directory in (uncertain, repeated):
            (directory / "audit-decisions.jsonl").write_bytes(large_invalid_record)

        real_read = cli.os.read
        requested_sizes: list[int] = []

        def bounded_read(descriptor: int, size: int) -> bytes:
            requested_sizes.append(size)
            return real_read(descriptor, size)

        with mock.patch.object(cli.os, "read", side_effect=bounded_read):
            result = self.run_cli(self.argv(bundle, uncertain, repeated))

        self.assertEqual(2, result[0])
        report = self.assert_report(result)
        self.assertEqual("invalid", report["status"])
        self.assertFalse(report["checks"]["uncertain_artifact_contracts_valid"])
        self.assertFalse(report["checks"]["repeated_artifact_contracts_valid"])
        self.assertTrue(report["checks"]["import_directory_file_bytes_equal"])
        self.assertTrue(report["checks"]["final_recapture_valid"])
        self.assertTrue(requested_sizes)
        self.assertLessEqual(
            max(requested_sizes),
            cli._FINALIZATION_COMPARISON_CHUNK_BYTES,
        )
        self.assertGreaterEqual(
            requested_sizes.count(cli._FINALIZATION_COMPARISON_CHUNK_BYTES),
            4,
        )
        self.assert_value_free(result[1], padding[:128], str(parent))

    def test_failure_states_never_enter_recovery_or_external_side_effect_paths(self) -> None:
        forbidden = AssertionError("comparison attempted a prohibited failure side effect")
        forbidden_targets = (
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
            (subprocess, "run"),
            (subprocess, "Popen"),
            (socket, "socket"),
            (cli, "cmd_quality_coding_audit_review_import"),
            (cli, "_cmd_quality_coding_audit_review_import"),
            (cli, "build_native_coding_review_import"),
            (cli, "cmd_quality_coding_audit_finalize"),
            (cli, "_cmd_quality_coding_audit_finalize"),
            (cli, "build_native_coding_audit_finalization"),
            (cli, "cmd_handoff_create"),
            (cli, "cmd_handoff_import"),
            (cli, "create_handoff"),
            (cli, "import_handoff"),
            (cli, "cmd_source_promote_enumerator"),
            (cli, "promote_enumerator"),
            (cli, "_publish_new_audit_bundle"),
            (cli, "_atomic_rename_no_replace"),
            (cli, "_atomic_rename_no_replace_at"),
        )

        for state in ("mismatch", "invalid", "unreadable", "stdout_interrupted"):
            with self.subTest(state=state):
                parent, bundle, uncertain, repeated = self.fresh_inputs(
                    f"no-side-effects-{state}"
                )
                argv = self.argv(bundle, uncertain, repeated)
                if state == "mismatch":
                    argv = self.argv(
                        bundle,
                        uncertain,
                        repeated,
                        receipt_sha256="0" * 64,
                    )
                elif state == "invalid":
                    argv = self.argv(
                        bundle,
                        uncertain,
                        repeated,
                        receipt_sha256="A" * 64,
                    )
                elif state == "unreadable":
                    argv = self.argv(
                        bundle,
                        uncertain,
                        parent / "missing-repeated-review-import",
                    )
                before = _tree_snapshot(parent)

                with contextlib.ExitStack() as stack:
                    for owner, name in forbidden_targets:
                        stack.enter_context(
                            mock.patch.object(owner, name, side_effect=forbidden)
                        )
                    if state == "stdout_interrupted":
                        stack.enter_context(
                            mock.patch.object(
                                cli,
                                "_write_stdout_bytes",
                                side_effect=BrokenPipeError(
                                    "private stdout interruption"
                                ),
                            )
                        )
                    result = self.run_cli(argv)

                expected_code = 3 if state == "mismatch" else 2
                self.assertEqual(expected_code, result[0])
                if state == "stdout_interrupted":
                    self.assertEqual("", result[1])
                    self.assertIn("Ошибка:", result[2])
                else:
                    report = self.assert_report(result)
                    self.assertEqual(state, report["status"])
                self.assertEqual(before, _tree_snapshot(parent))

    def test_source_and_clean_install_are_identical_for_all_four_states(self) -> None:
        parent, bundle, uncertain, repeated = self.fresh_inputs("portable-parity")
        hostile_pythonpath = self.root / "ambient-conflicting-pythonpath"
        hostile_package = hostile_pythonpath / "judicial_meaning"
        hostile_package.mkdir(parents=True)
        (hostile_package / "__init__.py").write_text(
            "raise RuntimeError('ambient package must not load')\n",
            encoding="utf-8",
        )
        installed_skill = self.installed_script.parents[1]
        self.assertFalse((installed_skill / "tests").exists())
        self.assertFalse((installed_skill / "evals").exists())
        self.assertFalse((installed_skill / "openspec").exists())
        before = {
            "root": _tree_snapshot(self.root),
            "source_codebook": _file_snapshot(SOURCE_CODEBOOK),
            "installed_codebook": _file_snapshot(self.installed_codebook),
        }
        cases = (
            ("match", 0, self.argv(bundle, uncertain, repeated)),
            (
                "mismatch",
                3,
                self.argv(
                    bundle,
                    uncertain,
                    repeated,
                    receipt_sha256="0" * 64,
                ),
            ),
            (
                "invalid",
                2,
                self.argv(
                    bundle,
                    uncertain,
                    repeated,
                    receipt_sha256="A" * 64,
                ),
            ),
            (
                "unreadable",
                2,
                self.argv(
                    bundle,
                    uncertain,
                    parent / "missing-repeated-review-import",
                ),
            ),
        )

        for expected_status, expected_code, argv in cases:
            with self.subTest(status=expected_status):
                source = self.run_script(
                    SCRIPT,
                    argv,
                    cwd=self.root,
                    pythonpath=hostile_pythonpath,
                )
                installed = self.run_script(
                    self.installed_script,
                    argv,
                    cwd=self.root,
                    pythonpath=hostile_pythonpath,
                )
                self.assertEqual(expected_code, source.returncode, source.stderr)
                self.assertEqual(source.returncode, installed.returncode)
                self.assertEqual(source.stdout, installed.stdout)
                self.assertEqual("", source.stderr)
                self.assertEqual(source.stderr, installed.stderr)
                report = self.assert_report(
                    (source.returncode, source.stdout, source.stderr)
                )
                self.assertEqual(expected_status, report["status"])

        self.assertEqual(before["root"], _tree_snapshot(self.root))
        self.assertEqual(
            before["source_codebook"],
            _file_snapshot(SOURCE_CODEBOOK),
        )
        self.assertEqual(
            before["installed_codebook"],
            _file_snapshot(self.installed_codebook),
        )


if __name__ == "__main__":
    unittest.main()
