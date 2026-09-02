# pyright: reportMissingImports=false, reportMissingModuleSource=false
from __future__ import annotations

import hashlib
import hmac
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping


SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB_ROOT = SKILL_ROOT / "lib"
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))

from ksrf.filing.admissibility import CANONICAL_GATE_IDS  # noqa: E402
from ksrf.filing.issue_options import (  # noqa: E402
    issue_approval_requests,
    issue_candidate_content_fingerprint,
    issue_candidate_from_dict,
)
from ksrf.filing.matter import initialize_matter  # noqa: E402
from ksrf.filing.source_evidence import (  # noqa: E402
    SourceEvidenceRepository,
    source_identity_fingerprint,
)
from ksrf.filing.storage import canonical_json_bytes  # noqa: E402
from ksrf.filing.trusted_approvals import TrustedApprovalLedger  # noqa: E402
from ksrf.filing.workflow import WorkflowRouter, workflow_exit_code  # noqa: E402


CHECKED_AT = "2026-08-30T12:00:00Z"
EXPIRES_AT = "2026-09-05T12:00:00Z"
SOURCE_ID = "ksrf_decisions"
SOURCE_ISSUER = "Конституционный Суд Российской Федерации"
OFFICIAL_LOCATOR = "https://www.ksrf.ru/ru/Decision/Pages/default.aspx"


class _MutableClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def __call__(self) -> datetime:
        return self.current

    def advance(self, *, seconds: int = 1) -> None:
        self.current += timedelta(seconds=seconds)


class _TestHmacHostVerifier:
    """Application-owned test trust root; it is never shipped in runtime code."""

    verifier_id = "test-hmac-host-v1"

    def __init__(self, key: bytes) -> None:
        self._key = key

    def _signature(self, domain: str, body: bytes) -> str:
        return hmac.new(
            self._key,
            domain.encode("utf-8") + b"\0" + body,
            hashlib.sha256,
        ).hexdigest()

    def actor_assertion(self, claims: Mapping[str, Any]) -> dict[str, Any]:
        canonical_claims = dict(claims)
        return {
            "claims": canonical_claims,
            "signature": self._signature(
                "actor-assertion", canonical_json_bytes(canonical_claims)
            ),
        }

    def verify_actor_assertion(self, assertion: Any) -> Mapping[str, Any]:
        if not isinstance(assertion, Mapping):
            raise ValueError("actor assertion must be a mapping")
        claims = assertion.get("claims")
        signature = str(assertion.get("signature") or "")
        if not isinstance(claims, Mapping):
            raise ValueError("actor assertion claims are missing")
        expected = self._signature(
            "actor-assertion", canonical_json_bytes(dict(claims))
        )
        if not hmac.compare_digest(signature, expected):
            raise ValueError("actor assertion signature mismatch")
        return dict(claims)

    def attest_record(
        self,
        kind: str,
        canonical_body: bytes,
        verified_actor_claims: Mapping[str, Any],
    ) -> dict[str, Any]:
        claims = dict(verified_actor_claims)
        message = canonical_body + b"\0" + canonical_json_bytes(claims)
        return {
            "verifier_id": self.verifier_id,
            "actor_claims": claims,
            "signature": self._signature(f"record:{kind}", message),
        }

    def verify_record_attestation(
        self,
        kind: str,
        canonical_body: bytes,
        attestation: Any,
    ) -> bool:
        if not isinstance(attestation, Mapping):
            return False
        if attestation.get("verifier_id") != self.verifier_id:
            return False
        claims = attestation.get("actor_claims")
        signature = str(attestation.get("signature") or "")
        if not isinstance(claims, Mapping):
            return False
        message = canonical_body + b"\0" + canonical_json_bytes(dict(claims))
        expected = self._signature(f"record:{kind}", message)
        return hmac.compare_digest(signature, expected)


def _gate(gate_id: str, official_evidence_id: str) -> dict[str, Any]:
    gate: dict[str, Any] = {
        "gate_id": gate_id,
        "status": "pass",
        "rationale": f"Порог {gate_id} подтверждён доказательствами.",
        "applicability_reason": "Порог применим к индивидуальной жалобе.",
        "evidence_ids": [f"matter-evidence-{gate_id}"],
        "official_rule_evidence_ids": [official_evidence_id],
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


def _matrix(
    *,
    matter_id: str,
    official_evidence_id: str,
    candidate_payload: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = issue_candidate_from_dict(candidate_payload)
    issue_id = candidate.issue_id
    return {
        "$schema": (
            "https://example.local/schemas/ksrf_filing/"
            "admissibility-matrix.v1.schema.json"
        ),
        "schema_version": "1.0.0",
        "artifact_type": "AdmissibilityMatrix",
        "matrix_id": "matrix-revocation-integration",
        "matter_id": matter_id,
        "claim_id": candidate.claim_id,
        "official_rule_snapshot": {
            "status": "verified_current",
            "checked_at": CHECKED_AT,
            "evidence_ids": [official_evidence_id],
        },
        "gates": [
            _gate(gate_id, official_evidence_id)
            for gate_id in CANONICAL_GATE_IDS
        ],
        "route_context": {
            "issue_assessment_status": "complete",
            "option_bindings": [
                {
                    "option_id": issue_id,
                    "content_fingerprint": issue_candidate_content_fingerprint(
                        candidate
                    ),
                    "readiness": "viable",
                    "evidence_ids": list(candidate.application_evidence_ids),
                }
            ],
            "preferred_option_id": issue_id,
            "reserve_option_ids": [],
            "expected_client_benefit": "Получить проверку нормативного смысла.",
            "adverse_risks": ["Возможен отказ в принятии обращения."],
            "alternatives_and_deadlines": [
                "Проверить ближайший процессуальный срок."
            ],
            "next_actions_in_order": [
                "Передать рекомендацию юристу на проверку."
            ],
            "reconsideration_conditions": [
                "Отзыв подтверждения или появление нового официального акта."
            ],
        },
    }


def _issue_payload(*, official_evidence_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "seeds": [
            {
                "seed_id": "seed-revocation-integration",
                "claim_id": "claim-revocation-integration",
                "norm_id": "norm-revocation-integration",
                "norm_version_id": "norm-version-revocation-integration",
                "theory_code": "legal_uncertainty",
                "normative_meaning": "Проверяемый нормативный смысл нормы.",
                "application_evidence_ids": [official_evidence_id],
                "application_gate_passed": True,
                "constitutional_benchmarks": ["ст. 19 Конституции РФ"],
                "rights_impairment": "Неравное применение нормы.",
                "anti_fourth_instance_boundary": "Оспаривается смысл нормы.",
                "ksrf_authority_ids": [official_evidence_id],
                "adverse_authority_ids": [],
                "adverse_authority_summary": "Неблагоприятные позиции проверены.",
                "adverse_authority_delta": "Препятствий для выбранной теории не найдено.",
                "requested_remedy": "Проверить конституционный смысл нормы.",
                "strengths": ["Есть проверяемая нормативная проблема."],
                "weaknesses": [],
                "source_gaps": [],
                "model_rank": 1,
                "anti_fourth_instance_gate": {
                    "state": "passed",
                    "rationale": "Оспаривается нормативный смысл, а не факты дела.",
                    "evidence_ids": [official_evidence_id],
                    "requires_human_review": False,
                },
                "practice_claims": [],
                "adverse_authority_gate": {
                    "state": "passed",
                    "rationale": "Неблагоприятные позиции разобраны.",
                    "evidence_ids": [official_evidence_id],
                },
                "remedy_gate": {
                    "state": "passed",
                    "rationale": "Просимый способ защиты относится к компетенции КС РФ.",
                    "evidence_ids": [official_evidence_id],
                },
                "human_selection": {
                    "state": "principal",
                    "reviewer": "Тестовый проверяющий",
                    "reviewed_at": CHECKED_AT,
                    "note": "Вариант выбран как основной.",
                },
            }
        ],
    }


class _Scenario:
    def __init__(self, root: Path, *, matter_identifier: str) -> None:
        self.workspace = root / "matter"
        self.matter = initialize_matter(
            self.workspace,
            matter_identifier=matter_identifier,
            created_at=CHECKED_AT,
        )
        self.clock = _MutableClock(
            datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
        )
        self.verifier = _TestHmacHostVerifier(b"synthetic-test-host-key")
        self.ledger = TrustedApprovalLedger(
            self.workspace / "trusted-approvals",
            host_verifier=self.verifier,
            clock=self.clock,
        )
        claims = {
            "actor_id": "reviewer-1",
            "actor_display_name": "Тестовый проверяющий",
            "session_id": "session-revocation-integration",
            "authenticated_at": CHECKED_AT,
            "verification_method": "test_hmac_host_assertion",
            "assertion_id": "assertion-revocation-integration",
        }
        self.context = self.ledger.authenticate_actor(
            self.verifier.actor_assertion(claims)
        )
        self.router = WorkflowRouter(
            self.workspace,
            approval_ledger=self.ledger,
        )

    def import_official_source(self, root: Path) -> tuple[dict[str, Any], str]:
        raw_bytes = b"%PDF-1.4\nsynthetic official KSRF act\n%%EOF\n"
        local_file = root / "synthetic-official-act.pdf"
        local_file.write_bytes(raw_bytes)
        content_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        bindings = {
            "source_id": SOURCE_ID,
            "official_locator": OFFICIAL_LOCATOR,
            "content_sha256": content_sha256,
        }
        approval = self.ledger.create_approval(
            purpose="source_identity",
            subject_type="official_source_content",
            subject_id=SOURCE_ID,
            fingerprint=source_identity_fingerprint(**bindings),
            bindings=bindings,
            context=self.context,
            expires_at=EXPIRES_AT,
        )
        source_result = self.router.dispatch(
            "sources",
            "manual-import",
            {
                "schema_version": "1.0.0",
                "source_id": SOURCE_ID,
                "locator": str(local_file),
                "bounded_scope": {
                    "act_number": "1-П/2026",
                    "act_date": "2026-08-30",
                    "official_locator": OFFICIAL_LOCATOR,
                },
                "identity_checks": [
                    {
                        "check": "issuer_domain",
                        "status": "passed",
                        "issuer": SOURCE_ISSUER,
                        "domain": "www.ksrf.ru",
                        "official_locator": OFFICIAL_LOCATOR,
                    },
                    {
                        "check": "exact_document_identifier",
                        "status": "passed",
                        "identifier_type": "act_number",
                        "expected_value": "1-П/2026",
                        "observed_value": "1-П/2026",
                    },
                    {
                        "check": "document_date",
                        "status": "passed",
                        "identifier_type": "act_date",
                        "expected_value": "2026-08-30",
                        "observed_value": "2026-08-30",
                    },
                    {
                        "check": "content_locator_hash_binding",
                        "status": "passed",
                        "official_locator": OFFICIAL_LOCATOR,
                        "content_sha256": content_sha256,
                    },
                ],
                "approval_ids": [approval["approval_id"]],
            },
        )
        if source_result["state"] != "ready_for_expert_review":
            raise AssertionError(source_result)
        if source_result["result"]["network_access_authorized"] is not False:
            raise AssertionError("manual import unexpectedly authorized network access")
        evidence = source_result["result"]["evidence"]
        if not isinstance(evidence, dict):
            raise AssertionError("source evidence was not persisted")
        return evidence, str(approval["approval_id"])

    def persist_viable_issue(
        self, *, official_evidence_id: str
    ) -> tuple[dict[str, Any], dict[str, str]]:
        base_payload = _issue_payload(official_evidence_id=official_evidence_id)
        first = self.router.dispatch("issues", "generate", base_payload)
        candidate_payload = first["result"]["candidates"][0]
        candidate = issue_candidate_from_dict(candidate_payload)
        approvals: dict[str, str] = {}
        for key, request in issue_approval_requests(candidate).items():
            record = self.ledger.create_approval(
                **request,
                context=self.context,
                expires_at=EXPIRES_AT,
            )
            approvals[key] = str(record["approval_id"])
        approved_payload = deepcopy(base_payload)
        approved_payload["approval_ids"] = {candidate.issue_id: approvals}
        approved = self.router.dispatch("issues", "generate", approved_payload)
        if candidate.issue_id not in approved["result"]["release_ready_candidate_ids"]:
            raise AssertionError(approved)
        return approved["result"]["candidates"][0], approvals

    def derive_go(
        self,
        *,
        evidence: Mapping[str, Any],
        candidate: Mapping[str, Any],
    ) -> dict[str, Any]:
        derived = self.router.dispatch(
            "admissibility",
            "derive",
            _matrix(
                matter_id=str(self.matter["matter_id"]),
                official_evidence_id=str(evidence["evidence_id"]),
                candidate_payload=candidate,
            ),
        )
        recommendation = derived["result"]["recommendation"]
        if recommendation["decision"] != "GO_TO_KSRF":
            raise AssertionError(derived)
        if derived["state"] != "ready_for_expert_review":
            raise AssertionError(derived)
        return derived


class AdmissibilityRevocationIntegrationTests(unittest.TestCase):
    def _assert_status_preserves_go(
        self,
        *,
        scenario: _Scenario,
        derived: Mapping[str, Any],
        result_bytes_before: bytes,
        events_before: bytes,
        status: Mapping[str, Any],
    ) -> None:
        recommendation = status["result"]["recommendation"]
        self.assertEqual(status["state"], "blocked")
        self.assertEqual(workflow_exit_code(status), 3)
        self.assertEqual(recommendation["decision"], "ABSTAIN_PENDING_RECORD")
        self.assertEqual(recommendation["human_decision"], "pending")
        self.assertFalse(recommendation["legal_assessment_automated"])
        self.assertFalse(recommendation["filing_authority"])
        self.assertFalse(recommendation["filing_performed"])
        self.assertFalse(status["result"]["cached_result_reused_without_revalidation"])
        self.assertEqual(
            scenario.router.objects.read_bytes(derived["result_object"]),
            result_bytes_before,
        )

        events_after = (
            scenario.workspace / "workflow" / "events.jsonl"
        ).read_bytes()
        self.assertTrue(events_after.startswith(events_before))
        suffix = events_after[len(events_before) :]
        suffix_lines = suffix.splitlines()
        self.assertEqual(len(suffix_lines), 1)
        appended = json.loads(suffix_lines[0])
        self.assertEqual(appended["route"], "admissibility")
        self.assertEqual(appended["action"], "status")
        self.assertEqual(appended["state"], "blocked")

    def test_revoked_source_identity_approval_downgrades_go_to_abstain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario = _Scenario(
                root,
                matter_identifier="CASE-SOURCE-REVOCATION-INTEGRATION",
            )
            evidence, source_approval_id = scenario.import_official_source(root)
            candidate, _ = scenario.persist_viable_issue(
                official_evidence_id=str(evidence["evidence_id"])
            )
            derived = scenario.derive_go(evidence=evidence, candidate=candidate)
            result_bytes_before = scenario.router.objects.read_bytes(
                derived["result_object"]
            )
            events_before = (
                scenario.workspace / "workflow" / "events.jsonl"
            ).read_bytes()

            scenario.clock.advance()
            scenario.ledger.revoke_approval(
                source_approval_id,
                context=scenario.context,
                reason="Официальная идентичность требует повторной проверки.",
            )
            repository = SourceEvidenceRepository(
                scenario.workspace / "evidence" / "official-sources",
                approval_ledger=scenario.ledger,
            )
            current_authority = repository.current_filing_authority(evidence)
            self.assertIn("approval_revoked", current_authority["blockers"])

            status = scenario.router.dispatch("admissibility", "status")
            exact_blocker = f"{evidence['evidence_id']}:approval_revoked"
            self.assertIn(
                exact_blocker,
                status["result"]["official_authority_blockers"],
            )
            self.assertIn(
                f"official_authority_unverified:{evidence['evidence_id']}",
                status["result"]["recommendation"]["blocker_codes"],
            )
            self._assert_status_preserves_go(
                scenario=scenario,
                derived=derived,
                result_bytes_before=result_bytes_before,
                events_before=events_before,
                status=status,
            )

    def test_revoked_issue_selection_approval_downgrades_go_to_abstain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario = _Scenario(
                root,
                matter_identifier="CASE-ISSUE-REVOCATION-INTEGRATION",
            )
            evidence, _ = scenario.import_official_source(root)
            candidate, approvals = scenario.persist_viable_issue(
                official_evidence_id=str(evidence["evidence_id"])
            )
            derived = scenario.derive_go(evidence=evidence, candidate=candidate)
            result_bytes_before = scenario.router.objects.read_bytes(
                derived["result_object"]
            )
            events_before = (
                scenario.workspace / "workflow" / "events.jsonl"
            ).read_bytes()

            scenario.clock.advance()
            scenario.ledger.revoke_approval(
                approvals["selection"],
                context=scenario.context,
                reason="Выбор основного варианта отозван человеком.",
            )
            issue_id = str(candidate["issue_id"])
            status = scenario.router.dispatch("admissibility", "status")
            exact_native = (
                "trusted_issue_approval_invalid:selection:approval_revoked"
            )
            exact_blocker = (
                f"issue_binding_gate_blocker:{issue_id}:{exact_native}"
            )
            self.assertIn(exact_blocker, status["result"]["issue_binding_blockers"])
            self.assertIn(
                exact_blocker,
                status["result"]["recommendation"]["blocker_codes"],
            )
            matching_checks = [
                item
                for item in status["result"]["issue_binding_checks"]
                if item["option_id"] == issue_id
            ]
            self.assertEqual(len(matching_checks), 1)
            self.assertFalse(matching_checks[0]["current_gate_passed"])
            self.assertIn(exact_blocker, matching_checks[0]["blockers"])
            self._assert_status_preserves_go(
                scenario=scenario,
                derived=derived,
                result_bytes_before=result_bytes_before,
                events_before=events_before,
                status=status,
            )


if __name__ == "__main__":
    unittest.main()
