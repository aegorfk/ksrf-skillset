import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from judicial_meaning import practice_quality
from judicial_meaning.casework import (
    build_explainable_queue,
    analyze_case_relative_dynamics,
    classify_applicant_relation,
    compare_case_features,
    prepare_casework,
)
from judicial_meaning.handoff_workbench import bind_request_payload, create_handoff
from judicial_meaning.reporting import derive_research_status, write_offline_report
from tests import test_practice_quality


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_ROOT / "schemas" / "case-relative-workbench.v1.json"
PRACTICE_SCHEMA_PATH = SKILL_ROOT / "schemas" / "practice-quality.v1.json"


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
            self.assertEqual(6, quality["minItems"])
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
        self.assertEqual(2, len(binding["oneOf"]))
        standard_binding, receipt_binding = binding["oneOf"]
        artifact_refs = {
            item["$ref"].removeprefix("#/definitions/")
            for item in standard_binding["properties"]["artifact"]["oneOf"]
        }
        self.assertEqual(set(quality_definitions.values()), artifact_refs)
        conditional_refs = {
            item["if"]["properties"]["quality_type"]["const"]:
            item["then"]["properties"]["artifact"]["$ref"].removeprefix(
                "#/definitions/"
            )
            for item in standard_binding["allOf"]
        }
        self.assertEqual(quality_definitions, conditional_refs)
        self.assertEqual(
            "coding_audit_finalization_receipt",
            receipt_binding["properties"]["quality_type"]["const"],
        )
        self.assertEqual(
            "#/definitions/coding_audit_finalization_receipt",
            receipt_binding["properties"]["artifact"]["$ref"],
        )
        self.assertEqual(
            {
                "quality_type",
                "artifact_sha256",
                "artifact",
                "expected_receipt_sha256",
            },
            set(receipt_binding["required"]),
        )
        self.assertIs(standard_binding["additionalProperties"], False)
        self.assertIs(receipt_binding["additionalProperties"], False)

        origin = self.definitions["coding_reliability_origin"]
        self.assertEqual(
            {
                "status",
                "reason_codes",
                "expected_receipt_sha256",
                "reliability_contract_valid",
                "receipt_contract_valid",
                "receipt_self_digest_valid",
                "external_receipt_digest_valid",
                "reliability_file_digest_valid",
                "audit_plan_digest_valid",
                "candidate_population_valid",
                "usable_for_claim",
            },
            set(origin["required"]),
        )
        self.assertEqual(
            {"missing", "compatibility_only", "native_finalization_bound"},
            set(origin["properties"]["status"]["enum"]),
        )
        profile = self.definitions["uncertainty_profile"]
        self.assertIn("coding_reliability_origin", profile["properties"])
        self.assertTrue(
            {
                "coding_audit_finalization_receipt",
                "expected_finalization_receipt_sha256",
            }.issubset(profile["properties"]["input_sha256s"]["properties"])
        )

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

    def test_native_receipt_candidate_ids_use_the_runtime_identifier_contract(self):
        candidate = self.definitions["coding_audit_candidate_id"]
        validator = Draft202012Validator(candidate)
        self.assertTrue(
            validator.is_valid("audit-candidate-sha256:" + "a" * 64)
        )
        self.assertFalse(validator.is_valid("candidate-1"))

        receipt = self.definitions["coding_audit_finalization_receipt"]
        candidate_refs = (
            receipt["properties"]["candidate_ids"]["items"],
            receipt["properties"]["required_difference_pairs"]["items"]
            ["properties"]["candidate_id"],
            receipt["properties"]["resolved_candidate_ids"]["items"],
            receipt["properties"]["resolved_field_populations"]["items"]
            ["properties"]["candidate_id"],
        )
        self.assertEqual(
            {"#/definitions/coding_audit_candidate_id"},
            {item["$ref"] for item in candidate_refs},
        )

    def test_stable_schemas_disclose_native_cross_artifact_runtime_invariants(self):
        schemas = (
            self.schema,
            json.loads(PRACTICE_SCHEMA_PATH.read_text(encoding="utf-8")),
        )
        for schema in schemas:
            with self.subTest(schema=schema.get("$id")):
                profile_text = " ".join(
                    schema["definitions"]["uncertainty_profile"][
                        "x-runtime-invariants"
                    ]
                )
                receipt_text = " ".join(
                    schema["definitions"]["coding_audit_finalization_receipt"][
                        "x-runtime-invariants"
                    ]
                )
                for marker in (
                    "coding_reliability_origin",
                    "input_sha256s",
                    "expected_finalization_receipt_sha256",
                    "claim_use_ready",
                ):
                    self.assertIn(marker, profile_text)
                for marker in (
                    "exactly one trailing LF",
                    "audit_plan_sha256",
                    "candidate_ids",
                    "receipt_sha256",
                    "separately retained",
                ):
                    self.assertIn(marker, receipt_text)

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
        invalid_standard_binding = {
            **valid_binding,
            "expected_receipt_sha256": "5" * 64,
        }
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
        self.assertTrue(list(validator.iter_errors(invalid_standard_binding)))
        self.assertTrue(list(validator.iter_errors(mislabeled)))

    def test_native_reliability_doctor_report_schema_is_closed_and_rooted(self):
        schema = json.loads(PRACTICE_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.assertEqual("1.5", schema["contract_version"])
        self.assertEqual(
            1,
            schema["oneOf"].count(
                {"$ref": "#/definitions/native_reliability_doctor_report"}
            ),
        )
        definition = schema["definitions"]["native_reliability_doctor_report"]
        self.assertFalse(definition["additionalProperties"])
        validator = Draft202012Validator(
            {
                "$schema": schema["$schema"],
                "$ref": "#/definitions/native_reliability_doctor_report",
                "definitions": schema["definitions"],
            }
        )
        report = {
            "schema_version": "1.0",
            "artifact_type": "native_reliability_doctor_report",
            "status": "valid",
            "native_relation_valid": True,
            "reason_codes": [],
            "checks": {
                "coding_reliability_present": True,
                "coding_reliability_readable": True,
                "coding_reliability_contract_valid": True,
                "coding_reliability_complete": True,
                "finalization_receipt_present": True,
                "finalization_receipt_readable": True,
                "finalization_receipt_contract_valid": True,
                "expected_receipt_sha256_present": True,
                "expected_receipt_sha256_valid": True,
                "receipt_self_digest_valid": True,
                "external_receipt_digest_valid": True,
                "coding_reliability_file_digest_valid": True,
                "audit_plan_digest_valid": True,
                "candidate_population_valid": True,
            },
            "remediation": [],
            "scope": {
                "technical_lineage_only": True,
                "consumer_revalidation_required": True,
                "reviewer_identity_authenticated": False,
                "legal_readiness": False,
                "filing_authorized": False,
            },
        }
        self.assertEqual([], list(validator.iter_errors(report)))
        Draft202012Validator(schema).validate(report)

        remediation_messages = {
            "check_local_read_access": (
                "Проверьте, что указанный локальный файл существует и доступен "
                "для чтения; команда не будет его изменять."
            ),
            "use_original_finalizer_files": (
                "Используйте исходные файлы успешной финализации и не "
                "исправляйте их JSON вручную."
            ),
            "provide_exact_triple": (
                "Передайте оба неизменённых файла финализации и отдельно "
                "сохранённый SHA-256 из её успешного стандартного вывода."
            ),
            "retain_external_digest": (
                "Берите ожидаемый SHA-256 только из стандартного вывода успешно "
                "завершившейся финализации и не восстанавливайте его из квитанции."
            ),
            "recover_in_new_sibling": (
                "Повторите финализацию из тех же неизменённых входов в новой "
                "соседней папке и побайтово сравните результат."
            ),
        }

        def state_report(status, reason_codes, check_changes, remediation_codes):
            value = copy.deepcopy(report)
            value.update(
                {
                    "status": status,
                    "native_relation_valid": False,
                    "reason_codes": reason_codes,
                    "remediation": [
                        {
                            "code": code,
                            "message_ru": remediation_messages[code],
                        }
                        for code in remediation_codes
                    ],
                }
            )
            value["checks"].update(check_changes)
            return value

        unreadable_report = state_report(
            "unreadable",
            ["coding_reliability_unreadable"],
            {
                "coding_reliability_readable": False,
                "coding_reliability_contract_valid": None,
                "coding_reliability_complete": None,
                "coding_reliability_file_digest_valid": None,
                "audit_plan_digest_valid": None,
                "candidate_population_valid": None,
            },
            ["check_local_read_access"],
        )
        invalid_report = state_report(
            "invalid",
            ["expected_finalization_receipt_sha256_invalid"],
            {
                "expected_receipt_sha256_valid": False,
                "external_receipt_digest_valid": None,
            },
            ["retain_external_digest", "recover_in_new_sibling"],
        )
        incomplete_report = state_report(
            "incomplete",
            ["expected_finalization_receipt_sha256_missing"],
            {
                "expected_receipt_sha256_present": False,
                "expected_receipt_sha256_valid": None,
                "external_receipt_digest_valid": None,
            },
            [
                "provide_exact_triple",
                "retain_external_digest",
                "recover_in_new_sibling",
            ],
        )
        mismatch_report = state_report(
            "mismatch",
            ["external_finalization_receipt_digest_mismatch"],
            {"external_receipt_digest_valid": False},
            ["recover_in_new_sibling"],
        )
        self_mismatch_report = state_report(
            "mismatch",
            ["finalization_receipt_self_digest_mismatch"],
            {
                "receipt_self_digest_valid": False,
                "external_receipt_digest_valid": None,
            },
            ["recover_in_new_sibling"],
        )
        for candidate in (
            unreadable_report,
            invalid_report,
            incomplete_report,
            mismatch_report,
            self_mismatch_report,
        ):
            with self.subTest(valid_status=candidate["status"]):
                self.assertEqual([], list(validator.iter_errors(candidate)))
                Draft202012Validator(schema).validate(candidate)

        invalid_variants = (
            {**report, "unexpected": "private"},
            {
                **report,
                "checks": {
                    key: value
                    for key, value in report["checks"].items()
                    if key != "coding_reliability_complete"
                },
            },
            {**report, "reason_codes": ["private_input_value"]},
            {
                **report,
                "checks": {**report["checks"], "private_check": False},
            },
            {
                **report,
                "scope": {**report["scope"], "private_scope": False},
            },
            {
                **report,
                "remediation": [
                    {
                        "code": "provide_exact_triple",
                        "message_ru": "Произвольный текст",
                    }
                ],
            },
            {**report, "status": "mismatch", "native_relation_valid": True},
            {**unreadable_report, "reason_codes": []},
            {
                **unreadable_report,
                "reason_codes": ["coding_reliability_json_invalid"],
            },
            {**invalid_report, "reason_codes": []},
            {
                **invalid_report,
                "reason_codes": ["coding_reliability_unreadable"],
            },
            {
                **incomplete_report,
                "reason_codes": [
                    "coding_reliability_contract_invalid",
                    "coding_reliability_incomplete",
                ],
            },
            {
                **mismatch_report,
                "reason_codes": [
                    "coding_reliability_incomplete",
                    "external_finalization_receipt_digest_mismatch",
                ],
            },
            {
                **mismatch_report,
                "checks": {
                    **mismatch_report["checks"],
                    "external_receipt_digest_valid": True,
                },
            },
            {
                **mismatch_report,
                "checks": {
                    **mismatch_report["checks"],
                    "external_receipt_digest_valid": True,
                    "candidate_population_valid": False,
                },
            },
            {
                **self_mismatch_report,
                "checks": {
                    **self_mismatch_report["checks"],
                    "external_receipt_digest_valid": True,
                },
            },
            {
                **unreadable_report,
                "checks": {
                    **unreadable_report["checks"],
                    "coding_reliability_readable": True,
                },
                "remediation": invalid_report["remediation"],
            },
            {
                **invalid_report,
                "checks": {
                    **invalid_report["checks"],
                    "expected_receipt_sha256_valid": True,
                    "external_receipt_digest_valid": True,
                },
                "remediation": unreadable_report["remediation"],
            },
            {
                **incomplete_report,
                "checks": {
                    **incomplete_report["checks"],
                    "expected_receipt_sha256_present": True,
                    "expected_receipt_sha256_valid": True,
                    "external_receipt_digest_valid": True,
                },
            },
            {
                **self_mismatch_report,
                "reason_codes": [
                    "finalization_receipt_self_digest_mismatch",
                    "external_finalization_receipt_digest_mismatch",
                ],
                "checks": {
                    **self_mismatch_report["checks"],
                    "external_receipt_digest_valid": False,
                },
            },
            {
                **incomplete_report,
                "remediation": list(reversed(incomplete_report["remediation"])),
            },
            {
                **mismatch_report,
                "remediation": [
                    unreadable_report["remediation"][0],
                    mismatch_report["remediation"][0],
                ],
            },
            {
                **invalid_report,
                "remediation": [mismatch_report["remediation"][0]],
            },
            {**incomplete_report, "remediation": []},
        )
        for invalid in invalid_variants:
            with self.subTest(invalid=invalid):
                self.assertTrue(list(validator.iter_errors(invalid)))

    def test_native_reliability_doctor_runtime_states_fit_exact_schema(self):
        schema = json.loads(PRACTICE_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(
            {
                "$schema": schema["$schema"],
                "$ref": "#/definitions/native_reliability_doctor_report",
                "definitions": schema["definitions"],
            }
        )
        fixture = test_practice_quality.PracticeQualityTests()
        reliability, receipt, expected = fixture.native_reliability_inputs(
            practice_quality
        )
        reliability_file_sha256 = fixture.reliability_file_sha256(reliability)

        def build(
            reliability_value,
            receipt_value,
            expected_value,
            *,
            coding_present=True,
            coding_readable=True,
            coding_canonical=True,
            coding_file_sha256=reliability_file_sha256,
            receipt_present=True,
            receipt_readable=True,
            input_reason_codes=(),
        ):
            return practice_quality.build_native_reliability_doctor_report(
                reliability_value,
                receipt_value,
                expected_value,
                coding_reliability_present=coding_present,
                coding_reliability_readable=coding_readable,
                coding_reliability_canonical_bytes_valid=coding_canonical,
                coding_reliability_file_sha256=coding_file_sha256,
                finalization_receipt_present=receipt_present,
                finalization_receipt_readable=receipt_readable,
                input_reason_codes=input_reason_codes,
            )

        reports = [build(reliability, receipt, expected)]
        reports.append(
            build(
                None,
                None,
                None,
                coding_present=False,
                coding_readable=None,
                coding_canonical=None,
                coding_file_sha256=None,
                receipt_present=False,
                receipt_readable=None,
            )
        )
        reports.append(
            build(
                None,
                None,
                None,
                coding_readable=False,
                coding_canonical=None,
                coding_file_sha256=None,
                receipt_present=False,
                receipt_readable=None,
                input_reason_codes=("coding_reliability_unreadable",),
            )
        )
        reports.append(
            build(
                reliability,
                receipt,
                expected,
                coding_canonical=False,
            )
        )
        reports.append(
            build(
                reliability,
                None,
                expected,
                receipt_readable=False,
            )
        )
        reports.append(
            build(
                None,
                receipt,
                expected,
                coding_canonical=None,
                coding_file_sha256="0" * 64,
            )
        )
        reports.append(
            build(
                {"schema_version": "1.0"},
                receipt,
                expected,
                coding_file_sha256="0" * 64,
            )
        )
        reports.append(build(reliability, None, expected))
        reports.append(build(reliability, {}, expected))
        reports.append(build(reliability, receipt, "НЕ-SHA-256"))
        reports.append(
            build(
                None,
                None,
                None,
                coding_readable=False,
                coding_canonical=None,
                coding_file_sha256=None,
                input_reason_codes=("coding_reliability_unreadable",),
            )
        )

        incomplete = copy.deepcopy(fixture.complete_reliability(practice_quality))
        incomplete["complete"] = False
        incomplete_payload = dict(incomplete)
        incomplete_payload.pop("evidence_sha256")
        incomplete["evidence_sha256"] = practice_quality.canonical_digest(
            incomplete_payload
        )
        reports.append(
            build(
                incomplete,
                None,
                None,
                coding_file_sha256=fixture.reliability_file_sha256(incomplete),
                receipt_present=False,
                receipt_readable=None,
            )
        )

        def resigned(**changes):
            unsigned = copy.deepcopy(receipt)
            unsigned.pop("receipt_sha256")
            unsigned.update(changes)
            signed = {
                **unsigned,
                "receipt_sha256": practice_quality.canonical_digest(unsigned),
            }
            return signed, signed["receipt_sha256"]

        self_mismatch = {**receipt, "plan_sha256": "0" * 64}
        file_mismatch = resigned(coding_reliability_file_sha256="0" * 64)
        plan_mismatch = resigned(audit_plan_sha256="0" * 64)
        candidate_mismatch = resigned(
            candidate_ids=["audit-candidate-sha256:" + "b" * 64]
        )
        reports.extend(
            (
                build(reliability, self_mismatch, expected),
                build(reliability, receipt, "0" * 64),
                build(reliability, *file_mismatch),
                build(reliability, *plan_mismatch),
                build(reliability, *candidate_mismatch),
            )
        )
        combined_receipt, combined_expected = resigned(
            coding_reliability_file_sha256="0" * 64,
            audit_plan_sha256="0" * 64,
            candidate_ids=["audit-candidate-sha256:" + "b" * 64],
        )
        reports.append(build(reliability, combined_receipt, "0" * 64))
        reports.append(
            build(
                reliability,
                {**combined_receipt, "plan_sha256": "0" * 64},
                combined_expected,
            )
        )

        reason_enum = set(
            schema["definitions"]["native_reliability_doctor_report"]
            ["properties"]["reason_codes"]["items"]["enum"]
        )
        self.assertEqual(
            reason_enum,
            {
                reason
                for value in reports
                for reason in value["reason_codes"]
            },
        )
        self.assertEqual(
            {"valid", "incomplete", "mismatch", "invalid", "unreadable"},
            {value["status"] for value in reports},
        )
        for value in reports:
            with self.subTest(
                status=value["status"], reasons=value["reason_codes"]
            ):
                errors = sorted(
                    validator.iter_errors(value), key=lambda item: list(item.path)
                )
                self.assertEqual([], [error.message for error in errors])

        reason_examples = {}
        remediation_examples = {}
        for value in reports:
            for reason in value["reason_codes"]:
                reason_examples.setdefault(reason, value)
            for item in value["remediation"]:
                remediation_examples.setdefault(item["code"], value)
        self.assertEqual(reason_enum, set(reason_examples))
        self.assertEqual(
            {
                "check_local_read_access",
                "use_original_finalizer_files",
                "provide_exact_triple",
                "retain_external_digest",
                "recover_in_new_sibling",
            },
            set(remediation_examples),
        )
        for reason, value in reason_examples.items():
            with self.subTest(missing_reason=reason):
                missing_reason = copy.deepcopy(value)
                missing_reason["reason_codes"].remove(reason)
                self.assertTrue(list(validator.iter_errors(missing_reason)))
        for code, value in remediation_examples.items():
            with self.subTest(missing_remediation=code):
                missing_remediation = copy.deepcopy(value)
                missing_remediation["remediation"] = [
                    item
                    for item in missing_remediation["remediation"]
                    if item["code"] != code
                ]
                self.assertTrue(list(validator.iter_errors(missing_remediation)))
        ordered = max(reports, key=lambda value: len(value["remediation"]))
        self.assertEqual(5, len(ordered["remediation"]))
        reordered = copy.deepcopy(ordered)
        reordered["remediation"].reverse()
        self.assertTrue(list(validator.iter_errors(reordered)))

    def test_native_finalization_comparison_schema_is_additive_closed_and_exact(self):
        schema = json.loads(PRACTICE_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.assertEqual("1.5", schema["contract_version"])
        self.assertEqual(
            1,
            schema["oneOf"].count(
                {
                    "$ref": (
                        "#/definitions/"
                        "native_finalization_comparison_report"
                    )
                }
            ),
        )
        definition = schema["definitions"][
            "native_finalization_comparison_report"
        ]
        self.assertFalse(definition["additionalProperties"])
        validator = Draft202012Validator(
            {
                "$schema": schema["$schema"],
                "$ref": (
                    "#/definitions/native_finalization_comparison_report"
                ),
                "definitions": schema["definitions"],
            }
        )
        root_validator = Draft202012Validator(schema)
        fixture = test_practice_quality.PracticeQualityTests()
        checks = fixture.native_finalization_comparison_checks()
        reports = [
            practice_quality.build_native_finalization_comparison_report(
                checks=checks
            )
        ]
        reports.extend(
            practice_quality.build_native_finalization_comparison_report(
                checks=fixture.comparison_checks_with_failure(check)
            )
            for check in checks
        )
        early_drift_checks = fixture.comparison_checks_with_failure(
            "uncertain_directory_readable"
        )
        early_drift_checks["final_recapture_valid"] = False
        early_drift = (
            practice_quality.build_native_finalization_comparison_report(
                checks=early_drift_checks
            )
        )
        drift_after_mismatch = (
            practice_quality.build_native_finalization_comparison_report(
                checks=fixture.native_finalization_comparison_checks(
                    uncertain_internal_relation_valid=False,
                    directory_file_bytes_equal=None,
                    final_recapture_valid=False,
                )
            )
        )
        admin_invalid_checks = fixture.comparison_checks_with_failure(
            "uncertain_artifact_contracts_valid"
        )
        admin_invalid_checks["directory_file_bytes_equal"] = False
        admin_invalid_mismatch = (
            practice_quality.build_native_finalization_comparison_report(
                checks=admin_invalid_checks
            )
        )
        reports.extend(
            (early_drift, drift_after_mismatch, admin_invalid_mismatch)
        )
        self.assertEqual(
            {"match", "mismatch", "invalid", "unreadable"},
            {report["status"] for report in reports},
        )
        self.assertEqual(
            set(
                definition["properties"]["reason_codes"]["items"]["enum"]
            ),
            {
                reason
                for report in reports
                for reason in report["reason_codes"]
            },
        )
        reason_order = definition["properties"]["reason_codes"]["items"]["enum"]
        reason_validator = Draft202012Validator(
            {
                "$schema": schema["$schema"],
                "$ref": (
                    "#/definitions/native_finalization_comparison_report/"
                    "properties/reason_codes"
                ),
                "definitions": schema["definitions"],
            }
        )
        self.assertEqual([], list(reason_validator.iter_errors(reason_order)))
        for earlier_index in range(len(reason_order) - 1):
            swapped = list(reason_order)
            swapped[earlier_index], swapped[earlier_index + 1] = (
                swapped[earlier_index + 1],
                swapped[earlier_index],
            )
            with self.subTest(swapped_positions=(earlier_index, earlier_index + 1)):
                self.assertTrue(list(reason_validator.iter_errors(swapped)))
        for earlier_index, earlier_reason in enumerate(reason_order):
            for later_reason in reason_order[earlier_index + 1 :]:
                with self.subTest(
                    earlier_reason=earlier_reason,
                    later_reason=later_reason,
                ):
                    self.assertEqual(
                        [],
                        list(
                            reason_validator.iter_errors(
                                [earlier_reason, later_reason]
                            )
                        ),
                    )
                    self.assertTrue(
                        list(
                            reason_validator.iter_errors(
                                [later_reason, earlier_reason]
                            )
                        )
                    )
        for report in reports:
            with self.subTest(
                status=report["status"], reasons=report["reason_codes"]
            ):
                self.assertEqual([], list(validator.iter_errors(report)))
                root_validator.validate(report)

        match = reports[0]
        mismatch = next(
            report
            for report in reports
            if report["reason_codes"]
            == ["finalization_directory_bytes_mismatch"]
        )
        invalid = next(
            report
            for report in reports
            if report["reason_codes"]
            == ["expected_finalization_receipt_sha256_invalid"]
        )
        unreadable = next(
            report
            for report in reports
            if report["reason_codes"]
            == ["uncertain_finalization_unreadable"]
        )
        hostile = "СЕКРЕТНЫЙ-ПУТЬ-И-ДАЙДЖЕСТ"
        invalid_variants = (
            {**match, "private_path": hostile},
            {
                **match,
                "checks": {**match["checks"], "private_check": True},
            },
            {
                **match,
                "scope": {**match["scope"], "private_scope": False},
            },
            {**match, "status": "mismatch"},
            {**match, "recovery_comparison_valid": False},
            {**mismatch, "reason_codes": []},
            {
                **mismatch,
                "checks": {
                    **mismatch["checks"],
                    "directory_file_bytes_equal": True,
                },
            },
            {
                **invalid,
                "reason_codes": [
                    "external_finalization_receipt_digest_mismatch"
                ],
            },
            {**unreadable, "status": "invalid"},
            {
                **unreadable,
                "checks": {
                    **unreadable["checks"],
                    "uncertain_directory_private": True,
                },
            },
            {
                **match,
                "checks": {
                    **match["checks"],
                    "directory_file_bytes_equal": None,
                },
            },
            {
                **match,
                "checks": {
                    **match["checks"],
                    "final_recapture_valid": None,
                },
            },
            {
                **early_drift,
                "checks": {
                    **early_drift["checks"],
                    "final_recapture_valid": True,
                },
            },
            {
                **early_drift,
                "checks": {
                    **early_drift["checks"],
                    "directory_file_bytes_equal": False,
                },
            },
            {
                **mismatch,
                "remediation": [
                    {
                        "code": "repeat_after_mismatch",
                        "message_ru": hostile,
                    }
                ],
            },
            {
                **mismatch,
                "remediation": [
                    {
                        **mismatch["remediation"][0],
                        "private": hostile,
                    },
                    *mismatch["remediation"][1:],
                ],
            },
            {
                **drift_after_mismatch,
                "remediation": [
                    *drift_after_mismatch["remediation"],
                    mismatch["remediation"][-1],
                ],
            },
            {
                **admin_invalid_mismatch,
                "remediation": [
                    *admin_invalid_mismatch["remediation"],
                    mismatch["remediation"][-1],
                ],
            },
        )
        for forged in invalid_variants:
            with self.subTest(forged=forged):
                self.assertTrue(list(validator.iter_errors(forged)))

        combined_checks = fixture.comparison_checks_with_failure(
            "uncertain_directory_readable"
        )
        combined_checks["expected_receipt_sha256_valid"] = False
        combined_checks["repeated_external_receipt_digest_valid"] = None
        combined_checks["repeated_native_relation_valid"] = None
        combined = practice_quality.build_native_finalization_comparison_report(
            checks=combined_checks
        )
        validator.validate(combined)
        reordered_reasons = copy.deepcopy(combined)
        reordered_reasons["reason_codes"].reverse()
        self.assertTrue(list(validator.iter_errors(reordered_reasons)))
        self.assertGreater(len(combined["remediation"]), 1)
        reordered = copy.deepcopy(combined)
        reordered["remediation"].reverse()
        self.assertTrue(list(validator.iter_errors(reordered)))

    def test_native_review_import_comparison_schema_is_additive_closed_and_exact(self):
        schema = json.loads(PRACTICE_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.assertEqual("1.5", schema["contract_version"])
        reference = {
            "$ref": "#/definitions/native_review_import_comparison_report"
        }
        self.assertEqual(1, schema["oneOf"].count(reference))
        definition = schema["definitions"][
            "native_review_import_comparison_report"
        ]
        self.assertFalse(definition["additionalProperties"])
        self.assertFalse(
            definition["properties"]["checks"]["additionalProperties"]
        )
        self.assertFalse(
            definition["properties"]["scope"]["additionalProperties"]
        )
        for name, remediation_definition in definition["$defs"].items():
            if name.startswith("remediation_") and "after" not in name:
                self.assertFalse(
                    remediation_definition["additionalProperties"]
                )
        validator = Draft202012Validator(
            {
                "$schema": schema["$schema"],
                "$ref": reference["$ref"],
                "definitions": schema["definitions"],
            }
        )
        root_validator = Draft202012Validator(schema)
        fixture = test_practice_quality.PracticeQualityTests()
        match = practice_quality.build_native_review_import_comparison_report(
            checks=fixture.native_review_import_comparison_checks()
        )
        codebook_unreadable = (
            practice_quality.build_native_review_import_comparison_report(
                checks=fixture.review_import_comparison_checks_with_failure(
                    "installed_codebook_readable"
                )
            )
        )
        raw_mismatch = (
            practice_quality.build_native_review_import_comparison_report(
                checks=fixture.review_import_comparison_checks_with_failure(
                    "import_directory_file_bytes_equal"
                )
            )
        )
        manifest_invalid = (
            practice_quality.build_native_review_import_comparison_report(
                checks=fixture.review_import_comparison_checks_with_failure(
                    "expected_manifest_sha256_valid"
                )
            )
        )
        admin_checks = fixture.review_import_comparison_checks_with_failure(
            "uncertain_artifact_contracts_valid"
        )
        admin_checks["import_directory_file_bytes_equal"] = False
        admin_mismatch = (
            practice_quality.build_native_review_import_comparison_report(
                checks=admin_checks
            )
        )
        reports = [
            match,
            codebook_unreadable,
            raw_mismatch,
            manifest_invalid,
            admin_mismatch,
        ]

        self.assertEqual(
            {"match", "mismatch", "invalid", "unreadable"},
            {report["status"] for report in reports},
        )
        reason_order = definition["properties"]["reason_codes"]["items"][
            "enum"
        ]
        self.assertEqual(26, len(reason_order))
        for report in reports:
            with self.subTest(
                status=report["status"], reasons=report["reason_codes"]
            ):
                validator.validate(report)
        root_validator.validate(match)

        reason_validator = Draft202012Validator(
            {
                "$schema": schema["$schema"],
                "$ref": (
                    "#/definitions/native_review_import_comparison_report/"
                    "properties/reason_codes"
                ),
                "definitions": schema["definitions"],
            }
        )
        self.assertEqual([], list(reason_validator.iter_errors(reason_order)))
        reason_rank = {reason: index for index, reason in enumerate(reason_order)}
        for report in reports:
            self.assertEqual(
                sorted(
                    report["reason_codes"],
                    key=reason_rank.__getitem__,
                ),
                report["reason_codes"],
            )

        invalid_variants = (
            {**match, "private_path": "СЕКРЕТНЫЙ-ПУТЬ"},
            {**match, "status": "mismatch"},
            {
                **codebook_unreadable,
                "checks": {
                    **codebook_unreadable["checks"],
                    "installed_codebook_binding_valid": True,
                },
            },
            {
                **admin_mismatch,
                "remediation": [
                    *admin_mismatch["remediation"],
                    raw_mismatch["remediation"][-1],
                ],
            },
        )
        for forged in invalid_variants:
            with self.subTest(forged=forged):
                self.assertTrue(list(validator.iter_errors(forged)))

        combined_checks = fixture.review_import_comparison_checks_with_failure(
            "source_bundle_readable"
        )
        combined_checks["expected_manifest_sha256_valid"] = False
        combined = (
            practice_quality.build_native_review_import_comparison_report(
                checks=combined_checks
            )
        )
        validator.validate(combined)
        self.assertGreater(len(combined["remediation"]), 1)
        self.assertEqual(
            sorted(
                combined["reason_codes"],
                key=reason_rank.__getitem__,
            ),
            combined["reason_codes"],
        )
        reversed_remediation = copy.deepcopy(combined)
        reversed_remediation["remediation"].reverse()
        self.assertNotEqual(combined["remediation"], reversed_remediation["remediation"])
        validator.validate(reversed_remediation)

    def test_native_audit_bundle_comparison_schema_is_additive_closed_and_exact(self):
        schema = json.loads(PRACTICE_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.assertEqual("1.5", schema["contract_version"])
        reference = {
            "$ref": "#/definitions/native_audit_bundle_comparison_report"
        }
        self.assertEqual(1, schema["oneOf"].count(reference))

        definition = schema["definitions"][
            "native_audit_bundle_comparison_report"
        ]
        self.assertEqual("1.0", definition["x-contract-version"])
        self.assertFalse(definition["additionalProperties"])
        self.assertFalse(
            definition["properties"]["checks"]["additionalProperties"]
        )
        self.assertFalse(
            definition["properties"]["scope"]["additionalProperties"]
        )

        expected_checks = (
            "common_parent_valid",
            "directories_distinct",
            "uncertain_bundle_readable",
            "repeated_bundle_readable",
            "uncertain_bundle_private",
            "repeated_bundle_private",
            "uncertain_inventory_exact",
            "repeated_inventory_exact",
            "expected_manifest_sha256_valid",
            "expected_independent_review_packet_sha256_valid",
            "uncertain_bundle_contract_valid",
            "repeated_bundle_contract_valid",
            "uncertain_installed_codebook_readable",
            "repeated_installed_codebook_readable",
            "uncertain_installed_codebook_binding_valid",
            "repeated_installed_codebook_binding_valid",
            "repeated_external_manifest_digest_valid",
            "repeated_external_independent_review_packet_digest_valid",
            "audit_bundle_file_bytes_equal",
            "final_recapture_valid",
        )
        self.assertEqual(
            expected_checks,
            tuple(definition["properties"]["checks"]["required"]),
        )
        self.assertEqual(
            set(expected_checks),
            set(definition["properties"]["checks"]["properties"]),
        )

        expected_reasons = (
            "uncertain_audit_bundle_unreadable",
            "repeated_audit_bundle_unreadable",
            "uncertain_installed_codebook_unreadable",
            "repeated_installed_codebook_unreadable",
            "comparison_input_changed",
            "comparison_topology_invalid",
            "uncertain_audit_bundle_privacy_invalid",
            "repeated_audit_bundle_privacy_invalid",
            "uncertain_audit_bundle_inventory_invalid",
            "repeated_audit_bundle_inventory_invalid",
            "expected_manifest_sha256_invalid",
            "expected_independent_review_packet_sha256_invalid",
            "uncertain_audit_bundle_artifact_contract_invalid",
            "repeated_audit_bundle_artifact_contract_invalid",
            "uncertain_installed_codebook_binding_mismatch",
            "repeated_installed_codebook_binding_mismatch",
            "external_manifest_digest_mismatch",
            "external_independent_review_packet_digest_mismatch",
            "audit_bundle_directory_bytes_mismatch",
        )
        self.assertEqual(
            expected_reasons,
            tuple(
                definition["properties"]["reason_codes"]["items"]["enum"]
            ),
        )
        self.assertTrue(
            any(
                "fixed native-audit-bundle-comparison order" in invariant
                for invariant in definition["x-runtime-invariants"]
            )
        )

        expected_scope = {
            "technical_recovery_comparison_only": True,
            "original_recovery_eligibility_verified": False,
            "recovery_action_authorized": False,
            "repeat_normal_return_verified": False,
            "input_provenance_authenticated": False,
            "external_manifest_digest_provenance_authenticated": False,
            "external_independent_review_packet_digest_provenance_authenticated": False,
            "original_durability_verified": False,
            "source_workspace_reverified": False,
            "result_selection_performed": False,
            "downstream_use_authorized": False,
            "consumer_revalidation_required": True,
            "reviewer_identity_authenticated": False,
            "publication_safe": False,
            "legal_readiness": False,
            "filing_authorized": False,
        }
        scope_schema = definition["properties"]["scope"]
        self.assertEqual(tuple(expected_scope), tuple(scope_schema["required"]))
        self.assertEqual(
            expected_scope,
            {
                key: value["const"]
                for key, value in scope_schema["properties"].items()
            },
        )

        expected_remediation = {
            "check_local_read_access": (
                "Проверьте доступность двух указанных локальных папок пакета и "
                "встроенных справочников, не изменяя их; команда не выполняет "
                "восстановление."
            ),
            "preserve_and_stop": (
                "Остановите использование обоих пакетов и сохраните их "
                "неизменными; команда ничего не исправляет, не выбирает и не "
                "удаляет."
            ),
            "use_safe_complete_siblings": (
                "Сравнивайте только две разные полные приватные семифайловые "
                "папки у одного безопасного родителя; небезопасное или неполное "
                "состояние передайте системному администратору."
            ),
            "retain_successful_repeat_anchors": (
                "Передайте оба SHA-256 только из одной полной строки стандартного "
                "вывода успешно и нормально завершившегося повтора подготовки; "
                "не восстанавливайте их из пакета."
            ),
            "use_exact_installed_codebook": (
                "Используйте только встроенный справочник точной версии, "
                "указанной каждым проверенным манифестом; не подменяйте и не "
                "ищите его по произвольному пути."
            ),
            "administrator_quarantine": (
                "При изменении inode, жёсткой ссылке, ACL, неучтённом или "
                "перемещённом объекте остановите автоматику и передайте состояние "
                "системному администратору для учёта всех ссылок и карантина."
            ),
            "investigate_without_selection": (
                "Не выбирайте и не используйте ни один из несовпавших пакетов; "
                "сохраните их раздельно и исследуйте причину без автоматического "
                "повтора или назначения результата."
            ),
        }
        remediation_definitions = {
            item["properties"]["code"]["const"]: item["properties"][
                "message_ru"
            ]["const"]
            for name, item in definition["$defs"].items()
            if name.startswith("remediation_")
        }
        self.assertEqual(expected_remediation, remediation_definitions)
        self.assertTrue(
            all(
                item["additionalProperties"] is False
                for name, item in definition["$defs"].items()
                if name.startswith("remediation_")
            )
        )

        validator = Draft202012Validator(
            {
                "$schema": schema["$schema"],
                "$ref": reference["$ref"],
                "definitions": schema["definitions"],
            }
        )
        root_validator = Draft202012Validator(schema)
        fixture = test_practice_quality.PracticeQualityTests()
        build_report = (
            practice_quality.build_native_audit_bundle_comparison_report
        )
        match = build_report(
            checks=fixture.native_audit_bundle_comparison_checks()
        )
        unreadable = build_report(
            checks=fixture.audit_bundle_comparison_checks_with_failure(
                "uncertain_bundle_readable"
            )
        )
        invalid = build_report(
            checks=fixture.audit_bundle_comparison_checks_with_failure(
                "expected_manifest_sha256_valid"
            )
        )
        codebook_invalid = build_report(
            checks=fixture.audit_bundle_comparison_checks_with_failure(
                "uncertain_installed_codebook_binding_valid"
            )
        )
        mismatch = build_report(
            checks=fixture.audit_bundle_comparison_checks_with_failure(
                "audit_bundle_file_bytes_equal"
            )
        )
        reports = [
            match,
            unreadable,
            invalid,
            codebook_invalid,
            mismatch,
        ]
        self.assertEqual(
            {"match", "mismatch", "invalid", "unreadable"},
            {report["status"] for report in reports},
        )
        for report in reports:
            with self.subTest(
                status=report["status"], reasons=report["reason_codes"]
            ):
                validator.validate(report)
        root_validator.validate(match)

        reason_reports = [
            build_report(
                checks=fixture.audit_bundle_comparison_checks_with_failure(
                    check
                )
            )
            for check in expected_checks
        ]
        self.assertEqual(
            set(expected_reasons),
            {
                reason
                for report in reason_reports
                for reason in report["reason_codes"]
            },
        )
        reason_rank = {
            reason: index for index, reason in enumerate(expected_reasons)
        }
        for report in reason_reports:
            self.assertEqual(
                sorted(report["reason_codes"], key=reason_rank.__getitem__),
                report["reason_codes"],
            )
            validator.validate(report)

        self.assertEqual([], match["remediation"])
        self.assertEqual(
            ["check_local_read_access"],
            [item["code"] for item in unreadable["remediation"]],
        )
        self.assertEqual(
            ["preserve_and_stop", "retain_successful_repeat_anchors"],
            [item["code"] for item in invalid["remediation"]],
        )
        self.assertEqual(
            ["preserve_and_stop", "use_exact_installed_codebook"],
            [item["code"] for item in codebook_invalid["remediation"]],
        )
        self.assertEqual(
            ["preserve_and_stop", "investigate_without_selection"],
            [item["code"] for item in mismatch["remediation"]],
        )

        invalid_variants = (
            {**match, "private_path": "СЕКРЕТНЫЙ-ПУТЬ"},
            {**match, "status": "mismatch"},
            {**match, "recovery_comparison_valid": False},
            {
                **match,
                "checks": {**match["checks"], "private_check": True},
            },
            {
                **match,
                "checks": {
                    **match["checks"],
                    "audit_bundle_file_bytes_equal": None,
                },
            },
            {
                **unreadable,
                "checks": {
                    **unreadable["checks"],
                    "uncertain_bundle_private": True,
                },
            },
            {
                **invalid,
                "checks": {
                    **invalid["checks"],
                    "repeated_external_manifest_digest_valid": False,
                },
            },
            {
                **mismatch,
                "checks": {
                    **mismatch["checks"],
                    "audit_bundle_file_bytes_equal": True,
                },
            },
            {
                **mismatch,
                "reason_codes": ["comparison_topology_invalid"],
            },
            {
                **match,
                "scope": {
                    **match["scope"],
                    "downstream_use_authorized": True,
                },
            },
            {
                **match,
                "remediation": [
                    {
                        "code": "preserve_and_stop",
                        "message_ru": "СЕКРЕТНЫЙ-ПУТЬ",
                    }
                ],
            },
            {
                **match,
                "remediation": [
                    {
                        "code": "preserve_and_stop",
                        "message_ru": expected_remediation[
                            "preserve_and_stop"
                        ],
                        "private": "СЕКРЕТНЫЙ-ПУТЬ",
                    }
                ],
            },
        )
        for forged in invalid_variants:
            with self.subTest(forged=forged):
                self.assertTrue(list(validator.iter_errors(forged)))

    def test_publication_recovery_diagnostic_schema_is_additive_closed_and_exact(self):
        schema = json.loads(PRACTICE_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.assertEqual("1.5", schema["contract_version"])
        reference = {
            "$ref": (
                "#/definitions/"
                "coding_audit_publication_recovery_diagnostic"
            )
        }
        self.assertEqual(1, schema["oneOf"].count(reference))

        definition = schema["definitions"][
            "coding_audit_publication_recovery_diagnostic"
        ]
        self.assertEqual("1.0", definition["x-contract-version"])
        root_keys = {
            "schema_version",
            "artifact_type",
            "command",
            "error_code",
            "recovery_route",
            "stdout_disposition",
            "message_ru",
            "exit_code",
            "scope",
        }
        scope_values = {
            "diagnostic_only": True,
            "same_destination_retry_allowed": False,
            "recovery_eligibility_verified": False,
            "recovery_action_authorized": False,
            "downstream_use_allowed": False,
            "automatic_retry_performed": False,
            "automatic_delete_performed": False,
            "automatic_quarantine_performed": False,
            "diagnostic_provenance_authenticated": False,
            "publication_safe": False,
            "legal_readiness": False,
            "filing_authorized": False,
        }
        self.assertEqual(root_keys, set(definition["required"]))
        self.assertEqual(root_keys, set(definition["properties"]))
        self.assertFalse(definition["additionalProperties"])
        scope_definition = definition["properties"]["scope"]
        self.assertEqual(set(scope_values), set(scope_definition["required"]))
        self.assertEqual(set(scope_values), set(scope_definition["properties"]))
        self.assertFalse(scope_definition["additionalProperties"])
        for key, expected in scope_values.items():
            self.assertEqual(
                expected,
                scope_definition["properties"][key]["const"],
            )

        commands = (
            "coding-audit-prepare",
            "coding-audit-review-import",
            "coding-audit-finalize",
        )
        correlations = {
            "staging_cleanup_uncertain": (
                "administrator_only",
                "empty_invalid",
            ),
            "publication_state_uncertain": (
                "administrator_only",
                "empty_invalid",
            ),
            "publication_durability_uncertain": (
                "repeat_then_compare_candidate",
                "empty_invalid",
            ),
            "publication_finalization_uncertain": (
                "repeat_then_compare_candidate",
                "empty_invalid",
            ),
            "confirmation_delivery_uncertain": (
                "repeat_then_compare_candidate",
                "empty_partial_or_apparent_complete_invalid",
            ),
        }
        self.assertEqual(
            set(commands),
            set(definition["properties"]["command"]["enum"]),
        )
        self.assertEqual(
            set(correlations),
            set(definition["properties"]["error_code"]["enum"]),
        )
        self.assertEqual(
            {route for route, _ in correlations.values()},
            set(definition["properties"]["recovery_route"]["enum"]),
        )
        self.assertEqual(
            {disposition for _, disposition in correlations.values()},
            set(definition["properties"]["stdout_disposition"]["enum"]),
        )
        self.assertEqual(2, len(definition["allOf"]))
        self.assertTrue(
            all(len(correlation["oneOf"]) == 5 for correlation in definition["allOf"])
        )

        validator = Draft202012Validator(
            {
                "$schema": schema["$schema"],
                "$ref": reference["$ref"],
                "definitions": schema["definitions"],
            }
        )
        root_validator = Draft202012Validator(schema)
        report = {
            "schema_version": "1.0",
            "artifact_type": "coding_audit_publication_recovery_diagnostic",
            "command": commands[0],
            "error_code": "staging_cleanup_uncertain",
            "recovery_route": "administrator_only",
            "stdout_disposition": "empty_invalid",
            "message_ru": "Состояние публикации не подтверждено.",
            "exit_code": 2,
            "scope": scope_values,
        }
        for index, (error_code, pair) in enumerate(correlations.items()):
            route, disposition = pair
            candidate = copy.deepcopy(report)
            candidate.update(
                {
                    "command": commands[index % len(commands)],
                    "error_code": error_code,
                    "recovery_route": route,
                    "stdout_disposition": disposition,
                }
            )
            with self.subTest(valid_pair=error_code):
                validator.validate(candidate)
                root_validator.validate(candidate)

        for missing in root_keys:
            candidate = copy.deepcopy(report)
            del candidate[missing]
            with self.subTest(missing_root=missing):
                self.assertTrue(list(validator.iter_errors(candidate)))
        extra_root = copy.deepcopy(report)
        extra_root["retry_allowed"] = True
        self.assertTrue(list(validator.iter_errors(extra_root)))

        for missing in scope_values:
            candidate = copy.deepcopy(report)
            del candidate["scope"][missing]
            with self.subTest(missing_scope=missing):
                self.assertTrue(list(validator.iter_errors(candidate)))
        extra_scope = copy.deepcopy(report)
        extra_scope["scope"]["human_approval_created"] = False
        self.assertTrue(list(validator.iter_errors(extra_scope)))

        for key, expected in scope_values.items():
            candidate = copy.deepcopy(report)
            candidate["scope"][key] = not expected
            with self.subTest(forged_scope=key):
                self.assertTrue(list(validator.iter_errors(candidate)))

        for error_code, pair in correlations.items():
            route, disposition = pair
            wrong_route = (
                "repeat_then_compare_candidate"
                if route == "administrator_only"
                else "administrator_only"
            )
            wrong_disposition = (
                "empty_partial_or_apparent_complete_invalid"
                if disposition == "empty_invalid"
                else "empty_invalid"
            )
            forged_route = copy.deepcopy(report)
            forged_route.update(
                {
                    "error_code": error_code,
                    "recovery_route": wrong_route,
                    "stdout_disposition": disposition,
                }
            )
            forged_disposition = copy.deepcopy(report)
            forged_disposition.update(
                {
                    "error_code": error_code,
                    "recovery_route": route,
                    "stdout_disposition": wrong_disposition,
                }
            )
            with self.subTest(wrong_route=error_code):
                self.assertTrue(list(validator.iter_errors(forged_route)))
            with self.subTest(wrong_stdout_disposition=error_code):
                self.assertTrue(list(validator.iter_errors(forged_disposition)))

        for forged in (
            {**report, "error_code": "unknown_recovery"},
            {**report, "command": "coding-audit-compare"},
            {**report, "message_ru": ""},
            {**report, "exit_code": 3},
        ):
            with self.subTest(forged=forged):
                self.assertTrue(list(validator.iter_errors(forged)))

    def test_native_profile_fields_are_required_only_for_claim_use(self):
        dimension = {
            "state": "verified",
            "chain_ids": [],
            "evidence_refs": [],
            "unknowns": [],
            "claim_effect": "Предел вывода проверен.",
            "assessed": True,
            "usable_for_claim": True,
            "review_complete": True,
        }
        origin = {
            "status": "native_finalization_bound",
            "reason_codes": [],
            "expected_receipt_sha256": "a" * 64,
            "reliability_contract_valid": True,
            "receipt_contract_valid": True,
            "receipt_self_digest_valid": True,
            "external_receipt_digest_valid": True,
            "reliability_file_digest_valid": True,
            "audit_plan_digest_valid": True,
            "candidate_population_valid": True,
            "usable_for_claim": True,
        }
        input_hashes = {
            key: str(index) * 64
            for index, key in enumerate(
                (
                    "applicant_relations",
                    "coding_reliability",
                    "comparisons",
                    "higher_authority_treatments",
                    "position_cards",
                    "source_reconciliation",
                    "temporal_analysis",
                    "trajectories",
                ),
                start=1,
            )
        }
        input_hashes.update(
            {
                "coding_audit_finalization_receipt": "b" * 64,
                "expected_finalization_receipt_sha256": "a" * 64,
            }
        )
        native_profile = {
            "schema_version": "1.0",
            "fingerprint_sha256": "c" * 64,
            "unit": "independent_case_chain",
            "dimensions": {
                name: copy.deepcopy(dimension)
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
            },
            "profile_assessed": True,
            "claim_use_ready": True,
            "blocking_dimensions": [],
            "profile_complete": True,
            "numeric_aggregation": "prohibited",
            "constitutional_conclusion_permitted": False,
            "malformed_position_card_refs": [],
            "malformed_trajectory_refs": [],
            "coding_reliability_origin": origin,
            "input_sha256s": input_hashes,
            "claim_limit": "Только в проверенных пределах.",
            "profile_id": "d" * 64,
        }

        schemas = (
            self.schema,
            json.loads(PRACTICE_SCHEMA_PATH.read_text(encoding="utf-8")),
        )
        for schema in schemas:
            validator = Draft202012Validator(
                {
                    "$schema": schema["$schema"],
                    "$ref": "#/definitions/uncertainty_profile",
                    "$defs": schema.get("$defs", {}),
                    "definitions": schema["definitions"],
                },
                format_checker=FormatChecker(),
            )
            with self.subTest(schema=schema.get("$id"), variant="native"):
                self.assertTrue(validator.is_valid(native_profile))
            for missing in (
                "coding_reliability_origin",
                "coding_audit_finalization_receipt",
                "expected_finalization_receipt_sha256",
            ):
                candidate = copy.deepcopy(native_profile)
                if missing == "coding_reliability_origin":
                    candidate.pop(missing)
                else:
                    candidate["input_sha256s"].pop(missing)
                with self.subTest(schema=schema.get("$id"), missing=missing):
                    self.assertFalse(validator.is_valid(candidate))

            historical = copy.deepcopy(native_profile)
            historical["claim_use_ready"] = False
            historical["profile_complete"] = False
            historical.pop("coding_reliability_origin")
            historical["input_sha256s"].pop(
                "coding_audit_finalization_receipt"
            )
            historical["input_sha256s"].pop(
                "expected_finalization_receipt_sha256"
            )
            with self.subTest(schema=schema.get("$id"), variant="historical"):
                self.assertTrue(validator.is_valid(historical))

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
