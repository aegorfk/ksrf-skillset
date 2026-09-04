import copy
import hashlib
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from judicial_meaning.handoff_workbench import (
    _quality_binding_errors,
    artifact_sha256,
    bind_request_payload,
    build_approved_finding,
    build_artifact_manifest,
    build_selected_position_set_sha256,
    build_trusted_source_receipt,
    check_handoff,
    create_handoff,
    import_handoff,
)


def canonical_digest(envelope):
    unsigned = {key: value for key, value in envelope.items() if key != "handoff_id"}
    payload = json.dumps(
        unsigned,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_file_sha256(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    return hashlib.sha256(payload).hexdigest()


class HandoffWorkbenchTests(unittest.TestCase):
    plan_sha256 = "a" * 64
    evidence_sha256 = "b" * 64
    fingerprint_sha256 = "c" * 64
    audit_candidate_id = "audit-candidate-sha256:" + "1" * 64
    other_audit_candidate_id = "audit-candidate-sha256:" + "2" * 64
    limitations = ["Только раскрытый наблюдаемый корпус."]

    def test_portable_digest_rejects_non_finite_json_numbers(self):
        with self.assertRaises(ValueError):
            artifact_sha256({"score": float("nan")})

    @staticmethod
    def claim_bindings():
        return [
            {
                "claim_id": "claim-1",
                "claim_sha256": "1" * 64,
                "source_locator": "жалоба.md#абзац-12",
            }
        ]

    def make_request(self):
        payload = bind_request_payload(
            {
                "drafting_ready": False,
                "questions": ["Каков судебный смысл нормы в сопоставимых делах?"],
                "claim_bindings": self.claim_bindings(),
            }
        )
        return create_handoff(
            source_skill="ksrf-complaint-cycle",
            target_skill="ksrf-cassation-judicial-meaning",
            run_id="request-run",
            plan_sha256=self.plan_sha256,
            evidence_sha256=self.evidence_sha256,
            payload_type="unproven_research_questions",
            payload=payload,
            limitations=[],
            created_at="2026-08-26T11:00:00Z",
        )

    @staticmethod
    def position_card(card_id, *, proposition, quote, family):
        return {
            "position_card_id": card_id,
            "chain_id": f"chain-{card_id}",
            "document_id": f"document-{card_id}",
            "court_id": "2kas",
            "decision_date": "2025-12-04",
            "official_url": f"https://2kas.sudrf.ru/{card_id}",
            "document_sha256": "d" * 64,
            "speaker": "court",
            "proposition": proposition,
            "quote": quote,
            "quote_locator": "абзац 18",
            "quote_verified": True,
            "full_text_reviewed": True,
            "norm_edition_id": "article-135-edition-1",
            "material_facts": ["ежемесячная премия"],
            "comparison_features": [],
            "reasoning_to_outcome": "Вывод был необходим для результата.",
            "outcome_materiality": "necessary_to_outcome",
            "alternative_grounds": [],
            "reading_family": family,
            "outcome": "решение по существу",
            "remedy": "взыскание премии",
            "coder": "И.И. Иванов",
            "human_review": "approved",
            "adverse_buckets": ["opposite_reading"],
        }

    def selected_proofs(self):
        support = self.position_card(
            "position-support-1",
            proposition="Премия входит в систему оплаты труда.",
            quote="премия является составной частью заработной платы",
            family="wage_component",
        )
        adverse_card = self.position_card(
            "position-adverse-1",
            proposition="Условия премирования допускают усмотрение работодателя.",
            quote="выплата премии зависит от предусмотренных положением условий",
            family="employer_discretion",
        )
        comparisons = []
        relations = []
        for card, relation_name in ((support, "supports"), (adverse_card, "adverse")):
            comparison = {
                "comparison_id": f"comparison-{card['position_card_id']}",
                "position_card_id": card["position_card_id"],
                "position_card_sha256": artifact_sha256(card),
                "status": "matched",
                "fingerprint_sha256": self.fingerprint_sha256,
                "review_provenance": {
                    "status": "approved",
                    "reviewer": "И.И. Иванов",
                    "reviewed_at": "2026-08-26T11:10:00Z",
                },
            }
            comparisons.append(comparison)
            relations.append(
                {
                    "position_card_id": card["position_card_id"],
                    "position_card_sha256": artifact_sha256(card),
                    "comparison_id": comparison["comparison_id"],
                    "comparison_sha256": artifact_sha256(comparison),
                    "relation": relation_name,
                    "fingerprint_sha256": self.fingerprint_sha256,
                    "human_review": "approved",
                    "stale": False,
                }
            )
        adverse = {
            "completed": True,
            "completed_buckets": [
                "opposite_reading",
                "narrower_reading",
                "alternative_ground",
                "later_authority",
            ],
            "missing_buckets": [],
            "buckets": {
                "opposite_reading": ["position-adverse-1"],
                "narrower_reading": [],
                "alternative_ground": [],
                "later_authority": [],
            },
        }
        bridge = {
            "norm_ref": "ст. 135 ТК РФ",
            "applicant_case_meaning": "Премия снижена без проверяемого критерия.",
            "corpus_observation": "В сопоставимом корпусе раскрыты разные прочтения.",
            "constitutional_consequence": "Вознаграждение становится непредсказуемым.",
            "ordinary_remedy_analysis": "Обычная проверка неопределённость не устранила.",
            "supporting_position_card_ids": ["position-support-1"],
            "adverse_position_card_ids": ["position-adverse-1"],
            "fingerprint_sha256": self.fingerprint_sha256,
            "maximum_permitted_claim": "mixed_post_event",
            "claim_wording": "В раскрытом сопоставимом корпусе наблюдаются разные прочтения нормы.",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-26T11:20:00Z",
            "human_review": "approved",
        }
        decision = {
            "schema_version": "1.0",
            "decision": "approved",
            "reviewer": "И.И. Иванов",
            "decided_at": "2026-08-26T11:30:00Z",
            "plan_sha256": self.plan_sha256,
            "evidence_sha256": self.evidence_sha256,
            "candidate_ids": ["thesis-1"],
            "adverse_review_complete": True,
            "coverage_review_complete": True,
        }
        validation = {
            "schema_version": "1.0",
            "valid": True,
            "errors": [],
            "plan_sha256": self.plan_sha256,
            "evidence_sha256": self.evidence_sha256,
            "fingerprint_sha256": self.fingerprint_sha256,
            "validated_at": "2026-08-26T11:31:00Z",
        }
        return {
            "position_cards": [support, adverse_card],
            "comparisons": comparisons,
            "relations": relations,
            "adverse": adverse,
            "bridge": bridge,
            "human_decision": decision,
            "validation_report": validation,
        }

    def quality_bindings(self, *, evidence_sha256=None):
        bound_evidence_sha256 = evidence_sha256 or self.evidence_sha256
        trajectory_payload = {
            "schema_version": "1.0",
            "chain_id": "chain-position-support-1",
            "observation_ids": ["observation-1"],
            "observation_sha256s": ["9" * 64],
            "origin_stage": "first_instance",
            "origin_reading_family": "wage_component",
            "reported_only_observation_ids": [],
            "cassation_treatment": "expressly_adopts",
            "cassation_express_adoption": True,
            "alternative_sufficient_ground_present": False,
            "review_complete": True,
            "unresolved_reasons": [],
            "claim_limit": "bounded_observed_corpus",
        }
        trajectory = {
            **trajectory_payload,
            "trajectory_id": artifact_sha256(trajectory_payload),
        }
        chain_payload = {
            "schema_version": "1.0",
            "observation_count": 2,
            "observations_sha256": "b" * 64,
            "chain_count": 1,
            "required_chain_ids": ["chain-position-support-1"],
            "trajectories": [trajectory],
            "unresolved": [],
            "review_complete": True,
        }
        chain = {**chain_payload, "evidence_sha256": artifact_sha256(chain_payload)}
        audit_plan_payload = {
            "schema_version": "1.0",
            "plan_sha256": self.plan_sha256,
            "screening_sha256": "7" * 64,
            "primary_coding_sha256": "8" * 64,
            "selection_method": "canonical_sha256_rank",
            "sample_size": 1,
            "exclusion_sample_size": 0,
            "sample_candidate_ids": [self.audit_candidate_id],
            "exclusion_sample_candidate_ids": [],
            "required_candidate_ids": [self.audit_candidate_id],
            "invalid_screening_record_ids": [],
            "invalid_primary_record_ids": [],
            "frozen": True,
        }
        audit_plan = {
            **audit_plan_payload,
            "audit_plan_sha256": artifact_sha256(audit_plan_payload),
        }
        reliability_payload = {
            "schema_version": "1.0",
            "audit_plan_input_sha256": artifact_sha256(audit_plan),
            "audit_plan_sha256": audit_plan["audit_plan_sha256"],
            "audit_plan_frozen": True,
            "audit_plan_contract_valid": True,
            "audit_plan_digest_valid": True,
            "primary_coding_sha256": audit_plan["primary_coding_sha256"],
            "current_primary_coding_sha256": audit_plan["primary_coding_sha256"],
            "audit_decisions_sha256": "9" * 64,
            "adjudications_sha256": artifact_sha256([]),
            "required_candidate_ids": [self.audit_candidate_id],
            "audited_candidate_ids": [self.audit_candidate_id],
            "missing_candidate_ids": [],
            "same_reviewer_candidate_ids": [],
            "invalid_binding_candidate_ids": [],
            "invalid_provenance_candidate_ids": [],
            "invalid_screening_record_ids": [],
            "invalid_primary_record_ids": [],
            "invalid_audit_record_ids": [],
            "invalid_adjudication_record_ids": [],
            "field_disagreements": [],
            "false_exclusion_diagnostics": [],
            "unresolved_candidate_ids": [],
            "stale": False,
            "complete": True,
        }
        reliability = {
            **reliability_payload,
            "evidence_sha256": artifact_sha256(reliability_payload),
        }
        receipt_payload = {
            "schema_version": "1.0",
            "artifact_type": "coding_audit_finalization_receipt",
            "producer": "judicial_meaning.quality.coding_audit_finalize",
            "bundle_contract_version": "1.1",
            "plan_sha256": self.plan_sha256,
            "audit_plan_sha256": audit_plan["audit_plan_sha256"],
            "codebook_version": "1.0",
            "source_bundle_manifest_sha256": "1" * 64,
            "expected_source_bundle_manifest_sha256": "1" * 64,
            "source_bundle_manifest_file_sha256": "2" * 64,
            "audit_plan_file_sha256": "3" * 64,
            "primary_decisions_file_sha256": "4" * 64,
            "review_packet_sha256": "5" * 64,
            "codebook_sha256": "6" * 64,
            "coding_brief_file_sha256": "7" * 64,
            "audit_import_receipt_sha256": "8" * 64,
            "expected_audit_import_receipt_sha256": "8" * 64,
            "audit_import_receipt_file_sha256": "9" * 64,
            "audit_decisions_file_sha256": "a" * 64,
            "resolutions_present": False,
            "resolutions_file_sha256": None,
            "resolutions_state_sha256": artifact_sha256(
                {"present": False, "file_sha256": None}
            ),
            "resolved_review_decisions_file_sha256": "c" * 64,
            "adjudications_file_sha256": "d" * 64,
            "coding_reliability_file_sha256": canonical_file_sha256(reliability),
            "candidate_ids": list(reliability["required_candidate_ids"]),
            "required_difference_pairs": [],
            "resolved_candidate_ids": [],
            "resolved_field_populations": [],
            "final_coding_sha256": "e" * 64,
            "difference_resolution_bijection_verified": True,
            "final_quote_literal_presence_verified": True,
            "final_quote_normalized_presence_verified": True,
            "quote_locator_review_declared": False,
            "quote_locator_verified": False,
            "reliability_complete": True,
            "source_workspace_reverified": False,
            "reviewer_identity_authenticated": False,
            "human_review_authenticated": False,
            "independence_verified": False,
            "receipt_authenticated": False,
            "norm_edition_temporal_applicability_verified": False,
            "publication_safe": False,
            "legal_readiness": False,
        }
        receipt = {
            **receipt_payload,
            "receipt_sha256": artifact_sha256(receipt_payload),
        }
        expected_receipt_sha256 = receipt["receipt_sha256"]
        dimensions = {
            name: {
                "state": "reviewed",
                "chain_ids": ["chain-position-support-1"],
                "evidence_refs": ["position-support-1"],
                "unknowns": [],
                "claim_effect": "bounded",
                "assessed": True,
                "usable_for_claim": True,
                "review_complete": True,
            }
            for name in (
                "comparable_reading_plurality",
                "fact_sensitivity",
                "court_distribution",
                "temporal_distribution",
                "chain_endorsement",
                "outcome_materiality",
                "higher_authority_treatment",
                "coverage_limits",
                "coding_reliability",
            )
        }
        profile_payload = {
            "schema_version": "1.0",
            "fingerprint_sha256": self.fingerprint_sha256,
            "unit": "independent_case_chain",
            "dimensions": dimensions,
            "profile_assessed": True,
            "claim_use_ready": True,
            "blocking_dimensions": [],
            "profile_complete": True,
            "numeric_aggregation": "prohibited",
            "constitutional_conclusion_permitted": False,
            "malformed_position_card_refs": [],
            "malformed_trajectory_refs": [],
            "coding_reliability_origin": {
                "status": "native_finalization_bound",
                "reason_codes": [],
                "expected_receipt_sha256": expected_receipt_sha256,
                "reliability_contract_valid": True,
                "receipt_contract_valid": True,
                "receipt_self_digest_valid": True,
                "external_receipt_digest_valid": True,
                "reliability_file_digest_valid": True,
                "audit_plan_digest_valid": True,
                "candidate_population_valid": True,
                "usable_for_claim": True,
            },
            "input_sha256s": {
                "applicant_relations": "1" * 64,
                "coding_audit_finalization_receipt": artifact_sha256(receipt),
                "coding_reliability": artifact_sha256(reliability),
                "comparisons": "3" * 64,
                "expected_finalization_receipt_sha256": expected_receipt_sha256,
                "higher_authority_treatments": "4" * 64,
                "position_cards": "5" * 64,
                "source_reconciliation": "6" * 64,
                "temporal_analysis": "7" * 64,
                "trajectories": artifact_sha256(chain["trajectories"]),
            },
            "claim_limit": "bounded_observed_corpus",
        }
        profile = {**profile_payload, "profile_id": artifact_sha256(profile_payload)}
        refresh_plan_payload = {
            "as_of": "2026-08-26T11:40:00Z",
            "max_age_seconds": 604800,
            "evidence_digest": f"corpus-evidence-sha256:{'4' * 64}",
            "treatment_ids": [],
            "treatment_population_sha256": "7" * 64,
            "coverage_requirements": [{"court_id": "2kas"}],
            "entries": [],
            "coverage_gaps": [],
        }
        refresh_plan = {
            "plan_id": (
                "refresh-plan-sha256:"
                + artifact_sha256(refresh_plan_payload)
            ),
            **refresh_plan_payload,
        }
        refresh_payload = {
            "schema_version": "1.0",
            "baseline_corpus_digest": "4" * 64,
            "current_corpus_digest": "4" * 64,
            "subject_evidence_sha256": bound_evidence_sha256,
            "refresh_plan_id": refresh_plan["plan_id"],
            "refresh_plan_sha256": artifact_sha256(refresh_plan),
            "refresh_plan_contract_valid": True,
            "refresh_plan_as_of": refresh_plan["as_of"],
            "refresh_plan_max_age_seconds": refresh_plan["max_age_seconds"],
            "refresh_plan_evidence_digest": refresh_plan["evidence_digest"],
            "refresh_plan_treatment_ids": refresh_plan["treatment_ids"],
            "refresh_plan_treatment_population_sha256": refresh_plan[
                "treatment_population_sha256"
            ],
            "refresh_plan_coverage_requirements": refresh_plan[
                "coverage_requirements"
            ],
            "refresh_plan_coverage_requirements_sha256": artifact_sha256(
                refresh_plan["coverage_requirements"]
            ),
            "checked_through": "2026-08-26T11:40:00Z",
            "filing_cutoff": "2026-08-26T11:35:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-26T11:45:00Z",
            "claim_ids": ["claim-1"],
            "affected_claim_ids": [],
            "live_binding_version": "1.0",
            "live_corpus_binding_contract_valid": True,
            "live_corpus_binding_verified": True,
            "live_cache_stable": True,
            "live_corpus_evidence_digest": (
                f"corpus-evidence-sha256:{'4' * 64}"
            ),
            "live_refresh_plan_sha256": artifact_sha256(refresh_plan),
            "live_treatment_set_sha256": "5" * 64,
            "live_treatment_population_sha256": "7" * 64,
            "live_treatment_ids": [],
            "live_binding_issue_ids": [],
            "treatment_set_contract_valid": True,
            "treatment_set_sha256": "5" * 64,
            "treatment_set_corpus_evidence_digest": (
                f"corpus-evidence-sha256:{'4' * 64}"
            ),
            "treatment_set_population_sha256": "7" * 64,
            "treatments_sha256": "6" * 64,
            "pending_treatment_ids": [],
            "verified_treatment_ids": [],
            "rejected_treatment_ids": [],
            "superseded_treatment_ids": [],
            "treatment_chronology_issue_ids": [],
            "stale_seed_ids": [],
            "malformed_refresh_entry_ids": [],
            "malformed_coverage_requirement_ids": [],
            "malformed_coverage_gap_ids": [],
            "coverage_gaps": [],
            "reasons": [],
            "status": "current_no_material_change",
            "complete": True,
        }
        refresh = {**refresh_payload, "refresh_id": artifact_sha256(refresh_payload)}
        ordinary_bindings = [
            {
                "quality_type": quality_type,
                "artifact_sha256": artifact_sha256(artifact),
                "artifact": artifact,
            }
            for quality_type, artifact in (
                ("chain_stage_propagation", chain),
                ("uncertainty_profile", profile),
                ("coding_audit_plan", audit_plan),
                ("coding_reliability", reliability),
                ("prefiling_refresh", refresh),
            )
        ]
        ordinary_bindings.append(
            {
                "quality_type": "coding_audit_finalization_receipt",
                "artifact_sha256": artifact_sha256(receipt),
                "artifact": receipt,
                "expected_receipt_sha256": expected_receipt_sha256,
            }
        )
        return ordinary_bindings

    @staticmethod
    def quality_binding(envelope, quality_type):
        return next(
            item
            for item in envelope["payload"]["quality_bindings"]
            if item["quality_type"] == quality_type
        )

    def quality_errors(self, bindings):
        return _quality_binding_errors(
            bindings,
            plan_sha256=self.plan_sha256,
            evidence_sha256=self.evidence_sha256,
            fingerprint_sha256=self.fingerprint_sha256,
            claim_bindings=self.claim_bindings(),
        )

    @staticmethod
    def rehash_quality_binding(binding, id_field):
        artifact = binding["artifact"]
        payload = {key: value for key, value in artifact.items() if key != id_field}
        artifact[id_field] = artifact_sha256(payload)
        binding["artifact_sha256"] = artifact_sha256(artifact)

    def rehash_reliability_and_profile(self, envelope):
        reliability = self.quality_binding(envelope, "coding_reliability")
        self.rehash_quality_binding(reliability, "evidence_sha256")
        receipt = self.quality_binding(
            envelope, "coding_audit_finalization_receipt"
        )
        receipt_artifact = receipt["artifact"]
        receipt_artifact["coding_reliability_file_sha256"] = canonical_file_sha256(
            reliability["artifact"]
        )
        receipt_artifact["audit_plan_sha256"] = reliability["artifact"][
            "audit_plan_sha256"
        ]
        receipt_artifact["candidate_ids"] = list(
            reliability["artifact"]["required_candidate_ids"]
        )
        self.rehash_receipt_and_profile(envelope)

    def rehash_receipt_and_profile(self, envelope, *, update_expected=True):
        receipt = self.quality_binding(
            envelope, "coding_audit_finalization_receipt"
        )
        receipt_artifact = receipt["artifact"]
        receipt_payload = {
            key: value
            for key, value in receipt_artifact.items()
            if key != "receipt_sha256"
        }
        receipt_artifact["receipt_sha256"] = artifact_sha256(receipt_payload)
        receipt["artifact_sha256"] = artifact_sha256(receipt_artifact)
        if update_expected:
            receipt["expected_receipt_sha256"] = receipt_artifact["receipt_sha256"]
        profile = self.quality_binding(envelope, "uncertainty_profile")
        profile["artifact"]["input_sha256s"]["coding_reliability"] = (
            artifact_sha256(
                self.quality_binding(envelope, "coding_reliability")["artifact"]
            )
        )
        profile["artifact"]["input_sha256s"][
            "coding_audit_finalization_receipt"
        ] = artifact_sha256(receipt_artifact)
        if update_expected:
            profile["artifact"]["input_sha256s"][
                "expected_finalization_receipt_sha256"
            ] = receipt["expected_receipt_sha256"]
            profile["artifact"]["coding_reliability_origin"][
                "expected_receipt_sha256"
            ] = receipt["expected_receipt_sha256"]
        self.rehash_quality_binding(profile, "profile_id")

    def persist_trusted_source(self, workspace, envelope):
        selected = envelope["payload"]["selected_proofs"]
        workspace.mkdir(parents=True, exist_ok=True)
        for name, records in (
            ("position-cards.jsonl", selected["position_cards"]),
            ("comparability-matrix.jsonl", selected["comparisons"]),
            ("applicant-relations.jsonl", selected["relations"]),
        ):
            (workspace / name).write_text(
                "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
                encoding="utf-8",
            )
        for name, key in (
            ("case-adverse-review.json", "adverse"),
            ("normative-bridge.json", "bridge"),
            ("human-decision.json", "human_decision"),
            ("validation-report.json", "validation_report"),
        ):
            (workspace / name).write_text(
                json.dumps(selected[key], ensure_ascii=False), encoding="utf-8"
            )
        request = self.make_request()
        request_dir = workspace / "handoffs" / "trusted-requests"
        request_dir.mkdir(parents=True, exist_ok=True)
        (request_dir / f"{request['handoff_id']}.json").write_text(
            json.dumps(request, ensure_ascii=False), encoding="utf-8"
        )
        quality_dir = workspace / "handoffs" / "trusted-quality"
        quality_dir.mkdir(parents=True, exist_ok=True)
        for binding in envelope["payload"]["quality_bindings"]:
            (quality_dir / f"{binding['quality_type']}-{binding['artifact_sha256']}.json").write_text(
                json.dumps(binding["artifact"], ensure_ascii=False), encoding="utf-8"
            )
        result_dir = workspace / "handoffs" / "trusted-results"
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / f"{envelope['handoff_id']}.json").write_text(
            json.dumps(build_trusted_source_receipt(envelope), ensure_ascii=False),
            encoding="utf-8",
        )

    def make_approved(self, *, run_id="run-1", evidence_sha256=None):
        request = self.make_request()
        selected_proofs = self.selected_proofs()
        bound_evidence_sha256 = evidence_sha256 or self.evidence_sha256
        selected_proofs["human_decision"]["evidence_sha256"] = bound_evidence_sha256
        selected_proofs["validation_report"]["evidence_sha256"] = bound_evidence_sha256
        bridge = selected_proofs["bridge"]
        candidate = {
            "candidate_id": "thesis-1",
            "plan_sha256": self.plan_sha256,
            "observed_statement": "В сопоставимом корпусе раскрыты разные прочтения.",
            "normative_defect_bridge": bridge["claim_wording"],
            "maximum_permitted_claim": bridge["maximum_permitted_claim"],
            "supporting_position_card_ids": bridge["supporting_position_card_ids"],
            "adverse_position_card_ids": bridge["adverse_position_card_ids"],
            "human_review": "approved",
            "drafting_ready": True,
        }
        finding = build_approved_finding(candidate, ["claim-1"], bridge)
        payload = {
            "drafting_ready": True,
            "request_handoff_id": request["handoff_id"],
            "request_sha256": request["payload"]["request_sha256"],
            "claim_set_sha256": request["payload"]["claim_set_sha256"],
            "claim_bindings": request["payload"]["claim_bindings"],
            "findings": [finding],
            "supporting_position_card_ids": bridge["supporting_position_card_ids"],
            "adverse_position_card_ids": bridge["adverse_position_card_ids"],
            "approval_binding": {
                "human_decision_sha256": artifact_sha256(selected_proofs["human_decision"]),
                "validation_report_sha256": artifact_sha256(selected_proofs["validation_report"]),
                "normative_bridge_sha256": artifact_sha256(bridge),
                "reviewer": selected_proofs["human_decision"]["reviewer"],
                "approved_at": selected_proofs["human_decision"]["decided_at"],
            },
            "artifact_manifest": build_artifact_manifest(selected_proofs),
            "selected_position_set_sha256": build_selected_position_set_sha256(selected_proofs),
            "selected_proofs": selected_proofs,
            "maximum_permitted_claim": bridge["maximum_permitted_claim"],
            "limitations": self.limitations,
            "quality_bindings": self.quality_bindings(
                evidence_sha256=bound_evidence_sha256
            ),
        }
        return create_handoff(
            source_skill="ksrf-cassation-judicial-meaning",
            target_skill="ksrf-complaint-cycle",
            run_id=run_id,
            plan_sha256=self.plan_sha256,
            evidence_sha256=bound_evidence_sha256,
            payload_type="approved_bounded_findings",
            payload=payload,
            limitations=self.limitations,
            created_at="2026-08-26T12:00:00Z",
            fingerprint_sha256=self.fingerprint_sha256,
        )

    def test_v2_request_and_approved_result_are_content_bound(self):
        request = self.make_request()
        self.assertEqual("2.0", request["schema_version"])
        self.assertEqual(request["handoff_id"], canonical_digest(request))
        self.assertTrue(check_handoff(request)["valid"])

        bad_request = copy.deepcopy(request)
        bad_request["payload"]["claim_bindings"][0]["source_locator"] = "иной абзац"
        bad_request["handoff_id"] = canonical_digest(bad_request)
        result = check_handoff(bad_request)
        self.assertFalse(result["valid"])
        self.assertIn("claim_set_sha256", " ".join(result["errors"]))

        envelope = self.make_approved()
        unanchored = check_handoff(envelope, expected_target="ksrf-complaint-cycle")
        self.assertFalse(unanchored["valid"])
        self.assertEqual("audit_only_unanchored", unanchored["status"])
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            self.persist_trusted_source(source, envelope)
            valid = check_handoff(
                envelope,
                expected_target="ksrf-complaint-cycle",
                current_plan_sha256=self.plan_sha256,
                current_evidence_sha256=self.evidence_sha256,
                current_fingerprint_sha256=self.fingerprint_sha256,
                current_maximum_permitted_claim="mixed_post_event",
                trusted_source_workspace=source,
            )
            self.assertTrue(valid["valid"], valid["errors"])

    def test_reviewed_receiver_requires_explicit_target_before_trusted_verification(self):
        envelope = self.make_approved()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            ledger = Path(tmp) / "inbox.jsonl"
            self.persist_trusted_source(source, envelope)
            checked = check_handoff(
                envelope,
                trusted_source_workspace=source,
            )
            imported = import_handoff(
                envelope,
                ledger,
                trusted_source_workspace=source,
            )
            self.assertFalse(ledger.exists())
        self.assertFalse(checked["valid"])
        self.assertEqual("incompatible", checked["status"])
        self.assertIn("expected_target", " ".join(checked["errors"]))
        self.assertFalse(imported["valid"])
        self.assertFalse(imported["imported"])

        request = check_handoff(self.make_request())
        self.assertTrue(request["valid"])

    def test_full_nested_rehash_attacks_require_external_source_anchor(self):
        envelope = copy.deepcopy(self.make_approved())
        payload = envelope["payload"]
        selected = payload["selected_proofs"]
        card = selected["position_cards"][0]
        card["quote"] = "полностью выдуманная цитата"
        comparison = selected["comparisons"][0]
        comparison["position_card_sha256"] = artifact_sha256(card)
        relation = selected["relations"][0]
        relation["position_card_sha256"] = artifact_sha256(card)
        relation["comparison_sha256"] = artifact_sha256(comparison)
        bridge = selected["bridge"]
        old_support = bridge["supporting_position_card_ids"][0]
        old_adverse = bridge["adverse_position_card_ids"][0]
        for item in selected["relations"]:
            if item["position_card_id"] == old_support:
                item["relation"] = "adverse"
            elif item["position_card_id"] == old_adverse:
                item["relation"] = "supports"
        bridge["supporting_position_card_ids"] = [old_adverse]
        bridge["adverse_position_card_ids"] = [old_support]
        selected["adverse"]["buckets"]["opposite_reading"] = [old_support]
        payload["supporting_position_card_ids"] = [old_adverse]
        payload["adverse_position_card_ids"] = [old_support]
        bridge["maximum_permitted_claim"] = "вся практика доказывает неконституционность"
        bridge["claim_wording"] = "Вся практика доказывает неконституционность."
        payload["maximum_permitted_claim"] = bridge["maximum_permitted_claim"]
        candidate = payload["findings"][0]["candidate"]
        candidate["supporting_position_card_ids"] = [old_adverse]
        candidate["adverse_position_card_ids"] = [old_support]
        candidate["maximum_permitted_claim"] = bridge["maximum_permitted_claim"]
        payload["findings"] = [build_approved_finding(candidate, ["claim-1"], bridge)]
        payload["approval_binding"]["normative_bridge_sha256"] = artifact_sha256(bridge)
        payload["selected_position_set_sha256"] = build_selected_position_set_sha256(selected)
        payload["artifact_manifest"] = build_artifact_manifest(selected)
        envelope["handoff_id"] = canonical_digest(envelope)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            pristine = self.make_approved()
            self.persist_trusted_source(source, pristine)
            result = check_handoff(
                envelope,
                expected_target="ksrf-complaint-cycle",
                trusted_source_workspace=source,
            )
        self.assertFalse(result["valid"])
        self.assertIn("trusted", " ".join(result["errors"]).lower())

    def test_rehashed_request_and_claim_set_are_rejected_by_trusted_request(self):
        envelope = copy.deepcopy(self.make_approved())
        payload = envelope["payload"]
        payload["request_handoff_id"] = "f" * 64
        payload["request_sha256"] = "e" * 64
        payload["claim_bindings"][0]["claim_sha256"] = "9" * 64
        payload["claim_bindings"][0]["source_locator"] = "invented.md#1"
        payload["claim_set_sha256"] = artifact_sha256(payload["claim_bindings"])
        envelope["handoff_id"] = canonical_digest(envelope)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            self.persist_trusted_source(source, self.make_approved())
            result = check_handoff(
                envelope,
                expected_target="ksrf-complaint-cycle",
                trusted_source_workspace=source,
            )
        self.assertFalse(result["valid"])

    def test_rehashed_invented_ids_relations_quotes_and_limits_are_rejected(self):
        mutations = {
            "finding id": lambda payload: payload["findings"][0].__setitem__(
                "finding_id", "f" * 64
            ),
            "relation": lambda payload: payload["selected_proofs"]["relations"][0].__setitem__(
                "relation", "adverse"
            ),
            "quote": lambda payload: payload["selected_proofs"]["position_cards"][0].__setitem__(
                "quote", "придуманная цитата"
            ),
            "limit": lambda payload: payload.__setitem__(
                "maximum_permitted_claim", "all_practice"
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                envelope = copy.deepcopy(self.make_approved())
                mutate(envelope["payload"])
                envelope["handoff_id"] = canonical_digest(envelope)
                result = check_handoff(envelope)
                self.assertFalse(result["valid"])
                self.assertEqual("incompatible", result["status"])

    def test_missing_selected_proof_and_partial_claim_binding_fail_closed(self):
        envelope = copy.deepcopy(self.make_approved())
        del envelope["payload"]["selected_proofs"]["validation_report"]
        envelope["handoff_id"] = canonical_digest(envelope)
        result = check_handoff(envelope)
        self.assertFalse(result["valid"])
        self.assertIn("validation_report", " ".join(result["errors"]))

        request = self.make_request()
        del request["payload"]["claim_bindings"][0]["source_locator"]
        request["handoff_id"] = canonical_digest(request)
        result = check_handoff(request)
        self.assertFalse(result["valid"])
        self.assertIn("source_locator", " ".join(result["errors"]))

    def test_quality_artifact_is_content_bound(self):
        envelope = copy.deepcopy(self.make_approved())
        profile_binding = next(
            item
            for item in envelope["payload"]["quality_bindings"]
            if item["quality_type"] == "uncertainty_profile"
        )
        profile_binding["artifact"]["profile_id"] = "8" * 64
        envelope["handoff_id"] = canonical_digest(envelope)
        result = check_handoff(envelope)
        self.assertFalse(result["valid"])
        self.assertIn("quality_bindings", " ".join(result["errors"]))

    def test_native_quality_population_has_six_exact_cross_bound_bindings(self):
        bindings = self.quality_bindings()

        self.assertEqual([], self.quality_errors(bindings))
        self.assertEqual(
            {
                "chain_stage_propagation",
                "uncertainty_profile",
                "coding_audit_plan",
                "coding_reliability",
                "prefiling_refresh",
                "coding_audit_finalization_receipt",
            },
            {binding["quality_type"] for binding in bindings},
        )

    def test_only_finalization_receipt_uses_four_field_binding(self):
        mutations = {
            "receipt represented by generic binding": lambda bindings: next(
                item
                for item in bindings
                if item["quality_type"] == "coding_audit_finalization_receipt"
            ).pop("expected_receipt_sha256"),
            "ordinary binding receives expectation": lambda bindings: next(
                item
                for item in bindings
                if item["quality_type"] == "coding_reliability"
            ).__setitem__("expected_receipt_sha256", "f" * 64),
            "sixth type is absent": lambda bindings: bindings.__setitem__(
                slice(None),
                [
                    item
                    for item in bindings
                    if item["quality_type"]
                    != "coding_audit_finalization_receipt"
                ],
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                bindings = copy.deepcopy(self.quality_bindings())
                mutate(bindings)

                errors = self.quality_errors(bindings)

                self.assertTrue(errors)
                self.assertIn("quality", " ".join(errors).lower())

    def test_native_receipt_relation_rejects_rehashed_inner_mismatches(self):
        def make_envelope():
            return {"payload": {"quality_bindings": self.quality_bindings()}}

        def wrong_external_anchor(envelope):
            receipt = self.quality_binding(
                envelope, "coding_audit_finalization_receipt"
            )
            receipt["expected_receipt_sha256"] = "f" * 64

        def wrong_self_digest(envelope):
            receipt = self.quality_binding(
                envelope, "coding_audit_finalization_receipt"
            )
            receipt["artifact"]["receipt_sha256"] = "f" * 64
            receipt["artifact_sha256"] = artifact_sha256(receipt["artifact"])
            profile = self.quality_binding(envelope, "uncertainty_profile")
            profile["artifact"]["input_sha256s"][
                "coding_audit_finalization_receipt"
            ] = receipt["artifact_sha256"]
            self.rehash_quality_binding(profile, "profile_id")

        def wrong_reliability_file(envelope):
            receipt = self.quality_binding(
                envelope, "coding_audit_finalization_receipt"
            )
            receipt["artifact"]["coding_reliability_file_sha256"] = "f" * 64
            self.rehash_receipt_and_profile(envelope)

        def wrong_plan(envelope):
            receipt = self.quality_binding(
                envelope, "coding_audit_finalization_receipt"
            )
            receipt["artifact"]["audit_plan_sha256"] = "f" * 64
            self.rehash_receipt_and_profile(envelope)

        def wrong_outer_plan(envelope):
            receipt = self.quality_binding(
                envelope, "coding_audit_finalization_receipt"
            )
            receipt["artifact"]["plan_sha256"] = "f" * 64
            self.rehash_receipt_and_profile(envelope)

        def wrong_candidates(envelope):
            receipt = self.quality_binding(
                envelope, "coding_audit_finalization_receipt"
            )
            receipt["artifact"]["candidate_ids"] = [
                self.other_audit_candidate_id
            ]
            self.rehash_receipt_and_profile(envelope)

        for label, mutate in {
            "external anchor": wrong_external_anchor,
            "receipt self digest": wrong_self_digest,
            "reliability file": wrong_reliability_file,
            "audit plan": wrong_plan,
            "outer plan": wrong_outer_plan,
            "candidate population": wrong_candidates,
        }.items():
            with self.subTest(label=label):
                envelope = make_envelope()
                mutate(envelope)

                errors = self.quality_errors(
                    envelope["payload"]["quality_bindings"]
                )

                self.assertTrue(errors)
                self.assertIn(
                    "coding_audit_finalization_receipt",
                    " ".join(errors),
                )

    def test_uncertainty_profile_binds_reliability_receipt_and_external_anchor(self):
        mutations = {
            "reliability": lambda profile: profile["input_sha256s"].__setitem__(
                "coding_reliability", "f" * 64
            ),
            "receipt": lambda profile: profile["input_sha256s"].__setitem__(
                "coding_audit_finalization_receipt", "f" * 64
            ),
            "external expectation": lambda profile: profile[
                "input_sha256s"
            ].__setitem__("expected_finalization_receipt_sha256", "f" * 64),
            "origin expectation": lambda profile: profile[
                "coding_reliability_origin"
            ].__setitem__("expected_receipt_sha256", "f" * 64),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                envelope = {
                    "payload": {
                        "quality_bindings": copy.deepcopy(self.quality_bindings())
                    }
                }
                profile_binding = self.quality_binding(
                    envelope, "uncertainty_profile"
                )
                mutate(profile_binding["artifact"])
                self.rehash_quality_binding(profile_binding, "profile_id")

                errors = self.quality_errors(
                    envelope["payload"]["quality_bindings"]
                )

                self.assertTrue(errors)
                self.assertIn("uncertainty_profile", " ".join(errors))

    def test_native_receipt_errors_do_not_echo_hostile_private_values(self):
        bindings = copy.deepcopy(self.quality_bindings())
        receipt = next(
            item
            for item in bindings
            if item["quality_type"] == "coding_audit_finalization_receipt"
        )
        hostile = "Секретная цитата /Users/private/дело Иван Иванов"
        receipt["artifact"]["invented_private_value"] = hostile
        receipt["artifact_sha256"] = artifact_sha256(receipt["artifact"])

        errors = self.quality_errors(bindings)

        self.assertTrue(errors)
        self.assertNotIn(hostile, " ".join(errors))

    def test_finalization_receipt_enforces_resolution_bijection_and_order(self):
        def unexpected_resolution_file(receipt):
            receipt["resolutions_present"] = True
            receipt["resolutions_file_sha256"] = "1" * 64
            receipt["resolutions_state_sha256"] = artifact_sha256(
                {"present": True, "file_sha256": "1" * 64}
            )

        def wrong_resolution_state(receipt):
            receipt["resolutions_state_sha256"] = "f" * 64

        def false_review_declaration(receipt):
            receipt["quote_locator_review_declared"] = True

        def unordered_difference_pairs(receipt):
            receipt["required_difference_pairs"] = [
                {"candidate_id": self.audit_candidate_id, "field": "quote"},
                {"candidate_id": self.audit_candidate_id, "field": "label"},
            ]
            receipt["resolved_candidate_ids"] = [self.audit_candidate_id]
            receipt["resolved_field_populations"] = [
                {
                    "candidate_id": self.audit_candidate_id,
                    "fields": ["quote", "label"],
                }
            ]
            receipt["resolutions_present"] = True
            receipt["resolutions_file_sha256"] = "1" * 64
            receipt["resolutions_state_sha256"] = artifact_sha256(
                {"present": True, "file_sha256": "1" * 64}
            )
            receipt["quote_locator_review_declared"] = True

        for label, mutate in {
            "unexpected resolution file": unexpected_resolution_file,
            "wrong resolution-state digest": wrong_resolution_state,
            "false review declaration": false_review_declaration,
            "unordered difference pairs": unordered_difference_pairs,
        }.items():
            with self.subTest(label=label):
                envelope = {
                    "payload": {
                        "quality_bindings": copy.deepcopy(self.quality_bindings())
                    }
                }
                receipt = self.quality_binding(
                    envelope, "coding_audit_finalization_receipt"
                )["artifact"]
                mutate(receipt)
                self.rehash_receipt_and_profile(envelope)

                errors = self.quality_errors(
                    envelope["payload"]["quality_bindings"]
                )

                self.assertTrue(errors)
                self.assertIn(
                    "coding_audit_finalization_receipt",
                    " ".join(errors),
                )

    def test_finalization_receipt_requires_native_candidate_identifiers(self):
        envelope = {
            "payload": {"quality_bindings": copy.deepcopy(self.quality_bindings())}
        }
        audit_plan = self.quality_binding(envelope, "coding_audit_plan")
        audit_plan["artifact"]["sample_candidate_ids"] = ["candidate-1"]
        audit_plan["artifact"]["required_candidate_ids"] = ["candidate-1"]
        self.rehash_quality_binding(audit_plan, "audit_plan_sha256")
        reliability = self.quality_binding(envelope, "coding_reliability")
        reliability["artifact"].update(
            audit_plan_input_sha256=artifact_sha256(audit_plan["artifact"]),
            audit_plan_sha256=audit_plan["artifact"]["audit_plan_sha256"],
            required_candidate_ids=["candidate-1"],
            audited_candidate_ids=["candidate-1"],
        )
        self.rehash_reliability_and_profile(envelope)

        errors = self.quality_errors(envelope["payload"]["quality_bindings"])

        self.assertTrue(errors)
        self.assertIn("coding_audit_finalization_receipt", " ".join(errors))

    def test_trusted_receipt_binds_complete_special_quality_binding(self):
        envelope = self.make_approved()
        receipt = build_trusted_source_receipt(envelope)

        self.assertEqual(
            sorted(
                artifact_sha256(binding)
                for binding in envelope["payload"]["quality_bindings"]
            ),
            receipt["quality_binding_sha256s"],
        )

    def test_fabricated_or_missing_quality_bindings_fail_closed(self):
        missing = copy.deepcopy(self.make_approved())
        del missing["payload"]["quality_bindings"]
        missing["handoff_id"] = canonical_digest(missing)
        result = check_handoff(missing)
        self.assertFalse(result["valid"])
        self.assertIn("quality_bindings", " ".join(result["errors"]))

        fabricated = copy.deepcopy(self.make_approved())
        artifact = {"invented": True}
        fabricated["payload"]["quality_bindings"] = [
            {
                "quality_type": "prefiling_refresh",
                "artifact_sha256": artifact_sha256(artifact),
                "artifact": artifact,
            }
        ]
        fabricated["handoff_id"] = canonical_digest(fabricated)
        result = check_handoff(fabricated)
        self.assertFalse(result["valid"])
        self.assertIn("quality", " ".join(result["errors"]).lower())

    def test_prefiling_quality_rejects_missing_fields_and_overlapping_treatments(self):
        for mutation in (
            "missing_field",
            "overlap",
            "malformed",
            "coverage_digest",
            "undeclared_gap",
            "treatment_set_digest",
        ):
            with self.subTest(mutation=mutation):
                envelope = copy.deepcopy(self.make_approved())
                binding = next(
                    item
                    for item in envelope["payload"]["quality_bindings"]
                    if item["quality_type"] == "prefiling_refresh"
                )
                artifact = binding["artifact"]
                if mutation == "missing_field":
                    del artifact["malformed_refresh_entry_ids"]
                elif mutation == "overlap":
                    artifact["verified_treatment_ids"] = ["treatment-1"]
                    artifact["rejected_treatment_ids"] = ["treatment-1"]
                else:
                    if mutation == "malformed":
                        artifact["verified_treatment_ids"] = [{"invented": True}]
                    elif mutation == "coverage_digest":
                        artifact["refresh_plan_coverage_requirements_sha256"] = "9" * 64
                    elif mutation == "undeclared_gap":
                        artifact["coverage_gaps"] = [
                            {
                                "court_id": "foreign-court",
                                "reason": "coverage_gap_not_observed",
                                "action": "Проверить сегмент.",
                            }
                        ]
                        artifact["status"] = "bounded_current_with_disclosed_gaps"
                        artifact["reasons"] = ["unchanged_disclosed_coverage_gaps"]
                    elif mutation == "treatment_set_digest":
                        artifact["treatment_set_corpus_evidence_digest"] = (
                            f"corpus-evidence-sha256:{'9' * 64}"
                        )
                refresh_payload = {
                    key: value for key, value in artifact.items() if key != "refresh_id"
                }
                artifact["refresh_id"] = artifact_sha256(refresh_payload)
                binding["artifact_sha256"] = artifact_sha256(artifact)
                envelope["handoff_id"] = canonical_digest(envelope)
                result = check_handoff(envelope)
                self.assertFalse(result["valid"])
                self.assertEqual("incompatible", result["status"])
                self.assertIn("prefiling_refresh", " ".join(result["errors"]))

    def test_prefiling_quality_accepts_nonempty_superseded_partition(self):
        envelope = copy.deepcopy(self.make_approved())
        binding = self.quality_binding(envelope, "prefiling_refresh")
        artifact = binding["artifact"]
        treatment_ids = ["treatment-current", "treatment-superseded"]
        artifact["refresh_plan_treatment_ids"] = treatment_ids
        artifact["live_treatment_ids"] = treatment_ids
        artifact["verified_treatment_ids"] = ["treatment-current"]
        artifact["superseded_treatment_ids"] = ["treatment-superseded"]
        self.rehash_quality_binding(binding, "refresh_id")
        envelope["handoff_id"] = canonical_digest(envelope)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            self.persist_trusted_source(source, envelope)
            result = check_handoff(
                envelope,
                expected_target="ksrf-complaint-cycle",
                current_plan_sha256=self.plan_sha256,
                current_evidence_sha256=self.evidence_sha256,
                current_fingerprint_sha256=self.fingerprint_sha256,
                current_maximum_permitted_claim="mixed_post_event",
                trusted_source_workspace=source,
            )

        self.assertTrue(result["valid"], result["errors"])

    def test_coding_audit_plan_rejects_impossible_counts_bool_duplicates_and_union(self):
        mutations = {
            "count below selected IDs": lambda artifact: artifact.__setitem__(
                "sample_size", 0
            ),
            "boolean count": lambda artifact: artifact.__setitem__(
                "sample_size", True
            ),
            "duplicate selected IDs": lambda artifact: artifact.update(
                sample_size=2,
                sample_candidate_ids=[self.audit_candidate_id, self.audit_candidate_id],
            ),
            "required IDs differ from sample union": lambda artifact: artifact.__setitem__(
                "required_candidate_ids", [self.other_audit_candidate_id]
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                envelope = copy.deepcopy(self.make_approved())
                binding = self.quality_binding(envelope, "coding_audit_plan")
                mutate(binding["artifact"])
                self.rehash_quality_binding(binding, "audit_plan_sha256")
                envelope["handoff_id"] = canonical_digest(envelope)

                result = check_handoff(envelope)

                self.assertFalse(result["valid"])
                self.assertEqual("incompatible", result["status"])
                self.assertIn("coding_audit_plan", " ".join(result["errors"]))

    def test_coding_reliability_rejects_unresolved_or_unmatched_disagreements(self):
        mutations = {
            "unresolved field disagreement": lambda artifact: artifact[
                "field_disagreements"
            ].append(
                {
                    "candidate_id": self.audit_candidate_id,
                    "fields": ["label"],
                    "primary_coding_sha256": "b" * 64,
                    "secondary_coding_sha256": "c" * 64,
                    "resolved": False,
                    "adjudication_sha256": None,
                }
            ),
            "false exclusion without label disagreement": lambda artifact: artifact.update(
                field_disagreements=[
                    {
                        "candidate_id": self.audit_candidate_id,
                        "fields": ["reasoning"],
                        "primary_coding_sha256": "b" * 64,
                        "secondary_coding_sha256": "c" * 64,
                        "resolved": True,
                        "adjudication_sha256": "d" * 64,
                    }
                ],
                false_exclusion_diagnostics=[
                    {
                        "candidate_id": self.audit_candidate_id,
                        "primary_label": "false_positive",
                        "secondary_label": "core_merits",
                        "resolved": True,
                    }
                ],
            ),
            "invented audited field": lambda artifact: artifact.update(
                adjudications_sha256="e" * 64,
                field_disagreements=[
                    {
                        "candidate_id": self.audit_candidate_id,
                        "fields": ["invented"],
                        "primary_coding_sha256": "b" * 64,
                        "secondary_coding_sha256": "c" * 64,
                        "resolved": True,
                        "adjudication_sha256": "d" * 64,
                    }
                ],
            ),
            "nonempty adjudication digest without disagreements": lambda artifact: artifact.__setitem__(
                "adjudications_sha256", "e" * 64
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                envelope = copy.deepcopy(self.make_approved())
                reliability = self.quality_binding(
                    envelope, "coding_reliability"
                )["artifact"]
                mutate(reliability)
                self.rehash_reliability_and_profile(envelope)
                envelope["handoff_id"] = canonical_digest(envelope)

                result = check_handoff(envelope)

                self.assertFalse(result["valid"])
                self.assertEqual("incompatible", result["status"])
                self.assertIn("coding_reliability", " ".join(result["errors"]))

    def test_prefiling_quality_rejects_changed_corpus_even_when_rehashed(self):
        envelope = copy.deepcopy(self.make_approved())
        binding = self.quality_binding(envelope, "prefiling_refresh")
        binding["artifact"]["baseline_corpus_digest"] = "f" * 64
        self.rehash_quality_binding(binding, "refresh_id")
        envelope["handoff_id"] = canonical_digest(envelope)

        result = check_handoff(envelope)

        self.assertFalse(result["valid"])
        self.assertEqual("incompatible", result["status"])
        self.assertIn("prefiling_refresh", " ".join(result["errors"]))

    def test_quality_bindings_require_coding_audit_plan(self):
        envelope = copy.deepcopy(self.make_approved())
        envelope["payload"]["quality_bindings"] = [
            binding
            for binding in envelope["payload"]["quality_bindings"]
            if binding["quality_type"] != "coding_audit_plan"
        ]
        envelope["handoff_id"] = canonical_digest(envelope)

        result = check_handoff(envelope)

        self.assertFalse(result["valid"])
        self.assertEqual("incompatible", result["status"])
        self.assertIn("coding_audit_plan", " ".join(result["errors"]))

    def test_reliability_must_match_bound_coding_audit_plan(self):
        mutations = {
            "audit plan input": lambda artifact: artifact.__setitem__(
                "audit_plan_input_sha256", "f" * 64
            ),
            "audit plan ID": lambda artifact: artifact.__setitem__(
                "audit_plan_sha256", "f" * 64
            ),
            "primary coding": lambda artifact: artifact.update(
                primary_coding_sha256="f" * 64,
                current_primary_coding_sha256="f" * 64,
            ),
            "required candidates": lambda artifact: artifact.update(
                required_candidate_ids=[self.other_audit_candidate_id],
                audited_candidate_ids=[self.other_audit_candidate_id],
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                envelope = copy.deepcopy(self.make_approved())
                reliability = self.quality_binding(
                    envelope, "coding_reliability"
                )["artifact"]
                mutate(reliability)
                self.rehash_reliability_and_profile(envelope)
                envelope["handoff_id"] = canonical_digest(envelope)

                result = check_handoff(envelope)

                self.assertFalse(result["valid"])
                self.assertEqual("incompatible", result["status"])
                self.assertIn(
                    "не связан с переданным coding_audit_plan",
                    " ".join(result["errors"]),
                )

    def test_uncertainty_input_hashes_must_match_quality_artifacts(self):
        for input_name in ("coding_reliability", "trajectories"):
            with self.subTest(input_name=input_name):
                envelope = copy.deepcopy(self.make_approved())
                profile = self.quality_binding(
                    envelope, "uncertainty_profile"
                )
                profile["artifact"]["input_sha256s"][input_name] = "f" * 64
                self.rehash_quality_binding(profile, "profile_id")
                envelope["handoff_id"] = canonical_digest(envelope)

                result = check_handoff(envelope)

                self.assertFalse(result["valid"])
                self.assertEqual("incompatible", result["status"])
                self.assertIn("uncertainty_profile", " ".join(result["errors"]))

    def test_duplicate_selected_ids_fail_runtime_like_schema(self):
        envelope = copy.deepcopy(self.make_approved())
        payload = envelope["payload"]
        selected = payload["selected_proofs"]
        bridge = selected["bridge"]
        bridge["supporting_position_card_ids"] *= 2
        payload["supporting_position_card_ids"] = list(bridge["supporting_position_card_ids"])
        payload["findings"] = [
            build_approved_finding(payload["findings"][0]["candidate"], ["claim-1"], bridge)
        ]
        payload["approval_binding"]["normative_bridge_sha256"] = artifact_sha256(bridge)
        payload["artifact_manifest"] = build_artifact_manifest(selected)
        payload["selected_position_set_sha256"] = build_selected_position_set_sha256(selected)
        envelope["handoff_id"] = canonical_digest(envelope)
        result = check_handoff(envelope)
        self.assertFalse(result["valid"])
        self.assertIn("повтор", " ".join(result["errors"]).lower())

    def test_legacy_v1_is_audit_readable_but_never_importable(self):
        legacy = {
            "schema_version": "1.0",
            "created_at": "2026-08-26T12:00:00Z",
            "source_skill": "ksrf-cassation-judicial-meaning",
            "target_skill": "ksrf-complaint-cycle",
            "run_id": "legacy-run",
            "plan_sha256": self.plan_sha256,
            "evidence_sha256": self.evidence_sha256,
            "payload_type": "approved_bounded_findings",
            "payload": {
                "drafting_ready": True,
                "maximum_permitted_claim": "bounded",
                "findings": [{"candidate_id": "legacy-thesis"}],
                "supporting_position_card_ids": ["legacy-card"],
                "adverse_position_card_ids": [],
            },
            "limitations": self.limitations,
            "fingerprint_sha256": self.fingerprint_sha256,
        }
        legacy["handoff_id"] = canonical_digest(legacy)
        result = check_handoff(legacy)
        self.assertFalse(result["valid"])
        self.assertTrue(result["audit_readable"])
        self.assertEqual("legacy_audit_only", result["status"])

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "inbox.jsonl"
            imported = import_handoff(legacy, ledger)
            self.assertFalse(imported["imported"])
            self.assertFalse(ledger.exists())

    def test_import_is_atomic_idempotent_and_rejects_stale_or_tampered_input(self):
        first = self.make_approved()
        second = self.make_approved(run_id="run-2", evidence_sha256="e" * 64)

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "inbox" / "import-ledger.jsonl"
            source = Path(tmp) / "source"
            self.persist_trusted_source(source, first)
            imported = import_handoff(
                first,
                ledger,
                expected_target="ksrf-complaint-cycle",
                current_plan_sha256=self.plan_sha256,
                current_evidence_sha256=self.evidence_sha256,
                trusted_source_workspace=source,
            )
            self.assertEqual("imported", imported["status"])
            original_bytes = ledger.read_bytes()

            duplicate = import_handoff(
                first,
                ledger,
                expected_target="ksrf-complaint-cycle",
                trusted_source_workspace=source,
            )
            self.assertEqual("idempotent_noop", duplicate["status"])
            self.assertEqual(original_bytes, ledger.read_bytes())

            tampered = copy.deepcopy(first)
            tampered["payload"]["findings"][0]["claim_wording"] = "подмена"
            rejected = import_handoff(tampered, ledger)
            self.assertEqual("tampered", rejected["status"])
            self.assertEqual(original_bytes, ledger.read_bytes())

            stale = import_handoff(
                first,
                ledger,
                expected_target="ksrf-complaint-cycle",
                current_evidence_sha256="f" * 64,
                trusted_source_workspace=source,
            )
            self.assertEqual("stale", stale["status"])
            self.assertEqual(original_bytes, ledger.read_bytes())

            with patch(
                "judicial_meaning.handoff_workbench.os.replace",
                side_effect=OSError("simulated atomic replace failure"),
            ):
                second_source = Path(tmp) / "second-source"
                self.persist_trusted_source(second_source, second)
                with self.assertRaisesRegex(OSError, "atomic replace failure"):
                    import_handoff(
                        second,
                        ledger,
                        expected_target="ksrf-complaint-cycle",
                        trusted_source_workspace=second_source,
                    )
            self.assertEqual(original_bytes, ledger.read_bytes())
            self.assertFalse(list(ledger.parent.glob("*.tmp")))

    def test_concurrent_imports_do_not_lose_records(self):
        first = self.make_approved(run_id="race-1")
        second = self.make_approved(run_id="race-2")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            self.persist_trusted_source(source, first)
            self.persist_trusted_source(source, second)
            ledger = Path(tmp) / "inbox.jsonl"
            barrier = threading.Barrier(2)

            def import_one(envelope):
                barrier.wait(timeout=5)
                return import_handoff(
                    envelope,
                    ledger,
                    expected_target="ksrf-complaint-cycle",
                    trusted_source_workspace=source,
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(import_one, (first, second)))
            self.assertTrue(all(result["imported"] for result in results))
            records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(2, len(records))


if __name__ == "__main__":
    unittest.main()
