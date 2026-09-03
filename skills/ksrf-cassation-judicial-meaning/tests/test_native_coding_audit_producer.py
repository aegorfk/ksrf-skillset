from __future__ import annotations

import copy
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unicodedata
import unittest
import zipfile
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError

from judicial_meaning.analysis import screen_text
import judicial_meaning.cli as cli_module
import judicial_meaning.practice_quality as practice_quality_module
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
    build_native_coding_audit_inputs,
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
    "independent-review-packet.zip",
    "coding-audit-inputs-manifest.json",
}
REVIEW_PACKET_FILES = {
    "CODING-BRIEF.json",
    "CODING-CODEBOOK.md",
    "REVIEW-INSTRUCTIONS.md",
    "review-materials.jsonl",
    "review-packet-manifest.json",
    "secondary-coding-template.jsonl",
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

    @staticmethod
    def _jsonl_bytes(value: bytes) -> list[dict[str, object]]:
        return [
            json.loads(line)
            for line in value.decode("utf-8").splitlines()
            if line.strip()
        ]

    def _seed_workspace(self, root: Path) -> dict[str, object]:
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
    def _prepare_arguments(
        state: dict[str, object], output: Path, *, codebook_version: str = "1.0"
    ) -> list[str]:
        return [
            "quality",
            "coding-audit-prepare",
            "--workspace",
            str(state["workspace"]),
            "--codebook-version",
            codebook_version,
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

        review_zip = bundle / "independent-review-packet.zip"
        with zipfile.ZipFile(review_zip, "r") as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(sorted(REVIEW_PACKET_FILES), archive.namelist())
            review_bytes = {
                name: archive.read(name) for name in archive.namelist()
            }
            for info in archive.infolist():
                self.assertEqual((1980, 1, 1, 0, 0, 0), info.date_time)
                self.assertEqual(zipfile.ZIP_STORED, info.compress_type)
                self.assertEqual(3, info.create_system)
                self.assertEqual(0o644, (info.external_attr >> 16) & 0o777)
                self.assertNotIn("/", info.filename)
            self.assertEqual(b"", archive.comment)

        review_materials = self._jsonl_bytes(
            review_bytes["review-materials.jsonl"]
        )
        self.assertEqual(1, len(review_materials))
        material = review_materials[0]
        self.assertEqual(
            {
                "schema_version",
                "candidate_id",
                "chain_id",
                "document_id",
                "source_text_sha256",
                "packet_text_sha256",
                "text",
            },
            set(material),
        )
        self.assertEqual(expected_candidate_id, material["candidate_id"])
        self.assertEqual(state["text"], material["text"])
        self.assertEqual(
            hashlib.sha256(str(state["text"]).encode("utf-8")).hexdigest(),
            material["packet_text_sha256"],
        )
        self.assertEqual(
            review_bytes["secondary-coding-template.jsonl"],
            (bundle / "secondary-coding-template.jsonl").read_bytes(),
        )
        self.assertEqual(
            (
                SKILL_ROOT / "references" / "coding-audit-codebook-v1.md"
            ).read_bytes(),
            review_bytes["CODING-CODEBOOK.md"],
        )
        coding_brief = json.loads(review_bytes["CODING-BRIEF.json"].decode("utf-8"))
        self.assertEqual(frozen["plan_sha256"], coding_brief["plan_sha256"])
        self.assertEqual("1.0", coding_brief["codebook_version"])
        self.assertEqual(
            "hypothesis_under_test",
            coding_brief["research_questions"][0]["status"],
        )
        self.assertEqual(frozen["research_questions"][0]["question"], coding_brief["research_questions"][0]["question"])
        self.assertNotIn("query_lanes", coding_brief)
        self.assertNotIn("approved_by", coding_brief)
        self.assertNotIn("adverse_review", coding_brief)
        self.assertEqual(
            canonical_digest(
                {
                    key: value
                    for key, value in coding_brief.items()
                    if key != "brief_sha256"
                }
            ),
            coding_brief["brief_sha256"],
        )
        guide = review_bytes["REVIEW-INSTRUCTIONS.md"].decode("utf-8")
        logical_guide = " ".join(guide.casefold().split())
        self.assertIn("не передавайте весь родительский каталог", logical_guide)
        self.assertIn("по независимому каналу", logical_guide)
        self.assertIn("shasum -a 256", logical_guide)
        self.assertIn("ровно 20 полями", logical_guide)
        self.assertIn("independently_sufficient", logical_guide)
        self.assertIn("distinguishes", logical_guide)
        self.assertIn("строгий utf-8 jsonl", logical_guide)
        self.assertIn("повторяющихся ключей", logical_guide)
        self.assertIn("nan", logical_guide)
        self.assertIn("штатного импорта", logical_guide)
        self.assertIn("coding-codebook.md", logical_guide)
        self.assertIn("coding-brief.json", logical_guide)
        self.assertIn("направленную проверяемую гипотезу", logical_guide)
        self.assertIn("supports", logical_guide)
        self.assertIn("adverse", logical_guide)
        self.assertIn("сам факт включения", logical_guide)
        self.assertIn("конкретную поисковую дорожку", logical_guide)
        self.assertIn("логическое json-значение", logical_guide)
        self.assertIn("не скрывает исход судебного дела", logical_guide)
        self.assertIn("не разрешает публикацию", logical_guide)

        review_manifest = json.loads(
            review_bytes["review-packet-manifest.json"].decode("utf-8")
        )
        self.assertEqual(
            {
                "schema_version",
                "artifact_type",
                "producer",
                "plan_sha256",
                "codebook_version",
                "codebook_sha256",
                "coding_brief_file_sha256",
                "candidate_ids",
                "blinding_scope",
                "excluded_information",
                "contains_full_text",
                "contains_primary_coding",
                "review_state",
                "human_approval_created",
                "publication_safe",
                "legal_readiness",
                "files",
                "manifest_sha256",
            },
            set(review_manifest),
        )
        self.assertEqual(
            "coding_audit_blinded_review_packet",
            review_manifest["artifact_type"],
        )
        self.assertEqual("1.0", review_manifest["codebook_version"])
        self.assertEqual(
            hashlib.sha256(review_bytes["CODING-CODEBOOK.md"]).hexdigest(),
            review_manifest["codebook_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(review_bytes["CODING-BRIEF.json"]).hexdigest(),
            review_manifest["coding_brief_file_sha256"],
        )
        self.assertEqual([expected_candidate_id], review_manifest["candidate_ids"])
        self.assertEqual("primary_coding_answer_only", review_manifest["blinding_scope"])
        self.assertEqual(
            [
                "adjudication",
                "primary_coder_identity",
                "primary_coding",
                "primary_coding_sha256",
                "sample_lane",
                "screening_matches",
                "screening_queries",
            ],
            review_manifest["excluded_information"],
        )
        self.assertIs(review_manifest["contains_full_text"], True)
        self.assertIs(review_manifest["contains_primary_coding"], False)
        self.assertEqual(
            "independent_secondary_required",
            review_manifest["review_state"],
        )
        self.assertIs(review_manifest["human_approval_created"], False)
        self.assertIs(review_manifest["publication_safe"], False)
        self.assertIs(review_manifest["legal_readiness"], False)
        self.assertEqual(
            canonical_digest(
                {
                    key: value
                    for key, value in review_manifest.items()
                    if key != "manifest_sha256"
                }
            ),
            review_manifest["manifest_sha256"],
        )
        self.assertEqual(
            REVIEW_PACKET_FILES - {"review-packet-manifest.json"},
            {item["path"] for item in review_manifest["files"]},
        )
        for item in review_manifest["files"]:
            content = review_bytes[item["path"]]
            self.assertEqual(len(content), item["bytes"])
            self.assertEqual(hashlib.sha256(content).hexdigest(), item["sha256"])

        plan = read_json(bundle / "coding-audit-plan.json")
        self.assertEqual([expected_candidate_id], plan["sample_candidate_ids"])
        self.assertEqual([expected_candidate_id], plan["exclusion_sample_candidate_ids"])
        self.assertEqual([expected_candidate_id], plan["required_candidate_ids"])
        self.assertEqual(5, plan["sample_size"])
        self.assertEqual(5, plan["exclusion_sample_size"])
        self.assertIs(plan["frozen"], True)

        manifest = read_json(bundle / "coding-audit-inputs-manifest.json")
        self.assertEqual("1.0", manifest["schema_version"])
        self.assertEqual("1.1", manifest["bundle_contract_version"])
        self.assertEqual("1.0", manifest["codebook_version"])
        self.assertEqual(
            review_manifest["codebook_sha256"], manifest["codebook_sha256"]
        )
        self.assertEqual(
            review_manifest["coding_brief_file_sha256"],
            manifest["coding_brief_file_sha256"],
        )
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
        validate_definition("coding_audit_neutral_brief", coding_brief)
        validate_definition("coding_audit_blinded_review_material", material)
        validate_definition("coding_audit_blinded_review_manifest", review_manifest)
        validate_definition("coding_audit_plan", plan)
        validate_definition("coding_audit_inputs_manifest", manifest)
        legacy_manifest = copy.deepcopy(manifest)
        del legacy_manifest["bundle_contract_version"]
        del legacy_manifest["codebook_version"]
        del legacy_manifest["codebook_sha256"]
        del legacy_manifest["coding_brief_file_sha256"]
        legacy_manifest["files"] = [
            item
            for item in legacy_manifest["files"]
            if item["path"] != "independent-review-packet.zip"
        ]
        legacy_unsigned = {
            key: value
            for key, value in legacy_manifest.items()
            if key != "manifest_sha256"
        }
        legacy_manifest["manifest_sha256"] = canonical_digest(legacy_unsigned)
        validate_definition("coding_audit_inputs_manifest", legacy_manifest)
        incompatible_new_manifest = copy.deepcopy(manifest)
        incompatible_new_manifest["files"] = legacy_manifest["files"]
        with self.assertRaises(ValidationError):
            validate_definition(
                "coding_audit_inputs_manifest", incompatible_new_manifest
            )
        incompatible_legacy_manifest = copy.deepcopy(manifest)
        del incompatible_legacy_manifest["bundle_contract_version"]
        del incompatible_legacy_manifest["codebook_version"]
        del incompatible_legacy_manifest["codebook_sha256"]
        del incompatible_legacy_manifest["coding_brief_file_sha256"]
        with self.assertRaises(ValidationError):
            validate_definition(
                "coding_audit_inputs_manifest", incompatible_legacy_manifest
            )
        top_level_validator = Draft202012Validator(schema)
        for artifact_name, artifact in (
            ("screening-candidates.audit.jsonl", frame[0]),
            ("primary-decisions.audit.jsonl", primary[0]),
            ("coding-audit-plan.json", plan),
            ("secondary-review-queue.jsonl", queue[0]),
            ("secondary-coding-template.jsonl", template),
            ("CODING-BRIEF.json", coding_brief),
            ("coding-audit-inputs-manifest.json", manifest),
            ("review-materials.jsonl", material),
            ("review-packet-manifest.json", review_manifest),
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
                payload = json.loads(completed.stdout)
                self.assertIsInstance(payload, dict)
                self.assertEqual(
                    {
                        "artifact_type",
                        "output_dir",
                        "manifest_sha256",
                        "independent_review_packet_sha256",
                        "candidate_count",
                        "required_candidate_count",
                        "secondary_review_state",
                        "human_approval_created",
                        "legal_readiness",
                    },
                    set(payload),
                )
                self.assertEqual(
                    hashlib.sha256(
                        (bundle / "independent-review-packet.zip").read_bytes()
                    ).hexdigest(),
                    payload["independent_review_packet_sha256"],
                )
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

    def test_review_zip_is_invariant_to_primary_answers_and_sampling_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            first = Path(state["bundles"]) / "first"
            completed = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, first),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)

            primary = read_jsonl(Path(state["primary_path"]))
            primary[0].update(
                {
                    "label": "core_merits",
                    "coder": "changed-primary-reviewer",
                    "proposition": "Иная допустимая формулировка первого кодировщика.",
                    "quote": "Проверенная позиция суда обусловила отмену акта",
                    "quote_locator": "иной локатор первичного кодировщика",
                    "reasoning_to_outcome": "Иное объяснение связи мотива и исхода.",
                    "reading_family": "changed-primary-family",
                    "material_facts": ["иной первично выделенный факт"],
                }
            )
            write_jsonl(Path(state["primary_path"]), primary)
            second = Path(state["bundles"]) / "second"
            completed = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, second),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)

            self.assertNotEqual(
                (first / "primary-decisions.audit.jsonl").read_bytes(),
                (second / "primary-decisions.audit.jsonl").read_bytes(),
            )
            self.assertNotEqual(
                (first / "coding-audit-plan.json").read_bytes(),
                (second / "coding-audit-plan.json").read_bytes(),
            )
            self.assertEqual(
                (first / "independent-review-packet.zip").read_bytes(),
                (second / "independent-review-packet.zip").read_bytes(),
            )

    def test_review_material_distinguishes_store_and_exact_packet_text_digests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            sources = read_jsonl(Path(state["sources_path"]))
            text = str(sources[0]["text"]).replace(
                "Суд установил, что",
                "Суд\t  установил,\n\v\f\rчто",
            )
            normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()
            sources[0]["text"] = text
            sources[0]["text_sha256"] = hashlib.sha256(
                normalized.encode("utf-8")
            ).hexdigest()
            sources[0]["document_id"] = (
                f"document-sha256:{sources[0]['text_sha256']}"
            )
            write_jsonl(Path(state["sources_path"]), sources)

            frozen = state["frozen"]
            screening = {
                "source_id": sources[0]["source_id"],
                "document_id": sources[0]["document_id"],
                "chain_id": sources[0]["chain_id"],
                "matches": screen_text(text, frozen["query_lanes"]),
                "status": "candidate_needs_full_text_review",
            }
            write_jsonl(Path(state["screening_path"]), [screening])
            primary = read_jsonl(Path(state["primary_path"]))
            primary[0]["document_id"] = sources[0]["document_id"]
            write_jsonl(Path(state["primary_path"]), primary)

            bundle = Path(state["bundles"]) / "whitespace"
            completed = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(state, bundle),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            with zipfile.ZipFile(bundle / "independent-review-packet.zip") as archive:
                material = self._jsonl_bytes(
                    archive.read("review-materials.jsonl")
                )[0]
            self.assertEqual(text, material["text"])
            self.assertEqual(sources[0]["text_sha256"], material["source_text_sha256"])
            self.assertEqual(
                hashlib.sha256(text.encode("utf-8")).hexdigest(),
                material["packet_text_sha256"],
            )
            self.assertNotEqual(
                material["source_text_sha256"],
                material["packet_text_sha256"],
            )

    def test_captured_text_runtime_rejects_every_forbidden_unicode_category(self) -> None:
        allowed_layout = {"\t", "\n", "\v", "\f", "\r"}
        for character in allowed_layout:
            self.assertTrue(
                practice_quality_module._is_captured_full_text(
                    f"видимый{character}текст"
                )
            )

        wrongly_accepted: list[str] = []
        for codepoint in range(sys.maxunicode + 1):
            character = chr(codepoint)
            category = unicodedata.category(character)
            if category in {"Cf", "Cs"} or (
                category == "Cc" and character not in allowed_layout
            ):
                if practice_quality_module._is_captured_full_text(
                    "видимый" + character + "текст"
                ):
                    wrongly_accepted.append(f"U+{codepoint:04X}/{category}")
        self.assertEqual([], wrongly_accepted)

    def test_review_packet_requires_exact_multi_candidate_bijection_and_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            sources = read_jsonl(Path(state["sources_path"]))
            second_source = copy.deepcopy(sources[0])
            second_source.update(
                {
                    "source_id": 202,
                    "chain_id": "chain-second",
                    "canonical_url": "https://1kas.sudrf.ru/second-document",
                    "text": (
                        "Суд установил, что срок подлежит восстановлению. "
                        "Второй полный текст содержит самостоятельные факты."
                    ),
                }
            )
            second_source["text_sha256"] = hashlib.sha256(
                second_source["text"].encode("utf-8")
            ).hexdigest()
            second_source["raw_sha256"] = hashlib.sha256(
                ("RAW:" + second_source["text"]).encode("utf-8")
            ).hexdigest()
            second_source["document_id"] = (
                f"document-sha256:{second_source['text_sha256']}"
            )
            sources.append(second_source)

            screening = read_jsonl(Path(state["screening_path"]))
            screening.append(
                {
                    "source_id": second_source["source_id"],
                    "document_id": second_source["document_id"],
                    "chain_id": second_source["chain_id"],
                    "matches": screen_text(
                        second_source["text"], state["frozen"]["query_lanes"]
                    ),
                    "status": "candidate_needs_full_text_review",
                }
            )
            primary = read_jsonl(Path(state["primary_path"]))
            second_primary = copy.deepcopy(primary[0])
            second_primary.update(
                {
                    "chain_id": second_source["chain_id"],
                    "document_id": second_source["document_id"],
                    "quote": "срок подлежит восстановлению",
                    "coder": "primary-reviewer-second-record",
                }
            )
            primary.append(second_primary)
            captured_sources = cli_module._captured_workspace_source_texts(
                Path(state["workspace"]), sources
            )
            projection = build_native_coding_audit_inputs(
                screening,
                primary,
                captured_sources,
                plan_sha256=state["frozen"]["plan_sha256"],
                codebook_version="1.0",
                sample_size=5,
                exclusion_sample_size=5,
            )
            self.assertEqual(
                2, len(projection["audit_plan"]["required_candidate_ids"])
            )
            baseline = cli_module._build_blinded_review_packet(
                projection,
                plan_sha256=state["frozen"]["plan_sha256"],
                codebook_content=cli_module._load_audit_codebook("1.0"),
                coding_brief_content=cli_module._canonical_json_bytes(
                    cli_module._build_neutral_coding_brief(
                        state["frozen"], codebook_version="1.0"
                    )
                ),
            )
            with zipfile.ZipFile(io.BytesIO(baseline)) as archive:
                self.assertEqual(
                    2,
                    len(self._jsonl_bytes(archive.read("review-materials.jsonl"))),
                )

            def missing_material(value: dict[str, object]) -> None:
                value["secondary_review_materials"].pop()

            def duplicate_template(value: dict[str, object]) -> None:
                value["secondary_coding_templates"].append(
                    copy.deepcopy(value["secondary_coding_templates"][0])
                )

            def extra_material(value: dict[str, object]) -> None:
                extra = copy.deepcopy(value["secondary_review_materials"][0])
                extra["candidate_id"] = "audit-candidate-sha256:" + "e" * 64
                value["secondary_review_materials"].append(extra)

            def swapped_identity(value: dict[str, object]) -> None:
                materials = value["secondary_review_materials"]
                materials[0]["chain_id"] = materials[1]["chain_id"]

            def stale_packet_digest(value: dict[str, object]) -> None:
                value["secondary_review_materials"][0]["packet_text_sha256"] = (
                    "f" * 64
                )

            def cross_bound_text(value: dict[str, object]) -> None:
                material = value["secondary_review_materials"][0]
                material["text"] = "Совершенно другой полный текст."
                material["packet_text_sha256"] = hashlib.sha256(
                    material["text"].encode("utf-8")
                ).hexdigest()

            cases = (
                ("missing-material", missing_material),
                ("duplicate-template", duplicate_template),
                ("extra-material", extra_material),
                ("swapped-identity", swapped_identity),
                ("stale-packet-digest", stale_packet_digest),
                ("cross-bound-text", cross_bound_text),
            )
            for name, mutate in cases:
                with self.subTest(case=name):
                    tampered = copy.deepcopy(projection)
                    mutate(tampered)
                    with self.assertRaises(ValueError):
                        cli_module._build_blinded_review_packet(
                            tampered,
                            plan_sha256=state["frozen"]["plan_sha256"],
                            codebook_content=cli_module._load_audit_codebook("1.0"),
                            coding_brief_content=cli_module._canonical_json_bytes(
                                cli_module._build_neutral_coding_brief(
                                    state["frozen"], codebook_version="1.0"
                                )
                            ),
                        )

    def test_neutral_brief_and_codebook_are_closed_trusted_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            sources = read_jsonl(Path(state["sources_path"]))
            projection = build_native_coding_audit_inputs(
                read_jsonl(Path(state["screening_path"])),
                read_jsonl(Path(state["primary_path"])),
                cli_module._captured_workspace_source_texts(
                    Path(state["workspace"]), sources
                ),
                plan_sha256=state["frozen"]["plan_sha256"],
                codebook_version="1.0",
                sample_size=5,
                exclusion_sample_size=5,
            )
            codebook = cli_module._load_audit_codebook("1.0")
            brief = cli_module._build_neutral_coding_brief(
                state["frozen"], codebook_version="1.0"
            )

            def extra_search_field(value: dict[str, object]) -> None:
                value["screening_queries"] = ["скрытый запрос"]

            def unsafe_visible_text(value: dict[str, object]) -> None:
                value["title"] = str(value["title"]) + "\u200b"

            def unsafe_canonical_identifier(value: dict[str, object]) -> None:
                value["research_questions"][0]["id"] += "\x00"

            for name, mutate in (
                ("extra-search-field", extra_search_field),
                ("unsafe-visible-text", unsafe_visible_text),
                ("unsafe-canonical-identifier", unsafe_canonical_identifier),
            ):
                with self.subTest(case=name):
                    tampered = copy.deepcopy(brief)
                    mutate(tampered)
                    unsigned = {
                        key: value
                        for key, value in tampered.items()
                        if key != "brief_sha256"
                    }
                    tampered["brief_sha256"] = canonical_digest(unsigned)
                    with self.assertRaises(ValueError):
                        cli_module._build_blinded_review_packet(
                            projection,
                            plan_sha256=state["frozen"]["plan_sha256"],
                            codebook_content=codebook,
                            coding_brief_content=cli_module._canonical_json_bytes(
                                tampered
                            ),
                        )

            with self.assertRaises(ValueError):
                cli_module._build_blinded_review_packet(
                    projection,
                    plan_sha256=state["frozen"]["plan_sha256"],
                    codebook_content=codebook + b"\n<!-- untrusted change -->\n",
                    coding_brief_content=cli_module._canonical_json_bytes(brief),
                )

    def test_codebook_asset_failures_and_concurrent_change_publish_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "codebook.md"
            link = root / "codebook-link.md"
            cases = (
                ("missing", root / "missing.md"),
                ("empty", existing),
                ("non-utf8", existing),
                ("symlink", link),
            )
            for name, path in cases:
                with self.subTest(case=name):
                    if existing.exists():
                        existing.unlink()
                    if link.is_symlink():
                        link.unlink()
                    if name == "empty":
                        existing.write_bytes(b"")
                    elif name == "non-utf8":
                        existing.write_bytes(b"\xff")
                    elif name == "symlink":
                        existing.write_text("valid", encoding="utf-8")
                        link.symlink_to(existing)
                    with patch.dict(
                        cli_module._AUDIT_CODEBOOK_PATHS,
                        {"1.0": str(path)},
                        clear=True,
                    ):
                        with self.assertRaises(ValueError):
                            cli_module._load_audit_codebook("1.0")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            destination = Path(state["bundles"]) / "must-not-exist"
            codebook = cli_module._load_audit_codebook("1.0")
            args = cli_module.argparse.Namespace(
                workspace=str(state["workspace"]),
                output_dir=str(destination),
                codebook_version="1.0",
                sample_size=5,
                exclusion_sample_size=5,
            )
            with patch.object(
                cli_module,
                "_load_audit_codebook",
                side_effect=(codebook, codebook, codebook + b"\nchanged\n"),
            ):
                with self.assertRaisesRegex(ValueError, "изменились"):
                    cli_module.cmd_quality_coding_audit_prepare(args)
            self.assertFalse(destination.exists())

    def test_multiple_questions_and_unsafe_brief_text_publish_nothing(self) -> None:
        def add_second_question(plan: dict[str, object]) -> None:
            question = copy.deepcopy(plan["research_questions"][0])
            question["id"] = "rq-second"
            question["question"] = "Каков второй отдельный проверяемый вопрос?"
            plan["research_questions"].append(question)

        def add_nul_to_title(plan: dict[str, object]) -> None:
            plan["title"] = str(plan["title"]) + "\x00"

        def add_zero_width_to_rule(plan: dict[str, object]) -> None:
            plan["inclusion_rules"][0] += "\u200b"

        def make_question_open(plan: dict[str, object]) -> None:
            plan["research_questions"][0]["status"] = "research_question"
            plan["research_questions"][0]["question"] = (
                "Как суды толкуют спорную норму?"
            )

        for name, mutate in (
            ("multiple-questions", add_second_question),
            ("open-question", make_question_open),
            ("nul-title", add_nul_to_title),
            ("zero-width-rule", add_zero_width_to_rule),
        ):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                state = self._seed_workspace(root)
                plan_path = Path(state["workspace"]) / "plans" / "plan-v1.json"
                plan = read_json(plan_path)
                mutate(plan)
                unsigned = {
                    key: value
                    for key, value in plan.items()
                    if key not in {"frozen", "plan_sha256"}
                }
                plan["plan_sha256"] = canonical_digest(unsigned)
                write_json(plan_path, plan)
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

        def nul_in_source_text(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["sources_path"]))
            records[0]["text"] += "\x00"
            write_jsonl(Path(state["sources_path"]), records)

        def zero_width_in_source_text(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["sources_path"]))
            records[0]["text"] += "\u200b"
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

        def duplicate_with_different_exact_layout(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["sources_path"]))
            mirror = copy.deepcopy(records[0])
            mirror["source_id"] = 102
            mirror["canonical_url"] = "https://1kas.sudrf.ru/layout-mirror"
            mirror["text"] += "\n"
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

        def primary_codebook_mismatch(state: dict[str, object]) -> None:
            records = read_jsonl(Path(state["primary_path"]))
            records[0]["codebook_version"] = "primary-reviewer-says-false-positive"
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
            ("nul-in-source-text", nul_in_source_text),
            ("zero-width-in-source-text", zero_width_in_source_text),
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
            (
                "duplicate-with-different-exact-layout",
                duplicate_with_different_exact_layout,
            ),
            ("missing-coding-field", missing_coding_field),
            ("primary-codebook-mismatch", primary_codebook_mismatch),
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
                "--codebook-version",
                "1.0",
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

    def test_unknown_codebook_version_is_refused_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = self._seed_workspace(root)
            destination = Path(state["bundles"]) / "must-not-exist"
            completed = self._run(
                REPO / SCRIPT,
                self._prepare_arguments(
                    state, destination, codebook_version="primary-controlled"
                ),
                cwd=root,
            )
            self.assertEqual(2, completed.returncode, completed.stdout)
            self.assertEqual("", completed.stdout)
            self.assertIn("--codebook-version", completed.stderr)
            self.assertFalse(destination.exists())

    def test_russian_help_explains_outputs_refusal_and_human_boundaries(self) -> None:
        required_fragments = (
            "--workspace",
            "--codebook-version",
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
            "independent_review_packet_sha256",
            "coding-codebook.md",
            "coding-brief.json",
            "hypothesis_under_test",
            "независимому каналу",
            "до распаковки",
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
