from __future__ import annotations

import copy
from hashlib import sha256
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = SKILL_ROOT / "lib"
TEST_ROOT = Path(__file__).resolve().parent
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from ksrf.filing.composer import (  # noqa: E402
    ComplaintModelError,
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
from ksrf.filing.practice_binding import (  # noqa: E402
    build_practice_claim_binding_index_resolution,
    build_practice_claim_binding_request,
)
from ksrf.filing.release import (  # noqa: E402
    _manifest_practice_binding_projection_errors,
    release_basis_sha256,
    verify_release_manifest,
)
from ksrf.filing.sentence_roles import (  # noqa: E402
    build_sentence_role_index_resolution,
    sentence_role_binding,
)
from ksrf.filing.storage import canonical_json_bytes  # noqa: E402

from test_remedy_evidence_binding import (  # noqa: E402
    StaticAuthority,
    _complaint_payload,
    _resolution,
    _sentence,
)
from test_practice_binding_module import (  # noqa: E402
    StaticAuthority as StaticPracticeAuthority,
    _rebind_result_handoff,
    _valid_case,
)


REMEDY_SENTENCE_ID = "sent-aaaaaaaaaaaaaaaa"
PRACTICE_SENTENCE_ID = "sent-eeeeeeeeeeeeeeee"
SECOND_PRACTICE_SENTENCE_ID = "sent-dddddddddddddddd"
FICTIONAL_FINDING_ID = "f" * 64
FILING_SCHEMA_PATH = (
    SKILL_ROOT / "schemas" / "ksrf_filing" / "filing-package.schema.json"
)


def _digest(value: object) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def _retarget_practice_resolution_text(
    request: dict[str, object],
    resolution: dict[str, object],
    sentence_text: str,
) -> tuple[dict[str, object], dict[str, object]]:
    """Rebuild the text-dependent native projections in the integration fixture."""

    resolution = copy.deepcopy(resolution)
    result = resolution["result"]
    payload = result["payload"]
    bridge = payload["selected_proofs"]["bridge"]
    bridge["claim_wording"] = sentence_text
    normative_bridge_sha256 = _digest(bridge)
    payload["approval_binding"][
        "normative_bridge_sha256"
    ] = normative_bridge_sha256
    for artifact in payload["artifact_manifest"]["files"]:
        if artifact["path"] == "normative-bridge.json":
            artifact["bytes"] = len(canonical_json_bytes(bridge))
            artifact["sha256"] = normative_bridge_sha256
    payload["artifact_manifest"]["manifest_sha256"] = _digest(
        payload["artifact_manifest"]["files"]
    )
    finding = payload["findings"][0]
    candidate = finding["candidate"]
    candidate["claim_wording"] = sentence_text
    candidate_sha256 = _digest(candidate)
    finding["candidate_sha256"] = candidate_sha256
    finding["claim_wording"] = sentence_text
    finding_id = _digest(
        {
            "candidate_sha256": candidate_sha256,
            "claim_ids": finding["claim_ids"],
            "normative_bridge_sha256": normative_bridge_sha256,
        }
    )
    finding["finding_id"] = finding_id

    request = build_practice_claim_binding_request(
        matter_id=request["matter_id"],
        draft_id=request["draft_id"],
        sentence_id=request["sentence_id"],
        section_code=request["section_code"],
        sentence_text=sentence_text,
        claim_id=request["claim_id"],
        practice_claim_id=request["practice_claim_id"],
        issue_option_id=request["issue_option_id"],
        evidence_ids=[finding_id],
        maximum_supported_inference=request["maximum_supported_inference"],
    )
    resolution["practice_binding_sha256"] = request["practice_binding_sha256"]
    resolution["findings"] = [copy.deepcopy(finding)]

    wording_review = resolution["wording_review"]
    wording_review["finding_ids"] = [finding_id]
    wording_review["wording_text"] = sentence_text
    wording_review["wording_sha256"] = _digest(sentence_text)
    wording_review["normative_bridge_sha256"] = normative_bridge_sha256
    _rebind_result_handoff(resolution)

    issue_payload = resolution["issue_candidate"]
    issue_claim = issue_payload["gates"]["practice_claims"][0]
    issue_claim["statement"] = sentence_text
    issue_claim["evidence_ids"] = [finding_id]
    issue = issue_candidate_from_dict(issue_payload)
    approvals = issue_approval_requests(issue)
    practice_key = f"practice:{request['practice_claim_id']}"
    resolution["issue_approval_requests"] = {
        practice_key: approvals[practice_key],
        "selection": approvals["selection"],
    }
    resolution["issue_candidate_fingerprint"] = (
        issue_candidate_content_fingerprint(issue)
    )
    return request, resolution


def _complaint_with_practice(evidence_ids: object) -> tuple[object, StaticAuthority]:
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
    rights_section["sentences"] = [
        {
            "sentence_id": PRACTICE_SENTENCE_ID,
            "text": "В проверенном корпусе наблюдается устойчивый судебный подход.",
            "role": "practice_claim",
            "claim_id": "CLAIM-A",
            "practice_claim_id": "claim-practice",
            "issue_option_id": "ISSUE-A",
            "evidence_ids": evidence_ids,
            "support_status": "verified",
            "maximum_supported_inference": "corroborated_observed_corpus",
        }
    ]
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


def _current_practice_case(
    *, sentence_text: str | None = None
) -> tuple[
    object,
    StaticAuthority,
    StaticPracticeAuthority,
]:
    base_request, resolution = _valid_case()
    if sentence_text is not None:
        base_request, resolution = _retarget_practice_resolution_text(
            base_request, resolution, sentence_text
        )
    request = build_practice_claim_binding_request(
        matter_id="MATTER-1",
        draft_id="DRAFT-1",
        sentence_id=PRACTICE_SENTENCE_ID,
        section_code="rights_analysis",
        sentence_text=base_request["sentence_text"],
        claim_id=base_request["claim_id"],
        practice_claim_id=base_request["practice_claim_id"],
        issue_option_id=base_request["issue_option_id"],
        evidence_ids=base_request["evidence_ids"],
        maximum_supported_inference=base_request["maximum_supported_inference"],
    )
    resolution["practice_binding_sha256"] = request["practice_binding_sha256"]
    resolution["matter_binding"]["matter_id"] = request["matter_id"]
    resolution["matter_binding"]["draft_id"] = request["draft_id"]

    remedy_text = "Признать норму неконституционной"
    payload = _complaint_payload(
        [
            _sentence(
                REMEDY_SENTENCE_ID,
                request["claim_id"],
                request["issue_option_id"],
                "PASSPORT-A",
                "APP-A",
                "E-A",
                remedy_text,
            )
        ],
        issue_option_ids=[request["issue_option_id"]],
        norm_passport_ids=["PASSPORT-A"],
    )
    rights_section = next(
        section for section in payload["sections"] if section["code"] == "rights_analysis"
    )
    rights_section["sentences"] = [
        {
            "sentence_id": request["sentence_id"],
            "text": request["sentence_text"],
            "role": "practice_claim",
            "claim_id": request["claim_id"],
            "practice_claim_id": request["practice_claim_id"],
            "issue_option_id": request["issue_option_id"],
            "evidence_ids": request["evidence_ids"],
            "support_status": "verified",
            "maximum_supported_inference": request["maximum_supported_inference"],
        }
    ]
    complaint = build_structured_complaint(payload)
    relief_authority = StaticAuthority(
        {
            REMEDY_SENTENCE_ID: _resolution(
                request["claim_id"],
                request["issue_option_id"],
                "PASSPORT-A",
                "APP-A",
                "E-A",
                remedy_text,
            )
        }
    )
    index = build_practice_claim_binding_index_resolution(
        matter_id=request["matter_id"],
        draft_id=request["draft_id"],
        bindings=[
            {
                "sentence_id": request["sentence_id"],
                "section_code": request["section_code"],
                "role": "practice_claim",
                "claim_id": request["claim_id"],
                "practice_claim_id": request["practice_claim_id"],
                "issue_option_id": request["issue_option_id"],
                "practice_binding_sha256": request["practice_binding_sha256"],
            }
        ],
        authority_revision_id="practice-authority-revision-1",
        checked_at="2026-09-01T09:53:00Z",
    )
    return complaint, relief_authority, StaticPracticeAuthority(resolution, index)


def _blocked_manifest_with_practice() -> tuple[
    dict[str, object],
    StaticAuthority,
    StaticPracticeAuthority,
]:
    complaint, relief_authority, practice_authority = _current_practice_case()
    receipts = require_release_support(
        complaint,
        relief_binding_authority=relief_authority,
        practice_binding_authority=practice_authority,
        require_practice_index=True,
    )
    manifest: dict[str, object] = {
        "schema_version": "1.3",
        "matter_id": complaint.matter_id,
        "draft_id": complaint.draft_id,
        "status": "blocked",
        "filing_performed": False,
        "human_only_actions": ["signature", "filing"],
        "source_versions": ["SOURCE-1"],
        "norm_passport_ids": list(complaint.norm_passport_ids),
        "issue_option_ids": list(complaint.issue_option_ids),
        "issue_option_id": complaint.issue_option_id,
        "sentence_evidence_map": complaint.sentence_evidence_map(),
        "relief_binding_receipts": list(receipts.relief_binding_receipts),
        "relief_binding_index_receipt": copy.deepcopy(
            receipts.relief_binding_receipts[0]["binding_index_receipt"]
        ),
        "holding_binding_receipts": [],
        "holding_binding_index_receipt": None,
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
    return manifest, relief_authority, practice_authority


class MultiPracticeAuthority:
    def __init__(
        self,
        resolutions: dict[str, dict[str, object]],
        index: dict[str, object],
    ) -> None:
        self.resolutions = resolutions
        self.index = index

    def resolve_practice_claim_evidence_binding(
        self, request: dict[str, object]
    ) -> dict[str, object] | None:
        value = self.resolutions.get(str(request.get("sentence_id") or ""))
        return copy.deepcopy(value)

    def resolve_practice_claim_evidence_binding_index(
        self, request: dict[str, object]
    ) -> dict[str, object]:
        return copy.deepcopy(self.index)


def _multi_practice_case(
    *, second_case_id: str | None = None
) -> tuple[object, StaticAuthority, MultiPracticeAuthority]:
    complaint, relief_authority, practice_authority = _current_practice_case()
    payload = complaint.to_dict()
    rights_section = next(
        section
        for section in payload["sections"]
        if section["code"] == "rights_analysis"
    )
    second = copy.deepcopy(rights_section["sentences"][0])
    second["sentence_id"] = SECOND_PRACTICE_SENTENCE_ID
    rights_section["sentences"].append(second)
    complaint = build_structured_complaint(payload)
    requests = [
        complaint.practice_claim_binding_request(sentence)
        for section in complaint.sections
        for sentence in section.sentences
        if sentence.role == "practice_claim"
    ]
    exact_requests = [request for request in requests if request is not None]
    resolutions: dict[str, dict[str, object]] = {}
    bindings: list[dict[str, object]] = []
    for request in exact_requests:
        resolution = copy.deepcopy(practice_authority.resolution)
        resolution["practice_binding_sha256"] = request[
            "practice_binding_sha256"
        ]
        if (
            request["sentence_id"] == SECOND_PRACTICE_SENTENCE_ID
            and second_case_id is not None
        ):
            resolution["matter_binding"]["case_id"] = second_case_id
            resolution["filing_validation"]["state"]["case_id"] = second_case_id
        resolutions[request["sentence_id"]] = resolution
        bindings.append(
            {
                "sentence_id": request["sentence_id"],
                "section_code": request["section_code"],
                "role": "practice_claim",
                "claim_id": request["claim_id"],
                "practice_claim_id": request["practice_claim_id"],
                "issue_option_id": request["issue_option_id"],
                "practice_binding_sha256": request[
                    "practice_binding_sha256"
                ],
            }
        )
    index = build_practice_claim_binding_index_resolution(
        matter_id=complaint.matter_id,
        draft_id=complaint.draft_id,
        bindings=bindings,
        authority_revision_id="practice-authority-revision-1",
        checked_at="2026-09-01T09:55:00Z",
    )
    return complaint, relief_authority, MultiPracticeAuthority(resolutions, index)


def _blocked_manifest_for(
    complaint: object,
    relief_authority: StaticAuthority,
    practice_authority: object,
) -> dict[str, object]:
    receipts = require_release_support(
        complaint,
        relief_binding_authority=relief_authority,
        practice_binding_authority=practice_authority,
        require_practice_index=True,
    )
    manifest: dict[str, object] = {
        "schema_version": "1.3",
        "matter_id": complaint.matter_id,
        "draft_id": complaint.draft_id,
        "status": "blocked",
        "filing_performed": False,
        "human_only_actions": ["signature", "filing"],
        "source_versions": ["SOURCE-1"],
        "norm_passport_ids": list(complaint.norm_passport_ids),
        "issue_option_ids": list(complaint.issue_option_ids),
        "issue_option_id": complaint.issue_option_id,
        "sentence_evidence_map": complaint.sentence_evidence_map(),
        "relief_binding_receipts": list(receipts.relief_binding_receipts),
        "relief_binding_index_receipt": copy.deepcopy(
            receipts.relief_binding_receipts[0]["binding_index_receipt"]
        ),
        "holding_binding_receipts": [],
        "holding_binding_index_receipt": None,
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


class PracticeClaimEvidenceBindingRedTests(unittest.TestCase):
    def test_verified_looking_fictional_finding_requires_host_authority(self) -> None:
        complaint, relief = _complaint_with_practice([FICTIONAL_FINDING_ID])

        with self.assertRaisesRegex(
            ComplaintModelError, "practice_binding_authority_required"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=relief,
            )

    def test_practice_finding_ids_are_not_string_coerced(self) -> None:
        with self.assertRaisesRegex(ComplaintModelError, "evidence_ids.*списком"):
            _complaint_with_practice("FAKE")

    def test_current_host_projection_and_complete_index_emit_receipts(self) -> None:
        complaint, relief_authority, practice_authority = _current_practice_case()

        receipts = require_release_support(
            complaint,
            relief_binding_authority=relief_authority,
            practice_binding_authority=practice_authority,
            require_practice_index=True,
        )

        self.assertEqual(len(receipts.practice_binding_receipts), 1)
        self.assertEqual(
            receipts.practice_binding_receipts[0]["sentence_id"],
            PRACTICE_SENTENCE_ID,
        )
        self.assertEqual(
            receipts.practice_binding_index_receipt["bindings"][0]["role"],
            "practice_claim",
        )

    def test_claim_receipts_and_index_require_one_authority_snapshot(self) -> None:
        complaint, relief_authority, practice_authority = _current_practice_case()
        practice_authority.index["authority_revision_id"] = (
            "different-practice-authority-revision"
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "practice_binding_authority_snapshot_mismatch"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=relief_authority,
                practice_binding_authority=practice_authority,
                require_practice_index=True,
            )

    def test_multiple_practice_receipts_reject_mixed_case_snapshot(self) -> None:
        complaint, relief_authority, practice_authority = _multi_practice_case(
            second_case_id="case-2"
        )

        with self.assertRaisesRegex(
            ComplaintModelError, "practice_binding_authority_snapshot_mismatch"
        ):
            require_release_support(
                complaint,
                relief_binding_authority=relief_authority,
                practice_binding_authority=practice_authority,
                require_practice_index=True,
            )

    def test_manifest_replay_rejects_mixed_case_snapshot(self) -> None:
        mutations = {
            "matter_id": "MATTER-2",
            "draft_id": "DRAFT-2",
            "case_id": "case-2",
            "workspace_revision_id": "workspace-revision-2",
            "input_bindings_sha256": "8" * 64,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                complaint, relief_authority, practice_authority = (
                    _multi_practice_case()
                )
                manifest = _blocked_manifest_for(
                    complaint, relief_authority, practice_authority
                )
                second_receipt = next(
                    receipt
                    for receipt in manifest["practice_binding_receipts"]
                    if receipt["sentence_id"] == SECOND_PRACTICE_SENTENCE_ID
                )
                second_receipt["matter_binding"][field] = value

                errors = _manifest_practice_binding_projection_errors(manifest)

                self.assertIn(
                    "practice_binding_authority_snapshot_mismatch", errors
                )

    def test_multiline_practice_sentence_text_is_preserved_exactly(self) -> None:
        multiline_text = (
            "В раскрытом корпусе наблюдается проверенный судебный подход.\n"
            "Он ограничен раскрытым проверенным корпусом."
        )
        rebuilt, relief_authority, practice_authority = _current_practice_case(
            sentence_text=multiline_text
        )
        practice_sentence = next(
            sentence
            for section in rebuilt.sections
            for sentence in section.sentences
            if sentence.role == "practice_claim"
        )
        request = rebuilt.practice_claim_binding_request(practice_sentence)

        self.assertEqual(practice_sentence.text, multiline_text)
        self.assertEqual(request["sentence_text"], multiline_text)

        manifest = _blocked_manifest_for(
            rebuilt, relief_authority, practice_authority
        )
        projection_errors = _manifest_practice_binding_projection_errors(manifest)
        self.assertEqual(projection_errors, [])

    def test_multiple_practice_sentences_require_complete_exact_index(self) -> None:
        complaint, relief_authority, practice_authority = _current_practice_case()
        payload = complaint.to_dict()
        rights_section = next(
            section
            for section in payload["sections"]
            if section["code"] == "rights_analysis"
        )
        second = copy.deepcopy(rights_section["sentences"][0])
        second["sentence_id"] = SECOND_PRACTICE_SENTENCE_ID
        rights_section["sentences"].append(second)
        complaint = build_structured_complaint(payload)
        requests = [
            complaint.practice_claim_binding_request(sentence)
            for section in complaint.sections
            for sentence in section.sentences
            if sentence.role == "practice_claim"
        ]
        self.assertTrue(all(request is not None for request in requests))
        exact_requests = [request for request in requests if request is not None]
        resolutions: dict[str, dict[str, object]] = {}
        bindings: list[dict[str, object]] = []
        for request in exact_requests:
            resolution = copy.deepcopy(practice_authority.resolution)
            resolution["practice_binding_sha256"] = request[
                "practice_binding_sha256"
            ]
            resolutions[request["sentence_id"]] = resolution
            bindings.append(
                {
                    "sentence_id": request["sentence_id"],
                    "section_code": request["section_code"],
                    "role": "practice_claim",
                    "claim_id": request["claim_id"],
                    "practice_claim_id": request["practice_claim_id"],
                    "issue_option_id": request["issue_option_id"],
                    "practice_binding_sha256": request[
                        "practice_binding_sha256"
                    ],
                }
            )
        index = build_practice_claim_binding_index_resolution(
            matter_id=complaint.matter_id,
            draft_id=complaint.draft_id,
            bindings=bindings,
            authority_revision_id="practice-authority-revision-1",
            checked_at="2026-09-01T09:55:00Z",
        )
        authority = MultiPracticeAuthority(resolutions, index)

        receipts = require_release_support(
            complaint,
            relief_binding_authority=relief_authority,
            practice_binding_authority=authority,
            require_practice_index=True,
        )

        self.assertEqual(len(receipts.practice_binding_receipts), 2)
        self.assertEqual(
            [
                item["sentence_id"]
                for item in receipts.practice_binding_index_receipt["bindings"]
            ],
            sorted([PRACTICE_SENTENCE_ID, SECOND_PRACTICE_SENTENCE_ID]),
        )

    def test_release_verify_reopens_current_practice_authority(self) -> None:
        cases = {
            "authority_revision": ("checked_at", "2026-09-01T10:00:00Z"),
            "source_file": ("source_file_sha256", "8" * 64),
            "attachment": ("attachment_event_sha256", "8" * 64),
            "trust_anchor": ("trust_anchor_sha256", "8" * 64),
        }
        for label, (field, value) in cases.items():
            with self.subTest(case=label):
                manifest, relief_authority, practice_authority = (
                    _blocked_manifest_with_practice()
                )
                baseline = verify_release_manifest(
                    manifest,
                    relief_binding_authority=relief_authority,
                    practice_binding_authority=practice_authority,
                )
                self.assertFalse(
                    any(
                        error.startswith("practice_binding")
                        for error in baseline
                    ),
                    baseline,
                )

                if field == "checked_at":
                    practice_authority.resolution[field] = value
                else:
                    practice_authority.resolution["practice_state"][field] = value
                    practice_authority.resolution["ready_binding"][field] = value
                stale = verify_release_manifest(
                    manifest,
                    relief_binding_authority=relief_authority,
                    practice_binding_authority=practice_authority,
                )

                if field == "checked_at":
                    self.assertIn(
                        f"practice_binding_receipt_stale:{PRACTICE_SENTENCE_ID}",
                        stale,
                    )
                else:
                    self.assertTrue(
                        any(
                            error.startswith(
                                f"practice_binding:{PRACTICE_SENTENCE_ID}:"
                            )
                            for error in stale
                        ),
                        stale,
                    )

    def test_release_manifest_detects_role_downgrade_and_index_deletion(self) -> None:
        manifest, relief_authority, practice_authority = (
            _blocked_manifest_with_practice()
        )
        practice_entry = next(
            entry
            for entry in manifest["sentence_evidence_map"]
            if entry["sentence_id"] == PRACTICE_SENTENCE_ID
        )
        practice_entry["role"] = "narrative"
        stored_index = manifest["practice_binding_index_receipt"]
        stored_index["bindings"] = []
        index_basis = {
            "schema_version": "1.0.0",
            "matter_id": manifest["matter_id"],
            "draft_id": manifest["draft_id"],
            "bindings": [],
        }
        stored_index["binding_index_sha256"] = sha256(
            canonical_json_bytes(index_basis)
        ).hexdigest()
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest,
            relief_binding_authority=relief_authority,
            practice_binding_authority=practice_authority,
        )

        self.assertIn(
            f"practice_binding_receipt_orphan:{PRACTICE_SENTENCE_ID}", errors
        )
        self.assertIn("practice_binding_index_set_mismatch", errors)

    def test_release_manifest_rejects_cross_snapshot_index_replay(self) -> None:
        manifest, relief_authority, practice_authority = (
            _blocked_manifest_with_practice()
        )
        manifest["practice_binding_index_receipt"]["authority_revision_id"] = (
            "replayed-index-revision"
        )
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        errors = verify_release_manifest(
            manifest,
            relief_binding_authority=relief_authority,
            practice_binding_authority=practice_authority,
        )

        self.assertIn("practice_binding_authority_snapshot_mismatch", errors)

    def test_filing_schema_accepts_exact_practice_receipt_and_index(self) -> None:
        manifest, _relief_authority, _practice_authority = (
            _blocked_manifest_with_practice()
        )
        manifest["status"] = "ready_for_expert_review"
        holding_index = build_holding_binding_index_resolution(
            matter_id=manifest["matter_id"],
            draft_id=manifest["draft_id"],
            bindings=[],
            authority_revision_id="holding-index-revision-1",
            checked_at="2026-09-01T09:54:00Z",
        )
        holding_index.pop("status")
        manifest["holding_binding_index_receipt"] = holding_index
        manifest["schema_version"] = "1.4"
        role_bindings = [
            sentence_role_binding(
                ordinal=ordinal,
                sentence_id=entry["sentence_id"],
                section_code=entry["section_code"],
                text=entry["text"],
                role=entry["role"],
            )
            for ordinal, entry in enumerate(
                manifest["sentence_evidence_map"], start=1
            )
        ]
        role_index = build_sentence_role_index_resolution(
            matter_id=manifest["matter_id"],
            draft_id=manifest["draft_id"],
            bindings=role_bindings,
            authority_revision_id="sentence-role-index-revision-1",
            checked_at="2026-09-01T09:54:00Z",
        )
        role_index.pop("status")
        manifest["sentence_role_index_receipt"] = role_index
        schema = json.loads(FILING_SCHEMA_PATH.read_text(encoding="utf-8"))

        errors = list(Draft202012Validator(schema).iter_errors(manifest))

        self.assertEqual(errors, [])

    def test_ready_manifest_rejects_nonempty_blockers_in_runtime_and_schema(self) -> None:
        manifest, relief_authority, practice_authority = (
            _blocked_manifest_with_practice()
        )
        manifest["status"] = "ready_for_expert_review"
        manifest["blockers"] = ["unresolved_release_blocker"]
        holding_index = build_holding_binding_index_resolution(
            matter_id=manifest["matter_id"],
            draft_id=manifest["draft_id"],
            bindings=[],
            authority_revision_id="holding-index-revision-1",
            checked_at="2026-09-01T09:54:00Z",
        )
        holding_index.pop("status")
        manifest["holding_binding_index_receipt"] = holding_index
        manifest["release_basis_sha256"] = release_basis_sha256(manifest)

        runtime_errors = verify_release_manifest(
            manifest,
            relief_binding_authority=relief_authority,
            practice_binding_authority=practice_authority,
        )
        schema = json.loads(FILING_SCHEMA_PATH.read_text(encoding="utf-8"))
        schema_errors = list(Draft202012Validator(schema).iter_errors(manifest))

        self.assertIn("ready_manifest_has_blockers", runtime_errors)
        self.assertTrue(
            any(list(error.path) == ["blockers"] for error in schema_errors),
            schema_errors,
        )


if __name__ == "__main__":
    unittest.main()
