import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from judicial_meaning.casework import (
    build_explainable_queue,
    analyze_case_relative_dynamics,
    classify_applicant_relation,
    compare_case_features,
    prepare_casework,
)
from judicial_meaning.handoff_workbench import bind_request_payload, create_handoff
from judicial_meaning.reporting import derive_research_status, write_offline_report


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_ROOT / "schemas" / "case-relative-workbench.v1.json"


class WorkbenchSchemaContractTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.definitions = self.schema["definitions"]

    def assertSchemaValid(self, definition_name, payload):
        validator = Draft202012Validator(
            {
                "$schema": self.schema["$schema"],
                "$ref": f"#/definitions/{definition_name}",
                "definitions": self.definitions,
            },
            format_checker=FormatChecker(),
        )
        errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
        self.assertEqual([], [error.message for error in errors])

    def assertRuntimeKeysConform(self, definition_name, payload):
        definition = self.definitions[definition_name]
        self.assertTrue(
            set(definition["required"]).issubset(payload),
            f"{definition_name}: runtime misses required schema keys",
        )
        if definition.get("additionalProperties") is False:
            self.assertTrue(
                set(payload).issubset(definition["properties"]),
                f"{definition_name}: schema rejects runtime keys "
                f"{sorted(set(payload) - set(definition['properties']))}",
            )

    def test_every_schema_file_is_standard_json(self):
        for path in sorted((SKILL_ROOT / "schemas").glob("*.json")):
            with self.subTest(path=path.name):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_bundle_has_versioned_required_definitions(self):
        self.assertEqual(
            "https://json-schema.org/draft/2020-12/schema",
            self.schema["$schema"],
        )
        self.assertEqual("1.1", self.schema["contract_version"])
        expected = {
            "case_fingerprint",
            "query_suggestion",
            "query_decision",
            "supplemental_query",
            "casework_bundle",
            "position_card",
            "feature_comparison",
            "applicant_relation",
            "review_queue",
            "adverse_review",
            "normative_bridge",
            "case_temporal_analysis",
            "derived_status",
            "report_manifest",
            "handoff_envelope",
            "public_cache_exchange",
            "funnel",
            "treatment_edge",
            "enumerator_manifest",
            "source_reconciliation",
            "promotion_record",
        }
        self.assertTrue(expected.issubset(self.definitions))
        for name in sorted(expected):
            with self.subTest(definition=name):
                definition = self.definitions[name]
                self.assertEqual(
                    (
                        "2.0"
                        if name == "handoff_envelope"
                        else "1.1"
                        if name == "treatment_edge"
                        else "1.0"
                    ),
                    definition["x-contract-version"],
                )
                self.assertEqual("object", definition["type"])
                self.assertTrue(definition["required"])
                self.assertTrue(set(definition["required"]).issubset(definition["properties"]))

    def test_all_local_definition_references_resolve(self):
        pending = [self.schema]
        references = []
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                reference = value.get("$ref")
                if isinstance(reference, str):
                    references.append(reference)
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
        for reference in references:
            with self.subTest(reference=reference):
                self.assertTrue(reference.startswith("#/definitions/"))
                self.assertIn(reference.removeprefix("#/definitions/"), self.definitions)

    def test_case_relative_enums_are_closed(self):
        self.assertEqual(
            {"verified", "unknown", "disputed"},
            set(self.definitions["case_feature"]["properties"]["status"]["enum"]),
        )
        self.assertEqual(
            {
                "exact_norm",
                "case_feature",
                "court_language",
                "legal_mechanism",
                "controlled_synonym",
                "opposite_reading",
                "narrower_reading",
                "alternative_ground",
                "later_legislation",
                "higher_authority",
            },
            set(self.definitions["query_suggestion"]["properties"]["lane"]["enum"]),
        )
        self.assertEqual(
            {
                "necessary_to_outcome",
                "independent_sufficient_ground",
                "contextual",
                "unclear",
            },
            set(
                self.definitions["position_card"]["properties"]["outcome_materiality"][
                    "enum"
                ]
            ),
        )
        self.assertEqual(
            {"matched", "different", "unknown"},
            set(
                self.definitions["feature_comparison_item"]["properties"]["status"][
                    "enum"
                ]
            ),
        )
        self.assertEqual(
            {"matched", "distinguishable", "uncertain"},
            set(self.definitions["feature_comparison"]["properties"]["status"]["enum"]),
        )
        self.assertEqual(
            {"supports", "adverse", "distinguishes", "neutral", "unresolved"},
            set(self.definitions["applicant_relation"]["properties"]["relation"]["enum"]),
        )
        self.assertEqual(
            {"pending_review", "coded_position", "reviewed_exclusion"},
            set(self.definitions["review_queue_item"]["properties"]["status"]["enum"]),
        )

    def test_casework_schema_carries_source_query_and_missing_task_contracts(self):
        source = self.definitions["source_locator"]
        self.assertTrue(
            {
                "source_type",
                "document_id",
                "decision_id",
                "speaker",
                "quote",
                "quote_locator",
            }.issubset(source["properties"])
        )
        feature_required = set(self.definitions["case_feature"]["required"])
        self.assertTrue({"confirmation_state", "revision"}.issubset(feature_required))

        query_required = set(self.definitions["query_suggestion"]["required"])
        self.assertTrue(
            {
                "reason_code",
                "confirmation_state",
                "plan_relationship",
            }.issubset(query_required)
        )
        self.assertIn(
            "source_records",
            self.definitions["query_provenance"]["required"],
        )

        bundle_required = set(self.definitions["casework_bundle"]["required"])
        self.assertTrue({"missing_tasks", "dependency_state"}.issubset(bundle_required))
        self.assertIn("missing_task", self.definitions)
        self.assertIn("dependency_state", self.definitions)

    def test_runtime_casework_and_comparison_outputs_fit_closed_schema_properties(self):
        casework = prepare_casework(
            issue="Пределы снижения премии",
            norm_refs=["ст. 135 ТК РФ"],
            features=[
                {
                    "feature_id": "payment_kind",
                    "value": "ежемесячная",
                    "status": "verified",
                    "material": True,
                    "source": {
                        "document_id": "act-1",
                        "quote_locator": "абзац 5",
                    },
                    "query_terms": [],
                }
            ],
        )
        self.assertRuntimeKeysConform("casework_bundle", casework)
        self.assertSchemaValid("casework_bundle", casework)
        self.assertRuntimeKeysConform("case_fingerprint", casework["fingerprint"])
        for feature in casework["fingerprint"]["features"]:
            self.assertRuntimeKeysConform("case_feature", feature)
        for suggestion in casework["query_suggestions"]:
            self.assertRuntimeKeysConform("query_suggestion", suggestion)
            self.assertRuntimeKeysConform(
                "query_provenance", suggestion["provenance"]
            )

        features = [
            {
                "feature_id": "payment_kind",
                "value": "ежемесячная",
                "status": "verified",
                "material": True,
            }
        ]
        comparison = compare_case_features(
            features,
            features,
            reviewer="Иванов И.И.",
            reviewed_at="2026-08-27T12:00:00Z",
            fingerprint_sha256="a" * 64,
        )
        self.assertRuntimeKeysConform("feature_comparison", comparison)
        self.assertSchemaValid("feature_comparison", comparison)

    def test_runtime_relation_and_queue_outputs_fit_closed_schema_properties(self):
        relation = classify_applicant_relation(
            {"reading_family": "wage_component"},
            {"status": "matched", "fingerprint_sha256": "a" * 64},
            {"supportive_reading_families": ["wage_component"]},
            current_fingerprint_sha256="b" * 64,
        )
        self.assertTrue(relation["stale"])
        self.assertRuntimeKeysConform("applicant_relation", relation)
        self.assertSchemaValid("applicant_relation", relation)

        queue = build_explainable_queue(
            [
                {
                    "candidate_id": "candidate-1",
                    "chain_id": "chain-1",
                    "document_id": "document-1",
                    "court_id": "2kas",
                    "stratum_id": "post-event",
                    "lane": "exact_norm",
                }
            ],
            quotas={"court_id": {"2kas": 1}},
        )
        self.assertRuntimeKeysConform("review_queue", queue)
        for item in queue["items"]:
            self.assertRuntimeKeysConform("review_queue_item", item)
            self.assertSchemaValid("review_queue_item", item)

    def test_real_position_status_report_bridge_and_handoff_instances_validate(self):
        position = {
            "position_card_id": "position-1",
            "chain_id": "chain-1",
            "document_id": "document-1",
            "court_id": "2kas",
            "decision_date": "2025-12-04",
            "official_url": "https://2kas.sudrf.ru/example",
            "document_sha256": "a" * 64,
            "speaker": "court",
            "proposition": "Премия входит в систему оплаты труда.",
            "quote": "премия является частью заработной платы",
            "quote_locator": "абзац 18",
            "quote_verified": True,
            "full_text_reviewed": True,
            "norm_edition_id": "edition-1",
            "material_facts": ["премия начисляется ежемесячно"],
            "comparison_features": [
                {
                    "feature_id": "payment_kind",
                    "value": "ежемесячная премия",
                    "status": "verified",
                    "material": True,
                    "source": {
                        "document_id": "document-1",
                        "quote_locator": "абзац 18",
                    },
                }
            ],
            "reasoning_to_outcome": "Этот вывод повлёк взыскание.",
            "outcome_materiality": "necessary_to_outcome",
            "alternative_grounds": [],
            "reading_family": "wage_component",
            "outcome": "частичное удовлетворение",
            "remedy": "взыскание премии",
            "coder": "И.И. Иванов",
            "human_review": "approved",
            "adverse_buckets": ["opposite_reading"],
        }
        self.assertSchemaValid("position_card", position)
        temporal = analyze_case_relative_dynamics(
            [position],
            {
                "position-1": {
                    "status": "matched",
                    "fingerprint_sha256": "b" * 64,
                    "review_provenance": {"status": "approved"},
                }
            },
            {
                "position-1": {
                    "relation": "supports",
                    "fingerprint_sha256": "b" * 64,
                    "human_review": "approved",
                    "stale": False,
                }
            },
            fingerprint_sha256="b" * 64,
        )
        self.assertSchemaValid("case_temporal_analysis", temporal)

        bridge = {
            "norm_ref": "ст. 135 ТК РФ",
            "applicant_case_meaning": "Премия снижена без критерия.",
            "corpus_observation": "Есть сопоставимая проверенная позиция.",
            "constitutional_consequence": "Вознаграждение становится непредсказуемым.",
            "ordinary_remedy_analysis": "Обычное толкование не устранило проблему.",
            "supporting_position_card_ids": ["position-1"],
            "adverse_position_card_ids": [],
            "fingerprint_sha256": "b" * 64,
            "maximum_permitted_claim": "bounded_observed_corpus",
            "claim_wording": "В раскрытом корпусе наблюдается проверенная позиция.",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:00:00Z",
            "human_review": "approved",
        }
        self.assertSchemaValid("normative_bridge", bridge)

        status = derive_research_status({"plan_frozen": False})
        self.assertSchemaValid("derived_status", status)
        request_payload = bind_request_payload(
            {
                "drafting_ready": False,
                "questions": ["Что показывает корпус?"],
                "claim_bindings": [
                    {
                        "claim_id": "claim-1",
                        "claim_sha256": "1" * 64,
                        "source_locator": "жалоба.md#абзац-12",
                    }
                ],
            }
        )
        handoff = create_handoff(
            source_skill="ksrf-cassation-judicial-meaning",
            target_skill="ksrf-complaint-cycle",
            run_id="run-1",
            plan_sha256="c" * 64,
            evidence_sha256="d" * 64,
            payload_type="unproven_research_questions",
            payload=request_payload,
            limitations=[],
            created_at="2026-08-27T12:00:00Z",
        )
        self.assertSchemaValid("handoff_envelope", handoff)

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            manifest = write_offline_report(
                {
                    "run_id": "run-1",
                    "plan_sha256": "c" * 64,
                    "evidence_sha256": "d" * 64,
                    "fingerprint_sha256": "b" * 64,
                    "state": {"plan_frozen": False},
                },
                Path(tmp) / "report.html",
                Path(tmp) / "manifest.json",
            )
        self.assertSchemaValid("report_manifest", manifest)

    def test_fail_closed_review_and_status_enums_are_explicit(self):
        adverse = {
            "opposite_reading",
            "narrower_reading",
            "alternative_ground",
            "later_authority",
        }
        self.assertEqual(
            adverse,
            set(
                self.definitions["adverse_review"]["properties"]["completed_buckets"][
                    "items"
                ]["enum"]
            ),
        )
        self.assertEqual(
            adverse,
            set(self.definitions["adverse_buckets"]["required"]),
        )
        self.assertEqual(
            {
                "approval_stale",
                "plan_not_frozen",
                "case_fingerprint_incomplete",
                "collection_incomplete",
                "coding_incomplete",
                "comparison_review_incomplete",
                "applicant_relation_incomplete",
                "adverse_review_incomplete",
                "coverage_review_incomplete",
                "normative_bridge_incomplete",
                "analysis_incomplete",
                "temporal_analysis_incomplete",
                "human_review_pending",
                "candidate_review_pending",
                "validation_incomplete",
                "drafting_ready",
            },
            set(self.definitions["derived_status"]["properties"]["code"]["enum"]),
        )
        self.assertEqual(
            {
                "unproven_research_questions",
                "approved_bounded_findings",
                "authority_cards",
            },
            set(self.definitions["handoff_envelope"]["properties"]["payload_type"]["enum"]),
        )
        payload = self.definitions["handoff_envelope"]["properties"]["payload"]
        self.assertEqual(
            {
                "#/definitions/handoff_request_payload",
                "#/definitions/handoff_approved_payload",
                "#/definitions/handoff_authority_cards_payload",
            },
            {item["$ref"] for item in payload["oneOf"]},
        )
        for definition_name in (
            "handoff_approved_payload",
            "handoff_authority_cards_payload",
        ):
            definition = self.definitions[definition_name]
            self.assertIn("quality_bindings", definition["required"])
            quality = definition["properties"]["quality_bindings"]
            self.assertEqual(5, quality["minItems"])
            self.assertTrue(quality["uniqueItems"])

    def test_handoff_quality_bindings_reference_closed_mirrored_contracts(self):
        quality_definitions = {
            "chain_stage_propagation": "chain_propagation_result",
            "uncertainty_profile": "uncertainty_profile",
            "coding_audit_plan": "coding_audit_plan",
            "coding_reliability": "coding_reliability",
            "prefiling_refresh": "prefiling_refresh",
        }
        for definition_name in {
            "chain_meaning_trajectory",
            "uncertainty_dimension",
            *quality_definitions.values(),
        }:
            with self.subTest(definition=definition_name):
                definition = self.definitions[definition_name]
                expected_version = (
                    "1.1"
                    if definition_name
                    in {"coding_audit_plan", "coding_reliability", "prefiling_refresh"}
                    else "1.0"
                )
                self.assertEqual(expected_version, definition["x-contract-version"])
                self.assertIs(definition["additionalProperties"], False)

        binding = self.definitions["handoff_quality_binding"]
        artifact_refs = {
            item["$ref"].removeprefix("#/definitions/")
            for item in binding["properties"]["artifact"]["oneOf"]
        }
        self.assertEqual(set(quality_definitions.values()), artifact_refs)
        conditional_refs = {
            item["if"]["properties"]["quality_type"]["const"]:
            item["then"]["properties"]["artifact"]["$ref"].removeprefix(
                "#/definitions/"
            )
            for item in binding["allOf"]
        }
        self.assertEqual(quality_definitions, conditional_refs)

        prefiling = self.definitions["prefiling_refresh"]
        self.assertEqual(
            [
                "pending_treatment_ids",
                "verified_treatment_ids",
                "rejected_treatment_ids",
                "superseded_treatment_ids",
            ],
            prefiling["x-pairwise-disjoint"],
        )
        self.assertTrue(
            {
                "treatment_chronology_issue_ids",
                "malformed_refresh_entry_ids",
                "malformed_coverage_gap_ids",
                "refresh_plan_contract_valid",
                "refresh_plan_as_of",
                "refresh_plan_max_age_seconds",
                "refresh_plan_evidence_digest",
            }.issubset(prefiling["required"])
        )
        for key in ("baseline_corpus_digest", "current_corpus_digest"):
            self.assertEqual(
                "#/definitions/sha256",
                prefiling["properties"][key]["$ref"],
            )

        self.assertIn(
            "observations_sha256",
            self.definitions["chain_propagation_result"]["required"],
        )
        self.assertTrue(
            {"malformed_position_card_refs", "malformed_trajectory_refs"}.issubset(
                self.definitions["uncertainty_profile"]["required"]
            )
        )
        invalid_audit_fields = {
            "invalid_screening_record_ids",
            "invalid_primary_record_ids",
        }
        self.assertTrue(
            invalid_audit_fields.issubset(
                self.definitions["coding_audit_plan"]["required"]
            )
        )
        self.assertTrue(
            (
                invalid_audit_fields
                | {
                    "audit_plan_input_sha256",
                    "audit_plan_contract_valid",
                    "audit_decisions_sha256",
                    "adjudications_sha256",
                    "invalid_audit_record_ids",
                    "invalid_adjudication_record_ids",
                }
            ).issubset(self.definitions["coding_reliability"]["required"])
        )

        audit_payload = {
            "schema_version": "1.0",
            "plan_sha256": "0" * 64,
            "screening_sha256": "1" * 64,
            "primary_coding_sha256": "2" * 64,
            "selection_method": "canonical_sha256_rank",
            "sample_size": 1,
            "exclusion_sample_size": 0,
            "sample_candidate_ids": ["candidate-1"],
            "exclusion_sample_candidate_ids": [],
            "required_candidate_ids": ["candidate-1"],
            "invalid_screening_record_ids": [],
            "invalid_primary_record_ids": [],
            "frozen": True,
            "audit_plan_sha256": "3" * 64,
        }
        valid_binding = {
            "quality_type": "coding_audit_plan",
            "artifact_sha256": "4" * 64,
            "artifact": audit_payload,
        }
        self.assertSchemaValid("handoff_quality_binding", valid_binding)
        audit_validator = Draft202012Validator(
            {
                "$schema": self.schema["$schema"],
                "$ref": "#/definitions/coding_audit_plan",
                "definitions": self.definitions,
            },
            format_checker=FormatChecker(),
        )
        for label, changes in (
            ("boolean sample size", {"sample_size": True}),
            (
                "duplicate sample IDs",
                {
                    "sample_size": 2,
                    "sample_candidate_ids": ["candidate-1", "candidate-1"],
                },
            ),
        ):
            with self.subTest(label=label):
                invalid_audit = {**audit_payload, **changes}
                self.assertTrue(list(audit_validator.iter_errors(invalid_audit)))
        mislabeled = {**valid_binding, "quality_type": "prefiling_refresh"}
        validator = Draft202012Validator(
            {
                "$schema": self.schema["$schema"],
                "$ref": "#/definitions/handoff_quality_binding",
                "definitions": self.definitions,
            },
            format_checker=FormatChecker(),
        )
        self.assertTrue(list(validator.iter_errors(mislabeled)))

    def test_public_cache_and_source_contract_enums_are_explicit(self):
        self.assertEqual(
            {
                "official_enumerator_observation",
                "official_user_seed",
                "official_authority_seed",
                "discovery_only",
            },
            set(self.definitions["public_cache_seed"]["properties"]["role"]["enum"]),
        )
        funnel_statuses = {
            "enumerated",
            "card",
            "document_link",
            "payload_validated",
            "full_text_extracted",
            "indexed",
            "screened",
            "coded",
            "approved_independent_chain",
            "blocked",
            "retryable_error",
            "official_page_no_text",
            "unextractable",
            "ocr_pending",
            "human_verification_pending",
        }
        self.assertEqual(
            funnel_statuses,
            set(self.definitions["funnel_item"]["properties"]["status"]["enum"]),
        )
        self.assertEqual(
            {
                "applies",
                "follows",
                "distinguishes",
                "limits",
                "rejects",
                "supersedes",
                "unclear",
                "does_not_reach",
            },
            set(self.definitions["treatment_edge"]["properties"]["treatment_type"]["enum"]),
        )
        self.assertEqual(
            {"candidate", "verified", "rejected", "superseded"},
            set(self.definitions["treatment_edge"]["properties"]["status"]["enum"]),
        )
        self.assertEqual(
            {"official", "official_unconfigured"},
            set(self.definitions["enumerator_manifest"]["properties"]["source_role"]["enum"]),
        )
        self.assertEqual(
            {
                "not_applicable",
                "not_configured",
                "observed_only",
                "closed_declared_enumeration",
            },
            set(self.definitions["route_coverage_result"]["properties"]["status"]["enum"]),
        )
        self.assertEqual(
            {"confirmed", "unconfirmed", "needs_merge_split_review", "outside_configured_scope"},
            set(self.definitions["source_observation"]["properties"]["identity_status"]["enum"]),
        )
        self.assertEqual(
            {"observed_only", "closed_declared_enumerations"},
            set(self.definitions["source_reconciliation"]["properties"]["overall_status"]["enum"]),
        )
        self.assertEqual(
            {"official_verified"},
            set(self.definitions["promotion_record"]["properties"]["status"]["enum"]),
        )


if __name__ == "__main__":
    unittest.main()
