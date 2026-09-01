# pyright: reportMissingImports=false, reportMissingModuleSource=false
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = SKILL_ROOT / "lib"
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))

from ksrf.filing.application_evidence import (  # noqa: E402
    application_review_approval_request,
    application_record_content_fingerprint,
    application_record_from_dict,
    assess_application_chain,
    build_preservation_rule_evidence,
    preservation_rule_review_approval_request,
)
from ksrf.filing.composer import (  # noqa: E402
    ComplaintModelError,
    REQUIRED_SECTION_CODES,
    build_structured_complaint,
    require_release_support,
)
from ksrf.filing.holding_binding import (  # noqa: E402
    build_holding_binding_index_resolution,
)
from ksrf.filing.issue_options import (  # noqa: E402
    issue_approval_requests,
    issue_candidate_content_fingerprint,
    issue_candidate_from_dict,
)
from ksrf.filing.norm_versions import (  # noqa: E402
    norm_version_passport_content_fingerprint,
    norm_version_review_approval_request,
)
from ksrf.filing.relief_binding import (  # noqa: E402
    build_relief_binding_index_resolution,
)
from ksrf.filing.release import release_basis_sha256, verify_release_manifest  # noqa: E402


SCHEMA_PATH = SKILL_ROOT / "schemas" / "ksrf_filing" / "structured-complaint.schema.json"
FILING_SCHEMA_PATH = SKILL_ROOT / "schemas" / "ksrf_filing" / "filing-package.schema.json"


def _gate(rationale: str) -> dict[str, Any]:
    return {
        "state": "passed",
        "rationale": rationale,
        "evidence_ids": ["AUTH-1"],
        "requires_human_review": False,
    }


def _issue_payload(
    claim_id: str,
    issue_id: str,
    evidence_id: str,
    remedy_text: str,
    *,
    norm_id: str = "NORM-1",
    norm_version_id: str = "EDITION-1",
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "issue_id": issue_id,
        "seed_id": f"SEED-{claim_id}",
        "claim_id": claim_id,
        "object_of_review": {
            "norm_id": norm_id,
            "norm_version_id": norm_version_id,
        },
        "theory_code": "legal_uncertainty",
        "normative_meaning": "Оспариваемый нормативный смысл",
        "application_proof": {
            "evidence_ids": [evidence_id],
            "gate_passed": True,
        },
        "constitutional_benchmarks": ["ст. 19 Конституции РФ"],
        "rights_impairment": "Нарушено равенство",
        "anti_fourth_instance_boundary": "Оспаривается нормативный смысл",
        "ksrf_authority_ids": ["KSRF-1"],
        "adverse_authority": {
            "authority_ids": ["KSRF-ADVERSE-1"],
            "summary": "Учтена неблагоприятная практика",
            "delta": "Фактическое отличие проверено",
        },
        "requested_remedy": remedy_text,
        "strengths": ["Точная привязка"],
        "weaknesses": ["Нужна ручная проверка"],
        "source_gaps": [],
        "model_rank": 1,
        "gates": {
            "anti_fourth_instance": _gate("Граница соблюдена"),
            "practice_claims": [],
            "adverse_authority": _gate("Неблагоприятная практика разрешена"),
            "remedy": _gate("Просьба в компетенции КС РФ"),
        },
        "human_selection": {
            "state": "principal",
            "reviewer": "Проверяющий",
            "reviewed_at": "2026-09-01T10:00:00Z",
            "note": "Выбрано человеком",
        },
    }


def _application_payload(
    claim_id: str,
    record_id: str,
    evidence_id: str,
    *,
    norm_id: str = "NORM-1",
    norm_version_id: str = "EDITION-1",
    locator_value: str = "абз. 12",
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "record_id": record_id,
        "claim_id": claim_id,
        "norm_id": norm_id,
        "norm_version_id": norm_version_id,
        "normative_meaning_id": f"MEANING-{claim_id}",
        "act_id": f"ACT-{claim_id}",
        "stage": "cassation",
        "stage_order": 1,
        "norm_use_status": "direct_reasoned_use",
        "outcome_causation": "determinative",
        "preservation_exhaustion": "raised_and_reviewed",
        "relation_to_prior": "initial",
        "incorporated_record_ids": [],
        "evidence": [
            {
                "evidence_id": evidence_id,
                "claim_id": claim_id,
                "norm_id": norm_id,
                "act_id": f"ACT-{claim_id}",
                "stage": "cassation",
                "source_kind": "full_act",
                "locator": {"kind": "paragraph", "value": locator_value},
                "quote": "Суд применил оспариваемую норму",
                "speaker": "court",
                "reasoning_role": "express_norm_use",
                "inference_status": "observed",
            },
            {
                "evidence_id": f"{evidence_id}-RULE",
                "claim_id": claim_id,
                "norm_id": norm_id,
                "act_id": f"ACT-{claim_id}",
                "stage": "cassation",
                "source_kind": "full_act",
                "locator": {"kind": "paragraph", "value": f"{locator_value}.1"},
                "quote": "Суд сформулировал применённое правило",
                "speaker": "court",
                "reasoning_role": "operative_rule",
                "inference_status": "observed",
            },
            {
                "evidence_id": f"{evidence_id}-OUTCOME",
                "claim_id": claim_id,
                "norm_id": norm_id,
                "act_id": f"ACT-{claim_id}",
                "stage": "cassation",
                "source_kind": "full_act",
                "locator": {"kind": "paragraph", "value": f"{locator_value}.2"},
                "quote": "Применение нормы определило исход дела",
                "speaker": "court",
                "reasoning_role": "outcome_link",
                "inference_status": "observed",
            }
        ],
        "implicit_premises": [],
        "affirmative_non_application": None,
        "human_review": {"state": "pending", "note": ""},
        "decision_rationale": "Прямое применение подтверждено",
    }


def _passport_payload(
    passport_id: str,
    *,
    norm_id: str = "NORM-1",
    norm_version_id: str = "EDITION-1",
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "passport_id": passport_id,
        "passport_revision_id": f"REV-{passport_id}",
        "norm_id": norm_id,
        "canonical_citation": "ст. 1 ТК РФ",
        "issuing_authority": "Федеральный законодатель",
        "official_publication_identity": "publication-1",
        "amendment_acts": [],
        "legal_timepoints": [],
        "edition_segments": [
            {
                "edition_id": norm_version_id,
                "valid_from": "2020-01-01",
                "valid_to": None,
            }
        ],
        "provider_assertions": [],
        "unresolved_conflicts": [],
        "timepoint_edition_map": {},
    }


def _base_receipt(fingerprint: str) -> dict[str, Any]:
    return {
        "passed": True,
        "content_fingerprint": fingerprint,
    }


def _issue_receipt(issue: Any) -> dict[str, Any]:
    requests = issue_approval_requests(issue)
    return {
        **_base_receipt(issue_candidate_content_fingerprint(issue)),
        "approval_requests": requests,
        "trusted_approval_ids": {
            key: f"APPROVAL-ISSUE-{key}"
            for key in sorted(requests)
        },
    }


def _norm_receipt(passport: dict[str, Any]) -> dict[str, Any]:
    return {
        **_base_receipt(
            norm_version_passport_content_fingerprint(passport)
        ),
        "approval_request": norm_version_review_approval_request(passport),
        "trusted_approval_id": "APPROVAL-NORM-VERSION",
    }


def _application_receipt(
    application: Any,
    records: list[Any],
    passport: dict[str, Any],
    norm_receipt: dict[str, Any],
) -> dict[str, Any]:
    chain = assess_application_chain(records)
    preservation_rule = build_preservation_rule_evidence(
        application,
        rule_status="verified_not_required",
        rule_citation="ст. 96 ФКЗ о КС РФ",
        rule_statement="Дополнительное сохранение возражения не требуется",
        evidence_ids=["PRESERVATION-OFFICIAL-1"],
    )
    preservation_approval_id = "APPROVAL-PRESERVATION"
    approval_request = application_review_approval_request(
        application,
        chain,
        norm_version_status="verified",
        version_evidence_ids=(),
        preservation_rule_status="verified_not_required",
        norm_version_passport=passport,
        norm_version_approval_id=norm_receipt["trusted_approval_id"],
        preservation_rule_evidence=preservation_rule,
        preservation_rule_approval_id=preservation_approval_id,
    )
    return {
        "record_id": application.record_id,
        **_base_receipt(application_record_content_fingerprint(application)),
        "approval_request": approval_request,
        "trusted_approval_id": "APPROVAL-APPLICATION",
        "preservation_rule_evidence": preservation_rule,
        "preservation_rule_gate_receipt": {
            **_base_receipt(preservation_rule["content_fingerprint"]),
            "approval_request": preservation_rule_review_approval_request(
                preservation_rule
            ),
            "trusted_approval_id": preservation_approval_id,
        },
    }


def _resolution(
    claim_id: str,
    issue_id: str,
    passport_id: str,
    record_id: str,
    evidence_id: str,
    remedy_text: str,
) -> dict[str, Any]:
    issue_payload = _issue_payload(claim_id, issue_id, evidence_id, remedy_text)
    application_payload = _application_payload(claim_id, record_id, evidence_id)
    passport_payload = _passport_payload(passport_id)
    issue = issue_candidate_from_dict(issue_payload)
    application = application_record_from_dict(application_payload)
    norm_receipt = _norm_receipt(passport_payload)
    return {
        "status": "verified",
        "issue_option": issue_payload,
        "norm_version_passport": passport_payload,
        "application_records": [application_payload],
        "claim_evidence": [],
        "issue_gate_receipt": _issue_receipt(issue),
        "norm_version_gate_receipt": norm_receipt,
        "application_gate_receipts": [
            _application_receipt(
                application,
                [application],
                passport_payload,
                norm_receipt,
            )
        ],
    }


class StaticAuthority:
    def __init__(self, resolutions: dict[str, dict[str, Any]]) -> None:
        self.resolutions = resolutions
        self.binding_requests: dict[str, dict[str, Any]] = {}
        self.binding_index_snapshot: list[dict[str, str]] | None = None
        self.index_authority_revision_id = "DRAFT-REGISTRY-REV-1"
        self.index_checked_at = "2026-09-01T10:00:00Z"

    def resolve_relief_evidence_binding(
        self, request: dict[str, Any]
    ) -> dict[str, Any] | None:
        sentence_id = request["sentence_id"]
        resolution = self.resolutions.get(sentence_id)
        if resolution is None:
            return None
        self.binding_requests[sentence_id] = copy.deepcopy(request)
        result = copy.deepcopy(resolution)
        result["relief_binding_sha256"] = request["relief_binding_sha256"]
        return result

    def resolve_relief_evidence_binding_index(
        self, request: dict[str, Any]
    ) -> dict[str, Any]:
        if self.binding_index_snapshot is None:
            self.binding_index_snapshot = [
                {
                    "sentence_id": item["sentence_id"],
                    "section_code": "requested_remedy",
                    "role": "requested_remedy",
                    "relief_binding_sha256": item["relief_binding_sha256"],
                }
                for item in sorted(
                    self.binding_requests.values(),
                    key=lambda value: value["sentence_id"],
                )
            ]
        return build_relief_binding_index_resolution(
            matter_id=request["matter_id"],
            draft_id=request["draft_id"],
            bindings=self.binding_index_snapshot,
            authority_revision_id=self.index_authority_revision_id,
            checked_at=self.index_checked_at,
        )


def _sentence(
    sentence_id: str,
    claim_id: str,
    issue_id: str,
    passport_id: str,
    record_id: str,
    evidence_id: str,
    text: str,
) -> dict[str, Any]:
    return {
        "sentence_id": sentence_id,
        "text": text,
        "role": "requested_remedy",
        "evidence_ids": [evidence_id],
        "support_status": "verified",
        "claim_id": claim_id,
        "issue_option_id": issue_id,
        "norm_passport_id": passport_id,
        "application_record_ids": [record_id],
    }


def _complaint_payload(
    remedy_sentences: list[dict[str, Any]],
    *,
    issue_option_ids: list[str] | None = None,
    norm_passport_ids: list[str] | None = None,
) -> dict[str, Any]:
    sections = []
    for code in REQUIRED_SECTION_CODES:
        sentences: list[dict[str, Any]] = []
        if code == "requested_remedy":
            sentences = copy.deepcopy(remedy_sentences)
        sections.append(
            {
                "code": code,
                "heading": f"Раздел {code}",
                "sentences": sentences,
            }
        )
    return {
        "matter_id": "MATTER-1",
        "draft_id": "DRAFT-1",
        "title": "Жалоба",
        "sections": sections,
        "norm_passport_ids": norm_passport_ids or [],
        "issue_option_ids": issue_option_ids or [],
        "issue_option_id": issue_option_ids[0] if issue_option_ids else None,
    }


def _single_binding_case() -> tuple[Any, str, dict[str, Any]]:
    text = "Признать норму неконституционной"
    sentence_id = "sent-aaaaaaaaaaaaaaaa"
    complaint = build_structured_complaint(
        _complaint_payload(
            [
                _sentence(
                    sentence_id,
                    "CLAIM-A",
                    "ISSUE-A",
                    "PASSPORT-A",
                    "APP-A",
                    "E-A",
                    text,
                )
            ],
            issue_option_ids=["ISSUE-A"],
            norm_passport_ids=["PASSPORT-A"],
        )
    )
    return complaint, sentence_id, _resolution(
        "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text
    )


class RemedyEvidenceBindingTests(unittest.TestCase):
    def _manifest_for(
        self,
        complaint: Any,
        authority: StaticAuthority,
    ) -> dict[str, Any]:
        receipts = require_release_support(
            complaint, relief_binding_authority=authority
        )
        manifest: dict[str, Any] = {
            "schema_version": "1.2",
            "matter_id": complaint.matter_id,
            "draft_id": complaint.draft_id,
            "status": "blocked",
            "filing_performed": False,
            "human_only_actions": [
                "signature",
                "fee_or_exemption_confirmation",
                "filing",
            ],
            "source_versions": ["SOURCE-1"],
            "norm_passport_ids": list(complaint.norm_passport_ids),
            "issue_option_ids": list(complaint.issue_option_ids),
            "issue_option_id": complaint.issue_option_id,
            "sentence_evidence_map": complaint.sentence_evidence_map(),
            "relief_binding_receipts": list(receipts),
            "relief_binding_index_receipt": (
                copy.deepcopy(receipts[0]["binding_index_receipt"])
                if receipts
                else None
            ),
            "holding_binding_receipts": [],
            "holding_binding_index_receipt": None,
            "formal_check": {},
            "formal_check_ready": False,
            "artifacts": [],
            "qa_artifacts": [],
            "enclosure_refs": [],
            "enclosures": [],
            "render_qa": {"passed": False},
            "blockers": [],
        }
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)
        return manifest

    def _manifest_with_binding(
        self,
    ) -> tuple[dict[str, Any], StaticAuthority]:
        text = "Признать норму неконституционной"
        complaint = build_structured_complaint(
            _complaint_payload(
                [
                    _sentence(
                        "sent-aaaaaaaaaaaaaaaa",
                        "CLAIM-A",
                        "ISSUE-A",
                        "PASSPORT-A",
                        "APP-A",
                        "E-A",
                        text,
                    )
                ],
                issue_option_ids=["ISSUE-A"],
                norm_passport_ids=["PASSPORT-A"],
            )
        )
        authority = StaticAuthority(
            {
                "sent-aaaaaaaaaaaaaaaa": _resolution(
                    "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text
                )
            }
        )
        return self._manifest_for(complaint, authority), authority

    def test_legacy_verified_looking_remedy_is_draft_only(self) -> None:
        payload = _complaint_payload(
            [
                {
                    "sentence_id": "sent-0000000000000001",
                    "text": "Признать норму неконституционной",
                    "role": "requested_remedy",
                    "evidence_ids": ["E-LEGACY"],
                    "support_status": "verified",
                    "passed": True,
                    "filing_ready": True,
                }
            ]
        )
        complaint = build_structured_complaint(payload)

        with self.assertRaisesRegex(
            ComplaintModelError, "sent-0000000000000001|relief_binding"
        ):
            require_release_support(complaint)

    def test_requested_remedy_section_cannot_downgrade_role(self) -> None:
        payload = _complaint_payload(
            [
                {
                    "sentence_id": "sent-0000000000000002",
                    "text": "Признать норму неконституционной",
                    "role": "narrative",
                    "evidence_ids": [],
                    "support_status": "pending",
                }
            ]
        )
        complaint = build_structured_complaint(payload)
        remedy_sentence = next(
            sentence
            for section in complaint.sections
            if section.code == "requested_remedy"
            for sentence in section.sentences
        )

        self.assertEqual(remedy_sentence.role, "requested_remedy")
        with self.assertRaisesRegex(
            ComplaintModelError, "sent-0000000000000002|relief_binding"
        ):
            require_release_support(complaint)

    def test_requested_remedy_role_cannot_move_to_facts_section(self) -> None:
        text = "Признать норму неконституционной"
        payload = _complaint_payload(
            [],
            issue_option_ids=["ISSUE-A"],
            norm_passport_ids=["PASSPORT-A"],
        )
        facts = next(
            section for section in payload["sections"] if section["code"] == "facts"
        )
        facts["sentences"] = [
            _sentence(
                "sent-aaaaaaaaaaaaaaaa",
                "CLAIM-A",
                "ISSUE-A",
                "PASSPORT-A",
                "APP-A",
                "E-A",
                text,
            )
        ]

        with self.assertRaisesRegex(
            ComplaintModelError,
            "requested_remedy_section_role_mismatch:sent-aaaaaaaaaaaaaaaa",
        ):
            build_structured_complaint(payload)

    def test_empty_requested_remedy_section_is_release_blocked(self) -> None:
        complaint = build_structured_complaint(_complaint_payload([]))

        with self.assertRaisesRegex(
            ComplaintModelError, "requested_remedy_sentence_missing"
        ):
            require_release_support(complaint)

    def test_cross_claim_remedy_evidence_is_blocked(self) -> None:
        text = "Признать норму неконституционной для линии B"
        sentence = _sentence(
            "sent-bbbbbbbbbbbbbbbb",
            "CLAIM-B",
            "ISSUE-B",
            "PASSPORT-B",
            "APP-A",
            "E-A",
            text,
        )
        complaint = build_structured_complaint(
            _complaint_payload(
                [sentence],
                issue_option_ids=["ISSUE-B"],
                norm_passport_ids=["PASSPORT-B"],
            )
        )
        authority = StaticAuthority(
            {
                "sent-bbbbbbbbbbbbbbbb": _resolution(
                    "CLAIM-A",
                    "ISSUE-B",
                    "PASSPORT-B",
                    "APP-A",
                    "E-A",
                    text,
                )
            }
        )

        with self.assertRaisesRegex(ComplaintModelError, "claim|CLAIM"):
            require_release_support(
                complaint, relief_binding_authority=authority
            )

    def test_unknown_sentence_evidence_is_blocked(self) -> None:
        text = "Признать норму неконституционной"
        complaint = build_structured_complaint(
            _complaint_payload(
                [
                    _sentence(
                        "sent-aaaaaaaaaaaaaaaa",
                        "CLAIM-A",
                        "ISSUE-A",
                        "PASSPORT-A",
                        "APP-A",
                        "E-UNKNOWN",
                        text,
                    )
                ],
                issue_option_ids=["ISSUE-A"],
                norm_passport_ids=["PASSPORT-A"],
            )
        )
        authority = StaticAuthority(
            {
                "sent-aaaaaaaaaaaaaaaa": _resolution(
                    "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text
                )
            }
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "sentence_evidence_unknown:E-UNKNOWN"
        ):
            require_release_support(
                complaint, relief_binding_authority=authority
            )

    def test_cross_edition_application_record_is_blocked(self) -> None:
        text = "Признать норму неконституционной"
        sentence_id = "sent-aaaaaaaaaaaaaaaa"
        complaint = build_structured_complaint(
            _complaint_payload(
                [
                    _sentence(
                        sentence_id,
                        "CLAIM-A",
                        "ISSUE-A",
                        "PASSPORT-A",
                        "APP-A",
                        "E-A",
                        text,
                    )
                ],
                issue_option_ids=["ISSUE-A"],
                norm_passport_ids=["PASSPORT-A"],
            )
        )
        resolution = _resolution(
            "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text
        )
        resolution["application_records"][0]["norm_version_id"] = "EDITION-2"
        changed_record = application_record_from_dict(
            resolution["application_records"][0]
        )
        resolution["application_gate_receipts"][0]["content_fingerprint"] = (
            application_record_content_fingerprint(changed_record)
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "application_record_edition_mismatch:APP-A"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_cross_edition_claim_evidence_is_blocked(self) -> None:
        text = "Признать норму неконституционной"
        sentence_id = "sent-aaaaaaaaaaaaaaaa"
        complaint = build_structured_complaint(
            _complaint_payload(
                [
                    _sentence(
                        sentence_id,
                        "CLAIM-A",
                        "ISSUE-A",
                        "PASSPORT-A",
                        "APP-A",
                        "E-OLD",
                        text,
                    )
                ],
                issue_option_ids=["ISSUE-A"],
                norm_passport_ids=["PASSPORT-A"],
            )
        )
        resolution = _resolution(
            "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text
        )
        resolution["claim_evidence"] = [
            {
                "evidence_id": "E-OLD",
                "claim_id": "CLAIM-A",
                "norm_id": "NORM-1",
                "norm_version_id": "EDITION-OLD",
                "status": "current",
                "content_sha256": "b" * 64,
                "verification_revision_id": "VERIFY-OLD",
                "verifier_id": "VERIFIER-1",
                "checked_at": "2026-09-01T10:00:00Z",
                "locator": {"kind": "paragraph", "value": "абз. 5"},
            }
        ]

        with self.assertRaisesRegex(
            ComplaintModelError, "claim_evidence_edition_mismatch:E-OLD"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_principal_and_reserve_bindings_pass_independently(self) -> None:
        text_a = "Признать норму неконституционной для линии A"
        text_b = "Истолковать норму конституционно для линии B"
        sentence_a = _sentence(
            "sent-aaaaaaaaaaaaaaaa",
            "CLAIM-A",
            "ISSUE-A",
            "PASSPORT-A",
            "APP-A",
            "E-A",
            text_a,
        )
        sentence_b = _sentence(
            "sent-bbbbbbbbbbbbbbbb",
            "CLAIM-B",
            "ISSUE-B",
            "PASSPORT-B",
            "APP-B",
            "E-B",
            text_b,
        )
        complaint = build_structured_complaint(
            _complaint_payload(
                [sentence_a, sentence_b],
                issue_option_ids=["ISSUE-A", "ISSUE-B"],
                norm_passport_ids=["PASSPORT-A", "PASSPORT-B"],
            )
        )
        authority = StaticAuthority(
            {
                "sent-aaaaaaaaaaaaaaaa": _resolution(
                    "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text_a
                ),
                "sent-bbbbbbbbbbbbbbbb": _resolution(
                    "CLAIM-B", "ISSUE-B", "PASSPORT-B", "APP-B", "E-B", text_b
                ),
            }
        )

        receipts = require_release_support(
            complaint, relief_binding_authority=authority
        )

        self.assertEqual(
            {item["sentence_id"] for item in receipts},
            {"sent-aaaaaaaaaaaaaaaa", "sent-bbbbbbbbbbbbbbbb"},
        )
        evidence_map = complaint.sentence_evidence_map()
        remedy_entries = [
            item for item in evidence_map if item["role"] == "requested_remedy"
        ]
        self.assertTrue(
            all(len(item["relief_binding_sha256"]) == 64 for item in remedy_entries)
        )

    def test_duplicate_application_record_ids_are_rejected(self) -> None:
        sentence = _sentence(
            "sent-aaaaaaaaaaaaaaaa",
            "CLAIM-A",
            "ISSUE-A",
            "PASSPORT-A",
            "APP-A",
            "E-A",
            "Признать норму неконституционной",
        )
        sentence["application_record_ids"] = ["APP-A", "APP-A"]

        with self.assertRaisesRegex(ComplaintModelError, "duplicate|повтор|unique"):
            build_structured_complaint(
                _complaint_payload(
                    [sentence],
                    issue_option_ids=["ISSUE-A"],
                    norm_passport_ids=["PASSPORT-A"],
                )
            )

    def test_duplicate_evidence_ids_are_rejected(self) -> None:
        sentence = _sentence(
            "sent-aaaaaaaaaaaaaaaa",
            "CLAIM-A",
            "ISSUE-A",
            "PASSPORT-A",
            "APP-A",
            "E-A",
            "Признать норму неконституционной",
        )
        sentence["evidence_ids"] = ["E-A", "E-A"]

        with self.assertRaisesRegex(ComplaintModelError, "duplicate|повтор"):
            build_structured_complaint(
                _complaint_payload(
                    [sentence],
                    issue_option_ids=["ISSUE-A"],
                    norm_passport_ids=["PASSPORT-A"],
                )
            )

    def test_malformed_supplied_sentence_id_is_rejected(self) -> None:
        sentence = _sentence(
            "sent-aaaaaaaaaaaaaaaa",
            "CLAIM-A",
            "ISSUE-A",
            "PASSPORT-A",
            "APP-A",
            "E-A",
            "Признать норму неконституционной",
        )
        sentence["sentence_id"] = 123

        with self.assertRaisesRegex(ComplaintModelError, "sentence_id"):
            build_structured_complaint(
                _complaint_payload(
                    [sentence],
                    issue_option_ids=["ISSUE-A"],
                    norm_passport_ids=["PASSPORT-A"],
                )
            )

    def test_duplicate_sentence_ids_are_rejected(self) -> None:
        first = _sentence(
            "sent-aaaaaaaaaaaaaaaa",
            "CLAIM-A",
            "ISSUE-A",
            "PASSPORT-A",
            "APP-A",
            "E-A",
            "Признать норму неконституционной",
        )
        second = _sentence(
            "sent-aaaaaaaaaaaaaaaa",
            "CLAIM-B",
            "ISSUE-B",
            "PASSPORT-B",
            "APP-B",
            "E-B",
            "Истолковать норму конституционно",
        )

        with self.assertRaisesRegex(ComplaintModelError, "sentence_id|Повтор"):
            build_structured_complaint(
                _complaint_payload(
                    [first, second],
                    issue_option_ids=["ISSUE-A", "ISSUE-B"],
                    norm_passport_ids=["PASSPORT-A", "PASSPORT-B"],
                )
            )

    def test_non_string_application_record_id_is_rejected(self) -> None:
        sentence = _sentence(
            "sent-aaaaaaaaaaaaaaaa",
            "CLAIM-A",
            "ISSUE-A",
            "PASSPORT-A",
            "APP-A",
            "E-A",
            "Признать норму неконституционной",
        )
        sentence["application_record_ids"] = ["APP-A", 7]

        with self.assertRaisesRegex(
            ComplaintModelError, "пустой или нестроковый"
        ):
            build_structured_complaint(
                _complaint_payload(
                    [sentence],
                    issue_option_ids=["ISSUE-A"],
                    norm_passport_ids=["PASSPORT-A"],
                )
            )

    def test_whitespace_binding_identifier_is_rejected(self) -> None:
        sentence = _sentence(
            "sent-aaaaaaaaaaaaaaaa",
            " CLAIM-A ",
            "ISSUE-A",
            "PASSPORT-A",
            "APP-A",
            "E-A",
            "Признать норму неконституционной",
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "канонической строкой|лишними пробелами"
        ):
            build_structured_complaint(
                _complaint_payload(
                    [sentence],
                    issue_option_ids=["ISSUE-A"],
                    norm_passport_ids=["PASSPORT-A"],
                )
            )

    def test_non_string_matter_identity_is_rejected(self) -> None:
        payload = _complaint_payload([])
        payload["matter_id"] = 123

        with self.assertRaisesRegex(
            ComplaintModelError, "matter_id должен быть непустой строкой"
        ):
            build_structured_complaint(payload)

    def test_post_build_global_sentence_duplicate_is_rejected(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        sections = list(complaint.sections)
        facts_index = next(
            index for index, section in enumerate(sections) if section.code == "facts"
        )
        facts = sections[facts_index]
        remedy_sentence = next(
            sentence
            for section in sections
            if section.code == "requested_remedy"
            for sentence in section.sentences
        )
        duplicate = type(remedy_sentence)(
            sentence_id=sentence_id,
            section_code="facts",
            text="Диагностический narrative",
            role="narrative",
        )
        sections[facts_index] = type(facts)(
            code=facts.code,
            heading=facts.heading,
            sentences=(*facts.sentences, duplicate),
        )
        complaint.sections = tuple(sections)

        with self.assertRaisesRegex(
            ComplaintModelError,
            "relief_binding_sentence_duplicate:sent-aaaaaaaaaaaaaaaa",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_stale_issue_fingerprint_is_rejected(self) -> None:
        text = "Признать норму неконституционной"
        sentence = _sentence(
            "sent-aaaaaaaaaaaaaaaa",
            "CLAIM-A",
            "ISSUE-A",
            "PASSPORT-A",
            "APP-A",
            "E-A",
            text,
        )
        complaint = build_structured_complaint(
            _complaint_payload(
                [sentence],
                issue_option_ids=["ISSUE-A"],
                norm_passport_ids=["PASSPORT-A"],
            )
        )
        resolution = _resolution(
            "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text
        )
        resolution["issue_gate_receipt"]["content_fingerprint"] = "stale"

        with self.assertRaisesRegex(ComplaintModelError, "fingerprint|stale"):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {"sent-aaaaaaaaaaaaaaaa": resolution}
                ),
            )

    def test_arbitrary_issue_approval_request_is_rejected(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        resolution["issue_gate_receipt"]["approval_requests"] = {
            "remedy": {"fingerprint": "totally-stale"}
        }

        with self.assertRaisesRegex(
            ComplaintModelError, "issue_approval_requests_mismatch"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_incomplete_issue_approval_set_is_rejected(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        resolution["issue_gate_receipt"]["trusted_approval_ids"].pop(
            "adverse_authority", None
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "issue_trusted_approval_set_mismatch"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_arbitrary_norm_approval_request_is_rejected(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        resolution["norm_version_gate_receipt"]["approval_request"] = {
            "fingerprint": "totally-stale"
        }

        with self.assertRaisesRegex(
            ComplaintModelError, "norm_version_approval_request_mismatch"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_arbitrary_application_approval_request_is_rejected(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        resolution["application_gate_receipts"][0]["approval_request"] = {
            "fingerprint": "totally-stale"
        }

        with self.assertRaisesRegex(
            ComplaintModelError, "application:APP-A_approval_request_mismatch"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_schema_1_2_distinguishes_bound_and_legacy_draft(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        text = "Признать норму неконституционной"
        bound = build_structured_complaint(
            _complaint_payload(
                [
                    _sentence(
                        "sent-aaaaaaaaaaaaaaaa",
                        "CLAIM-A",
                        "ISSUE-A",
                        "PASSPORT-A",
                        "APP-A",
                        "E-A",
                        text,
                    )
                ],
                issue_option_ids=["ISSUE-A"],
                norm_passport_ids=["PASSPORT-A"],
            )
        ).to_dict()

        self.assertEqual(bound["schema_version"], "1.2")
        self.assertEqual(list(validator.iter_errors(bound)), [])
        bound_entry = next(
            item
            for item in bound["sentence_evidence_map"]
            if item["role"] == "requested_remedy"
        )
        self.assertEqual(bound_entry["relief_binding_status"], "bound")

        unbound = build_structured_complaint(
            _complaint_payload(
                [
                    {
                        "sentence_id": "sent-0000000000000003",
                        "text": "Признать норму неконституционной",
                        "role": "requested_remedy",
                        "evidence_ids": ["E-LEGACY"],
                        "support_status": "verified",
                    }
                ]
            )
        ).to_dict()
        unbound_entry = next(
            item
            for item in unbound["sentence_evidence_map"]
            if item["role"] == "requested_remedy"
        )
        self.assertEqual(unbound_entry["relief_binding_status"], "unbound")
        self.assertEqual(list(validator.iter_errors(unbound)), [])

        falsely_bound = copy.deepcopy(unbound)
        false_entry = next(
            item
            for item in falsely_bound["sentence_evidence_map"]
            if item["role"] == "requested_remedy"
        )
        false_entry["relief_binding_status"] = "bound"
        self.assertTrue(list(validator.iter_errors(falsely_bound)))

    def test_manifest_revalidation_requires_current_host_authority(self) -> None:
        manifest, authority = self._manifest_with_binding()

        without_authority = verify_release_manifest(manifest)
        with_authority = verify_release_manifest(
            manifest, relief_binding_authority=authority
        )

        self.assertTrue(
            any("relief_binding_authority_required" in item for item in without_authority)
        )
        self.assertFalse(any(item.startswith("relief_binding:") for item in with_authority))

    def test_manifest_tampered_binding_receipt_is_stale(self) -> None:
        manifest, authority = self._manifest_with_binding()
        manifest["relief_binding_receipts"][0][
            "issue_content_fingerprint"
        ] = "tampered"
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest, relief_binding_authority=authority
        )

        self.assertIn(
            "relief_binding_receipt_stale:sent-aaaaaaaaaaaaaaaa", errors
        )

    def test_manifest_stale_authoritative_index_receipt_is_rejected(self) -> None:
        manifest, authority = self._manifest_with_binding()
        authority.index_authority_revision_id = "DRAFT-REGISTRY-REV-2"

        errors = verify_release_manifest(
            manifest, relief_binding_authority=authority
        )

        self.assertIn("relief_binding_index_receipt_stale", errors)

    def test_host_index_checked_at_must_be_rfc3339_datetime(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()

        class InvalidIndexTimeAuthority(StaticAuthority):
            def resolve_relief_evidence_binding_index(
                self, request: dict[str, Any]
            ) -> dict[str, Any]:
                result = super().resolve_relief_evidence_binding_index(request)
                result["checked_at"] = "not-a-date"
                return result

        with self.assertRaisesRegex(
            ComplaintModelError, "relief_binding_index_checked_at_invalid"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=InvalidIndexTimeAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_line_authority_without_index_authority_is_blocked(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()

        class LineOnlyAuthority:
            def resolve_relief_evidence_binding(
                self, request: dict[str, Any]
            ) -> dict[str, Any] | None:
                result = copy.deepcopy(resolution)
                result["relief_binding_sha256"] = request[
                    "relief_binding_sha256"
                ]
                return result

        with self.assertRaisesRegex(
            ComplaintModelError, "relief_binding_index_authority_required"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=LineOnlyAuthority(),
            )

    def test_manifest_unbound_status_is_rejected(self) -> None:
        manifest, authority = self._manifest_with_binding()
        manifest["sentence_evidence_map"][0]["relief_binding_status"] = "unbound"
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest, relief_binding_authority=authority
        )

        self.assertIn(
            "relief_binding_status_not_bound:sent-aaaaaaaaaaaaaaaa", errors
        )

    def test_filing_schema_allows_blocked_unbound_diagnostic_manifest(self) -> None:
        manifest, _authority = self._manifest_with_binding()
        entry = manifest["sentence_evidence_map"][0]
        entry["relief_binding_status"] = "unbound"
        for key in (
            "claim_id",
            "issue_option_id",
            "norm_passport_id",
            "application_record_ids",
            "relief_binding_sha256",
        ):
            entry.pop(key, None)
        manifest["relief_binding_receipts"] = []
        schema = json.loads(FILING_SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(
            list(Draft202012Validator(schema).iter_errors(manifest)), []
        )

    def test_filing_schema_requires_bound_relief_for_ready_manifest(self) -> None:
        manifest, _authority = self._manifest_with_binding()
        manifest["status"] = "ready_for_expert_review"
        entry = manifest["sentence_evidence_map"][0]
        entry["relief_binding_status"] = "unbound"
        manifest["relief_binding_receipts"] = []
        schema = json.loads(FILING_SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertTrue(
            list(Draft202012Validator(schema).iter_errors(manifest))
        )

    def test_filing_schema_accepts_current_bound_manifest(self) -> None:
        manifest, _authority = self._manifest_with_binding()
        manifest["status"] = "ready_for_expert_review"
        holding_index = build_holding_binding_index_resolution(
            matter_id=manifest["matter_id"],
            draft_id=manifest["draft_id"],
            bindings=[],
            authority_revision_id="HOLDING-REGISTRY-REV-1",
            checked_at="2026-09-01T10:00:00Z",
        )
        holding_index.pop("status")
        manifest["holding_binding_index_receipt"] = holding_index
        schema = json.loads(FILING_SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(
            list(Draft202012Validator(schema).iter_errors(manifest)), []
        )

    def test_manifest_cannot_remove_all_remedy_bindings(self) -> None:
        manifest, authority = self._manifest_with_binding()
        manifest["sentence_evidence_map"] = []
        manifest["relief_binding_receipts"] = []
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest, relief_binding_authority=authority
        )

        self.assertIn("relief_binding_requested_remedy_missing", errors)

    def test_manifest_malformed_sentence_id_is_rejected_before_authority(self) -> None:
        manifest, authority = self._manifest_with_binding()
        manifest["sentence_evidence_map"][0]["sentence_id"] = 123
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest, relief_binding_authority=authority
        )

        self.assertIn("relief_binding_sentence_id_invalid:1", errors)

    def test_manifest_duplicate_binding_identifiers_are_rejected(self) -> None:
        manifest, authority = self._manifest_with_binding()
        entry = manifest["sentence_evidence_map"][0]
        entry["evidence_ids"] = ["E-A", "E-A"]
        entry["application_record_ids"] = ["APP-A", "APP-A"]
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest, relief_binding_authority=authority
        )

        self.assertIn(
            "relief_binding_identifier_duplicate:"
            "sent-aaaaaaaaaaaaaaaa:evidence_ids",
            errors,
        )
        self.assertIn(
            "relief_binding_identifier_duplicate:"
            "sent-aaaaaaaaaaaaaaaa:application_record_ids",
            errors,
        )

    def test_manifest_cannot_drop_one_of_two_remedy_lines(self) -> None:
        text_a = "Признать норму неконституционной для линии A"
        text_b = "Истолковать норму конституционно для линии B"
        complaint = build_structured_complaint(
            _complaint_payload(
                [
                    _sentence(
                        "sent-aaaaaaaaaaaaaaaa",
                        "CLAIM-A",
                        "ISSUE-A",
                        "PASSPORT-A",
                        "APP-A",
                        "E-A",
                        text_a,
                    ),
                    _sentence(
                        "sent-bbbbbbbbbbbbbbbb",
                        "CLAIM-B",
                        "ISSUE-B",
                        "PASSPORT-B",
                        "APP-B",
                        "E-B",
                        text_b,
                    ),
                ],
                issue_option_ids=["ISSUE-A", "ISSUE-B"],
                norm_passport_ids=["PASSPORT-A", "PASSPORT-B"],
            )
        )
        authority = StaticAuthority(
            {
                "sent-aaaaaaaaaaaaaaaa": _resolution(
                    "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text_a
                ),
                "sent-bbbbbbbbbbbbbbbb": _resolution(
                    "CLAIM-B", "ISSUE-B", "PASSPORT-B", "APP-B", "E-B", text_b
                ),
            }
        )
        manifest = self._manifest_for(complaint, authority)
        manifest["sentence_evidence_map"] = [
            item
            for item in manifest["sentence_evidence_map"]
            if item["sentence_id"] != "sent-bbbbbbbbbbbbbbbb"
        ]
        manifest["relief_binding_receipts"] = [
            item
            for item in manifest["relief_binding_receipts"]
            if item["sentence_id"] != "sent-bbbbbbbbbbbbbbbb"
        ]
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest, relief_binding_authority=authority
        )

        self.assertTrue(
            any("relief_binding_index_set_mismatch" in item for item in errors)
        )

    def test_manifest_requested_section_role_downgrade_is_rejected(self) -> None:
        manifest, authority = self._manifest_with_binding()
        manifest["sentence_evidence_map"][0]["role"] = "narrative"
        manifest["relief_binding_receipts"] = []
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest, relief_binding_authority=authority
        )

        self.assertIn(
            "relief_binding_manifest_role_mismatch:sent-aaaaaaaaaaaaaaaa",
            errors,
        )

    def test_manifest_global_duplicate_sentence_id_is_rejected(self) -> None:
        manifest, authority = self._manifest_with_binding()
        duplicate = copy.deepcopy(manifest["sentence_evidence_map"][0])
        duplicate["section_code"] = "facts"
        duplicate["role"] = "narrative"
        manifest["sentence_evidence_map"].append(duplicate)
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest, relief_binding_authority=authority
        )

        self.assertIn(
            "relief_binding_sentence_duplicate:sent-aaaaaaaaaaaaaaaa",
            errors,
        )

    def test_source_evidence_sha_change_stales_manifest_receipt(self) -> None:
        text = "Признать норму неконституционной"
        sentence_id = "sent-aaaaaaaaaaaaaaaa"
        complaint = build_structured_complaint(
            _complaint_payload(
                [
                    _sentence(
                        sentence_id,
                        "CLAIM-A",
                        "ISSUE-A",
                        "PASSPORT-A",
                        "APP-A",
                        "E-SOURCE",
                        text,
                    )
                ],
                issue_option_ids=["ISSUE-A"],
                norm_passport_ids=["PASSPORT-A"],
            )
        )
        resolution = _resolution(
            "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text
        )
        source_entry = {
            "evidence_id": "E-SOURCE",
            "claim_id": "CLAIM-A",
            "norm_id": "NORM-1",
            "norm_version_id": "EDITION-1",
            "status": "current",
            "content_sha256": "b" * 64,
            "verification_revision_id": "VERIFY-1",
            "verifier_id": "VERIFIER-1",
            "checked_at": "2026-09-01T10:00:00Z",
            "locator": {"kind": "paragraph", "value": "абз. 7"},
        }
        resolution["claim_evidence"] = [source_entry]
        initial_authority = StaticAuthority({sentence_id: resolution})
        manifest = self._manifest_for(complaint, initial_authority)
        changed = copy.deepcopy(resolution)
        changed["claim_evidence"][0]["content_sha256"] = "c" * 64
        current_authority = StaticAuthority({sentence_id: changed})

        errors = verify_release_manifest(
            manifest, relief_binding_authority=current_authority
        )

        self.assertIn(
            "relief_binding_receipt_stale:sent-aaaaaaaaaaaaaaaa", errors
        )

    def test_source_evidence_locator_change_stales_manifest_receipt(self) -> None:
        text = "Признать норму неконституционной"
        sentence_id = "sent-aaaaaaaaaaaaaaaa"
        complaint = build_structured_complaint(
            _complaint_payload(
                [
                    _sentence(
                        sentence_id,
                        "CLAIM-A",
                        "ISSUE-A",
                        "PASSPORT-A",
                        "APP-A",
                        "E-SOURCE",
                        text,
                    )
                ],
                issue_option_ids=["ISSUE-A"],
                norm_passport_ids=["PASSPORT-A"],
            )
        )
        resolution = _resolution(
            "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text
        )
        resolution["claim_evidence"] = [
            {
                "evidence_id": "E-SOURCE",
                "claim_id": "CLAIM-A",
                "norm_id": "NORM-1",
                "norm_version_id": "EDITION-1",
                "status": "current",
                "content_sha256": "b" * 64,
                "verification_revision_id": "VERIFY-1",
                "verifier_id": "VERIFIER-1",
                "checked_at": "2026-09-01T10:00:00Z",
                "locator": {"kind": "paragraph", "value": "абз. 7"},
            }
        ]
        manifest = self._manifest_for(
            complaint, StaticAuthority({sentence_id: resolution})
        )
        changed = copy.deepcopy(resolution)
        changed["claim_evidence"][0]["locator"]["value"] = "абз. 8"

        errors = verify_release_manifest(
            manifest,
            relief_binding_authority=StaticAuthority({sentence_id: changed}),
        )

        self.assertIn(
            "relief_binding_receipt_stale:sent-aaaaaaaaaaaaaaaa", errors
        )

    def test_source_evidence_checked_at_must_be_rfc3339_datetime(self) -> None:
        text = "Признать норму неконституционной"
        sentence_id = "sent-aaaaaaaaaaaaaaaa"
        complaint = build_structured_complaint(
            _complaint_payload(
                [
                    _sentence(
                        sentence_id,
                        "CLAIM-A",
                        "ISSUE-A",
                        "PASSPORT-A",
                        "APP-A",
                        "E-SOURCE",
                        text,
                    )
                ],
                issue_option_ids=["ISSUE-A"],
                norm_passport_ids=["PASSPORT-A"],
            )
        )
        resolution = _resolution(
            "CLAIM-A", "ISSUE-A", "PASSPORT-A", "APP-A", "E-A", text
        )
        resolution["claim_evidence"] = [
            {
                "evidence_id": "E-SOURCE",
                "claim_id": "CLAIM-A",
                "norm_id": "NORM-1",
                "norm_version_id": "EDITION-1",
                "status": "current",
                "content_sha256": "b" * 64,
                "verification_revision_id": "VERIFY-1",
                "verifier_id": "VERIFIER-1",
                "checked_at": "not-a-date",
                "locator": {"kind": "paragraph", "value": "абз. 7"},
            }
        ]

        with self.assertRaisesRegex(
            ComplaintModelError,
            "claim_evidence_checked_at_invalid:E-SOURCE",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_issue_identifier_is_not_string_coerced(self) -> None:
        text = "Признать норму неконституционной"
        sentence_id = "sent-aaaaaaaaaaaaaaaa"
        complaint = build_structured_complaint(
            _complaint_payload(
                [
                    _sentence(
                        sentence_id,
                        "CLAIM-A",
                        "123",
                        "PASSPORT-A",
                        "APP-A",
                        "E-A",
                        text,
                    )
                ],
                issue_option_ids=["123"],
                norm_passport_ids=["PASSPORT-A"],
            )
        )
        resolution = _resolution(
            "CLAIM-A", "123", "PASSPORT-A", "APP-A", "E-A", text
        )
        resolution["issue_option"]["issue_id"] = 123

        with self.assertRaisesRegex(
            ComplaintModelError, "issue_option_raw_identifier_invalid:issue_id"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_issue_schema_version_is_pinned(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        resolution["issue_option"]["schema_version"] = "0.9.0"
        resolution["issue_gate_receipt"] = _issue_receipt(
            issue_candidate_from_dict(resolution["issue_option"])
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "issue_option_schema_version_invalid"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_issue_application_evidence_id_is_not_string_coerced(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        resolution["issue_option"]["application_proof"]["evidence_ids"] = [123]

        with self.assertRaisesRegex(
            ComplaintModelError,
            "issue_option:application_proof:evidence_ids_raw_identifier_invalid:1",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_issue_gate_boolean_cannot_downgrade_approval_set(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        resolution["issue_option"]["gates"]["anti_fourth_instance"][
            "requires_human_review"
        ] = 1
        issue = issue_candidate_from_dict(resolution["issue_option"])
        resolution["issue_gate_receipt"] = _issue_receipt(issue)

        with self.assertRaisesRegex(
            ComplaintModelError,
            "anti_fourth_instance:requires_human_review_raw_boolean_invalid",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_application_locator_is_not_string_coerced(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        resolution["application_records"][0]["evidence"][0]["locator"][
            "value"
        ] = 12

        with self.assertRaisesRegex(
            ComplaintModelError,
            "application_record:1:evidence:1:locator_raw_identifier_invalid:value",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_application_graph_id_is_not_string_coerced(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        resolution["application_records"][0]["normative_meaning_id"] = 123

        with self.assertRaisesRegex(
            ComplaintModelError,
            "application_record:1_raw_identifier_invalid:normative_meaning_id",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_passport_identifier_whitespace_is_not_normalized(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        resolution["norm_version_passport"]["passport_id"] = " PASSPORT-A "

        with self.assertRaisesRegex(
            ComplaintModelError,
            "norm_version_passport_raw_identifier_invalid:passport_id",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_passport_nested_source_id_is_not_string_coerced(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        passport = resolution["norm_version_passport"]
        passport["official_publication_identity"] = {
            "source_evidence_id": 123,
            "content_sha256": "a" * 64,
        }
        norm_receipt = _norm_receipt(passport)
        resolution["norm_version_gate_receipt"] = norm_receipt
        application = application_record_from_dict(
            resolution["application_records"][0]
        )
        resolution["application_gate_receipts"] = [
            _application_receipt(
                application,
                [application],
                passport,
                norm_receipt,
            )
        ]

        with self.assertRaisesRegex(
            ComplaintModelError,
            "official_publication_identity:source_evidence_id_raw_identifier_invalid",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_passport_required_nested_source_id_cannot_be_null(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        passport = resolution["norm_version_passport"]
        passport["official_publication_identity"] = {
            "source_evidence_id": None,
            "content_sha256": "a" * 64,
        }
        norm_receipt = _norm_receipt(passport)
        resolution["norm_version_gate_receipt"] = norm_receipt
        application = application_record_from_dict(
            resolution["application_records"][0]
        )
        resolution["application_gate_receipts"] = [
            _application_receipt(
                application,
                [application],
                passport,
                norm_receipt,
            )
        ]

        with self.assertRaisesRegex(
            ComplaintModelError,
            "official_publication_identity:source_evidence_id_raw_identifier_invalid",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_passport_schema_version_is_pinned(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        passport = resolution["norm_version_passport"]
        passport["schema_version"] = "0.9.0"
        norm_receipt = _norm_receipt(passport)
        resolution["norm_version_gate_receipt"] = norm_receipt
        application = application_record_from_dict(
            resolution["application_records"][0]
        )
        resolution["application_gate_receipts"] = [
            _application_receipt(
                application,
                [application],
                passport,
                norm_receipt,
            )
        ]

        with self.assertRaisesRegex(
            ComplaintModelError, "norm_version_passport_schema_version_invalid"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_application_stage_is_not_string_coerced(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        raw_application = resolution["application_records"][0]
        raw_application["stage"] = 123
        raw_application["evidence"][0]["stage"] = 123
        application = application_record_from_dict(raw_application)
        passport = resolution["norm_version_passport"]
        norm_receipt = resolution["norm_version_gate_receipt"]
        resolution["application_gate_receipts"] = [
            _application_receipt(
                application,
                [application],
                passport,
                norm_receipt,
            )
        ]

        with self.assertRaisesRegex(
            ComplaintModelError,
            "application_record:1_raw_identifier_invalid:stage",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_application_schema_version_is_pinned(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        raw_application = resolution["application_records"][0]
        raw_application["schema_version"] = "0.9.0"
        application = application_record_from_dict(raw_application)
        passport = resolution["norm_version_passport"]
        norm_receipt = resolution["norm_version_gate_receipt"]
        resolution["application_gate_receipts"] = [
            _application_receipt(
                application,
                [application],
                passport,
                norm_receipt,
            )
        ]

        with self.assertRaisesRegex(
            ComplaintModelError, "application_record_schema_version_invalid:1"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_host_application_stage_order_is_not_integer_coerced(self) -> None:
        complaint, sentence_id, resolution = _single_binding_case()
        raw_application = resolution["application_records"][0]
        raw_application["stage_order"] = "1"
        application = application_record_from_dict(raw_application)
        passport = resolution["norm_version_passport"]
        norm_receipt = resolution["norm_version_gate_receipt"]
        resolution["application_gate_receipts"] = [
            _application_receipt(
                application,
                [application],
                passport,
                norm_receipt,
            )
        ]

        with self.assertRaisesRegex(
            ComplaintModelError,
            "application_record_stage_order_raw_integer_invalid:1",
        ):
            require_release_support(
                complaint,
                relief_binding_authority=StaticAuthority(
                    {sentence_id: resolution}
                ),
            )

    def test_mutating_authority_cannot_swap_bound_evidence(self) -> None:
        complaint, sentence_id, _resolution_a = _single_binding_case()
        resolution_b = _resolution(
            "CLAIM-A",
            "ISSUE-A",
            "PASSPORT-A",
            "APP-A",
            "E-B",
            "Признать норму неконституционной",
        )

        class MutatingAuthority(StaticAuthority):
            def resolve_relief_evidence_binding(
                self, request: dict[str, Any]
            ) -> dict[str, Any] | None:
                request["evidence_ids"][0] = "E-B"
                result = copy.deepcopy(resolution_b)
                result["relief_binding_sha256"] = request[
                    "relief_binding_sha256"
                ]
                return result

        with self.assertRaisesRegex(
            ComplaintModelError, "relief_binding_request_mutated"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=MutatingAuthority(
                    {sentence_id: resolution_b}
                ),
            )


if __name__ == "__main__":
    unittest.main()
