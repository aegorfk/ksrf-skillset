from __future__ import annotations

import copy
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError

from judicial_meaning.analysis import screen_text
import judicial_meaning.cli as cli_module
from judicial_meaning.cli import (
    _atomic_rename_no_replace,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)
from judicial_meaning.plan import freeze_plan
from judicial_meaning.practice_quality import (
    AUDIT_CODING_RECORD_FIELDS,
    canonical_digest,
)


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO = SKILL_ROOT.parents[1]
SCRIPT = Path("skills/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py")
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
BUNDLE_FILES = {
    "screening-candidates.audit.jsonl",
    "primary-decisions.audit.jsonl",
    "coding-audit-plan.json",
    "secondary-review-queue.jsonl",
    "secondary-coding-template.jsonl",
    "coding-audit-inputs-manifest.json",
}


class NativeCodingAuditProducerTests(unittest.TestCase):
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
    def _run(script: Path, arguments: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *arguments],
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )

    @staticmethod
    def _tree_snapshot(root: Path) -> dict[str, tuple[str, bytes | None]]:
        snapshot: dict[str, tuple[str, bytes | None]] = {".": ("dir", None)}
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                snapshot[relative] = ("symlink", os.readlink(path).encode("utf-8"))
            elif path.is_dir():
                snapshot[relative] = ("dir", None)
            elif path.is_file():
                snapshot[relative] = ("file", path.read_bytes())
            else:
                snapshot[relative] = ("other", None)
        return snapshot

    @staticmethod
    def _bundle_bytes(bundle: Path) -> dict[str, bytes]:
        return {
            path.relative_to(bundle).as_posix(): path.read_bytes()
            for path in sorted(bundle.rglob("*"))
            if path.is_file()
        }

    def _seed_workspace(self, root: Path) -> dict[str, object]:
        workspace = root / "workspace"
        workspace.mkdir(parents=True)
        plan = json.loads(
            (FIXTURES / "research-plan-valid.json").read_text(encoding="utf-8")
        )
        frozen = freeze_plan(plan, workspace)
        text = (
            "Суд установил, что срок подлежит восстановлению и статья 10 "
            "применяется. Проверенная позиция суда обусловила отмену акта."
        )
        text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        raw_sha256 = hashlib.sha256(("RAW:" + text).encode("utf-8")).hexdigest()
        source = {
            "source_id": 101,
            "run_id": "run-fixture",
            "snapshot_id": 201,
            "court_code": "1kas",
            "kind": "doc",
            "canonical_url": "https://1kas.sudrf.ru/example-document",
            "case_uid": "case-fixture",
            "document_id": f"document-sha256:{text_sha256}",
            "chain_id": "chain-fixture",
            "raw_sha256": raw_sha256,
            "text_sha256": text_sha256,
            "text": text,
            "metadata_json": "{}",
            "created_at": "2026-09-03T12:00:00Z",
        }
        matches = screen_text(text, frozen["query_lanes"])
        self.assertTrue(matches)
        screening = {
            "source_id": source["source_id"],
            "document_id": source["document_id"],
            "chain_id": source["chain_id"],
            "matches": matches,
            "status": "candidate_needs_full_text_review",
        }
        primary = {
            "chain_id": source["chain_id"],
            "document_id": source["document_id"],
            "court_code": source["court_code"],
            "decision_date": "2024-03-07",
            "label": "false_positive",
            "speaker": "court",
            "proposition": "Суд связал восстановление срока с исходом дела.",
            "quote": "срок подлежит восстановлению",
            "quote_locator": "абзац fixture",
            "quote_verified": True,
            "full_text_reviewed": True,
            "norm_edition_id": "edition-fixture",
            "material_facts": ["уважительная причина пропуска срока"],
            "material_facts_group": "fixture",
            "comparability_approved": True,
            "reasoning_to_outcome": "Этот мотив повлёк отмену судебного акта.",
            "alternative_grounds": [],
            "remedy": "отмена",
            "reading_family": "restore_deadline",
            "relation": "supports",
            "coder": "primary-reviewer",
            "codebook_version": "1.0",
            "human_review": "approved",
        }
        sources_path = workspace / "exports" / "sources.jsonl"
        screening_path = workspace / "screening-candidates.jsonl"
        primary_path = workspace / "coding-decisions.jsonl"
        write_jsonl(sources_path, [source])
        write_jsonl(screening_path, [screening])
        write_jsonl(primary_path, [primary])
        bundles = root / "bundles"
        bundles.mkdir()
        return {
            "workspace": workspace,
            "bundles": bundles,
            "frozen": frozen,
            "source": source,
            "text": text,
            "screening": screening,
            "primary": primary,
            "sources_path": sources_path,
            "screening_path": screening_path,
            "primary_path": primary_path,
        }

    @staticmethod
    def _prepare_arguments(state: dict[str, object], output: Path) -> list[str]:
        return [
            "quality",
            "coding-audit-prepare",
            "--workspace",
            str(state["workspace"]),
            "--sample-size",
            "5",
            "--exclusion-sample-size",
            "5",
            "--output-dir",
            str(output),
        ]

    def _assert_bundle_contract(self, state: dict[str, object], bundle: Path) -> str:
        self.assertTrue(bundle.is_dir())
        self.assertEqual(BUNDLE_FILES, {path.name for path in bundle.iterdir()})

        frozen = state["frozen"]
        self.assertIsInstance(frozen, dict)
        expected_candidate_id = "audit-candidate-sha256:" + canonical_digest(
            {
                "schema_version": "1.0",
                "plan_sha256": frozen["plan_sha256"],
                "chain_id": "chain-fixture",
                "document_id": state["source"]["document_id"],
            }
        )
        expected_source_ids = sorted(
            record["source_id"]
            for record in read_jsonl(Path(state["sources_path"]))
            if record.get("chain_id") == "chain-fixture"
            and record.get("document_id") == state["source"]["document_id"]
        )
        frame = read_jsonl(bundle / "screening-candidates.audit.jsonl")
        self.assertEqual(1, len(frame))
        self.assertEqual(
            {
                "schema_version",
                "candidate_id",
                "plan_sha256",
                "chain_id",
                "document_id",
                "source_ids",
                "matches",
                "status",
            },
            set(frame[0]),
        )
        self.assertEqual(expected_candidate_id, frame[0]["candidate_id"])
        self.assertEqual(frozen["plan_sha256"], frame[0]["plan_sha256"])
        self.assertEqual(expected_source_ids, frame[0]["source_ids"])
        self.assertEqual(state["screening"]["matches"], frame[0]["matches"])

        primary = read_jsonl(bundle / "primary-decisions.audit.jsonl")
        self.assertEqual(1, len(primary))
        self.assertEqual(AUDIT_CODING_RECORD_FIELDS, set(primary[0]))
        self.assertEqual(expected_candidate_id, primary[0]["candidate_id"])
        self.assertNotIn("court_code", primary[0])
        self.assertNotIn("comparability_approved", primary[0])

        queue = read_jsonl(bundle / "secondary-review-queue.jsonl")
        self.assertEqual(
            {
                "schema_version",
                "candidate_id",
                "chain_id",
                "document_id",
                "source_ids",
                "source_text_sha256",
                "primary_coding_sha256",
                "codebook_version",
                "review_state",
            },
            set(queue[0]),
        )
        self.assertEqual(expected_candidate_id, queue[0]["candidate_id"])
        self.assertEqual(expected_source_ids, queue[0]["source_ids"])
        self.assertEqual(
            hashlib.sha256(str(state["text"]).encode("utf-8")).hexdigest(),
            queue[0]["source_text_sha256"],
        )
        self.assertEqual("independent_secondary_required", queue[0]["review_state"])
        for forbidden in (
            "label",
            "speaker",
            "proposition",
            "quote",
            "quote_locator",
            "reasoning_to_outcome",
            "reading_family",
            "relation",
            "remedy",
            "material_facts",
            "alternative_grounds",
        ):
            self.assertNotIn(forbidden, queue[0])

        templates = read_jsonl(bundle / "secondary-coding-template.jsonl")
        self.assertEqual(1, len(templates))
        template = templates[0]
        self.assertEqual(AUDIT_CODING_RECORD_FIELDS, set(template))
        self.assertEqual(expected_candidate_id, template["candidate_id"])
        self.assertEqual("chain-fixture", template["chain_id"])
        self.assertEqual(state["source"]["document_id"], template["document_id"])
        self.assertEqual("1.0", template["codebook_version"])
        self.assertEqual("pending", template["human_review"])
        self.assertIs(template["quote_verified"], False)
        self.assertIs(template["full_text_reviewed"], False)
        self.assertEqual([], template["material_facts"])
        self.assertEqual([], template["alternative_grounds"])
        for field in AUDIT_CODING_RECORD_FIELDS - {
            "candidate_id",
            "chain_id",
            "document_id",
            "codebook_version",
            "human_review",
            "quote_verified",
            "full_text_reviewed",
            "material_facts",
            "alternative_grounds",
        }:
            self.assertIsNone(template[field], field)

        plan = read_json(bundle / "coding-audit-plan.json")
        self.assertEqual([expected_candidate_id], plan["sample_candidate_ids"])
        self.assertEqual([expected_candidate_id], plan["exclusion_sample_candidate_ids"])
        self.assertEqual([expected_candidate_id], plan["required_candidate_ids"])
        self.assertEqual(5, plan["sample_size"])
        self.assertEqual(5, plan["exclusion_sample_size"])
        self.assertIs(plan["frozen"], True)

        manifest = read_json(bundle / "coding-audit-inputs-manifest.json")
        self.assertEqual("1.0", manifest["schema_version"])
        self.assertEqual(
            "judicial_meaning.quality.coding_audit_prepare", manifest["producer"]
        )
        self.assertEqual(frozen["plan_sha256"], manifest["plan_sha256"])
        self.assertEqual([expected_candidate_id], manifest["candidate_ids"])
        self.assertEqual(
            hashlib.sha256(Path(state["screening_path"]).read_bytes()).hexdigest(),
            manifest["source_screening_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(Path(state["primary_path"]).read_bytes()).hexdigest(),
            manifest["source_primary_sha256"],
        )
        self.assertRegex(manifest["source_text_inventory_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            canonical_digest(
                {key: value for key, value in manifest.items() if key != "manifest_sha256"}
            ),
            manifest["manifest_sha256"],
        )
        files = manifest["files"]
        expected_content_files = BUNDLE_FILES - {"coding-audit-inputs-manifest.json"}
        self.assertEqual(expected_content_files, {item["path"] for item in files})
        for item in files:
            content = (bundle / item["path"]).read_bytes()
            self.assertEqual(len(content), item["bytes"])
            self.assertEqual(hashlib.sha256(content).hexdigest(), item["sha256"])

        schema = json.loads(
            (SKILL_ROOT / "schemas" / "practice-quality.v1.json").read_text(
                encoding="utf-8"
            )
        )

        def validate_definition(name: str, value: object) -> None:
            Draft202012Validator(
                {
                    "$schema": schema["$schema"],
                    "$ref": f"#/definitions/{name}",
                    "definitions": schema["definitions"],
                }
            ).validate(value)

        validate_definition("coding_audit_screening_frame_row", frame[0])
        validate_definition("coding_audit_review_queue_row", queue[0])
        validate_definition("coding_audit_pending_template", template)
        validate_definition("coding_audit_plan", plan)
        validate_definition("coding_audit_inputs_manifest", manifest)
        top_level_validator = Draft202012Validator(schema)
        for artifact_name, artifact in (
            ("screening-candidates.audit.jsonl", frame[0]),
            ("primary-decisions.audit.jsonl", primary[0]),
            ("coding-audit-plan.json", plan),
            ("secondary-review-queue.jsonl", queue[0]),
            ("secondary-coding-template.jsonl", template),
            ("coding-audit-inputs-manifest.json", manifest),
        ):
            self.assertEqual(
                [],
                [error.message for error in top_level_validator.iter_errors(artifact)],
                artifact_name,
            )
        for definition, native_record in (
            ("coding_audit_screening_frame_row", frame[0]),
            ("coding_audit_review_queue_row", queue[0]),
            ("coding_audit_pending_template", template),
        ):
            invalid_record = {**native_record, "document_id": "document-1"}
            with self.assertRaises(ValidationError):
                validate_definition(definition, invalid_record)
        return expected_candidate_id

    def test_valid_workspace_produces_byte_identical_pending_bundle_in_source_and_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            workspace_before = self._tree_snapshot(Path(state["workspace"]))
            bundles: dict[str, Path] = {}
            outputs: dict[str, dict[str, bytes]] = {}
            for location, script in self._locations():
                bundle = Path(state["bundles"]) / location
                completed = self._run(
                    script,
                    self._prepare_arguments(state, bundle),
                    cwd=root,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                self.assertEqual("", completed.stderr)
                self.assertIsInstance(json.loads(completed.stdout), dict)
                self._assert_bundle_contract(state, bundle)
                bundles[location] = bundle
                outputs[location] = self._bundle_bytes(bundle)
                self.assertEqual(
                    workspace_before,
                    self._tree_snapshot(Path(state["workspace"])),
                )
            self.assertEqual(outputs["source"], outputs["installed"])

            repeated = Path(state["bundles"]) / "repeated"
            completed = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, repeated),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual(outputs["source"], self._bundle_bytes(repeated))

    def test_valid_nonmatching_source_and_legacy_alternative_quote_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            sources = read_jsonl(Path(state["sources_path"]))
            nonmatching = copy.deepcopy(sources[0])
            nonmatching["source_id"] = 202
            nonmatching["chain_id"] = "chain-nonmatching"
            nonmatching["canonical_url"] = "https://1kas.sudrf.ru/nonmatching-document"
            nonmatching["text"] = "zzz_unique_nonmatching_text_7429"
            nonmatching["text_sha256"] = hashlib.sha256(
                nonmatching["text"].encode("utf-8")
            ).hexdigest()
            nonmatching["document_id"] = (
                f"document-sha256:{nonmatching['text_sha256']}"
            )
            sources.append(nonmatching)
            write_jsonl(Path(state["sources_path"]), sources)

            primary = read_jsonl(Path(state["primary_path"]))
            primary[0]["alternative_grounds"] = [
                {
                    "ground": "Дополнительный мотив в том же полном тексте",
                    "independently_sufficient": False,
                    "quote": "Проверенная позиция суда обусловила отмену акта",
                }
            ]
            write_jsonl(Path(state["primary_path"]), primary)

            destination = Path(state["bundles"]) / "compatible"
            completed = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, destination),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            projected = read_jsonl(destination / "primary-decisions.audit.jsonl")
            self.assertEqual(
                primary[0]["alternative_grounds"], projected[0]["alternative_grounds"]
            )

    def test_invalid_plan_screen_source_coding_and_quote_publish_nothing(self) -> None:
        def plan_digest_mismatch(state: dict[str, object]) -> None:
            path = Path(state["workspace"]) / "plans" / "plan-v1.json"
            value = read_json(path)
            value["title"] = "Изменённый после заморозки план"
            write_json(path, value)

        def stale_screening_match(state: dict[str, object]) -> None:
            path = Path(state["screening_path"])
            records = read_jsonl(path)
            records[0]["matches"][0]["start"] += 1
            write_jsonl(path, records)

        def missing_source(state: dict[str, object]) -> None:
            write_jsonl(Path(state["sources_path"]), [])

        def invalid_source_id(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["sources_path"]))
            records[0]["source_id"] = True
            write_jsonl(Path(state["sources_path"]), records)

        def stale_source_text_hash(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["sources_path"]))
            records[0]["text"] += " Дополнение без поисковой фразы."
            write_jsonl(Path(state["sources_path"]), records)

        def stale_document_content_id(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["sources_path"]))
            records[0]["text"] += " Дополнение без поисковой фразы."
            records[0]["text_sha256"] = hashlib.sha256(
                records[0]["text"].encode("utf-8")
            ).hexdigest()
            write_jsonl(Path(state["sources_path"]), records)

        def append_nonmatching_source(state: dict[str, object]) -> dict[str, object]:
            records = read_jsonl(Path(state["sources_path"]))
            source = copy.deepcopy(records[0])
            source["source_id"] = 202
            source["chain_id"] = "chain-nonmatching"
            source["canonical_url"] = "https://1kas.sudrf.ru/nonmatching-document"
            source["text"] = "zzz_unique_nonmatching_text_7429"
            source["text_sha256"] = hashlib.sha256(
                source["text"].encode("utf-8")
            ).hexdigest()
            source["document_id"] = f"document-sha256:{source['text_sha256']}"
            records.append(source)
            write_jsonl(Path(state["sources_path"]), records)
            return source

        def stale_nonmatching_source_text_hash(state: dict[str, object]) -> None:
            append_nonmatching_source(state)
            records = read_jsonl(Path(state["sources_path"]))
            records[-1]["text"] += "_changed"
            write_jsonl(Path(state["sources_path"]), records)

        def stale_nonmatching_document_content_id(state: dict[str, object]) -> None:
            append_nonmatching_source(state)
            records = read_jsonl(Path(state["sources_path"]))
            records[-1]["document_id"] = "document-sha256:" + "f" * 64
            write_jsonl(Path(state["sources_path"]), records)

        def duplicate_nonmatching_source_id(state: dict[str, object]) -> None:
            append_nonmatching_source(state)
            records = read_jsonl(Path(state["sources_path"]))
            records[-1]["source_id"] = records[0]["source_id"]
            write_jsonl(Path(state["sources_path"]), records)

        def noncanonical_nonmatching_identity(state: dict[str, object]) -> None:
            append_nonmatching_source(state)
            records = read_jsonl(Path(state["sources_path"]))
            records[-1]["chain_id"] = " chain-nonmatching "
            write_jsonl(Path(state["sources_path"]), records)

        def ambiguous_source_text(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["sources_path"]))
            mirror = copy.deepcopy(records[0])
            mirror["source_id"] = 102
            mirror["text"] += " Иное содержание."
            mirror["text_sha256"] = hashlib.sha256(
                mirror["text"].encode("utf-8")
            ).hexdigest()
            records.append(mirror)
            write_jsonl(Path(state["sources_path"]), records)

        def conflicting_duplicate_matches(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["sources_path"]))
            mirror = copy.deepcopy(records[0])
            mirror["source_id"] = 102
            mirror["canonical_url"] = "https://1kas.sudrf.ru/offset-mirror"
            mirror["text"] = " " + mirror["text"]
            records.append(mirror)
            write_jsonl(Path(state["sources_path"]), records)

            screening = read_jsonl(Path(state["screening_path"]))
            mirror_screening = copy.deepcopy(screening[0])
            mirror_screening["source_id"] = 102
            mirror_screening["matches"] = screen_text(
                mirror["text"], state["frozen"]["query_lanes"]
            )
            screening.append(mirror_screening)
            write_jsonl(Path(state["screening_path"]), screening)

        def missing_coding_field(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["primary_path"]))
            del records[0]["remedy"]
            write_jsonl(Path(state["primary_path"]), records)

        def quote_not_in_text(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["primary_path"]))
            records[0]["quote"] = "цитата, которой в сохранённом тексте нет"
            write_jsonl(Path(state["primary_path"]), records)

        def alternative_quote_not_in_text(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["primary_path"]))
            records[0]["alternative_grounds"] = [
                {
                    "ground": "Иное самостоятельное основание",
                    "independently_sufficient": True,
                    "quote": "отсутствующая альтернативная цитата",
                    "quote_locator": "абзац 99",
                }
            ]
            write_jsonl(Path(state["primary_path"]), records)

        def foreign_candidate_id(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["primary_path"]))
            records[0]["candidate_id"] = "audit-candidate-sha256:" + "f" * 64
            write_jsonl(Path(state["primary_path"]), records)

        def null_candidate_id(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["primary_path"]))
            records[0]["candidate_id"] = None
            write_jsonl(Path(state["primary_path"]), records)

        def non_finite_coding_value(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["primary_path"]))
            records[0]["remedy"] = float("nan")
            write_jsonl(Path(state["primary_path"]), records)

        cases = (
            ("plan-digest", plan_digest_mismatch),
            ("stale-screening", stale_screening_match),
            ("missing-source", missing_source),
            ("invalid-source-id", invalid_source_id),
            ("stale-source-text-hash", stale_source_text_hash),
            ("stale-document-content-id", stale_document_content_id),
            ("stale-nonmatching-source-text-hash", stale_nonmatching_source_text_hash),
            (
                "stale-nonmatching-document-content-id",
                stale_nonmatching_document_content_id,
            ),
            ("duplicate-nonmatching-source-id", duplicate_nonmatching_source_id),
            ("noncanonical-nonmatching-identity", noncanonical_nonmatching_identity),
            ("ambiguous-source", ambiguous_source_text),
            ("conflicting-duplicate-matches", conflicting_duplicate_matches),
            ("missing-coding-field", missing_coding_field),
            ("quote-mismatch", quote_not_in_text),
            ("alternative-quote-mismatch", alternative_quote_not_in_text),
            ("foreign-candidate-id", foreign_candidate_id),
            ("null-candidate-id", null_candidate_id),
            ("non-finite-coding", non_finite_coding_value),
        )
        for name, mutate in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                state = self._seed_workspace(root)
                mutate(state)
                before = self._tree_snapshot(root)
                destination = Path(state["bundles"]) / "must-not-exist"
                completed = self._run(
                    REPO / SCRIPT,
                    self._prepare_arguments(state, destination),
                    cwd=root,
                )
                self.assertEqual(2, completed.returncode, completed.stdout)
                self.assertEqual("", completed.stdout)
                self.assertTrue(completed.stderr.startswith("Ошибка: "))
                self.assertFalse(destination.exists())
                self.assertEqual(before, self._tree_snapshot(root))

    def test_existing_destination_is_refused_without_overwrite(self) -> None:
        for location, script in self._locations():
            with self.subTest(location=location), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                state = self._seed_workspace(root)
                destination = Path(state["bundles"]) / "existing"
                destination.mkdir()
                (destination / "sentinel.txt").write_text(
                    "Сохранить без изменений.\n", encoding="utf-8"
                )
                before = self._tree_snapshot(root)
                completed = self._run(
                    script,
                    self._prepare_arguments(state, destination),
                    cwd=root,
                )
                self.assertEqual(2, completed.returncode, completed.stdout)
                self.assertEqual("", completed.stdout)
                self.assertTrue(completed.stderr.startswith("Ошибка: "))
                self.assertEqual(before, self._tree_snapshot(root))

    def test_workspace_destination_and_atomic_race_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            destination = Path(state["workspace"]) / "audit-must-not-appear"
            before = self._tree_snapshot(Path(state["workspace"]))
            completed = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, destination),
                cwd=root,
            )
            self.assertEqual(2, completed.returncode, completed.stdout)
            self.assertEqual("", completed.stdout)
            self.assertFalse(destination.exists())
            self.assertEqual(before, self._tree_snapshot(Path(state["workspace"])))

            staging = root / "staging"
            racing_destination = root / "destination-created-by-racer"
            staging.mkdir()
            (staging / "bundle.txt").write_text("new\n", encoding="utf-8")
            racing_destination.mkdir()
            with self.assertRaises(FileExistsError):
                _atomic_rename_no_replace(staging, racing_destination)
            self.assertTrue(staging.is_dir())
            self.assertEqual([], list(racing_destination.iterdir()))

    def test_case_alias_cannot_place_bundle_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            workspace = Path(state["workspace"])
            alias = workspace.with_name(workspace.name.upper())
            if not alias.exists() or not os.path.samefile(alias, workspace):
                self.skipTest("Файловая система чувствительна к регистру.")
            destination = alias / "audit-via-case-alias"
            before = self._tree_snapshot(workspace)
            completed = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, destination),
                cwd=root,
            )
            self.assertEqual(2, completed.returncode, completed.stdout)
            self.assertEqual("", completed.stdout)
            self.assertTrue(completed.stderr.startswith("Ошибка: "))
            self.assertFalse(destination.exists())
            self.assertEqual(before, self._tree_snapshot(workspace))

    def test_missing_darwin_no_replace_primitive_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = root / "staging"
            destination = root / "destination"
            staging.mkdir()
            with (
                patch.object(cli_module.sys, "platform", "darwin"),
                patch.object(cli_module.ctypes, "CDLL", return_value=object()),
            ):
                with self.assertRaises(OSError) as observed:
                    _atomic_rename_no_replace(staging, destination)
            self.assertEqual(errno.ENOTSUP, observed.exception.errno)
            self.assertTrue(staging.is_dir())
            self.assertFalse(destination.exists())

    def test_jsonl_round_trip_preserves_unicode_line_and_paragraph_separators(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "unicode-separators.jsonl"
            record = {"text": "до\u2028середина\u2029после"}
            write_jsonl(path, [record])
            self.assertEqual([record], read_jsonl(path))

            state = self._seed_workspace(root)
            primary = read_jsonl(Path(state["primary_path"]))
            primary[0]["proposition"] = record["text"]
            write_jsonl(Path(state["primary_path"]), primary)
            destination = Path(state["bundles"]) / "unicode"
            completed = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, destination),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            projected = read_jsonl(destination / "primary-decisions.audit.jsonl")
            self.assertEqual(record["text"], projected[0]["proposition"])

    def test_identical_duplicate_sources_collapse_without_changing_candidate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            sources = read_jsonl(Path(state["sources_path"]))
            mirror = copy.deepcopy(sources[0])
            mirror["source_id"] = 102
            mirror["canonical_url"] = "https://1kas.sudrf.ru/example-document-mirror"
            sources.append(mirror)
            write_jsonl(Path(state["sources_path"]), sources)
            screening = read_jsonl(Path(state["screening_path"]))
            mirror_screening = copy.deepcopy(screening[0])
            mirror_screening["source_id"] = 102
            screening.append(mirror_screening)
            write_jsonl(Path(state["screening_path"]), screening)

            destination = Path(state["bundles"]) / "collapsed"
            completed = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, destination),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            candidate_id = self._assert_bundle_contract(state, destination)
            frame = read_jsonl(destination / "screening-candidates.audit.jsonl")
            queue = read_jsonl(destination / "secondary-review-queue.jsonl")
            self.assertEqual(1, len(frame))
            self.assertEqual(candidate_id, frame[0]["candidate_id"])
            self.assertEqual([101, 102], frame[0]["source_ids"])
            self.assertEqual([101, 102], queue[0]["source_ids"])

    def test_consistent_full_text_change_gets_a_new_content_bound_candidate_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            first_destination = Path(state["bundles"]) / "before"
            first = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, first_destination),
                cwd=root,
            )
            self.assertEqual(0, first.returncode, first.stderr)
            first_id = read_jsonl(
                first_destination / "screening-candidates.audit.jsonl"
            )[0]["candidate_id"]

            sources = read_jsonl(Path(state["sources_path"]))
            sources[0]["text"] += " Новый материальный мотив без поисковой фразы."
            new_text_sha256 = hashlib.sha256(
                sources[0]["text"].encode("utf-8")
            ).hexdigest()
            new_document_id = f"document-sha256:{new_text_sha256}"
            sources[0]["text_sha256"] = new_text_sha256
            sources[0]["document_id"] = new_document_id
            write_jsonl(Path(state["sources_path"]), sources)
            screening = read_jsonl(Path(state["screening_path"]))
            screening[0]["document_id"] = new_document_id
            write_jsonl(Path(state["screening_path"]), screening)
            primary = read_jsonl(Path(state["primary_path"]))
            primary[0]["document_id"] = new_document_id
            write_jsonl(Path(state["primary_path"]), primary)

            second_destination = Path(state["bundles"]) / "after"
            second = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, second_destination),
                cwd=root,
            )
            self.assertEqual(0, second.returncode, second.stderr)
            second_id = read_jsonl(
                second_destination / "screening-candidates.audit.jsonl"
            )[0]["candidate_id"]
            self.assertNotEqual(first_id, second_id)

    def test_pending_template_cannot_satisfy_coding_reliability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            bundle = Path(state["bundles"]) / "audit-inputs"
            prepared = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, bundle),
                cwd=root,
            )
            self.assertEqual(0, prepared.returncode, prepared.stderr)
            candidate_id = self._assert_bundle_contract(state, bundle)
            primary = read_jsonl(bundle / "primary-decisions.audit.jsonl")[0]
            template = read_jsonl(bundle / "secondary-coding-template.jsonl")[0]
            audit_path = root / "unchanged-pending-template.jsonl"
            write_jsonl(
                audit_path,
                [
                    {
                        "candidate_id": candidate_id,
                        "primary_coding_sha256": canonical_digest(primary),
                        "secondary_coding": template,
                        "secondary_coding_sha256": canonical_digest(template),
                    }
                ],
            )
            observed: dict[str, dict[str, object]] = {}
            for location, script in self._locations():
                completed = self._run(
                    script,
                    [
                        "quality",
                        "coding-reliability",
                        "--audit-plan",
                        str(bundle / "coding-audit-plan.json"),
                        "--primary-decisions",
                        str(bundle / "primary-decisions.audit.jsonl"),
                        "--audit-decisions",
                        str(audit_path),
                    ],
                    cwd=root,
                )
                self.assertEqual(3, completed.returncode, completed.stderr)
                self.assertEqual("", completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertIs(payload["complete"], False)
                self.assertIn(candidate_id, payload["invalid_audit_record_ids"])
                self.assertIn(candidate_id, payload["unresolved_candidate_ids"])
                observed[location] = payload
            self.assertEqual(observed["source"], observed["installed"])

    def test_coding_reliability_rejects_ambiguous_json_in_every_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            bundle = Path(state["bundles"]) / "strict-inputs"
            prepared = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, bundle),
                cwd=root,
            )
            self.assertEqual(0, prepared.returncode, prepared.stderr)

            plan_path = bundle / "coding-audit-plan.json"
            primary_path = bundle / "primary-decisions.audit.jsonl"
            plan = read_json(plan_path)
            primary = read_jsonl(primary_path)[0]
            secondary = {**primary, "coder": "independent-secondary-reviewer"}
            audit = {
                "candidate_id": primary["candidate_id"],
                "primary_coding_sha256": canonical_digest(primary),
                "secondary_coding": secondary,
                "secondary_coding_sha256": canonical_digest(secondary),
            }
            audit_path = root / "valid-audit.jsonl"
            write_jsonl(audit_path, [audit])

            canonical_options = {
                "ensure_ascii": False,
                "sort_keys": True,
                "separators": (",", ":"),
            }
            ambiguous_plan = root / "ambiguous-plan.json"
            plan_json = json.dumps(plan, **canonical_options)
            ambiguous_plan.write_text(
                '{"schema_version":"attacker-visible-first",' + plan_json[1:] + "\n",
                encoding="utf-8",
            )
            ambiguous_primary = root / "ambiguous-primary.json"
            primary_json = json.dumps(primary, **canonical_options)
            ambiguous_primary.write_text(
                '[{"candidate_id":"attacker-visible-first",'
                + primary_json[1:]
                + "]\n",
                encoding="utf-8",
            )
            ambiguous_audit = root / "ambiguous-audit.jsonl"
            secondary_json = json.dumps(secondary, **canonical_options)
            ambiguous_secondary_json = (
                '{"candidate_id":"attacker-visible-first",' + secondary_json[1:]
            )
            ambiguous_audit.write_text(
                "{"
                + '"candidate_id":'
                + json.dumps(audit["candidate_id"], ensure_ascii=False)
                + ',"primary_coding_sha256":'
                + json.dumps(audit["primary_coding_sha256"])
                + ',"secondary_coding":'
                + ambiguous_secondary_json
                + ',"secondary_coding_sha256":'
                + json.dumps(audit["secondary_coding_sha256"])
                + "}\n",
                encoding="utf-8",
            )
            ambiguous_adjudications = root / "ambiguous-adjudications.jsonl"
            ambiguous_adjudications.write_text(
                '{"candidate_id":"attacker-visible-first",'
                f'"candidate_id":{json.dumps(primary["candidate_id"])}}}\n',
                encoding="utf-8",
            )
            nonfinite_primary = root / "nonfinite-primary.json"
            nonfinite_primary.write_text('[{"candidate_id":NaN}]\n', encoding="utf-8")
            nonfinite_audit = root / "nonfinite-audit.jsonl"
            nonfinite_audit.write_text('{"candidate_id":Infinity}\n', encoding="utf-8")

            cases = (
                ("plan-duplicate", ambiguous_plan, primary_path, audit_path, None),
                ("primary-duplicate", plan_path, ambiguous_primary, audit_path, None),
                ("audit-nested-duplicate", plan_path, primary_path, ambiguous_audit, None),
                (
                    "adjudication-duplicate",
                    plan_path,
                    primary_path,
                    audit_path,
                    ambiguous_adjudications,
                ),
                ("primary-nan", plan_path, nonfinite_primary, audit_path, None),
                ("audit-infinity", plan_path, primary_path, nonfinite_audit, None),
            )
            for name, selected_plan, selected_primary, selected_audit, adjudications in cases:
                for location, script in self._locations():
                    with self.subTest(case=name, location=location):
                        arguments = [
                            "quality",
                            "coding-reliability",
                            "--audit-plan",
                            str(selected_plan),
                            "--primary-decisions",
                            str(selected_primary),
                            "--audit-decisions",
                            str(selected_audit),
                        ]
                        if adjudications is not None:
                            arguments.extend(["--adjudications", str(adjudications)])
                        completed = self._run(script, arguments, cwd=root)
                        self.assertEqual(2, completed.returncode, completed.stdout)
                        self.assertEqual("", completed.stdout)
                        self.assertTrue(completed.stderr.startswith("Ошибка: "))

    def test_coding_reliability_keeps_escaped_surrogates_visible_as_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            bundle = Path(state["bundles"]) / "surrogate-inputs"
            prepared = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, bundle),
                cwd=root,
            )
            self.assertEqual(0, prepared.returncode, prepared.stderr)

            plan_path = bundle / "coding-audit-plan.json"
            primary_path = bundle / "primary-decisions.audit.jsonl"
            plan = read_json(plan_path)
            primary = read_jsonl(primary_path)[0]
            valid_secondary = {**primary, "coder": "independent-secondary-reviewer"}
            valid_audit = {
                "candidate_id": primary["candidate_id"],
                "primary_coding_sha256": canonical_digest(primary),
                "secondary_coding": valid_secondary,
                "secondary_coding_sha256": canonical_digest(valid_secondary),
            }
            valid_audit_path = root / "valid-audit.jsonl"
            write_jsonl(valid_audit_path, [valid_audit])

            bad_identifier_audit = root / "surrogate-candidate.jsonl"
            bad_identifier_audit.write_text(
                '{"candidate_id":"\\ud800"}\n', encoding="utf-8"
            )
            bad_secondary = {**valid_secondary, "proposition": "\ud800"}
            bad_nested_audit = root / "surrogate-secondary.jsonl"
            bad_nested_audit.write_text(
                json.dumps(
                    {
                        **valid_audit,
                        "secondary_coding": bad_secondary,
                        "secondary_coding_sha256": "0" * 64,
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            bad_plan = {**plan, "required_candidate_ids": ["\ud800"]}
            bad_plan_path = root / "surrogate-plan.json"
            bad_plan_path.write_text(
                json.dumps(bad_plan, ensure_ascii=True, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            cases = (
                ("audit-identifier", plan_path, bad_identifier_audit),
                ("audit-nested", plan_path, bad_nested_audit),
                ("plan-required", bad_plan_path, valid_audit_path),
            )
            observed: dict[tuple[str, str], dict[str, object]] = {}
            for case, selected_plan, selected_audit in cases:
                for location, script in self._locations():
                    with self.subTest(case=case, location=location):
                        completed = self._run(
                            script,
                            [
                                "quality",
                                "coding-reliability",
                                "--audit-plan",
                                str(selected_plan),
                                "--primary-decisions",
                                str(primary_path),
                                "--audit-decisions",
                                str(selected_audit),
                            ],
                            cwd=root,
                        )
                        self.assertEqual(3, completed.returncode, completed.stderr)
                        self.assertEqual("", completed.stderr)
                        payload = json.loads(completed.stdout)
                        self.assertIs(payload["complete"], False)
                        self.assertTrue(payload["unresolved_candidate_ids"])
                        self.assertRegex(payload["audit_decisions_sha256"], r"^[0-9a-f]{64}$")
                        observed[(case, location)] = payload
            for case, _, _ in cases:
                self.assertEqual(
                    observed[(case, "source")], observed[(case, "installed")]
                )

    def test_empty_audit_selection_is_refused_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            primary = read_jsonl(Path(state["primary_path"]))
            primary[0]["label"] = "core_merits"
            write_jsonl(Path(state["primary_path"]), primary)
            destination = Path(state["bundles"]) / "must-not-exist"
            before = self._tree_snapshot(Path(state["workspace"]))
            arguments = [
                "quality",
                "coding-audit-prepare",
                "--workspace",
                str(state["workspace"]),
                "--sample-size",
                "0",
                "--exclusion-sample-size",
                "1",
                "--output-dir",
                str(destination),
            ]
            completed = self._run(REPO / SCRIPT, arguments, cwd=root)
            self.assertEqual(2, completed.returncode, completed.stdout)
            self.assertEqual("", completed.stdout)
            self.assertTrue(completed.stderr.startswith("Ошибка: "))
            self.assertFalse(destination.exists())
            self.assertEqual(before, self._tree_snapshot(Path(state["workspace"])))

    def test_russian_help_explains_outputs_refusal_and_human_boundaries(self) -> None:
        required_fragments = (
            "--workspace",
            "--sample-size",
            "--exclusion-sample-size",
            "--output-dir",
            "замороженн",
            "первичн",
            "полн",
            "без сетев",
            "существующ",
            "ожидающ",
            "вторичн",
            "расхожд",
            "юридическ",
            "пода",
            *sorted(BUNDLE_FILES),
        )
        observed: dict[str, str] = {}
        for location, script in self._locations():
            completed = self._run(
                script,
                ["quality", "coding-audit-prepare", "--help"],
                cwd=REPO,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual("", completed.stderr)
            logical_help = re.sub(r"-\n\s*", "-", completed.stdout)
            lowered = logical_help.casefold()
            for fragment in required_fragments:
                self.assertIn(fragment.casefold(), lowered, (location, fragment))
            observed[location] = completed.stdout
        self.assertEqual(observed["source"], observed["installed"])


if __name__ == "__main__":
    unittest.main()
