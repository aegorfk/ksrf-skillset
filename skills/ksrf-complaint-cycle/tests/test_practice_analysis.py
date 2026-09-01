from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import tempfile
import threading
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "ksrf_practice_analysis.py"
)
SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "practice-analysis.v1.json"
)


def _load_runtime():
    if not SCRIPT_PATH.exists():
        return None, f"Не создан runtime: {SCRIPT_PATH}"
    spec = importlib.util.spec_from_file_location("ksrf_practice_analysis", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        return None, f"Не удалось загрузить runtime: {SCRIPT_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, None


practice, IMPORT_ERROR = _load_runtime()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sign_envelope(envelope: dict) -> dict:
    signed = dict(envelope)
    signed.pop("handoff_id", None)
    signed["handoff_id"] = _digest(signed)
    return signed


class PracticeAnalysisTestCase(unittest.TestCase):
    def setUp(self) -> None:
        if practice is None:
            self.fail(IMPORT_ERROR or "Runtime не загружен")
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "matter"
        self.case_file = self.root / "case-file.json"
        _write_json(
            self.case_file,
            {
                "schema": "ksrf.casefile.v3",
                "documents": [
                    {"document_id": "act-a", "sha256": "a" * 64},
                    {"document_id": "act-b", "sha256": "b" * 64},
                ],
            },
        )
        practice.init_workspace(
            self.workspace,
            case_id="case-1",
            case_file=self.case_file,
            now="2026-08-27T10:00:00Z",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def scan_claims(self, claims: list[dict]) -> dict:
        source = self.root / "claims.json"
        _write_json(source, {"claims": claims})
        return practice.scan_input(
            self.workspace,
            source,
            now="2026-08-27T10:05:00Z",
        )

    def attach_with_fake_sibling(self, request: dict) -> dict:
        skills_root = self.root / "skills"
        sibling = (
            skills_root
            / "ksrf-cassation-judicial-meaning"
            / "scripts"
            / "judicial_meaning.py"
        )
        sibling.parent.mkdir(parents=True, exist_ok=True)
        sibling.write_text(
            """#!/usr/bin/env python3
import json
import pathlib
import sys

if sys.argv[1:3] == ['handoff', 'check']:
    source = pathlib.Path(sys.argv[sys.argv.index('--input') + 1])
    source_workspace = pathlib.Path(sys.argv[sys.argv.index('--source-workspace') + 1])
    envelope = json.loads(source.read_text(encoding='utf-8'))
    valid = source_workspace.is_dir() and (source_workspace / 'handoff-inbox.jsonl').is_file() and not (source_workspace / 'tampered.flag').exists()
    print(json.dumps({
        'valid': valid,
        'status': 'valid' if valid else 'source_workspace_invalid',
        'handoff_id': envelope.get('handoff_id'),
        'audit_readable': True,
    }))
    raise SystemExit(0 if valid else 2)
ledger = pathlib.Path(sys.argv[sys.argv.index('--ledger') + 1])
ledger.parent.mkdir(parents=True, exist_ok=True)
ledger.write_text(json.dumps({'imported': True}) + '\\n', encoding='utf-8')
print(json.dumps({'valid': True, 'status': 'imported'}))
""",
            encoding="utf-8",
        )
        return practice.attach_run(
            self.workspace,
            request_id=request["handoff_id"],
            cassation_workspace=self.root / "cassation-run",
            skills_root=skills_root,
            now="2026-08-27T10:10:00Z",
        )

    def import_with_attached_source(self, request: dict, result_path: Path) -> dict:
        return practice.import_result(
            self.workspace,
            result_path,
            request_id=request["handoff_id"],
            now="2026-08-27T11:02:00Z",
        )

    def valid_v2_result(self, request: dict) -> dict:
        claim_bindings = request["payload"]["claim_bindings"]
        position_cards = [{"position_card_id": "position-1", "human_review": "approved"}]
        comparisons = [
            {
                "comparison_id": "comparison-1",
                "position_card_id": "position-1",
                "status": "matched",
                "review_provenance": {"status": "approved", "reviewer": "И.И. Иванов"},
            }
        ]
        relations = [
            {
                "relation_id": "relation-1",
                "position_card_id": "position-1",
                "relation": "supports",
                "stale": False,
                "human_review": "approved",
            }
        ]
        adverse = {"review_id": "case-adverse-review", "complete": True}
        bridge = {
            "claim_wording": "Суды последовательно придают норме расширительный смысл.",
            "maximum_permitted_claim": "corroborated_observed_corpus",
            "supporting_position_card_ids": ["position-1"],
            "adverse_position_card_ids": [],
        }
        human_decision = {
            "decision": "approved",
            "reviewer": "И.И. Иванов",
            "candidate_ids": ["candidate-1"],
        }
        validation_report = {
            "schema_version": "2.0",
            "valid": True,
            "gate": "drafting_ready",
        }
        selected_proofs = {
            "position_cards": position_cards,
            "comparisons": comparisons,
            "relations": relations,
            "adverse": adverse,
            "bridge": bridge,
            "human_decision": human_decision,
            "validation_report": validation_report,
        }
        proof_files = {
            "selected-proofs/position-cards.json": position_cards,
            "selected-proofs/comparisons.json": comparisons,
            "selected-proofs/relations.json": relations,
            "case-adverse-review.json": adverse,
            "normative-bridge.json": bridge,
            "human-decision.json": human_decision,
            "validation-report.json": validation_report,
        }
        manifest_files = sorted(
            [
                {
                    "path": path,
                    "present": True,
                    "bytes": len(_canonical_bytes(content)),
                    "sha256": _digest(content),
                }
                for path, content in proof_files.items()
            ],
            key=lambda item: item["path"],
        )
        candidate = {
            "candidate_id": "candidate-1",
            "plan_sha256": "3" * 64,
            "claim_wording": bridge["claim_wording"],
            "maximum_permitted_claim": bridge["maximum_permitted_claim"],
            "human_review": "approved",
            "drafting_ready": True,
        }
        claim_ids = sorted(item["claim_id"] for item in claim_bindings)
        candidate_sha256 = _digest(candidate)
        finding_id = _digest(
            {
                "candidate_sha256": candidate_sha256,
                "claim_ids": claim_ids,
                "normative_bridge_sha256": _digest(bridge),
            }
        )
        quality_bindings = []
        for quality_type in (
            "chain_stage_propagation",
            "uncertainty_profile",
            "coding_reliability",
            "prefiling_refresh",
        ):
            artifact = {"quality_type": quality_type}
            quality_bindings.append(
                {
                    "quality_type": quality_type,
                    "artifact_sha256": _digest(artifact),
                    "artifact": artifact,
                }
            )
        envelope = {
            "schema_version": "2.0",
            "created_at": "2026-08-27T11:00:00Z",
            "source_skill": "ksrf-cassation-judicial-meaning",
            "target_skill": "ksrf-complaint-cycle",
            "run_id": "run-1",
            "plan_sha256": "3" * 64,
            "evidence_sha256": "4" * 64,
            "fingerprint_sha256": "5" * 64,
            "payload_type": "approved_bounded_findings",
            "payload": {
                "drafting_ready": True,
                "maximum_permitted_claim": "corroborated_observed_corpus",
                "findings": [
                    {
                        "finding_id": finding_id,
                        "candidate_id": candidate["candidate_id"],
                        "candidate": candidate,
                        "candidate_sha256": candidate_sha256,
                        "claim_ids": claim_ids,
                        "claim_wording": bridge["claim_wording"],
                        "supporting_position_card_ids": bridge["supporting_position_card_ids"],
                        "adverse_position_card_ids": bridge["adverse_position_card_ids"],
                        "maximum_permitted_claim": bridge["maximum_permitted_claim"],
                    }
                ],
                "supporting_position_card_ids": ["position-1"],
                "adverse_position_card_ids": [],
                "request_handoff_id": request["handoff_id"],
                "request_sha256": request["payload"]["request_sha256"],
                "claim_set_sha256": request["payload"]["claim_set_sha256"],
                "claim_bindings": claim_bindings,
                "approval_binding": {
                    "human_decision_sha256": _digest(human_decision),
                    "validation_report_sha256": _digest(validation_report),
                    "normative_bridge_sha256": _digest(bridge),
                    "reviewer": "И.И. Иванов",
                    "approved_at": "2026-08-27T10:59:00Z",
                },
                "artifact_manifest": {
                    "files": manifest_files,
                    "manifest_sha256": _digest(manifest_files),
                },
                "selected_position_set_sha256": _digest(
                    {
                        "position_cards": position_cards,
                        "comparisons": comparisons,
                        "relations": relations,
                    }
                ),
                "selected_proofs": selected_proofs,
                "limitations": ["Вывод относится только к раскрытому проверенному корпусу."],
                "quality_bindings": quality_bindings,
            },
            "limitations": ["Вывод относится только к раскрытому проверенному корпусу."],
        }
        return _sign_envelope(envelope)


class TestScanningAndRevisions(PracticeAnalysisTestCase):
    def test_changed_or_missing_scanned_source_requires_rescan_even_for_not_required_claim(self) -> None:
        self.scan_claims(
            [
                {
                    "claim_id": "claim-direct",
                    "text": "Норма применена в деле заявителя.",
                    "practice_dependency": False,
                }
            ]
        )
        before = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(before["claims"][0]["state"], "not_required")
        source = self.root / "claims.json"
        _write_json(
            source,
            {
                "claims": [
                    {
                        "claim_id": "claim-direct",
                        "text": "Все кассационные суды всегда толкуют норму одинаково.",
                    }
                ]
            },
        )
        changed = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(changed["claims"][0]["state"], "stale")
        self.assertIn("source_file_changed", changed["claims"][0]["blocking_reasons"])
        self.assertIn("rescan_required", changed["claims"][0]["blocking_reasons"])

        source.unlink()
        missing = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(missing["claims"][0]["state"], "stale")
        self.assertIn("source_file_missing", missing["claims"][0]["blocking_reasons"])
        self.assertIn("rescan_required", missing["claims"][0]["blocking_reasons"])

    def test_structured_scan_creates_required_claim_and_append_only_revision(self) -> None:
        first = self.scan_claims(
            [
                {
                    "claim_id": "claim-a",
                    "text": "Кассационные суды устойчиво исходят из широкого толкования нормы.",
                    "case_dependency_ids": ["act-a"],
                    "hypothesis_ids": ["hypothesis-a"],
                }
            ]
        )
        first_state = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(first_state["claims"][0]["state"], "required")

        second = self.scan_claims(
            [
                {
                    "claim_id": "claim-a",
                    "text": "После 2023 года кассационные суды изменили широкое толкование нормы.",
                    "case_dependency_ids": ["act-a"],
                    "hypothesis_ids": ["hypothesis-a"],
                }
            ]
        )
        ledger = practice.read_jsonl(
            self.workspace / "practice-analysis" / "claim-ledger.jsonl"
        )
        self.assertEqual(len(ledger), 2)
        self.assertNotEqual(first["claims"][0]["revision_id"], second["claims"][0]["revision_id"])
        self.assertEqual(
            second["claims"][0]["supersedes_revision_id"],
            first["claims"][0]["revision_id"],
        )

    def test_reviewed_not_required_override_requires_reason(self) -> None:
        self.scan_claims(
            [{"claim_id": "claim-a", "text": "Сложились два подхода в судебной практике."}]
        )
        with self.assertRaisesRegex(ValueError, "причин"):
            practice.review_trigger(
                self.workspace,
                claim_id="claim-a",
                decision="not_required",
                reviewer="И.И. Иванов",
                reason="",
                now="2026-08-27T10:06:00Z",
            )
        practice.review_trigger(
            self.workspace,
            claim_id="claim-a",
            decision="not_required",
            reviewer="И.И. Иванов",
            reason="Абзац лишь описывает вопрос исследования и не содержит утверждения.",
            now="2026-08-27T10:07:00Z",
        )
        state = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(state["claims"][0]["state"], "not_required")
        self.assertFalse(state["claims"][0]["draft_blocked"])

    def test_docx_is_scanned_offline_with_standard_library(self) -> None:
        docx = self.root / "draft.docx"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>Судебная практика является противоречивой.</w:t>'
            '</w:r></w:p></w:body></w:document>'
        )
        with zipfile.ZipFile(docx, "w") as archive:
            archive.writestr("word/document.xml", xml)
        result = practice.scan_input(
            self.workspace,
            docx,
            now="2026-08-27T10:08:00Z",
        )
        self.assertEqual(result["format"], "docx")
        self.assertEqual(len(result["claims"]), 1)
        self.assertIn("split", result["claims"][0]["empirical_dimensions"])

    def test_plain_text_is_scanned_without_external_dependencies(self) -> None:
        draft = self.root / "draft.md"
        draft.write_text(
            "Суды кассационной инстанции по-разному толкуют применённую норму.\n",
            encoding="utf-8",
        )
        result = practice.scan_input(
            self.workspace,
            draft,
            now="2026-08-27T10:08:00Z",
        )
        self.assertEqual(result["format"], "md")
        self.assertEqual(len(result["claims"]), 1)
        self.assertIn("split", result["claims"][0]["empirical_dimensions"])

    def test_selective_case_dependency_change_stales_only_linked_claim(self) -> None:
        self.scan_claims(
            [
                {
                    "claim_id": "claim-a",
                    "text": "Практика по первому акту является единообразной.",
                    "case_dependency_ids": ["act-a"],
                },
                {
                    "claim_id": "claim-b",
                    "text": "Практика по второму акту является единообразной.",
                    "case_dependency_ids": ["act-b"],
                },
            ]
        )
        _write_json(
            self.case_file,
            {
                "schema": "ksrf.casefile.v3",
                "documents": [
                    {"document_id": "act-a", "sha256": "c" * 64},
                    {"document_id": "act-b", "sha256": "b" * 64},
                ],
            },
        )
        practice.init_workspace(
            self.workspace,
            case_id="case-1",
            case_file=self.case_file,
            now="2026-08-27T10:09:00Z",
        )
        states = {
            item["claim_id"]: item["state"]
            for item in practice.derive_state(self.workspace, stage="drafting")["claims"]
        }
        self.assertEqual(states, {"claim-a": "stale", "claim-b": "required"})


class TestRequestAttachAndImport(PracticeAnalysisTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.scan_claims(
            [
                {
                    "claim_id": "claim-a",
                    "text": "Судебный хаос показывает, что закон не работает.",
                    "case_dependency_ids": ["act-a"],
                    "hypothesis_ids": ["hypothesis-a"],
                    "norm_refs": ["ст. 135 ТК РФ"],
                }
            ]
        )

    def test_request_is_neutral_v2_and_content_bound(self) -> None:
        request = practice.create_request(
            self.workspace,
            now="2026-08-27T10:10:00Z",
        )
        self.assertEqual(request["schema_version"], "2.0")
        self.assertEqual(request["payload_type"], "unproven_research_questions")
        question_text = " ".join(request["payload"]["questions"]).lower()
        self.assertNotIn("судебный хаос", question_text)
        self.assertNotIn("закон не работает", question_text)
        self.assertNotIn("findings", request["payload"])
        self.assertNotIn("complaint_wording", request["payload"])
        self.assertEqual(
            set(request),
            {
                "schema_version",
                "handoff_id",
                "created_at",
                "source_skill",
                "target_skill",
                "run_id",
                "plan_sha256",
                "evidence_sha256",
                "payload_type",
                "payload",
                "limitations",
            },
        )
        self.assertEqual(request["handoff_id"], _digest({k: v for k, v in request.items() if k != "handoff_id"}))
        binding = request["payload"]["claim_bindings"][0]
        self.assertEqual(binding["claim_id"], "claim-a")
        self.assertEqual(
            request["payload"]["claim_set_sha256"],
            _digest(
                sorted(
                    request["payload"]["claim_bindings"],
                    key=lambda item: (
                        item["claim_id"],
                        item["claim_sha256"],
                        item["source_locator"],
                    ),
                )
            ),
        )

    def test_exported_request_keeps_canonical_workspace_copy_for_attach(self) -> None:
        exported = self.root / "outbox" / "request.json"
        request = practice.create_request(
            self.workspace,
            output=exported,
            now="2026-08-27T10:10:00Z",
        )
        canonical = (
            self.workspace
            / "practice-analysis"
            / "requests"
            / f"{request['handoff_id']}.json"
        )
        self.assertTrue(exported.exists())
        self.assertTrue(canonical.exists())
        self.assertEqual(json.loads(exported.read_text(encoding="utf-8")), request)
        self.assertEqual(self.attach_with_fake_sibling(request)["status"], "attached")

    def test_sibling_attach_invokes_cli_and_sets_running(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        attachment = self.attach_with_fake_sibling(request)
        self.assertEqual(attachment["status"], "attached")
        state = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(state["claims"][0]["state"], "running")

    def test_missing_sibling_is_actionable_block_not_global_crash(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        result = practice.attach_run(
            self.workspace,
            request_id=request["handoff_id"],
            cassation_workspace=self.root / "cassation-run",
            skills_root=self.root / "missing-skills",
            now="2026-08-27T10:11:00Z",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("ksrf-cassation-judicial-meaning", result["error"])
        state = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(state["claims"][0]["state"], "blocked")
        self.assertEqual(state["global_integrity_errors"], [])

    def test_v2_import_checks_request_claim_and_approval_proof_bindings(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        valid = self.valid_v2_result(request)
        invalid = json.loads(json.dumps(valid))
        invalid["payload"]["claim_bindings"][0]["claim_sha256"] = "f" * 64
        invalid = _sign_envelope(invalid)
        invalid_path = self.root / "invalid-result.json"
        _write_json(invalid_path, invalid)
        with self.assertRaisesRegex(ValueError, "claim_sha256"):
            practice.import_result(
                self.workspace,
                invalid_path,
                request_id=request["handoff_id"],
                now="2026-08-27T11:01:00Z",
            )
        results_dir = self.workspace / "practice-analysis" / "results"
        self.assertEqual(list(results_dir.glob("*.json")) if results_dir.exists() else [], [])

        valid_path = self.root / "valid-result.json"
        _write_json(valid_path, valid)
        imported = practice.import_result(
            self.workspace,
            valid_path,
            request_id=request["handoff_id"],
            now="2026-08-27T11:02:00Z",
        )
        self.assertEqual(imported["status"], "imported")
        self.assertEqual(
            practice.derive_state(self.workspace, stage="drafting")["claims"][0]["state"],
            "blocked",
        )

    def test_tampered_result_is_rejected_atomically(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        result = self.valid_v2_result(request)
        result["limitations"] = ["Подменённое ограничение"]
        result_path = self.root / "tampered.json"
        _write_json(result_path, result)
        with self.assertRaisesRegex(ValueError, "handoff_id"):
            practice.import_result(
                self.workspace,
                result_path,
                request_id=request["handoff_id"],
                now="2026-08-27T11:02:00Z",
            )
        self.assertFalse((self.workspace / "practice-analysis" / "results" / f"{result['handoff_id']}.json").exists())

    def test_resigned_but_inconsistent_portable_proof_is_rejected(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        result = self.valid_v2_result(request)
        result["payload"]["approval_binding"]["normative_bridge_sha256"] = "f" * 64
        result = _sign_envelope(result)
        result_path = self.root / "inconsistent-proof.json"
        _write_json(result_path, result)
        with self.assertRaisesRegex(ValueError, "normative_bridge_sha256"):
            practice.import_result(
                self.workspace,
                result_path,
                request_id=request["handoff_id"],
                now="2026-08-27T11:02:00Z",
            )

    def test_resigned_finding_must_be_canonical_and_cover_bound_claims(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        for label, mutation, error_pattern in (
            (
                "invented-id",
                lambda finding: finding.__setitem__("finding_id", "f" * 64),
                "finding_id",
            ),
            (
                "extra-field",
                lambda finding: finding.__setitem__("bridge_id", "invented"),
                "не выведен|ровно",
            ),
        ):
            with self.subTest(label=label):
                result = self.valid_v2_result(request)
                mutation(result["payload"]["findings"][0])
                result = _sign_envelope(result)
                result_path = self.root / f"{label}.json"
                _write_json(result_path, result)
                with self.assertRaisesRegex(ValueError, error_pattern):
                    practice.import_result(
                        self.workspace,
                        result_path,
                        request_id=request["handoff_id"],
                        now="2026-08-27T11:02:00Z",
                    )

    def test_legacy_v1_result_is_preserved_for_audit_but_never_ready(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        legacy = self.valid_v2_result(request)
        legacy["schema_version"] = "1.0"
        legacy = _sign_envelope(legacy)
        legacy_path = self.root / "legacy.json"
        _write_json(legacy_path, legacy)
        imported = practice.import_result(
            self.workspace,
            legacy_path,
            request_id=request["handoff_id"],
            now="2026-08-27T11:03:00Z",
        )
        self.assertEqual(imported["status"], "legacy_audit_only")
        state = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(state["claims"][0]["state"], "blocked")
        self.assertIn("legacy", " ".join(state["claims"][0]["blocking_reasons"]).lower())

    def test_idempotent_result_import_does_not_duplicate_events(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        result = self.valid_v2_result(request)
        result_path = self.root / "result.json"
        _write_json(result_path, result)
        first = practice.import_result(self.workspace, result_path, request_id=request["handoff_id"])
        second = practice.import_result(self.workspace, result_path, request_id=request["handoff_id"])
        self.assertEqual(first["status"], "imported")
        self.assertEqual(second["status"], "idempotent_noop")
        events = practice.read_jsonl(
            self.workspace / "practice-analysis" / "result-imports.jsonl"
        )
        self.assertEqual(len(events), 1)

    def test_unanchored_v2_is_audit_only_and_never_ready(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        result = self.valid_v2_result(request)
        result_path = self.root / "unanchored.json"
        _write_json(result_path, result)
        imported = practice.import_result(
            self.workspace,
            result_path,
            request_id=request["handoff_id"],
        )
        self.assertEqual(imported["status"], "audit_only_unanchored")
        self.assertFalse(imported["eligible_for_drafting"])
        state = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(state["claims"][0]["state"], "blocked")

    def test_attached_source_is_revalidated_and_missing_or_changed_source_stales(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        attachment = self.attach_with_fake_sibling(request)
        result = self.valid_v2_result(request)
        result_path = self.root / "anchored.json"
        _write_json(result_path, result)
        imported = practice.import_result(
            self.workspace,
            result_path,
            request_id=request["handoff_id"],
        )
        self.assertTrue(imported["eligible_for_drafting"])
        self.assertEqual(imported["anchor_status"], "valid")
        source_workspace = Path(attachment["cassation_workspace"])
        (source_workspace / "tampered.flag").write_text("changed", encoding="utf-8")
        state = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(state["claims"][0]["state"], "stale")
        self.assertIn("trusted_source_changed", state["claims"][0]["blocking_reasons"])

    def test_incomplete_adverse_rejected_card_and_wrong_validation_gate_are_rejected(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        for label, mutate, pattern in (
            (
                "adverse",
                lambda result: result["payload"]["selected_proofs"]["adverse"].__setitem__("complete", False),
                "adverse",
            ),
            (
                "position",
                lambda result: result["payload"]["selected_proofs"]["position_cards"][0].__setitem__("human_review", "rejected"),
                "position",
            ),
            (
                "gate",
                lambda result: result["payload"]["selected_proofs"]["validation_report"].__setitem__("gate", "other"),
                "gate",
            ),
        ):
            with self.subTest(label=label):
                result = self.valid_v2_result(request)
                mutate(result)
                selected = result["payload"]["selected_proofs"]
                files = practice._proof_file_manifest(selected)
                result["payload"]["artifact_manifest"] = {
                    "files": files,
                    "manifest_sha256": _digest(files),
                }
                result["payload"]["selected_position_set_sha256"] = _digest(
                    {
                        "position_cards": selected["position_cards"],
                        "comparisons": selected["comparisons"],
                        "relations": selected["relations"],
                    }
                )
                result["payload"]["approval_binding"]["validation_report_sha256"] = _digest(
                    selected["validation_report"]
                )
                result = _sign_envelope(result)
                path = self.root / f"{label}.json"
                _write_json(path, result)
                with self.assertRaisesRegex(ValueError, pattern):
                    practice.import_result(
                        self.workspace,
                        path,
                        request_id=request["handoff_id"],
                    )

    def test_missing_result_and_structurally_incomplete_event_fail_closed_without_crash(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        result = self.valid_v2_result(request)
        path = self.root / "result.json"
        _write_json(path, result)
        practice.import_result(self.workspace, path, request_id=request["handoff_id"])
        stored = self.workspace / "practice-analysis" / "results" / f"{result['handoff_id']}.json"
        stored.unlink()
        state = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(state["claims"][0]["state"], "blocked")
        self.assertIn("result_missing", state["claims"][0]["blocking_reasons"])

        events = self.workspace / "practice-analysis" / "result-imports.jsonl"
        events.unlink()
        checkpoint = practice._ledger_checkpoint_path(events)
        checkpoint.unlink(missing_ok=True)
        practice._append_event(
            events,
            {
                "schema_version": "1.0",
                "record_type": "result_import",
                "request_id": request["handoff_id"],
                "eligible_for_drafting": True,
            },
        )
        lint = practice.lint_workspace(self.workspace)
        self.assertFalse(lint["valid"])

    def test_actual_quality_bindings_contract_is_accepted_and_content_bound(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        result = self.valid_v2_result(request)
        required_types = (
            "chain_stage_propagation",
            "uncertainty_profile",
            "coding_audit_plan",
            "coding_reliability",
            "prefiling_refresh",
        )
        result["payload"]["quality_bindings"] = [
            {
                "quality_type": quality_type,
                "artifact_sha256": _digest(artifact := {"quality_type": quality_type}),
                "artifact": artifact,
            }
            for quality_type in required_types
        ]
        result = _sign_envelope(result)
        path = self.root / "quality-result.json"
        _write_json(path, result)
        imported = self.import_with_attached_source(request, path)
        self.assertTrue(imported["eligible_for_drafting"])

    def test_quality_binding_with_resigned_wrong_artifact_hash_is_rejected(self) -> None:
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        result = self.valid_v2_result(request)
        required_types = (
            "chain_stage_propagation",
            "uncertainty_profile",
            "coding_audit_plan",
            "coding_reliability",
            "prefiling_refresh",
        )
        result["payload"]["quality_bindings"] = [
            {
                "quality_type": quality_type,
                "artifact_sha256": "9" * 64,
                "artifact": {"quality_type": quality_type},
            }
            for quality_type in required_types
        ]
        result = _sign_envelope(result)
        path = self.root / "quality-result-tampered.json"
        _write_json(path, result)
        with self.assertRaisesRegex(ValueError, "artifact_sha256"):
            self.import_with_attached_source(request, path)


class TestWordingStagesAndRefresh(PracticeAnalysisTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.claim_source = self.root / "claims.json"
        _write_json(
            self.claim_source,
            {
                "claims": [
                    {
                        "claim_id": "claim-practice",
                        "text": "Суды последовательно придают норме расширительный смысл.",
                        "case_dependency_ids": ["act-a"],
                        "hypothesis_ids": ["hypothesis-practice"],
                        "option_ids": ["option-practice"],
                    },
                    {
                        "claim_id": "claim-direct",
                        "text": "Норма была применена в деле заявителя.",
                        "practice_dependency": False,
                        "case_dependency_ids": ["act-b"],
                        "hypothesis_ids": ["hypothesis-direct"],
                    },
                ]
            },
        )
        practice.scan_input(self.workspace, self.claim_source, now="2026-08-27T10:05:00Z")
        self.request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(self.request)
        self.result = self.valid_v2_result(self.request)
        self.finding_id = self.result["payload"]["findings"][0]["finding_id"]
        self.result_path = self.root / "result.json"
        _write_json(self.result_path, self.result)
        practice.import_result(
            self.workspace,
            self.result_path,
            request_id=self.request["handoff_id"],
            now="2026-08-27T11:02:00Z",
        )

    def review_within_limit(self) -> dict:
        return practice.review_wording(
            self.workspace,
            claim_id="claim-practice",
            handoff_id=self.result["handoff_id"],
            decision="within_limit",
            reviewer="И.И. Иванов",
            reason="Финальная формулировка не сильнее разрешённого предела.",
            finding_ids=[self.finding_id],
            wording_text="Суды последовательно придают норме расширительный смысл.",
            wording_source=self.claim_source,
            now="2026-08-27T11:05:00Z",
        )

    def test_valid_result_needs_human_wording_review_before_ready(self) -> None:
        before = practice.derive_state(self.workspace, stage="drafting")
        before_by_id = {item["claim_id"]: item for item in before["claims"]}
        self.assertEqual(before_by_id["claim-practice"]["state"], "blocked")
        self.assertEqual(before_by_id["claim-direct"]["state"], "not_required")

        review = self.review_within_limit()
        self.assertEqual(review["decision"], "within_limit")
        after = practice.derive_state(self.workspace, stage="drafting")
        after_by_id = {item["claim_id"]: item for item in after["claims"]}
        self.assertEqual(after_by_id["claim-practice"]["state"], "ready")
        self.assertFalse(after_by_id["claim-practice"]["draft_blocked"])

    def test_too_strong_or_unclear_wording_remains_blocked(self) -> None:
        practice.review_wording(
            self.workspace,
            claim_id="claim-practice",
            handoff_id=self.result["handoff_id"],
            decision="too_strong",
            reviewer="И.И. Иванов",
            reason="Текст утверждает всеобщность за пределами корпуса.",
            finding_ids=[self.finding_id],
            wording_text="Суды последовательно придают норме расширительный смысл.",
            wording_source=self.claim_source,
            now="2026-08-27T11:05:00Z",
        )
        state = practice.derive_state(self.workspace, stage="drafting")
        claim = next(item for item in state["claims"] if item["claim_id"] == "claim-practice")
        self.assertEqual(claim["state"], "blocked")
        self.assertIn("too_strong", claim["blocking_reasons"])

    def test_tampered_wording_review_cannot_upgrade_claim(self) -> None:
        practice.review_wording(
            self.workspace,
            claim_id="claim-practice",
            handoff_id=self.result["handoff_id"],
            decision="too_strong",
            reviewer="И.И. Иванов",
            reason="Формулировка выходит за пределы корпуса.",
            finding_ids=[self.finding_id],
            wording_text="Суды последовательно придают норме расширительный смысл.",
            wording_source=self.claim_source,
            now="2026-08-27T11:05:00Z",
        )
        reviews_path = self.workspace / "practice-analysis" / "wording-reviews.jsonl"
        review = json.loads(reviews_path.read_text(encoding="utf-8").strip())
        review["decision"] = "within_limit"
        reviews_path.write_text(json.dumps(review, ensure_ascii=False) + "\n", encoding="utf-8")
        state = practice.derive_state(self.workspace, stage="drafting")
        claim = next(item for item in state["claims"] if item["claim_id"] == "claim-practice")
        self.assertEqual(claim["state"], "blocked")
        self.assertTrue(state["global_integrity_errors"])

    def test_claim_text_change_selectively_invalidates_prior_ready_binding(self) -> None:
        self.review_within_limit()
        _write_json(
            self.claim_source,
            {
                "claims": [
                    {
                        "claim_id": "claim-practice",
                        "text": "Суды всегда и без исключений придают норме расширительный смысл.",
                        "case_dependency_ids": ["act-a"],
                        "hypothesis_ids": ["hypothesis-practice"],
                    },
                    {
                        "claim_id": "claim-direct",
                        "text": "Норма была применена в деле заявителя.",
                        "practice_dependency": False,
                        "case_dependency_ids": ["act-b"],
                        "hypothesis_ids": ["hypothesis-direct"],
                    },
                ]
            },
        )
        practice.scan_input(self.workspace, self.claim_source, now="2026-08-27T11:06:00Z")
        state = practice.derive_state(self.workspace, stage="drafting")
        by_id = {item["claim_id"]: item for item in state["claims"]}
        self.assertEqual(by_id["claim-practice"]["state"], "stale")
        self.assertEqual(by_id["claim-direct"]["state"], "not_required")

    def test_post_import_result_replacement_cannot_preserve_ready_state(self) -> None:
        self.review_within_limit()
        replacement = json.loads(json.dumps(self.result))
        replacement["limitations"] = ["Новый, переподписанный envelope."]
        replacement = _sign_envelope(replacement)
        stored_path = (
            self.workspace
            / "practice-analysis"
            / "results"
            / f"{self.result['handoff_id']}.json"
        )
        _write_json(stored_path, replacement)
        state = practice.derive_state(self.workspace, stage="drafting")
        claim = next(item for item in state["claims"] if item["claim_id"] == "claim-practice")
        self.assertEqual(claim["state"], "blocked")
        self.assertIn("result_integrity_failed", claim["blocking_reasons"])

    def test_tampered_claim_revision_cannot_preserve_ready_state(self) -> None:
        self.review_within_limit()
        ledger_path = self.workspace / "practice-analysis" / "claim-ledger.jsonl"
        records = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
        records[0]["claim_text"] = "Подменённый текст без обновления claim_sha256."
        ledger_path.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
            encoding="utf-8",
        )
        state = practice.derive_state(self.workspace, stage="drafting")
        self.assertTrue(state["global_integrity_errors"])
        claim = next(item for item in state["claims"] if item["claim_id"] == "claim-practice")
        self.assertEqual(claim["state"], "blocked")
        self.assertIn("ledger_integrity_failed", claim["blocking_reasons"])

    def test_stage_validation_is_per_claim_and_filing_requires_refresh(self) -> None:
        drafting_before = practice.validate_workspace(self.workspace, stage="drafting")
        self.assertFalse(drafting_before["valid"])
        self.assertEqual(drafting_before["blocked_claim_ids"], ["claim-practice"])
        self.assertIn("claim-direct", drafting_before["unaffected_claim_ids"])

        self.review_within_limit()
        drafting_after = practice.validate_workspace(self.workspace, stage="drafting")
        filing_before = practice.validate_workspace(self.workspace, stage="filing")
        self.assertTrue(drafting_after["valid"])
        self.assertFalse(filing_before["valid"])
        self.assertIn("prefiling_refresh_required", filing_before["errors"])

        practice.record_refresh(
            self.workspace,
            as_of="2026-08-27",
            reviewer="И.И. Иванов",
            official_check_ref="Официальные источники и corpus cutoff перепроверены.",
            now="2026-08-27T11:10:00Z",
        )
        filing_after = practice.validate_workspace(self.workspace, stage="filing")
        self.assertTrue(filing_after["valid"])

    def test_current_filing_claim_projection_reopens_exact_ready_material(self) -> None:
        self.review_within_limit()
        refresh = practice.record_refresh(
            self.workspace,
            as_of="2026-08-27",
            reviewer="И.И. Иванов",
            official_check_ref="Официальные источники и corpus cutoff перепроверены.",
            now="2026-08-27T11:10:00Z",
        )

        projection = practice.current_filing_claim_projection(
            self.workspace,
            claim_id="claim-practice",
            issue_option_id="option-practice",
            now="2026-08-27T11:11:00Z",
        )

        self.assertEqual(projection["case_id"], "case-1")
        self.assertEqual(projection["claim_state"]["state"], "ready")
        self.assertFalse(projection["claim_state"]["draft_blocked"])
        self.assertEqual(
            projection["wording_review"]["finding_ids"], [self.finding_id]
        )
        self.assertEqual(
            projection["findings"][0]["finding_id"], self.finding_id
        )
        self.assertEqual(projection["issue_option_id"], "option-practice")
        self.assertEqual(
            projection["findings"][0]["claim_wording"],
            projection["wording_review"]["wording_text"],
        )
        self.assertEqual(
            projection["findings"][0]["candidate"]["claim_wording"],
            projection["wording_review"]["wording_text"],
        )
        self.assertEqual(
            projection["ready_binding"]["maximum_permitted_claim"],
            "corroborated_observed_corpus",
        )
        self.assertEqual(
            projection["prefiling_refresh"]["record"]["event_sha256"],
            refresh["event_sha256"],
        )
        self.assertTrue(projection["prefiling_refresh"]["required"])
        self.assertTrue(projection["prefiling_refresh"]["valid"])
        self.assertEqual(projection["filing_validation"]["stage"], "filing")

    def test_current_projection_rejects_source_mutation_after_validation(self) -> None:
        self.review_within_limit()
        practice.record_refresh(
            self.workspace,
            as_of="2026-08-27",
            reviewer="И.И. Иванов",
            official_check_ref="Официальные источники перепроверены.",
            now="2026-08-27T11:10:00Z",
        )
        original_validate = practice.validate_workspace

        def validate_then_mutate(*args, **kwargs):
            report = original_validate(*args, **kwargs)
            source = json.loads(self.claim_source.read_text(encoding="utf-8"))
            source["tampered_after_validation"] = True
            _write_json(self.claim_source, source)
            return report

        with mock.patch.object(
            practice,
            "validate_workspace",
            side_effect=validate_then_mutate,
        ):
            with self.assertRaisesRegex(ValueError, "изменился"):
                practice.current_filing_claim_projection(
                    self.workspace,
                    claim_id="claim-practice",
                    issue_option_id="option-practice",
                    now="2026-08-27T11:11:00Z",
                )

    def test_current_projection_rejects_report_level_integrity_error(self) -> None:
        self.review_within_limit()
        practice.record_refresh(
            self.workspace,
            as_of="2026-08-27",
            reviewer="И.И. Иванов",
            official_check_ref="Официальные источники перепроверены.",
            now="2026-08-27T11:10:00Z",
        )
        original_validate = practice.validate_workspace

        def validate_with_report_error(*args, **kwargs):
            report = json.loads(json.dumps(original_validate(*args, **kwargs)))
            report["valid"] = False
            report["global_integrity_errors"] = ["concurrent_validation_error"]
            return report

        with mock.patch.object(
            practice,
            "validate_workspace",
            side_effect=validate_with_report_error,
        ):
            with self.assertRaisesRegex(ValueError, "global integrity"):
                practice.current_filing_claim_projection(
                    self.workspace,
                    claim_id="claim-practice",
                    issue_option_id="option-practice",
                    now="2026-08-27T11:11:00Z",
                )

    def test_current_projection_requires_exact_issue_option(self) -> None:
        self.review_within_limit()
        practice.record_refresh(
            self.workspace,
            as_of="2026-08-27",
            reviewer="И.И. Иванов",
            official_check_ref="Официальные источники перепроверены.",
            now="2026-08-27T11:10:00Z",
        )

        with self.assertRaisesRegex(ValueError, "exact issue_option_id"):
            practice.current_filing_claim_projection(
                self.workspace,
                claim_id="claim-practice",
                issue_option_id="option-foreign",
                now="2026-08-27T11:11:00Z",
            )

    def test_current_projection_rechecks_finding_and_candidate_wording(self) -> None:
        self.review_within_limit()
        practice.record_refresh(
            self.workspace,
            as_of="2026-08-27",
            reviewer="И.И. Иванов",
            official_check_ref="Официальные источники перепроверены.",
            now="2026-08-27T11:10:00Z",
        )
        stored_result = (
            self.workspace
            / "practice-analysis"
            / "results"
            / f"{self.result['handoff_id']}.json"
        ).resolve()
        original_validate = practice.validate_workspace
        original_read = practice._read_json

        for target in ("finding", "candidate"):
            with self.subTest(target=target):
                validation_finished = False

                def validate_then_project(*args, **kwargs):
                    nonlocal validation_finished
                    report = original_validate(*args, **kwargs)
                    validation_finished = True
                    return report

                def read_with_wording_substitution(path):
                    value = original_read(path)
                    if validation_finished and Path(path).resolve() == stored_result:
                        value = json.loads(json.dumps(value))
                        finding = value["payload"]["findings"][0]
                        if target == "finding":
                            finding["claim_wording"] = "Подменённая формулировка."
                        else:
                            finding["candidate"]["claim_wording"] = (
                                "Подменённая формулировка."
                            )
                    return value

                with mock.patch.object(
                    practice,
                    "validate_workspace",
                    side_effect=validate_then_project,
                ), mock.patch.object(
                    practice,
                    "_read_json",
                    side_effect=read_with_wording_substitution,
                ):
                    with self.assertRaisesRegex(ValueError, "wording"):
                        practice.current_filing_claim_projection(
                            self.workspace,
                            claim_id="claim-practice",
                            issue_option_id="option-practice",
                            now="2026-08-27T11:11:00Z",
                        )

    def test_refresh_binds_exact_material_events_and_later_same_day_wording_invalidates_it(self) -> None:
        self.review_within_limit()
        refresh = practice.record_refresh(
            self.workspace,
            as_of="2026-08-27",
            reviewer="И.И. Иванов",
            official_check_ref="Официальные источники перепроверены.",
            now="2026-08-27T11:10:00Z",
        )
        binding = refresh["ready_claim_bindings"][0]
        for field in (
            "revision_id",
            "source_file_sha256",
            "input_bindings_sha256",
            "input_manifest_updated_at",
            "wording_review_event_sha256",
            "wording_reviewed_at",
            "result_import_event_sha256",
            "result_imported_at",
            "result_source_sha256",
            "attachment_event_sha256",
            "attachment_attached_at",
            "anchor_checked_at",
            "trust_anchor_sha256",
        ):
            self.assertTrue(binding[field], field)

        practice.review_wording(
            self.workspace,
            claim_id="claim-practice",
            handoff_id=self.result["handoff_id"],
            decision="within_limit",
            reviewer="И.И. Иванов",
            reason="Повторная проверка формулировки позднее в тот же день.",
            finding_ids=[self.finding_id],
            wording_text="Суды последовательно придают норме расширительный смысл.",
            wording_source=self.claim_source,
            now="2026-08-27T11:11:00Z",
        )
        filing = practice.validate_workspace(
            self.workspace,
            stage="filing",
            now="2026-08-27T11:12:00Z",
        )
        self.assertFalse(filing["valid"])
        self.assertFalse(filing["state"]["prefiling_refresh"]["valid"])
        self.assertIn("prefiling_refresh_required", filing["errors"])

    def test_newer_attachment_invalidates_prior_result_trust_binding_selectively(self) -> None:
        self.review_within_limit()
        practice.record_refresh(
            self.workspace,
            as_of="2026-08-27",
            reviewer="И.И. Иванов",
            official_check_ref="Официальные источники перепроверены.",
            now="2026-08-27T11:10:00Z",
        )
        self.attach_with_fake_sibling(self.request)
        drafting = practice.validate_workspace(
            self.workspace,
            stage="drafting",
            now="2026-08-27T11:12:00Z",
        )
        by_id = {item["claim_id"]: item for item in drafting["state"]["claims"]}
        self.assertEqual(by_id["claim-practice"]["state"], "stale")
        self.assertIn(
            "attachment_changed_since_result",
            by_id["claim-practice"]["blocking_reasons"],
        )
        self.assertEqual(by_id["claim-direct"]["state"], "not_required")

    def test_wording_review_stales_when_reviewed_text_or_source_file_changes(self) -> None:
        self.review_within_limit()
        payload = json.loads(self.claim_source.read_text(encoding="utf-8"))
        payload["claims"][0]["text"] = "Все суды всегда нарушают закон без исключений."
        _write_json(self.claim_source, payload)
        state = practice.derive_state(self.workspace, stage="drafting")
        claim = next(item for item in state["claims"] if item["claim_id"] == "claim-practice")
        self.assertEqual(claim["state"], "stale")
        self.assertIn("source_file_changed", claim["blocking_reasons"])
        self.assertIn("rescan_required", claim["blocking_reasons"])

    def test_wording_review_rejects_finding_of_another_claim(self) -> None:
        stored_path = (
            self.workspace
            / "practice-analysis"
            / "results"
            / f"{self.result['handoff_id']}.json"
        )
        stored = json.loads(stored_path.read_text(encoding="utf-8"))
        finding = stored["payload"]["findings"][0]
        finding["claim_ids"] = ["different-claim"]
        _write_json(stored_path, stored)
        with self.assertRaisesRegex(ValueError, "текущему claim"):
            practice.review_wording(
                self.workspace,
                claim_id="claim-practice",
                handoff_id=self.result["handoff_id"],
                decision="within_limit",
                reviewer="И.И. Иванов",
                reason="Неверная привязка.",
                finding_ids=[self.finding_id],
                wording_text="Суды последовательно придают норме расширительный смысл.",
                wording_source=self.claim_source,
            )

    def test_ancient_or_pre_result_refresh_cannot_enable_filing(self) -> None:
        self.review_within_limit()
        with self.assertRaisesRegex(ValueError, "свеж"):
            practice.record_refresh(
                self.workspace,
                as_of="2000-01-01",
                reviewer="И.И. Иванов",
                official_check_ref="Проверено.",
                now="2026-08-27T11:10:00Z",
            )
        practice.record_refresh(
            self.workspace,
            as_of="2026-08-27",
            reviewer="И.И. Иванов",
            official_check_ref="Проверено.",
            corpus_cutoff="2026-08-27",
            now="2026-08-27T11:10:00Z",
        )
        self.assertTrue(practice.validate_workspace(self.workspace, stage="filing")["valid"])

    def test_changed_claim_does_not_block_independent_claim_in_shared_result(self) -> None:
        # The direct claim is made practice-dependent and the shared result is rebound to both.
        payload = json.loads(self.claim_source.read_text(encoding="utf-8"))
        payload["claims"][1]["text"] = "Суды последовательно применяют норму к другой ситуации."
        payload["claims"][1]["practice_dependency"] = True
        _write_json(self.claim_source, payload)
        practice.scan_input(self.workspace, self.claim_source, now="2026-08-27T11:11:00Z")
        # A fresh independent request/result is needed for the changed claim set.
        request = practice.create_request(self.workspace, now="2026-08-27T11:12:00Z")
        self.attach_with_fake_sibling(request)
        result = self.valid_v2_result(request)
        result_path = self.root / "shared.json"
        _write_json(result_path, result)
        practice.import_result(self.workspace, result_path, request_id=request["handoff_id"])
        finding_id = result["payload"]["findings"][0]["finding_id"]
        wording_sources: dict[str, Path] = {}
        for claim_id, wording in (
            ("claim-practice", payload["claims"][0]["text"]),
            ("claim-direct", payload["claims"][1]["text"]),
        ):
            wording_source = self.root / f"{claim_id}.txt"
            wording_source.write_text(wording, encoding="utf-8")
            wording_sources[claim_id] = wording_source
            practice.review_wording(
                self.workspace,
                claim_id=claim_id,
                handoff_id=result["handoff_id"],
                decision="within_limit",
                reviewer="И.И. Иванов",
                reason="В пределах.",
                finding_ids=[finding_id],
                wording_text=wording,
                wording_source=wording_source,
            )
        payload["claims"][0]["text"] = "После 2023 года подход изменился."
        _write_json(self.claim_source, payload)
        practice.scan_input(self.workspace, self.claim_source, now="2026-08-27T11:13:00Z")
        state = {item["claim_id"]: item for item in practice.derive_state(self.workspace)["claims"]}
        self.assertEqual(state["claim-practice"]["state"], "stale")
        self.assertEqual(state["claim-direct"]["state"], "ready")


class TestLintSchemaAndCli(PracticeAnalysisTestCase):
    def test_validate_workspace_rejects_concurrent_ledger_mutation_before_publication(self) -> None:
        self.scan_claims(
            [
                {
                    "claim_id": "claim-direct",
                    "text": "Норма применена в деле заявителя.",
                    "practice_dependency": False,
                }
            ]
        )
        real_derive = practice.derive_state

        def derive_then_mutate(*args, **kwargs):
            state = real_derive(*args, **kwargs)
            claim = practice._active_claims(self.workspace)["claim-direct"]
            practice._append_event(
                self.workspace / "practice-analysis" / "trigger-reviews.jsonl",
                {
                    "schema_version": "1.0",
                    "record_type": "trigger_review",
                    "claim_id": "claim-direct",
                    "revision_id": claim["revision_id"],
                    "claim_sha256": claim["claim_sha256"],
                    "decision": "required",
                    "reviewer": "Unsynchronized writer",
                    "reason": "Мутация после построения state.",
                    "reviewed_at": "2026-08-27T10:06:00Z",
                },
            )
            return state

        with mock.patch.object(practice, "derive_state", side_effect=derive_then_mutate):
            report = practice.validate_workspace(
                self.workspace,
                stage="drafting",
                now="2026-08-27T10:07:00Z",
            )
        self.assertFalse(report["valid"])
        self.assertIn("workspace_changed_during_validation", report["errors"])

    def test_workspace_transaction_closes_post_snapshot_publication_window(self) -> None:
        self.scan_claims(
            [
                {
                    "claim_id": "claim-direct",
                    "text": "Норма применена в деле заявителя.",
                    "practice_dependency": False,
                }
            ]
        )
        publication_reached = threading.Event()
        mutation_started = threading.Event()
        mutation_finished = threading.Event()
        real_atomic_write = practice._atomic_write_json

        def mutate_after_snapshot() -> None:
            publication_reached.wait(timeout=2)
            mutation_started.set()
            practice.review_trigger(
                self.workspace,
                claim_id="claim-direct",
                decision="required",
                reviewer="Concurrent reviewer",
                reason="Мутация в прежнем post-snapshot окне.",
                now="2026-08-27T10:06:00Z",
            )
            mutation_finished.set()

        mutator = threading.Thread(target=mutate_after_snapshot)
        mutator.start()

        def pause_at_validation_publication(path, value):
            if Path(path).name == practice.VALIDATION_FILE:
                publication_reached.set()
                self.assertTrue(mutation_started.wait(timeout=2))
                self.assertFalse(mutation_finished.wait(timeout=0.05))
            return real_atomic_write(path, value)

        with mock.patch.object(
            practice,
            "_atomic_write_json",
            side_effect=pause_at_validation_publication,
        ):
            returned = practice.validate_workspace(
                self.workspace,
                stage="drafting",
                now="2026-08-27T10:07:00Z",
            )
        mutator.join(timeout=2)
        self.assertFalse(mutator.is_alive())
        self.assertTrue(returned["valid"])

        persisted = json.loads(
            (
                self.workspace
                / "practice-analysis"
                / practice.VALIDATION_FILE
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(persisted["valid"])
        self.assertIn("workspace_changed_since_validation", persisted["errors"])
        current = practice.derive_state(self.workspace, stage="drafting")
        self.assertEqual(current["claims"][0]["state"], "required")

    def test_lint_reports_corrupt_append_only_ledger_in_russian(self) -> None:
        ledger = self.workspace / "practice-analysis" / "claim-ledger.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text("{повреждено\n", encoding="utf-8")
        result = practice.lint_workspace(self.workspace)
        self.assertFalse(result["valid"])
        self.assertIn("строк", " ".join(result["errors"]).lower())

    def test_schema_declares_states_claims_and_stage_verdict(self) -> None:
        self.assertTrue(SCHEMA_PATH.exists(), f"Не создана схема: {SCHEMA_PATH}")
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        state_enum = schema["$defs"]["claim_state"]["enum"]
        self.assertEqual(
            state_enum,
            ["not_required", "required", "running", "blocked", "ready", "stale"],
        )
        gate_required = schema["$defs"]["practice_analysis_gate"]["required"]
        self.assertIn("claims", gate_required)
        self.assertIn("stage_verdict", gate_required)
        self.assertFalse(schema["$defs"]["claim_revision"]["additionalProperties"])
        self.assertFalse(schema["$defs"]["practice_request_v2"]["additionalProperties"])
        self.assertFalse(schema["$defs"]["practice_result_v2"]["additionalProperties"])
        self.assertIn("ledger_event", schema["$defs"])

    def test_cli_returns_actionable_nonzero_validation_result(self) -> None:
        claims = self.root / "claims.json"
        _write_json(
            claims,
            {"claims": [{"claim_id": "claim-a", "text": "Сложились два судебных подхода."}]},
        )
        practice.scan_input(self.workspace, claims, now="2026-08-27T10:05:00Z")
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = practice.main(
                ["validate", "--workspace", str(self.workspace), "--stage", "qa"]
            )
        self.assertEqual(exit_code, 2)
        self.assertIn("blocking_empirical_overclaim", output.getvalue())


class TestAdversarialIntegrityAndCoverage(PracticeAnalysisTestCase):
    def test_closed_event_contract_rejects_unknown_fields(self) -> None:
        self.scan_claims(
            [{"claim_id": "claim-a", "text": "Судебная практика противоречива."}]
        )
        claim = practice._active_claims(self.workspace)["claim-a"]
        practice._append_event(
            self.workspace / "practice-analysis" / "trigger-reviews.jsonl",
            {
                "schema_version": "1.0",
                "record_type": "trigger_review",
                "claim_id": "claim-a",
                "revision_id": claim["revision_id"],
                "claim_sha256": claim["claim_sha256"],
                "decision": "required",
                "reviewer": "Reviewer",
                "reason": "Нужен корпус.",
                "reviewed_at": "2026-08-27T10:00:00Z",
                "unexpected_authority": "must-not-pass",
            },
        )
        lint = practice.lint_workspace(self.workspace)
        self.assertFalse(lint["valid"])
        self.assertTrue(any("неизвестные поля" in error for error in lint["errors"]))

    def test_closed_claim_contract_rejects_fully_rehashed_unknown_fields(self) -> None:
        self.scan_claims(
            [{"claim_id": "claim-a", "text": "Судебная практика противоречива."}]
        )
        ledger = self.workspace / "practice-analysis" / "claim-ledger.jsonl"
        record = practice.read_jsonl(ledger)[0]
        for field in ("ledger_id", "sequence", "previous_event_sha256", "event_sha256"):
            record.pop(field, None)
        ledger.unlink()
        practice._ledger_checkpoint_path(ledger).unlink(missing_ok=True)
        record["unexpected_authority"] = "must-not-pass"
        practice._append_event(ledger, record)
        lint = practice.lint_workspace(self.workspace)
        self.assertFalse(lint["valid"])
        self.assertTrue(any("неизвестные поля" in error for error in lint["errors"]))

    def test_closed_v2_result_rejects_resigned_unknown_payload_fields(self) -> None:
        self.scan_claims(
            [{"claim_id": "claim-a", "text": "Судебная практика противоречива."}]
        )
        request = practice.create_request(self.workspace, now="2026-08-27T10:10:00Z")
        self.attach_with_fake_sibling(request)
        result = self.valid_v2_result(request)
        result["payload"]["unexpected_authority"] = "must-not-pass"
        result = _sign_envelope(result)
        path = self.root / "result-extra-field.json"
        _write_json(path, result)
        with self.assertRaisesRegex(ValueError, "ровно canonical"):
            self.import_with_attached_source(request, path)

    def test_frequency_and_court_specific_empirical_claims_trigger_but_question_does_not(self) -> None:
        positives = (
            "Во всех изученных делах суды отказывают работникам в премии.",
            "Второй КСОЮ чаще поддерживает работодателей.",
            "Подходы судов к выплате премии различаются.",
        )
        for text in positives:
            with self.subTest(text=text):
                self.assertTrue(practice._detect_triggers(text)[1])
        self.assertFalse(
            practice._detect_triggers(
                "Нужно проверить, различаются ли подходы судов к выплате премии?"
            )[1]
        )

    def test_reordered_or_truncated_ledger_is_detected(self) -> None:
        self.scan_claims(
            [{"claim_id": "claim-a", "text": "Судебная практика противоречива."}]
        )
        practice.review_trigger(
            self.workspace,
            claim_id="claim-a",
            decision="required",
            reviewer="Reviewer",
            reason="Нужен корпус.",
        )
        practice.review_trigger(
            self.workspace,
            claim_id="claim-a",
            decision="not_required",
            reviewer="Reviewer",
            reason="Фраза является вопросом.",
        )
        ledger = self.workspace / "practice-analysis" / "trigger-reviews.jsonl"
        lines = ledger.read_text(encoding="utf-8").splitlines()
        ledger.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")
        self.assertFalse(practice.lint_workspace(self.workspace)["valid"])
        ledger.write_text(lines[0] + "\n", encoding="utf-8")
        self.assertFalse(practice.lint_workspace(self.workspace)["valid"])

    def test_claim_revision_reorder_and_broken_supersedes_are_detected(self) -> None:
        source = self.root / "claims.json"
        _write_json(source, {"claims": [{"claim_id": "claim-a", "text": "Суды толкуют норму единообразно."}]})
        practice.scan_input(self.workspace, source)
        _write_json(source, {"claims": [{"claim_id": "claim-a", "text": "Суды толкуют норму противоречиво."}]})
        practice.scan_input(self.workspace, source)
        ledger = self.workspace / "practice-analysis" / "claim-ledger.jsonl"
        lines = ledger.read_text(encoding="utf-8").splitlines()
        ledger.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")
        self.assertFalse(practice.lint_workspace(self.workspace)["valid"])

    def test_scan_tombstones_claim_removed_from_same_source(self) -> None:
        source = self.root / "claims.json"
        _write_json(
            source,
            {"claims": [
                {"claim_id": "claim-a", "text": "Судебная практика противоречива."},
                {"claim_id": "claim-b", "text": "Суды последовательно толкуют норму."},
            ]},
        )
        practice.scan_input(self.workspace, source)
        _write_json(source, {"claims": [{"claim_id": "claim-a", "text": "Судебная практика противоречива."}]})
        practice.scan_input(self.workspace, source)
        self.assertNotIn("claim-b", practice._active_claims(self.workspace))

    def test_concurrent_append_preserves_all_events(self) -> None:
        path = self.workspace / "practice-analysis" / "concurrent.jsonl"
        barrier = threading.Barrier(20)
        failures: list[Exception] = []

        def append(index: int) -> None:
            try:
                barrier.wait()
                practice._append_event(path, {"record_type": "test", "index": index})
            except Exception as exc:  # pragma: no cover - assertion reports failures
                failures.append(exc)

        threads = [threading.Thread(target=append, args=(index,)) for index in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(failures, [])
        self.assertEqual(len(practice.read_jsonl(path)), 20)
        self.assertEqual(practice._ledger_integrity_errors(path), [])

    def test_request_rejects_path_traversal_and_pseudonymizes_private_fields(self) -> None:
        self.scan_claims(
            [{
                "claim_id": "Иванов-ivanov@example.com",
                "text": "Судебная практика противоречива.",
                "source_locator": "/Users/ivanov/Дело Иванова/жалоба.docx#Иванов",
            }]
        )
        request = practice.create_request(self.workspace)
        binding = request["payload"]["claim_bindings"][0]
        self.assertNotIn("Иванов", binding["claim_id"])
        self.assertNotIn("ivanov", binding["claim_id"])
        self.assertNotIn("/Users/", binding["source_locator"])
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            practice._request_by_id(self.workspace, "../../../outside")

    def test_docx_footnote_is_scanned_and_oversize_entry_is_blocked(self) -> None:
        docx = self.root / "footnote.docx"
        namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        with zipfile.ZipFile(docx, "w") as archive:
            archive.writestr(
                "word/document.xml",
                f'<w:document xmlns:w="{namespace}"><w:body><w:p/></w:body></w:document>',
            )
            archive.writestr(
                "word/footnotes.xml",
                f'<w:footnotes xmlns:w="{namespace}"><w:footnote w:id="1"><w:p><w:r><w:t>Судебная практика противоречива.</w:t></w:r></w:p></w:footnote></w:footnotes>',
            )
        result = practice.scan_input(self.workspace, docx)
        self.assertEqual(result["claims"][0]["empirical_dimensions"], ["split"])

        bomb = self.root / "bomb.docx"
        with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", "x" * (practice.MAX_DOCX_PART_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "лимит"):
            practice.scan_input(self.workspace, bomb)


if __name__ == "__main__":
    unittest.main()
