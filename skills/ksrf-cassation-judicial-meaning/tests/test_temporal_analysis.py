import unittest

from judicial_meaning.analysis import (
    analyze_reviewed_chains,
    build_thesis_candidates,
    validate_thesis_candidate,
    validate_thesis_readiness,
)


STRATA = [
    {"id": "before", "label": "До события", "date_from": "2022-01-01", "date_to": "2022-12-31"},
    {"id": "after", "label": "После события", "date_from": "2023-01-01", "date_to": "2023-12-31"},
    {"id": "future", "label": "Следующий период", "date_from": "2024-01-01", "date_to": "2024-12-31"},
]
EVENTS = [
    {
        "id": "event-1",
        "label": "Официальное интерпретационное событие",
        "effective_date": "2023-01-01",
        "official_source_url": "https://official.example.invalid/event",
        "before_stratum_id": "before",
        "after_stratum_id": "after",
    }
]


def record(chain_id, family, decision_date, *, comparable=True, relation="supports"):
    return {
        "chain_id": chain_id,
        "reading_family": family,
        "relation": relation,
        "human_review": "approved",
        "decision_date": decision_date,
        "court_code": "2kas",
        "norm_edition_id": "edition-1",
        "material_facts_group": "comparable",
        "comparability_approved": comparable,
    }


class TemporalAnalysisTests(unittest.TestCase):
    def analyze(self, records, coverage_status="closed_official_population_observed"):
        return analyze_reviewed_chains(
            records,
            coverage_status=coverage_status,
            temporal_strata=STRATA,
            interpretive_events=EVENTS,
        )

    def test_matrices_count_unique_chains_and_keep_empty_stratum(self):
        before = record("a", "wide", "2022-06-01")
        result = self.analyze([before, dict(before), record("b", "narrow", "2023-06-01", relation="adverse")])

        self.assertEqual(2, result["independent_chain_count"])
        self.assertEqual(
            {"coded_chain_denominator": 1, "counts": {"wide": 1}, "shares": {"wide": 1.0}},
            result["reading_family_by_year"]["2022"],
        )
        self.assertEqual(
            {"coded_chain_denominator": 1, "counts": {"narrow": 1}, "shares": {"narrow": 1.0}},
            result["reading_family_by_stratum"]["after"],
        )
        self.assertEqual(
            {"coded_chain_denominator": 0, "counts": {}, "shares": {}},
            result["reading_family_by_stratum"]["future"],
        )
        self.assertEqual("approved_independent_coded_chains", result["denominator_scope"])
        self.assertEqual([], result["temporal_unassigned_chain_ids"])

    def test_event_classifies_emergent_and_mixed_post_event_readings(self):
        emergent = self.analyze(
            [record("a", "wide", "2022-06-01"), record("b", "narrow", "2023-06-01", relation="adverse")]
        )
        self.assertEqual("emergent_reading_candidate", emergent["status"])
        self.assertTrue(emergent["temporal_analysis_complete"])
        self.assertEqual(["narrow"], emergent["interpretive_event_findings"][0]["emergent_families"])

        mixed = self.analyze(
            [
                record("a", "wide", "2022-06-01"),
                record("b", "wide", "2023-04-01"),
                record("c", "narrow", "2023-06-01", relation="adverse"),
            ]
        )
        self.assertEqual("mixed_post_event", mixed["status"])
        self.assertEqual(["wide"], mixed["interpretive_event_findings"][0]["persisting_families"])

    def test_temporal_event_does_not_override_fact_or_circuit_confounders(self):
        fact_records = [
            {**record("a", "wide", "2022-06-01"), "material_facts_group": "facts-before"},
            {**record("b", "narrow", "2023-06-01"), "material_facts_group": "facts-after"},
        ]
        self.assertEqual("fact_sensitive_divergence", self.analyze(fact_records)["status"])

        circuit_records = [
            {**record("a", "wide", "2022-06-01"), "court_code": "1kas"},
            {**record("b", "narrow", "2023-06-01"), "court_code": "2kas"},
        ]
        self.assertEqual("circuit_divergence_candidate", self.analyze(circuit_records)["status"])

    def test_stable_mix_is_not_change_and_disappearing_family_is_disclosed(self):
        stable_mix = self.analyze(
            [
                record("a", "wide", "2022-04-01"),
                record("b", "narrow", "2022-06-01"),
                record("c", "wide", "2023-04-01"),
                record("d", "narrow", "2023-06-01"),
            ]
        )
        finding = stable_mix["interpretive_event_findings"][0]
        self.assertEqual("no_observed_change", finding["status"])
        self.assertNotEqual("mixed_post_event", stable_mix["status"])

        contraction = self.analyze(
            [
                record("a", "wide", "2022-04-01"),
                record("b", "narrow", "2022-06-01"),
                record("c", "wide", "2023-04-01"),
            ]
        )
        finding = contraction["interpretive_event_findings"][0]
        self.assertEqual(["narrow"], finding["disappeared_families"])
        self.assertEqual("contracted_post_event_observation", finding["status"])

    def test_bounded_sample_does_not_unlock_event_thesis(self):
        result = self.analyze(
            [record("a", "wide", "2022-06-01"), record("b", "narrow", "2023-06-01")],
            coverage_status="bounded_sample_observed",
        )
        self.assertEqual("insufficient_temporal_evidence", result["status"])
        self.assertFalse(result["temporal_analysis_complete"])
        explicit_closed = self.analyze(
            [record("a", "wide", "2022-06-01"), record("b", "narrow", "2023-06-01")],
            coverage_status="closed_declared_enumeration_observed",
        )
        self.assertEqual("emergent_reading_candidate", explicit_closed["status"])

    def test_missing_side_date_or_comparability_blocks_temporal_conclusion(self):
        scenarios = (
            [record("a", "wide", "2022-06-01")],
            [record("a", "wide", None), record("b", "narrow", "2023-06-01")],
            [record("a", "wide", "2022-06-01"), record("b", "narrow", "2023-06-99")],
            [record("a", "wide", "2022-06-01", comparable=False), record("b", "narrow", "2023-06-01")],
        )
        for records in scenarios:
            with self.subTest(records=records):
                result = self.analyze(records)
                self.assertEqual("insufficient_temporal_evidence", result["status"])
                self.assertFalse(result["temporal_analysis_complete"])
        invalid_date = self.analyze(
            [record("a", "wide", "2022-06-01"), record("b", "narrow", "2023-06-99")]
        )
        self.assertEqual(["b"], invalid_date["temporal_unassigned_chain_ids"])
        self.assertNotIn("2023", invalid_date["reading_family_by_year"])
        self.assertNotIn("2023", invalid_date["year_counts"])

    def test_temporal_candidate_requires_complete_evidence_and_event_link(self):
        plan = {
            "plan_sha256": "a" * 64,
            "research_questions": [{"id": "rq-1", "norm_refs": ["ст. 10 Примерного кодекса"]}],
        }
        applicant_chain = {"propositions": [{"speaker": "court", "meaning": "узкое чтение"}]}
        records = [record("a", "wide", "2022-06-01"), record("b", "narrow", "2023-06-01")]
        blocked = build_thesis_candidates(
            plan,
            applicant_chain,
            records,
            {"status": "insufficient_temporal_evidence", "coverage_status": "closed_official_population_observed"},
        )
        self.assertEqual([], blocked)

        analysis = self.analyze(records)
        candidates = build_thesis_candidates(plan, applicant_chain, records, analysis)
        self.assertEqual(["event-1"], candidates[0]["interpretive_event_ids"])
        self.assertIn("впервые наблюдается", candidates[0]["observed_statement"])
        self.assertNotIn("динамик", candidates[0]["observed_statement"].casefold())
        candidate = candidates[0]
        candidate.update(
            {
                "normative_defect_bridge": "Проверяемый нормативный мост.",
                "human_review": "approved",
                "drafting_ready": True,
            }
        )
        candidate["interpretive_event_ids"] = []
        self.assertTrue(validate_thesis_candidate(candidate))

    def test_temporal_thesis_uses_bounded_observation_not_trend_wording(self):
        state = {
            "plan_frozen": True,
            "collection_complete": True,
            "coding_complete": True,
            "adverse_review_complete": True,
            "coverage_review_complete": True,
            "human_approved": True,
            "candidate_approved": True,
            "maximum_permitted_claim": "emergent_reading_candidate",
            "temporal_analysis_complete": True,
        }
        bounded = "В раскрытом корпусе после указанного события впервые наблюдается иное чтение нормы."
        self.assertEqual([], validate_thesis_readiness(state, bounded))
        for thesis in (
            "В раскрытом корпусе выявлена динамика чтений после указанного события.",
            "За десять лет установлена устойчивая динамика перехода всех кассационных судов.",
        ):
            with self.subTest(thesis=thesis):
                self.assertTrue(validate_thesis_readiness(state, thesis))


if __name__ == "__main__":
    unittest.main()
