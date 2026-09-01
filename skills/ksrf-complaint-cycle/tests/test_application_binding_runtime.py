# pyright: reportMissingImports=false, reportMissingModuleSource=false
from __future__ import annotations

from copy import deepcopy
import sys
import unittest
from pathlib import Path
from typing import Any, Mapping


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
    payload["decision_rationale"] = "Неявное применение доказано по всем предпосылкам."
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
            "application_binding_chain_evidence_inference_invalid:"
            "E-INCORPORATION",
            errors,
        )
        self.assertIsNone(receipt)

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
