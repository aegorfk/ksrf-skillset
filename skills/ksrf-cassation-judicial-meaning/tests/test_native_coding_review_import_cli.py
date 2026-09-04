from __future__ import annotations

import argparse
import contextlib
import copy
import ctypes
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from unittest.mock import patch

from jsonschema import Draft202012Validator

from judicial_meaning.analysis import screen_text
import judicial_meaning.cli as cli_module
from judicial_meaning.cli import read_json, read_jsonl, write_jsonl
from judicial_meaning.plan import freeze_plan
from judicial_meaning.practice_quality import canonical_digest


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO = SKILL_ROOT.parents[1]
SCRIPT = Path("skills/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py")
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
OUTPUT_FILES = {
    "audit-decisions.jsonl",
    "coding-audit-review-import-receipt.json",
}


class NativeCodingReviewImportCliTests(unittest.TestCase):
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

    @classmethod
    def tearDownClass(cls) -> None:
        cls.install_tmp.cleanup()

    def _locations(self) -> tuple[tuple[str, Path], ...]:
        return (
            ("source", REPO / SCRIPT),
            (
                "installed",
                self.installed
                / "ksrf-cassation-judicial-meaning"
                / "scripts"
                / "judicial_meaning.py",
            ),
        )

    @staticmethod
    def _run(
        script: Path,
        arguments: list[str],
        *,
        cwd: Path,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *arguments],
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )

    def _seed_workspace(
        self, root: Path, *, candidate_count: int = 2
    ) -> dict[str, object]:
        workspace = root / "workspace"
        workspace.mkdir(parents=True)
        plan = json.loads(
            (FIXTURES / "research-plan-valid.json").read_text(encoding="utf-8")
        )
        plan["research_questions"][0]["status"] = "hypothesis_under_test"
        plan["research_questions"][0]["question"] = (
            "Подтверждается ли предположение, что спорная норма допускает "
            "восстановление срока при сопоставимых обстоятельствах?"
        )
        frozen = freeze_plan(plan, workspace)

        sources: list[dict[str, object]] = []
        screening: list[dict[str, object]] = []
        primary: list[dict[str, object]] = []
        for ordinal in range(1, candidate_count + 1):
            text = (
                "Суд установил, что срок подлежит восстановлению и статья 10 "
                f"применяется. Проверенная позиция суда номер {ordinal} "
                "обусловила отмену акта."
            )
            text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
            source = {
                "source_id": ordinal * 101,
                "run_id": "run-fixture",
                "snapshot_id": ordinal * 201,
                "court_code": "1kas",
                "kind": "doc",
                "canonical_url": f"https://1kas.sudrf.ru/document-{ordinal}",
                "case_uid": f"case-fixture-{ordinal}",
                "document_id": f"document-sha256:{text_sha256}",
                "chain_id": f"chain-fixture-{ordinal}",
                "raw_sha256": hashlib.sha256(
                    ("RAW:" + text).encode("utf-8")
                ).hexdigest(),
                "text_sha256": text_sha256,
                "text": text,
                "metadata_json": "{}",
                "created_at": "2026-09-03T12:00:00Z",
            }
            matches = screen_text(text, frozen["query_lanes"])
            self.assertTrue(matches)
            sources.append(source)
            screening.append(
                {
                    "source_id": source["source_id"],
                    "document_id": source["document_id"],
                    "chain_id": source["chain_id"],
                    "matches": matches,
                    "status": "candidate_needs_full_text_review",
                }
            )
            primary.append(
                {
                    "chain_id": source["chain_id"],
                    "document_id": source["document_id"],
                    "court_code": source["court_code"],
                    "decision_date": "2024-03-07",
                    "label": "false_positive",
                    "speaker": "court",
                    "proposition": "Суд связал восстановление срока с исходом дела.",
                    "quote": "срок подлежит восстановлению",
                    "quote_locator": f"абзац fixture {ordinal}",
                    "quote_verified": True,
                    "full_text_reviewed": True,
                    "norm_edition_id": "edition-fixture",
                    "material_facts": ["уважительная причина пропуска срока"],
                    "material_facts_group": "fixture",
                    "comparability_approved": True,
                    "reasoning_to_outcome": (
                        "Этот мотив повлёк отмену судебного акта."
                    ),
                    "alternative_grounds": [],
                    "remedy": "отмена",
                    "reading_family": "restore_deadline",
                    "relation": "supports",
                    "coder": f"primary-reviewer-{ordinal}",
                    "codebook_version": "1.0",
                    "human_review": "approved",
                }
            )

        sources_path = workspace / "exports" / "sources.jsonl"
        screening_path = workspace / "screening-candidates.jsonl"
        primary_path = workspace / "coding-decisions.jsonl"
        write_jsonl(sources_path, sources)
        write_jsonl(screening_path, screening)
        write_jsonl(primary_path, primary)
        bundles = root
        return {
            "workspace": workspace,
            "bundles": bundles,
            "frozen": frozen,
        }

    def _prepare_bundle(
        self, root: Path, *, candidate_count: int = 2
    ) -> tuple[dict[str, object], Path, str]:
        state = self._seed_workspace(root, candidate_count=candidate_count)
        bundle = Path(state["bundles"]) / "native-bundle"
        completed = self._run(
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
                str(bundle),
            ],
            cwd=root,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        return state, bundle, payload["manifest_sha256"]

    @staticmethod
    def _secondary_records(bundle: Path) -> list[dict[str, object]]:
        records = copy.deepcopy(read_jsonl(bundle / "primary-decisions.audit.jsonl"))
        for record in records:
            record["coder"] = "secondary-reviewer"
        return records

    @staticmethod
    def _write_secondary(
        root: Path, records: list[dict[str, object]], *, name: str = "returned.jsonl"
    ) -> Path:
        path = root / name
        write_jsonl(path, records)
        return path

    @staticmethod
    def _import_arguments(
        bundle: Path,
        secondary: Path,
        destination: Path,
        expected_manifest_sha256: str,
        *,
        expected_coder: str = "secondary-reviewer",
    ) -> list[str]:
        return [
            "quality",
            "coding-audit-review-import",
            "--bundle",
            str(bundle),
            "--expected-manifest-sha256",
            expected_manifest_sha256,
            "--expected-secondary-coder",
            expected_coder,
            "--secondary-coding",
            str(secondary),
            "--output-dir",
            str(destination),
        ]

    def _assert_rejected(
        self,
        *,
        root: Path,
        bundle: Path,
        secondary: Path,
        destination: Path,
        expected_manifest_sha256: str,
        expected_coder: str = "secondary-reviewer",
        error_fragment: str | None = None,
    ) -> None:
        completed = self._run(
            REPO / SCRIPT,
            self._import_arguments(
                bundle,
                secondary,
                destination,
                expected_manifest_sha256,
                expected_coder=expected_coder,
            ),
            cwd=root,
        )
        self.assertEqual(2, completed.returncode, completed.stdout)
        self.assertEqual("", completed.stdout)
        self.assertTrue(completed.stderr.startswith("Ошибка: "), completed.stderr)
        if error_fragment is not None:
            self.assertIn(error_fragment, completed.stderr)
        self.assertFalse(destination.exists())
        self.assertEqual([], list(destination.parent.glob(f".{destination.name}.staging-*")))

    @staticmethod
    def _refresh_parent_manifest(bundle: Path) -> str:
        path = bundle / "coding-audit-inputs-manifest.json"
        manifest = read_json(path)
        for entry in manifest["files"]:
            content = (bundle / entry["path"]).read_bytes()
            entry["bytes"] = len(content)
            entry["sha256"] = hashlib.sha256(content).hexdigest()
        unsigned = {
            key: value for key, value in manifest.items() if key != "manifest_sha256"
        }
        manifest["manifest_sha256"] = canonical_digest(unsigned)
        path.write_bytes(cli_module._canonical_json_bytes(manifest))
        return manifest["manifest_sha256"]

    @staticmethod
    def _rewrite_zip(
        bundle: Path,
        *,
        compression: int = zipfile.ZIP_STORED,
        altered_member: str | None = None,
        altered_timestamp: bool = False,
    ) -> None:
        path = bundle / "independent-review-packet.zip"
        with zipfile.ZipFile(path, "r") as archive:
            members = [(info.filename, archive.read(info)) for info in archive.infolist()]
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
            for name, content in members:
                if name == altered_member:
                    content += b"\n"
                timestamp = (1981, 1, 1, 0, 0, 0) if altered_timestamp else (
                    1980,
                    1,
                    1,
                    0,
                    0,
                    0,
                )
                info = zipfile.ZipInfo(name, date_time=timestamp)
                info.compress_type = compression
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.extra = b""
                info.comment = b""
                archive.writestr(info, content)
        path.write_bytes(buffer.getvalue())

    def test_source_and_install_emit_identical_canonical_receipt_and_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root)
            secondary_records = list(reversed(self._secondary_records(bundle)))
            secondary_records[0]["proposition"] = (
                "Независимая формулировка того же вывода."
            )
            secondary_records[0]["label"] = "mentioned_only"
            secondary = self._write_secondary(root, secondary_records)
            observed: dict[str, dict[str, bytes]] = {}
            for location, script in self._locations():
                destination = root / f"import-{location}"
                completed = self._run(
                    script,
                    self._import_arguments(bundle, secondary, destination, expected),
                    cwd=root,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                self.assertEqual("", completed.stderr)
                self.assertEqual(OUTPUT_FILES, {path.name for path in destination.iterdir()})
                self.assertEqual(0o700, stat.S_IMODE(destination.stat().st_mode))
                for path in destination.iterdir():
                    self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))

                decisions_bytes = (destination / "audit-decisions.jsonl").read_bytes()
                receipt_bytes = (
                    destination / "coding-audit-review-import-receipt.json"
                ).read_bytes()
                decisions = read_jsonl(destination / "audit-decisions.jsonl")
                receipt = json.loads(receipt_bytes)
                schema = json.loads(
                    (SKILL_ROOT / "schemas" / "practice-quality.v1.json").read_text(
                        encoding="utf-8"
                    )
                )
                Draft202012Validator(
                    {
                        "$schema": schema["$schema"],
                        "$ref": "#/definitions/coding_audit_review_import_receipt",
                        "definitions": schema["definitions"],
                    }
                ).validate(receipt)
                self.assertEqual(
                    canonical_digest(
                        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
                    ),
                    receipt["receipt_sha256"],
                )
                self.assertEqual(
                    hashlib.sha256(decisions_bytes).hexdigest(),
                    receipt["audit_decisions_file_sha256"],
                )
                self.assertEqual(
                    hashlib.sha256(secondary.read_bytes()).hexdigest(),
                    receipt["secondary_coding_file_sha256"],
                )
                self.assertEqual(
                    hashlib.sha256(
                        (bundle / "coding-audit-inputs-manifest.json").read_bytes()
                    ).hexdigest(),
                    receipt["source_bundle_manifest_file_sha256"],
                )
                self.assertEqual(
                    hashlib.sha256(
                        (bundle / "independent-review-packet.zip").read_bytes()
                    ).hexdigest(),
                    receipt["review_packet_sha256"],
                )
                self.assertEqual(
                    receipt["candidate_ids"],
                    [decision["candidate_id"] for decision in decisions],
                )
                self.assertEqual(sorted(receipt["candidate_ids"]), receipt["candidate_ids"])
                self.assertTrue(receipt["adjudication_required"])
                self.assertTrue(receipt["non_audited_content_review_required"])
                self.assertEqual(
                    [secondary_records[0]["candidate_id"]],
                    receipt["audited_field_disagreement_candidate_ids"],
                )
                self.assertEqual(
                    [secondary_records[0]["candidate_id"]],
                    receipt["non_audited_content_difference_candidate_ids"],
                )
                self.assertEqual(
                    [
                        {
                            "candidate_id": secondary_records[0]["candidate_id"],
                            "fields": ["label"],
                        }
                    ],
                    receipt["audited_field_differences"],
                )
                self.assertEqual(
                    [
                        {
                            "candidate_id": secondary_records[0]["candidate_id"],
                            "fields": ["proposition"],
                        }
                    ],
                    receipt["non_audited_content_differences"],
                )
                self.assertEqual(
                    hashlib.sha256(b"secondary-reviewer").hexdigest(),
                    receipt["expected_secondary_coder_label_sha256"],
                )
                for field in (
                    "returned_quote_literal_presence_verified",
                    "secondary_coder_label_differs_from_each_sampled_primary_label",
                    "single_secondary_coder_label",
                    "bundle_internal_consistency_verified",
                    "expected_manifest_digest_match_verified",
                    "norm_edition_allowlist_membership_verified",
                ):
                    self.assertIs(receipt[field], True, field)
                for field in (
                    "quote_locator_verified",
                    "secondary_coder_label_precommit_verified",
                    "source_workspace_reverified",
                    "reviewer_packet_use_attested",
                    "norm_edition_temporal_applicability_verified",
                    "reviewer_identity_authenticated",
                    "human_review_authenticated",
                    "independence_verified",
                    "receipt_authenticated",
                    "publication_safe",
                    "legal_readiness",
                ):
                    self.assertIs(receipt[field], False, field)
                stdout = json.loads(completed.stdout)
                self.assertTrue(stdout["adjudication_required"])
                self.assertTrue(stdout["non_audited_content_review_required"])
                self.assertEqual(
                    receipt["audited_field_differences"],
                    stdout["audited_field_differences"],
                )
                self.assertEqual(
                    receipt["non_audited_content_differences"],
                    stdout["non_audited_content_differences"],
                )
                self.assertEqual(
                    receipt["expected_secondary_coder_label_sha256"],
                    stdout["expected_secondary_coder_label_sha256"],
                )
                for field in (
                    "returned_quote_literal_presence_verified",
                    "quote_locator_verified",
                    "secondary_coder_label_precommit_verified",
                    "secondary_coder_label_differs_from_each_sampled_primary_label",
                    "single_secondary_coder_label",
                    "bundle_internal_consistency_verified",
                    "expected_manifest_digest_match_verified",
                    "norm_edition_allowlist_membership_verified",
                    "source_workspace_reverified",
                    "reviewer_packet_use_attested",
                    "norm_edition_temporal_applicability_verified",
                    "reviewer_identity_authenticated",
                    "human_review_authenticated",
                    "independence_verified",
                    "receipt_authenticated",
                    "publication_safe",
                    "legal_readiness",
                ):
                    self.assertIs(stdout[field], receipt[field], field)
                observed[location] = {
                    "decisions": decisions_bytes,
                    "receipt": receipt_bytes,
                }
            self.assertEqual(observed["source"], observed["installed"])

    def test_prepare_and_import_help_disclose_darwin_acl_boundary(self) -> None:
        required_fragments = (
            "macOS родительская, временная и итоговая папки",
            "вовсе не иметь расширенных ACL",
            "запрещающую запись и запись без наследования",
            "приватную родительскую папку без ACL",
            "обратитесь к системному администратору",
            "chmod сама по себе не подтверждает удаление ACL",
        )
        for location, script in self._locations():
            for command in ("coding-audit-prepare", "coding-audit-review-import"):
                with self.subTest(location=location, command=command):
                    completed = self._run(
                        script,
                        ["quality", command, "--help"],
                        cwd=REPO,
                    )
                    self.assertEqual(0, completed.returncode, completed.stderr)
                    normalized_help = " ".join(completed.stdout.split())
                    for fragment in required_fragments:
                        self.assertIn(fragment, normalized_help)

    def test_wrong_external_anchor_and_self_consistent_manifest_tamper_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            self._assert_rejected(
                root=root,
                bundle=bundle,
                secondary=secondary,
                destination=root / "wrong-anchor",
                expected_manifest_sha256="f" * 64,
                error_fragment="отдельно сохранённым",
            )

            manifest_path = bundle / "coding-audit-inputs-manifest.json"
            manifest = read_json(manifest_path)
            manifest["source_primary_sha256"] = "e" * 64
            manifest["manifest_sha256"] = canonical_digest(
                {key: value for key, value in manifest.items() if key != "manifest_sha256"}
            )
            manifest_path.write_bytes(cli_module._canonical_json_bytes(manifest))
            self._assert_rejected(
                root=root,
                bundle=bundle,
                secondary=secondary,
                destination=root / "tampered-anchor",
                expected_manifest_sha256=expected,
                error_fragment="отдельно сохранённым",
            )

    def test_main_and_alternative_quotes_require_literal_case_and_whitespace(self) -> None:
        cases = (
            "main-case",
            "main-whitespace",
            "alternative-case",
            "alternative-whitespace",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                records = self._secondary_records(bundle)
                if case == "main-case":
                    records[0]["quote"] = str(records[0]["quote"]).upper()
                elif case == "main-whitespace":
                    records[0]["quote"] = "срок  подлежит восстановлению"
                else:
                    alternative_quote = "Проверенная позиция суда номер 1"
                    if case == "alternative-case":
                        alternative_quote = alternative_quote.upper()
                    else:
                        alternative_quote = "Проверенная  позиция суда номер 1"
                    records[0]["alternative_grounds"] = [
                        {
                            "ground": "Дополнительное основание",
                            "independently_sufficient": True,
                            "quote": alternative_quote,
                            "quote_locator": "абзац fixture 1",
                        }
                    ]
                secondary = self._write_secondary(root, records)
                self._assert_rejected(
                    root=root,
                    bundle=bundle,
                    secondary=secondary,
                    destination=root / "must-not-exist",
                    expected_manifest_sha256=expected,
                    error_fragment="буквальной подстрокой",
                )

    def test_zip_preflight_rejects_zip64_entry_count_before_stdlib_parsing(self) -> None:
        zip64_end_record = struct.pack(
            "<4s4H2LH",
            b"PK\x05\x06",
            0,
            0,
            0xFFFF,
            0xFFFF,
            0,
            0,
            0,
        )
        with patch.object(
            cli_module.zipfile,
            "ZipFile",
            side_effect=AssertionError("zipfile parser must not run"),
        ):
            with self.assertRaisesRegex(ValueError, "ZIP64"):
                cli_module._preflight_blinded_review_zip(zip64_end_record)

    def test_no_replace_rename_rejects_replaced_staging_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = root / "staging"
            staging.mkdir()
            original_stat = staging.stat()
            staging.rename(root / "moved-original")
            staging.mkdir()
            descriptor = os.open(
                root,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                with self.assertRaisesRegex(OSError, "заменена"):
                    cli_module._atomic_rename_no_replace_at(
                        descriptor,
                        "staging",
                        "published",
                        expected_source_identity=(
                            original_stat.st_dev,
                            original_stat.st_ino,
                        ),
                    )
            finally:
                os.close(descriptor)
            self.assertFalse((root / "published").exists())

    def test_expected_coder_must_be_one_canonical_label_distinct_from_each_primary(self) -> None:
        cases = ("same", "mixed", "wrong-expected")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                candidate_count = 1 if case == "same" else 2
                _, bundle, expected = self._prepare_bundle(
                    root, candidate_count=candidate_count
                )
                records = self._secondary_records(bundle)
                expected_coder = "secondary-reviewer"
                if case == "same":
                    records[0]["coder"] = "primary-reviewer-1"
                    expected_coder = "  PRIMARY-REVIEWER-1  "
                elif case == "mixed":
                    records[1]["coder"] = "other-secondary-reviewer"
                else:
                    expected_coder = "unexpected-reviewer"
                secondary = self._write_secondary(root, records)
                self._assert_rejected(
                    root=root,
                    bundle=bundle,
                    secondary=secondary,
                    destination=root / "must-not-exist",
                    expected_manifest_sha256=expected,
                    expected_coder=expected_coder,
                )

    def test_parent_extra_missing_symlink_and_hardlink_are_rejected(self) -> None:
        for case in ("extra", "missing", "symlink", "hardlink"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = self._write_secondary(root, self._secondary_records(bundle))
                if case == "extra":
                    (bundle / "unexpected.txt").write_text("extra\n", encoding="utf-8")
                elif case == "missing":
                    (bundle / "secondary-coding-template.jsonl").unlink()
                elif case == "symlink":
                    target = bundle / "secondary-coding-template.jsonl"
                    outside = root / "template-copy.jsonl"
                    target.replace(outside)
                    target.symlink_to(outside)
                else:
                    os.link(bundle / "coding-audit-plan.json", root / "hardlink-plan.json")
                self._assert_rejected(
                    root=root,
                    bundle=bundle,
                    secondary=secondary,
                    destination=root / "must-not-exist",
                    expected_manifest_sha256=expected,
                )

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO requires POSIX")
    def test_fifo_inputs_are_rejected_without_blocking(self) -> None:
        for case in ("secondary", "bundle-child"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = root / "returned.jsonl"
                if case == "secondary":
                    os.mkfifo(secondary)
                else:
                    secondary = self._write_secondary(
                        root, self._secondary_records(bundle)
                    )
                    bundle_child = bundle / "coding-audit-plan.json"
                    bundle_child.unlink()
                    os.mkfifo(bundle_child)
                destination = root / "must-not-exist"
                completed = self._run(
                    REPO / SCRIPT,
                    self._import_arguments(
                        bundle, secondary, destination, expected
                    ),
                    cwd=root,
                    timeout=3,
                )
                self.assertEqual(2, completed.returncode, completed.stdout)
                self.assertEqual("", completed.stdout)
                self.assertIn("обычный файл", completed.stderr)
                self.assertFalse(destination.exists())

    def test_zip_compression_metadata_and_member_alterations_are_rejected(self) -> None:
        cases = ("compression", "timestamp", "member")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, _ = self._prepare_bundle(root, candidate_count=1)
                secondary = self._write_secondary(root, self._secondary_records(bundle))
                if case == "compression":
                    self._rewrite_zip(bundle, compression=zipfile.ZIP_DEFLATED)
                elif case == "timestamp":
                    self._rewrite_zip(bundle, altered_timestamp=True)
                else:
                    self._rewrite_zip(
                        bundle, altered_member="REVIEW-INSTRUCTIONS.md"
                    )
                expected = self._refresh_parent_manifest(bundle)
                self._assert_rejected(
                    root=root,
                    bundle=bundle,
                    secondary=secondary,
                    destination=root / "must-not-exist",
                    expected_manifest_sha256=expected,
                )

    def test_zip_diagnostic_does_not_echo_untrusted_member_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, _ = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            packet = bundle / "independent-review-packet.zip"
            with zipfile.ZipFile(packet, "r") as archive:
                members = [
                    (info.filename, archive.read(info)) for info in archive.infolist()
                ]
            untrusted_name = "SECRET-PRIVATE-PERSON-NAME.txt"
            buffer = io.BytesIO()
            with zipfile.ZipFile(
                buffer,
                "w",
                compression=zipfile.ZIP_STORED,
            ) as archive:
                for index, (name, content) in enumerate(members):
                    info = zipfile.ZipInfo(
                        untrusted_name if index == 0 else name,
                        date_time=(1980, 1, 1, 0, 0, 0),
                    )
                    info.compress_type = zipfile.ZIP_STORED
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, content)
            packet.write_bytes(buffer.getvalue())
            expected = self._refresh_parent_manifest(bundle)
            destination = root / "must-not-exist"
            completed = self._run(
                REPO / SCRIPT,
                self._import_arguments(bundle, secondary, destination, expected),
                cwd=root,
            )

            self.assertEqual(2, completed.returncode, completed.stdout)
            self.assertEqual("", completed.stdout)
            self.assertIn("ровно шесть уникальных файлов", completed.stderr)
            self.assertNotIn(untrusted_name, completed.stderr)
            self.assertFalse(destination.exists())

    def test_secondary_duplicate_extra_duplicate_key_and_nonfinite_json_fail_closed(self) -> None:
        cases = ("duplicate-row", "extra-row", "duplicate-key", "nan")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                records = self._secondary_records(bundle)
                secondary = root / "returned.jsonl"
                if case == "duplicate-row":
                    write_jsonl(secondary, [records[0], copy.deepcopy(records[0])])
                elif case == "extra-row":
                    extra = copy.deepcopy(records[0])
                    extra["candidate_id"] = "audit-candidate-sha256:" + "f" * 64
                    write_jsonl(secondary, [records[0], extra])
                elif case == "duplicate-key":
                    secondary.write_text(
                        '{"candidate_id":"first","candidate_id":"second"}\n',
                        encoding="utf-8",
                    )
                else:
                    content = json.dumps(records[0], ensure_ascii=False, sort_keys=True)
                    content = content[:-1] + ',"unexpected":NaN}\n'
                    secondary.write_text(content, encoding="utf-8")
                self._assert_rejected(
                    root=root,
                    bundle=bundle,
                    secondary=secondary,
                    destination=root / "must-not-exist",
                    expected_manifest_sha256=expected,
                )

    def test_untrusted_ids_and_duplicate_keys_do_not_leak_to_diagnostics(self) -> None:
        secret = "СЕКРЕТНАЯ ЦИТАТА ИЗ СУДЕБНОГО АКТА"
        for case in ("candidate-id", "duplicate-key"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = root / "returned.jsonl"
                if case == "candidate-id":
                    records = self._secondary_records(bundle)
                    records[0]["candidate_id"] = secret
                    write_jsonl(secondary, records)
                else:
                    secondary.write_text(
                        json.dumps({secret: "first"}, ensure_ascii=False)[:-1]
                        + ","
                        + json.dumps(secret, ensure_ascii=False)
                        + ':"second"}\n',
                        encoding="utf-8",
                    )
                destination = root / "must-not-exist"
                completed = self._run(
                    REPO / SCRIPT,
                    self._import_arguments(
                        bundle, secondary, destination, expected
                    ),
                    cwd=root,
                )
                self.assertEqual(2, completed.returncode, completed.stdout)
                self.assertEqual("", completed.stdout)
                self.assertNotIn(secret, completed.stderr)
                self.assertFalse(destination.exists())

    def test_output_must_be_new_sibling_of_parent_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            existing = root / "existing-output"
            existing.mkdir()
            (existing / "sentinel.txt").write_text("keep\n", encoding="utf-8")
            completed = self._run(
                REPO / SCRIPT,
                self._import_arguments(bundle, secondary, existing, expected),
                cwd=root,
            )
            self.assertEqual(2, completed.returncode)
            self.assertEqual("keep\n", (existing / "sentinel.txt").read_text(encoding="utf-8"))

            inside = bundle / "import-output"
            self._assert_rejected(
                root=root,
                bundle=bundle,
                secondary=secondary,
                destination=inside,
                expected_manifest_sha256=expected,
                error_fragment="соседней папкой",
            )

            other_parent = root / "other-parent"
            other_parent.mkdir()
            self._assert_rejected(
                root=root,
                bundle=bundle,
                secondary=secondary,
                destination=other_parent / "import-output",
                expected_manifest_sha256=expected,
                error_fragment="соседней папкой",
            )

    def test_output_parent_is_bound_to_bundle_parent_across_symlink_retarget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            _, original_bundle, expected = self._prepare_bundle(first, candidate_count=1)
            bundle_name = original_bundle.name
            copied_bundle = second / bundle_name
            import shutil

            shutil.copytree(original_bundle, copied_bundle)
            secondary = self._write_secondary(
                root, self._secondary_records(original_bundle)
            )
            link = root / "current"
            link.symlink_to(first, target_is_directory=True)
            bundle_through_link = link / bundle_name
            output_through_link = link / "import-output"
            args = argparse.Namespace(
                bundle=str(bundle_through_link),
                expected_manifest_sha256=expected,
                expected_secondary_coder="secondary-reviewer",
                secondary_coding=str(secondary),
                output_dir=str(output_through_link),
            )
            real_resolve = cli_module._resolve_new_import_output

            def retarget_then_resolve(
                raw_value: str, *, bundle_parent_descriptor: int
            ) -> Path:
                link.unlink()
                link.symlink_to(second, target_is_directory=True)
                return real_resolve(
                    raw_value,
                    bundle_parent_descriptor=bundle_parent_descriptor,
                )

            with patch.object(
                cli_module,
                "_resolve_new_import_output",
                side_effect=retarget_then_resolve,
            ), self.assertRaisesRegex(ValueError, "соседней папкой"):
                cli_module.cmd_quality_coding_audit_review_import(args)
            self.assertFalse(first.joinpath("import-output").exists())
            self.assertFalse(second.joinpath("import-output").exists())

    def test_extended_acl_probe_is_fail_closed_and_recaptures_fd_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "acl-probe-target"
            target.write_bytes(b"probe")
            descriptor = os.open(target, os.O_RDONLY)
            real_fstat = os.fstat
            fstat_calls = 0

            def counted_fstat(value: int) -> os.stat_result:
                nonlocal fstat_calls
                self.assertEqual(descriptor, value)
                fstat_calls += 1
                return real_fstat(value)

            try:
                with patch.object(
                    cli_module.os,
                    "fstat",
                    side_effect=counted_fstat,
                ):
                    observed_acl_types: list[int] = []
                    free_calls: list[object] = []

                    def no_acl(value: int, acl_type: int) -> None:
                        self.assertEqual(descriptor, value)
                        observed_acl_types.append(acl_type)
                        ctypes.set_errno(errno.ENOENT)
                        return None

                    def unexpected_free(value: object) -> int:
                        free_calls.append(value)
                        return 0

                    cli_module._assert_fd_has_no_extended_acl(
                        descriptor,
                        acl_type=7,
                        object_label="Проверяемый объект",
                        acl_get_fd_np=no_acl,
                        acl_free=unexpected_free,
                    )
                    self.assertEqual([], free_calls)

                    def unsupported(value: int, acl_type: int) -> None:
                        self.assertEqual(descriptor, value)
                        observed_acl_types.append(acl_type)
                        ctypes.set_errno(errno.EOPNOTSUPP)
                        return None

                    with self.assertRaisesRegex(
                        OSError,
                        "отсутствие расширенного ACL не подтверждено",
                    ):
                        cli_module._assert_fd_has_no_extended_acl(
                            descriptor,
                            acl_type=7,
                            object_label="Проверяемый объект",
                            acl_get_fd_np=unsupported,
                            acl_free=unexpected_free,
                        )

                    acl_pointer = ctypes.c_void_p(12345)

                    def present(value: int, acl_type: int) -> ctypes.c_void_p:
                        self.assertEqual(descriptor, value)
                        observed_acl_types.append(acl_type)
                        ctypes.set_errno(0)
                        return acl_pointer

                    def successful_free(value: object) -> int:
                        free_calls.append(value)
                        return 0

                    with self.assertRaisesRegex(
                        ValueError,
                        "обнаружен расширенный ACL macOS",
                    ):
                        cli_module._assert_fd_has_no_extended_acl(
                            descriptor,
                            acl_type=7,
                            object_label="Проверяемый объект",
                            acl_get_fd_np=present,
                            acl_free=successful_free,
                        )

                    def failed_free(value: object) -> int:
                        free_calls.append(value)
                        ctypes.set_errno(errno.EIO)
                        return -1

                    with self.assertRaisesRegex(
                        OSError,
                        "освобождение системного объекта ACL не подтверждено",
                    ):
                        cli_module._assert_fd_has_no_extended_acl(
                            descriptor,
                            acl_type=7,
                            object_label="Проверяемый объект",
                            acl_get_fd_np=present,
                            acl_free=failed_free,
                        )

                self.assertEqual([7, 7, 7, 7], observed_acl_types)
                self.assertEqual(8, fstat_calls)
                self.assertEqual(2, len(free_calls))
                self.assertTrue(all(value is acl_pointer for value in free_calls))
            finally:
                os.close(descriptor)

    def test_extended_acl_guard_is_a_noop_outside_darwin(self) -> None:
        with (
            patch.object(cli_module.sys, "platform", "linux"),
            patch.object(
                cli_module,
                "_load_darwin_extended_acl_functions",
                side_effect=AssertionError("Darwin API не должен загружаться"),
            ) as loader,
            patch.object(
                cli_module.os,
                "fstat",
                side_effect=AssertionError("fd не должен проверяться как Darwin"),
            ),
        ):
            cli_module._assert_darwin_fd_has_no_extended_acl(
                -1,
                object_label="Проверяемый объект",
            )
        loader.assert_not_called()

    @unittest.skipUnless(sys.platform == "darwin", "требуется macOS/Darwin")
    def test_darwin_acl_probe_rejects_mode_change_inside_system_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.chmod(root, 0o700)
            descriptor = os.open(
                root,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            free_called = False

            def chmod_then_report_no_acl(value: int, acl_type: int) -> None:
                self.assertEqual(descriptor, value)
                self.assertEqual(0x100, acl_type)
                os.fchmod(value, 0o770)
                ctypes.set_errno(errno.ENOENT)
                return None

            def unexpected_free(value: object) -> int:
                nonlocal free_called
                free_called = True
                return 0

            try:
                with (
                    patch.object(
                        cli_module,
                        "_load_darwin_extended_acl_functions",
                        return_value=(chmod_then_report_no_acl, unexpected_free),
                    ),
                    self.assertRaisesRegex(
                        OSError,
                        "объект изменился во время проверки расширенного ACL",
                    ) as raised,
                ):
                    cli_module._assert_safe_publication_parent(descriptor)
                self.assertFalse(free_called)
                self.assertEqual(0o770, stat.S_IMODE(os.fstat(descriptor).st_mode))
                self.assertNotIn(str(root), str(raised.exception))
            finally:
                os.fchmod(descriptor, 0o700)
                os.close(descriptor)

    @unittest.skipUnless(sys.platform == "darwin", "требуется macOS/Darwin")
    def test_darwin_acl_removal_during_probe_is_detected_by_ctime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.chmod(root, 0o700)
            added = subprocess.run(
                ["chmod", "+a", "everyone allow read", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, added.returncode, added.stderr)
            descriptor = os.open(
                root,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            ctime_before_removal: int | None = None
            ctime_after_removal: int | None = None
            time.sleep(1.05)

            def remove_then_report_no_acl(value: int, acl_type: int) -> None:
                nonlocal ctime_before_removal, ctime_after_removal
                self.assertEqual(descriptor, value)
                self.assertEqual(0x100, acl_type)
                ctime_before_removal = os.fstat(value).st_ctime_ns
                removed = subprocess.run(
                    ["chmod", "-N", str(root)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, removed.returncode, removed.stderr)
                ctime_after_removal = os.fstat(value).st_ctime_ns
                ctypes.set_errno(errno.ENOENT)
                return None

            try:
                with (
                    patch.object(
                        cli_module,
                        "_load_darwin_extended_acl_functions",
                        return_value=(remove_then_report_no_acl, lambda value: 0),
                    ),
                    self.assertRaisesRegex(
                        OSError,
                        "объект изменился во время проверки расширенного ACL",
                    ) as raised,
                ):
                    cli_module._assert_safe_publication_parent(descriptor)
                self.assertIsNotNone(ctime_before_removal)
                self.assertIsNotNone(ctime_after_removal)
                self.assertNotEqual(ctime_before_removal, ctime_after_removal)
                self.assertNotIn(str(root), str(raised.exception))
            finally:
                subprocess.run(
                    ["chmod", "-N", str(root)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                os.close(descriptor)

    @unittest.skipUnless(sys.platform == "darwin", "требуется macOS/Darwin")
    def test_darwin_inherited_parent_acl_is_rejected_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "acl-rejected-output"
            rule = "everyone allow read,execute,file_inherit,directory_inherit"
            added = subprocess.run(
                ["chmod", "+a", rule, str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, added.returncode, added.stderr)
            stdout = io.StringIO()
            stderr = io.StringIO()
            try:
                with (
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main(
                        self._import_arguments(
                            bundle,
                            secondary,
                            destination,
                            expected,
                        )
                    )
            finally:
                removed = subprocess.run(
                    ["chmod", "-N", str(root)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, removed.returncode, removed.stderr)

            diagnostic = stderr.getvalue()
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertFalse(destination.exists())
            self.assertEqual([], list(root.glob(".acl-rejected-output.staging-*")))
            self.assertIn("обнаружен расширенный ACL macOS", diagnostic)
            self.assertIn("0700/0600 не подтверждает приватность", diagnostic)
            self.assertNotIn(str(root), diagnostic)

    @unittest.skipUnless(sys.platform == "darwin", "требуется macOS/Darwin")
    def test_darwin_acl_added_after_parent_precheck_is_caught_on_staging_fd(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "acl-race-output"
            rule = "everyone allow read,execute,file_inherit,directory_inherit"
            real_mkdir = os.mkdir
            injected = False
            chmod_error = ""
            stdout = io.StringIO()
            stderr = io.StringIO()

            def add_inherited_acl_before_staging_mkdir(
                name: str,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> None:
                nonlocal injected, chmod_error
                if (
                    not injected
                    and dir_fd is not None
                    and name.startswith(f".{destination.name}.staging-")
                ):
                    added = subprocess.run(
                        ["chmod", "+a", rule, str(root)],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    chmod_error = added.stderr
                    if added.returncode != 0:
                        raise OSError("не удалось создать ACL для теста")
                    injected = True
                real_mkdir(name, mode, dir_fd=dir_fd)

            try:
                with (
                    patch.object(
                        cli_module.os,
                        "mkdir",
                        side_effect=add_inherited_acl_before_staging_mkdir,
                    ),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main(
                        self._import_arguments(
                            bundle,
                            secondary,
                            destination,
                            expected,
                        )
                    )

                staging_paths = list(root.glob(".acl-race-output.staging-*"))
                self.assertTrue(injected, chmod_error)
                self.assertEqual(2, return_code)
                self.assertEqual("", stdout.getvalue())
                self.assertFalse(destination.exists())
                self.assertEqual(1, len(staging_paths))
                self.assertEqual([], list(staging_paths[0].iterdir()))
                acl_listing = subprocess.run(
                    ["ls", "-lde", str(staging_paths[0])],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, acl_listing.returncode, acl_listing.stderr)
                self.assertIn("inherited", acl_listing.stdout)
                diagnostic = stderr.getvalue()
                staging_stat = staging_paths[0].stat()
                self.assertIn("Очистка временной публикации", diagnostic)
                self.assertIn(
                    f"устройство временной папки {staging_stat.st_dev}, "
                    f"inode {staging_stat.st_ino}",
                    diagnostic,
                )
                self.assertIn("Остановите автоматику", diagnostic)
                self.assertIn("поместить в карантин", diagnostic)
                self.assertNotIn(str(root), diagnostic)
            finally:
                for staging_path in root.glob(".acl-race-output.staging-*"):
                    subprocess.run(
                        ["chmod", "-N", str(staging_path)],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                subprocess.run(
                    ["chmod", "-N", str(root)],
                    text=True,
                    capture_output=True,
                    check=False,
                )

    @unittest.skipUnless(sys.platform == "darwin", "требуется macOS/Darwin")
    def test_inherited_acl_file_failure_reports_staging_and_file_coordinates(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "acl-file-race-output"
            rule = "everyone allow read,execute,file_inherit,directory_inherit"
            real_acl_guard = cli_module._assert_darwin_fd_has_no_extended_acl
            injected = False
            stdout = io.StringIO()
            stderr = io.StringIO()

            def add_acl_after_staging_guard(
                descriptor: int, *, object_label: str
            ) -> None:
                nonlocal injected
                real_acl_guard(descriptor, object_label=object_label)
                if object_label == "Временная папка публикации" and not injected:
                    staging_paths = list(
                        root.glob(".acl-file-race-output.staging-*")
                    )
                    self.assertEqual(1, len(staging_paths))
                    added = subprocess.run(
                        ["chmod", "+a", rule, str(staging_paths[0])],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(0, added.returncode, added.stderr)
                    injected = True

            try:
                with (
                    patch.object(
                        cli_module,
                        "_assert_darwin_fd_has_no_extended_acl",
                        side_effect=add_acl_after_staging_guard,
                    ),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main(
                        self._import_arguments(
                            bundle,
                            secondary,
                            destination,
                            expected,
                        )
                    )

                staging_paths = list(root.glob(".acl-file-race-output.staging-*"))
                self.assertTrue(injected)
                self.assertEqual(2, return_code)
                self.assertEqual("", stdout.getvalue())
                self.assertFalse(destination.exists())
                self.assertEqual(1, len(staging_paths))
                created_files = list(staging_paths[0].iterdir())
                self.assertEqual(1, len(created_files))
                self.assertEqual(0, created_files[0].stat().st_size)
                acl_listing = subprocess.run(
                    ["ls", "-le", str(created_files[0])],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, acl_listing.returncode, acl_listing.stderr)
                self.assertIn("inherited", acl_listing.stdout)
                staging_stat = staging_paths[0].stat()
                file_stat = created_files[0].stat()
                diagnostic = stderr.getvalue()
                self.assertIn("Очистка временной публикации", diagnostic)
                self.assertIn(
                    f"устройство временной папки {staging_stat.st_dev}, "
                    f"inode {staging_stat.st_ino}",
                    diagnostic,
                )
                self.assertIn(
                    f"устройство {file_stat.st_dev}, inode {file_stat.st_ino}",
                    diagnostic,
                )
                self.assertIn("все имена и жёсткие ссылки", diagnostic)
                self.assertIn("поместить в карантин", diagnostic)
                self.assertNotIn(str(root), diagnostic)
            finally:
                for staging_path in root.glob(".acl-file-race-output.staging-*"):
                    for child in staging_path.iterdir():
                        subprocess.run(
                            ["chmod", "-N", str(child)],
                            text=True,
                            capture_output=True,
                            check=False,
                        )
                    subprocess.run(
                        ["chmod", "-N", str(staging_path)],
                        text=True,
                        capture_output=True,
                        check=False,
                    )

    @unittest.skipUnless(os.name == "posix", "POSIX directory modes required")
    def test_writable_shared_output_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "must-not-exist"
            os.chmod(root, 0o777)
            try:
                self._assert_rejected(
                    root=root,
                    bundle=bundle,
                    secondary=secondary,
                    destination=destination,
                    expected_manifest_sha256=expected,
                    error_fragment="записи группе",
                )
            finally:
                os.chmod(root, 0o700)

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "geteuid"),
        "effective UID checks require POSIX",
    )
    def test_safe_parent_uses_effective_not_real_uid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            descriptor = os.open(
                root,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                owner = os.fstat(descriptor).st_uid
                with (
                    patch.object(cli_module.os, "geteuid", return_value=owner + 1),
                    patch.object(cli_module.os, "getuid", return_value=owner),
                    self.assertRaisesRegex(ValueError, "текущему пользователю"),
                ):
                    cli_module._assert_safe_publication_parent(descriptor)
                with (
                    patch.object(cli_module.os, "geteuid", return_value=owner),
                    patch.object(cli_module.os, "getuid", return_value=owner + 1),
                ):
                    cli_module._assert_safe_publication_parent(descriptor)
            finally:
                os.close(descriptor)

    def test_bundle_inventory_stops_at_first_excess_entry(self) -> None:
        consumed: list[int] = []

        class FakeEntry:
            def __init__(self, name: str) -> None:
                self.name = name

        class FakeScandir:
            def __enter__(self) -> "FakeScandir":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def __iter__(self):
                for index in range(100):
                    if index >= len(cli_module._AUDIT_BUNDLE_PATHS) + 1:
                        raise AssertionError("перечисление не остановилось на лимите")
                    consumed.append(index)
                    yield FakeEntry(f"entry-{index}")

        with tempfile.TemporaryDirectory() as tmp:
            descriptor = os.open(
                tmp,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                with (
                    patch.object(cli_module.os, "scandir", return_value=FakeScandir()),
                    self.assertRaisesRegex(ValueError, "слишком много записей"),
                ):
                    cli_module._capture_audit_bundle_descriptor(descriptor)
            finally:
                os.close(descriptor)
        self.assertEqual(len(cli_module._AUDIT_BUNDLE_PATHS) + 1, len(consumed))

    def test_secondary_resource_limits_reject_deep_and_oversized_inputs(self) -> None:
        for case in ("deep", "oversized"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = root / "returned.jsonl"
                if case == "deep":
                    record = self._secondary_records(bundle)[0]
                    nested: object = "leaf"
                    for _ in range(cli_module._AUDIT_IMPORT_MAX_JSON_DEPTH + 2):
                        nested = [nested]
                    record["material_facts"] = nested
                    secondary.write_text(
                        json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
                    )
                else:
                    with secondary.open("wb") as stream:
                        stream.truncate(cli_module._AUDIT_IMPORT_SECONDARY_LIMIT + 1)
                self._assert_rejected(
                    root=root,
                    bundle=bundle,
                    secondary=secondary,
                    destination=root / "must-not-exist",
                    expected_manifest_sha256=expected,
                    error_fragment=("глуб" if case == "deep" else "безопасный предел"),
                )

    def test_version_1_1_bundle_remains_importable_but_pre_packet_legacy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, _ = self._prepare_bundle(root, candidate_count=1)
            with zipfile.ZipFile(bundle / "independent-review-packet.zip", "r") as archive:
                member_bytes = {
                    info.filename: archive.read(info) for info in archive.infolist()
                }
            projection = {
                "audit_plan": read_json(bundle / "coding-audit-plan.json"),
                "screening_candidates": read_jsonl(
                    bundle / "screening-candidates.audit.jsonl"
                ),
                "secondary_review_queue": read_jsonl(
                    bundle / "secondary-review-queue.jsonl"
                ),
                "secondary_coding_templates": read_jsonl(
                    bundle / "secondary-coding-template.jsonl"
                ),
                "secondary_review_materials": [
                    json.loads(line)
                    for line in member_bytes["review-materials.jsonl"]
                    .decode("utf-8")
                    .splitlines()
                    if line
                ],
                "codebook_version": "1.0",
            }
            rebuilt_1_1 = cli_module._build_blinded_review_packet(
                projection,
                plan_sha256=projection["audit_plan"]["plan_sha256"],
                codebook_content=member_bytes["CODING-CODEBOOK.md"],
                coding_brief_content=member_bytes["CODING-BRIEF.json"],
                bundle_contract_version="1.1",
            )
            self.assertEqual(
                rebuilt_1_1,
                cli_module._build_blinded_review_packet(
                    projection,
                    plan_sha256=projection["audit_plan"]["plan_sha256"],
                    codebook_content=member_bytes["CODING-CODEBOOK.md"],
                    coding_brief_content=member_bytes["CODING-BRIEF.json"],
                    bundle_contract_version="1.1",
                ),
            )
            (bundle / "independent-review-packet.zip").write_bytes(rebuilt_1_1)
            manifest = read_json(bundle / "coding-audit-inputs-manifest.json")
            manifest["bundle_contract_version"] = "1.1"
            (bundle / "coding-audit-inputs-manifest.json").write_bytes(
                cli_module._canonical_json_bytes(manifest)
            )
            expected = self._refresh_parent_manifest(bundle)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "import-v1-1"
            accepted = self._run(
                REPO / SCRIPT,
                self._import_arguments(bundle, secondary, destination, expected),
                cwd=root,
            )
            self.assertEqual(0, accepted.returncode, accepted.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, _ = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            manifest_path = bundle / "coding-audit-inputs-manifest.json"
            manifest = read_json(manifest_path)
            del manifest["bundle_contract_version"]
            manifest["manifest_sha256"] = canonical_digest(
                {key: value for key, value in manifest.items() if key != "manifest_sha256"}
            )
            manifest_path.write_bytes(cli_module._canonical_json_bytes(manifest))
            self._assert_rejected(
                root=root,
                bundle=bundle,
                secondary=secondary,
                destination=root / "legacy-output",
                expected_manifest_sha256=manifest["manifest_sha256"],
                error_fragment="закрытый формат",
            )

    def test_each_input_change_during_final_recheck_leaves_no_partial_output(self) -> None:
        for changed_input in ("bundle", "secondary", "codebook"):
            with self.subTest(changed_input=changed_input), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = self._write_secondary(root, self._secondary_records(bundle))
                destination = root / "must-not-exist"
                args = argparse.Namespace(
                    bundle=str(bundle),
                    expected_manifest_sha256=expected,
                    expected_secondary_coder="secondary-reviewer",
                    secondary_coding=str(secondary),
                    output_dir=str(destination),
                )
                stack = contextlib.ExitStack()
                if changed_input == "bundle":
                    real_capture = cli_module._capture_audit_bundle_at

                    def changing_bundle(
                        parent_descriptor: int, bundle_name: str
                    ) -> dict[str, object]:
                        captured = copy.deepcopy(
                            real_capture(parent_descriptor, bundle_name)
                        )
                        captured["directory_identity"] = tuple(
                            captured["directory_identity"]
                        ) + (999,)
                        return captured

                    stack.enter_context(
                        patch.object(
                            cli_module,
                            "_capture_audit_bundle_at",
                            side_effect=changing_bundle,
                        )
                    )
                elif changed_input == "secondary":
                    real_capture = cli_module._capture_regular_file
                    secondary_calls = 0

                    def changing_file(
                        path: Path, *, label: str, byte_limit: int
                    ) -> dict[str, object]:
                        nonlocal secondary_calls
                        captured = real_capture(
                            path, label=label, byte_limit=byte_limit
                        )
                        if label == "--secondary-coding":
                            secondary_calls += 1
                            if secondary_calls > 1:
                                captured = copy.deepcopy(captured)
                                captured["identity"] = tuple(captured["identity"]) + (999,)
                        return captured

                    stack.enter_context(
                        patch.object(
                            cli_module,
                            "_capture_regular_file",
                            side_effect=changing_file,
                        )
                    )
                else:
                    real_codebook = cli_module._secure_codebook_capture
                    codebook_calls = 0

                    def changing_codebook(version: str) -> dict[str, object]:
                        nonlocal codebook_calls
                        codebook_calls += 1
                        captured = real_codebook(version)
                        if codebook_calls > 1:
                            captured = copy.deepcopy(captured)
                            captured["identity"] = tuple(captured["identity"]) + (999,)
                        return captured

                    stack.enter_context(
                        patch.object(
                            cli_module,
                            "_secure_codebook_capture",
                            side_effect=changing_codebook,
                        )
                    )
                with stack, contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(
                    ValueError, "изменились во время импорта"
                ):
                    cli_module.cmd_quality_coding_audit_review_import(args)
                self.assertFalse(destination.exists())
                self.assertEqual([], list(root.glob(".must-not-exist.staging-*")))

    def test_pre_rename_directory_fsync_failure_preserves_staging_for_quarantine(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "pre-commit-failure"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_fsync_directory = cli_module._fsync_directory
            fsync_calls = 0

            def fail_initial_staging_fsync(path: Path | int) -> None:
                nonlocal fsync_calls
                fsync_calls += 1
                if fsync_calls == 1:
                    raise OSError("имитация отказа fsync до публикации")
                real_fsync_directory(path)

            with (
                patch.object(
                    cli_module,
                    "_fsync_directory",
                    side_effect=fail_initial_staging_fsync,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertTrue(stderr.getvalue().startswith("Ошибка: "), stderr.getvalue())
            self.assertFalse(destination.exists())
            self.assertEqual(
                1,
                len(list(root.glob(".pre-commit-failure.staging-*"))),
            )
            self.assertIn(
                "автоматическое удаление файлов или самой папки намеренно не выполняется",
                stderr.getvalue(),
            )
            self.assertIn("системному администратору", stderr.getvalue())

    def test_precommit_close_interrupt_cannot_mask_partial_write_quarantine(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "partial-write-close-interrupt"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_write = os.write
            real_close = os.close
            created_descriptor: int | None = None
            close_interrupted = False

            def write_prefix_then_fail(descriptor: int, content: bytes) -> int:
                nonlocal created_descriptor
                if created_descriptor is None:
                    created_descriptor = descriptor
                    prefix_length = max(1, len(content) // 2)
                    real_write(descriptor, content[:prefix_length])
                    raise OSError("имитация отказа после частичной записи")
                return real_write(descriptor, content)

            def close_then_interrupt(descriptor: int) -> None:
                nonlocal close_interrupted
                real_close(descriptor)
                if descriptor == created_descriptor and not close_interrupted:
                    close_interrupted = True
                    raise KeyboardInterrupt(
                        "имитация прерывания после закрытия созданного файла"
                    )

            with (
                patch.object(cli_module.os, "write", side_effect=write_prefix_then_fail),
                patch.object(cli_module.os, "close", side_effect=close_then_interrupt),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            staging_paths = list(
                root.glob(".partial-write-close-interrupt.staging-*")
            )
            self.assertTrue(close_interrupted)
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertFalse(destination.exists())
            self.assertEqual(1, len(staging_paths))
            created_files = list(staging_paths[0].iterdir())
            self.assertEqual(1, len(created_files))
            self.assertGreater(created_files[0].stat().st_size, 0)
            staging_stat = staging_paths[0].stat()
            file_stat = created_files[0].stat()
            diagnostic = stderr.getvalue()
            self.assertIn("Очистка временной публикации", diagnostic)
            self.assertIn(
                f"устройство временной папки {staging_stat.st_dev}, "
                f"inode {staging_stat.st_ino}",
                diagnostic,
            )
            self.assertIn(
                f"устройство {file_stat.st_dev}, inode {file_stat.st_ino}",
                diagnostic,
            )
            self.assertIn("все имена и жёсткие ссылки", diagnostic)
            self.assertIn("поместить в карантин", diagnostic)
            self.assertNotIn("KeyboardInterrupt", diagnostic)

    def test_precommit_bookkeeping_interrupt_cannot_mask_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "bookkeeping-interrupt"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_stat = os.stat
            precommit_failed = False
            bookkeeping_interrupted = False

            def fail_precommit_assert(*args: object, **kwargs: object) -> None:
                nonlocal precommit_failed
                precommit_failed = True
                raise OSError("имитация отказа до переноса")

            def interrupt_cleanup_stat(
                path: str | bytes | int | os.PathLike[str],
                *args: object,
                **kwargs: object,
            ) -> os.stat_result:
                nonlocal bookkeeping_interrupted
                if (
                    precommit_failed
                    and path == destination.name
                    and kwargs.get("dir_fd") is not None
                ):
                    bookkeeping_interrupted = True
                    raise SystemExit("имитация прерывания cleanup stat")
                return real_stat(path, *args, **kwargs)

            with (
                patch.object(
                    cli_module,
                    "_assert_published_audit_bundle",
                    side_effect=fail_precommit_assert,
                ),
                patch.object(
                    cli_module.os,
                    "stat",
                    side_effect=interrupt_cleanup_stat,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            staging_paths = list(root.glob(".bookkeeping-interrupt.staging-*"))
            self.assertTrue(precommit_failed)
            self.assertTrue(bookkeeping_interrupted)
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertFalse(destination.exists())
            self.assertEqual(1, len(staging_paths))
            self.assertEqual(OUTPUT_FILES, {path.name for path in staging_paths[0].iterdir()})
            diagnostic = stderr.getvalue()
            self.assertIn("Очистка временной публикации", diagnostic)
            self.assertIn("Остановите автоматику", diagnostic)
            self.assertIn("поместить в карантин", diagnostic)
            self.assertNotIn("SystemExit", diagnostic)

    def test_staging_setup_open_and_fchmod_failures_preserve_quarantine_entry(
        self,
    ) -> None:
        for failure in ("open", "fchmod"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                destination = root / f"setup-{failure}"
                files = {"result.json": b"{}\n"}
                stack = contextlib.ExitStack()
                if failure == "open":
                    real_open = os.open

                    def fail_staging_open(
                        path: str | bytes | int,
                        flags: int,
                        *args: object,
                        **kwargs: object,
                    ) -> int:
                        if isinstance(path, str) and ".staging-" in path:
                            raise OSError("имитация отказа открытия staging")
                        return real_open(path, flags, *args, **kwargs)

                    stack.enter_context(
                        patch.object(
                            cli_module.os,
                            "open",
                            side_effect=fail_staging_open,
                        )
                    )
                else:
                    stack.enter_context(
                        patch.object(
                            cli_module.os,
                            "fchmod",
                            side_effect=OSError("имитация отказа fchmod"),
                        )
                    )
                with stack, self.assertRaisesRegex(
                    OSError,
                    "Очистка временной публикации не подтверждена",
                ) as raised:
                    cli_module._publish_new_audit_bundle(destination, files)
                self.assertFalse(destination.exists())
                self.assertEqual(
                    1,
                    len(list(root.glob(f".{destination.name}.staging-*"))),
                )
                diagnostic = str(raised.exception)
                self.assertIn("намеренно не выполняется", diagnostic)
                self.assertIn("прежнее имя записи", diagnostic)

    def test_failed_staging_open_never_removes_replacement_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "open-replacement"
            moved_original = root / "moved-original-staging"
            files = {"result.json": b"{}\n"}
            real_open = os.open
            replacement: Path | None = None

            def replace_before_failed_open(
                path: str | bytes | int,
                flags: int,
                *args: object,
                **kwargs: object,
            ) -> int:
                nonlocal replacement
                if isinstance(path, str) and ".staging-" in path:
                    replacement = root / path
                    os.rename(replacement, moved_original)
                    os.mkdir(replacement, 0o700)
                    raise OSError("имитация отказа после подмены имени staging")
                return real_open(path, flags, *args, **kwargs)

            with (
                patch.object(
                    cli_module.os,
                    "open",
                    side_effect=replace_before_failed_open,
                ),
                self.assertRaisesRegex(
                    OSError,
                    "Очистка временной публикации не подтверждена",
                ) as raised,
            ):
                cli_module._publish_new_audit_bundle(destination, files)

            assert replacement is not None
            self.assertTrue(moved_original.is_dir())
            self.assertTrue(replacement.is_dir())
            self.assertEqual([], list(replacement.iterdir()))
            self.assertFalse(destination.exists())
            diagnostic = str(raised.exception)
            self.assertIn("идентификатор временной папки получить не удалось", diagnostic)
            self.assertIn("намеренно не выполняется", diagnostic)

    def test_rename_then_helper_error_preserves_complete_published_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "rename-return-ambiguous"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_rename = cli_module._atomic_rename_no_replace_at

            def rename_then_raise(*args: object, **kwargs: object) -> None:
                real_rename(*args, **kwargs)
                raise OSError("имитация ошибки после выполненного rename")

            with (
                patch.object(
                    cli_module,
                    "_atomic_rename_no_replace_at",
                    side_effect=rename_then_raise,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(OUTPUT_FILES, {path.name for path in destination.iterdir()})
            self.assertTrue(all((destination / name).read_bytes() for name in OUTPUT_FILES))
            self.assertIn("Состояние публикации", stderr.getvalue())
            self.assertIn("не повторяйте команду", stderr.getvalue())

    def test_post_publish_stdout_write_or_flush_failure_preserves_output(self) -> None:
        class FlushFailure(io.StringIO):
            def flush(self) -> None:
                raise BrokenPipeError("имитация отказа flush")

        class ShortWrite(io.StringIO):
            def write(self, value: str) -> int:
                prefix = value[: max(1, len(value) // 2)]
                return super().write(prefix)

        for phase in ("write", "short-write", "flush"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = self._write_secondary(
                    root, self._secondary_records(bundle)
                )
                destination = root / f"confirmation-{phase}"
                stdout = (
                    io.StringIO()
                    if phase == "write"
                    else ShortWrite()
                    if phase == "short-write"
                    else FlushFailure()
                )
                stderr = io.StringIO()
                stack = contextlib.ExitStack()
                if phase == "write":
                    stack.enter_context(
                        patch.object(
                            cli_module,
                            "_write_stdout_line",
                            side_effect=BrokenPipeError(
                                "имитация закрытого стандартного вывода"
                            ),
                        )
                    )
                with (
                    stack,
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main(
                        self._import_arguments(
                            bundle,
                            secondary,
                            destination,
                            expected,
                        )
                    )

                self.assertEqual(2, return_code)
                self.assertEqual(
                    OUTPUT_FILES,
                    {path.name for path in destination.iterdir()},
                )
                if phase == "write":
                    self.assertEqual("", stdout.getvalue())
                elif phase == "short-write":
                    self.assertTrue(stdout.getvalue().startswith("{"))
                    self.assertNotIn("\n", stdout.getvalue())
                else:
                    apparent_success = json.loads(stdout.getvalue())
                    self.assertEqual(
                        "coding_audit_review_import_receipt",
                        apparent_success["artifact_type"],
                    )
                diagnostic = stderr.getvalue()
                self.assertIn("подтверждение", diagnostic)
                self.assertIn("пустым или частичным", diagnostic)
                self.assertIn("считайте его недействительным", diagnostic)
                self.assertIn("другую отсутствующую соседнюю папку", diagnostic)
                self.assertIn("побайтно сравните оба каталога", diagnostic)
                self.assertIn("флаги дальнейших действий", diagnostic)

    def test_confirmation_recovery_survives_neutralizer_interrupt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "confirmation-neutralizer-interrupt"
            stdout = io.StringIO()
            stderr = io.StringIO()

            with (
                patch.object(
                    cli_module,
                    "_write_stdout_line",
                    side_effect=BrokenPipeError("имитация отказа стандартного вывода"),
                ),
                patch.object(
                    cli_module,
                    "_neutralize_stdout_after_delivery_failure",
                    side_effect=KeyboardInterrupt(
                        "имитация повторного прерывания нейтрализации"
                    ),
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            diagnostic = stderr.getvalue()
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(
                OUTPUT_FILES,
                {path.name for path in destination.iterdir()},
            )
            self.assertIn("машиночитаемое подтверждение", diagnostic)
            self.assertIn("пустым или частичным", diagnostic)
            self.assertIn("Остановите автоматику", diagnostic)
            self.assertIn("не повторяйте команду", diagnostic)
            self.assertNotIn("KeyboardInterrupt", diagnostic)

    def test_import_interrupt_after_inner_return_uses_publisher_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "inner-return-interrupt"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_inner = cli_module._cmd_quality_coding_audit_review_import

            def publish_then_interrupt(
                *args: object, **kwargs: object
            ) -> tuple[str, tuple[int, int]]:
                result = real_inner(*args, **kwargs)
                publication_state = kwargs["publication_state"]
                self.assertEqual(1, len(publication_state))
                raise KeyboardInterrupt("имитация прерывания после возврата inner")

            with (
                patch.object(
                    cli_module,
                    "_cmd_quality_coding_audit_review_import",
                    side_effect=publish_then_interrupt,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            destination_stat = os.stat(destination)
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(OUTPUT_FILES, {path.name for path in destination.iterdir()})
            diagnostic = stderr.getvalue()
            self.assertIn("завершение команды после публикации", diagnostic)
            self.assertIn("стандартный вывод ещё не формировался", diagnostic)
            self.assertIn(f"устройство каталога {destination_stat.st_dev}", diagnostic)
            self.assertIn(f"inode {destination_stat.st_ino}", diagnostic)
            self.assertIn("Остановите автоматику", diagnostic)
            self.assertNotIn("KeyboardInterrupt", diagnostic)

    def test_interrupt_after_full_confirmation_before_return_invalidates_stdout(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "after-full-confirmation-interrupt"
            stdout = io.StringIO()
            stderr = io.StringIO()

            with (
                patch.object(
                    cli_module,
                    "_complete_published_command",
                    side_effect=SystemExit(
                        "имитация выхода после полного flush до возврата команды"
                    ),
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            apparent_success = json.loads(stdout.getvalue())
            self.assertEqual(2, return_code)
            self.assertEqual(
                "coding_audit_review_import_receipt",
                apparent_success["artifact_type"],
            )
            self.assertEqual(OUTPUT_FILES, {path.name for path in destination.iterdir()})
            diagnostic = stderr.getvalue()
            self.assertIn("после начала передачи", diagnostic)
            self.assertIn("выглядеть как полная строка JSON", diagnostic)
            self.assertIn("во всех случаях считайте его недействительным", diagnostic)
            self.assertIn("Остановите автоматику", diagnostic)
            self.assertNotIn("SystemExit", diagnostic)

    def test_parent_close_failure_after_publish_has_distinct_empty_stdout_route(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "parent-close-failure"
            stdout = io.StringIO()
            stderr = io.StringIO()

            def close_then_raise(descriptor: int) -> None:
                os.close(descriptor)
                raise OSError("имитация отказа close")

            with (
                patch.object(
                    cli_module,
                    "_close_command_parent_descriptor",
                    side_effect=close_then_raise,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(
                        bundle,
                        secondary,
                        destination,
                        expected,
                    )
                )

            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(
                OUTPUT_FILES,
                {path.name for path in destination.iterdir()},
            )
            diagnostic = stderr.getvalue()
            self.assertIn("завершение команды после публикации", diagnostic)
            self.assertIn("стандартный вывод ещё не формировался", diagnostic)
            self.assertIn("код 2 не доказывает отсутствия каталога", diagnostic)
            self.assertNotIn("пустым или частичным", diagnostic)

    def test_published_file_or_directory_close_failure_blocks_confirmation(self) -> None:
        for target_kind in ("file", "directory"):
            with self.subTest(target_kind=target_kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = self._write_secondary(
                    root, self._secondary_records(bundle)
                )
                destination = root / f"published-close-{target_kind}"
                stdout = io.StringIO()
                stderr = io.StringIO()
                failed = False

                def close_selected_descriptor(descriptor: int) -> None:
                    nonlocal failed
                    descriptor_stat = os.fstat(descriptor)
                    is_directory = stat.S_ISDIR(descriptor_stat.st_mode)
                    os.close(descriptor)
                    if not failed and is_directory == (target_kind == "directory"):
                        failed = True
                        raise OSError("имитация отказа close после публикации")

                with (
                    patch.object(
                        cli_module,
                        "_close_published_descriptor",
                        side_effect=close_selected_descriptor,
                    ),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main(
                        self._import_arguments(
                            bundle,
                            secondary,
                            destination,
                            expected,
                        )
                    )

                self.assertTrue(failed)
                self.assertEqual(2, return_code)
                self.assertEqual("", stdout.getvalue())
                self.assertEqual(
                    OUTPUT_FILES,
                    {path.name for path in destination.iterdir()},
                )
                diagnostic = stderr.getvalue()
                self.assertIn("завершение команды после публикации", diagnostic)
                self.assertIn("стандартный вывод ещё не формировался", diagnostic)
                self.assertIn("код 2 не доказывает отсутствия каталога", diagnostic)

    def test_keyboard_interrupt_during_published_descriptor_close_is_classified(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "published-close-interrupt"
            stdout = io.StringIO()
            stderr = io.StringIO()
            interrupted = False

            def close_then_interrupt(descriptor: int) -> None:
                nonlocal interrupted
                os.close(descriptor)
                if not interrupted:
                    interrupted = True
                    raise KeyboardInterrupt(
                        "имитация прерывания закрытия после публикации"
                    )

            with (
                patch.object(
                    cli_module,
                    "_close_published_descriptor",
                    side_effect=close_then_interrupt,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            diagnostic = stderr.getvalue()
            self.assertTrue(interrupted)
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(
                OUTPUT_FILES,
                {path.name for path in destination.iterdir()},
            )
            self.assertIn("завершение команды после публикации", diagnostic)
            self.assertIn("Координаты результата", diagnostic)
            self.assertIn("Остановите автоматику", diagnostic)
            self.assertIn("не повторяйте команду", diagnostic)

    def test_closed_stdout_pipe_keeps_classified_exit_code_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "closed-stdout-pipe"
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(REPO / SCRIPT),
                    *self._import_arguments(
                        bundle,
                        secondary,
                        destination,
                        expected,
                    ),
                ],
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            assert process.stdout is not None
            assert process.stderr is not None
            process.stdout.close()
            try:
                return_code = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                self.fail("Команда зависла после закрытия стандартного вывода.")
            diagnostic = process.stderr.read()
            process.stderr.close()

            self.assertEqual(2, return_code, diagnostic)
            self.assertEqual(
                OUTPUT_FILES,
                {path.name for path in destination.iterdir()},
            )
            self.assertIn("машиночитаемое подтверждение", diagnostic)
            self.assertIn("считайте его недействительным", diagnostic)
            self.assertNotIn("Exception ignored", diagnostic)
            self.assertNotIn("BrokenPipeError", diagnostic)

    def test_precommit_failure_does_not_attempt_cleanup_fsync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "no-cleanup-fsync"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_fsync_directory = cli_module._fsync_directory
            fsync_calls = 0

            def track_fsync(path: Path | int) -> None:
                nonlocal fsync_calls
                fsync_calls += 1
                real_fsync_directory(path)

            with (
                patch.object(
                    cli_module,
                    "_assert_published_audit_bundle",
                    side_effect=ValueError("имитация отказа до переноса"),
                ),
                patch.object(
                    cli_module,
                    "_fsync_directory",
                    side_effect=track_fsync,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(1, fsync_calls)
            self.assertFalse(destination.exists())
            self.assertEqual(
                1,
                len(list(root.glob(".no-cleanup-fsync.staging-*"))),
            )
            self.assertIn("намеренно не выполняется", stderr.getvalue())

    @unittest.skipUnless(os.name == "posix", "POSIX hardlinks required")
    def test_cleanup_detects_sensitive_hardlink_outside_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "hardlink-escape"
            escaped = root / "escaped-sensitive-copy"
            sensitive_content = b"sensitive audit result\n"
            files = {"result.json": sensitive_content}
            real_verify = cli_module._assert_published_audit_bundle
            linked = False

            def link_outside_then_fail(
                parent_descriptor: int,
                destination_name: str,
                expected_directory_identity: tuple[int, int],
                expected_files: dict[str, bytes],
                expected_file_identities: dict[str, tuple[int, int]] | None = None,
            ) -> None:
                nonlocal linked
                if not linked and ".staging-" in destination_name:
                    linked = True
                    os.link(
                        root / destination_name / "result.json",
                        escaped,
                        follow_symlinks=False,
                    )
                    raise ValueError("имитация отказа после создания hardlink")
                real_verify(
                    parent_descriptor,
                    destination_name,
                    expected_directory_identity,
                    expected_files,
                    expected_file_identities,
                )

            with (
                patch.object(
                    cli_module,
                    "_assert_published_audit_bundle",
                    side_effect=link_outside_then_fail,
                ),
                self.assertRaisesRegex(
                    OSError,
                    "Очистка временной публикации не подтверждена",
                ) as raised,
            ):
                cli_module._publish_new_audit_bundle(destination, files)

            diagnostic = str(raised.exception)
            self.assertFalse(destination.exists())
            self.assertEqual(sensitive_content, escaped.read_bytes())
            self.assertEqual(
                1,
                len(list(root.glob(".hardlink-escape.staging-*"))),
            )
            staging_file = next(root.glob(".hardlink-escape.staging-*/result.json"))
            self.assertEqual(staging_file.stat().st_ino, escaped.stat().st_ino)
            self.assertIn("копия через жёсткую ссылку", diagnostic)
            self.assertIn("result.json", diagnostic)
            self.assertIn("inode", diagnostic)
            self.assertIn("все имена и жёсткие ссылки", diagnostic)
            self.assertIn("неучтённой", diagnostic)

    def test_precommit_failure_never_attempts_destructive_unlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "no-destructive-cleanup"
            sensitive_content = b"sensitive audit result\n"
            files = {"result.json": sensitive_content}

            with (
                patch.object(
                    cli_module,
                    "_assert_published_audit_bundle",
                    side_effect=ValueError("имитация отказа до переноса"),
                ),
                patch.object(
                    cli_module.os,
                    "unlink",
                    side_effect=AssertionError("unlink не должен вызываться"),
                ) as unlink_mock,
                patch.object(
                    cli_module.os,
                    "rmdir",
                    side_effect=AssertionError("rmdir не должен вызываться"),
                ) as rmdir_mock,
                self.assertRaisesRegex(
                    OSError,
                    "Очистка временной публикации не подтверждена",
                ) as raised,
            ):
                cli_module._publish_new_audit_bundle(destination, files)

            diagnostic = str(raised.exception)
            self.assertFalse(destination.exists())
            staging_file = next(
                root.glob(".no-destructive-cleanup.staging-*/result.json")
            )
            self.assertEqual(sensitive_content, staging_file.read_bytes())
            unlink_mock.assert_not_called()
            rmdir_mock.assert_not_called()
            self.assertIn("намеренно не выполняется", diagnostic)
            self.assertIn("inode", diagnostic)
            self.assertIn("все имена и жёсткие ссылки", diagnostic)

    @unittest.skipUnless(os.name == "posix", "POSIX inode checks required")
    def test_cleanup_never_unlinks_replacement_for_escaped_created_inode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "created-inode-replaced"
            escaped = root / "escaped-original"
            sensitive_content = b"sensitive audit result\n"
            replacement_content = b"replacement\n"
            files = {"result.json": sensitive_content}
            real_verify = cli_module._assert_published_audit_bundle
            replaced = False

            def replace_created_inode_then_verify(
                parent_descriptor: int,
                destination_name: str,
                expected_directory_identity: tuple[int, int],
                expected_files: dict[str, bytes],
                expected_file_identities: dict[str, tuple[int, int]] | None = None,
            ) -> None:
                nonlocal replaced
                if not replaced and ".staging-" in destination_name:
                    replaced = True
                    staging_file = root / destination_name / "result.json"
                    os.rename(staging_file, escaped)
                    staging_file.write_bytes(replacement_content)
                    os.chmod(staging_file, 0o600)
                real_verify(
                    parent_descriptor,
                    destination_name,
                    expected_directory_identity,
                    expected_files,
                    expected_file_identities,
                )

            with (
                patch.object(
                    cli_module,
                    "_assert_published_audit_bundle",
                    side_effect=replace_created_inode_then_verify,
                ),
                self.assertRaisesRegex(
                    OSError,
                    "Очистка временной публикации не подтверждена",
                ) as raised,
            ):
                cli_module._publish_new_audit_bundle(destination, files)

            staging_file = next(
                root.glob(".created-inode-replaced.staging-*/result.json")
            )
            self.assertFalse(destination.exists())
            self.assertEqual(sensitive_content, escaped.read_bytes())
            self.assertEqual(replacement_content, staging_file.read_bytes())
            self.assertNotEqual(escaped.stat().st_ino, staging_file.stat().st_ino)
            self.assertIn("inode", str(raised.exception))
            self.assertIn("неучтённой", str(raised.exception))

    def test_mutated_staging_is_preserved_for_quarantine(self) -> None:
        for case in ("extra-entry", "replaced-with-directory"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = self._write_secondary(
                    root, self._secondary_records(bundle)
                )
                destination = root / f"cleanup-{case}"
                stdout = io.StringIO()
                stderr = io.StringIO()
                real_verify = cli_module._assert_published_audit_bundle
                stack = contextlib.ExitStack()
                mutated = False

                def break_staging_before_rename(
                    parent_descriptor: int,
                    destination_name: str,
                    expected_directory_identity: tuple[int, int],
                    files: dict[str, bytes],
                    expected_file_identities: dict[str, tuple[int, int]] | None = None,
                ) -> None:
                    nonlocal mutated
                    if not mutated and ".staging-" in destination_name:
                        mutated = True
                        staging_descriptor = os.open(
                            destination_name,
                            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
                            dir_fd=parent_descriptor,
                        )
                        try:
                            if case == "extra-entry":
                                extra = os.open(
                                    "unexpected-entry",
                                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                    0o600,
                                    dir_fd=staging_descriptor,
                                )
                                os.close(extra)
                            else:
                                os.unlink(
                                    "audit-decisions.jsonl",
                                    dir_fd=staging_descriptor,
                                )
                                os.mkdir(
                                    "audit-decisions.jsonl",
                                    0o700,
                                    dir_fd=staging_descriptor,
                                )
                        finally:
                            os.close(staging_descriptor)
                    real_verify(
                        parent_descriptor,
                        destination_name,
                        expected_directory_identity,
                        files,
                        expected_file_identities,
                    )

                stack.enter_context(
                    patch.object(
                        cli_module,
                        "_assert_published_audit_bundle",
                        side_effect=break_staging_before_rename,
                    )
                )

                with (
                    stack,
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main(
                        self._import_arguments(
                            bundle, secondary, destination, expected
                        )
                    )

                diagnostic = stderr.getvalue()
                self.assertEqual(2, return_code)
                self.assertEqual("", stdout.getvalue())
                self.assertFalse(destination.exists())
                self.assertEqual(
                    1,
                    len(list(root.glob(f".{destination.name}.staging-*"))),
                )
                self.assertIn("Очистка временной публикации не подтверждена", diagnostic)
                self.assertIn("системному администратору", diagnostic)
                self.assertIn("не повторяйте команду", diagnostic)
                self.assertIn("временную копию неучтённой", diagnostic)

    def test_parent_path_change_before_rename_never_reports_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "parent-path-change-before-rename"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_check = cli_module._assert_parent_path_matches_descriptor
            check_calls = 0

            def fail_second_check(path: Path, descriptor: int) -> None:
                nonlocal check_calls
                check_calls += 1
                if check_calls == 2:
                    raise ValueError("имитация замены родительской папки")
                real_check(path, descriptor)

            with (
                patch.object(
                    cli_module,
                    "_assert_parent_path_matches_descriptor",
                    side_effect=fail_second_check,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertTrue(stderr.getvalue().startswith("Ошибка: "))
            self.assertFalse(destination.exists())
            self.assertEqual(
                1,
                len(list(root.glob(f".{destination.name}.staging-*"))),
            )
            self.assertIn(
                "Очистка временной публикации не подтверждена",
                stderr.getvalue(),
            )

    @unittest.skipUnless(os.name == "posix", "POSIX directory modes required")
    def test_parent_permission_flip_before_and_after_rename_never_succeeds(self) -> None:
        for phase in ("before", "after"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = self._write_secondary(
                    root, self._secondary_records(bundle)
                )
                destination = root / f"permission-flip-{phase}"
                stdout = io.StringIO()
                stderr = io.StringIO()
                stack = contextlib.ExitStack()
                if phase == "before":
                    real_check = cli_module._assert_parent_path_matches_descriptor
                    check_calls = 0

                    def chmod_during_final_parent_check(
                        path: Path, descriptor: int
                    ) -> None:
                        nonlocal check_calls
                        check_calls += 1
                        real_check(path, descriptor)
                        if check_calls == 2:
                            os.chmod(root, 0o777)

                    stack.enter_context(
                        patch.object(
                            cli_module,
                            "_assert_parent_path_matches_descriptor",
                            side_effect=chmod_during_final_parent_check,
                        )
                    )
                else:
                    real_rename = cli_module._atomic_rename_no_replace_at

                    def chmod_after_rename(*args: object, **kwargs: object) -> None:
                        real_rename(*args, **kwargs)
                        os.chmod(root, 0o777)

                    stack.enter_context(
                        patch.object(
                            cli_module,
                            "_atomic_rename_no_replace_at",
                            side_effect=chmod_after_rename,
                        )
                    )
                try:
                    with (
                        stack,
                        contextlib.redirect_stdout(stdout),
                        contextlib.redirect_stderr(stderr),
                    ):
                        return_code = cli_module.main(
                            self._import_arguments(
                                bundle, secondary, destination, expected
                            )
                        )
                    self.assertEqual(2, return_code)
                    self.assertEqual("", stdout.getvalue())
                    expected_error = (
                        "Очистка временной публикации"
                        if phase == "before"
                        else "защищённость"
                    )
                    self.assertIn(expected_error, stderr.getvalue())
                    self.assertEqual(phase == "after", destination.exists())
                finally:
                    os.chmod(root, 0o700)

    def test_destination_replacement_after_rename_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "destination-replaced"
            displaced_name = ".destination-replaced.original"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_rename = cli_module._atomic_rename_no_replace_at
            published_identity: tuple[int, int] | None = None

            def replace_after_rename(
                parent_descriptor: int,
                source_name: str,
                destination_name: str,
                **kwargs: object,
            ) -> None:
                nonlocal published_identity
                real_rename(
                    parent_descriptor,
                    source_name,
                    destination_name,
                    **kwargs,
                )
                published_stat = os.stat(
                    destination_name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                published_identity = (published_stat.st_dev, published_stat.st_ino)
                os.rename(
                    destination_name,
                    displaced_name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                )
                os.mkdir(destination_name, 0o700, dir_fd=parent_descriptor)

            with (
                patch.object(
                    cli_module,
                    "_atomic_rename_no_replace_at",
                    side_effect=replace_after_rename,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            diagnostic = stderr.getvalue()
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual([], list(destination.iterdir()))
            self.assertEqual(
                OUTPUT_FILES,
                {path.name for path in (root / displaced_name).iterdir()},
            )
            self.assertIsNotNone(published_identity)
            self.assertIn("Идентификатор самого опубликованного каталога", diagnostic)
            self.assertIn(f"inode {published_identity[1]}", diagnostic)
            self.assertIn("карантин", diagnostic)

    @unittest.skipUnless(os.name == "posix", "POSIX hardlinks required")
    def test_post_rename_hardlink_requires_every_link_to_be_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / "published-hardlink"
            escaped = root / "escaped-published-copy"
            sensitive_content = b"sensitive published result\n"
            files = {"result.json": sensitive_content}
            real_rename = cli_module._atomic_rename_no_replace_at

            def rename_then_link(
                parent_descriptor: int,
                source_name: str,
                destination_name: str,
                **kwargs: object,
            ) -> None:
                real_rename(
                    parent_descriptor,
                    source_name,
                    destination_name,
                    **kwargs,
                )
                published_descriptor = os.open(
                    destination_name,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
                    dir_fd=parent_descriptor,
                )
                try:
                    os.link(
                        "result.json",
                        escaped.name,
                        src_dir_fd=published_descriptor,
                        dst_dir_fd=parent_descriptor,
                        follow_symlinks=False,
                    )
                finally:
                    os.close(published_descriptor)

            with (
                patch.object(
                    cli_module,
                    "_atomic_rename_no_replace_at",
                    side_effect=rename_then_link,
                ),
                self.assertRaisesRegex(
                    OSError,
                    "Состояние публикации после атомарного переноса не подтверждено",
                ) as raised,
            ):
                cli_module._publish_new_audit_bundle(destination, files)

            diagnostic = str(raised.exception)
            self.assertEqual(sensitive_content, escaped.read_bytes())
            self.assertEqual(sensitive_content, (destination / "result.json").read_bytes())
            self.assertEqual(
                escaped.stat().st_ino,
                (destination / "result.json").stat().st_ino,
            )
            self.assertIn("все имена и жёсткие ссылки", diagnostic)
            self.assertIn("result.json", diagnostic)
            self.assertIn("inode", diagnostic)
            self.assertIn("полностью учесть", diagnostic)
            self.assertIn("чувствительную копию неучтённой", diagnostic)

    def test_published_file_mutation_inside_rename_never_reports_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "published-file-mutated"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_rename = cli_module._atomic_rename_no_replace_at

            def mutate_after_rename(
                parent_descriptor: int,
                source_name: str,
                destination_name: str,
                **kwargs: object,
            ) -> None:
                real_rename(
                    parent_descriptor,
                    source_name,
                    destination_name,
                    **kwargs,
                )
                output_descriptor = os.open(
                    destination_name,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
                    dir_fd=parent_descriptor,
                )
                try:
                    child = os.open(
                        "audit-decisions.jsonl",
                        os.O_WRONLY | os.O_TRUNC,
                        dir_fd=output_descriptor,
                    )
                    try:
                        os.write(child, b"changed-after-rename\n")
                    finally:
                        os.close(child)
                finally:
                    os.close(output_descriptor)

            with (
                patch.object(
                    cli_module,
                    "_atomic_rename_no_replace_at",
                    side_effect=mutate_after_rename,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertTrue(destination.exists())
            self.assertIn("Состояние публикации", stderr.getvalue())
            self.assertIn("карантин", stderr.getvalue())

    def test_keyboard_interrupt_in_second_post_rename_assert_is_classified(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "post-rename-interrupt"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_assert = cli_module._assert_published_audit_bundle
            assert_calls = 0

            def interrupt_second_post_rename_assert(
                *args: object, **kwargs: object
            ) -> None:
                nonlocal assert_calls
                assert_calls += 1
                if assert_calls == 3:
                    raise KeyboardInterrupt(
                        "имитация прерывания второй проверки после публикации"
                    )
                real_assert(*args, **kwargs)

            with (
                patch.object(
                    cli_module,
                    "_assert_published_audit_bundle",
                    side_effect=interrupt_second_post_rename_assert,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            diagnostic = stderr.getvalue()
            self.assertEqual(3, assert_calls)
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(
                OUTPUT_FILES,
                {path.name for path in destination.iterdir()},
            )
            self.assertTrue(all((destination / name).read_bytes() for name in OUTPUT_FILES))
            self.assertIn(
                "Состояние публикации после атомарного переноса не подтверждено",
                diagnostic,
            )
            self.assertIn("Координаты поиска в файловой системе", diagnostic)
            self.assertIn("Остановите автоматику", diagnostic)
            self.assertIn("не повторяйте команду", diagnostic)
            self.assertIn("поместить в карантин", diagnostic)

    def test_system_exit_in_post_rename_fsync_is_classified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "post-rename-fsync-exit"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_fsync_directory = cli_module._fsync_directory
            fsync_calls = 0

            def exit_during_parent_fsync(path: Path | int) -> None:
                nonlocal fsync_calls
                fsync_calls += 1
                if fsync_calls == 2:
                    raise SystemExit("имитация выхода во время fsync публикации")
                real_fsync_directory(path)

            with (
                patch.object(
                    cli_module,
                    "_fsync_directory",
                    side_effect=exit_during_parent_fsync,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            diagnostic = stderr.getvalue()
            self.assertEqual(2, fsync_calls)
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(
                OUTPUT_FILES,
                {path.name for path in destination.iterdir()},
            )
            self.assertIn("Состояние публикации", diagnostic)
            self.assertIn("Координаты поиска в файловой системе", diagnostic)
            self.assertIn("Остановите автоматику", diagnostic)
            self.assertIn("не повторяйте команду", diagnostic)

    def test_recovery_uses_cached_parent_identity_after_persistent_fstat_fault(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root_stat = root.stat()
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "parent-fstat-fault"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_rename = cli_module._atomic_rename_no_replace_at
            real_fstat = os.fstat
            poisoned_parent_descriptor: int | None = None
            parent_fstat_calls = 0

            def rename_then_poison_parent_fstat(
                parent_descriptor: int,
                source_name: str,
                destination_name: str,
                **kwargs: object,
            ) -> None:
                nonlocal poisoned_parent_descriptor
                real_rename(
                    parent_descriptor,
                    source_name,
                    destination_name,
                    **kwargs,
                )
                poisoned_parent_descriptor = parent_descriptor

            def first_parent_fstat_only(descriptor: int) -> os.stat_result:
                nonlocal parent_fstat_calls
                if descriptor == poisoned_parent_descriptor:
                    parent_fstat_calls += 1
                    if parent_fstat_calls > 1:
                        raise OSError("имитация постоянного отказа parent fstat")
                return real_fstat(descriptor)

            with (
                patch.object(
                    cli_module,
                    "_atomic_rename_no_replace_at",
                    side_effect=rename_then_poison_parent_fstat,
                ),
                patch.object(cli_module.os, "fstat", side_effect=first_parent_fstat_only),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            diagnostic = stderr.getvalue()
            self.assertEqual(2, parent_fstat_calls)
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(
                OUTPUT_FILES,
                {path.name for path in destination.iterdir()},
            )
            self.assertTrue(all((destination / name).read_bytes() for name in OUTPUT_FILES))
            self.assertIn("Состояние публикации", diagnostic)
            self.assertIn(
                f"устройство {root_stat.st_dev}, inode родительской папки "
                f"{root_stat.st_ino}",
                diagnostic,
            )
            self.assertIn("Остановите автоматику", diagnostic)
            self.assertIn("поместить в карантин", diagnostic)
            self.assertIn("не повторяйте команду", diagnostic)

    def test_parent_move_after_rename_reports_recovery_identity_and_forbids_retry(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            moved_root = root.parent / f"{root.name}-moved"
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))
            destination = root / "parent-moved-after-rename"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_rename = cli_module._atomic_rename_no_replace_at

            def rename_then_move_parent(*args: object, **kwargs: object) -> None:
                real_rename(*args, **kwargs)
                root.rename(moved_root)

            try:
                with (
                    patch.object(
                        cli_module,
                        "_atomic_rename_no_replace_at",
                        side_effect=rename_then_move_parent,
                    ),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main(
                        self._import_arguments(bundle, secondary, destination, expected)
                    )

                diagnostic = stderr.getvalue()
                moved_destination = moved_root / destination.name
                self.assertEqual(2, return_code)
                self.assertEqual("", stdout.getvalue())
                self.assertFalse(destination.exists())
                self.assertEqual(
                    OUTPUT_FILES,
                    {path.name for path in moved_destination.iterdir()},
                )
                self.assertIn("Состояние публикации", diagnostic)
                self.assertIn("устройство ", diagnostic)
                self.assertIn("inode родительской папки", diagnostic)
                self.assertIn(f'имя записи "{destination.name}"', diagnostic)
                self.assertIn("сохраните все входы неизменными", diagnostic)
                self.assertIn("не повторяйте команду", diagnostic)
                self.assertIn("не передавайте результат дальше", diagnostic)
                self.assertIn("Каждую найденную копию", diagnostic)
                self.assertIn("поместить в карантин", diagnostic)
                self.assertIn("чувствительную копию неучтённой", diagnostic)
                self.assertNotIn("сравните оба результата побайтно", diagnostic)
            finally:
                if moved_root.exists() and not root.exists():
                    moved_root.rename(root)

    def test_parent_move_during_parent_fsync_is_always_location_uncertain(
        self,
    ) -> None:
        for fsync_fails in (False, True):
            with self.subTest(fsync_fails=fsync_fails), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                moved_root = root.parent / f"{root.name}-moved-during-fsync"
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = self._write_secondary(
                    root, self._secondary_records(bundle)
                )
                destination = root / "parent-moved-during-fsync"
                stdout = io.StringIO()
                stderr = io.StringIO()
                real_fsync_directory = cli_module._fsync_directory
                fsync_calls = 0

                def move_during_parent_fsync(path: Path | int) -> None:
                    nonlocal fsync_calls
                    fsync_calls += 1
                    if fsync_calls != 2:
                        real_fsync_directory(path)
                        return
                    if not fsync_fails:
                        real_fsync_directory(path)
                    root.rename(moved_root)
                    if fsync_fails:
                        raise OSError("имитация отказа fsync после перемещения")

                try:
                    with (
                        patch.object(
                            cli_module,
                            "_fsync_directory",
                            side_effect=move_during_parent_fsync,
                        ),
                        contextlib.redirect_stdout(stdout),
                        contextlib.redirect_stderr(stderr),
                    ):
                        return_code = cli_module.main(
                            self._import_arguments(
                                bundle, secondary, destination, expected
                            )
                        )

                    diagnostic = stderr.getvalue()
                    moved_destination = moved_root / destination.name
                    self.assertEqual(2, return_code)
                    self.assertEqual("", stdout.getvalue())
                    self.assertEqual(
                        OUTPUT_FILES,
                        {path.name for path in moved_destination.iterdir()},
                    )
                    self.assertIn("Состояние публикации", diagnostic)
                    self.assertIn("inode родительской папки", diagnostic)
                    self.assertIn("не повторяйте команду", diagnostic)
                    self.assertNotIn("Долговечность публикации", diagnostic)
                    self.assertNotIn("сравните оба результата побайтно", diagnostic)
                finally:
                    if moved_root.exists() and not root.exists():
                        moved_root.rename(root)

    def test_destination_replacement_during_parent_fsync_is_location_uncertain(
        self,
    ) -> None:
        for fsync_fails in (False, True):
            with self.subTest(fsync_fails=fsync_fails), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
                secondary = self._write_secondary(
                    root, self._secondary_records(bundle)
                )
                destination = root / "destination-replaced-during-fsync"
                displaced_name = (
                    f".{destination.name}.original-{int(fsync_fails)}"
                )
                stdout = io.StringIO()
                stderr = io.StringIO()
                real_fsync_directory = cli_module._fsync_directory
                fsync_calls = 0

                def replace_during_parent_fsync(path: Path | int) -> None:
                    nonlocal fsync_calls
                    fsync_calls += 1
                    if fsync_calls != 2:
                        real_fsync_directory(path)
                        return
                    if not isinstance(path, int):
                        raise AssertionError("ожидался дескриптор родительской папки")
                    if not fsync_fails:
                        real_fsync_directory(path)
                    os.rename(
                        destination.name,
                        displaced_name,
                        src_dir_fd=path,
                        dst_dir_fd=path,
                    )
                    os.mkdir(destination.name, 0o700, dir_fd=path)
                    if fsync_fails:
                        raise OSError("имитация отказа fsync после замены результата")

                with (
                    patch.object(
                        cli_module,
                        "_fsync_directory",
                        side_effect=replace_during_parent_fsync,
                    ),
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    return_code = cli_module.main(
                        self._import_arguments(
                            bundle, secondary, destination, expected
                        )
                    )

                diagnostic = stderr.getvalue()
                self.assertEqual(2, return_code)
                self.assertEqual("", stdout.getvalue())
                self.assertEqual([], list(destination.iterdir()))
                self.assertEqual(
                    OUTPUT_FILES,
                    {path.name for path in (root / displaced_name).iterdir()},
                )
                self.assertIn("Идентификатор самого опубликованного каталога", diagnostic)
                self.assertIn("не повторяйте команду", diagnostic)
                self.assertNotIn("Долговечность публикации", diagnostic)

    def test_post_rename_parent_fsync_failure_reports_ambiguity_and_keeps_full_output(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, bundle, expected = self._prepare_bundle(root, candidate_count=1)
            secondary = self._write_secondary(root, self._secondary_records(bundle))

            reference = root / "reference-import"
            completed = self._run(
                REPO / SCRIPT,
                self._import_arguments(bundle, secondary, reference, expected),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            expected_files = {
                name: (reference / name).read_bytes() for name in OUTPUT_FILES
            }

            destination = root / "post-commit-failure"
            stdout = io.StringIO()
            stderr = io.StringIO()
            real_fsync_directory = cli_module._fsync_directory
            fsync_calls = 0

            def fail_parent_fsync(path: Path | int) -> None:
                nonlocal fsync_calls
                fsync_calls += 1
                if fsync_calls == 2:
                    raise OSError("имитация отказа fsync родительской папки")
                real_fsync_directory(path)

            with (
                patch.object(
                    cli_module,
                    "_fsync_directory",
                    side_effect=fail_parent_fsync,
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                return_code = cli_module.main(
                    self._import_arguments(bundle, secondary, destination, expected)
                )

            diagnostic = stderr.getvalue()
            self.assertEqual(2, return_code)
            self.assertEqual("", stdout.getvalue())
            self.assertIn(
                "Долговечность публикации не подтверждена",
                diagnostic,
            )
            self.assertIn("полный каталог уже может быть виден", diagnostic)
            self.assertIn("не удаляйте его автоматически", diagnostic)
            self.assertIn("повторите эту команду с теми же неизменными входами", diagnostic)
            self.assertIn("сравните оба результата побайтно", diagnostic)
            self.assertEqual(OUTPUT_FILES, {path.name for path in destination.iterdir()})
            self.assertEqual(0o700, stat.S_IMODE(destination.stat().st_mode))
            self.assertEqual(
                expected_files,
                {name: (destination / name).read_bytes() for name in OUTPUT_FILES},
            )
            for path in destination.iterdir():
                self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
            self.assertEqual([], list(root.glob(".post-commit-failure.staging-*")))


if __name__ == "__main__":
    unittest.main()
