# pyright: reportMissingImports=false, reportMissingModuleSource=false
from __future__ import annotations

import copy
import inspect
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from jsonschema import Draft202012Validator


SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = SKILL_ROOT / "lib"
TEST_ROOT = Path(__file__).resolve().parent
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from ksrf.filing.application_binding import (  # noqa: E402
    build_application_finding_binding_index_resolution,
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
from ksrf.filing.practice_binding import (  # noqa: E402
    build_practice_claim_binding_index_resolution,
)
from ksrf.filing.release import (  # noqa: E402
    _manifest_application_binding_authority_errors,
    build_release_pack,
    release_basis_sha256,
    verify_release_manifest,
)
from ksrf.filing.sentence_roles import (  # noqa: E402
    build_sentence_role_index_resolution,
    sentence_role_binding,
)
from ksrf.filing.workflow import WorkflowRouter  # noqa: E402

from test_application_binding_runtime import (  # noqa: E402
    AUTHORITY_REVISION_ID,
    CHAIN_CHECKED_AT,
    CHAIN_REVISION_ID,
    CHECKED_AT,
    StaticApplicationAuthority,
    _index_binding,
    _resolution as _application_resolution,
)
from test_remedy_evidence_binding import (  # noqa: E402
    StaticAuthority,
    _resolution as _remedy_resolution,
    _sentence as _remedy_sentence,
)


APPLICATION_SENTENCE_ID = "sent-a111111111111111"
READY_STATUSES = {
    "ready_for_expert_review",
    "ready_for_human_signing_filing",
}
FILING_SCHEMA_PATH = (
    SKILL_ROOT / "schemas" / "ksrf_filing" / "filing-package.schema.json"
)


def _complaint_payload() -> dict[str, Any]:
    application_finding = {
        "sentence_id": APPLICATION_SENTENCE_ID,
        "text": "Суды применили оспариваемую норму в деле заявителя.",
        "role": "application_finding",
        "claim_id": "CLAIM-A",
        "norm_passport_id": "NVP-A",
        "application_record_ids": ["APP-A"],
        "evidence_ids": ["EVIDENCE-FICTIONAL"],
        "maximum_supported_inference": "explicitly_applied",
        "support_status": "verified",
    }
    sections: list[dict[str, Any]] = []
    for code in REQUIRED_SECTION_CODES:
        sections.append(
            {
                "code": code,
                "heading": f"Раздел {code}",
                "sentences": [application_finding] if code == "facts" else [],
            }
        )
    return {
        "matter_id": "MATTER-APPLICATION-1",
        "draft_id": "DRAFT-APPLICATION-1",
        "title": "Жалоба",
        "sections": sections,
        "norm_passport_ids": ["NVP-A"],
        "issue_option_ids": [],
    }


def _ready_status_rules(schema: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for rule in schema.get("allOf", []):
        if not isinstance(rule, dict):
            continue
        condition = rule.get("if", {})
        status = condition.get("properties", {}).get("status", {})
        if set(status.get("enum", ())) != READY_STATUSES:
            continue
        then_properties = rule.get("then", {}).get("properties", {})
        if isinstance(then_properties, dict):
            result.append(then_properties)
    return result


def _application_sentence(complaint: Any) -> Any:
    return next(
        sentence
        for section in complaint.sections
        for sentence in section.sentences
        if sentence.sentence_id == APPLICATION_SENTENCE_ID
    )


def _integrated_application_case() -> tuple[Any, StaticAuthority, Any]:
    remedy_sentence_id = "sent-b111111111111111"
    remedy_text = "Признать норму неконституционной"
    application_finding = {
        "sentence_id": APPLICATION_SENTENCE_ID,
        "text": "Суды применили оспариваемую норму в деле заявителя.",
        "role": "application_finding",
        "claim_id": "CLAIM-A",
        "norm_passport_id": "NVP-A",
        "application_record_ids": ["APP-A"],
        "evidence_ids": ["E-EXPRESS", "E-OUTCOME", "E-RULE"],
        "maximum_supported_inference": "explicitly_applied",
        "support_status": "verified",
    }
    remedy = _remedy_sentence(
        remedy_sentence_id,
        "CLAIM-A",
        "ISSUE-A",
        "NVP-A",
        "APP-A",
        "E-RELIEF",
        remedy_text,
    )
    sections: list[dict[str, Any]] = []
    for code in REQUIRED_SECTION_CODES:
        sentences: list[dict[str, Any]] = []
        if code == "facts":
            sentences = [application_finding]
        elif code == "requested_remedy":
            sentences = [remedy]
        sections.append(
            {
                "code": code,
                "heading": f"Раздел {code}",
                "sentences": sentences,
            }
        )
    complaint = build_structured_complaint(
        {
            "matter_id": "MATTER-A",
            "draft_id": "DRAFT-A",
            "title": "Жалоба",
            "sections": sections,
            "norm_passport_ids": ["NVP-A"],
            "issue_option_ids": ["ISSUE-A"],
            "issue_option_id": "ISSUE-A",
        }
    )
    relief_authority = StaticAuthority(
        {
            remedy_sentence_id: _remedy_resolution(
                "CLAIM-A",
                "ISSUE-A",
                "NVP-A",
                "APP-A",
                "E-RELIEF",
                remedy_text,
            )
        }
    )
    request = complaint.application_finding_binding_request(
        _application_sentence(complaint)
    )
    assert request is not None
    index_resolution = build_application_finding_binding_index_resolution(
        matter_id=complaint.matter_id,
        draft_id=complaint.draft_id,
        bindings=[_index_binding(request)],
        authority_revision_id=AUTHORITY_REVISION_ID,
        checked_at=CHECKED_AT,
    )
    application_authority = StaticApplicationAuthority(
        _application_resolution(request), index_resolution
    )
    return complaint, relief_authority, application_authority


class _AuxiliaryIndexAuthority:
    def __init__(
        self,
        *,
        holding_resolution: dict[str, Any],
        practice_resolution: dict[str, Any],
        sentence_role_resolution: dict[str, Any],
    ) -> None:
        self.holding_resolution = copy.deepcopy(holding_resolution)
        self.practice_resolution = copy.deepcopy(practice_resolution)
        self.sentence_role_resolution = copy.deepcopy(sentence_role_resolution)

    def resolve_holding_evidence_binding_index(
        self, request: dict[str, Any]
    ) -> dict[str, Any]:
        return copy.deepcopy(self.holding_resolution)

    def resolve_practice_claim_evidence_binding_index(
        self, request: dict[str, Any]
    ) -> dict[str, Any]:
        return copy.deepcopy(self.practice_resolution)

    def resolve_sentence_role_index(
        self, request: dict[str, Any]
    ) -> dict[str, Any]:
        return copy.deepcopy(self.sentence_role_resolution)


def _ready_application_manifest() -> tuple[
    dict[str, Any], StaticAuthority, Any, _AuxiliaryIndexAuthority
]:
    complaint, relief_authority, application_authority = (
        _integrated_application_case()
    )
    receipts = require_release_support(
        complaint,
        relief_binding_authority=relief_authority,
        application_binding_authority=application_authority,
        require_application_index=True,
    )
    role_bindings = [
        sentence_role_binding(
            ordinal=ordinal,
            sentence_id=entry["sentence_id"],
            section_code=entry["section_code"],
            text=entry["text"],
            role=entry["role"],
        )
        for ordinal, entry in enumerate(
            complaint.sentence_evidence_map(), start=1
        )
    ]
    role_resolution = build_sentence_role_index_resolution(
        matter_id=complaint.matter_id,
        draft_id=complaint.draft_id,
        bindings=role_bindings,
        authority_revision_id="SENTENCE-ROLE-REGISTRY-REV-APPLICATION-1",
        checked_at=CHECKED_AT,
    )
    holding_resolution = build_holding_binding_index_resolution(
        matter_id=complaint.matter_id,
        draft_id=complaint.draft_id,
        bindings=[],
        authority_revision_id="HOLDING-REGISTRY-REV-APPLICATION-1",
        checked_at=CHECKED_AT,
    )
    practice_resolution = build_practice_claim_binding_index_resolution(
        matter_id=complaint.matter_id,
        draft_id=complaint.draft_id,
        bindings=[],
        authority_revision_id="PRACTICE-REGISTRY-REV-APPLICATION-1",
        checked_at=CHECKED_AT,
    )
    auxiliary_authority = _AuxiliaryIndexAuthority(
        holding_resolution=holding_resolution,
        practice_resolution=practice_resolution,
        sentence_role_resolution=role_resolution,
    )
    role_receipt = copy.deepcopy(role_resolution)
    role_receipt.pop("status")
    holding_receipt = copy.deepcopy(holding_resolution)
    holding_receipt.pop("status")
    practice_receipt = copy.deepcopy(practice_resolution)
    practice_receipt.pop("status")
    relief_receipts = [
        copy.deepcopy(item) for item in receipts.relief_binding_receipts
    ]
    manifest: dict[str, Any] = {
        "schema_version": "1.5",
        "matter_id": complaint.matter_id,
        "draft_id": complaint.draft_id,
        "status": "ready_for_expert_review",
        "filing_performed": False,
        "human_only_actions": [
            "signature",
            "fee_or_exemption_confirmation",
            "filing",
        ],
        "source_versions": ["SOURCE-APPLICATION-1"],
        "norm_passport_ids": list(complaint.norm_passport_ids),
        "issue_option_ids": list(complaint.issue_option_ids),
        "issue_option_id": complaint.issue_option_id,
        "sentence_evidence_map": complaint.sentence_evidence_map(),
        "sentence_role_index_receipt": role_receipt,
        "relief_binding_receipts": relief_receipts,
        "relief_binding_index_receipt": copy.deepcopy(
            relief_receipts[0]["binding_index_receipt"]
        ),
        "application_binding_receipts": [
            copy.deepcopy(item)
            for item in receipts.application_binding_receipts
        ],
        "application_binding_index_receipt": copy.deepcopy(
            receipts.application_binding_index_receipt
        ),
        "holding_binding_receipts": [],
        "holding_binding_index_receipt": holding_receipt,
        "practice_binding_receipts": [],
        "practice_binding_index_receipt": practice_receipt,
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
    return (
        manifest,
        relief_authority,
        application_authority,
        auxiliary_authority,
    )


class ApplicationFindingEvidenceBindingRedTests(unittest.TestCase):
    def test_application_record_ids_survive_normalization_and_serialization(
        self,
    ) -> None:
        complaint = build_structured_complaint(_complaint_payload())
        sentence = _application_sentence(complaint)

        self.assertEqual(("APP-A",), sentence.application_record_ids)
        self.assertEqual(
            ["APP-A"],
            complaint.to_dict()["sentence_evidence_map"][0][
                "application_record_ids"
            ],
        )

    def test_application_finding_exposes_structural_binding_status_and_hash(
        self,
    ) -> None:
        complaint = build_structured_complaint(_complaint_payload())
        entry = next(
            item
            for item in complaint.to_dict()["sentence_evidence_map"]
            if item["sentence_id"] == APPLICATION_SENTENCE_ID
        )

        self.assertEqual("bound", entry["application_binding_status"])
        self.assertRegex(entry["application_binding_sha256"], r"^[0-9a-f]{64}$")

    def test_release_entrypoints_require_current_application_authority(
        self,
    ) -> None:
        support_parameters = inspect.signature(require_release_support).parameters
        pack_parameters = inspect.signature(build_release_pack).parameters

        self.assertIn("application_binding_authority", support_parameters)
        self.assertIn("require_application_index", support_parameters)
        self.assertIn("application_binding_authority", pack_parameters)

    def test_caller_status_and_fictional_id_fail_without_host_authority(
        self,
    ) -> None:
        complaint = build_structured_complaint(_complaint_payload())

        with self.assertRaises(ComplaintModelError) as caught:
            require_release_support(
                complaint,
                application_binding_authority=None,
                require_application_index=True,
            )

        self.assertIn(
            f"{APPLICATION_SENTENCE_ID}:application_binding_authority_required",
            caught.exception.reason_codes,
        )

    def test_ready_manifest_schema_requires_application_receipts_and_index(
        self,
    ) -> None:
        schema = json.loads(FILING_SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertIn("application_binding_receipts", schema["required"])
        self.assertIn("application_binding_index_receipt", schema["required"])
        self.assertIn("applicationBindingReceipt", schema["$defs"])
        self.assertIn("applicationBindingIndexReceipt", schema["$defs"])

        ready_rules = _ready_status_rules(schema)
        self.assertTrue(
            any(
                properties.get("application_binding_index_receipt")
                == {"$ref": "#/$defs/applicationBindingIndexReceipt"}
                for properties in ready_rules
            ),
            "ready manifests must require a current complete application index",
        )


class ApplicationFindingEvidenceBindingIntegrationTests(unittest.TestCase):
    def test_composer_accepts_real_current_application_authority_and_full_index(
        self,
    ) -> None:
        complaint, relief_authority, application_authority = (
            _integrated_application_case()
        )

        receipts = require_release_support(
            complaint,
            relief_binding_authority=relief_authority,
            application_binding_authority=application_authority,
            require_application_index=True,
        )

        self.assertEqual(len(receipts.application_binding_receipts), 1)
        receipt = receipts.application_binding_receipts[0]
        self.assertEqual(receipt["sentence_id"], APPLICATION_SENTENCE_ID)
        self.assertEqual(
            receipt["authority_revision_id"], AUTHORITY_REVISION_ID
        )
        self.assertEqual(receipt["checked_at"], CHECKED_AT)
        self.assertEqual(
            receipt["chain_inventory_receipt"]["chain_revision_id"],
            CHAIN_REVISION_ID,
        )
        self.assertEqual(
            receipt["chain_inventory_receipt"]["checked_at"],
            CHAIN_CHECKED_AT,
        )
        self.assertEqual(
            receipts.application_binding_index_receipt[
                "authority_revision_id"
            ],
            AUTHORITY_REVISION_ID,
        )
        self.assertEqual(
            receipts.application_binding_index_receipt["bindings"],
            [
                _index_binding(
                    complaint.application_finding_binding_request(
                        _application_sentence(complaint)
                    )
                )
            ],
        )

    def test_ready_manifest_with_real_receipt_and_index_passes_contract_and_revalidation(
        self,
    ) -> None:
        (
            manifest,
            relief_authority,
            application_authority,
            auxiliary_authority,
        ) = _ready_application_manifest()
        schema = json.loads(FILING_SCHEMA_PATH.read_text(encoding="utf-8"))

        schema_errors = list(Draft202012Validator(schema).iter_errors(manifest))
        application_errors = _manifest_application_binding_authority_errors(
            manifest, application_authority
        )
        verification_errors = verify_release_manifest(
            manifest,
            relief_binding_authority=relief_authority,
            application_binding_authority=application_authority,
            holding_binding_authority=auxiliary_authority,
            practice_binding_authority=auxiliary_authority,
            sentence_role_authority=auxiliary_authority,
        )

        self.assertEqual(schema_errors, [])
        self.assertEqual(application_errors, [])
        self.assertFalse(
            any(
                error.startswith("application_binding")
                for error in verification_errors
            ),
            verification_errors,
        )

    def test_schema_rejects_extra_fields_in_nested_application_receipts(
        self,
    ) -> None:
        manifest, _relief, _application, _auxiliary = (
            _ready_application_manifest()
        )
        schema = json.loads(FILING_SCHEMA_PATH.read_text(encoding="utf-8"))
        mutations = {
            "norm_gate": lambda receipt: receipt[
                "norm_version_gate_receipt"
            ].__setitem__("attacker_extra", True),
            "application_gate": lambda receipt: next(
                iter(receipt["application_gate_receipts"].values())
            ).__setitem__("attacker_extra", True),
            "scope_record": lambda receipt: receipt["scope_receipt"][
                "scope_record"
            ].__setitem__("attacker_extra", True),
            "scope_gate": lambda receipt: receipt["scope_receipt"][
                "scope_gate_receipt"
            ].__setitem__("attacker_extra", True),
        }

        for label, mutate in mutations.items():
            with self.subTest(label=label):
                changed = copy.deepcopy(manifest)
                mutate(changed["application_binding_receipts"][0])

                errors = list(
                    Draft202012Validator(schema).iter_errors(changed)
                )

                self.assertTrue(errors, label)

    def test_current_authority_mutation_blocks_stored_receipt_and_index(self) -> None:
        for mutation, expected_error in (
            (
                "line_checked_at",
                f"application_binding_receipt_stale:{APPLICATION_SENTENCE_ID}",
            ),
            (
                "index_checked_at",
                "application_binding_index_receipt_stale",
            ),
        ):
            with self.subTest(mutation=mutation):
                (
                    manifest,
                    relief_authority,
                    application_authority,
                    auxiliary_authority,
                ) = _ready_application_manifest()
                if mutation == "line_checked_at":
                    application_authority.resolution["checked_at"] = (
                        "2026-09-01T12:01:00Z"
                    )
                else:
                    application_authority.index_resolution["checked_at"] = (
                        "2026-09-01T12:01:00Z"
                    )

                errors = verify_release_manifest(
                    manifest,
                    relief_binding_authority=relief_authority,
                    application_binding_authority=application_authority,
                    holding_binding_authority=auxiliary_authority,
                    practice_binding_authority=auxiliary_authority,
                    sentence_role_authority=auxiliary_authority,
                )

                self.assertIn(expected_error, errors)

    def test_release_basis_binds_application_receipt_and_index(self) -> None:
        manifest, _relief, _application, _auxiliary = (
            _ready_application_manifest()
        )
        baseline = release_basis_sha256(manifest)
        mutations = {
            "receipt": lambda value: value[
                "application_binding_receipts"
            ][0].__setitem__("checked_at", "2026-09-01T12:02:00Z"),
            "index": lambda value: value[
                "application_binding_index_receipt"
            ].__setitem__("checked_at", "2026-09-01T12:02:00Z"),
        }

        for label, mutate in mutations.items():
            with self.subTest(field=label):
                changed = copy.deepcopy(manifest)
                mutate(changed)
                self.assertNotEqual(release_basis_sha256(changed), baseline)

    def test_render_never_returns_ready_with_application_receipts_stale_at_return(
        self,
    ) -> None:
        complaint, relief_authority, application_authority = (
            _integrated_application_case()
        )
        _manifest, _relief, _application, auxiliary_authority = (
            _ready_application_manifest()
        )
        with tempfile.TemporaryDirectory() as output_dir:
            router = object.__new__(WorkflowRouter)
            router.workspace = Path(output_dir)
            router.relief_binding_authority = relief_authority
            router.application_binding_authority = application_authority
            router.holding_binding_authority = auxiliary_authority
            router.practice_binding_authority = auxiliary_authority
            router.sentence_role_authority = auxiliary_authority

            def render(_complaint: Any, path: Any) -> SimpleNamespace:
                application_authority.resolution["checked_at"] = (
                    "2026-09-01T12:09:00Z"
                )
                application_authority.index_resolution["checked_at"] = (
                    "2026-09-01T12:09:00Z"
                )
                return SimpleNamespace(
                    path=Path(path),
                    to_dict=lambda: {"path": str(path)},
                )

            def convert(
                _docx: Any, path: Any, **_kwargs: Any
            ) -> SimpleNamespace:
                return SimpleNamespace(
                    path=Path(path),
                    to_dict=lambda: {"path": str(path)},
                )

            with (
                patch("ksrf.filing.renderer.render_docx", render),
                patch("ksrf.filing.renderer.convert_docx_to_pdf", convert),
                patch(
                    "ksrf.filing.renderer.validate_rendered_pair",
                    lambda *_args, **_kwargs: {"passed": True},
                ),
            ):
                result = router._render(
                    "build",
                    {"complaint": complaint.to_dict()},
                    {"sha256": "a" * 64},
                )

        if result["state"] != "blocked":
            self.assertEqual(
                result["result"]["application_binding_receipts"][0][
                    "checked_at"
                ],
                application_authority.resolution["checked_at"],
            )
            self.assertEqual(
                result["result"]["application_binding_index_receipt"][
                    "checked_at"
                ],
                application_authority.index_resolution["checked_at"],
            )

    def test_pack_build_never_returns_ready_with_application_receipts_stale_at_return(
        self,
    ) -> None:
        complaint, relief_authority, application_authority = (
            _integrated_application_case()
        )
        complaint = replace(complaint, source_versions=("SOURCE-APPLICATION-1",))
        _manifest, _relief, _application, auxiliary_authority = (
            _ready_application_manifest()
        )

        with tempfile.TemporaryDirectory() as output_dir:
            def render(_complaint: Any, path: Any) -> SimpleNamespace:
                application_authority.resolution["checked_at"] = (
                    "2026-09-01T12:09:00Z"
                )
                application_authority.index_resolution["checked_at"] = (
                    "2026-09-01T12:09:00Z"
                )
                return SimpleNamespace(
                    path=Path(path),
                    to_dict=lambda: {"kind": "complaint_docx"},
                )

            def convert(
                _docx: Any, path: Any, **_kwargs: Any
            ) -> SimpleNamespace:
                return SimpleNamespace(
                    path=Path(path),
                    to_dict=lambda: {"kind": "complaint_pdf"},
                )

            with (
                patch("ksrf.filing.release.REQUIRED_APPROVALS", ()),
                patch("ksrf.filing.release.render_docx", render),
                patch("ksrf.filing.release.convert_docx_to_pdf", convert),
                patch(
                    "ksrf.filing.release.validate_rendered_pair",
                    lambda *_args, **_kwargs: {"passed": True},
                ),
                patch(
                    "ksrf.filing.release._qa_artifacts",
                    lambda *_args: [{"dummy": True}],
                ),
                patch(
                    "ksrf.filing.release._formal_check_ready",
                    lambda *_args: (True, []),
                ),
                patch(
                    "ksrf.filing.release._manifest_schema_errors",
                    lambda *_args: [],
                ),
            ):
                manifest = build_release_pack(
                    complaint,
                    output_dir,
                    relief_binding_authority=relief_authority,
                    application_binding_authority=application_authority,
                    holding_binding_authority=auxiliary_authority,
                    practice_binding_authority=auxiliary_authority,
                    sentence_role_authority=auxiliary_authority,
                )

        self.assertEqual("ready_for_expert_review", manifest["status"])
        self.assertEqual([], manifest["blockers"])
        self.assertEqual(
            "2026-09-01T12:09:00Z",
            manifest["application_binding_receipts"][0]["checked_at"],
        )
        self.assertEqual(
            "2026-09-01T12:09:00Z",
            manifest["application_binding_index_receipt"]["checked_at"],
        )
        self.assertNotEqual(
            CHECKED_AT,
            manifest["application_binding_receipts"][0]["checked_at"],
        )


if __name__ == "__main__":
    unittest.main()
