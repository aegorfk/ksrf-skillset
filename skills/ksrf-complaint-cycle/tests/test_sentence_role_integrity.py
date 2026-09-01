# pyright: reportMissingImports=false, reportMissingModuleSource=false
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from jsonschema import Draft202012Validator


SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = SKILL_ROOT / "lib"
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))

from ksrf.filing.composer import (  # noqa: E402
    ComplaintModelError,
    REQUIRED_SECTION_CODES,
    build_structured_complaint,
    require_release_support,
)
from ksrf.filing.application_binding import (  # noqa: E402
    build_application_finding_binding_index_resolution,
)
from ksrf.filing.sentence_roles import (  # noqa: E402
    CANONICAL_SENTENCE_ROLES,
    build_sentence_role_index_resolution,
    resolve_sentence_role_index,
    sentence_role_binding,
    validate_sentence_role_index_receipt,
)
from ksrf.filing.release import (  # noqa: E402
    _manifest_sentence_role_authority_errors,
    _manifest_sentence_role_projection_errors,
    build_release_pack,
    release_basis_sha256,
)
from ksrf.filing.workflow import WorkflowRouter  # noqa: E402


def _complaint_payload(sentence: dict[str, Any] | str | None) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    for code in REQUIRED_SECTION_CODES:
        sentences: list[dict[str, Any] | str] = []
        if code == "facts" and sentence is not None:
            sentences.append(copy.deepcopy(sentence))
        sections.append(
            {
                "code": code,
                "heading": f"Раздел {code}",
                "sentences": sentences,
            }
        )
    return {
        "matter_id": "MATTER-ROLE-1",
        "draft_id": "DRAFT-ROLE-1",
        "title": "Жалоба",
        "sections": sections,
        "norm_passport_ids": [],
        "issue_option_ids": [],
    }


class StaticRoleAuthority:
    def __init__(self, resolution: Any) -> None:
        self.resolution = resolution
        self.requests: list[dict[str, Any]] = []

    def resolve_sentence_role_index(
        self, request: dict[str, Any]
    ) -> Any:
        self.requests.append(copy.deepcopy(request))
        return copy.deepcopy(self.resolution)


class MutatingRequestAuthority(StaticRoleAuthority):
    def resolve_sentence_role_index(
        self, request: dict[str, Any]
    ) -> Any:
        request["draft_id"] = "MUTATED-DRAFT"
        return copy.deepcopy(self.resolution)


class MappingRoleAuthority(StaticRoleAuthority):
    def resolve_sentence_role_index(
        self, request: dict[str, Any]
    ) -> Any:
        self.requests.append(copy.deepcopy(request))
        return MappingProxyType(copy.deepcopy(dict(self.resolution)))


class SentenceRoleIntegrityTests(unittest.TestCase):
    def _receipt_for(
        self, bindings: list[dict[str, Any]], *, revision: str = "draft-revision-7"
    ) -> dict[str, Any]:
        resolution = build_sentence_role_index_resolution(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            bindings=bindings,
            authority_revision_id=revision,
            checked_at="2026-09-01T10:15:00+03:00",
        )
        errors, receipt = resolve_sentence_role_index(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            expected_bindings=bindings,
            authority=StaticRoleAuthority(resolution),
        )
        self.assertEqual(errors, ())
        assert receipt is not None
        return receipt

    def test_explicit_unknown_role_is_never_release_supported(self) -> None:
        complaint = build_structured_complaint(
            _complaint_payload(
                {
                    "text": "Суды установили факт выплаты.",
                    "role": "application_findng",
                    "evidence_ids": ["CALLER-LABEL"],
                    "support_status": "human_approved",
                }
            )
        )

        sentence = next(
            section.sentences[0]
            for section in complaint.sections
            if section.code == "facts"
        )
        self.assertEqual(sentence.role, "application_findng")
        self.assertFalse(sentence.release_supported)
        self.assertEqual(complaint.unsupported_sentences(), [sentence])
        with self.assertRaisesRegex(
            ComplaintModelError,
            rf"sentence_role_unknown:{sentence.sentence_id}:application_findng",
        ) as captured:
            require_release_support(complaint)
        self.assertIn(
            f"sentence_role_unknown:{sentence.sentence_id}:application_findng",
            captured.exception.reason_codes,
        )

    def test_padded_role_is_preserved_as_unknown_without_aliasing(self) -> None:
        for padded_role in (" fact ", " narrative "):
            with self.subTest(role=padded_role):
                complaint = build_structured_complaint(
                    _complaint_payload(
                        {
                            "text": "Суды установили факт выплаты.",
                            "role": padded_role,
                        }
                    )
                )
                sentence = next(
                    section.sentences[0]
                    for section in complaint.sections
                    if section.code == "facts"
                )

                self.assertEqual(sentence.role, padded_role)
                self.assertFalse(sentence.release_supported)
                with self.assertRaisesRegex(
                    ComplaintModelError, "sentence_role_unknown"
                ):
                    require_release_support(complaint)

    def test_missing_role_and_raw_legacy_sentence_remain_narrative(self) -> None:
        for legacy in (
            {"text": "Нейтральная связка без правового утверждения."},
            "Нейтральная связка без правового утверждения.",
        ):
            with self.subTest(legacy=legacy):
                complaint = build_structured_complaint(_complaint_payload(legacy))
                sentence = next(
                    section.sentences[0]
                    for section in complaint.sections
                    if section.code == "facts"
                )
                self.assertEqual(sentence.role, "narrative")
                self.assertTrue(sentence.release_supported)

    def test_explicit_non_string_or_blank_role_is_rejected(self) -> None:
        for value in (None, False, 0, [], {}, "", " \t "):
            with self.subTest(value=value), self.assertRaisesRegex(
                ComplaintModelError, "sentence_role_(?:type|blank)_invalid:facts:1"
            ):
                build_structured_complaint(
                    _complaint_payload(
                        {
                            "text": "Строка с явно недопустимой ролью.",
                            "role": value,
                        }
                    )
                )

    def test_unknown_role_in_requested_remedy_is_preserved_and_blocked(self) -> None:
        payload = _complaint_payload(None)
        remedy = next(
            section
            for section in payload["sections"]
            if section["code"] == "requested_remedy"
        )
        remedy["sentences"] = [
            {
                "text": "Признать норму неконституционной.",
                "role": "practice_cliam",
                "application_record_ids": ["APP-1"],
            }
        ]

        complaint = build_structured_complaint(payload)
        sentence = next(
            section.sentences[0]
            for section in complaint.sections
            if section.code == "requested_remedy"
        )

        self.assertEqual(sentence.role, "practice_cliam")
        self.assertEqual(sentence.application_record_ids, ("APP-1",))
        self.assertEqual(
            complaint.to_dict()["sentence_evidence_map"][0][
                "application_record_ids"
            ],
            ["APP-1"],
        )
        schema = json.loads(
            (
                SKILL_ROOT
                / "schemas"
                / "ksrf_filing"
                / "structured-complaint.schema.json"
            ).read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(schema)
        self.assertEqual(list(validator.iter_errors(complaint.to_dict())), [])
        blank = complaint.to_dict()
        blank["sentence_evidence_map"][0]["role"] = "   "
        self.assertTrue(list(validator.iter_errors(blank)))
        with self.assertRaisesRegex(
            ComplaintModelError,
            rf"sentence_role_unknown:{sentence.sentence_id}:practice_cliam",
        ):
            require_release_support(complaint)

    def test_complete_role_index_accepts_exact_host_registry(self) -> None:
        binding = sentence_role_binding(
            ordinal=1,
            sentence_id="sent-0123456789abcdef",
            section_code="facts",
            text="Суды установили факт выплаты.",
            role="application_finding",
        )
        resolution = build_sentence_role_index_resolution(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            bindings=[binding],
            authority_revision_id="draft-revision-7",
            checked_at="2026-09-01T10:15:00+03:00",
        )
        authority = StaticRoleAuthority(resolution)

        errors, receipt = resolve_sentence_role_index(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            expected_bindings=[binding],
            authority=authority,
        )

        self.assertEqual(errors, ())
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(
            validate_sentence_role_index_receipt(
                MappingProxyType(receipt),
                matter_id="MATTER-ROLE-1",
                draft_id="DRAFT-ROLE-1",
                expected_bindings=[binding],
            ),
            (),
        )
        assert receipt is not None
        self.assertEqual(receipt["bindings"], [binding])
        self.assertEqual(
            authority.requests,
            [
                {
                    "schema_version": "1.0.0",
                    "matter_id": "MATTER-ROLE-1",
                    "draft_id": "DRAFT-ROLE-1",
                }
            ],
        )

    def test_role_index_preserves_legacy_non_ascii_or_hyphenated_section_code(
        self,
    ) -> None:
        payload = _complaint_payload(None)
        payload["sections"].append(
            {
                "code": "legal-analysis",
                "heading": "Дополнительный анализ",
                "sentences": [
                    {
                        "text": "Дополнительная нейтральная строка.",
                        "role": "narrative",
                    }
                ],
            }
        )

        complaint = build_structured_complaint(payload)
        bindings = complaint.sentence_role_index_bindings()

        self.assertEqual(len(bindings), 1)
        self.assertEqual(bindings[0]["section_code"], "legal-analysis")

    def test_mapping_authority_and_receipt_are_accepted_per_protocol(self) -> None:
        binding = sentence_role_binding(
            ordinal=1,
            sentence_id="sent-0123456789abcdef",
            section_code="facts",
            text="Суды установили факт выплаты.",
            role="application_finding",
        )
        resolution = build_sentence_role_index_resolution(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            bindings=[binding],
            authority_revision_id="draft-revision-7",
            checked_at="2026-09-01T10:15:00+03:00",
        )

        errors, receipt = resolve_sentence_role_index(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            expected_bindings=[binding],
            authority=MappingRoleAuthority(resolution),
        )

        self.assertEqual(errors, ())
        self.assertIsNotNone(receipt)

    def test_narrative_downgrade_fails_complete_role_index(self) -> None:
        authoritative = sentence_role_binding(
            ordinal=1,
            sentence_id="sent-0123456789abcdef",
            section_code="facts",
            text="Суды установили факт выплаты.",
            role="application_finding",
        )
        downgraded = sentence_role_binding(
            ordinal=1,
            sentence_id="sent-0123456789abcdef",
            section_code="facts",
            text="Суды установили факт выплаты.",
            role="narrative",
        )
        authority = StaticRoleAuthority(
            build_sentence_role_index_resolution(
                matter_id="MATTER-ROLE-1",
                draft_id="DRAFT-ROLE-1",
                bindings=[authoritative],
                authority_revision_id="draft-revision-7",
                checked_at="2026-09-01T10:15:00+03:00",
            )
        )

        errors, receipt = resolve_sentence_role_index(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            expected_bindings=[downgraded],
            authority=authority,
        )

        self.assertIn("sentence_role_index_set_mismatch", errors)
        self.assertIsNone(receipt)

    def test_sentence_reordering_fails_complete_role_index(self) -> None:
        first = sentence_role_binding(
            ordinal=1,
            sentence_id="sent-0123456789abcdef",
            section_code="facts",
            text="Первая строка.",
            role="fact",
        )
        second = sentence_role_binding(
            ordinal=2,
            sentence_id="sent-fedcba9876543210",
            section_code="facts",
            text="Вторая строка.",
            role="court_reasoning",
        )
        authority = StaticRoleAuthority(
            build_sentence_role_index_resolution(
                matter_id="MATTER-ROLE-1",
                draft_id="DRAFT-ROLE-1",
                bindings=[first, second],
                authority_revision_id="draft-revision-7",
                checked_at="2026-09-01T10:15:00+03:00",
            )
        )

        reordered_first = sentence_role_binding(
            ordinal=1,
            sentence_id=second["sentence_id"],
            section_code=second["section_code"],
            text="Вторая строка.",
            role=second["role"],
        )
        reordered_second = sentence_role_binding(
            ordinal=2,
            sentence_id=first["sentence_id"],
            section_code=first["section_code"],
            text="Первая строка.",
            role=first["role"],
        )

        errors, receipt = resolve_sentence_role_index(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            expected_bindings=[reordered_first, reordered_second],
            authority=authority,
        )

        self.assertIn("sentence_role_index_set_mismatch", errors)
        self.assertIsNone(receipt)

    def test_unknown_host_role_is_rejected_without_aliasing(self) -> None:
        with self.assertRaisesRegex(ValueError, "sentence_role_index_role_unknown"):
            build_sentence_role_index_resolution(
                matter_id="MATTER-ROLE-1",
                draft_id="DRAFT-ROLE-1",
                bindings=[
                    {
                        "ordinal": 1,
                        "sentence_id": "sent-0123456789abcdef",
                        "section_code": "facts",
                        "text_sha256": "0" * 64,
                        "role": "factual_claim",
                    }
                ],
                authority_revision_id="draft-revision-7",
                checked_at="2026-09-01T10:15:00+03:00",
            )

    def test_every_canonical_role_builds_an_exact_binding(self) -> None:
        for ordinal, role in enumerate(sorted(CANONICAL_SENTENCE_ROLES), start=1):
            with self.subTest(role=role):
                binding = sentence_role_binding(
                    ordinal=1,
                    sentence_id=f"sent-{ordinal:016x}",
                    section_code="facts",
                    text=f"Строка роли {role}.",
                    role=role,
                )
                self.assertEqual(binding["role"], role)
                self.assertEqual(len(binding["text_sha256"]), 64)

    def test_authority_request_mutation_and_malformed_response_fail_closed(self) -> None:
        binding = sentence_role_binding(
            ordinal=1,
            sentence_id="sent-0123456789abcdef",
            section_code="facts",
            text="Суды установили факт выплаты.",
            role="application_finding",
        )
        resolution = build_sentence_role_index_resolution(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            bindings=[binding],
            authority_revision_id="draft-revision-7",
            checked_at="2026-09-01T10:15:00+03:00",
        )
        errors, receipt = resolve_sentence_role_index(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            expected_bindings=[binding],
            authority=MutatingRequestAuthority(resolution),
        )
        self.assertEqual(errors, ("sentence_role_index_request_mutated",))
        self.assertIsNone(receipt)

        errors, receipt = resolve_sentence_role_index(
            matter_id="MATTER-ROLE-1",
            draft_id="DRAFT-ROLE-1",
            expected_bindings=[binding],
            authority=StaticRoleAuthority({"schema_version": "1.0.0"}),
        )
        self.assertIn(
            "sentence_role_index_resolution_field_missing:bindings", errors
        )
        self.assertIsNone(receipt)

    def test_required_complete_index_fails_closed_without_authority(self) -> None:
        complaint = build_structured_complaint(_complaint_payload(None))
        with self.assertRaisesRegex(
            ComplaintModelError, "sentence_role_index_authority_required"
        ):
            require_release_support(
                complaint,
                require_sentence_role_index=True,
            )

    def test_blocked_diagnostic_preserves_unknown_role_with_blocker(self) -> None:
        blocker = "sentence_role_unknown:sent-0123456789abcdef:practice_cliam"
        manifest = {
            "matter_id": "MATTER-ROLE-1",
            "draft_id": "DRAFT-ROLE-1",
            "status": "blocked",
            "blockers": [blocker],
            "sentence_evidence_map": [
                {
                    "sentence_id": "sent-0123456789abcdef",
                    "section_code": "authorities",
                    "text": "Судебная практика единообразна.",
                    "role": "practice_cliam",
                }
            ],
            "sentence_role_index_receipt": None,
        }

        self.assertEqual(_manifest_sentence_role_projection_errors(manifest), [])

        mismatched = copy.deepcopy(manifest)
        mismatched["blockers"] = [blocker + "_EXTRA"]
        self.assertIn(
            "sentence_role_unknown_blocker_missing:"
            "sent-0123456789abcdef:practice_cliam",
            _manifest_sentence_role_projection_errors(mismatched),
        )

    def test_release_pack_emits_exact_machine_blocker_for_unknown_role(self) -> None:
        complaint = build_structured_complaint(
            _complaint_payload(
                {
                    "text": "Судебная практика единообразна.",
                    "role": "practice_cliam",
                }
            )
        )
        sentence = next(
            section.sentences[0]
            for section in complaint.sections
            if section.code == "facts"
        )
        blocker = f"sentence_role_unknown:{sentence.sentence_id}:practice_cliam"

        with tempfile.TemporaryDirectory() as output_dir:
            manifest = build_release_pack(complaint, output_dir)

        self.assertIn(blocker, manifest["blockers"])
        self.assertNotIn(
            f"sentence_role_unknown_blocker_missing:{sentence.sentence_id}:practice_cliam",
            _manifest_sentence_role_projection_errors(manifest),
        )

    def test_ready_manifest_rejects_unknown_role_even_with_blocker(self) -> None:
        blocker = "sentence_role_unknown:sent-0123456789abcdef:practice_cliam"
        manifest = {
            "matter_id": "MATTER-ROLE-1",
            "draft_id": "DRAFT-ROLE-1",
            "status": "ready_for_expert_review",
            "blockers": [f"Нарушена целостность предложений: {blocker}"],
            "sentence_evidence_map": [
                {
                    "sentence_id": "sent-0123456789abcdef",
                    "section_code": "authorities",
                    "text": "Судебная практика единообразна.",
                    "role": "practice_cliam",
                }
            ],
            "sentence_role_index_receipt": None,
        }

        errors = _manifest_sentence_role_projection_errors(manifest)
        self.assertIn(blocker, errors)
        self.assertIn("sentence_role_index_receipt_missing", errors)

    def test_manifest_authority_detects_role_text_section_and_set_mutation(self) -> None:
        text = "Суды установили факт выплаты."
        sentence_id = "sent-0123456789abcdef"
        authoritative = sentence_role_binding(
            ordinal=1,
            sentence_id=sentence_id,
            section_code="facts",
            text=text,
            role="application_finding",
        )
        authority = StaticRoleAuthority(
            build_sentence_role_index_resolution(
                matter_id="MATTER-ROLE-1",
                draft_id="DRAFT-ROLE-1",
                bindings=[authoritative],
                authority_revision_id="draft-revision-7",
                checked_at="2026-09-01T10:15:00+03:00",
            )
        )
        mutations = (
            ("narrative", "facts", text),
            ("application_finding", "authorities", text),
            ("application_finding", "facts", text + " Изменено."),
        )
        for role, section_code, candidate_text in mutations:
            with self.subTest(role=role, section_code=section_code, text=candidate_text):
                local = sentence_role_binding(
                    ordinal=1,
                    sentence_id=sentence_id,
                    section_code=section_code,
                    text=candidate_text,
                    role=role,
                )
                manifest = {
                    "matter_id": "MATTER-ROLE-1",
                    "draft_id": "DRAFT-ROLE-1",
                    "status": "ready_for_expert_review",
                    "blockers": [],
                    "sentence_evidence_map": [
                        {
                            "sentence_id": sentence_id,
                            "section_code": section_code,
                            "text": candidate_text,
                            "role": role,
                        }
                    ],
                    "sentence_role_index_receipt": self._receipt_for([local]),
                }
                errors = _manifest_sentence_role_authority_errors(
                    manifest, authority
                )
                self.assertIn("sentence_role_index_set_mismatch", errors)

    def test_manifest_authority_detects_deleted_or_inserted_sentence(self) -> None:
        authoritative = sentence_role_binding(
            ordinal=1,
            sentence_id="sent-0123456789abcdef",
            section_code="facts",
            text="Суды установили факт выплаты.",
            role="application_finding",
        )
        authority = StaticRoleAuthority(
            build_sentence_role_index_resolution(
                matter_id="MATTER-ROLE-1",
                draft_id="DRAFT-ROLE-1",
                bindings=[authoritative],
                authority_revision_id="draft-revision-7",
                checked_at="2026-09-01T10:15:00+03:00",
            )
        )
        inserted = sentence_role_binding(
            ordinal=2,
            sentence_id="sent-fedcba9876543210",
            section_code="facts",
            text="Добавленная строка.",
            role="narrative",
        )
        for local_bindings in ([], [authoritative, inserted]):
            with self.subTest(count=len(local_bindings)):
                manifest = {
                    "matter_id": "MATTER-ROLE-1",
                    "draft_id": "DRAFT-ROLE-1",
                    "status": "ready_for_expert_review",
                    "blockers": [],
                    "sentence_evidence_map": [
                        {
                            "sentence_id": item["sentence_id"],
                            "section_code": item["section_code"],
                            "text": (
                                "Суды установили факт выплаты."
                                if item["sentence_id"] == authoritative["sentence_id"]
                                else "Добавленная строка."
                            ),
                            "role": item["role"],
                        }
                        for item in local_bindings
                    ],
                    "sentence_role_index_receipt": self._receipt_for(local_bindings),
                }
                errors = _manifest_sentence_role_authority_errors(
                    manifest, authority
                )
                self.assertIn("sentence_role_index_set_mismatch", errors)

    def test_manifest_authority_detects_stale_receipt_revision(self) -> None:
        text = "Суды установили факт выплаты."
        binding = sentence_role_binding(
            ordinal=1,
            sentence_id="sent-0123456789abcdef",
            section_code="facts",
            text=text,
            role="application_finding",
        )
        manifest = {
            "matter_id": "MATTER-ROLE-1",
            "draft_id": "DRAFT-ROLE-1",
            "status": "ready_for_expert_review",
            "blockers": [],
            "sentence_evidence_map": [
                {
                    "sentence_id": binding["sentence_id"],
                    "section_code": binding["section_code"],
                    "text": text,
                    "role": binding["role"],
                }
            ],
            "sentence_role_index_receipt": self._receipt_for(
                [binding], revision="draft-revision-7"
            ),
        }
        current = StaticRoleAuthority(
            build_sentence_role_index_resolution(
                matter_id="MATTER-ROLE-1",
                draft_id="DRAFT-ROLE-1",
                bindings=[binding],
                authority_revision_id="draft-revision-8",
                checked_at="2026-09-01T10:16:00+03:00",
            )
        )

        errors = _manifest_sentence_role_authority_errors(manifest, current)

        self.assertIn("sentence_role_index_receipt_stale", errors)

    def test_unchanged_revision_requires_stable_snapshot_time(self) -> None:
        text = "Суды установили факт выплаты."
        binding = sentence_role_binding(
            ordinal=1,
            sentence_id="sent-0123456789abcdef",
            section_code="facts",
            text=text,
            role="application_finding",
        )
        receipt = self._receipt_for([binding])
        manifest = {
            "matter_id": "MATTER-ROLE-1",
            "draft_id": "DRAFT-ROLE-1",
            "status": "ready_for_expert_review",
            "blockers": [],
            "sentence_evidence_map": [
                {
                    "sentence_id": binding["sentence_id"],
                    "section_code": binding["section_code"],
                    "text": text,
                    "role": binding["role"],
                }
            ],
            "sentence_role_index_receipt": receipt,
        }
        current = StaticRoleAuthority(
            build_sentence_role_index_resolution(
                matter_id="MATTER-ROLE-1",
                draft_id="DRAFT-ROLE-1",
                bindings=[binding],
                authority_revision_id=receipt["authority_revision_id"],
                checked_at="2026-09-01T10:16:00+03:00",
            )
        )

        errors = _manifest_sentence_role_authority_errors(manifest, current)

        self.assertIn("sentence_role_index_receipt_stale", errors)

    def test_render_status_revalidates_stored_role_receipt(self) -> None:
        application_index_receipt = (
            build_application_finding_binding_index_resolution(
                matter_id="MATTER-ROLE-1",
                draft_id="DRAFT-ROLE-1",
                bindings=[],
                authority_revision_id="application-draft-revision-1",
                checked_at="2026-09-01T12:00:00Z",
            )
        )
        stored_receipt = {
            "schema_version": "1.0.0",
            "authority_revision_id": "draft-revision-7",
        }
        latest = {
            "state": "ready_for_expert_review",
            "result": {
                "sentence_role_index_receipt": stored_receipt,
                "application_binding_receipts": [],
                "application_binding_index_receipt": application_index_receipt,
            },
        }
        current_receipt = {
            "schema_version": "1.0.0",
            "authority_revision_id": "draft-revision-8",
        }
        router = object.__new__(WorkflowRouter)
        router.relief_binding_authority = None
        router.holding_binding_authority = None
        router.practice_binding_authority = None
        router.sentence_role_authority = None
        router._latest_operation = lambda route: (  # type: ignore[method-assign]
            copy.deepcopy(latest),
            {"complaint": {}},
        )

        with patch(
            "ksrf.filing.composer.build_structured_complaint",
            return_value=object(),
        ), patch(
            "ksrf.filing.composer.require_release_support",
            return_value=SimpleNamespace(
                sentence_role_index_receipt=current_receipt,
                application_binding_receipts=(),
                application_binding_index_receipt=copy.deepcopy(
                    application_index_receipt
                ),
            ),
        ):
            result = router._render("status", None, None)

        self.assertEqual(result["state"], "blocked")
        self.assertFalse(result["result"]["support_revalidated"])
        self.assertEqual(
            result["result"]["support_errors"],
            ["sentence_role_index_receipt_stale"],
        )

        with patch(
            "ksrf.filing.composer.build_structured_complaint",
            return_value=object(),
        ), patch(
            "ksrf.filing.composer.require_release_support",
            return_value=SimpleNamespace(
                sentence_role_index_receipt=copy.deepcopy(stored_receipt),
                application_binding_receipts=(),
                application_binding_index_receipt=copy.deepcopy(
                    application_index_receipt
                ),
            ),
        ):
            unchanged = router._render("status", None, None)

        self.assertEqual(unchanged["state"], "ready_for_expert_review")
        self.assertTrue(unchanged["result"]["support_revalidated"])
        self.assertEqual(unchanged["result"]["support_errors"], [])

    def test_exact_current_receipt_passes_and_binds_release_basis(self) -> None:
        text = "Суды установили факт выплаты."
        binding = sentence_role_binding(
            ordinal=1,
            sentence_id="sent-0123456789abcdef",
            section_code="facts",
            text=text,
            role="application_finding",
        )
        receipt = self._receipt_for([binding])
        manifest = {
            "matter_id": "MATTER-ROLE-1",
            "draft_id": "DRAFT-ROLE-1",
            "status": "ready_for_expert_review",
            "blockers": [],
            "sentence_evidence_map": [
                {
                    "sentence_id": binding["sentence_id"],
                    "section_code": binding["section_code"],
                    "text": text,
                    "role": binding["role"],
                }
            ],
            "sentence_role_index_receipt": receipt,
            "artifacts": [],
            "qa_artifacts": [],
            "enclosures": [],
        }
        authority = StaticRoleAuthority(
            build_sentence_role_index_resolution(
                matter_id="MATTER-ROLE-1",
                draft_id="DRAFT-ROLE-1",
                bindings=[binding],
                authority_revision_id=receipt["authority_revision_id"],
                checked_at=receipt["checked_at"],
            )
        )

        self.assertEqual(
            _manifest_sentence_role_authority_errors(manifest, authority), []
        )
        original_basis = release_basis_sha256(manifest)
        changed = copy.deepcopy(manifest)
        changed["sentence_role_index_receipt"][
            "authority_revision_id"
        ] = "draft-revision-8"
        self.assertNotEqual(release_basis_sha256(changed), original_basis)

    def test_filing_schema_allows_unknown_only_in_blocked_diagnostic(self) -> None:
        blocker = "sentence_role_unknown:sent-0123456789abcdef:practice_cliam"
        manifest = {
            "schema_version": "1.5",
            "matter_id": "MATTER-ROLE-1",
            "draft_id": "DRAFT-ROLE-1",
            "status": "blocked",
            "filing_performed": False,
            "human_only_actions": [
                "signature",
                "fee_or_exemption_confirmation",
                "filing",
            ],
            "source_versions": [],
            "norm_passport_ids": [],
            "issue_option_ids": [],
            "sentence_evidence_map": [
                {
                    "sentence_id": "sent-0123456789abcdef",
                    "section_code": "authorities",
                    "text": "Судебная практика единообразна.",
                    "role": "practice_cliam",
                    "evidence_ids": [],
                    "support_status": "pending",
                }
            ],
            "sentence_role_index_receipt": None,
            "application_binding_receipts": [],
            "application_binding_index_receipt": None,
            "relief_binding_receipts": [],
            "relief_binding_index_receipt": None,
            "holding_binding_receipts": [],
            "holding_binding_index_receipt": None,
            "practice_binding_receipts": [],
            "practice_binding_index_receipt": None,
            "artifacts": [],
            "render_qa": {"passed": False},
            "blockers": [blocker],
        }
        schema = json.loads(
            (
                SKILL_ROOT
                / "schemas"
                / "ksrf_filing"
                / "filing-package.schema.json"
            ).read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(schema)
        self.assertEqual(list(validator.iter_errors(manifest)), [])

        malformed = copy.deepcopy(manifest)
        malformed["blockers"] = ["Префикс: " + blocker]
        self.assertTrue(list(validator.iter_errors(malformed)))

        blank = copy.deepcopy(manifest)
        blank["sentence_evidence_map"][0]["role"] = "   "
        blank["blockers"] = [
            "sentence_role_unknown:sent-0123456789abcdef:   "
        ]
        self.assertTrue(list(validator.iter_errors(blank)))
        self.assertIn(
            "sentence_role_blank_invalid:sent-0123456789abcdef",
            _manifest_sentence_role_projection_errors(blank),
        )

        ready = copy.deepcopy(manifest)
        ready["status"] = "ready_for_expert_review"
        ready["blockers"] = []
        ready_errors = list(validator.iter_errors(ready))
        self.assertTrue(
            any(
                error.validator == "enum"
                and list(error.absolute_path)[-1:] == ["role"]
                for error in ready_errors
            ),
            ready_errors,
        )


if __name__ == "__main__":
    unittest.main()
