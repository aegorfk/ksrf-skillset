import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

try:
    from judicial_meaning import practice_quality
except ImportError:
    practice_quality = None


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_ROOT / "schemas" / "practice-quality.v1.json"
TREATMENT_SOURCE_FIELDS = (
    "source_chain_id",
    "source_court_id",
    "target_authority_id",
    "target_kind",
    "target_identity",
    "target_identity_confirmed",
    "treatment_type",
    "review_decision",
    "snapshot_id",
    "supersedes_treatment_id",
    "superseded_by_treatment_id",
    "speaker",
    "document_id",
    "document_sha256",
    "text_sha256",
    "source_role",
    "official_url",
    "quote",
    "quote_locator",
    "proposition",
    "decision_reason",
    "created_at",
)


def definition_validator(schema, name):
    return Draft202012Validator(
        {
            "$schema": schema.get("$schema"),
            "$ref": f"#/definitions/{name}",
            "definitions": schema["definitions"],
        }
    )


class PracticeQualityTests(unittest.TestCase):
    maxDiff = None

    def api(self):
        self.assertIsNotNone(
            practice_quality,
            "dependency-free practice_quality module has not been implemented",
        )
        return practice_quality

    def stage(
        self,
        identifier,
        *,
        chain_id="chain-1",
        source_stage="first_instance",
        actor_stage=None,
        evidence_role="actor_primary_text",
        treatment="originates",
        disposition="claim_dismissed",
        reading_family="employer_discretion",
    ):
        actor_stage = actor_stage or source_stage
        return {
            "schema_version": "1.0",
            "observation_id": identifier,
            "chain_id": chain_id,
            "source_stage": source_stage,
            "position_actor_stage": actor_stage,
            "evidence_role": evidence_role,
            "document_id": f"document-{identifier}",
            "document_sha256": ("a" if source_stage == "first_instance" else "b") * 64,
            "official_url": "https://2kas.sudrf.ru/example",
            "speaker": "court",
            "proposition": "Проверенная позиция суда.",
            "quote": "проверенная позиция суда",
            "quote_locator": "абзац 18",
            "quote_verified": True,
            "full_text_reviewed": True,
            "reading_family": reading_family,
            "treatment_of_prior": treatment,
            "disposition": disposition,
            "outcome_materiality": "necessary_to_outcome",
            "alternative_grounds": [],
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:00:00Z",
            "human_review": "approved",
        }

    def primary(self, candidate_id, *, label="core_merits", coder="primary-a"):
        return {
            "candidate_id": candidate_id,
            "chain_id": f"chain-{candidate_id}",
            "document_id": f"document-{candidate_id}",
            "label": label,
            "speaker": "court" if label in {"core_merits", "contextual"} else "unknown",
            "proposition": "Проверенная позиция суда.",
            "norm_edition_id": "edition-1",
            "reading_family": "family-a" if label in {"core_merits", "contextual"} else "excluded",
            "relation": "supports" if label in {"core_merits", "contextual"} else "neutral",
            "reasoning_to_outcome": "Проверенная связь с исходом.",
            "alternative_grounds": [],
            "remedy": "отмена",
            "quote": "проверенная позиция суда",
            "quote_locator": "абзац 18",
            "quote_verified": True,
            "full_text_reviewed": True,
            "coder": coder,
            "codebook_version": "1.0",
            "material_facts": ["проверяемый факт"],
            "human_review": "approved",
        }

    def secondary(self, api, primary, *, coder="secondary-b", label=None):
        coding = copy.deepcopy(primary)
        coding["coder"] = coder
        if label is not None:
            coding["label"] = label
            coding["speaker"] = "court" if label in {"core_merits", "contextual"} else "unknown"
            coding["reading_family"] = "family-a" if label in {"core_merits", "contextual"} else "excluded"
            coding["relation"] = "supports" if label in {"core_merits", "contextual"} else "neutral"
        return {
            "candidate_id": primary["candidate_id"],
            "primary_coding_sha256": api.canonical_digest(primary),
            "secondary_coding": coding,
            "secondary_coding_sha256": api.canonical_digest(coding),
        }

    def reviewed_treatment(
        self,
        api,
        treatment_id="treatment-reviewed",
        *,
        status="verified",
    ):
        treatment_type = "applies" if status == "verified" else "does_not_reach"
        decision_reason = (
            None if status == "verified" else "Связь не подтверждена полным текстом."
        )
        source = {
            "source_chain_id": "chain-reviewed",
            "source_court_id": "2kas",
            "target_authority_id": "authority-reviewed",
            "target_kind": "constitutional_court_act",
            "target_identity": {"act_number": "32-П"},
            "target_identity_confirmed": True,
            "treatment_type": treatment_type,
            "review_decision": status,
            "snapshot_id": f"snapshot-sha256:{'d' * 64}",
            "supersedes_treatment_id": None,
            "superseded_by_treatment_id": None,
            "speaker": "court",
            "document_id": f"document-{treatment_id}",
            "document_sha256": "d" * 64,
            "text_sha256": "e" * 64,
            "source_role": "official_user_seed",
            "official_url": "https://2kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1",
            "quote": "суд применил правовую позицию к спорному правоотношению",
            "quote_locator": "абзац 24, предложение 2",
            "proposition": api.treatment_quality_proposition(
                status=status,
                source_chain_id="chain-reviewed",
                treatment_type=treatment_type,
                target_authority_id="authority-reviewed",
                decision_reason=decision_reason,
            ),
            "decision_reason": decision_reason,
            "created_at": "2026-08-27T12:00:00Z",
        }
        return {
            "treatment_id": treatment_id,
            "status": status,
            **source,
            "source_binding_sha256": api.canonical_digest(source),
            "reviewer": "П.П. Петров",
            "reviewed_at": "2026-08-27T12:05:00Z",
            "human_review": "approved",
            "quote_verified": True,
            "full_text_reviewed": True,
        }

    def treatment_set(
        self,
        api,
        items,
        *,
        corpus_digest="a" * 64,
        treatment_population_sha256="f" * 64,
    ):
        copied = copy.deepcopy(items)
        if (
            all(
                isinstance(item, dict)
                and isinstance(item.get("treatment_id"), str)
                for item in copied
            )
            and len({item["treatment_id"] for item in copied}) == len(copied)
        ):
            copied.sort(key=lambda item: item["treatment_id"])
        treatment_ids = [
            item.get("treatment_id") if isinstance(item, dict) else None
            for item in copied
        ]
        payload = {
            "schema_version": "1.0",
            "export_type": "public_corpus_treatment_quality_set",
            "corpus_evidence_digest": f"corpus-evidence-sha256:{corpus_digest}",
            "treatment_population_sha256": treatment_population_sha256,
            "integrity_issue_ids": [],
            "treatment_ids": treatment_ids,
            "items": copied,
        }
        return {**payload, "set_sha256": api.canonical_digest(payload)}

    def refresh_plan(
        self,
        api,
        *,
        as_of="2026-08-27T12:00:00Z",
        max_age_seconds=7 * 24 * 60 * 60,
        current_corpus_digest="a" * 64,
        entries=None,
        coverage_gaps=None,
        coverage_requirements=None,
        treatment_ids=None,
        treatment_population_sha256="f" * 64,
    ):
        payload = {
            "as_of": as_of,
            "max_age_seconds": max_age_seconds,
            "evidence_digest": f"corpus-evidence-sha256:{current_corpus_digest}",
            "treatment_ids": copy.deepcopy(treatment_ids) if treatment_ids else [],
            "treatment_population_sha256": treatment_population_sha256,
            "coverage_requirements": (
                copy.deepcopy(coverage_requirements)
                if coverage_requirements is not None
                else [{"court_id": "2kas"}]
            ),
            "entries": copy.deepcopy(entries) if entries is not None else [],
            "coverage_gaps": (
                copy.deepcopy(coverage_gaps) if coverage_gaps is not None else []
            ),
        }
        return {
            "plan_id": f"refresh-plan-sha256:{api.canonical_digest(payload)}",
            **payload,
        }

    def live_binding(self, api, refresh_plan, treatment_set):
        return {
            "binding_version": "1.0",
            "verified": True,
            "live_cache_stable": True,
            "live_corpus_evidence_digest": refresh_plan["evidence_digest"],
            "live_refresh_plan_sha256": api.canonical_digest(refresh_plan),
            "live_treatment_set_sha256": treatment_set["set_sha256"],
            "live_treatment_population_sha256": refresh_plan[
                "treatment_population_sha256"
            ],
            "live_treatment_ids": copy.deepcopy(refresh_plan["treatment_ids"]),
            "issue_ids": [],
        }

    def complete_reliability(self, api):
        candidates = [{"candidate_id": "candidate-reliability"}]
        primary = [self.primary("candidate-reliability")]
        plan = api.build_coding_audit_plan(
            candidates,
            primary,
            plan_sha256="d" * 64,
            sample_size=1,
            exclusion_sample_size=0,
        )
        audit = self.secondary(api, primary[0])
        result = api.assess_coding_reliability(plan, primary, [audit])
        self.assertTrue(result["complete"])
        return result

    def closed_reconciliation(self):
        return {
            "overall_status": "closed_declared_enumerations",
            "all_routes_closed": True,
            "route_coverage": {
                "daily": {"status": "closed_declared_enumeration"}
            },
        }

    def assert_no_scalar_keys(self, value):
        if isinstance(value, dict):
            for key, nested in value.items():
                folded = key.casefold()
                self.assertNotIn("score", folded)
                self.assertNotIn("index", folded)
                self.assertNotIn("индекс", folded)
                self.assert_no_scalar_keys(nested)
        elif isinstance(value, list):
            for nested in value:
                self.assert_no_scalar_keys(nested)

    def test_canonical_digest_is_order_independent_and_content_sensitive(self):
        api = self.api()
        left = api.canonical_digest({"b": [2, 3], "a": "значение"})
        right = api.canonical_digest({"a": "значение", "b": [2, 3]})
        changed = api.canonical_digest({"a": "другое", "b": [2, 3]})
        self.assertEqual(left, right)
        self.assertNotEqual(left, changed)
        self.assertRegex(left, r"^[0-9a-f]{64}$")

    def test_unchanged_result_is_not_cassation_adoption_without_express_quote(self):
        api = self.api()
        first = self.stage("first")
        cassation = self.stage(
            "cassation",
            source_stage="cassation",
            treatment="unclear",
            disposition="left_unchanged",
            reading_family=None,
        )
        result = api.analyze_chain_stage_propagation(
            [first, cassation], required_chain_ids=["chain-1"]
        )
        trajectory = result["trajectories"][0]
        self.assertTrue(result["review_complete"])
        self.assertEqual("first_instance", trajectory["origin_stage"])
        self.assertEqual(
            "leaves_result_without_endorsing",
            trajectory["cassation_treatment"],
        )
        self.assertFalse(trajectory["cassation_express_adoption"])
        self.assertIn("не означает", trajectory["claim_limit"])

    def test_later_court_recount_cannot_be_promoted_to_primary_stage_position(self):
        api = self.api()
        reported = self.stage(
            "reported-first",
            source_stage="cassation",
            actor_stage="first_instance",
            evidence_role="later_court_report",
            treatment="originates",
        )
        cassation = self.stage(
            "cassation",
            source_stage="cassation",
            treatment="does_not_reach",
            disposition="left_unchanged",
            reading_family=None,
        )
        result = api.analyze_chain_stage_propagation([reported, cassation])
        trajectory = result["trajectories"][0]
        self.assertIsNone(trajectory["origin_stage"])
        self.assertEqual(["reported-first"], trajectory["reported_only_observation_ids"])
        self.assertFalse(trajectory["cassation_express_adoption"])
        self.assertIn("первичный текст", trajectory["claim_limit"])

    def test_explicit_primary_cassation_quote_can_record_adoption(self):
        api = self.api()
        result = api.analyze_chain_stage_propagation(
            [
                self.stage("first"),
                self.stage(
                    "cassation",
                    source_stage="cassation",
                    treatment="expressly_adopts",
                    disposition="left_unchanged",
                ),
            ]
        )
        trajectory = result["trajectories"][0]
        self.assertEqual("expressly_adopts", trajectory["cassation_treatment"])
        self.assertTrue(trajectory["cassation_express_adoption"])

    def test_primary_follows_treatment_is_preserved_without_relabelling_it_express_adoption(self):
        api = self.api()
        result = api.analyze_chain_stage_propagation(
            [
                self.stage("first"),
                self.stage(
                    "cassation",
                    source_stage="cassation",
                    treatment="follows",
                    disposition="left_unchanged",
                ),
            ]
        )
        trajectory = result["trajectories"][0]
        self.assertEqual("follows", trajectory["cassation_treatment"])
        self.assertFalse(trajectory["cassation_express_adoption"])

    def test_chain_review_fails_closed_without_primary_origin(self):
        api = self.api()
        result = api.analyze_chain_stage_propagation(
            [
                self.stage(
                    "reported-first",
                    source_stage="cassation",
                    actor_stage="first_instance",
                    evidence_role="later_court_report",
                    treatment="originates",
                ),
                self.stage(
                    "cassation",
                    source_stage="cassation",
                    treatment="does_not_reach",
                    reading_family=None,
                ),
            ]
        )
        trajectory = result["trajectories"][0]
        self.assertFalse(trajectory["review_complete"])
        self.assertFalse(result["review_complete"])
        self.assertIn("primary_origin_not_observed", trajectory["unresolved_reasons"])

    def test_chain_review_fails_closed_without_cassation_primary_text(self):
        api = self.api()
        result = api.analyze_chain_stage_propagation([self.stage("first")])
        trajectory = result["trajectories"][0]
        self.assertFalse(trajectory["review_complete"])
        self.assertFalse(result["review_complete"])
        self.assertIn(
            "cassation_primary_text_not_observed",
            trajectory["unresolved_reasons"],
        )

    def test_conflicting_primary_cassation_treatments_cannot_establish_adoption(self):
        api = self.api()
        result = api.analyze_chain_stage_propagation(
            [
                self.stage("first"),
                self.stage(
                    "cassation-adopts",
                    source_stage="cassation",
                    treatment="expressly_adopts",
                ),
                self.stage(
                    "cassation-rejects",
                    source_stage="cassation",
                    treatment="rejects",
                ),
            ]
        )
        trajectory = result["trajectories"][0]
        self.assertFalse(trajectory["cassation_express_adoption"])
        self.assertEqual("unclear", trajectory["cassation_treatment"])
        self.assertFalse(trajectory["review_complete"])
        self.assertIn(
            "conflicting_cassation_treatments",
            trajectory["unresolved_reasons"],
        )

    def test_express_adoption_requires_matching_origin_reading_family(self):
        api = self.api()
        result = api.analyze_chain_stage_propagation(
            [
                self.stage("first", reading_family="family-a"),
                self.stage(
                    "cassation",
                    source_stage="cassation",
                    treatment="expressly_adopts",
                    reading_family="family-b",
                ),
            ]
        )
        trajectory = result["trajectories"][0]
        self.assertFalse(trajectory["cassation_express_adoption"])
        self.assertEqual("unclear", trajectory["cassation_treatment"])
        self.assertFalse(trajectory["review_complete"])
        self.assertIn(
            "cassation_reading_family_mismatch",
            trajectory["unresolved_reasons"],
        )

    def test_non_mapping_propagation_observation_is_explicit_unresolved_and_digest_bound(self):
        api = self.api()
        valid = [
            self.stage("first"),
            self.stage(
                "cassation",
                source_stage="cassation",
                treatment="expressly_adopts",
            ),
        ]
        raw = [*valid, None]
        result = api.analyze_chain_stage_propagation(raw)
        self.assertEqual(3, result["observation_count"])
        self.assertFalse(result["review_complete"])
        self.assertTrue(
            any(
                "observation_not_mapping" in item["errors"]
                for item in result["unresolved"]
            )
        )
        self.assertEqual(
            api.canonical_digest(raw), result.get("observations_sha256")
        )

        changed = api.analyze_chain_stage_propagation([*valid, "malformed"])
        self.assertNotEqual(
            result.get("observations_sha256"), changed.get("observations_sha256")
        )
        self.assertNotEqual(result["evidence_sha256"], changed["evidence_sha256"])

    def profile_inputs(self, api):
        cards = [
            {
                "position_card_id": "position-1",
                "chain_id": "chain-1",
                "court_id": "2kas",
                "reading_family": "family-a",
                "material_facts_group": "same-facts",
                "outcome_materiality": "necessary_to_outcome",
                "alternative_grounds": [],
            },
            {
                "position_card_id": "position-2",
                "chain_id": "chain-2",
                "court_id": "3kas",
                "reading_family": "family-b",
                "material_facts_group": "same-facts",
                "outcome_materiality": "independent_sufficient_ground",
                "alternative_grounds": [
                    {"ground": "пропуск срока", "independently_sufficient": True}
                ],
            },
        ]
        comparisons = {
            card["position_card_id"]: {
                "status": "matched",
                "fingerprint_sha256": "f" * 64,
                "review_provenance": {"status": "approved"},
            }
            for card in cards
        }
        relations = {
            "position-1": {
                "relation": "supports",
                "fingerprint_sha256": "f" * 64,
                "human_review": "approved",
                "stale": False,
            },
            "position-2": {
                "relation": "adverse",
                "fingerprint_sha256": "f" * 64,
                "human_review": "approved",
                "stale": False,
            },
        }
        trajectory_result = api.analyze_chain_stage_propagation(
            [
                self.stage("first"),
                self.stage("cassation", source_stage="cassation", treatment="expressly_adopts"),
                self.stage("other", chain_id="chain-2", reading_family="family-b"),
                self.stage(
                    "other-cassation",
                    chain_id="chain-2",
                    source_stage="cassation",
                    treatment="does_not_reach",
                    reading_family=None,
                ),
            ]
        )
        return cards, comparisons, relations, trajectory_result["trajectories"]

    def test_uncertainty_profile_has_nine_fixed_dimensions_and_no_scalar(self):
        api = self.api()
        cards, comparisons, relations, trajectories = self.profile_inputs(api)
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={
                "temporal_analysis_complete": True,
                "transitions": [
                    {"status": "descriptive_distribution_changed"}
                ],
            },
            trajectories=trajectories,
            source_reconciliation=self.closed_reconciliation(),
            coding_reliability=self.complete_reliability(api),
            higher_authority_treatments=[self.reviewed_treatment(api, "treatment-1")],
        )
        self.assertEqual(
            set(api.UNCERTAINTY_DIMENSIONS), set(profile["dimensions"])
        )
        self.assertEqual(9, len(profile["dimensions"]))
        self.assertEqual(
            "multiple_comparable_readings",
            profile["dimensions"]["comparable_reading_plurality"]["state"],
        )
        self.assertEqual("prohibited", profile["numeric_aggregation"])
        self.assertFalse(profile["constitutional_conclusion_permitted"])
        self.assertTrue(profile["profile_complete"])
        self.assert_no_scalar_keys(profile)

    def test_profile_separates_assessed_dimensions_from_claim_use_readiness(self):
        api = self.api()
        cards, comparisons, relations, _ = self.profile_inputs(api)
        incomplete_trajectories = api.analyze_chain_stage_propagation(
            [self.stage("first")]
        )["trajectories"]
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={
                "temporal_analysis_complete": False,
                "transitions": [],
            },
            trajectories=incomplete_trajectories,
            source_reconciliation={"overall_status": "observed_only"},
            coding_reliability={
                "complete": False,
                "unresolved_candidate_ids": ["candidate-1"],
            },
            higher_authority_treatments=[
                {"treatment_id": "treatment-pending", "status": "candidate"}
            ],
        )
        blockers = {
            "temporal_distribution",
            "chain_endorsement",
            "higher_authority_treatment",
            "coverage_limits",
            "coding_reliability",
        }
        for dimension_name in blockers:
            dimension = profile["dimensions"][dimension_name]
            self.assertTrue(dimension.get("assessed"), dimension_name)
            self.assertFalse(dimension.get("usable_for_claim", True), dimension_name)
            self.assertFalse(dimension["review_complete"], dimension_name)
        self.assertTrue(profile.get("profile_assessed"))
        self.assertFalse(profile.get("claim_use_ready", True))
        self.assertFalse(profile["profile_complete"])
        self.assertEqual(blockers, set(profile.get("blocking_dimensions", [])))
        self.assert_no_scalar_keys(profile)

    def test_open_coverage_is_assessed_but_blocks_claim_use(self):
        api = self.api()
        cards, comparisons, relations, trajectories = self.profile_inputs(api)
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={"temporal_analysis_complete": True, "transitions": []},
            trajectories=trajectories,
            source_reconciliation={
                "overall_status": "observed_only",
                "route_coverage": {"daily": {"status": "open"}},
            },
            coding_reliability=self.complete_reliability(api),
            higher_authority_treatments=[],
        )
        coverage = profile["dimensions"]["coverage_limits"]
        self.assertTrue(coverage["assessed"])
        self.assertFalse(coverage["usable_for_claim"])
        self.assertFalse(coverage["review_complete"])
        self.assertIn("coverage_limits", profile["blocking_dimensions"])
        self.assertFalse(profile["claim_use_ready"])

    def test_empty_declared_route_registry_cannot_be_closed(self):
        api = self.api()
        cards, comparisons, relations, trajectories = self.profile_inputs(api)
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={"temporal_analysis_complete": True, "transitions": []},
            trajectories=trajectories,
            source_reconciliation={
                "overall_status": "closed_declared_enumerations",
                "all_routes_closed": True,
                "route_coverage": {},
            },
            coding_reliability=self.complete_reliability(api),
            higher_authority_treatments=[],
        )
        coverage = profile["dimensions"]["coverage_limits"]
        self.assertFalse(coverage["usable_for_claim"])
        self.assertIn("declared_route_registry_empty", coverage["unknowns"])
        self.assertIn("coverage_limits", profile["blocking_dimensions"])

    def test_claim_ready_requires_full_content_bound_reliability_contract(self):
        api = self.api()
        cards, comparisons, relations, trajectories = self.profile_inputs(api)

        def profile_for(reliability):
            return api.build_uncertainty_profile(
                fingerprint_sha256="f" * 64,
                position_cards=cards,
                comparisons=comparisons,
                applicant_relations=relations,
                temporal_analysis={"temporal_analysis_complete": True, "transitions": []},
                trajectories=trajectories,
                source_reconciliation=self.closed_reconciliation(),
                coding_reliability=reliability,
                higher_authority_treatments=[],
            )

        stub = {"complete": True, "stale": False, "unresolved_candidate_ids": []}
        stub_profile = profile_for(stub)
        self.assertFalse(stub_profile["claim_use_ready"])
        self.assertIn("coding_reliability", stub_profile["blocking_dimensions"])

        valid = self.complete_reliability(api)
        self.assertTrue(valid.get("audit_plan_frozen"))
        self.assertTrue(valid.get("audit_plan_digest_valid"))
        self.assertTrue(profile_for(valid)["claim_use_ready"])

        for case_name, mutate in (
            ("unfrozen", lambda value: value.update(audit_plan_frozen=False)),
            ("candidate_mismatch", lambda value: value.update(audited_candidate_ids=[])),
            ("bad_digest", lambda value: value.update(evidence_sha256="e" * 64)),
        ):
            with self.subTest(case_name=case_name):
                invalid = copy.deepcopy(valid)
                mutate(invalid)
                if case_name != "bad_digest":
                    digest_payload = dict(invalid)
                    digest_payload.pop("evidence_sha256", None)
                    invalid["evidence_sha256"] = api.canonical_digest(digest_payload)
                invalid_profile = profile_for(invalid)
                self.assertFalse(invalid_profile["claim_use_ready"])
                self.assertIn(
                    "coding_reliability", invalid_profile["blocking_dimensions"]
                )

    def test_malformed_higher_authority_entry_is_not_discarded(self):
        api = self.api()
        cards, comparisons, relations, trajectories = self.profile_inputs(api)
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={"temporal_analysis_complete": True, "transitions": []},
            trajectories=trajectories,
            source_reconciliation=self.closed_reconciliation(),
            coding_reliability=self.complete_reliability(api),
            higher_authority_treatments=["not-a-treatment-record"],
        )
        authority = profile["dimensions"]["higher_authority_treatment"]
        self.assertTrue(authority["assessed"])
        self.assertFalse(authority["usable_for_claim"])
        self.assertTrue(authority["unknowns"])
        self.assertIn("higher_authority_treatment", profile["blocking_dimensions"])

    def test_malformed_position_cards_and_trajectories_are_digest_bound_blockers(self):
        api = self.api()
        cards, comparisons, relations, trajectories = self.profile_inputs(api)
        raw_cards = [*cards, None, {"chain_id": "missing-position-card-id"}]
        raw_trajectories = [
            *trajectories,
            "not-a-trajectory",
            {"chain_id": "missing-trajectory-contract"},
        ]
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=raw_cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={"temporal_analysis_complete": True, "transitions": []},
            trajectories=raw_trajectories,
            source_reconciliation=self.closed_reconciliation(),
            coding_reliability=self.complete_reliability(api),
            higher_authority_treatments=[],
        )
        self.assertEqual(2, len(profile.get("malformed_position_card_refs", [])))
        self.assertEqual(2, len(profile.get("malformed_trajectory_refs", [])))
        self.assertEqual(
            api.canonical_digest(raw_cards),
            profile["input_sha256s"]["position_cards"],
        )
        self.assertEqual(
            api.canonical_digest(raw_trajectories),
            profile["input_sha256s"]["trajectories"],
        )
        self.assertFalse(profile["claim_use_ready"])
        self.assertTrue(
            {
                "comparable_reading_plurality",
                "fact_sensitivity",
                "court_distribution",
                "outcome_materiality",
                "chain_endorsement",
            }.issubset(profile["blocking_dimensions"])
        )

    def test_profile_keeps_fact_court_and_alternative_ground_explanations_separate(self):
        api = self.api()
        cards, comparisons, relations, trajectories = self.profile_inputs(api)
        cards[1]["material_facts_group"] = "different-facts"
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={"temporal_analysis_complete": False, "transitions": []},
            trajectories=trajectories,
            source_reconciliation={"overall_status": "observed_only"},
            coding_reliability={"complete": True, "unresolved_candidate_ids": []},
            higher_authority_treatments=[],
        )
        dimensions = profile["dimensions"]
        self.assertEqual("fact_separated_readings", dimensions["fact_sensitivity"]["state"])
        self.assertEqual("court_separated_families", dimensions["court_distribution"]["state"])
        self.assertEqual("alternative_ground_exposure", dimensions["outcome_materiality"]["state"])
        self.assertNotEqual(
            dimensions["fact_sensitivity"]["claim_effect"],
            dimensions["court_distribution"]["claim_effect"],
        )

    def test_frozen_coding_audit_is_deterministic_and_distinct_reviewer_is_required(self):
        api = self.api()
        candidates = [{"candidate_id": value} for value in ("candidate-1", "candidate-2", "candidate-3")]
        primary = [
            self.primary("candidate-1"),
            self.primary("candidate-2", label="false_positive"),
            self.primary("candidate-3", label="contextual"),
        ]
        plan = api.build_coding_audit_plan(
            candidates,
            primary,
            plan_sha256="d" * 64,
            sample_size=2,
            exclusion_sample_size=1,
        )
        repeated = api.build_coding_audit_plan(
            list(reversed(candidates)),
            list(reversed(primary)),
            plan_sha256="d" * 64,
            sample_size=2,
            exclusion_sample_size=1,
        )
        self.assertEqual(plan, repeated)
        self.assertTrue(plan["frozen"])
        self.assertRegex(plan["audit_plan_sha256"], r"^[0-9a-f]{64}$")

        by_id = {item["candidate_id"]: item for item in primary}
        audits = [
            self.secondary(api, by_id[candidate_id])
            for candidate_id in plan["required_candidate_ids"]
        ]
        audits[0]["secondary_coding"]["coder"] = by_id[
            audits[0]["candidate_id"]
        ]["coder"]
        audits[0]["secondary_coding_sha256"] = api.canonical_digest(
            audits[0]["secondary_coding"]
        )
        result = api.assess_coding_reliability(plan, primary, audits)
        self.assertFalse(result["complete"])
        self.assertEqual([audits[0]["candidate_id"]], result["same_reviewer_candidate_ids"])

    def test_false_exclusion_requires_content_bound_independent_adjudication(self):
        api = self.api()
        candidates = [{"candidate_id": "candidate-1"}]
        primary = [self.primary("candidate-1", label="false_positive")]
        plan = api.build_coding_audit_plan(
            candidates,
            primary,
            plan_sha256="d" * 64,
            sample_size=1,
            exclusion_sample_size=1,
        )
        audit = self.secondary(api, primary[0], label="core_merits")
        blocked = api.assess_coding_reliability(plan, primary, [audit])
        self.assertFalse(blocked["complete"])
        self.assertEqual("candidate-1", blocked["false_exclusion_diagnostics"][0]["candidate_id"])
        self.assertIn("candidate-1", blocked["unresolved_candidate_ids"])

        adjudication = {
            "candidate_id": "candidate-1",
            "primary_coding_sha256": api.canonical_digest(primary[0]),
            "secondary_coding_sha256": api.canonical_digest(audit["secondary_coding"]),
            "resolved_fields": {
                "label": "false_positive",
                "speaker": "unknown",
                "reading_family": "excluded",
                "relation": "neutral",
            },
            "adjudicator": "supervisor-c",
            "reviewed_at": "2026-08-27T14:00:00Z",
            "human_review": "approved",
        }
        for malformed_timestamp in (
            "2026-08-27T14:00Z",
            "2026-W35-4T14:00:00Z",
        ):
            with self.subTest(malformed_timestamp=malformed_timestamp):
                malformed_adjudication = copy.deepcopy(adjudication)
                malformed_adjudication["reviewed_at"] = malformed_timestamp
                malformed_result = api.assess_coding_reliability(
                    plan,
                    primary,
                    [audit],
                    [malformed_adjudication],
                )
                self.assertFalse(malformed_result["complete"])
                self.assertEqual(
                    ["candidate-1"],
                    malformed_result["invalid_adjudication_record_ids"],
                )
                self.assertIn(
                    "candidate-1",
                    malformed_result["unresolved_candidate_ids"],
                )

        resolved = api.assess_coding_reliability(
            plan, primary, [audit], [adjudication]
        )
        self.assertTrue(resolved["complete"])
        self.assertEqual([], resolved["unresolved_candidate_ids"])
        self.assertTrue(resolved["false_exclusion_diagnostics"][0]["resolved"])

        changed_primary = copy.deepcopy(primary)
        changed_primary[0]["remedy"] = "изменённый результат"
        stale = api.assess_coding_reliability(
            plan, changed_primary, [audit], [adjudication]
        )
        self.assertTrue(stale["stale"])
        self.assertFalse(stale["complete"])

    def test_primary_coding_provenance_must_be_human_and_text_verified(self):
        api = self.api()
        candidates = [{"candidate_id": "candidate-1"}]
        invalid_primary = self.primary("candidate-1")
        invalid_primary["human_review"] = "pending"
        invalid_primary["quote_verified"] = False
        invalid_primary["full_text_reviewed"] = False
        plan = api.build_coding_audit_plan(
            candidates,
            [invalid_primary],
            plan_sha256="d" * 64,
            sample_size=1,
            exclusion_sample_size=0,
        )
        audit = self.secondary(api, invalid_primary)
        audit["secondary_coding"]["human_review"] = "approved"
        audit["secondary_coding"]["quote_verified"] = True
        audit["secondary_coding"]["full_text_reviewed"] = True
        audit["secondary_coding_sha256"] = api.canonical_digest(
            audit["secondary_coding"]
        )
        result = api.assess_coding_reliability(plan, [invalid_primary], [audit])
        self.assertFalse(result["complete"])
        self.assertEqual(
            ["candidate-1"],
            result.get("invalid_provenance_candidate_ids", []),
        )
        self.assertIn("candidate-1", result["unresolved_candidate_ids"])

    def test_malformed_audit_records_are_preserved_and_block_reliability(self):
        api = self.api()
        candidates = [{"candidate_id": "candidate-1"}, None]
        primary = [self.primary("candidate-1"), {"label": "core_merits"}]
        plan = api.build_coding_audit_plan(
            candidates,
            primary,
            plan_sha256="d" * 64,
            sample_size=1,
            exclusion_sample_size=0,
        )
        self.assertTrue(plan.get("invalid_screening_record_ids"))
        self.assertTrue(plan.get("invalid_primary_record_ids"))
        self.assertEqual(
            api.canonical_digest(sorted(candidates, key=api.canonical_digest)),
            plan["screening_sha256"],
        )
        self.assertEqual(
            api.canonical_digest(sorted(primary, key=api.canonical_digest)),
            plan["primary_coding_sha256"],
        )

        audit = self.secondary(api, primary[0])
        reliability = api.assess_coding_reliability(plan, primary, [audit])
        self.assertFalse(reliability["complete"])
        self.assertTrue(reliability.get("invalid_screening_record_ids"))
        self.assertTrue(reliability.get("invalid_primary_record_ids"))
        self.assertTrue(reliability["unresolved_candidate_ids"])

        cards, comparisons, relations, trajectories = self.profile_inputs(api)
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={"temporal_analysis_complete": True, "transitions": []},
            trajectories=trajectories,
            source_reconciliation=self.closed_reconciliation(),
            coding_reliability=reliability,
            higher_authority_treatments=[],
        )
        self.assertIn("coding_reliability", profile["blocking_dimensions"])

    def test_secondary_coding_schema_requires_verified_human_provenance(self):
        api = self.api()
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        primary = self.primary("candidate-1")
        audit = self.secondary(api, primary)
        del audit["secondary_coding"]["human_review"]
        audit["secondary_coding"]["quote_verified"] = False
        errors = list(
            definition_validator(schema, "coding_audit_decision").iter_errors(audit)
        )
        self.assertTrue(errors, "secondary provenance must be schema-enforced")

    def test_trajectory_schema_rejects_review_complete_with_unresolved_reasons(self):
        api = self.api()
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        trajectory = api.analyze_chain_stage_propagation(
            [self.stage("first")]
        )["trajectories"][0]
        self.assertFalse(trajectory["review_complete"])
        tampered = copy.deepcopy(trajectory)
        tampered["review_complete"] = True
        errors = list(
            Draft202012Validator(
                schema["definitions"]["chain_meaning_trajectory"]
            ).iter_errors(tampered)
        )
        self.assertTrue(errors, "unresolved trajectory cannot be schema-complete")

    def test_profile_schema_rejects_claim_ready_with_blocking_dimensions(self):
        api = self.api()
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cards, comparisons, relations, _ = self.profile_inputs(api)
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={"temporal_analysis_complete": False, "transitions": []},
            trajectories=api.analyze_chain_stage_propagation(
                [self.stage("first")]
            )["trajectories"],
            source_reconciliation={"overall_status": "observed_only"},
            coding_reliability={"complete": False, "unresolved_candidate_ids": []},
            higher_authority_treatments=[],
        )
        self.assertTrue(profile["blocking_dimensions"])
        tampered = copy.deepcopy(profile)
        tampered["claim_use_ready"] = True
        tampered["profile_complete"] = True
        errors = list(
            Draft202012Validator(
                schema["definitions"]["uncertainty_profile"]
            ).iter_errors(tampered)
        )
        self.assertTrue(errors, "blocking dimensions cannot be schema-ready")

    def test_profile_schema_rejects_ready_when_any_dimension_is_unusable(self):
        api = self.api()
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cards, comparisons, relations, trajectories = self.profile_inputs(api)
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={"temporal_analysis_complete": True, "transitions": []},
            trajectories=trajectories,
            source_reconciliation=self.closed_reconciliation(),
            coding_reliability=self.complete_reliability(api),
            higher_authority_treatments=[],
        )
        self.assertTrue(profile["claim_use_ready"])
        tampered = copy.deepcopy(profile)
        tampered["dimensions"]["coverage_limits"]["usable_for_claim"] = False
        errors = list(
            Draft202012Validator(
                schema["definitions"]["uncertainty_profile"]
            ).iter_errors(tampered)
        )
        self.assertTrue(errors, "an unusable dimension must contradict claim readiness")

    def test_propagation_schema_rejects_review_complete_with_unresolved_entries(self):
        api = self.api()
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        result = api.analyze_chain_stage_propagation(
            [
                self.stage("first"),
                self.stage(
                    "cassation",
                    source_stage="cassation",
                    treatment="expressly_adopts",
                ),
            ]
        )
        self.assertTrue(result["review_complete"])
        tampered = copy.deepcopy(result)
        tampered["unresolved"] = [
            {"observation_id": None, "chain_id": "chain-1", "errors": ["pending"]}
        ]
        errors = list(
            Draft202012Validator(
                schema["definitions"]["chain_propagation_result"]
            ).iter_errors(tampered)
        )
        self.assertTrue(errors, "unresolved propagation cannot be schema-complete")

    def test_prefiling_refresh_distinguishes_unchanged_pending_and_material_change(self):
        api = self.api()
        base = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(api),
            "treatments": self.treatment_set(api, []),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:10:00Z",
            "claim_ids": ["practice-claim-1"],
        }
        base["live_corpus_binding"] = self.live_binding(
            api, base["refresh_plan"], base["treatments"]
        )
        current = api.assess_prefiling_refresh(**base)
        self.assertEqual("current_no_material_change", current["status"])
        self.assertTrue(current["complete"])

        no_claim_scope = dict(base)
        no_claim_scope["claim_ids"] = []
        missing_scope = api.assess_prefiling_refresh(**no_claim_scope)
        self.assertEqual("refresh_incomplete", missing_scope["status"])
        self.assertFalse(missing_scope["complete"])
        self.assertIn("claim_scope_missing", missing_scope["reasons"])

        pending_input = dict(base)
        pending_input["treatments"] = self.treatment_set(
            api,
            [{"treatment_id": "treatment-pending", "status": "candidate"}],
        )
        pending = api.assess_prefiling_refresh(**pending_input)
        self.assertEqual("refresh_incomplete", pending["status"])
        self.assertFalse(pending["complete"])
        self.assertEqual(["treatment-pending"], pending["pending_treatment_ids"])

        changed_input = dict(base)
        changed_input["current_corpus_digest"] = "c" * 64
        changed_input["refresh_plan"] = self.refresh_plan(
            api,
            current_corpus_digest="c" * 64,
        )
        changed = api.assess_prefiling_refresh(**changed_input)
        self.assertEqual("material_change_requires_reanalysis", changed["status"])
        self.assertFalse(changed["complete"])
        self.assertEqual(["practice-claim-1"], changed["affected_claim_ids"])

        bounded_input = copy.deepcopy(base)
        bounded_input["refresh_plan"] = self.refresh_plan(
            api,
            coverage_gaps=[
                {
                    "court_id": "2kas",
                    "reason": "coverage_gap_not_observed",
                    "action": "Повторить ограниченный сбор из официального источника.",
                }
            ],
        )
        bounded_input["live_corpus_binding"] = self.live_binding(
            api, bounded_input["refresh_plan"], bounded_input["treatments"]
        )
        bounded = api.assess_prefiling_refresh(**bounded_input)
        self.assertEqual("bounded_current_with_disclosed_gaps", bounded["status"])
        self.assertTrue(bounded["complete"])

    def test_prefiling_refresh_rejects_missing_or_malformed_human_provenance(self):
        api = self.api()
        common = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(api),
            "treatments": self.treatment_set(api, []),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "",
            "reviewed_at": "not-a-time",
        }
        with self.assertRaisesRegex(ValueError, "reviewer|reviewed_at"):
            api.assess_prefiling_refresh(**common)

    def test_prefiling_refresh_blocks_unidentified_or_unreviewed_treatments(self):
        api = self.api()
        common = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(
                api, treatment_ids=["treatment-reviewed"]
            ),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:10:00Z",
            "claim_ids": ["practice-claim-1"],
        }
        unidentified = api.assess_prefiling_refresh(
            **common,
            treatments=self.treatment_set(api, [{"status": "candidate"}]),
        )
        self.assertEqual("refresh_incomplete", unidentified["status"])
        self.assertFalse(unidentified["complete"])
        self.assertTrue(unidentified["pending_treatment_ids"])

        unreviewed_resolved = api.assess_prefiling_refresh(
            **common,
            treatments=self.treatment_set(
                api,
                [{"treatment_id": "treatment-unbound", "status": "verified"}],
            ),
        )
        self.assertEqual("refresh_incomplete", unreviewed_resolved["status"])
        self.assertFalse(unreviewed_resolved["complete"])
        self.assertEqual(
            ["treatment-unbound"],
            unreviewed_resolved["pending_treatment_ids"],
        )

        reviewed_treatment_set = self.treatment_set(
            api, [self.reviewed_treatment(api)]
        )
        reviewed_resolved = api.assess_prefiling_refresh(
            **common,
            treatments=reviewed_treatment_set,
            live_corpus_binding=self.live_binding(
                api, common["refresh_plan"], reviewed_treatment_set
            ),
        )
        self.assertEqual("current_no_material_change", reviewed_resolved["status"])
        self.assertTrue(reviewed_resolved["complete"])

    def test_prefiling_refresh_binds_resolved_treatments_and_their_content(self):
        api = self.api()
        common = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(
                api,
                treatment_ids=["treatment-rejected", "treatment-verified"],
            ),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:10:00Z",
        }
        verified = self.reviewed_treatment(api, "treatment-verified", status="verified")
        rejected = self.reviewed_treatment(api, "treatment-rejected", status="rejected")
        result = api.assess_prefiling_refresh(
            **common,
            treatments=self.treatment_set(api, [verified, rejected]),
        )
        self.assertEqual(
            ["treatment-verified"], result.get("verified_treatment_ids", [])
        )
        self.assertEqual(
            ["treatment-rejected"], result.get("rejected_treatment_ids", [])
        )
        self.assertRegex(result.get("treatments_sha256", ""), r"^[0-9a-f]{64}$")

        reordered_result = api.assess_prefiling_refresh(
            **common,
            treatments=self.treatment_set(api, [rejected, verified]),
        )
        self.assertEqual(
            result.get("treatments_sha256"),
            reordered_result.get("treatments_sha256"),
        )
        self.assertEqual(result["refresh_id"], reordered_result["refresh_id"])

        changed = copy.deepcopy(verified)
        changed["quote"] = "иной проверенный фрагмент акта"
        source = {
            key: changed.get(key) for key in TREATMENT_SOURCE_FIELDS
        }
        changed["source_binding_sha256"] = api.canonical_digest(source)
        changed_result = api.assess_prefiling_refresh(
            **common,
            treatments=self.treatment_set(api, [changed, rejected]),
        )
        self.assertNotEqual(result.get("treatments_sha256"), changed_result.get("treatments_sha256"))
        self.assertNotEqual(result["refresh_id"], changed_result["refresh_id"])

    def test_prefiling_refresh_partitions_superseded_treatment_graph(self):
        api = self.api()
        old = self.reviewed_treatment(api, "treatment-old")
        replacement = self.reviewed_treatment(api, "treatment-replacement")
        old["status"] = "superseded"
        old["superseded_by_treatment_id"] = replacement["treatment_id"]
        replacement["supersedes_treatment_id"] = old["treatment_id"]
        replacement["created_at"] = "2026-08-27T12:06:00Z"
        replacement["reviewed_at"] = "2026-08-27T12:07:00Z"
        for item in (old, replacement):
            source = {field: item[field] for field in TREATMENT_SOURCE_FIELDS}
            item["source_binding_sha256"] = api.canonical_digest(source)
        items = [old, replacement]
        treatment_set = self.treatment_set(api, items)
        plan = self.refresh_plan(
            api,
            treatment_ids=sorted(item["treatment_id"] for item in items),
        )
        result = api.assess_prefiling_refresh(
            baseline_corpus_digest="a" * 64,
            current_corpus_digest="a" * 64,
            subject_evidence_sha256="b" * 64,
            refresh_plan=plan,
            treatments=treatment_set,
            checked_through="2026-08-27T12:00:00Z",
            filing_cutoff="2026-08-27T11:00:00Z",
            reviewer="И.И. Иванов",
            reviewed_at="2026-08-27T12:10:00Z",
            claim_ids=["practice-claim-1"],
            live_corpus_binding=self.live_binding(api, plan, treatment_set),
        )
        self.assertTrue(result["complete"])
        self.assertEqual(["treatment-old"], result["superseded_treatment_ids"])
        self.assertEqual(
            ["treatment-replacement"], result["verified_treatment_ids"]
        )
        self.assertEqual([], result["pending_treatment_ids"])

    def test_forged_or_cyclic_supersession_fails_closed(self):
        api = self.api()

        isolated = self.reviewed_treatment(api, "treatment-isolated")
        isolated["status"] = "superseded"
        isolated["superseded_by_treatment_id"] = "treatment-missing"
        isolated["source_binding_sha256"] = api.canonical_digest(
            {field: isolated[field] for field in TREATMENT_SOURCE_FIELDS}
        )
        isolated_set = self.treatment_set(api, [isolated])
        isolated_plan = self.refresh_plan(
            api, treatment_ids=[isolated["treatment_id"]]
        )
        isolated_result = api.assess_prefiling_refresh(
            baseline_corpus_digest="a" * 64,
            current_corpus_digest="a" * 64,
            subject_evidence_sha256="b" * 64,
            refresh_plan=isolated_plan,
            treatments=isolated_set,
            checked_through="2026-08-27T12:00:00Z",
            filing_cutoff="2026-08-27T11:00:00Z",
            reviewer="И.И. Иванов",
            reviewed_at="2026-08-27T12:10:00Z",
            claim_ids=["practice-claim-1"],
            live_corpus_binding=self.live_binding(
                api, isolated_plan, isolated_set
            ),
        )
        self.assertFalse(isolated_result["complete"])
        self.assertFalse(isolated_result["treatment_set_contract_valid"])

        first = self.reviewed_treatment(api, "treatment-cycle-a")
        second = self.reviewed_treatment(api, "treatment-cycle-b")
        for item, prior, successor in (
            (first, second["treatment_id"], second["treatment_id"]),
            (second, first["treatment_id"], first["treatment_id"]),
        ):
            item["status"] = "superseded"
            item["supersedes_treatment_id"] = prior
            item["superseded_by_treatment_id"] = successor
            item["created_at"] = "2026-08-27T12:05:00Z"
            item["reviewed_at"] = "2026-08-27T12:05:00Z"
            item["source_binding_sha256"] = api.canonical_digest(
                {field: item[field] for field in TREATMENT_SOURCE_FIELDS}
            )
        cycle_set = self.treatment_set(api, [first, second])
        cycle_plan = self.refresh_plan(
            api, treatment_ids=sorted([first["treatment_id"], second["treatment_id"]])
        )
        cycle_result = api.assess_prefiling_refresh(
            baseline_corpus_digest="a" * 64,
            current_corpus_digest="a" * 64,
            subject_evidence_sha256="b" * 64,
            refresh_plan=cycle_plan,
            treatments=cycle_set,
            checked_through="2026-08-27T12:00:00Z",
            filing_cutoff="2026-08-27T11:00:00Z",
            reviewer="И.И. Иванов",
            reviewed_at="2026-08-27T12:10:00Z",
            claim_ids=["practice-claim-1"],
            live_corpus_binding=self.live_binding(api, cycle_plan, cycle_set),
        )
        self.assertFalse(cycle_result["complete"])
        self.assertFalse(cycle_result["treatment_set_contract_valid"])

    def test_duplicate_treatment_ids_are_grouped_and_conflicts_stay_pending(self):
        api = self.api()
        common = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(api),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:10:00Z",
        }
        verified = self.reviewed_treatment(api, "treatment-duplicate", status="verified")
        rejected = self.reviewed_treatment(api, "treatment-duplicate", status="rejected")
        conflicting_status = api.assess_prefiling_refresh(
            **common,
            treatments=self.treatment_set(api, [verified, rejected]),
        )

        changed_source = copy.deepcopy(verified)
        changed_source["quote"] = "другой фрагмент того же идентификатора"
        source = {
            key: changed_source.get(key) for key in TREATMENT_SOURCE_FIELDS
        }
        changed_source["source_binding_sha256"] = api.canonical_digest(source)
        conflicting_source = api.assess_prefiling_refresh(
            **common,
            treatments=self.treatment_set(api, [verified, changed_source]),
        )

        for conflict in (conflicting_status, conflicting_source):
            self.assertEqual("refresh_incomplete", conflict["status"])
            self.assertEqual(
                ["treatment-duplicate"], conflict["pending_treatment_ids"]
            )
            self.assertEqual([], conflict["verified_treatment_ids"])
            self.assertEqual([], conflict["rejected_treatment_ids"])
            partitions = [
                set(conflict[field])
                for field in (
                    "pending_treatment_ids",
                    "verified_treatment_ids",
                    "rejected_treatment_ids",
                )
            ]
            self.assertFalse(partitions[0] & partitions[1])
            self.assertFalse(partitions[0] & partitions[2])
            self.assertFalse(partitions[1] & partitions[2])

        identical = api.assess_prefiling_refresh(
            **common,
            treatments=self.treatment_set(api, [verified, copy.deepcopy(verified)]),
        )
        self.assertFalse(identical["complete"])
        self.assertIn("treatment_set_contract_invalid", identical["reasons"])

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            [
                "pending_treatment_ids",
                "verified_treatment_ids",
                "rejected_treatment_ids",
                "superseded_treatment_ids",
            ],
            schema["definitions"]["prefiling_refresh"].get("x-pairwise-disjoint"),
        )

    def test_reviewed_treatment_requires_exact_content_bound_source_provenance(self):
        api = self.api()
        common = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(api),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:10:00Z",
        }
        for missing_field in (
            "document_id",
            "official_url",
            "quote",
            "quote_locator",
            "proposition",
            "source_binding_sha256",
        ):
            with self.subTest(missing_field=missing_field):
                treatment = self.reviewed_treatment(api)
                del treatment[missing_field]
                result = api.assess_prefiling_refresh(
                    **common,
                    treatments=self.treatment_set(api, [treatment]),
                )
                self.assertEqual("refresh_incomplete", result["status"])
                self.assertEqual(
                    ["treatment-reviewed"], result["pending_treatment_ids"]
                )

        wrong_binding = self.reviewed_treatment(api)
        wrong_binding["source_binding_sha256"] = "e" * 64
        result = api.assess_prefiling_refresh(
            **common,
            treatments=self.treatment_set(api, [wrong_binding]),
        )
        self.assertEqual("refresh_incomplete", result["status"])

    def test_reviewed_treatment_requires_relation_provenance(self):
        api = self.api()
        common = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(api),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:10:00Z",
        }
        for missing_field in (
            "source_chain_id",
            "target_authority_id",
            "treatment_type",
            "speaker",
        ):
            with self.subTest(missing_field=missing_field):
                treatment = self.reviewed_treatment(api)
                del treatment[missing_field]
                treatment["source_binding_sha256"] = api.canonical_digest(
                    {
                        field: treatment.get(field)
                        for field in TREATMENT_SOURCE_FIELDS
                    }
                )
                result = api.assess_prefiling_refresh(
                    **common,
                    treatments=self.treatment_set(api, [treatment]),
                )
                self.assertEqual("refresh_incomplete", result["status"])
                self.assertFalse(result["complete"])
                self.assertEqual(
                    ["treatment-reviewed"], result["pending_treatment_ids"]
                )

    def test_reviewed_treatment_with_non_official_url_stays_pending(self):
        api = self.api()
        common = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(api),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:10:00Z",
        }
        for url in ("https://localhost/act", "https://example.com/act"):
            with self.subTest(url=url):
                treatment = self.reviewed_treatment(api)
                treatment["official_url"] = url
                treatment["source_binding_sha256"] = api.canonical_digest(
                    {
                        field: treatment.get(field)
                        for field in TREATMENT_SOURCE_FIELDS
                    }
                )
                result = api.assess_prefiling_refresh(
                    **common,
                    treatments=self.treatment_set(api, [treatment]),
                )
                self.assertEqual("refresh_incomplete", result["status"])
                self.assertFalse(result["complete"])
                self.assertEqual(
                    ["treatment-reviewed"], result["pending_treatment_ids"]
                )

    def test_reviewed_treatment_with_discovery_source_role_stays_pending(self):
        api = self.api()
        treatment = self.reviewed_treatment(api)
        treatment["source_role"] = "discovery_only"
        treatment["source_binding_sha256"] = api.canonical_digest(
            {
                field: treatment.get(field)
                for field in TREATMENT_SOURCE_FIELDS
            }
        )
        result = api.assess_prefiling_refresh(
            baseline_corpus_digest="a" * 64,
            current_corpus_digest="a" * 64,
            subject_evidence_sha256="b" * 64,
            refresh_plan=self.refresh_plan(
                api, treatment_ids=["treatment-reviewed"]
            ),
            treatments=self.treatment_set(api, [treatment]),
            checked_through="2026-08-27T12:00:00Z",
            filing_cutoff="2026-08-27T11:00:00Z",
            reviewer="И.И. Иванов",
            reviewed_at="2026-08-27T12:10:00Z",
            claim_ids=["practice-claim-1"],
        )
        self.assertEqual("refresh_incomplete", result["status"])
        self.assertEqual(
            ["treatment-reviewed"], result["pending_treatment_ids"]
        )

    def test_malformed_prefiling_treatment_is_not_discarded(self):
        api = self.api()
        result = api.assess_prefiling_refresh(
            baseline_corpus_digest="a" * 64,
            current_corpus_digest="a" * 64,
            subject_evidence_sha256="b" * 64,
            refresh_plan=self.refresh_plan(api),
            treatments=self.treatment_set(api, [None]),
            checked_through="2026-08-27T12:00:00Z",
            filing_cutoff="2026-08-27T11:00:00Z",
            reviewer="И.И. Иванов",
            reviewed_at="2026-08-27T12:10:00Z",
            claim_ids=["practice-claim-1"],
        )
        self.assertEqual("refresh_incomplete", result["status"])
        self.assertTrue(result["pending_treatment_ids"])

    def test_malformed_refresh_plan_entries_and_gaps_are_explicit_blockers(self):
        api = self.api()
        common = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "treatments": self.treatment_set(api, []),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:10:00Z",
        }
        malformed_entries = api.assess_prefiling_refresh(
            **common,
            refresh_plan=self.refresh_plan(api, entries=[None]),
        )
        self.assertEqual("refresh_incomplete", malformed_entries["status"])
        self.assertTrue(malformed_entries.get("malformed_refresh_entry_ids"))
        self.assertIn("malformed_refresh_plan_entries", malformed_entries["reasons"])

        malformed_gaps = api.assess_prefiling_refresh(
            **common,
            refresh_plan=self.refresh_plan(api, coverage_gaps=[None]),
        )
        self.assertEqual("refresh_incomplete", malformed_gaps["status"])
        self.assertTrue(malformed_gaps.get("malformed_coverage_gap_ids"))
        self.assertIn("malformed_coverage_gaps", malformed_gaps["reasons"])

        missing_scope = api.assess_prefiling_refresh(
            **common,
            refresh_plan=self.refresh_plan(api, coverage_requirements=[]),
        )
        self.assertEqual("refresh_incomplete", missing_scope["status"])
        self.assertIn("refresh_plan_contract_invalid", missing_scope["reasons"])

        undeclared_gap = api.assess_prefiling_refresh(
            **common,
            refresh_plan=self.refresh_plan(
                api,
                coverage_gaps=[
                    {
                        "court_id": "foreign-court",
                        "reason": "coverage_gap_not_observed",
                        "action": "Проверить сегмент.",
                    }
                ],
            ),
        )
        self.assertEqual("refresh_incomplete", undeclared_gap["status"])
        self.assertIn("refresh_plan_contract_invalid", undeclared_gap["reasons"])

    def test_prefiling_treatment_set_must_equal_declared_cache_population(self):
        api = self.api()
        plan = self.refresh_plan(
            api,
            treatment_ids=["treatment-pending", "treatment-reviewed"],
        )
        omitted = self.treatment_set(api, [self.reviewed_treatment(api)])
        result = api.assess_prefiling_refresh(
            baseline_corpus_digest="a" * 64,
            current_corpus_digest="a" * 64,
            subject_evidence_sha256="b" * 64,
            refresh_plan=plan,
            treatments=omitted,
            checked_through="2026-08-27T12:00:00Z",
            filing_cutoff="2026-08-27T11:00:00Z",
            reviewer="И.И. Иванов",
            reviewed_at="2026-08-27T12:10:00Z",
            claim_ids=["practice-claim-1"],
        )
        self.assertEqual("refresh_incomplete", result["status"])
        self.assertFalse(result["treatment_set_contract_valid"])
        self.assertIn("treatment_set_contract_invalid", result["reasons"])

    def test_prefiling_corpus_digests_must_be_lowercase_sha256(self):
        api = self.api()
        common = {
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(api),
            "treatments": self.treatment_set(api, []),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:10:00Z",
        }
        for field in ("baseline_corpus_digest", "current_corpus_digest"):
            with self.subTest(field=field):
                arguments = {
                    **common,
                    "baseline_corpus_digest": "a" * 64,
                    "current_corpus_digest": "a" * 64,
                }
                arguments[field] = "NOT-A-SHA256"
                with self.assertRaisesRegex(ValueError, field):
                    api.assess_prefiling_refresh(**arguments)

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        properties = schema["definitions"]["prefiling_refresh"]["properties"]
        self.assertEqual(
            "^[0-9a-f]{64}$", properties["baseline_corpus_digest"].get("pattern")
        )
        self.assertEqual(
            "^[0-9a-f]{64}$", properties["current_corpus_digest"].get("pattern")
        )

    def test_each_resolved_treatment_review_must_not_postdate_final_review(self):
        api = self.api()
        common = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(api),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-27T12:10:00Z",
            "claim_ids": ["practice-claim-1"],
        }
        postdated = self.reviewed_treatment(api, "treatment-postdated")
        postdated["reviewed_at"] = "2026-08-27T12:11:00Z"
        postdated_result = api.assess_prefiling_refresh(
            **{
                **common,
                "refresh_plan": self.refresh_plan(
                    api, treatment_ids=["treatment-postdated"]
                ),
            },
            treatments=self.treatment_set(api, [postdated]),
        )
        self.assertEqual("refresh_incomplete", postdated_result["status"])
        self.assertEqual(
            ["treatment-postdated"],
            postdated_result.get("treatment_chronology_issue_ids", []),
        )

        mixed_timezone = self.reviewed_treatment(api, "treatment-naive")
        mixed_timezone["reviewed_at"] = "2026-08-27T12:05:00"
        mixed_result = api.assess_prefiling_refresh(
            **{
                **common,
                "refresh_plan": self.refresh_plan(
                    api, treatment_ids=["treatment-naive"]
                ),
            },
            treatments=self.treatment_set(api, [mixed_timezone]),
        )
        self.assertEqual("refresh_incomplete", mixed_result["status"])
        self.assertEqual(
            ["treatment-naive"],
            mixed_result.get("pending_treatment_ids", []),
        )
        self.assertEqual(
            [],
            mixed_result.get("treatment_chronology_issue_ids", []),
        )
        self.assertIn(
            "resolved_treatment_lacks_content_bound_human_review",
            mixed_result["reasons"],
        )

        equal_time = self.reviewed_treatment(api, "treatment-equal")
        equal_time["reviewed_at"] = common["reviewed_at"]
        equal_treatment_set = self.treatment_set(api, [equal_time])
        equal_plan = self.refresh_plan(
            api, treatment_ids=["treatment-equal"]
        )
        equal_result = api.assess_prefiling_refresh(
            **{
                **common,
                "refresh_plan": equal_plan,
            },
            treatments=equal_treatment_set,
            live_corpus_binding=self.live_binding(
                api, equal_plan, equal_treatment_set
            ),
        )
        self.assertTrue(equal_result["complete"])

    def test_prefiling_review_timestamp_must_follow_checked_through_with_same_timezone_kind(self):
        api = self.api()
        common = {
            "baseline_corpus_digest": "a" * 64,
            "current_corpus_digest": "a" * 64,
            "subject_evidence_sha256": "b" * 64,
            "refresh_plan": self.refresh_plan(api),
            "treatments": self.treatment_set(api, []),
            "checked_through": "2026-08-27T12:00:00Z",
            "filing_cutoff": "2026-08-27T11:00:00Z",
            "reviewer": "И.И. Иванов",
        }
        before_check = api.assess_prefiling_refresh(
            **common,
            reviewed_at="2026-08-27T11:59:59Z",
        )
        self.assertEqual("refresh_incomplete", before_check["status"])
        self.assertIn("reviewed_at_before_checked_through", before_check["reasons"])

        mixed_timezone = api.assess_prefiling_refresh(
            **common,
            reviewed_at="2026-08-27T12:10:00",
        )
        self.assertEqual("refresh_incomplete", mixed_timezone["status"])
        self.assertIn("reviewed_at_timezone_mismatch", mixed_timezone["reasons"])

    def test_prefiling_refresh_mixed_naive_and_aware_timestamps_fails_closed(self):
        api = self.api()
        try:
            result = api.assess_prefiling_refresh(
                baseline_corpus_digest="a" * 64,
                current_corpus_digest="a" * 64,
                subject_evidence_sha256="b" * 64,
                refresh_plan=self.refresh_plan(api),
                treatments=self.treatment_set(api, []),
                checked_through="2026-08-27T12:00:00Z",
                filing_cutoff="2026-08-27T11:00:00",
                reviewer="И.И. Иванов",
                reviewed_at="2026-08-27T12:10:00Z",
            )
        except Exception as exc:  # regression: this used to raise TypeError
            self.fail(f"mixed timezone awareness must fail closed, not crash: {exc!r}")
        self.assertEqual("refresh_incomplete", result["status"])
        self.assertFalse(result["complete"])
        self.assertIn("timestamp_timezone_mismatch", result["reasons"])

    def test_prefiling_schema_rejects_incomplete_or_material_status_marked_complete(self):
        api = self.api()
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        refresh = api.assess_prefiling_refresh(
            baseline_corpus_digest="a" * 64,
            current_corpus_digest="a" * 64,
            subject_evidence_sha256="b" * 64,
            refresh_plan=self.refresh_plan(api),
            treatments=self.treatment_set(api, []),
            checked_through="2026-08-27T12:00:00Z",
            filing_cutoff="2026-08-27T11:00:00Z",
            reviewer="И.И. Иванов",
            reviewed_at="2026-08-27T12:10:00Z",
            claim_ids=["practice-claim-1"],
        )
        validator = definition_validator(schema, "prefiling_refresh")
        for status in ("refresh_incomplete", "material_change_requires_reanalysis"):
            with self.subTest(status=status):
                tampered = copy.deepcopy(refresh)
                tampered["status"] = status
                tampered["complete"] = True
                self.assertTrue(
                    list(validator.iter_errors(tampered)),
                    f"{status} cannot be complete",
                )

    def test_runtime_contracts_validate_against_closed_schema(self):
        api = self.api()
        self.assertTrue(SCHEMA_PATH.exists(), "practice-quality schema is missing")
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        definitions = schema["definitions"]
        expected = {
            "chain_stage_observation",
            "chain_meaning_trajectory",
            "chain_propagation_result",
            "uncertainty_dimension",
            "uncertainty_profile",
            "coding_audit_plan",
            "coding_alternative_ground",
            "coding_audit_decision",
            "coding_adjudication",
            "coding_reliability",
            "coverage_requirement",
            "refresh_plan_entry",
            "coverage_gap",
            "refresh_plan",
            "treatment_quality_record",
            "treatment_quality_set",
            "prefiling_refresh",
        }
        self.assertTrue(expected.issubset(definitions))
        for name in expected:
            self.assertFalse(definitions[name].get("additionalProperties", True), name)

        chain_result = api.analyze_chain_stage_propagation(
            [
                self.stage("first"),
                self.stage("cassation", source_stage="cassation", treatment="expressly_adopts"),
            ]
        )
        Draft202012Validator(definitions["chain_propagation_result"]).validate(chain_result)

        cards, comparisons, relations, trajectories = self.profile_inputs(api)
        profile = api.build_uncertainty_profile(
            fingerprint_sha256="f" * 64,
            position_cards=cards,
            comparisons=comparisons,
            applicant_relations=relations,
            temporal_analysis={"temporal_analysis_complete": True, "transitions": []},
            trajectories=trajectories,
            source_reconciliation={"overall_status": "observed_only"},
            coding_reliability={"complete": True, "unresolved_candidate_ids": []},
            higher_authority_treatments=[],
        )
        Draft202012Validator(definitions["uncertainty_profile"]).validate(profile)

        candidates = [{"candidate_id": "candidate-1"}]
        primary = [self.primary("candidate-1")]
        audit_plan = api.build_coding_audit_plan(
            candidates,
            primary,
            plan_sha256="d" * 64,
            sample_size=1,
            exclusion_sample_size=0,
        )
        audit = self.secondary(api, primary[0])
        reliability = api.assess_coding_reliability(audit_plan, primary, [audit])
        definition_validator(schema, "coding_audit_plan").validate(audit_plan)
        definition_validator(schema, "coding_reliability").validate(reliability)

        invented_disagreement = copy.deepcopy(reliability)
        invented_disagreement["field_disagreements"] = [
            {
                "candidate_id": "candidate-1",
                "fields": ["invented"],
                "primary_coding_sha256": "b" * 64,
                "secondary_coding_sha256": "c" * 64,
                "resolved": True,
                "adjudication_sha256": "d" * 64,
            }
        ]
        invented_disagreement["adjudications_sha256"] = "e" * 64
        unsigned = dict(invented_disagreement)
        unsigned.pop("evidence_sha256")
        invented_disagreement["evidence_sha256"] = api.canonical_digest(unsigned)
        self.assertFalse(
            api._coding_reliability_contract_valid(invented_disagreement)
        )
        self.assertTrue(
            list(
                definition_validator(
                    schema, "coding_reliability"
                ).iter_errors(invented_disagreement)
            )
        )

        refresh = api.assess_prefiling_refresh(
            baseline_corpus_digest="a" * 64,
            current_corpus_digest="a" * 64,
            subject_evidence_sha256="b" * 64,
            refresh_plan=self.refresh_plan(api),
            treatments=self.treatment_set(api, []),
            checked_through="2026-08-27T12:00:00Z",
            filing_cutoff="2026-08-27T11:00:00Z",
            reviewer="И.И. Иванов",
            reviewed_at="2026-08-27T12:10:00Z",
            claim_ids=["practice-claim-1"],
        )
        definition_validator(schema, "prefiling_refresh").validate(refresh)
        root_validator = Draft202012Validator(schema)
        refresh_plan = self.refresh_plan(api)
        treatment_set = self.treatment_set(api, [])
        candidate_treatment = {
            "treatment_id": "treatment-candidate",
            "status": "candidate",
            "recorded_status": "candidate",
            "quality_blockers": ["pending_review"],
            "source_chain_id": "chain-1",
            "target_authority_id": "authority-1",
            "supersedes_treatment_id": None,
            "superseded_by_treatment_id": None,
            "created_at": "2026-08-27T11:00:00Z",
        }
        definition_validator(schema, "treatment_quality_record").validate(
            candidate_treatment
        )
        for payload in (
            chain_result,
            profile,
            audit_plan,
            reliability,
            refresh_plan,
            treatment_set,
            refresh,
        ):
            root_validator.validate(payload)

    def test_schema_matches_runtime_audit_and_adjudication_shapes(self):
        api = self.api()
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        primary = self.primary("candidate-schema-parity")
        valid_audit = self.secondary(api, primary)
        validator.validate(valid_audit)

        extra_secondary = copy.deepcopy(valid_audit)
        extra_secondary["secondary_coding"]["invented"] = True
        extra_secondary["secondary_coding_sha256"] = api.canonical_digest(
            extra_secondary["secondary_coding"]
        )
        self.assertTrue(list(validator.iter_errors(extra_secondary)))

        malformed_ground = copy.deepcopy(valid_audit)
        malformed_ground["secondary_coding"]["alternative_grounds"] = [
            {"ground": "Иное основание без логического признака"}
        ]
        malformed_ground["secondary_coding_sha256"] = api.canonical_digest(
            malformed_ground["secondary_coding"]
        )
        self.assertTrue(list(validator.iter_errors(malformed_ground)))

        adjudication = {
            "candidate_id": primary["candidate_id"],
            "primary_coding_sha256": api.canonical_digest(primary),
            "secondary_coding_sha256": valid_audit["secondary_coding_sha256"],
            "resolved_fields": {"invented": "value"},
            "adjudicator": "supervisor-c",
            "reviewed_at": "2026-08-27T12:00:00Z",
            "human_review": "approved",
        }
        self.assertTrue(list(validator.iter_errors(adjudication)))

        multiline_adjudication = {
            **adjudication,
            "resolved_fields": {"reasoning_to_outcome": "Строка 1\nСтрока 2"},
        }
        self.assertTrue(
            api._coding_adjudication_contract_valid(
                multiline_adjudication,
                primary["candidate_id"],
            )
        )
        adjudication_validator = definition_validator(schema, "coding_adjudication")
        adjudication_validator.validate(multiline_adjudication)


if __name__ == "__main__":
    unittest.main()
