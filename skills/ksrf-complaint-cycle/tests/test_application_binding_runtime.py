# pyright: reportMissingImports=false, reportMissingModuleSource=false
from __future__ import annotations

from copy import deepcopy
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker


SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = SKILL_ROOT / "lib"
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))

from ksrf.filing.application_binding import (  # noqa: E402
    build_application_finding_binding_index_resolution,
    build_application_finding_binding_request,
    build_application_finding_binding_resolution,
    resolve_application_finding_evidence_binding,
    resolve_application_finding_evidence_binding_index,
)
from ksrf.filing.application_evidence import (  # noqa: E402
    application_record_content_fingerprint,
    application_record_from_dict,
    application_review_approval_request,
    assess_application_chain,
    build_preservation_rule_evidence,
    classify_application,
    evaluate_application_admissibility,
    preservation_rule_review_approval_request,
)
from ksrf.filing.norm_versions import (  # noqa: E402
    norm_version_passport_content_fingerprint,
    norm_version_review_approval_request,
)


CHECKED_AT = "2026-09-01T12:00:00Z"
AUTHORITY_REVISION_ID = "APPLICATION-AUTHORITY-REV-1"
CHAIN_REVISION_ID = "APPLICATION-CHAIN-REV-1"
CHAIN_CHECKED_AT = "2026-09-01T11:59:00Z"
TRUSTED_SCOPE_APPROVAL_ID = "trusted-approval:sha256:" + "a" * 64


def _positive_record_payload(
    *, record_id: str = "APP-A", stage_order: int = 1
) -> dict[str, Any]:
    claim_id = "CLAIM-A"
    act_id = f"ACT-{record_id}"
    evidence = [
        {
            "evidence_id": "E-EXPRESS",
            "claim_id": claim_id,
            "norm_id": "NORM-1",
            "act_id": act_id,
            "stage": "first_instance",
            "source_kind": "full_act",
            "locator": {"kind": "paragraph", "value": "абз. 10"},
            "quote": "Суд прямо применил норму.",
            "speaker": "court",
            "reasoning_role": "express_norm_use",
            "inference_status": "observed",
        },
        {
            "evidence_id": "E-RULE",
            "claim_id": claim_id,
            "norm_id": "NORM-1",
            "act_id": act_id,
            "stage": "first_instance",
            "source_kind": "full_act",
            "locator": {"kind": "paragraph", "value": "абз. 11"},
            "quote": "Суд сформулировал применённое правило.",
            "speaker": "court",
            "reasoning_role": "operative_rule",
            "inference_status": "observed",
        },
        {
            "evidence_id": "E-OUTCOME",
            "claim_id": claim_id,
            "norm_id": "NORM-1",
            "act_id": act_id,
            "stage": "first_instance",
            "source_kind": "full_act",
            "locator": {"kind": "paragraph", "value": "абз. 12"},
            "quote": "Применение нормы определило исход.",
            "speaker": "disposition",
            "reasoning_role": "outcome_link",
            "inference_status": "observed",
        },
        {
            "evidence_id": "E-BACKGROUND",
            "claim_id": claim_id,
            "norm_id": "NORM-1",
            "act_id": act_id,
            "stage": "first_instance",
            "source_kind": "full_act",
            "locator": {"kind": "paragraph", "value": "абз. 2"},
            "quote": "Описание хода процесса.",
            "speaker": "court",
            "reasoning_role": "background",
            "inference_status": "observed",
        },
    ]
    return {
        "schema_version": "1.0.0",
        "record_id": record_id,
        "claim_id": claim_id,
        "norm_id": "NORM-1",
        "norm_version_id": "EDITION-1",
        "normative_meaning_id": "MEANING-A",
        "act_id": act_id,
        "stage": "first_instance",
        "stage_order": stage_order,
        "norm_use_status": "direct_reasoned_use",
        "outcome_causation": "determinative",
        "preservation_exhaustion": "raised_and_reviewed",
        "relation_to_prior": "initial",
        "incorporated_record_ids": [],
        "evidence": evidence,
        "implicit_premises": [],
        "affirmative_non_application": None,
        "human_review": {
            "state": "pending",
            "reviewer": None,
            "reviewed_at": None,
            "note": "",
        },
        "decision_rationale": "Прямое применение подтверждено.",
    }


def _incorporation_record_payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "record_id": "APP-FINAL",
        "claim_id": "CLAIM-A",
        "norm_id": "NORM-1",
        "norm_version_id": "EDITION-1",
        "normative_meaning_id": "MEANING-A",
        "act_id": "ACT-FINAL",
        "stage": "cassation",
        "stage_order": 2,
        "norm_use_status": "mentioned_only",
        "outcome_causation": "unclear",
        "preservation_exhaustion": "raised_and_reviewed",
        "relation_to_prior": "express_incorporation",
        "incorporated_record_ids": ["APP-A"],
        "evidence": [
            {
                "evidence_id": "E-INCORPORATION",
                "claim_id": "CLAIM-A",
                "norm_id": "NORM-1",
                "act_id": "ACT-FINAL",
                "stage": "cassation",
                "source_kind": "full_act",
                "locator": {"kind": "paragraph", "value": "абз. 20"},
                "quote": "Суд прямо согласился с мотивировкой нижестоящего суда.",
                "speaker": "court",
                "reasoning_role": "incorporation",
                "inference_status": "observed",
            }
        ],
        "implicit_premises": [],
        "affirmative_non_application": None,
        "human_review": {
            "state": "pending",
            "reviewer": None,
            "reviewed_at": None,
            "note": "",
        },
        "decision_rationale": "Инкорпорация мотивировки.",
    }


def _implicit_record_payload() -> dict[str, Any]:
    payload = _positive_record_payload()
    payload["norm_use_status"] = "reasoning_linked_implicit"
    payload["evidence"] = [
        {
            "evidence_id": "E-ISSUE",
            "claim_id": "CLAIM-A",
            "norm_id": "NORM-1",
            "act_id": "ACT-APP-A",
            "stage": "first_instance",
            "source_kind": "full_act",
            "locator": {"kind": "paragraph", "value": "абз. 30"},
            "quote": "Вопрос о применении нормы поставлен перед судом.",
            "speaker": "court",
            "reasoning_role": "issue_before_court",
            "inference_status": "observed",
        },
        {
            "evidence_id": "E-LOGIC",
            "claim_id": "CLAIM-A",
            "norm_id": "NORM-1",
            "act_id": "ACT-APP-A",
            "stage": "first_instance",
            "source_kind": "full_act",
            "locator": {"kind": "paragraph", "value": "абз. 31"},
            "quote": "Норма вошла в логику разрешения требования.",
            "speaker": "court",
            "reasoning_role": "application_reasoning",
            "inference_status": "observed",
        },
        {
            "evidence_id": "E-COUNTERFACTUAL",
            "claim_id": "CLAIM-A",
            "norm_id": "NORM-1",
            "act_id": "ACT-APP-A",
            "stage": "first_instance",
            "source_kind": "full_act",
            "locator": {"kind": "paragraph", "value": "абз. 32"},
            "quote": "Без этой нормы исход был бы иным.",
            "speaker": "disposition",
            "reasoning_role": "counterfactual_analysis",
            "inference_status": "observed",
        },
        {
            "evidence_id": "E-NO-ALTERNATIVE",
            "claim_id": "CLAIM-A",
            "norm_id": "NORM-1",
            "act_id": "ACT-APP-A",
            "stage": "first_instance",
            "source_kind": "full_act",
            "locator": {"kind": "paragraph", "value": "абз. 33"},
            "quote": "Самостоятельного достаточного основания не выявлено.",
            "speaker": "reviewer",
            "reasoning_role": "alternative_ground_analysis",
            "inference_status": "human_confirmed",
        },
    ]
    payload["implicit_premises"] = [
        {
            "premise": "issue_before_court",
            "conclusion": "Вопрос находился на разрешении суда.",
            "evidence_ids": ["E-ISSUE"],
            "inference_status": "observed",
        },
        {
            "premise": "operative_norm_logic",
            "conclusion": "Норма вошла в судебную логику.",
            "evidence_ids": ["E-LOGIC"],
            "inference_status": "observed",
        },
        {
            "premise": "counterfactual_outcome_dependence",
            "conclusion": "Исход зависел от нормы.",
            "evidence_ids": ["E-COUNTERFACTUAL"],
            "inference_status": "observed",
        },
        {
            "premise": "no_independent_sufficient_ground",
            "conclusion": "Иного достаточного основания не было.",
            "evidence_ids": ["E-NO-ALTERNATIVE"],
            "inference_status": "human_confirmed",
        },
    ]
    payload["human_review"] = {
        "state": "approved",
        "reviewer": "Reviewer A",
        "reviewed_at": "2026-09-12T18:00:00Z",
        "note": "Полный record и premise-level выводы проверены.",
    }
    payload["decision_rationale"] = "Неявное применение доказано по всем предпосылкам."
    return payload


def _implicit_independent_ground_payload() -> dict[str, Any]:
    payload = _implicit_record_payload()
    payload["outcome_causation"] = "independent_sufficient_ground"
    payload["evidence"] = payload["evidence"][:2]
    payload["evidence"].append(
        {
            "evidence_id": "E-INDEPENDENT",
            "claim_id": "CLAIM-A",
            "norm_id": "NORM-1",
            "act_id": "ACT-APP-A",
            "stage": "first_instance",
            "source_kind": "full_act",
            "locator": {"kind": "paragraph", "value": "абз. 34"},
            "quote": "Самостоятельное основание достаточно для того же результата.",
            "speaker": "court",
            "reasoning_role": "independent_ground",
            "inference_status": "observed",
        }
    )
    payload["implicit_premises"] = payload["implicit_premises"][:2]
    payload["affirmative_non_application"] = {
        "reason": "complete_independent_ground",
        "evidence_ids": ["E-INDEPENDENT"],
    }
    return payload


def _passport_payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "passport_id": "NVP-A",
        "passport_revision_id": "NVP-REV-1",
        "norm_id": "NORM-1",
        "canonical_citation": "ст. 1 ТК РФ",
        "issuing_authority": "Федеральный законодатель",
        "official_publication_identity": "publication-1",
        "amendment_acts": [],
        "legal_timepoints": [],
        "edition_segments": [
            {
                "edition_id": "EDITION-1",
                "valid_from": "2020-01-01",
                "valid_to": None,
            }
        ],
        "provider_assertions": [],
        "unresolved_conflicts": [],
        "timepoint_edition_map": {},
    }


def _norm_receipt(passport: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "passed": True,
        "content_fingerprint": norm_version_passport_content_fingerprint(
            passport
        ),
        "approval_request": norm_version_review_approval_request(passport),
        "trusted_approval_id": "APPROVAL-NORM-VERSION",
    }


def _application_receipt(
    record: Any,
    chain_records: list[Any],
    passport: Mapping[str, Any],
    norm_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    chain = assess_application_chain(chain_records)
    preservation = build_preservation_rule_evidence(
        record,
        rule_status="verified_not_required",
        rule_citation="ст. 96 ФКЗ о КС РФ",
        rule_statement="Дополнительное сохранение возражения не требуется.",
        evidence_ids=["PRESERVATION-OFFICIAL-1"],
    )
    preservation_approval_id = "APPROVAL-PRESERVATION"
    return {
        "record_id": record.record_id,
        "passed": True,
        "content_fingerprint": application_record_content_fingerprint(record),
        "approval_request": application_review_approval_request(
            record,
            chain,
            norm_version_status="verified",
            version_evidence_ids=(),
            preservation_rule_status="verified_not_required",
            norm_version_passport=passport,
            norm_version_approval_id=norm_receipt["trusted_approval_id"],
            preservation_rule_evidence=preservation,
            preservation_rule_approval_id=preservation_approval_id,
        ),
        "trusted_approval_id": "APPROVAL-APPLICATION",
        "preservation_rule_evidence": preservation,
        "preservation_rule_gate_receipt": {
            "passed": True,
            "content_fingerprint": preservation["content_fingerprint"],
            "approval_request": preservation_rule_review_approval_request(
                preservation
            ),
            "trusted_approval_id": preservation_approval_id,
        },
    }


def _request(
    evidence_ids: list[str] | None = None,
    *,
    maximum_supported_inference: str = "explicitly_applied",
) -> dict[str, Any]:
    return build_application_finding_binding_request(
        matter_id="MATTER-A",
        draft_id="DRAFT-A",
        sentence_id="sent-a111111111111111",
        section_code="facts",
        sentence_text="Суды применили оспариваемую норму в деле заявителя.",
        claim_id="CLAIM-A",
        norm_passport_id="NVP-A",
        application_record_ids=["APP-A"],
        evidence_ids=evidence_ids
        or ["E-EXPRESS", "E-OUTCOME", "E-RULE"],
        maximum_supported_inference=maximum_supported_inference,
    )


def _resolution(
    request: Mapping[str, Any], *, incorporated: bool = False
) -> dict[str, Any]:
    selected = application_record_from_dict(_positive_record_payload())
    records = [selected]
    if incorporated:
        records.append(
            application_record_from_dict(_incorporation_record_payload())
        )
    passport = _passport_payload()
    norm_receipt = _norm_receipt(passport)
    return build_application_finding_binding_resolution(
        request=request,
        application_records=[selected.to_dict()],
        chain_records=[record.to_dict() for record in records],
        norm_version_passport=passport,
        norm_version_gate_receipt=norm_receipt,
        application_gate_receipts=[
            _application_receipt(selected, records, passport, norm_receipt)
        ],
        trusted_scope_approval_id=TRUSTED_SCOPE_APPROVAL_ID,
        chain_revision_id=CHAIN_REVISION_ID,
        chain_checked_at=CHAIN_CHECKED_AT,
        authority_revision_id=AUTHORITY_REVISION_ID,
        checked_at=CHECKED_AT,
    )


def _resolution_for_payloads(
    request: Mapping[str, Any],
    *,
    selected_payload: Mapping[str, Any],
    chain_payloads: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    selected = application_record_from_dict(selected_payload)
    records = [
        application_record_from_dict(payload)
        for payload in (chain_payloads or [selected_payload])
    ]
    passport = _passport_payload()
    norm_receipt = _norm_receipt(passport)
    return build_application_finding_binding_resolution(
        request=request,
        application_records=[selected.to_dict()],
        chain_records=[record.to_dict() for record in records],
        norm_version_passport=passport,
        norm_version_gate_receipt=norm_receipt,
        application_gate_receipts=[
            _application_receipt(selected, records, passport, norm_receipt)
        ],
        trusted_scope_approval_id=TRUSTED_SCOPE_APPROVAL_ID,
        chain_revision_id=CHAIN_REVISION_ID,
        chain_checked_at=CHAIN_CHECKED_AT,
        authority_revision_id=AUTHORITY_REVISION_ID,
        checked_at=CHECKED_AT,
    )


def _index_binding(request: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sentence_id": request["sentence_id"],
        "section_code": request["section_code"],
        "role": "application_finding",
        "claim_id": request["claim_id"],
        "norm_passport_id": request["norm_passport_id"],
        "application_binding_sha256": request["application_binding_sha256"],
    }


class StaticApplicationAuthority:
    def __init__(
        self,
        resolution: Mapping[str, Any] | None,
        index_resolution: Mapping[str, Any] | None = None,
    ) -> None:
        self.resolution = deepcopy(resolution)
        self.index_resolution = deepcopy(index_resolution)

    def resolve_application_finding_evidence_binding(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None:
        return deepcopy(self.resolution)

    def resolve_application_finding_evidence_binding_index(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None:
        return deepcopy(self.index_resolution)


class MutatingApplicationAuthority(StaticApplicationAuthority):
    def resolve_application_finding_evidence_binding(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None:
        request["evidence_ids"].append("E-INJECTED")  # type: ignore[attr-defined]
        return deepcopy(self.resolution)


class ApplicationBindingRuntimeTests(unittest.TestCase):
    def test_wave_e_contract_binds_named_marker_without_trusted_approval(self) -> None:
        fixture_path = (
            SKILL_ROOT.parents[1]
            / "tests"
            / "fixtures"
            / "academic_wave_8_forward_contracts.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        contract = next(
            item
            for item in fixture["cases"]
            if item["id"] == "implicit_norm_use_with_independent_ground"
        )
        self.assertIs(contract["input_manifest"]["named_review_marker"], True)
        self.assertIs(
            contract["input_manifest"]["trusted_full_record_approval"], False
        )

        record = application_record_from_dict(
            _implicit_independent_ground_payload()
        )
        classification = classify_application(record)

        self.assertTrue(record.human_review.is_named_approval)
        self.assertEqual(
            "diagnostic_named_marker_only",
            contract["expected"]["review_status"],
        )
        self.assertEqual("required", contract["expected"]["trusted_approval_status"])
        self.assertEqual(
            contract["expected"]["norm_use_status"], record.norm_use_status
        )
        self.assertEqual(
            contract["expected"]["outcome_causation"], record.outcome_causation
        )
        self.assertEqual(
            contract["expected"]["application_status"], classification.status
        )
        self.assertNotIn("complete_independent_ground", classification.reason_codes)
        self.assertFalse(contract["expected"]["not_applied"])
        decision = evaluate_application_admissibility(
            record,
            assess_application_chain([record]),
            norm_version_status="unknown",
            version_evidence_ids=(),
            preservation_rule_status="unknown",
        )
        self.assertFalse(decision.passed)
        self.assertIn("human_application_review_required", decision.blockers)
        self.assertIn("causal_harm_not_proven", decision.blockers)

    def test_exact_positive_resolution_emits_current_receipt(self) -> None:
        request = _request()

        errors, receipt = resolve_application_finding_evidence_binding(
            request, StaticApplicationAuthority(_resolution(request))
        )

        self.assertEqual((), errors)
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(
            request["application_binding_sha256"],
            receipt["application_binding_sha256"],
        )
        self.assertEqual(AUTHORITY_REVISION_ID, receipt["authority_revision_id"])
        self.assertEqual(
            ["APP-A"], sorted(receipt["application_gate_receipts"])
        )
        self.assertEqual(
            ["APP-A"],
            sorted(
                receipt["chain_inventory_receipt"][
                    "record_content_fingerprints"
                ]
            ),
        )
        self.assertEqual(
            CHAIN_REVISION_ID,
            receipt["chain_inventory_receipt"]["chain_revision_id"],
        )
        self.assertEqual(
            CHAIN_CHECKED_AT,
            receipt["chain_inventory_receipt"]["checked_at"],
        )

    def test_complete_chain_can_include_unselected_incorporation_record(self) -> None:
        request = _request(
            ["E-EXPRESS", "E-INCORPORATION", "E-OUTCOME", "E-RULE"]
        )

        errors, receipt = resolve_application_finding_evidence_binding(
            request,
            StaticApplicationAuthority(_resolution(request, incorporated=True)),
        )

        self.assertEqual((), errors)
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(
            "incorporated",
            receipt["chain_inventory_receipt"]["chain_assessment"]["status"],
        )
        self.assertEqual(
            ["APP-A"], sorted(receipt["application_gate_receipts"])
        )
        self.assertEqual(
            ["APP-A", "APP-FINAL"],
            sorted(
                receipt["chain_inventory_receipt"][
                    "record_content_fingerprints"
                ]
            ),
        )

    def test_background_span_is_not_positive_application_proof(self) -> None:
        request = _request(["E-BACKGROUND"])

        errors, receipt = resolve_application_finding_evidence_binding(
            request, StaticApplicationAuthority(_resolution(request))
        )

        self.assertIn(
            "application_binding_evidence_not_positive:E-BACKGROUND", errors
        )
        self.assertIsNone(receipt)

    def test_implicit_background_cannot_be_smuggled_into_premise_proof(
        self,
    ) -> None:
        payload = _implicit_record_payload()
        payload["evidence"].append(
            {
                "evidence_id": "E-IMPLICIT-BACKGROUND",
                "claim_id": "CLAIM-A",
                "norm_id": "NORM-1",
                "act_id": "ACT-APP-A",
                "stage": "first_instance",
                "source_kind": "full_act",
                "locator": {"kind": "paragraph", "value": "абз. 2"},
                "quote": "Фоновое описание дела.",
                "speaker": "court",
                "reasoning_role": "background",
                "inference_status": "observed",
            }
        )
        payload["implicit_premises"][0]["evidence_ids"].append(
            "E-IMPLICIT-BACKGROUND"
        )
        request = _request(
            [
                "E-COUNTERFACTUAL",
                "E-IMPLICIT-BACKGROUND",
                "E-ISSUE",
                "E-LOGIC",
                "E-NO-ALTERNATIVE",
            ],
            maximum_supported_inference="implicitly_applied_proven",
        )

        errors, receipt = resolve_application_finding_evidence_binding(
            request,
            StaticApplicationAuthority(
                _resolution_for_payloads(request, selected_payload=payload)
            ),
        )

        self.assertIn(
            "application_binding_implicit_evidence_role_invalid:"
            "E-IMPLICIT-BACKGROUND",
            errors,
        )
        self.assertIsNone(receipt)

    def test_human_confirmed_reviewer_counterproof_is_allowed(self) -> None:
        payload = _implicit_record_payload()
        classification = classify_application(application_record_from_dict(payload))
        self.assertEqual("implicitly_applied_proven", classification.status)
        request = _request(
            [
                "E-COUNTERFACTUAL",
                "E-ISSUE",
                "E-LOGIC",
                "E-NO-ALTERNATIVE",
            ],
            maximum_supported_inference="implicitly_applied_proven",
        )

        errors, receipt = resolve_application_finding_evidence_binding(
            request,
            StaticApplicationAuthority(
                _resolution_for_payloads(request, selected_payload=payload)
            ),
        )

        self.assertEqual((), errors)
        self.assertIsNotNone(receipt)

    def test_independent_ground_does_not_erase_proven_implicit_norm_use(
        self,
    ) -> None:
        payload = _implicit_independent_ground_payload()

        classification = classify_application(application_record_from_dict(payload))

        self.assertEqual("application_unclear", classification.status)
        self.assertEqual(
            (
                "implicit_norm_use_preserved",
                "independent_ground_blocks_outcome_causation",
            ),
            classification.reason_codes,
        )
        self.assertEqual(
            ("E-ISSUE", "E-LOGIC", "E-INDEPENDENT"),
            classification.evidence_ids,
        )

        payload["affirmative_non_application"] = None
        classification_without_duplicate_assertion = classify_application(
            application_record_from_dict(payload)
        )
        self.assertEqual(
            classification,
            classification_without_duplicate_assertion,
        )

    def test_unapproved_implicit_candidate_stays_unclear_with_independent_ground(
        self,
    ) -> None:
        for state, reviewer, reviewed_at in (
            ("pending", None, None),
            ("rejected", "Reviewer A", "2026-09-12T18:00:00Z"),
            ("needs_changes", "Reviewer A", "2026-09-12T18:00:00Z"),
            ("approved", None, "2026-09-12T18:00:00Z"),
            ("approved", "Reviewer A", "not-a-timestamp"),
            ("approved", "Reviewer A", "2026-13-40T25:61:61Z"),
        ):
            with self.subTest(state=state, reviewer=reviewer):
                payload = _implicit_independent_ground_payload()
                payload["human_review"] = {
                    "state": state,
                    "reviewer": reviewer,
                    "reviewed_at": reviewed_at,
                    "note": "",
                }
                classification = classify_application(
                    application_record_from_dict(payload)
                )
                self.assertEqual("application_unclear", classification.status)
                self.assertEqual(
                    (
                        "implicit_norm_use_not_verified",
                        "independent_ground_blocks_outcome_causation",
                    ),
                    classification.reason_codes,
                )
                self.assertEqual(("E-INDEPENDENT",), classification.evidence_ids)

                payload["affirmative_non_application"] = None
                self.assertEqual(
                    classification,
                    classify_application(application_record_from_dict(payload)),
                )

    def test_contradicted_implicit_premise_is_not_preserved(
        self,
    ) -> None:
        for premise_index, premise in enumerate(
            ("issue_before_court", "operative_norm_logic")
        ):
            with self.subTest(premise=premise):
                payload = _implicit_independent_ground_payload()
                payload["implicit_premises"][premise_index][
                    "inference_status"
                ] = "contradicted"
                classification = classify_application(
                    application_record_from_dict(payload)
                )
                self.assertEqual("application_unclear", classification.status)
                self.assertEqual(
                    (
                        "implicit_norm_use_not_verified",
                        "independent_ground_blocks_outcome_causation",
                    ),
                    classification.reason_codes,
                )
                self.assertNotIn(
                    "implicit_norm_use_preserved", classification.reason_codes
                )

                request = _request(
                    ["E-INDEPENDENT", "E-ISSUE", "E-LOGIC"],
                    maximum_supported_inference="application_unclear",
                )
                errors, receipt = resolve_application_finding_evidence_binding(
                    request,
                    StaticApplicationAuthority(
                        _resolution_for_payloads(
                            request,
                            selected_payload=payload,
                        )
                    ),
                )
                self.assertIn(
                    "application_binding_implicit_premise_inference_invalid:"
                    f"{premise}",
                    errors,
                )
                self.assertIsNone(receipt)

                payload["affirmative_non_application"] = None
                generic = classify_application(application_record_from_dict(payload))
                self.assertEqual(classification, generic)

    def test_unusable_implicit_span_is_not_preserved(self) -> None:
        for label, evidence_index, field, value in (
            ("contradicted", 0, "inference_status", "contradicted"),
            ("blank_quote", 1, "quote", ""),
            ("missing_locator", 0, "locator", None),
        ):
            with self.subTest(label=label):
                payload = _implicit_independent_ground_payload()
                payload["evidence"][evidence_index][field] = value
                classification = classify_application(
                    application_record_from_dict(payload)
                )
                self.assertEqual("application_unclear", classification.status)
                self.assertEqual(
                    (
                        "implicit_norm_use_not_verified",
                        "independent_ground_blocks_outcome_causation",
                    ),
                    classification.reason_codes,
                )
                payload["affirmative_non_application"] = None
                self.assertEqual(
                    classification,
                    classify_application(application_record_from_dict(payload)),
                )

    def test_unapproved_complete_implicit_record_is_not_called_proven(self) -> None:
        for state, reviewer, reviewed_at in (
            ("pending", None, None),
            ("rejected", "Reviewer A", "2026-09-12T18:00:00Z"),
            ("needs_changes", "Reviewer A", "2026-09-12T18:00:00Z"),
            ("approved", "Reviewer A", None),
            ("approved", "Reviewer A", "not-a-timestamp"),
            ("approved", "Reviewer A", "2026-13-40T25:61:61Z"),
        ):
            with self.subTest(state=state, reviewed_at=reviewed_at):
                payload = _implicit_record_payload()
                payload["human_review"] = {
                    "state": state,
                    "reviewer": reviewer,
                    "reviewed_at": reviewed_at,
                    "note": "",
                }
                classification = classify_application(
                    application_record_from_dict(payload)
                )
                self.assertEqual("application_unclear", classification.status)
                self.assertEqual(
                    ("implicit_record_approval_required",),
                    classification.reason_codes,
                )

    def test_unusable_implicit_span_blocks_ordinary_proof(self) -> None:
        for label, evidence_index, field, value, expected_gap in (
            (
                "contradicted_issue",
                0,
                "inference_status",
                "contradicted",
                "issue_before_court:evidence_contradicted",
            ),
            (
                "missing_issue_locator",
                0,
                "locator",
                None,
                "issue_before_court:full_act_locator_required",
            ),
            (
                "blank_logic_quote",
                1,
                "quote",
                "   ",
                "operative_norm_logic:quote_required",
            ),
        ):
            with self.subTest(label=label):
                payload = _implicit_record_payload()
                payload["evidence"][evidence_index][field] = value

                classification = classify_application(
                    application_record_from_dict(payload)
                )

                self.assertEqual("application_unclear", classification.status)
                self.assertEqual(
                    ("implicit_application_not_proven",),
                    classification.reason_codes,
                )
                self.assertIn(expected_gap, classification.missing_premises)

    def test_contradicted_implicit_premise_blocks_ordinary_proof(self) -> None:
        for premise_index, premise in enumerate(
            (
                "issue_before_court",
                "operative_norm_logic",
                "counterfactual_outcome_dependence",
                "no_independent_sufficient_ground",
            )
        ):
            with self.subTest(premise=premise):
                payload = _implicit_record_payload()
                payload["implicit_premises"][premise_index][
                    "inference_status"
                ] = "contradicted"
                classification = classify_application(
                    application_record_from_dict(payload)
                )
                self.assertEqual("application_unclear", classification.status)
                self.assertEqual(
                    ("implicit_application_not_proven",),
                    classification.reason_codes,
                )
                self.assertIn(
                    f"{premise}:inference_contradicted",
                    classification.missing_premises,
                )

    def test_duplicate_implicit_premise_is_rejected_in_every_order(self) -> None:
        for contradicted_first in (True, False):
            with self.subTest(contradicted_first=contradicted_first):
                payload = _implicit_record_payload()
                contradicted = deepcopy(payload["implicit_premises"][0])
                contradicted["inference_status"] = "contradicted"
                if contradicted_first:
                    payload["implicit_premises"].insert(0, contradicted)
                else:
                    payload["implicit_premises"].append(contradicted)
                with self.assertRaisesRegex(
                    ValueError,
                    "implicit premise values must be unique",
                ):
                    application_record_from_dict(payload)

    def test_application_evidence_schema_rejects_duplicate_premises(self) -> None:
        schema = json.loads(
            (
                SKILL_ROOT
                / "schemas"
                / "ksrf_filing"
                / "application-evidence.schema.json"
            ).read_text(encoding="utf-8")
        )
        payload = _implicit_record_payload()
        payload["implicit_premises"].append(
            deepcopy(payload["implicit_premises"][0])
        )

        errors = list(Draft202012Validator(schema).iter_errors(payload))

        self.assertTrue(
            any(error.validator == "maxContains" for error in errors),
            errors,
        )

    def test_application_evidence_schema_accepts_canonical_implicit_record(
        self,
    ) -> None:
        schema = json.loads(
            (
                SKILL_ROOT
                / "schemas"
                / "ksrf_filing"
                / "application-evidence.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)

        errors = list(
            Draft202012Validator(schema).iter_errors(_implicit_record_payload())
        )

        self.assertEqual([], errors)

    def test_application_evidence_schema_rejects_malformed_review_timestamp(
        self,
    ) -> None:
        schema = json.loads(
            (
                SKILL_ROOT
                / "schemas"
                / "ksrf_filing"
                / "application-evidence.schema.json"
            ).read_text(encoding="utf-8")
        )
        payload = _implicit_record_payload()
        for value, expected_validator in (("not-a-timestamp", "pattern"),):
            with self.subTest(value=value):
                payload["human_review"]["reviewed_at"] = value
                errors = list(
                    Draft202012Validator(
                        schema,
                        format_checker=FormatChecker(),
                    ).iter_errors(payload)
                )
                self.assertTrue(
                    any(
                        error.validator == expected_validator
                        for error in errors
                    ),
                    errors,
                )

    def test_independent_ground_still_proves_non_application_without_use_candidate(
        self,
    ) -> None:
        payload = _implicit_independent_ground_payload()
        payload["norm_use_status"] = "unclear"
        payload["implicit_premises"] = []

        classification = classify_application(application_record_from_dict(payload))

        self.assertEqual("not_applied", classification.status)
        self.assertEqual(
            ("complete_independent_ground",), classification.reason_codes
        )
        payload["affirmative_non_application"] = None
        self.assertEqual(
            classification,
            classify_application(application_record_from_dict(payload)),
        )

    def test_party_assertion_cannot_prove_complete_independent_ground(self) -> None:
        payload = _implicit_independent_ground_payload()
        payload["norm_use_status"] = "unclear"
        payload["implicit_premises"] = []
        payload["evidence"][-1]["speaker"] = "party"

        classification = classify_application(application_record_from_dict(payload))

        self.assertEqual("application_unclear", classification.status)
        self.assertEqual(
            ("silence_is_not_non_application",), classification.reason_codes
        )

    def test_independent_ground_assertion_requires_matching_causation_axis(
        self,
    ) -> None:
        payload = _implicit_independent_ground_payload()
        payload["outcome_causation"] = "determinative"

        with self.assertRaisesRegex(
            ValueError,
            "complete independent ground assertion requires matching outcome causation",
        ):
            application_record_from_dict(payload)

    def test_court_independent_ground_span_requires_matching_causation_axis(
        self,
    ) -> None:
        payload = _implicit_record_payload()
        ground = deepcopy(_implicit_independent_ground_payload()["evidence"][-1])
        payload["evidence"].append(ground)

        with self.assertRaisesRegex(
            ValueError,
            "court independent ground evidence requires matching outcome causation",
        ):
            application_record_from_dict(payload)

    def test_application_evidence_schema_rejects_causal_axis_conflicts(
        self,
    ) -> None:
        schema = json.loads(
            (
                SKILL_ROOT
                / "schemas"
                / "ksrf_filing"
                / "application-evidence.schema.json"
            ).read_text(encoding="utf-8")
        )
        payloads = []

        assertion_payload = _implicit_independent_ground_payload()
        assertion_payload["outcome_causation"] = "determinative"
        payloads.append(assertion_payload)

        evidence_payload = _implicit_record_payload()
        evidence_payload["evidence"].append(
            deepcopy(_implicit_independent_ground_payload()["evidence"][-1])
        )
        payloads.append(evidence_payload)

        for payload in payloads:
            with self.subTest(record_id=payload["record_id"]):
                errors = list(Draft202012Validator(schema).iter_errors(payload))
                self.assertTrue(
                    any(error.validator == "const" for error in errors),
                    errors,
                )

    def test_invalid_extra_independent_ground_span_is_not_reported_as_evidence(
        self,
    ) -> None:
        for label, field, value in (
            ("contradicted", "inference_status", "contradicted"),
            ("party", "speaker", "party"),
            ("missing_locator", "locator", None),
            ("blank_quote", "quote", ""),
        ):
            for assertion_references_bad_span in (False, True):
                with self.subTest(
                    label=label,
                    assertion_references_bad_span=assertion_references_bad_span,
                ):
                    payload = _implicit_independent_ground_payload()
                    bad = deepcopy(payload["evidence"][-1])
                    bad["evidence_id"] = "E-BAD"
                    bad[field] = value
                    payload["evidence"].append(bad)
                    if assertion_references_bad_span:
                        payload["affirmative_non_application"][
                            "evidence_ids"
                        ].append("E-BAD")
                    else:
                        payload["affirmative_non_application"] = None

                    classification = classify_application(
                        application_record_from_dict(payload)
                    )

                    self.assertEqual("application_unclear", classification.status)
                    self.assertEqual(
                        (
                            "implicit_norm_use_preserved",
                            "independent_ground_blocks_outcome_causation",
                        ),
                        classification.reason_codes,
                    )
                    self.assertEqual(
                        ("E-ISSUE", "E-LOGIC", "E-INDEPENDENT"),
                        classification.evidence_ids,
                    )

    def test_contradicted_direct_span_is_not_positive_proof(self) -> None:
        payload = _positive_record_payload()
        contradicted = deepcopy(payload["evidence"][0])
        contradicted["evidence_id"] = "E-CONTRADICTED"
        contradicted["inference_status"] = "contradicted"
        payload["evidence"].append(contradicted)
        request = _request(
            ["E-CONTRADICTED", "E-EXPRESS", "E-OUTCOME", "E-RULE"]
        )

        errors, receipt = resolve_application_finding_evidence_binding(
            request,
            StaticApplicationAuthority(
                _resolution_for_payloads(request, selected_payload=payload)
            ),
        )

        self.assertIn(
            "application_binding_evidence_inference_invalid:E-CONTRADICTED",
            errors,
        )
        self.assertIsNone(receipt)

    def test_contradicted_incorporation_cannot_prove_survival(self) -> None:
        final_payload = _incorporation_record_payload()
        final_payload["evidence"][0]["inference_status"] = "contradicted"
        request = _request(
            ["E-EXPRESS", "E-INCORPORATION", "E-OUTCOME", "E-RULE"]
        )

        errors, receipt = resolve_application_finding_evidence_binding(
            request,
            StaticApplicationAuthority(
                _resolution_for_payloads(
                    request,
                    selected_payload=_positive_record_payload(),
                    chain_payloads=[_positive_record_payload(), final_payload],
                )
            ),
        )

        self.assertIn(
            "application_binding_evidence_inference_invalid:E-INCORPORATION",
            errors,
        )
        self.assertIn("application_binding_chain_not_release_supported", errors)
        self.assertIsNone(receipt)

    def test_blank_incorporation_quote_cannot_prove_survival(self) -> None:
        final_payload = _incorporation_record_payload()
        final_payload["evidence"][0]["quote"] = "   "
        request = _request(
            ["E-EXPRESS", "E-INCORPORATION", "E-OUTCOME", "E-RULE"]
        )

        errors, receipt = resolve_application_finding_evidence_binding(
            request,
            StaticApplicationAuthority(
                _resolution_for_payloads(
                    request,
                    selected_payload=_positive_record_payload(),
                    chain_payloads=[_positive_record_payload(), final_payload],
                )
            ),
        )

        self.assertIn("application_binding_chain_not_release_supported", errors)
        self.assertIn("application_binding_positive_evidence_set_mismatch", errors)
        self.assertIsNone(receipt)

    def test_unusable_later_independent_ground_cannot_prove_supersession(
        self,
    ) -> None:
        for label, field, value in (
            ("blank_quote", "quote", "   "),
            ("contradicted", "inference_status", "contradicted"),
        ):
            with self.subTest(label=label):
                final_payload = _incorporation_record_payload()
                final_payload["relation_to_prior"] = "superseding_ground"
                final_payload["incorporated_record_ids"] = []
                final_payload["outcome_causation"] = "independent_sufficient_ground"
                final_payload["evidence"][0]["reasoning_role"] = (
                    "independent_ground"
                )
                final_payload["evidence"][0][field] = value

                chain = assess_application_chain(
                    [
                        application_record_from_dict(_positive_record_payload()),
                        application_record_from_dict(final_payload),
                    ]
                )

                self.assertEqual("unclear", chain.status)
                self.assertEqual(
                    ("superseding_ground_not_proven",),
                    chain.reason_codes,
                )

    def test_foreign_norm_incorporation_span_is_rejected(self) -> None:
        final_payload = _incorporation_record_payload()
        final_payload["evidence"][0]["norm_id"] = "NORM-FOREIGN"
        request = _request(
            ["E-EXPRESS", "E-INCORPORATION", "E-OUTCOME", "E-RULE"]
        )

        errors, receipt = resolve_application_finding_evidence_binding(
            request,
            StaticApplicationAuthority(
                _resolution_for_payloads(
                    request,
                    selected_payload=_positive_record_payload(),
                    chain_payloads=[_positive_record_payload(), final_payload],
                )
            ),
        )

        self.assertIn(
            "application_binding_chain_evidence_scope_mismatch:"
            "E-INCORPORATION",
            errors,
        )
        self.assertIsNone(receipt)

    def test_incorporation_reference_must_exist_in_complete_chain(self) -> None:
        final_payload = _incorporation_record_payload()
        final_payload["incorporated_record_ids"].append("APP-MISSING")
        request = _request(
            ["E-EXPRESS", "E-INCORPORATION", "E-OUTCOME", "E-RULE"]
        )

        errors, receipt = resolve_application_finding_evidence_binding(
            request,
            StaticApplicationAuthority(
                _resolution_for_payloads(
                    request,
                    selected_payload=_positive_record_payload(),
                    chain_payloads=[_positive_record_payload(), final_payload],
                )
            ),
        )

        self.assertIn(
            "application_binding_incorporated_record_unknown:APP-MISSING",
            errors,
        )
        self.assertIsNone(receipt)

    def test_selected_evidence_must_cover_complete_positive_proof_set(self) -> None:
        request = _request(["E-EXPRESS"])

        errors, receipt = resolve_application_finding_evidence_binding(
            request, StaticApplicationAuthority(_resolution(request))
        )

        self.assertIn(
            "application_binding_positive_evidence_set_mismatch", errors
        )
        self.assertIsNone(receipt)

    def test_reviewed_statement_tampering_invalidates_scope(self) -> None:
        request = _request()
        resolution = _resolution(request)
        resolution["scope_record"]["reviewed_statement"] += " Дополнение."

        errors, receipt = resolve_application_finding_evidence_binding(
            request, StaticApplicationAuthority(resolution)
        )

        self.assertIn("application_binding_scope_record_mismatch", errors)
        self.assertIsNone(receipt)

    def test_index_authority_revision_is_independent_from_chain_scope(self) -> None:
        request = _request()
        resolution = _resolution(request)
        resolution["authority_revision_id"] = "application-authority-revision-2"

        errors, receipt = resolve_application_finding_evidence_binding(
            request, StaticApplicationAuthority(resolution)
        )

        self.assertEqual((), errors)
        self.assertIsNotNone(receipt)

    def test_chain_inventory_revision_and_time_are_bound_into_scope(self) -> None:
        request = _request()
        for field, replacement in (
            ("chain_revision_id", "APPLICATION-CHAIN-REV-2"),
            ("chain_checked_at", "2026-09-01T12:01:00Z"),
        ):
            with self.subTest(field=field):
                resolution = _resolution(request)
                resolution[field] = replacement

                errors, receipt = resolve_application_finding_evidence_binding(
                    request, StaticApplicationAuthority(resolution)
                )

                self.assertIn("application_binding_scope_record_mismatch", errors)
                self.assertIsNone(receipt)

    def test_authority_cannot_mutate_exact_request(self) -> None:
        request = _request()

        errors, receipt = resolve_application_finding_evidence_binding(
            request, MutatingApplicationAuthority(_resolution(request))
        )

        self.assertEqual(("application_binding_request_mutated",), errors)
        self.assertIsNone(receipt)

    def test_duplicate_chain_stage_order_is_rejected(self) -> None:
        request = _request(
            ["E-EXPRESS", "E-INCORPORATION", "E-OUTCOME", "E-RULE"]
        )
        resolution = _resolution(request, incorporated=True)
        resolution["chain_records"][1]["stage_order"] = 1

        errors, receipt = resolve_application_finding_evidence_binding(
            request, StaticApplicationAuthority(resolution)
        )

        self.assertIn(
            "application_binding_chain_records_stage_order_duplicate", errors
        )
        self.assertIsNone(receipt)

    def test_complete_index_accepts_empty_and_nonempty_host_sets(self) -> None:
        for bindings in ([], [_index_binding(_request())]):
            with self.subTest(bindings=bindings):
                index = build_application_finding_binding_index_resolution(
                    matter_id="MATTER-A",
                    draft_id="DRAFT-A",
                    bindings=bindings,
                    authority_revision_id=AUTHORITY_REVISION_ID,
                    checked_at=CHECKED_AT,
                )
                errors, receipt = (
                    resolve_application_finding_evidence_binding_index(
                        matter_id="MATTER-A",
                        draft_id="DRAFT-A",
                        expected_bindings=bindings,
                        authority=StaticApplicationAuthority(None, index),
                    )
                )

                self.assertEqual((), errors)
                self.assertIsNotNone(receipt)
                assert receipt is not None
                self.assertEqual(bindings, receipt["bindings"])
                self.assertEqual(
                    AUTHORITY_REVISION_ID, receipt["authority_revision_id"]
                )


if __name__ == "__main__":
    unittest.main()
