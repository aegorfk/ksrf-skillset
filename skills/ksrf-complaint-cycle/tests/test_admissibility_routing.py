# pyright: reportMissingImports=false, reportMissingModuleSource=false
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator


SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = SKILL_ROOT / "lib"
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))

from ksrf.filing.admissibility import (  # noqa: E402
    CANONICAL_GATE_IDS,
    AdmissibilityContractError,
    derive_route_recommendation,
    validate_admissibility_matrix,
)
from ksrf.filing.matter import initialize_matter  # noqa: E402
from ksrf.filing.issue_options import (  # noqa: E402
    issue_candidate_content_fingerprint,
    issue_candidate_from_dict,
)
from ksrf.filing.workflow import (  # noqa: E402
    WorkflowInputError,
    WorkflowRouter,
    workflow_exit_code,
)


SCHEMA_ROOT = SKILL_ROOT / "schemas" / "ksrf_filing"
MATRIX_SCHEMA_PATH = SCHEMA_ROOT / "admissibility-matrix.v1.schema.json"
RECOMMENDATION_SCHEMA_PATH = (
    SCHEMA_ROOT / "ksrf-route-recommendation.v1.schema.json"
)
MATRIX_TEMPLATE_PATH = (
    SKILL_ROOT / "references" / "admissibility-matrix-template.v1.json"
)
CHECKED_AT = "2026-09-02T00:00:00Z"
OFFICIAL_EVIDENCE_ID = "official-fkz-current"


def _canonical_issue_fingerprint(
    *, issue_id: str = "issue-option-1", claim_id: str = "claim-1"
) -> str:
    candidate = issue_candidate_from_dict(
        {
            "schema_version": "1.0.0",
            "issue_id": issue_id,
            "claim_id": claim_id,
        }
    )
    return issue_candidate_content_fingerprint(candidate)


def _gate(gate_id: str) -> dict[str, object]:
    gate: dict[str, object] = {
        "gate_id": gate_id,
        "status": "pass",
        "rationale": f"Порог {gate_id} подтверждён исследователем.",
        "applicability_reason": "Порог применим к индивидуальной жалобе.",
        "evidence_ids": [f"evidence-{gate_id}"],
        "official_rule_evidence_ids": [OFFICIAL_EVIDENCE_ID],
        "official_checked_at": CHECKED_AT,
        "curability": "not_applicable",
        "record_availability": "available",
        "next_action": None,
        "disposition": None,
    }
    if gate_id == "competence_and_route":
        gate["disposition"] = "individual_complaint"
    elif gate_id == "case_status":
        gate["disposition"] = "completed"
    elif gate_id == "permissible_remedy":
        gate["disposition"] = "viable"
    return gate


def _matrix() -> dict[str, object]:
    return {
        "$schema": (
            "https://example.local/schemas/ksrf_filing/"
            "admissibility-matrix.v1.schema.json"
        ),
        "schema_version": "1.0.0",
        "artifact_type": "AdmissibilityMatrix",
        "matrix_id": "matrix-case-1-claim-1",
        "matter_id": "matter-case-1",
        "claim_id": "claim-1",
        "official_rule_snapshot": {
            "status": "verified_current",
            "checked_at": CHECKED_AT,
            "evidence_ids": [OFFICIAL_EVIDENCE_ID],
        },
        "gates": [_gate(gate_id) for gate_id in CANONICAL_GATE_IDS],
        "route_context": {
            "issue_assessment_status": "complete",
            "option_bindings": [
                {
                    "option_id": "issue-option-1",
                    "content_fingerprint": _canonical_issue_fingerprint(),
                    "readiness": "viable",
                    "evidence_ids": ["issue-evidence-1"],
                }
            ],
            "preferred_option_id": "issue-option-1",
            "reserve_option_ids": [],
            "expected_client_benefit": "Получить проверку нормативного смысла.",
            "adverse_risks": ["Возможен отказ в принятии обращения."],
            "alternatives_and_deadlines": ["Проверить ближайший процессуальный срок."],
            "next_actions_in_order": ["Передать рекомендацию юристу на проверку."],
            "reconsideration_conditions": ["Появление нового официального акта."],
        },
    }


def _gate_by_id(matrix: dict[str, object], gate_id: str) -> dict[str, object]:
    gates = matrix["gates"]
    assert isinstance(gates, list)
    return next(gate for gate in gates if gate["gate_id"] == gate_id)


def _issue_generation_payload(*, claim_id: str = "claim-1") -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "seeds": [
            {
                "seed_id": "seed-admissibility-1",
                "claim_id": claim_id,
                "norm_id": "norm-1",
                "norm_version_id": "norm-version-1",
                "theory_code": "legal_uncertainty",
                "normative_meaning": "Проверяемый нормативный смысл.",
                "application_evidence_ids": ["issue-evidence-1"],
                "application_gate_passed": False,
                "constitutional_benchmarks": ["ст. 19 Конституции РФ"],
                "rights_impairment": "Неравное применение нормы.",
                "anti_fourth_instance_boundary": "Оспаривается смысл нормы.",
                "ksrf_authority_ids": ["ksrf-authority-1"],
                "adverse_authority_ids": [],
                "adverse_authority_summary": "Неблагоприятная практика не закрыта.",
                "adverse_authority_delta": "Отличие требует проверки.",
                "requested_remedy": "Проверить конституционный смысл нормы.",
                "strengths": ["Есть проверяемая нормативная проблема."],
                "weaknesses": ["Не завершена независимая проверка."],
                "source_gaps": ["Нужно подтвердить официальные опоры."],
                "model_rank": 1,
                "anti_fourth_instance_gate": {
                    "state": "unknown",
                    "rationale": "Нужна проверка.",
                    "evidence_ids": ["issue-evidence-1"],
                },
                "adverse_authority_gate": {
                    "state": "unknown",
                    "rationale": "Нужна проверка.",
                    "evidence_ids": ["ksrf-authority-1"],
                },
                "remedy_gate": {
                    "state": "unknown",
                    "rationale": "Нужна проверка.",
                    "evidence_ids": ["issue-evidence-1"],
                },
                "human_selection": {
                    "state": "pending",
                    "note": "Решение человека ещё не принято.",
                },
            }
        ],
    }


class AdmissibilitySchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix_schema = json.loads(MATRIX_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.recommendation_schema = json.loads(
            RECOMMENDATION_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(cls.matrix_schema)
        Draft202012Validator.check_schema(cls.recommendation_schema)

    def test_matrix_schema_accepts_complete_contract(self) -> None:
        errors = list(
            Draft202012Validator(self.matrix_schema).iter_errors(_matrix())
        )
        self.assertEqual(errors, [])

    def test_installed_template_is_valid_and_fail_closed(self) -> None:
        template = json.loads(MATRIX_TEMPLATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            list(Draft202012Validator(self.matrix_schema).iter_errors(template)),
            [],
        )
        recommendation = derive_route_recommendation(
            template,
            current_official_evidence_ids=(),
        )
        self.assertEqual(
            recommendation["decision"],
            "ABSTAIN_PENDING_RECORD",
        )
        self.assertNotEqual(recommendation["decision"], "GO_TO_KSRF")

    def test_matrix_schema_rejects_missing_gate_and_unsupported_na(self) -> None:
        missing = _matrix()
        gates = missing["gates"]
        assert isinstance(gates, list)
        gates.pop()
        self.assertTrue(
            list(Draft202012Validator(self.matrix_schema).iter_errors(missing))
        )

        unsupported = _matrix()
        gate = _gate_by_id(unsupported, "continuing_legal_effect")
        gate.update(
            status="not_applicable",
            applicability_reason="",
            evidence_ids=[],
            official_rule_evidence_ids=[],
        )
        self.assertTrue(
            list(Draft202012Validator(self.matrix_schema).iter_errors(unsupported))
        )

    def test_matrix_schema_rejects_disposition_status_mismatch(self) -> None:
        mismatched_route = _matrix()
        _gate_by_id(mismatched_route, "competence_and_route")["disposition"] = (
            "ordinary_process"
        )
        self.assertTrue(
            list(
                Draft202012Validator(self.matrix_schema).iter_errors(
                    mismatched_route
                )
            )
        )

        mismatched_remedy = _matrix()
        _gate_by_id(mismatched_remedy, "permissible_remedy")["disposition"] = (
            "not_viable"
        )
        self.assertTrue(
            list(
                Draft202012Validator(self.matrix_schema).iter_errors(
                    mismatched_remedy
                )
            )
        )

        active_individual = _matrix()
        _gate_by_id(active_individual, "case_status")["disposition"] = "active"
        self.assertTrue(
            list(
                Draft202012Validator(self.matrix_schema).iter_errors(
                    active_individual
                )
            )
        )


class AdmissibilityDomainTests(unittest.TestCase):
    def assert_decision(
        self,
        matrix: dict[str, object],
        expected: str,
        *,
        current_official: tuple[str, ...] = (OFFICIAL_EVIDENCE_ID,),
    ) -> dict[str, object]:
        recommendation = derive_route_recommendation(
            matrix,
            current_official_evidence_ids=current_official,
        )
        self.assertEqual(recommendation["decision"], expected)
        self.assertEqual(recommendation["human_decision"], "pending")
        self.assertTrue(recommendation["human_legal_review_required"])
        self.assertFalse(recommendation["legal_assessment_automated"])
        self.assertFalse(recommendation["filing_authority"])
        self.assertFalse(recommendation["filing_performed"])
        self.assertNotIn("score", recommendation)
        errors = list(
            Draft202012Validator(
                AdmissibilitySchemaTests.recommendation_schema
            ).iter_errors(recommendation)
        )
        self.assertEqual(errors, [])
        return recommendation

    def test_validation_is_exact_and_deterministic(self) -> None:
        first = validate_admissibility_matrix(_matrix())
        second = validate_admissibility_matrix(copy.deepcopy(_matrix()))
        self.assertEqual(first, second)
        self.assertEqual(
            tuple(gate["gate_id"] for gate in first["gates"]),
            CANONICAL_GATE_IDS,
        )

        duplicated = _matrix()
        gates = duplicated["gates"]
        assert isinstance(gates, list)
        gates[-1] = copy.deepcopy(gates[0])
        with self.assertRaisesRegex(AdmissibilityContractError, "дублируется|отсутствует"):
            validate_admissibility_matrix(duplicated)

    def test_missing_or_invalid_check_time_is_rejected(self) -> None:
        missing = _matrix()
        snapshot = missing["official_rule_snapshot"]
        assert isinstance(snapshot, dict)
        snapshot.pop("checked_at")
        with self.assertRaisesRegex(AdmissibilityContractError, "checked_at"):
            validate_admissibility_matrix(missing)

        invalid = _matrix()
        _gate_by_id(invalid, "one_year_deadline")["official_checked_at"] = "yesterday"
        with self.assertRaisesRegex(AdmissibilityContractError, "official_checked_at"):
            validate_admissibility_matrix(invalid)

    def test_all_pass_requires_viable_issue_and_remedy_for_go(self) -> None:
        recommendation = self.assert_decision(_matrix(), "GO_TO_KSRF")
        self.assertEqual(len(recommendation["decisive_gate_evidence"]), 12)
        self.assertTrue(
            all(
                item["evidence_ids"]
                for item in recommendation["decisive_gate_evidence"]
            )
        )

        incomplete = _matrix()
        context = incomplete["route_context"]
        assert isinstance(context, dict)
        context.update(
            issue_assessment_status="not_started",
            option_bindings=[],
            preferred_option_id=None,
        )
        self.assert_decision(incomplete, "FIX_FIRST")

    def test_unknown_never_becomes_go_or_no_go(self) -> None:
        controlled = _matrix()
        _gate_by_id(controlled, "one_year_deadline").update(
            status="unknown",
            rationale="Исходная дата пока не подтверждена.",
            evidence_ids=["deadline-source-search-attempt"],
            curability="curable",
            record_availability="controlled_retrieval",
            next_action="Получить завершающий судебный акт.",
        )
        recommendation = self.assert_decision(controlled, "FIX_FIRST")
        self.assertEqual(
            recommendation["decisive_gate_evidence"][0]["gate_id"],
            "one_year_deadline",
        )
        self.assertEqual(
            recommendation["next_actions_in_order"][0],
            "Получить завершающий судебный акт.",
        )

        unavailable = _matrix()
        _gate_by_id(unavailable, "application_or_meaning").update(
            status="unknown",
            rationale="Полный текст акта не опубликован после полного поиска.",
            evidence_ids=["act-source-exhausted-search-observation"],
            curability="unknown",
            record_availability="unavailable_after_exhaustive_search",
            next_action="Запросить копию у участника дела.",
        )
        self.assert_decision(unavailable, "ABSTAIN_PENDING_RECORD")

        for label, curability, availability, expected in (
            ("controlled", "curable", "controlled_retrieval", "FIX_FIRST"),
            ("residual", "unknown", "available", "ABSTAIN_PENDING_RECORD"),
        ):
            with self.subTest(label=label):
                mixed = _matrix()
                _gate_by_id(mixed, "anti_appeal_boundary").update(
                    status="fail",
                    rationale="Доказан неустранимый барьер.",
                    curability="incurable",
                    next_action="Рассмотреть иной правовой маршрут.",
                )
                _gate_by_id(mixed, "application_or_meaning").update(
                    status="unknown",
                    rationale="Материал пока не позволяет закрыть порог.",
                    evidence_ids=[f"{label}-search-observation"],
                    curability=curability,
                    record_availability=availability,
                    next_action="Получить и проверить недостающий материал.",
                )
                self.assert_decision(mixed, expected)

    def test_fail_precedence_distinguishes_incurable_and_curable(self) -> None:
        incurable = _matrix()
        _gate_by_id(incurable, "anti_appeal_boundary").update(
            status="fail",
            rationale="Предмет сводится к переоценке доказательств.",
            curability="incurable",
            next_action="Рассмотреть иные способы защиты.",
        )
        recommendation = self.assert_decision(incurable, "NO_GO_KSRF")
        self.assertIn(
            "anti_appeal_boundary",
            {
                item["gate_id"]
                for item in recommendation["decisive_gate_evidence"]
            },
        )

        curable = _matrix()
        _gate_by_id(curable, "exhaustion_and_preservation").update(
            status="fail",
            rationale="Доступный обычный маршрут ещё не завершён.",
            curability="curable",
            next_action="Завершить доступную судебную стадию.",
        )
        self.assert_decision(curable, "FIX_FIRST")

        mixed_failures = copy.deepcopy(incurable)
        _gate_by_id(mixed_failures, "exhaustion_and_preservation").update(
            status="fail",
            rationale="Обычный способ защиты ещё не завершён.",
            curability="curable",
            next_action="Завершить доступную судебную стадию.",
        )
        recommendation = self.assert_decision(mixed_failures, "NO_GO_KSRF")
        self.assertIn(
            "controlled_gap_requires_action",
            recommendation["blocker_codes"],
        )

    def test_active_case_routes_to_court_request_only_after_other_gaps(self) -> None:
        invalid_individual = _matrix()
        _gate_by_id(invalid_individual, "case_status")["disposition"] = "active"
        with self.assertRaisesRegex(
            AdmissibilityContractError,
            "individual_complaint.*case_status=completed",
        ):
            validate_admissibility_matrix(invalid_individual)

        active = _matrix()
        _gate_by_id(active, "competence_and_route")["disposition"] = "court_request"
        _gate_by_id(active, "case_status")["disposition"] = "active"
        self.assert_decision(active, "COURT_REQUEST_ROUTE")

        _gate_by_id(active, "challenged_norm_version").update(
            status="unknown",
            rationale="Редакция нормы ещё проверяется.",
            evidence_ids=["norm-source-retrieval-attempt"],
            curability="curable",
            record_availability="controlled_retrieval",
            next_action="Получить официальный текст редакции.",
        )
        self.assert_decision(active, "FIX_FIRST")

    def test_unverified_official_source_abstains_not_rejects(self) -> None:
        recommendation = self.assert_decision(
            _matrix(),
            "ABSTAIN_PENDING_RECORD",
            current_official=(),
        )
        self.assertIn("official_authority_unverified", recommendation["blocker_codes"])
        self.assertIn(
            f"official_authority_unverified:{OFFICIAL_EVIDENCE_ID}",
            recommendation["blocker_codes"],
        )
        self.assertEqual(len(recommendation["decisive_gate_evidence"]), 12)

        stale = _matrix()
        snapshot = stale["official_rule_snapshot"]
        assert isinstance(snapshot, dict)
        snapshot["status"] = "stale"
        self.assert_decision(stale, "ABSTAIN_PENDING_RECORD")

    def test_stale_issue_binding_abstains_with_exact_blocker(self) -> None:
        blocker = "issue-option-1:issue_candidate_fingerprint_mismatch"
        recommendation = derive_route_recommendation(
            _matrix(),
            current_official_evidence_ids=(OFFICIAL_EVIDENCE_ID,),
            current_issue_binding_blockers=(blocker,),
        )
        self.assertEqual(recommendation["decision"], "ABSTAIN_PENDING_RECORD")
        self.assertIn("issue_binding_unverified", recommendation["blocker_codes"])
        self.assertIn(blocker, recommendation["blocker_codes"])
        self.assertEqual(
            list(
                Draft202012Validator(
                    AdmissibilitySchemaTests.recommendation_schema
                ).iter_errors(recommendation)
            ),
            [],
        )

    def test_completed_research_without_viable_issue_is_not_no_go(self) -> None:
        matrix = _matrix()
        context = matrix["route_context"]
        assert isinstance(context, dict)
        context.update(
            option_bindings=[
                {
                    "option_id": "issue-option-rejected",
                    "content_fingerprint": "issue-candidate-content:sha256:" + "2" * 64,
                    "readiness": "rejected",
                    "evidence_ids": ["issue-rejection-evidence"],
                }
            ],
            preferred_option_id=None,
        )
        self.assert_decision(matrix, "FIX_FIRST")

    def test_viable_option_without_human_preference_is_fix_first(self) -> None:
        matrix = _matrix()
        context = matrix["route_context"]
        assert isinstance(context, dict)
        context["preferred_option_id"] = None
        recommendation = self.assert_decision(matrix, "FIX_FIRST")
        self.assertIn(
            "preferred_viable_option_missing",
            recommendation["blocker_codes"],
        )

    def test_unknown_precedence_keeps_every_independent_gate_blocker(self) -> None:
        matrix = _matrix()
        _gate_by_id(matrix, "anti_appeal_boundary").update(
            status="fail",
            rationale="Предмет сводится к переоценке доказательств.",
            curability="incurable",
            next_action="Рассмотреть иной правовой маршрут.",
        )
        _gate_by_id(matrix, "exhaustion_and_preservation").update(
            status="fail",
            rationale="Обычный способ защиты ещё не завершён.",
            curability="curable",
            next_action="Завершить доступную судебную стадию.",
        )
        _gate_by_id(matrix, "application_or_meaning").update(
            status="unknown",
            rationale="Полный акт недоступен после исчерпывающего поиска.",
            evidence_ids=["act-source-exhausted-search-observation"],
            curability="unknown",
            record_availability="unavailable_after_exhaustive_search",
            next_action="Запросить заверенную копию полного акта.",
        )
        recommendation = self.assert_decision(
            matrix,
            "ABSTAIN_PENDING_RECORD",
        )
        self.assertEqual(
            recommendation["next_actions_in_order"][0],
            "Запросить заверенную копию полного акта.",
        )
        self.assertEqual(
            recommendation["next_actions_in_order"][1],
            "Рассмотреть иной правовой маршрут.",
        )
        self.assertEqual(
            recommendation["next_actions_in_order"][2],
            "Завершить доступную судебную стадию.",
        )
        self.assertEqual(
            set(recommendation["blocker_codes"]),
            {
                "controlled_gap_requires_action",
                "critical_record_unavailable",
                "incurable_admissibility_failure",
            },
        )
        self.assertEqual(
            {
                item["gate_id"]
                for item in recommendation["decisive_gate_evidence"]
            },
            {
                "anti_appeal_boundary",
                "application_or_meaning",
                "exhaustion_and_preservation",
            },
        )

    def test_evidence_bound_nonviable_remedy_is_no_go(self) -> None:
        matrix = _matrix()
        remedy = _gate_by_id(matrix, "permissible_remedy")
        remedy.update(
            status="fail",
            rationale="Исследованный способ защиты юридически недоступен.",
            curability="incurable",
            next_action="Рассмотреть иной правовой маршрут.",
            disposition="not_viable",
        )
        self.assert_decision(matrix, "NO_GO_KSRF")

    def test_recommendation_binds_exact_matrix_and_option_revisions(self) -> None:
        first = self.assert_decision(_matrix(), "GO_TO_KSRF")
        changed = _matrix()
        _gate_by_id(changed, "causation_and_rights_harm")["rationale"] = (
            "Изменённая доказательственная формулировка."
        )
        second = self.assert_decision(changed, "GO_TO_KSRF")
        self.assertNotEqual(first["matrix_revision_id"], second["matrix_revision_id"])
        self.assertNotEqual(first["recommendation_id"], second["recommendation_id"])
        self.assertEqual(
            first["option_bindings"][0]["content_fingerprint"],
            _canonical_issue_fingerprint(),
        )


class AdmissibilityWorkflowTests(unittest.TestCase):
    def test_derive_and_status_are_append_only_local_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            matter = initialize_matter(
                workspace,
                matter_identifier="CASE-ADMISSIBILITY-1",
                created_at=CHECKED_AT,
            )
            router = WorkflowRouter(workspace)
            matrix = _matrix()
            matrix["matter_id"] = matter["matter_id"]
            current = {
                "evidence": {"evidence_id": OFFICIAL_EVIDENCE_ID},
                "authority": {"filing_ready": True, "blockers": []},
            }
            with patch.object(
                router,
                "_resolve_current_source_authority",
                return_value=current,
            ), patch.object(
                router,
                "_validate_current_issue_bindings",
                return_value=(({
                    "option_id": "issue-option-1",
                    "current_gate_passed": True,
                    "blockers": [],
                },), ()),
            ):
                derived = router.dispatch("admissibility", "derive", matrix)

            self.assertEqual(derived["result"]["recommendation"]["decision"], "GO_TO_KSRF")
            self.assertEqual(derived["state"], "ready_for_expert_review")
            self.assertEqual(workflow_exit_code(derived), 0)
            self.assertFalse(derived["external_transmission_performed"])
            self.assertFalse(derived["filing_performed"])
            self.assertTrue(derived["input_object"]["sha256"])
            self.assertTrue(derived["result_object"]["sha256"])
            prior_result_bytes = router.objects.read_bytes(derived["result_object"])

            with patch.object(
                router,
                "_resolve_current_source_authority",
                return_value=None,
            ), patch.object(
                router,
                "_validate_current_issue_bindings",
                return_value=(({
                    "option_id": "issue-option-1",
                    "current_gate_passed": True,
                    "blockers": [],
                },), ()),
            ):
                status = router.dispatch("admissibility", "status")
            latest = status["result"]["latest"]
            self.assertEqual(
                latest["result"]["recommendation"]["matrix_revision_id"],
                derived["result"]["recommendation"]["matrix_revision_id"],
            )
            self.assertEqual(
                status["result"]["recommendation"]["decision"],
                "ABSTAIN_PENDING_RECORD",
            )
            self.assertEqual(workflow_exit_code(status), 3)
            events = (workspace / "workflow" / "events.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertEqual(len(events), 2)
            self.assertEqual(
                router.objects.read_bytes(derived["result_object"]),
                prior_result_bytes,
            )

    def test_unverified_persisted_issue_cannot_self_promote_to_viable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            matter = initialize_matter(
                workspace,
                matter_identifier="CASE-ADMISSIBILITY-ISSUE-BINDING",
                created_at=CHECKED_AT,
            )
            router = WorkflowRouter(workspace)
            issues = router.dispatch(
                "issues",
                "generate",
                _issue_generation_payload(),
            )
            candidate_payload = issues["result"]["candidates"][0]
            candidate = issue_candidate_from_dict(candidate_payload)
            self.assertFalse(issues["result"]["candidate_gates"][0]["passed"])

            matrix = _matrix()
            matrix["matter_id"] = matter["matter_id"]
            context = matrix["route_context"]
            assert isinstance(context, dict)
            context["option_bindings"] = [
                {
                    "option_id": candidate.issue_id,
                    "content_fingerprint": issue_candidate_content_fingerprint(
                        candidate
                    ),
                    "readiness": "viable",
                    "evidence_ids": ["issue-evidence-1"],
                }
            ]
            context["preferred_option_id"] = candidate.issue_id

            objects_before = {
                path.relative_to(workspace)
                for path in (workspace / "objects").rglob("*")
                if path.is_file()
            }
            events_before = (workspace / "workflow" / "events.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            with self.assertRaisesRegex(
                WorkflowInputError,
                "issue_binding_viability_unverified",
            ):
                router.dispatch("admissibility", "derive", matrix)

            binding = context["option_bindings"][0]
            assert isinstance(binding, dict)
            binding["readiness"] = "conditional"
            context["preferred_option_id"] = None
            binding["evidence_ids"] = ["fabricated-evidence"]
            with self.assertRaisesRegex(
                WorkflowInputError,
                "issue_binding_evidence_not_current",
            ):
                router.dispatch("admissibility", "derive", matrix)

            binding["evidence_ids"] = ["issue-evidence-1"]
            binding["content_fingerprint"] = (
                "issue-candidate-content:sha256:" + "f" * 64
            )
            with self.assertRaisesRegex(
                WorkflowInputError,
                "issue_binding_fingerprint_mismatch",
            ):
                router.dispatch("admissibility", "derive", matrix)

            binding["content_fingerprint"] = issue_candidate_content_fingerprint(
                candidate
            )
            matrix["claim_id"] = "claim-from-another-artifact"
            with self.assertRaisesRegex(
                WorkflowInputError,
                "issue_binding_claim_mismatch",
            ):
                router.dispatch("admissibility", "derive", matrix)
            objects_after = {
                path.relative_to(workspace)
                for path in (workspace / "objects").rglob("*")
                if path.is_file()
            }
            events_after = (workspace / "workflow" / "events.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertEqual(objects_after, objects_before)
            self.assertEqual(events_after, events_before)

    def test_status_downgrades_stale_issue_binding_and_preserves_go(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            matter = initialize_matter(
                workspace,
                matter_identifier="CASE-ADMISSIBILITY-STATUS-BINDING",
                created_at=CHECKED_AT,
            )
            router = WorkflowRouter(workspace)
            matrix = _matrix()
            matrix["matter_id"] = matter["matter_id"]
            current = {
                "evidence": {"evidence_id": OFFICIAL_EVIDENCE_ID},
                "authority": {"filing_ready": True, "blockers": []},
            }
            valid_checks = (({
                "option_id": "issue-option-1",
                "current_gate_passed": True,
                "blockers": [],
            },), ())
            with patch.object(
                router,
                "_resolve_current_source_authority",
                return_value=current,
            ), patch.object(
                router,
                "_validate_current_issue_bindings",
                return_value=valid_checks,
            ):
                derived = router.dispatch("admissibility", "derive", matrix)
            self.assertEqual(
                derived["result"]["recommendation"]["decision"],
                "GO_TO_KSRF",
            )
            prior_result_bytes = router.objects.read_bytes(derived["result_object"])
            exact_blocker = (
                "issue_binding_fingerprint_mismatch:issue-option-1"
            )
            with patch.object(
                router,
                "_resolve_current_source_authority",
                return_value=current,
            ), patch.object(
                router,
                "_validate_current_issue_bindings",
                return_value=((), (exact_blocker,)),
            ):
                status = router.dispatch("admissibility", "status")
            recommendation = status["result"]["recommendation"]
            self.assertEqual(
                recommendation["decision"],
                "ABSTAIN_PENDING_RECORD",
            )
            self.assertIn(exact_blocker, recommendation["blocker_codes"])
            self.assertEqual(
                router.objects.read_bytes(derived["result_object"]),
                prior_result_bytes,
            )
            events = [
                json.loads(line)
                for line in (workspace / "workflow" / "events.jsonl").read_text(
                    encoding="utf-8"
                ).splitlines()
            ]
            self.assertEqual(
                [event["action"] for event in events],
                ["derive", "status"],
            )

    def test_cross_matter_input_is_rejected_before_cas_or_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            initialize_matter(
                workspace,
                matter_identifier="CASE-ADMISSIBILITY-ISOLATION",
                created_at=CHECKED_AT,
            )
            router = WorkflowRouter(workspace)
            matrix = _matrix()
            matrix["matter_id"] = "matter-from-another-case"

            with self.assertRaisesRegex(WorkflowInputError, "matter_id"):
                router.dispatch("admissibility", "derive", matrix)

            self.assertFalse((workspace / "workflow" / "events.jsonl").exists())
            self.assertEqual(
                [
                    path
                    for path in (workspace / "objects").rglob("*")
                    if path.is_file()
                ],
                [],
            )


if __name__ == "__main__":
    unittest.main()
