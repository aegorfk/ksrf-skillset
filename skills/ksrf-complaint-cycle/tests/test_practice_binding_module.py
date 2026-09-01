from __future__ import annotations

from copy import deepcopy
from collections.abc import Iterator, Mapping, Sequence
from hashlib import sha256
from pathlib import Path
import sys
import unittest
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = SKILL_ROOT / "lib"
TEST_ROOT = SKILL_ROOT / "tests"
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

import test_practice_analysis as practice_analysis_tests  # noqa: E402

practice = practice_analysis_tests.practice

from ksrf.filing.issue_options import (  # noqa: E402
    issue_approval_requests,
    issue_candidate_from_dict,
)
from ksrf.filing.practice_binding import (  # noqa: E402
    build_practice_claim_binding_index_resolution,
    build_practice_claim_binding_request,
    build_practice_claim_binding_resolution,
    resolve_practice_claim_evidence_binding,
    resolve_practice_claim_evidence_binding_index,
)
from ksrf.filing.storage import canonical_json_bytes  # noqa: E402


def _digest(value: object) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def _gate(*, rationale: str) -> dict[str, object]:
    return {
        "state": "passed",
        "rationale": rationale,
        "evidence_ids": [],
        "reviewer": None,
        "reviewed_at": None,
        "requires_human_review": False,
    }


def _issue_candidate(
    *, claim_id: str, issue_id: str, practice_claim_id: str, text: str, finding_id: str
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "issue_id": issue_id,
        "seed_id": "seed-practice",
        "claim_id": claim_id,
        "object_of_review": {"norm_id": "norm-1", "norm_version_id": "edition-1"},
        "theory_code": "judicial_meaning",
        "normative_meaning": "Проверяемый смысл нормы.",
        "application_proof": {"evidence_ids": ["application-1"], "gate_passed": True},
        "constitutional_benchmarks": ["ст. 19 Конституции РФ"],
        "rights_impairment": "Неравное применение.",
        "anti_fourth_instance_boundary": "Оспаривается смысл нормы.",
        "ksrf_authority_ids": ["ksrf-1"],
        "adverse_authority": {"authority_ids": [], "summary": "Нет.", "delta": "Нет."},
        "requested_remedy": "Выявить конституционно-правовой смысл.",
        "strengths": ["Есть корпус."],
        "weaknesses": [],
        "source_gaps": [],
        "model_rank": 1,
        "gates": {
            "anti_fourth_instance": _gate(rationale="Граница соблюдена."),
            "practice_claims": [
                {
                    "claim_id": practice_claim_id,
                    "statement": text,
                    "state": "proven",
                    "evidence_ids": [finding_id],
                    "authority_scope": "Раскрытый проверенный корпус.",
                    "authority_class": "official_judicial",
                    "freshness_status": "current",
                    "counterexample_ids": [],
                    "counterexample_review_status": "reviewed_none_found",
                    "human_decision": "approved",
                    "reviewer": "И.И. Иванов",
                    "reviewed_at": "2026-09-01T10:00:00Z",
                }
            ],
            "adverse_authority": _gate(rationale="Неблагоприятная практика проверена."),
            "remedy": _gate(rationale="Просьба в компетенции КС РФ."),
        },
        "human_selection": {
            "state": "principal",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-09-01T10:00:00Z",
            "note": "Основной вариант.",
        },
    }


def _valid_case() -> tuple[dict[str, Any], dict[str, Any]]:
    request = build_practice_claim_binding_request(
        matter_id="matter-1",
        draft_id="draft-1",
        sentence_id="sent-0123456789abcdef",
        section_code="legal_position",
        sentence_text="В раскрытом корпусе наблюдается проверенный судебный подход.",
        claim_id="constitutional-claim-1",
        practice_claim_id="practice-claim-1",
        issue_option_id="issue-option-1",
        evidence_ids=["0" * 64],
        maximum_supported_inference="corroborated_observed_corpus",
    )

    candidate = {
        "candidate_id": "candidate-1",
        "plan_sha256": "3" * 64,
        "claim_wording": request["sentence_text"],
        "maximum_permitted_claim": request["maximum_supported_inference"],
        "human_review": "approved",
        "drafting_ready": True,
    }
    position_cards = [
        {"position_card_id": "position-1", "human_review": "approved"}
    ]
    comparisons = [
        {
            "comparison_id": "comparison-1",
            "position_card_id": "position-1",
            "status": "matched",
            "review_provenance": {
                "status": "approved",
                "reviewer": "И.И. Иванов",
            },
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
        "claim_wording": request["sentence_text"],
        "maximum_permitted_claim": request["maximum_supported_inference"],
        "supporting_position_card_ids": ["position-1"],
        "adverse_position_card_ids": [],
    }
    human_decision = {
        "decision": "approved",
        "reviewer": "И.И. Иванов",
        "candidate_ids": [candidate["candidate_id"]],
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
                "bytes": len(canonical_json_bytes(content)),
                "sha256": _digest(content),
            }
            for path, content in proof_files.items()
        ],
        key=lambda item: item["path"],
    )
    normative_bridge_sha256 = _digest(bridge)
    candidate_sha256 = _digest(candidate)
    finding_id = _digest(
        {
            "candidate_sha256": candidate_sha256,
            "claim_ids": [request["practice_claim_id"]],
            "normative_bridge_sha256": normative_bridge_sha256,
        }
    )
    request = build_practice_claim_binding_request(
        matter_id=request["matter_id"],
        draft_id=request["draft_id"],
        sentence_id=request["sentence_id"],
        section_code=request["section_code"],
        sentence_text=request["sentence_text"],
        claim_id=request["claim_id"],
        practice_claim_id=request["practice_claim_id"],
        issue_option_id=request["issue_option_id"],
        evidence_ids=[finding_id],
        maximum_supported_inference=request["maximum_supported_inference"],
    )
    finding = {
        "finding_id": finding_id,
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": candidate_sha256,
        "candidate": candidate,
        "claim_ids": [request["practice_claim_id"]],
        "claim_wording": request["sentence_text"],
        "supporting_position_card_ids": ["position-1"],
        "adverse_position_card_ids": [],
        "maximum_permitted_claim": request["maximum_supported_inference"],
    }
    claim_bindings = [
        {
            "claim_id": request["practice_claim_id"],
            "claim_sha256": "a" * 64,
            "source_locator": "source-"
            + _digest({"private_source_locator": "claims.json#/claims/0"})[:24],
        }
    ]
    research_questions = ["Каков проверяемый судебный смысл нормы?"]
    research_core = {
        "questions": research_questions,
        "claim_bindings": claim_bindings,
        "claim_set_sha256": _digest(claim_bindings),
    }
    research_request_sha256 = _digest(research_core)
    research_request = {
        "schema_version": "2.0",
        "created_at": "2026-09-01T09:10:00Z",
        "source_skill": "ksrf-complaint-cycle",
        "target_skill": "ksrf-cassation-judicial-meaning",
        "run_id": "practice-request-fixture",
        "plan_sha256": research_request_sha256,
        "evidence_sha256": "7" * 64,
        "payload_type": "unproven_research_questions",
        "payload": {
            **research_core,
            "request_sha256": research_request_sha256,
            "claim_questions": [
                {
                    "claim_id": request["practice_claim_id"],
                    "question_id": _digest(
                        {
                            "claim_id": request["practice_claim_id"],
                            "question": research_questions[0],
                        }
                    ),
                    "question": research_questions[0],
                    "disconfirmation_prompts": [
                        "Найти противоположное прочтение."
                    ],
                }
            ],
            "drafting_ready": False,
        },
        "limitations": ["Request не является выводом для жалобы."],
    }
    research_request["handoff_id"] = _digest(research_request)
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
    result = {
        "schema_version": "2.0",
        "created_at": "2026-09-01T09:30:00Z",
        "source_skill": "ksrf-cassation-judicial-meaning",
        "target_skill": "ksrf-complaint-cycle",
        "run_id": "run-1",
        "plan_sha256": candidate["plan_sha256"],
        "evidence_sha256": "4" * 64,
        "fingerprint_sha256": "5" * 64,
        "payload_type": "approved_bounded_findings",
        "payload": {
            "request_handoff_id": research_request["handoff_id"],
            "request_sha256": research_request_sha256,
            "claim_set_sha256": _digest(claim_bindings),
            "claim_bindings": claim_bindings,
            "findings": [finding],
            "approval_binding": {
                "human_decision_sha256": _digest(human_decision),
                "validation_report_sha256": _digest(validation_report),
                "normative_bridge_sha256": normative_bridge_sha256,
                "reviewer": "И.И. Иванов",
                "approved_at": "2026-09-01T09:29:00Z",
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
            "maximum_permitted_claim": request["maximum_supported_inference"],
            "limitations": ["Только раскрытый корпус."],
            "quality_bindings": quality_bindings,
            "drafting_ready": True,
            "supporting_position_card_ids": ["position-1"],
            "adverse_position_card_ids": [],
        },
        "limitations": ["Только раскрытый корпус."],
    }
    result["handoff_id"] = _digest(result)

    wording_review = {
        "schema_version": "1.0",
        "record_type": "wording_review",
        "claim_id": request["practice_claim_id"],
        "revision_id": "f" * 64,
        "claim_sha256": "a" * 64,
        "handoff_id": result["handoff_id"],
        "request_id": result["payload"]["request_handoff_id"],
        "finding_ids": [finding_id],
        "maximum_permitted_claim": request["maximum_supported_inference"],
        "plan_sha256": result["plan_sha256"],
        "evidence_sha256": result["evidence_sha256"],
        "fingerprint_sha256": result["fingerprint_sha256"],
        "human_decision_sha256": result["payload"]["approval_binding"]["human_decision_sha256"],
        "validation_report_sha256": result["payload"]["approval_binding"]["validation_report_sha256"],
        "normative_bridge_sha256": normative_bridge_sha256,
        "decision": "within_limit",
        "reviewer": "И.И. Иванов",
        "reason": "Формулировка в пределах корпуса.",
        "wording_text": request["sentence_text"],
        "wording_sha256": _digest(request["sentence_text"]),
        "wording_source_path": "/host-owned/claims.json",
        "wording_source_sha256": "1" * 64,
        "reviewed_at": "2026-09-01T09:40:00Z",
        "ledger_id": "wording-ledger",
        "sequence": 1,
        "previous_event_sha256": None,
        "event_sha256": None,
    }
    wording_review["event_sha256"] = _digest(
        {
            key: value
            for key, value in wording_review.items()
            if key != "event_sha256"
        }
    )
    practice_state = {
        "claim_id": request["practice_claim_id"],
        "revision_id": wording_review["revision_id"],
        "claim_sha256": wording_review["claim_sha256"],
        "source_locator": "claims.json#/claims/0",
        "source_file_sha256": "1" * 64,
        "input_bindings_sha256": "2" * 64,
        "input_manifest_updated_at": "2026-09-01T09:00:00Z",
        "claim_created_at": "2026-09-01T09:00:00Z",
        "hypothesis_ids": ["hypothesis-1"],
        "option_ids": [request["issue_option_id"]],
        "empirical_dimensions": ["judicial_meaning"],
        "analysis_route": "cassation-judicial-meaning",
        "state": "ready",
        "draft_blocked": False,
        "blocking_reasons": [],
        "next_actions": [],
        "request_id": result["payload"]["request_handoff_id"],
        "handoff_id": result["handoff_id"],
        "maximum_permitted_claim": request["maximum_supported_inference"],
        "plan_sha256": result["plan_sha256"],
        "evidence_sha256": result["evidence_sha256"],
        "fingerprint_sha256": result["fingerprint_sha256"],
        "wording_review_event_sha256": wording_review["event_sha256"],
        "wording_reviewed_at": wording_review["reviewed_at"],
        "result_import_event_sha256": "3" * 64,
        "result_imported_at": "2026-09-01T09:35:00Z",
        "result_source_sha256": "4" * 64,
        "result_created_at": result["created_at"],
        "attachment_event_sha256": "5" * 64,
        "attachment_attached_at": "2026-09-01T09:20:00Z",
        "anchor_checked_at": "2026-09-01T09:35:00Z",
        "trust_anchor_sha256": "6" * 64,
        "wording_review": wording_review,
    }
    ready_binding_fields = (
        "claim_id", "revision_id", "claim_sha256", "source_file_sha256",
        "input_bindings_sha256", "input_manifest_updated_at", "claim_created_at",
        "handoff_id", "plan_sha256", "evidence_sha256", "fingerprint_sha256",
        "maximum_permitted_claim", "wording_review_event_sha256", "wording_reviewed_at",
        "result_import_event_sha256", "result_imported_at", "result_source_sha256",
        "result_created_at", "attachment_event_sha256", "attachment_attached_at",
        "anchor_checked_at", "trust_anchor_sha256",
    )
    ready_binding = {key: practice_state[key] for key in ready_binding_fields}
    ready_claim_bindings = [ready_binding]
    ready_set_sha = _digest(ready_claim_bindings)
    refresh_record = {
        "schema_version": "1.0",
        "record_type": "prefiling_refresh",
        "as_of": "2026-09-01",
        "corpus_cutoff": "2026-09-01",
        "reviewer": "И.И. Иванов",
        "official_check_ref": "Официальные источники перепроверены.",
        "ready_claim_bindings": ready_claim_bindings,
        "ready_claim_set_sha256": ready_set_sha,
        "recorded_at": "2026-09-01T09:50:00Z",
        "ledger_id": "refresh-ledger",
        "sequence": 1,
        "previous_event_sha256": None,
        "event_sha256": None,
    }
    refresh_record["event_sha256"] = _digest(
        {
            key: value
            for key, value in refresh_record.items()
            if key != "event_sha256"
        }
    )
    refresh = {
        "required": True,
        "valid": True,
        "record": refresh_record,
        "ready_claim_set_sha256": ready_set_sha,
    }
    filing_state = {
        "schema_version": "1.0",
        "case_id": "case-1",
        "generated_at": "2026-09-01T09:51:00Z",
        "stage": "filing",
        "input_bindings": {
            "case_file_sha256": "8" * 64,
            "argument_research_sha256": "9" * 64,
            "input_bindings_sha256": practice_state["input_bindings_sha256"],
        },
        "counts_by_state": {
            "not_required": 0, "required": 0, "running": 0,
            "blocked": 0, "ready": 1, "stale": 0,
        },
        "claims": [practice_state],
        "stage_verdict": "ready",
        "blocked_claim_ids": [],
        "allowed_claim_ids": [request["practice_claim_id"]],
        "unaffected_claim_ids": [],
        "global_integrity_errors": [],
        "prefiling_refresh": refresh,
    }
    filing_validation = {
        "schema_version": "1.0",
        "valid": True,
        "stage": "filing",
        "errors": [],
        "blocked_claim_ids": [],
        "allowed_claim_ids": [request["practice_claim_id"]],
        "unaffected_claim_ids": [],
        "global_integrity_errors": [],
        "state": filing_state,
        "validated_at": "2026-09-01T09:51:00Z",
    }
    issue_payload = _issue_candidate(
        claim_id=request["claim_id"],
        issue_id=request["issue_option_id"],
        practice_claim_id=request["practice_claim_id"],
        text=request["sentence_text"],
        finding_id=finding_id,
    )
    issue = issue_candidate_from_dict(issue_payload)
    approvals = issue_approval_requests(issue)
    selected_approvals = {
        f"practice:{request['practice_claim_id']}": approvals[f"practice:{request['practice_claim_id']}"],
        "selection": approvals["selection"],
    }
    resolution = build_practice_claim_binding_resolution(
        request=request,
        matter_binding={
            "matter_id": request["matter_id"],
            "draft_id": request["draft_id"],
            "case_id": filing_state["case_id"],
            "workspace_revision_id": "workspace-revision-1",
            "input_bindings_sha256": practice_state["input_bindings_sha256"],
        },
        practice_state=practice_state,
        ready_binding=ready_binding,
        research_request=research_request,
        result=result,
        findings=[finding],
        wording_review=wording_review,
        filing_validation=filing_validation,
        prefiling_refresh=refresh,
        issue_candidate=issue_payload,
        issue_approval_requests=selected_approvals,
        trusted_approval_ids={
            f"practice:{request['practice_claim_id']}": "trusted-approval:sha256:" + "a" * 64,
            "selection": "trusted-approval:sha256:" + "b" * 64,
        },
        authority_revision_id="practice-authority-revision-1",
        checked_at="2026-09-01T09:52:00Z",
    )
    return request, resolution


def _rebind_result_handoff(resolution: dict[str, Any]) -> None:
    result = resolution["result"]
    result["handoff_id"] = _digest(
        {key: deepcopy(value) for key, value in result.items() if key != "handoff_id"}
    )
    handoff_id = result["handoff_id"]

    wording = resolution["wording_review"]
    wording["handoff_id"] = handoff_id
    wording["event_sha256"] = _digest(
        {key: value for key, value in wording.items() if key != "event_sha256"}
    )
    state = resolution["practice_state"]
    state["handoff_id"] = handoff_id
    state["wording_review_event_sha256"] = wording["event_sha256"]
    state["wording_review"] = deepcopy(wording)
    resolution["ready_binding"]["handoff_id"] = handoff_id
    resolution["ready_binding"]["wording_review_event_sha256"] = wording[
        "event_sha256"
    ]

    filing_state = resolution["filing_validation"]["state"]
    filing_state["claims"][0] = deepcopy(state)

    refresh = resolution["prefiling_refresh"]
    refresh["record"]["ready_claim_bindings"][0] = deepcopy(
        resolution["ready_binding"]
    )
    ready_set_sha256 = _digest(refresh["record"]["ready_claim_bindings"])
    refresh["record"]["ready_claim_set_sha256"] = ready_set_sha256
    refresh["record"]["event_sha256"] = _digest(
        {
            key: value
            for key, value in refresh["record"].items()
            if key != "event_sha256"
        }
    )
    refresh["ready_claim_set_sha256"] = ready_set_sha256
    filing_state["prefiling_refresh"] = deepcopy(refresh)


class StaticAuthority:
    def __init__(self, resolution: dict[str, object], index: dict[str, object] | None = None):
        self.resolution = resolution
        self.index = index

    def resolve_practice_claim_evidence_binding(self, request: dict[str, object]):
        return deepcopy(self.resolution)

    def resolve_practice_claim_evidence_binding_index(self, request: dict[str, object]):
        return deepcopy(self.index)


class MutatingAuthority(StaticAuthority):
    def resolve_practice_claim_evidence_binding(self, request: dict[str, object]):
        request["practice_claim_id"] = "swapped"
        return deepcopy(self.resolution)


class VolatileResolution(Mapping[str, object]):
    def __init__(self, resolution: dict[str, object]) -> None:
        self.resolution = deepcopy(resolution)
        self.trusted_reads = 0

    def __getitem__(self, key: str) -> object:
        if key == "trusted_approval_ids":
            self.trusted_reads += 1
            if self.trusted_reads > 1:
                return {
                    "practice:practice-claim-1": "tampered",
                    "selection": "tampered",
                }
        return self.resolution[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.resolution)

    def __len__(self) -> int:
        return len(self.resolution)


class VolatileAuthority:
    def __init__(self, resolution: dict[str, object]) -> None:
        self.resolution = VolatileResolution(resolution)

    def resolve_practice_claim_evidence_binding(
        self, request: dict[str, object]
    ) -> Mapping[str, object]:
        return self.resolution


class VolatileIndexResolution(Mapping[str, object]):
    def __init__(self, resolution: dict[str, object]) -> None:
        self.resolution = deepcopy(resolution)
        self.revision_reads = 0

    def __getitem__(self, key: str) -> object:
        if key == "authority_revision_id":
            self.revision_reads += 1
            if self.revision_reads > 1:
                return "tampered-index-revision"
        return self.resolution[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.resolution)

    def __len__(self) -> int:
        return len(self.resolution)


class VolatileIndexAuthority:
    def __init__(self, resolution: dict[str, object]) -> None:
        self.resolution = VolatileIndexResolution(resolution)

    def resolve_practice_claim_evidence_binding_index(
        self, request: dict[str, object]
    ) -> Mapping[str, object]:
        return self.resolution


class VolatileExpectedBinding(Mapping[str, object]):
    def __init__(self, binding: dict[str, object]) -> None:
        self.binding = deepcopy(binding)
        self.binding_sha_reads = 0

    def __getitem__(self, key: str) -> object:
        if key == "practice_binding_sha256":
            self.binding_sha_reads += 1
            if self.binding_sha_reads > 1:
                return "f" * 64
        return self.binding[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.binding)

    def __len__(self) -> int:
        return len(self.binding)


class ExplodingSequence(Sequence[object]):
    def __getitem__(self, index: int) -> object:
        raise RuntimeError("boom")

    def __len__(self) -> int:
        return 1


class ExplodingEquality:
    def __eq__(self, other: object) -> bool:
        raise RuntimeError("equality boom")


class ExplodingSplitString(str):
    def split(self, *args: object, **kwargs: object) -> list[str]:
        raise RuntimeError("split boom")


class RaisingLookupAuthority:
    def __getattribute__(self, name: str) -> object:
        if name.startswith("resolve_practice_claim_evidence_binding"):
            raise RuntimeError("lookup boom")
        return super().__getattribute__(name)


class EqualityMutatingAuthority(StaticAuthority):
    def resolve_practice_claim_evidence_binding(self, request: dict[str, object]):
        request["practice_claim_id"] = ExplodingEquality()
        return deepcopy(self.resolution)

    def resolve_practice_claim_evidence_binding_index(
        self, request: dict[str, object]
    ):
        request["matter_id"] = ExplodingEquality()
        return deepcopy(self.index)


class PracticeBindingModuleTests(unittest.TestCase):
    def test_current_practice_projection_feeds_public_binding_resolver(self) -> None:
        fixture = practice_analysis_tests.TestWordingStagesAndRefresh(
            "test_current_filing_claim_projection_reopens_exact_ready_material"
        )
        fixture.setUp()
        try:
            fixture.review_within_limit()
            practice.record_refresh(
                fixture.workspace,
                as_of="2026-08-27",
                reviewer="И.И. Иванов",
                official_check_ref="Официальные источники перепроверены.",
                now="2026-08-27T11:10:00Z",
            )
            projection = practice.current_filing_claim_projection(
                fixture.workspace,
                claim_id="claim-practice",
                issue_option_id="option-practice",
                now="2026-08-27T11:11:00Z",
            )
            state = projection["claim_state"]
            wording = projection["wording_review"]
            request = build_practice_claim_binding_request(
                matter_id="matter-1",
                draft_id="draft-1",
                sentence_id="sent-0123456789abcdef",
                section_code="legal_position",
                sentence_text=wording["wording_text"],
                claim_id="constitutional-claim-1",
                practice_claim_id=state["claim_id"],
                issue_option_id=projection["issue_option_id"],
                evidence_ids=wording["finding_ids"],
                maximum_supported_inference=state["maximum_permitted_claim"],
            )
            issue_payload = _issue_candidate(
                claim_id=request["claim_id"],
                issue_id=request["issue_option_id"],
                practice_claim_id=request["practice_claim_id"],
                text=request["sentence_text"],
                finding_id=request["evidence_ids"][0],
            )
            issue = issue_candidate_from_dict(issue_payload)
            all_approvals = issue_approval_requests(issue)
            practice_key = f"practice:{request['practice_claim_id']}"
            selected_approvals = {
                practice_key: all_approvals[practice_key],
                "selection": all_approvals["selection"],
            }
            resolution = build_practice_claim_binding_resolution(
                request=request,
                matter_binding={
                    "matter_id": request["matter_id"],
                    "draft_id": request["draft_id"],
                    "case_id": projection["case_id"],
                    "workspace_revision_id": projection["workspace_binding"][
                        "workspace_snapshot_sha256"
                    ],
                    "input_bindings_sha256": state["input_bindings_sha256"],
                },
                practice_state=state,
                ready_binding=projection["ready_binding"],
                research_request=projection["research_request"],
                result=projection["result"],
                findings=projection["findings"],
                wording_review=wording,
                filing_validation=projection["filing_validation"],
                prefiling_refresh=projection["prefiling_refresh"],
                issue_candidate=issue_payload,
                issue_approval_requests=selected_approvals,
                trusted_approval_ids={
                    practice_key: "trusted-approval:sha256:" + "a" * 64,
                    "selection": "trusted-approval:sha256:" + "b" * 64,
                },
                authority_revision_id=(
                    "workspace:"
                    + projection["workspace_binding"]["workspace_snapshot_sha256"]
                ),
                checked_at="2026-08-27T11:12:00Z",
            )

            errors, receipt = resolve_practice_claim_evidence_binding(
                request, StaticAuthority(resolution)
            )

            self.assertEqual(errors, ())
            self.assertIsNotNone(receipt)
            assert receipt is not None
            self.assertEqual(
                receipt["result_handoff_id"], projection["result"]["handoff_id"]
            )
        finally:
            fixture.tearDown()

    def test_valid_closed_projection_emits_receipt(self) -> None:
        request, resolution = _valid_case()

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertEqual(errors, ())
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(receipt["practice_binding_sha256"], request["practice_binding_sha256"])
        self.assertEqual(set(receipt["trusted_approval_ids"]), {"practice:practice-claim-1", "selection"})
        self.assertEqual(receipt["matter_binding"]["workspace_revision_id"], "workspace-revision-1")

    def test_scalar_finding_ids_are_rejected_without_coercion(self) -> None:
        with self.assertRaisesRegex(ValueError, "evidence_ids"):
            build_practice_claim_binding_request(
                matter_id="matter-1", draft_id="draft-1",
                sentence_id="sent-0123456789abcdef", section_code="legal_position",
                sentence_text="Текст.", claim_id="claim-1",
                practice_claim_id="practice-1", issue_option_id="issue-1",
                evidence_ids="0" * 64,
                maximum_supported_inference="bounded",
            )

    def test_authority_cannot_mutate_canonical_request(self) -> None:
        request, resolution = _valid_case()

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, MutatingAuthority(resolution)
        )

        self.assertIn("practice_binding_request_mutated", errors)
        self.assertIsNone(receipt)

    def test_authority_lookup_and_hostile_equality_fail_closed(self) -> None:
        request, resolution = _valid_case()
        for authority in (
            RaisingLookupAuthority(),
            EqualityMutatingAuthority(resolution),
        ):
            with self.subTest(authority=type(authority).__name__):
                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, authority
                )

                self.assertEqual(errors, ("practice_binding_authority_error",))
                self.assertIsNone(receipt)

    def test_authority_resolution_is_snapshotted_before_validation(self) -> None:
        request, resolution = _valid_case()
        expected_ids = deepcopy(resolution["trusted_approval_ids"])

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, VolatileAuthority(resolution)
        )

        self.assertEqual(errors, ())
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(receipt["trusted_approval_ids"], expected_ids)

    def test_result_finding_substitution_is_rejected(self) -> None:
        request, resolution = _valid_case()
        resolution["findings"][0]["finding_id"] = "f" * 64

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertTrue(any("finding" in error for error in errors), errors)
        self.assertIsNone(receipt)

    def test_extra_native_result_finding_is_rejected(self) -> None:
        request, resolution = _valid_case()
        payload = resolution["result"]["payload"]
        extra_finding = deepcopy(payload["findings"][0])
        extra_candidate = deepcopy(extra_finding["candidate"])
        extra_candidate["candidate_id"] = "candidate-2"
        extra_candidate_sha256 = _digest(extra_candidate)
        extra_finding.update(
            {
                "candidate_id": extra_candidate["candidate_id"],
                "candidate_sha256": extra_candidate_sha256,
                "candidate": extra_candidate,
            }
        )
        extra_finding["finding_id"] = _digest(
            {
                "candidate_sha256": extra_candidate_sha256,
                "claim_ids": extra_finding["claim_ids"],
                "normative_bridge_sha256": payload["approval_binding"][
                    "normative_bridge_sha256"
                ],
            }
        )
        payload["findings"].append(extra_finding)
        payload["claim_set_sha256"] = _digest(payload["claim_bindings"])
        _rebind_result_handoff(resolution)

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_result_finding_set_mismatch", errors)
        self.assertIsNone(receipt)

    def test_extra_finding_for_another_bound_claim_is_ignored(self) -> None:
        request, resolution = _valid_case()
        payload = resolution["result"]["payload"]
        foreign_claim_id = "practice-claim-foreign"
        payload["claim_bindings"].append(
            {
                "claim_id": foreign_claim_id,
                "claim_sha256": "0" * 64,
                "source_locator": "claims.json#foreign",
            }
        )
        extra_finding = deepcopy(payload["findings"][0])
        extra_candidate = deepcopy(extra_finding["candidate"])
        extra_candidate["candidate_id"] = "candidate-foreign"
        extra_candidate_sha256 = _digest(extra_candidate)
        extra_finding.update(
            {
                "candidate_id": extra_candidate["candidate_id"],
                "candidate_sha256": extra_candidate_sha256,
                "candidate": extra_candidate,
                "claim_ids": [foreign_claim_id],
            }
        )
        extra_finding["finding_id"] = _digest(
            {
                "candidate_sha256": extra_candidate_sha256,
                "claim_ids": extra_finding["claim_ids"],
                "normative_bridge_sha256": payload["approval_binding"][
                    "normative_bridge_sha256"
                ],
            }
        )
        payload["findings"].append(extra_finding)
        payload["claim_set_sha256"] = _digest(payload["claim_bindings"])
        research_request = resolution["research_request"]
        research_payload = research_request["payload"]
        foreign_question = "Каков смысл по второму связанному требованию?"
        research_payload["questions"].append(foreign_question)
        research_payload["claim_bindings"] = deepcopy(payload["claim_bindings"])
        research_payload["claim_set_sha256"] = payload["claim_set_sha256"]
        research_payload["claim_questions"].append(
            {
                "claim_id": foreign_claim_id,
                "question_id": _digest(
                    {"claim_id": foreign_claim_id, "question": foreign_question}
                ),
                "question": foreign_question,
                "disconfirmation_prompts": ["Найти противоположное прочтение."],
            }
        )
        research_payload["request_sha256"] = _digest(
            {
                "questions": research_payload["questions"],
                "claim_bindings": research_payload["claim_bindings"],
                "claim_set_sha256": research_payload["claim_set_sha256"],
            }
        )
        research_request["plan_sha256"] = research_payload["request_sha256"]
        research_request["handoff_id"] = _digest(
            {
                key: value
                for key, value in research_request.items()
                if key != "handoff_id"
            }
        )
        payload["request_handoff_id"] = research_request["handoff_id"]
        payload["request_sha256"] = research_payload["request_sha256"]
        resolution["practice_state"]["request_id"] = research_request[
            "handoff_id"
        ]
        resolution["wording_review"]["request_id"] = research_request[
            "handoff_id"
        ]
        payload["selected_proofs"]["human_decision"]["candidate_ids"].append(
            extra_candidate["candidate_id"]
        )
        human_decision = payload["selected_proofs"]["human_decision"]
        payload["approval_binding"]["human_decision_sha256"] = _digest(
            human_decision
        )
        for artifact in payload["artifact_manifest"]["files"]:
            if artifact["path"] == "human-decision.json":
                artifact["bytes"] = len(canonical_json_bytes(human_decision))
                artifact["sha256"] = _digest(human_decision)
        payload["artifact_manifest"]["manifest_sha256"] = _digest(
            payload["artifact_manifest"]["files"]
        )
        resolution["wording_review"]["human_decision_sha256"] = payload[
            "approval_binding"
        ]["human_decision_sha256"]
        _rebind_result_handoff(resolution)

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertEqual(errors, ())
        self.assertIsNotNone(receipt)

    def test_non_mapping_projected_finding_is_not_silently_dropped(self) -> None:
        request, resolution = _valid_case()
        resolution["findings"].append("injected")

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_resolution_finding_invalid:2", errors)
        self.assertIsNone(receipt)

    def test_native_finding_and_candidate_wording_bind_exact_sentence(self) -> None:
        request, resolution = _valid_case()
        result_finding = resolution["result"]["payload"]["findings"][0]
        projected_finding = resolution["findings"][0]
        result_finding["claim_wording"] = "Иной, более сильный вывод."
        projected_finding["claim_wording"] = "Иной, более сильный вывод."
        result_finding["candidate"]["claim_wording"] = "Ещё более сильный вывод."
        projected_finding["candidate"]["claim_wording"] = "Ещё более сильный вывод."

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        finding_id = request["evidence_ids"][0]
        self.assertIn(
            f"practice_result_finding_claim_wording_mismatch:{finding_id}",
            errors,
        )
        self.assertIn(
            f"practice_result_finding_candidate_wording_mismatch:{finding_id}",
            errors,
        )
        self.assertIsNone(receipt)

    def test_result_candidate_must_be_human_approved_and_drafting_ready(self) -> None:
        cases = (
            ("human_review", "rejected", "candidate_not_approved"),
            ("drafting_ready", False, "candidate_not_drafting_ready"),
        )
        for field, value, expected in cases:
            with self.subTest(field=field):
                request, resolution = _valid_case()
                resolution["result"]["payload"]["findings"][0]["candidate"][
                    field
                ] = value

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertTrue(any(expected in error for error in errors), errors)
                self.assertIsNone(receipt)

    def test_result_claim_bindings_are_complete_canonical_objects(self) -> None:
        malformed_cases = (
            [None],
            [
                {
                    "claim_id": "practice-claim-1",
                    "claim_sha256": "a" * 64,
                    "source_locator": "claims.json#0",
                },
                {
                    "claim_id": "practice-claim-1",
                    "claim_sha256": "b" * 64,
                    "source_locator": "claims.json#1",
                },
            ],
        )
        for bindings in malformed_cases:
            with self.subTest(bindings=bindings):
                request, resolution = _valid_case()
                payload = resolution["result"]["payload"]
                payload["claim_bindings"] = bindings
                payload["claim_set_sha256"] = _digest(bindings)
                _rebind_result_handoff(resolution)

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertTrue(
                    any("claim_binding" in error for error in errors), errors
                )
                self.assertIsNone(receipt)

    def test_result_proof_bundle_is_recomputed_from_selected_artifacts(self) -> None:
        mutations = {
            "validation": lambda payload: payload["selected_proofs"][
                "validation_report"
            ].update({"valid": False}),
            "manifest": lambda payload: payload["artifact_manifest"]["files"][
                0
            ].update({"sha256": "f" * 64}),
            "quality": lambda payload: payload["quality_bindings"][0][
                "artifact"
            ].update({"tampered": True}),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                request, resolution = _valid_case()
                mutate(resolution["result"]["payload"])
                _rebind_result_handoff(resolution)

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertTrue(
                    any(
                        marker in error
                        for error in errors
                        for marker in (
                            "validation_report",
                            "artifact_manifest",
                            "quality_artifact",
                            "selected_proof",
                        )
                    ),
                    errors,
                )
                self.assertIsNone(receipt)

    def test_result_request_sha_is_bound_to_exact_native_request(self) -> None:
        request, resolution = _valid_case()
        resolution["result"]["payload"]["request_sha256"] = "9" * 64
        _rebind_result_handoff(resolution)

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_result_request_sha256_mismatch", errors)
        self.assertIsNone(receipt)

    def test_research_claim_question_is_content_bound(self) -> None:
        request, resolution = _valid_case()
        research_request = resolution["research_request"]
        research_request["payload"]["claim_questions"][0][
            "question_id"
        ] = "9" * 64
        research_request["handoff_id"] = _digest(
            {
                key: value
                for key, value in research_request.items()
                if key != "handoff_id"
            }
        )
        resolution["result"]["payload"]["request_handoff_id"] = research_request[
            "handoff_id"
        ]
        resolution["practice_state"]["request_id"] = research_request[
            "handoff_id"
        ]
        resolution["wording_review"]["request_id"] = research_request[
            "handoff_id"
        ]
        _rebind_result_handoff(resolution)

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn(
            "practice_research_request_claim_question_id_mismatch:1", errors
        )
        self.assertIsNone(receipt)

    def test_native_material_identifiers_are_required(self) -> None:
        for field in ("source_locator", "request_id"):
            with self.subTest(field=field):
                request, resolution = _valid_case()
                state = resolution["practice_state"]
                filing_state = resolution["filing_validation"]["state"]["claims"][0]
                if field == "source_locator":
                    state[field] = None
                    filing_state[field] = None
                    resolution["result"]["payload"]["claim_bindings"][0][
                        "source_locator"
                    ] = "None"
                else:
                    state[field] = None
                    filing_state[field] = None
                    state["wording_review"]["request_id"] = None
                    filing_state["wording_review"]["request_id"] = None
                    resolution["wording_review"]["request_id"] = None
                    resolution["result"]["payload"]["request_handoff_id"] = None
                _rebind_result_handoff(resolution)

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertTrue(
                    any(field in error and "invalid" in error for error in errors),
                    errors,
                )
                self.assertIsNone(receipt)

    def test_option_ids_require_a_list_of_nonempty_identifiers(self) -> None:
        for malformed in ("issue-option-1", 7, [""]):
            with self.subTest(malformed=malformed):
                request, resolution = _valid_case()
                resolution["practice_state"]["option_ids"] = malformed
                resolution["filing_validation"]["state"]["claims"][0][
                    "option_ids"
                ] = deepcopy(malformed)

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertTrue(
                    any("option_ids" in error for error in errors), errors
                )
                self.assertIsNone(receipt)

    def test_position_card_ids_require_list_containers(self) -> None:
        for scope in ("payload", "finding"):
            for field in (
                "supporting_position_card_ids",
                "adverse_position_card_ids",
            ):
                with self.subTest(scope=scope, field=field):
                    request, resolution = _valid_case()
                    payload = resolution["result"]["payload"]
                    if scope == "payload":
                        payload[field] = "position-1"
                    else:
                        payload["findings"][0][field] = "position-1"
                        resolution["findings"][0][field] = "position-1"
                    _rebind_result_handoff(resolution)

                    errors, receipt = resolve_practice_claim_evidence_binding(
                        request, StaticAuthority(resolution)
                    )

                    self.assertTrue(
                        any("position_card_ids" in error for error in errors), errors
                    )
                    self.assertIsNone(receipt)

    def test_malformed_resolution_never_escapes_validation(self) -> None:
        request, resolution = _valid_case()
        resolution["result"]["payload"]["findings"][0]["candidate"][
            "opaque"
        ] = object()

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertEqual(errors, ("practice_binding_resolution_validation_error",))
        self.assertIsNone(receipt)

    def test_selection_approval_is_independently_required(self) -> None:
        request, resolution = _valid_case()
        resolution["trusted_approval_ids"].pop("selection")

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_issue_trusted_approval_ids_mismatch", errors)
        self.assertIsNone(receipt)

    def test_practice_approval_is_independently_required(self) -> None:
        request, resolution = _valid_case()
        resolution["trusted_approval_ids"].pop(
            f"practice:{request['practice_claim_id']}"
        )

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_issue_trusted_approval_ids_mismatch", errors)
        self.assertIsNone(receipt)

    def test_practice_and_selection_approvals_must_be_distinct(self) -> None:
        request, resolution = _valid_case()
        practice_key = f"practice:{request['practice_claim_id']}"
        resolution["trusted_approval_ids"]["selection"] = resolution[
            "trusted_approval_ids"
        ][practice_key]

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_issue_trusted_approval_ids_not_distinct", errors)
        self.assertIsNone(receipt)

    def test_wrong_matter_workspace_resolution_is_rejected(self) -> None:
        request, resolution = _valid_case()
        resolution["matter_binding"]["matter_id"] = "matter-2"

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_matter_binding_matter_id_mismatch", errors)
        self.assertIsNone(receipt)

    def test_stale_refresh_cannot_predate_current_native_events(self) -> None:
        request, resolution = _valid_case()
        stale_record = deepcopy(resolution["prefiling_refresh"]["record"])
        stale_record.update(
            {
                "as_of": "2000-01-01",
                "corpus_cutoff": "2000-01-01",
                "recorded_at": "2000-01-01T00:00:00Z",
            }
        )
        resolution["prefiling_refresh"]["record"] = stale_record
        resolution["filing_validation"]["state"]["prefiling_refresh"] = deepcopy(
            resolution["prefiling_refresh"]
        )
        resolution["filing_validation"]["validated_at"] = "2000-01-01T00:01:00Z"
        resolution["checked_at"] = "2000-01-01T00:02:00Z"

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_binding_timestamp_order_invalid", errors)
        self.assertIsNone(receipt)

    def test_projected_ledger_events_are_content_bound(self) -> None:
        for scope in ("wording", "refresh"):
            with self.subTest(scope=scope):
                request, resolution = _valid_case()
                if scope == "wording":
                    resolution["wording_review"]["reason"] = "Подменённое основание."
                else:
                    record = resolution["prefiling_refresh"]["record"]
                    record["official_check_ref"] = "Подменённая перепроверка."
                    resolution["filing_validation"]["state"][
                        "prefiling_refresh"
                    ] = deepcopy(resolution["prefiling_refresh"])

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertTrue(
                    any("event_sha256_mismatch" in error for error in errors),
                    errors,
                )
                self.assertIsNone(receipt)

    def test_refresh_requires_identified_human_and_official_check(self) -> None:
        for field in ("reviewer", "official_check_ref"):
            with self.subTest(field=field):
                request, resolution = _valid_case()
                record = resolution["prefiling_refresh"]["record"]
                record[field] = ""
                record["event_sha256"] = _digest(
                    {
                        key: value
                        for key, value in record.items()
                        if key != "event_sha256"
                    }
                )
                resolution["filing_validation"]["state"][
                    "prefiling_refresh"
                ] = deepcopy(resolution["prefiling_refresh"])

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertIn(
                    f"practice_prefiling_refresh_{field}_invalid", errors
                )
                self.assertIsNone(receipt)

    def test_wording_review_source_sha_tracks_current_claim_source(self) -> None:
        request, resolution = _valid_case()
        resolution["wording_review"]["wording_source_sha256"] = "0" * 64

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn(
            "practice_wording_review_binding_mismatch:wording_source_sha256",
            errors,
        )
        self.assertIsNone(receipt)

    def test_result_created_at_is_bound_to_native_state(self) -> None:
        request, resolution = _valid_case()
        resolution["result"]["created_at"] = "2026-09-01T09:31:00Z"
        _rebind_result_handoff(resolution)

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_result_created_at_state_mismatch", errors)
        self.assertIsNone(receipt)

    def test_research_request_precedes_attachment_and_result(self) -> None:
        request, resolution = _valid_case()
        research_request = resolution["research_request"]
        research_request["created_at"] = "2026-09-01T10:30:00Z"
        research_request["handoff_id"] = _digest(
            {
                key: value
                for key, value in research_request.items()
                if key != "handoff_id"
            }
        )
        result_payload = resolution["result"]["payload"]
        result_payload["request_handoff_id"] = research_request["handoff_id"]
        resolution["practice_state"]["request_id"] = research_request[
            "handoff_id"
        ]
        resolution["wording_review"]["request_id"] = research_request[
            "handoff_id"
        ]
        _rebind_result_handoff(resolution)

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_result_request_timestamp_order_invalid", errors)
        self.assertIsNone(receipt)

    def test_result_approval_metadata_and_timeline_are_validated(self) -> None:
        cases = (
            ("reviewer", "", "practice_result_approval_reviewer_invalid"),
            ("approved_at", "not-a-date", "practice_result_approval_approved_at_invalid"),
            (
                "approved_at",
                "2026-09-01T09:31:00Z",
                "practice_result_approval_timestamp_order_invalid",
            ),
        )
        for field, malformed, expected_error in cases:
            with self.subTest(field=field, malformed=malformed):
                request, resolution = _valid_case()
                resolution["result"]["payload"]["approval_binding"][
                    field
                ] = malformed
                _rebind_result_handoff(resolution)

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertIn(expected_error, errors)
                self.assertIsNone(receipt)

    def test_unexpected_non_string_field_names_fail_closed(self) -> None:
        request, resolution = _valid_case()
        malformed = dict(request)
        malformed[1] = "non-string"
        malformed["unexpected"] = "extra"

        errors, receipt = resolve_practice_claim_evidence_binding(
            malformed, StaticAuthority(resolution)
        )

        self.assertIn("practice_binding_request_field_name_invalid", errors)
        self.assertIsNone(receipt)

    def test_wording_and_inference_substitution_are_rejected(self) -> None:
        request, baseline = _valid_case()
        cases = {
            "wording": lambda value: value["wording_review"].update(
                {"wording_text": "Более сильная формулировка."}
            ),
            "maximum": lambda value: value["practice_state"].update(
                {"maximum_permitted_claim": "unbounded_generalization"}
            ),
        }
        for label, mutate in cases.items():
            with self.subTest(case=label):
                resolution = deepcopy(baseline)
                mutate(resolution)

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertTrue(
                    any(
                        marker in error
                        for error in errors
                        for marker in ("wording", "maximum")
                    ),
                    errors,
                )
                self.assertIsNone(receipt)

    def test_cross_claim_finding_is_rejected(self) -> None:
        request, resolution = _valid_case()
        resolution["result"]["payload"]["findings"][0]["claim_ids"] = [
            "foreign-practice-claim"
        ]
        resolution["findings"][0]["claim_ids"] = ["foreign-practice-claim"]

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertTrue(any("foreign_claim" in error for error in errors), errors)
        self.assertTrue(any("unbound_claim" in error for error in errors), errors)
        self.assertIsNone(receipt)

    def test_target_claim_must_be_ready_even_when_report_is_current(self) -> None:
        request, resolution = _valid_case()
        resolution["practice_state"]["state"] = "stale"
        resolution["practice_state"]["draft_blocked"] = True

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_state_not_ready", errors)
        self.assertIsNone(receipt)

    def test_filing_claim_id_projections_reject_scalar_strings(self) -> None:
        request, resolution = _valid_case()
        target_id = request["practice_claim_id"]
        for projection in (resolution["filing_validation"], resolution["filing_validation"]["state"]):
            projection["allowed_claim_ids"] = target_id

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_filing_allowed_claim_ids_invalid", errors)
        self.assertIsNone(receipt)

    def test_unrelated_blocked_claim_does_not_block_ready_target(self) -> None:
        request, resolution = _valid_case()
        other = deepcopy(resolution["practice_state"])
        other.update(
            {
                "claim_id": "practice-claim-10",
                "state": "blocked",
                "draft_blocked": True,
                "blocking_reasons": ["wording_review_required"],
                "option_ids": ["unrelated-issue"],
            }
        )
        filing = resolution["filing_validation"]
        filing.update(
            {
                "valid": False,
                "errors": ["blocking_empirical_overclaim:practice-claim-10:blocked"],
                "blocked_claim_ids": ["practice-claim-10"],
            }
        )
        filing["state"].update(
            {
                "claims": [resolution["practice_state"], other],
                "stage_verdict": "partial",
                "blocked_claim_ids": ["practice-claim-10"],
                "counts_by_state": {
                    "not_required": 0, "required": 0, "running": 0,
                    "blocked": 1, "ready": 1, "stale": 0,
                },
            }
        )

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertEqual(errors, ())
        self.assertIsNotNone(receipt)

    def test_not_required_claim_is_both_allowed_and_unaffected(self) -> None:
        request, resolution = _valid_case()
        other = deepcopy(resolution["practice_state"])
        other.update(
            {
                "claim_id": "practice-claim-10",
                "state": "not_required",
                "draft_blocked": False,
                "option_ids": ["unrelated-issue"],
            }
        )
        filing = resolution["filing_validation"]
        filing.update(
            {
                "allowed_claim_ids": [
                    request["practice_claim_id"],
                    other["claim_id"],
                ],
                "unaffected_claim_ids": [other["claim_id"]],
            }
        )
        filing["state"].update(
            {
                "claims": [resolution["practice_state"], other],
                "allowed_claim_ids": filing["allowed_claim_ids"],
                "unaffected_claim_ids": filing["unaffected_claim_ids"],
                "counts_by_state": {
                    "not_required": 1,
                    "required": 0,
                    "running": 0,
                    "blocked": 0,
                    "ready": 1,
                    "stale": 0,
                },
            }
        )

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertEqual(errors, ())
        self.assertIsNotNone(receipt)

    def test_foreign_ready_claim_requires_complete_native_material(self) -> None:
        request, resolution = _valid_case()
        other = deepcopy(resolution["practice_state"])
        other.update(
            {
                "claim_id": "practice-claim-10",
                "source_locator": None,
                "source_file_sha256": None,
                "request_id": None,
                "wording_reviewed_at": "not-a-time",
                "option_ids": ["unrelated-issue"],
            }
        )
        filing = resolution["filing_validation"]
        filing["allowed_claim_ids"] = [request["practice_claim_id"], other["claim_id"]]
        filing["state"].update(
            {
                "claims": [resolution["practice_state"], other],
                "allowed_claim_ids": filing["allowed_claim_ids"],
                "counts_by_state": {
                    "not_required": 0,
                    "required": 0,
                    "running": 0,
                    "blocked": 0,
                    "ready": 2,
                    "stale": 0,
                },
            }
        )
        foreign_ready = deepcopy(resolution["ready_binding"])
        for field in foreign_ready:
            if field in other:
                foreign_ready[field] = deepcopy(other[field])
        refresh = resolution["prefiling_refresh"]
        refresh["record"]["ready_claim_bindings"].append(foreign_ready)
        refresh["record"]["ready_claim_set_sha256"] = _digest(
            refresh["record"]["ready_claim_bindings"]
        )
        refresh["ready_claim_set_sha256"] = refresh["record"][
            "ready_claim_set_sha256"
        ]
        refresh["record"]["event_sha256"] = _digest(
            {
                key: value
                for key, value in refresh["record"].items()
                if key != "event_sha256"
            }
        )
        filing["state"]["prefiling_refresh"] = deepcopy(refresh)

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertTrue(
            any("practice_filing_ready_claim" in error for error in errors),
            errors,
        )
        self.assertIsNone(receipt)

    def test_refresh_follows_material_events_of_every_ready_claim(self) -> None:
        request, resolution = _valid_case()
        other = deepcopy(resolution["practice_state"])
        other.update(
            {
                "claim_id": "practice-claim-10",
                "wording_reviewed_at": "2026-09-01T10:30:00Z",
                "option_ids": ["unrelated-issue"],
            }
        )
        other_wording = other["wording_review"]
        other_wording["claim_id"] = other["claim_id"]
        other_wording["reviewed_at"] = other["wording_reviewed_at"]
        other_wording["event_sha256"] = _digest(
            {
                key: value
                for key, value in other_wording.items()
                if key != "event_sha256"
            }
        )
        other["wording_review_event_sha256"] = other_wording["event_sha256"]
        filing = resolution["filing_validation"]
        filing["allowed_claim_ids"] = [request["practice_claim_id"], other["claim_id"]]
        filing["state"].update(
            {
                "claims": [resolution["practice_state"], other],
                "allowed_claim_ids": filing["allowed_claim_ids"],
                "counts_by_state": {
                    "not_required": 0,
                    "required": 0,
                    "running": 0,
                    "blocked": 0,
                    "ready": 2,
                    "stale": 0,
                },
            }
        )
        foreign_ready = deepcopy(resolution["ready_binding"])
        for field in foreign_ready:
            if field in other:
                foreign_ready[field] = deepcopy(other[field])
        refresh = resolution["prefiling_refresh"]
        refresh["record"]["ready_claim_bindings"].append(foreign_ready)
        refresh["record"]["ready_claim_set_sha256"] = _digest(
            refresh["record"]["ready_claim_bindings"]
        )
        refresh["ready_claim_set_sha256"] = refresh["record"][
            "ready_claim_set_sha256"
        ]
        refresh["record"]["event_sha256"] = _digest(
            {
                key: value
                for key, value in refresh["record"].items()
                if key != "event_sha256"
            }
        )
        filing["state"]["prefiling_refresh"] = deepcopy(refresh)

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_binding_timestamp_order_invalid", errors)
        self.assertIsNone(receipt)

    def test_filing_lists_counts_and_sibling_blocking_are_derived(self) -> None:
        mutations = {
            "counts": lambda resolution: resolution["filing_validation"][
                "state"
            ]["counts_by_state"].update({"ready": 0}),
            "list": lambda resolution: (
                resolution["filing_validation"]["allowed_claim_ids"].append(
                    "phantom-claim"
                ),
                resolution["filing_validation"]["state"][
                    "allowed_claim_ids"
                ].append("phantom-claim"),
            ),
            "sibling": lambda resolution: resolution["filing_validation"][
                "state"
            ]["claims"].append(
                {
                    **deepcopy(resolution["practice_state"]),
                    "claim_id": "practice-claim-10",
                    "state": "blocked",
                    "draft_blocked": False,
                    "option_ids": ["unrelated-issue"],
                }
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                request, resolution = _valid_case()
                mutate(resolution)

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertTrue(
                    any(
                        marker in error
                        for error in errors
                        for marker in (
                            "counts_by_state",
                            "derivation_mismatch",
                            "draft_blocked_mismatch",
                        )
                    ),
                    errors,
                )
                self.assertIsNone(receipt)

    def test_filing_input_file_hashes_have_native_types(self) -> None:
        cases = (
            ("case_file_sha256", None, "case_file_sha256_invalid"),
            ("case_file_sha256", False, "case_file_sha256_invalid"),
            (
                "argument_research_sha256",
                False,
                "argument_research_sha256_invalid",
            ),
            (
                "argument_research_sha256",
                "x",
                "argument_research_sha256_invalid",
            ),
        )
        for field, malformed, expected in cases:
            with self.subTest(field=field, malformed=malformed):
                request, resolution = _valid_case()
                resolution["filing_validation"]["state"]["input_bindings"][
                    field
                ] = malformed

                errors, receipt = resolve_practice_claim_evidence_binding(
                    request, StaticAuthority(resolution)
                )

                self.assertTrue(any(expected in error for error in errors), errors)
                self.assertIsNone(receipt)

    def test_partial_filing_cannot_claim_global_validity(self) -> None:
        request, resolution = _valid_case()
        other = deepcopy(resolution["practice_state"])
        other.update(
            {
                "claim_id": "practice-claim-10",
                "state": "blocked",
                "draft_blocked": True,
                "blocking_reasons": ["wording_review_required"],
                "option_ids": ["unrelated-issue"],
            }
        )
        filing = resolution["filing_validation"]
        filing.update(
            {
                "valid": True,
                "errors": ["blocking_empirical_overclaim:practice-claim-10:blocked"],
                "blocked_claim_ids": ["practice-claim-10"],
            }
        )
        filing["state"].update(
            {
                "claims": [resolution["practice_state"], other],
                "stage_verdict": "partial",
                "blocked_claim_ids": ["practice-claim-10"],
                "counts_by_state": {
                    "not_required": 0,
                    "required": 0,
                    "running": 0,
                    "blocked": 1,
                    "ready": 1,
                    "stale": 0,
                },
            }
        )

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_filing_validation_validity_mismatch", errors)
        self.assertIsNone(receipt)

    def test_invalid_filing_validation_never_issues_receipt(self) -> None:
        request, resolution = _valid_case()
        resolution["filing_validation"]["valid"] = False

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_filing_validation_not_valid", errors)
        self.assertIsNone(receipt)

    def test_blocked_filing_stage_never_issues_receipt(self) -> None:
        request, resolution = _valid_case()
        resolution["filing_validation"]["state"]["stage_verdict"] = "blocked"

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertIn("practice_filing_state_verdict_blocked", errors)
        self.assertIsNone(receipt)

    def test_refresh_must_bind_complete_ready_claim_set(self) -> None:
        request, resolution = _valid_case()
        resolution["prefiling_refresh"]["record"]["ready_claim_bindings"] = []

        errors, receipt = resolve_practice_claim_evidence_binding(
            request, StaticAuthority(resolution)
        )

        self.assertTrue(any("refresh" in error for error in errors), errors)
        self.assertIsNone(receipt)

    def test_complete_empty_index_is_mandatory_and_exact(self) -> None:
        index = build_practice_claim_binding_index_resolution(
            matter_id="matter-1", draft_id="draft-1", bindings=[],
            authority_revision_id="practice-index-revision-1",
            checked_at="2026-09-01T09:53:00Z",
        )
        authority = StaticAuthority({}, index)

        errors, receipt = resolve_practice_claim_evidence_binding_index(
            matter_id="matter-1", draft_id="draft-1", expected_bindings=[], authority=authority
        )
        mismatch, missing = resolve_practice_claim_evidence_binding_index(
            matter_id="matter-1",
            draft_id="draft-1",
            expected_bindings=[{
                "sentence_id": "sent-0123456789abcdef",
                "section_code": "legal_position",
                "role": "practice_claim",
                "claim_id": "claim-1",
                "practice_claim_id": "practice-1",
                "issue_option_id": "issue-1",
                "practice_binding_sha256": "0" * 64,
            }],
            authority=authority,
        )

        self.assertEqual(errors, ())
        self.assertEqual(receipt["bindings"], [])
        self.assertIn("practice_binding_index_set_mismatch", mismatch)
        self.assertIsNone(missing)

    def test_index_resolution_is_snapshotted_before_validation(self) -> None:
        index = build_practice_claim_binding_index_resolution(
            matter_id="matter-1",
            draft_id="draft-1",
            bindings=[],
            authority_revision_id="practice-index-revision-1",
            checked_at="2026-09-01T09:53:00Z",
        )

        errors, receipt = resolve_practice_claim_evidence_binding_index(
            matter_id="matter-1",
            draft_id="draft-1",
            expected_bindings=[],
            authority=VolatileIndexAuthority(index),
        )

        self.assertEqual(errors, ())
        self.assertEqual(
            receipt["authority_revision_id"], "practice-index-revision-1"
        )

    def test_expected_index_binding_is_snapshotted_before_validation(self) -> None:
        request, _ = _valid_case()
        binding = {
            "sentence_id": request["sentence_id"],
            "section_code": request["section_code"],
            "role": "practice_claim",
            "claim_id": request["claim_id"],
            "practice_claim_id": request["practice_claim_id"],
            "issue_option_id": request["issue_option_id"],
            "practice_binding_sha256": request["practice_binding_sha256"],
        }
        index = build_practice_claim_binding_index_resolution(
            matter_id="matter-1",
            draft_id="draft-1",
            bindings=[binding],
            authority_revision_id="practice-index-revision-1",
            checked_at="2026-09-01T09:53:00Z",
        )

        errors, receipt = resolve_practice_claim_evidence_binding_index(
            matter_id="matter-1",
            draft_id="draft-1",
            expected_bindings=[VolatileExpectedBinding(binding)],
            authority=StaticAuthority({}, index),
        )

        self.assertEqual(errors, ())
        self.assertEqual(receipt["bindings"], [binding])

    def test_hostile_index_sequences_and_authorities_fail_closed(self) -> None:
        index = build_practice_claim_binding_index_resolution(
            matter_id="matter-1",
            draft_id="draft-1",
            bindings=[],
            authority_revision_id="practice-index-revision-1",
            checked_at="2026-09-01T09:53:00Z",
        )
        cases = (
            (
                ExplodingSequence(),
                StaticAuthority({}, index),
                "practice_binding_index_expected_snapshot_error",
            ),
            (
                [],
                RaisingLookupAuthority(),
                "practice_binding_index_authority_error",
            ),
            (
                [],
                EqualityMutatingAuthority({}, index),
                "practice_binding_index_authority_error",
            ),
        )
        for expected, authority, error in cases:
            with self.subTest(error=error):
                errors, receipt = resolve_practice_claim_evidence_binding_index(
                    matter_id="matter-1",
                    draft_id="draft-1",
                    expected_bindings=expected,
                    authority=authority,
                )

                self.assertEqual(errors, (error,))
                self.assertIsNone(receipt)

        malformed_index = deepcopy(index)
        malformed_index["bindings"] = ExplodingSequence()
        errors, receipt = resolve_practice_claim_evidence_binding_index(
            matter_id="matter-1",
            draft_id="draft-1",
            expected_bindings=[],
            authority=StaticAuthority({}, malformed_index),
        )
        self.assertEqual(
            errors, ("practice_binding_index_resolution_snapshot_error",)
        )
        self.assertIsNone(receipt)

        errors, receipt = resolve_practice_claim_evidence_binding_index(
            matter_id=ExplodingSplitString("matter-1"),
            draft_id="draft-1",
            expected_bindings=[],
            authority=None,
        )
        self.assertEqual(
            errors, ("practice_binding_index_input_validation_error",)
        )
        self.assertIsNone(receipt)


if __name__ == "__main__":
    unittest.main()
