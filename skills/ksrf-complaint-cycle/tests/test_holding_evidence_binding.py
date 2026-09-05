from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = SKILL_ROOT / "lib"
TEST_ROOT = Path(__file__).resolve().parent
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from ksrf.filing.composer import (  # noqa: E402
    ComplaintModelError,
    StructuredComplaint,
    build_structured_complaint,
    require_release_support,
)
from ksrf.filing.application_binding import (  # noqa: E402
    build_application_finding_binding_index_resolution,
)
from ksrf.filing.holding_binding import (  # noqa: E402
    build_holding_binding_index_resolution,
    build_holding_binding_resolution,
    build_holding_claim_scope,
)
from ksrf.filing.release import (  # noqa: E402
    release_basis_sha256,
    verify_release_manifest,
)
from ksrf.filing.sentence_roles import (  # noqa: E402
    build_sentence_role_index_resolution,
)
from ksrf.filing.workflow import WorkflowRouter  # noqa: E402

from test_remedy_evidence_binding import (  # noqa: E402
    StaticAuthority,
    _complaint_payload,
    _resolution,
    _sentence,
)


REMEDY_SENTENCE_ID = "sent-aaaaaaaaaaaaaaaa"
HOLDING_SENTENCE_ID = "sent-bbbbbbbbbbbbbbbb"
SECOND_HOLDING_SENTENCE_ID = "sent-cccccccccccccccc"
EXTRA_HOLDING_SENTENCE_ID = "sent-dddddddddddddddd"
EVIDENCE_A = "source-evidence:sha256:" + "1" * 64
EVIDENCE_B = "source-evidence:sha256:" + "2" * 64
UNKNOWN_EVIDENCE = "source-evidence:sha256:" + "f" * 64
TRUSTED_SCOPE_APPROVAL_ID = "trusted-approval:sha256:" + "a" * 64
CHECKED_AT = "2026-09-01T10:00:00Z"


def _holding_sentence(
    sentence_id: str,
    *,
    evidence_ids: Sequence[Any] | Any = (EVIDENCE_A,),
    claim_id: Any = "CLAIM-A",
    text: str = "Официальная позиция подтверждает заявленный узкий предел.",
    maximum_supported_inference: Any = "Только заявленный узкий предел.",
    role: str = "legal_holding",
) -> dict[str, Any]:
    return {
        "sentence_id": sentence_id,
        "text": text,
        "role": role,
        "claim_id": claim_id,
        "evidence_ids": evidence_ids,
        "support_status": "verified",
        "maximum_supported_inference": maximum_supported_inference,
    }


def _complaint_with_holdings(
    holding_sentences: Sequence[Mapping[str, Any]],
) -> tuple[StructuredComplaint, StaticAuthority]:
    remedy_text = "Признать норму неконституционной"
    payload = _complaint_payload(
        [
            _sentence(
                REMEDY_SENTENCE_ID,
                "CLAIM-A",
                "ISSUE-A",
                "PASSPORT-A",
                "APP-A",
                "E-A",
                remedy_text,
            )
        ],
        issue_option_ids=["ISSUE-A"],
        norm_passport_ids=["PASSPORT-A"],
    )
    rights_section = next(
        section for section in payload["sections"] if section["code"] == "rights_analysis"
    )
    rights_section["sentences"] = copy.deepcopy(list(holding_sentences))
    complaint = build_structured_complaint(copy.deepcopy(payload))
    relief_authority = StaticAuthority(
        {
            REMEDY_SENTENCE_ID: _resolution(
                "CLAIM-A",
                "ISSUE-A",
                "PASSPORT-A",
                "APP-A",
                "E-A",
                remedy_text,
            )
        }
    )
    return complaint, relief_authority


def _holding_requests(complaint: StructuredComplaint) -> dict[str, dict[str, Any]]:
    requests: dict[str, dict[str, Any]] = {}
    for section in complaint.sections:
        for sentence in section.sentences:
            request = complaint.holding_binding_request(sentence)
            if request is not None:
                requests[sentence.sentence_id] = request
    return requests


def _index_bindings(complaint: StructuredComplaint) -> list[dict[str, str]]:
    return [
        {
            "sentence_id": request["sentence_id"],
            "section_code": request["section_code"],
            "role": "legal_holding",
            "holding_binding_sha256": request["holding_binding_sha256"],
        }
        for request in sorted(
            _holding_requests(complaint).values(),
            key=lambda item: item["sentence_id"],
        )
    ]


def _source_evidence(evidence_id: str) -> dict[str, Any]:
    digest = evidence_id.rsplit(":", 1)[-1]
    source_suffix = digest[:8]
    locator = f"https://ksrf.ru/decision/{source_suffix}#paragraph-12"
    return {
        "schema_version": "1.0.0",
        "observation_id": f"OBS-{source_suffix}",
        "source_id": f"KSRF-SOURCE-{source_suffix}",
        "issuer": "Конституционный Суд Российской Федерации",
        "authority_class": "official_primary",
        "origin_url": locator,
        "acquisition_transport": "direct_http",
        "discovery_transport": None,
        "redirect_chain": [],
        "retrieved_at": CHECKED_AT,
        "content_type": "application/pdf",
        "raw_object": {
            "sha256": digest,
            "size": 1024,
            "object_path": f"objects/{source_suffix}.pdf",
        },
        "extracted_object": None,
        "identity_checks": [],
        "derived_identity_checks": [],
        "identity_fingerprint": "source-identity:sha256:" + digest,
        "identity_verification_mode": "trusted_derived",
        "identity_verification_blockers": [],
        "verified_official_locator": locator,
        "human_identity_reviewer": None,
        "approval_ids": [],
        "trusted_approval_id": None,
        "transform_chain": [],
        "filing_authority_state": "verified_official",
        "filing_ready": True,
        "validation_state": "verified",
        "supersedes_evidence_id": None,
        "evidence_id": evidence_id,
        "verification_revision_id": "source-verification:sha256:" + digest,
    }


def _current_authority(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": evidence["evidence_id"],
        "filing_ready": True,
        "identity_verification_mode": evidence["identity_verification_mode"],
        "blockers": [],
    }


def _positive_resolution(
    request: Mapping[str, Any],
    *,
    source_evidence: Sequence[Mapping[str, Any]] | None = None,
    claim_scope: Sequence[Mapping[str, Any]] | None = None,
    current_authority: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    sources = (
        [copy.deepcopy(dict(item)) for item in source_evidence]
        if source_evidence is not None
        else [_source_evidence(item) for item in request["evidence_ids"]]
    )
    scopes = (
        [copy.deepcopy(dict(item)) for item in claim_scope]
        if claim_scope is not None
        else [
            build_holding_claim_scope(
                evidence=evidence,
                claim_id=request["claim_id"],
                pinpoint=f"абз. {ordinal}",
                maximum_supported_inference=request["maximum_supported_inference"],
                checked_at=CHECKED_AT,
            )
            for ordinal, evidence in enumerate(sources, start=1)
        ]
    )
    current = (
        [copy.deepcopy(dict(item)) for item in current_authority]
        if current_authority is not None
        else [_current_authority(evidence) for evidence in sources]
    )
    return build_holding_binding_resolution(
        request=request,
        source_evidence=sources,
        current_authority=current,
        claim_scope=scopes,
        trusted_approval_id=TRUSTED_SCOPE_APPROVAL_ID,
        authority_revision_id="HOLDING-AUTHORITY-REV-1",
        checked_at=CHECKED_AT,
    )


class StaticHoldingAuthority:
    """Host fixture with an independently supplied complete draft index."""

    def __init__(
        self,
        resolutions: Mapping[str, Mapping[str, Any]],
        *,
        binding_index_snapshot: Sequence[Mapping[str, Any]] | None,
    ) -> None:
        self.resolutions = {
            key: copy.deepcopy(dict(value)) for key, value in resolutions.items()
        }
        self.binding_index_snapshot = (
            None
            if binding_index_snapshot is None
            else [copy.deepcopy(dict(item)) for item in binding_index_snapshot]
        )
        self.line_requests: list[dict[str, Any]] = []
        self.index_requests: list[dict[str, Any]] = []
        self.mutate_line_request = False
        self.mutate_index_request = False

    def resolve_holding_evidence_binding(
        self, request: dict[str, Any]
    ) -> dict[str, Any] | None:
        self.line_requests.append(copy.deepcopy(request))
        if self.mutate_line_request:
            request["claim_id"] = "CLAIM-MUTATED-BY-ADAPTER"
        resolution = self.resolutions.get(request["sentence_id"])
        return copy.deepcopy(resolution) if resolution is not None else None

    def resolve_holding_evidence_binding_index(
        self, request: dict[str, Any]
    ) -> dict[str, Any] | None:
        self.index_requests.append(copy.deepcopy(request))
        if self.mutate_index_request:
            request["draft_id"] = "DRAFT-MUTATED-BY-ADAPTER"
        if self.binding_index_snapshot is None:
            return None
        return build_holding_binding_index_resolution(
            matter_id=self.index_requests[-1]["matter_id"],
            draft_id=self.index_requests[-1]["draft_id"],
            bindings=self.binding_index_snapshot,
            authority_revision_id="HOLDING-DRAFT-REGISTRY-REV-1",
            checked_at=CHECKED_AT,
        )


class StaticSentenceRoleAuthority:
    def __init__(self, complaint: StructuredComplaint) -> None:
        self.bindings = complaint.sentence_role_index_bindings()

    def resolve_sentence_role_index(
        self, request: dict[str, Any]
    ) -> dict[str, Any]:
        return build_sentence_role_index_resolution(
            matter_id=request["matter_id"],
            draft_id=request["draft_id"],
            bindings=self.bindings,
            authority_revision_id="ROLE-DRAFT-REGISTRY-REV-1",
            checked_at=CHECKED_AT,
        )


class StaticEmptyApplicationAuthority:
    def resolve_application_finding_evidence_binding_index(
        self, request: dict[str, Any]
    ) -> dict[str, Any]:
        return build_application_finding_binding_index_resolution(
            matter_id=request["matter_id"],
            draft_id=request["draft_id"],
            bindings=[],
            authority_revision_id="APPLICATION-DRAFT-REGISTRY-REV-1",
            checked_at=CHECKED_AT,
        )


def _positive_authority(complaint: StructuredComplaint) -> StaticHoldingAuthority:
    requests = _holding_requests(complaint)
    return StaticHoldingAuthority(
        {
            sentence_id: _positive_resolution(request)
            for sentence_id, request in requests.items()
        },
        binding_index_snapshot=_index_bindings(complaint),
    )


def _manifest_for(
    complaint: StructuredComplaint,
    relief_authority: StaticAuthority,
    holding_authority: StaticHoldingAuthority,
    *,
    status: str = "blocked",
) -> dict[str, Any]:
    receipts = require_release_support(
        complaint,
        relief_binding_authority=relief_authority,
        holding_binding_authority=holding_authority,
        require_holding_index=True,
    )
    manifest: dict[str, Any] = {
        "schema_version": "1.3",
        "matter_id": complaint.matter_id,
        "draft_id": complaint.draft_id,
        "status": status,
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
        "relief_binding_receipts": list(receipts.relief_binding_receipts),
        "relief_binding_index_receipt": (
            copy.deepcopy(
                receipts.relief_binding_receipts[0]["binding_index_receipt"]
            )
            if receipts.relief_binding_receipts
            else None
        ),
        "holding_binding_receipts": list(receipts.holding_binding_receipts),
        "holding_binding_index_receipt": copy.deepcopy(
            receipts.holding_binding_index_receipt
        ),
        "practice_binding_receipts": list(receipts.practice_binding_receipts),
        "practice_binding_index_receipt": copy.deepcopy(
            receipts.practice_binding_index_receipt
        ),
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


class HoldingEvidenceBindingTests(unittest.TestCase):
    def _require(
        self,
        complaint: StructuredComplaint,
        relief_authority: StaticAuthority,
        holding_authority: StaticHoldingAuthority | None,
        *,
        require_holding_index: bool = False,
    ) -> Any:
        return require_release_support(
            complaint,
            relief_binding_authority=relief_authority,
            holding_binding_authority=holding_authority,
            require_holding_index=require_holding_index,
        )

    def test_positive_single_holding_emits_exact_receipt_and_complete_index(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        authority = _positive_authority(complaint)

        receipts = self._require(complaint, relief, authority)

        self.assertEqual(len(receipts.holding_binding_receipts), 1)
        receipt = receipts.holding_binding_receipts[0]
        self.assertEqual(receipt["sentence_id"], HOLDING_SENTENCE_ID)
        self.assertEqual(receipt["evidence_ids"], [EVIDENCE_A])
        self.assertEqual(set(receipt["source_evidence_receipts"]), {EVIDENCE_A})
        self.assertEqual(
            receipt["scope_gate_receipt"]["trusted_approval_id"],
            TRUSTED_SCOPE_APPROVAL_ID,
        )
        self.assertEqual(
            receipts.holding_binding_index_receipt["bindings"],
            _index_bindings(complaint),
        )

    def test_verified_looking_fictional_holding_requires_host_authority(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [
                _holding_sentence(
                    HOLDING_SENTENCE_ID,
                    evidence_ids=[UNKNOWN_EVIDENCE],
                )
            ]
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_binding_authority_required"
        ):
            self._require(complaint, relief, None)

    def test_syntactically_valid_unknown_evidence_is_rejected(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [
                _holding_sentence(
                    HOLDING_SENTENCE_ID,
                    evidence_ids=[UNKNOWN_EVIDENCE],
                )
            ]
        )
        authority = StaticHoldingAuthority(
            {}, binding_index_snapshot=_index_bindings(complaint)
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_binding_resolution_missing"
        ):
            self._require(complaint, relief, authority)

    def test_cross_claim_scope_is_rejected(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        request = _holding_requests(complaint)[HOLDING_SENTENCE_ID]
        evidence = _source_evidence(EVIDENCE_A)
        wrong_scope = build_holding_claim_scope(
            evidence=evidence,
            claim_id="CLAIM-B",
            pinpoint="абз. 12",
            maximum_supported_inference=request["maximum_supported_inference"],
            checked_at=CHECKED_AT,
        )
        authority = StaticHoldingAuthority(
            {
                HOLDING_SENTENCE_ID: _positive_resolution(
                    request,
                    source_evidence=[evidence],
                    claim_scope=[wrong_scope],
                )
            },
            binding_index_snapshot=_index_bindings(complaint),
        )

        with self.assertRaisesRegex(
            ComplaintModelError,
            "holding_claim_scope_binding_mismatch:.*:claim_id",
        ):
            self._require(complaint, relief, authority)

    def test_holding_evidence_ids_are_not_string_coerced(self) -> None:
        with self.assertRaisesRegex(ComplaintModelError, "evidence_ids"):
            _complaint_with_holdings(
                [
                    _holding_sentence(
                        HOLDING_SENTENCE_ID,
                        evidence_ids=EVIDENCE_A,
                    )
                ]
            )

    def test_holding_evidence_id_entries_are_not_scalar_coerced(self) -> None:
        with self.assertRaisesRegex(ComplaintModelError, "evidence_ids"):
            _complaint_with_holdings(
                [
                    _holding_sentence(
                        HOLDING_SENTENCE_ID,
                        evidence_ids=[7],
                    )
                ]
            )

    def test_malformed_holding_evidence_id_is_rejected_before_authority(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [
                _holding_sentence(
                    HOLDING_SENTENCE_ID,
                    evidence_ids=["NOT-A-SOURCE-EVIDENCE-ID"],
                )
            ]
        )
        authority = StaticHoldingAuthority(
            {}, binding_index_snapshot=_index_bindings(complaint)
        )

        with self.assertRaisesRegex(
            ComplaintModelError,
            "holding_binding_request_evidence_ids_identifier_invalid:1",
        ):
            self._require(complaint, relief, authority)
        self.assertEqual(authority.line_requests, [])

    def test_superseded_or_noncurrent_scope_is_rejected(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        request = _holding_requests(complaint)[HOLDING_SENTENCE_ID]
        for field, value, marker in (
            ("current_evidence_id", EVIDENCE_B, "current_evidence_id"),
            ("freshness_state", "superseded", "holding_claim_scope_not_current"),
        ):
            with self.subTest(field=field):
                resolution = _positive_resolution(request)
                resolution["claim_scope"][0][field] = value
                authority = StaticHoldingAuthority(
                    {HOLDING_SENTENCE_ID: resolution},
                    binding_index_snapshot=_index_bindings(complaint),
                )
                with self.assertRaisesRegex(ComplaintModelError, marker):
                    self._require(complaint, relief, authority)

    def test_raw_sha_or_verification_revision_drift_is_rejected(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        request = _holding_requests(complaint)[HOLDING_SENTENCE_ID]
        for field, value, marker in (
            ("raw_sha256", "9" * 64, "raw_sha256"),
            (
                "verification_revision_id",
                "source-verification:sha256:" + "9" * 64,
                "verification_revision_id",
            ),
        ):
            with self.subTest(field=field):
                resolution = _positive_resolution(request)
                resolution["claim_scope"][0][field] = value
                authority = StaticHoldingAuthority(
                    {HOLDING_SENTENCE_ID: resolution},
                    binding_index_snapshot=_index_bindings(complaint),
                )
                with self.assertRaisesRegex(ComplaintModelError, marker):
                    self._require(complaint, relief, authority)

    def test_locator_or_pinpoint_tampering_is_rejected(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        request = _holding_requests(complaint)[HOLDING_SENTENCE_ID]
        mutations = (
            (
                "verified_official_locator",
                "https://ksrf.ru/decision/other#paragraph-1",
                "verified_official_locator",
            ),
            ("pinpoint", "абз. 999", "holding_scope_approval_request_mismatch"),
        )
        for field, value, marker in mutations:
            with self.subTest(field=field):
                resolution = _positive_resolution(request)
                resolution["claim_scope"][0][field] = value
                authority = StaticHoldingAuthority(
                    {HOLDING_SENTENCE_ID: resolution},
                    binding_index_snapshot=_index_bindings(complaint),
                )
                with self.assertRaisesRegex(ComplaintModelError, marker):
                    self._require(complaint, relief, authority)

    def test_maximum_supported_inference_mismatch_is_rejected(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        request = _holding_requests(complaint)[HOLDING_SENTENCE_ID]
        resolution = _positive_resolution(request)
        resolution["claim_scope"][0]["maximum_supported_inference"] = (
            "Более широкий, не подтверждённый источником вывод."
        )
        authority = StaticHoldingAuthority(
            {HOLDING_SENTENCE_ID: resolution},
            binding_index_snapshot=_index_bindings(complaint),
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "maximum_supported_inference"
        ):
            self._require(complaint, relief, authority)

    def test_current_authority_must_be_filing_ready_without_blockers(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        request = _holding_requests(complaint)[HOLDING_SENTENCE_ID]
        evidence = _source_evidence(EVIDENCE_A)
        current = _current_authority(evidence)
        current["filing_ready"] = False
        current["blockers"] = ["source_superseded"]
        authority = StaticHoldingAuthority(
            {
                HOLDING_SENTENCE_ID: _positive_resolution(
                    request,
                    source_evidence=[evidence],
                    current_authority=[current],
                )
            },
            binding_index_snapshot=_index_bindings(complaint),
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_current_authority_not_ready"
        ):
            self._require(complaint, relief, authority)

    def test_nonofficial_or_unverified_source_cannot_support_holding(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        request = _holding_requests(complaint)[HOLDING_SENTENCE_ID]
        for field, value, marker in (
            (
                "authority_class",
                "discovery_only",
                "authority_class_not_official",
            ),
            (
                "identity_verification_mode",
                "unverified",
                "identity_verification_mode_not_trusted",
            ),
        ):
            with self.subTest(field=field):
                evidence = _source_evidence(EVIDENCE_A)
                evidence[field] = value
                authority = StaticHoldingAuthority(
                    {
                        HOLDING_SENTENCE_ID: _positive_resolution(
                            request,
                            source_evidence=[evidence],
                            current_authority=[_current_authority(evidence)],
                        )
                    },
                    binding_index_snapshot=_index_bindings(complaint),
                )
                with self.assertRaisesRegex(ComplaintModelError, marker):
                    self._require(complaint, relief, authority)

    def test_maximum_supported_inference_is_not_coerced_or_normalized(self) -> None:
        for value in (7, "  Только заявленный предел.  "):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ComplaintModelError, "maximum_supported_inference"
                ):
                    _complaint_with_holdings(
                        [
                            _holding_sentence(
                                HOLDING_SENTENCE_ID,
                                maximum_supported_inference=value,
                            )
                        ]
                    )

    def test_host_adapter_cannot_mutate_exact_line_request(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        authority = _positive_authority(complaint)
        authority.mutate_line_request = True

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_binding_request_mutated"
        ):
            self._require(complaint, relief, authority)

    def test_vsrf_or_other_authority_role_cannot_support_ksrf_holding(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        request = _holding_requests(complaint)[HOLDING_SENTENCE_ID]
        evidence = _source_evidence(EVIDENCE_A)
        vsrf_scope = build_holding_claim_scope(
            evidence=evidence,
            claim_id=request["claim_id"],
            pinpoint="абз. 12",
            maximum_supported_inference=request["maximum_supported_inference"],
            checked_at=CHECKED_AT,
            authority_role="vsrf_legal_holding",
        )
        authority = StaticHoldingAuthority(
            {
                HOLDING_SENTENCE_ID: _positive_resolution(
                    request,
                    source_evidence=[evidence],
                    claim_scope=[vsrf_scope],
                )
            },
            binding_index_snapshot=_index_bindings(complaint),
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_claim_scope_authority_role_invalid"
        ):
            self._require(complaint, relief, authority)

    def test_ready_path_requires_authoritative_empty_index_without_holdings(self) -> None:
        complaint, relief = _complaint_with_holdings([])

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_binding_index_authority_required"
        ):
            self._require(
                complaint,
                relief,
                None,
                require_holding_index=True,
            )

        authority = StaticHoldingAuthority({}, binding_index_snapshot=[])
        receipts = self._require(
            complaint,
            relief,
            authority,
            require_holding_index=True,
        )
        self.assertEqual(receipts.holding_binding_receipts, ())
        self.assertEqual(receipts.holding_binding_index_receipt["bindings"], [])

    def test_complaint_insertion_not_present_in_host_index_is_rejected(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        requests = _holding_requests(complaint)
        authority = StaticHoldingAuthority(
            {
                HOLDING_SENTENCE_ID: _positive_resolution(
                    requests[HOLDING_SENTENCE_ID]
                )
            },
            binding_index_snapshot=[],
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_binding_index_set_mismatch"
        ):
            self._require(complaint, relief, authority)

    def test_complaint_deletion_from_host_index_is_rejected(self) -> None:
        baseline, _baseline_relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        prior_index = _index_bindings(baseline)
        complaint, relief = _complaint_with_holdings([])
        authority = StaticHoldingAuthority({}, binding_index_snapshot=prior_index)

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_binding_index_set_mismatch"
        ):
            self._require(
                complaint,
                relief,
                authority,
                require_holding_index=True,
            )

    def test_legal_holding_role_downgrade_cannot_hide_host_binding(self) -> None:
        baseline, _baseline_relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        prior_index = _index_bindings(baseline)
        complaint, relief = _complaint_with_holdings(
            [
                _holding_sentence(
                    HOLDING_SENTENCE_ID,
                    role="narrative",
                    evidence_ids=[EVIDENCE_A],
                )
            ]
        )
        authority = StaticHoldingAuthority({}, binding_index_snapshot=prior_index)

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_binding_index_set_mismatch"
        ):
            self._require(
                complaint,
                relief,
                authority,
                require_holding_index=True,
            )

    def test_render_route_blocks_deleted_or_downgraded_host_holding(self) -> None:
        baseline, _baseline_relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        prior_index = _index_bindings(baseline)
        cases = {
            "deleted": [],
            "role_downgraded": [
                _holding_sentence(
                    HOLDING_SENTENCE_ID,
                    role="narrative",
                    evidence_ids=[EVIDENCE_A],
                )
            ],
        }
        for label, sentences in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as temp_dir:
                complaint, relief = _complaint_with_holdings(sentences)
                holding_authority = StaticHoldingAuthority(
                    {}, binding_index_snapshot=prior_index
                )
                router = object.__new__(WorkflowRouter)
                router.workspace = Path(temp_dir)
                router.relief_binding_authority = relief
                router.application_binding_authority = (
                    StaticEmptyApplicationAuthority()
                )
                router.holding_binding_authority = holding_authority
                router.sentence_role_authority = StaticSentenceRoleAuthority(
                    complaint
                )

                result = router._dispatch_supported(
                    "render",
                    "build",
                    {"complaint": complaint.to_dict()},
                    {"sha256": "7" * 64},
                    allow_network=False,
                )

                self.assertEqual(result["state"], "blocked")
                self.assertEqual(
                    result["result"]["reason_code"],
                    "evidence_authority_required",
                )
                self.assertIn(
                    "holding_binding_index_set_mismatch",
                    result["result"]["error"],
                )

    def test_host_index_insertion_is_rejected(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        authority = _positive_authority(complaint)
        assert authority.binding_index_snapshot is not None
        authority.binding_index_snapshot.append(
            {
                "sentence_id": EXTRA_HOLDING_SENTENCE_ID,
                "section_code": "rights_analysis",
                "role": "legal_holding",
                "holding_binding_sha256": "e" * 64,
            }
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_binding_index_set_mismatch"
        ):
            self._require(complaint, relief, authority)

    def test_host_adapter_cannot_mutate_index_lookup(self) -> None:
        complaint, relief = _complaint_with_holdings([])
        authority = StaticHoldingAuthority({}, binding_index_snapshot=[])
        authority.mutate_index_request = True

        with self.assertRaisesRegex(
            ComplaintModelError, "holding_binding_index_request_mutated"
        ):
            self._require(
                complaint,
                relief,
                authority,
                require_holding_index=True,
            )

    def test_positive_multiple_holding_lines_and_sources(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [
                _holding_sentence(
                    HOLDING_SENTENCE_ID,
                    evidence_ids=[EVIDENCE_A, EVIDENCE_B],
                ),
                _holding_sentence(
                    SECOND_HOLDING_SENTENCE_ID,
                    evidence_ids=[EVIDENCE_B],
                    text="Вторая официальная позиция подтверждает иной узкий предел.",
                    maximum_supported_inference="Только второй заявленный предел.",
                ),
            ]
        )
        authority = _positive_authority(complaint)

        receipts = self._require(complaint, relief, authority)

        self.assertEqual(len(receipts.holding_binding_receipts), 2)
        self.assertEqual(
            [item["sentence_id"] for item in receipts.holding_binding_receipts],
            [HOLDING_SENTENCE_ID, SECOND_HOLDING_SENTENCE_ID],
        )
        self.assertEqual(
            receipts.holding_binding_index_receipt["bindings"],
            _index_bindings(complaint),
        )

    def test_manifest_revalidation_requires_current_holding_authority(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        authority = _positive_authority(complaint)
        manifest = _manifest_for(complaint, relief, authority)

        errors = verify_release_manifest(
            manifest,
            relief_binding_authority=relief,
            holding_binding_authority=None,
        )

        self.assertTrue(
            any("holding_binding_authority_required" in error for error in errors),
            errors,
        )

    def test_manifest_source_or_scope_change_stales_holding_receipt(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        request = _holding_requests(complaint)[HOLDING_SENTENCE_ID]
        for change in ("source", "scope"):
            with self.subTest(change=change):
                authority = _positive_authority(complaint)
                manifest = _manifest_for(complaint, relief, authority)
                source = _source_evidence(EVIDENCE_A)
                if change == "source":
                    source["raw_object"]["sha256"] = "9" * 64
                    source["verification_revision_id"] = (
                        "source-verification:sha256:" + "9" * 64
                    )
                    source["identity_fingerprint"] = (
                        "source-identity:sha256:" + "9" * 64
                    )
                    pinpoint = "абз. 1"
                else:
                    pinpoint = "абз. 99"
                scope = build_holding_claim_scope(
                    evidence=source,
                    claim_id=request["claim_id"],
                    pinpoint=pinpoint,
                    maximum_supported_inference=request[
                        "maximum_supported_inference"
                    ],
                    checked_at=CHECKED_AT,
                )
                authority.resolutions[HOLDING_SENTENCE_ID] = _positive_resolution(
                    request,
                    source_evidence=[source],
                    claim_scope=[scope],
                )

                errors = verify_release_manifest(
                    manifest,
                    relief_binding_authority=relief,
                    holding_binding_authority=authority,
                )

                self.assertIn(
                    f"holding_binding_receipt_stale:{HOLDING_SENTENCE_ID}",
                    errors,
                )

    def test_manifest_index_revision_change_is_detected_as_toctou(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        authority = _positive_authority(complaint)
        manifest = _manifest_for(complaint, relief, authority)
        manifest_index = manifest["holding_binding_index_receipt"]
        self.assertIsNotNone(manifest_index)
        manifest_index["authority_revision_id"] = "STALE-HOLDING-INDEX-REV"
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest,
            relief_binding_authority=relief,
            holding_binding_authority=authority,
        )

        self.assertIn("holding_binding_index_receipt_stale", errors)

    def test_manifest_sentence_text_change_cannot_reuse_holding_receipt(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        authority = _positive_authority(complaint)
        manifest = _manifest_for(complaint, relief, authority)
        holding_entry = next(
            item
            for item in manifest["sentence_evidence_map"]
            if item["sentence_id"] == HOLDING_SENTENCE_ID
        )
        holding_entry["text"] = "Подменённый текст правовой позиции."
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest,
            relief_binding_authority=relief,
            holding_binding_authority=authority,
        )

        self.assertIn(
            f"holding_binding_projection_sha_mismatch:{HOLDING_SENTENCE_ID}",
            errors,
        )

    def test_manifest_requires_canonical_sorted_holding_evidence_ids(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [
                _holding_sentence(
                    HOLDING_SENTENCE_ID,
                    evidence_ids=[EVIDENCE_A, EVIDENCE_B],
                )
            ]
        )
        authority = _positive_authority(complaint)
        manifest = _manifest_for(complaint, relief, authority)
        holding_entry = next(
            item
            for item in manifest["sentence_evidence_map"]
            if item["sentence_id"] == HOLDING_SENTENCE_ID
        )
        holding_entry["evidence_ids"] = [EVIDENCE_B, EVIDENCE_A]
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest,
            relief_binding_authority=relief,
            holding_binding_authority=authority,
        )

        self.assertIn(
            "holding_binding_identifier_order_invalid:"
            f"{HOLDING_SENTENCE_ID}:evidence_ids",
            errors,
        )

    def test_ready_manifest_requires_nonnull_authoritative_empty_index(self) -> None:
        complaint, relief = _complaint_with_holdings([])
        authority = StaticHoldingAuthority({}, binding_index_snapshot=[])
        manifest = _manifest_for(
            complaint,
            relief,
            authority,
            status="ready_for_expert_review",
        )

        positive_errors = verify_release_manifest(
            manifest,
            relief_binding_authority=relief,
            holding_binding_authority=authority,
        )
        self.assertFalse(
            any(error.startswith("holding_binding_") for error in positive_errors),
            positive_errors,
        )

        manifest["holding_binding_index_receipt"] = None
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)
        missing_errors = verify_release_manifest(
            manifest,
            relief_binding_authority=relief,
            holding_binding_authority=authority,
        )
        self.assertIn("holding_binding_index_receipt_missing", missing_errors)

    def test_manifest_cannot_delete_or_downgrade_only_holding_line(self) -> None:
        complaint, relief = _complaint_with_holdings(
            [_holding_sentence(HOLDING_SENTENCE_ID)]
        )
        authority = _positive_authority(complaint)
        baseline = _manifest_for(complaint, relief, authority)
        for mutation in ("delete", "downgrade"):
            with self.subTest(mutation=mutation):
                manifest = copy.deepcopy(baseline)
                if mutation == "delete":
                    manifest["sentence_evidence_map"] = [
                        item
                        for item in manifest["sentence_evidence_map"]
                        if item["sentence_id"] != HOLDING_SENTENCE_ID
                    ]
                else:
                    holding_entry = next(
                        item
                        for item in manifest["sentence_evidence_map"]
                        if item["sentence_id"] == HOLDING_SENTENCE_ID
                    )
                    holding_entry["role"] = "narrative"
                    holding_entry["holding_binding_status"] = "unbound"
                manifest["release_basis_sha256"] = release_basis_sha256(manifest)

                errors = verify_release_manifest(
                    manifest,
                    relief_binding_authority=relief,
                    holding_binding_authority=authority,
                )

                self.assertTrue(
                    "holding_binding_index_projection_mismatch" in errors
                    or any(
                        error.startswith("holding_binding_receipt_orphan:")
                        for error in errors
                    ),
                    errors,
                )


if __name__ == "__main__":
    unittest.main()
