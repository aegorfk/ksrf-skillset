import copy
import unittest

from judicial_meaning.casework import (
    ADVERSE_BUCKETS,
    analyze_case_relative_dynamics,
    build_adverse_review,
    build_explainable_queue,
    classify_applicant_relation,
    compare_case_features,
    prepare_casework,
    validate_normative_bridge,
    validate_position_card,
)


class CaseRelativePositionWorkbenchTests(unittest.TestCase):
    def test_verified_feature_cannot_have_an_empty_value_or_unknown_document(self):
        feature = {
            "feature_id": "applicant_case_meaning",
            "value": None,
            "status": "verified",
            "material": True,
            "source": {
                "document_id": "not-in-intake",
                "quote_locator": "абзац 1",
            },
            "query_terms": [],
        }
        with self.assertRaisesRegex(ValueError, "непустого значения"):
            prepare_casework(
                issue="Пределы снижения премии",
                norm_refs=["ст. 135 ТК РФ"],
                features=[feature],
            )
        feature["value"] = "суд допустил снижение"
        with self.assertRaisesRegex(ValueError, "инвентаризированных актов"):
            prepare_casework(
                issue="Пределы снижения премии",
                norm_refs=["ст. 135 ТК РФ"],
                features=[feature],
                allowed_document_ids={"known-document"},
                document_text_by_id={"known-document": "текст"},
            )

    def test_case_features_preserve_explicit_document_and_user_decision_provenance(self):
        result = prepare_casework(
            issue="Пределы изменения стимулирующей выплаты",
            norm_refs=["ст. 135 ТК РФ"],
            features=[
                {
                    "feature_id": "court_meaning",
                    "value": "  премия   не начислена  ",
                    "status": "verified",
                    "material": True,
                    "source": {
                        "source_type": "document",
                        "document_id": "applicant-appeal",
                        "speaker": "court",
                        "quote": "премия работодателем не начислена",
                        "quote_locator": "абзац 14",
                    },
                    "query_terms": [],
                },
                {
                    "feature_id": "materiality_choice",
                    "value": "исходозначимый признак",
                    "status": "verified",
                    "material": True,
                    "source": {
                        "source_type": "user_decision",
                        "decision_id": "decision-2026-08-27-01",
                        "speaker": "applicant",
                    },
                    "query_terms": [],
                },
                {
                    "feature_id": "unknown_basis",
                    "value": None,
                    "status": "unknown",
                    "material": True,
                    "source": {
                        "source_type": "document",
                        "speaker": "party",
                        "quote_locator": "доводы жалобы, абзац 3",
                    },
                    "query_terms": ["не использовать неизвестный факт"],
                },
            ],
        )

        features = {
            item["feature_id"]: item for item in result["fingerprint"]["features"]
        }
        document_source = features["court_meaning"]["source"]
        self.assertEqual("премия не начислена", features["court_meaning"]["value"])
        self.assertEqual("document", document_source["source_type"])
        self.assertEqual("court", document_source["speaker"])
        self.assertEqual(
            "премия работодателем не начислена", document_source["quote"]
        )
        self.assertEqual("абзац 14", document_source["quote_locator"])
        self.assertEqual(
            "decision-2026-08-27-01",
            features["materiality_choice"]["source"]["decision_id"],
        )
        self.assertNotIn("document_id", features["unknown_basis"]["source"])
        self.assertNotIn("quote", features["unknown_basis"]["source"])
        self.assertTrue(
            all(feature["revision"] == 1 for feature in features.values())
        )
        self.assertEqual("unknown", features["unknown_basis"]["confirmation_state"])
        self.assertIn(
            "unknown_basis",
            [task.get("feature_id") for task in result["missing_tasks"]],
        )
        self.assertNotIn(
            "не использовать неизвестный факт",
            [item["query"] for item in result["query_suggestions"]],
        )

    def test_query_compiler_emits_every_subject_neutral_lane_with_traceability(self):
        result = prepare_casework(
            issue="Пределы снижения премии",
            norm_refs=["ст. 135 ТК РФ"],
            features=[
                {
                    "feature_id": "payment_kind",
                    "value": "ежемесячная премия",
                    "status": "verified",
                    "material": True,
                    "source": {
                        "document_id": "applicant-act",
                        "quote_locator": "абзац 7",
                    },
                    "query_terms": [],
                }
            ],
            query_axes={
                "exact_norm": [
                    {
                        "query": "ст. 135 ТК РФ в редакции на дату спора",
                        "status": "verified",
                    }
                ],
                "court_language": [
                    {
                        "query": "стимулирующая выплата является частью заработной платы",
                        "status": "verified",
                        "source": {
                            "source_type": "document",
                            "document_id": "applicant-act",
                            "speaker": "court",
                            "quote": "стимулирующая выплата",
                            "quote_locator": "абзац 7",
                        },
                    }
                ],
                "legal_mechanism": ["неначисление премии"],
                "opposite_reading": [
                    {
                        "query": "непроверенное противоположное толкование",
                        "status": "unknown",
                    }
                ],
            },
        )

        expected_lanes = {
            "exact_norm",
            "court_language",
            "legal_mechanism",
            "controlled_synonym",
            "opposite_reading",
            "narrower_reading",
            "alternative_ground",
            "later_legislation",
            "higher_authority",
        }
        suggestions = result["query_suggestions"]
        self.assertEqual(expected_lanes, {item["lane"] for item in suggestions})
        for suggestion in suggestions:
            self.assertTrue(suggestion["reason_code"])
            self.assertEqual(
                "suggested_unconfirmed", suggestion["confirmation_state"]
            )
            self.assertEqual(
                "pre_freeze_candidate", suggestion["plan_relationship"]
            )
            self.assertEqual(
                result["fingerprint"]["fingerprint_sha256"],
                suggestion["provenance"]["fingerprint_sha256"],
            )
            self.assertEqual(
                result["fingerprint"]["revision"],
                suggestion["provenance"]["fingerprint_revision"],
            )
            self.assertTrue(suggestion["provenance"]["derived_from"])
        court_language = next(
            item
            for item in suggestions
            if item["query"]
            == "стимулирующая выплата является частью заработной платы"
        )
        self.assertEqual(
            "applicant-act",
            court_language["provenance"]["source_records"][0]["document_id"],
        )
        self.assertNotIn(
            "непроверенное противоположное толкование",
            [item["query"] for item in suggestions],
        )
        self.assertIn(
            "ст. 135 ТК РФ в редакции на дату спора",
            [item["query"] for item in suggestions],
        )
        opposite_tasks = [
            task
            for task in result["missing_tasks"]
            if task.get("lane") == "opposite_reading"
        ]
        self.assertTrue(opposite_tasks)
        self.assertTrue(
            all(task["task_type"] == "query_axis_confirmation" for task in opposite_tasks)
        )

    def test_prepare_versions_fingerprint_and_links_every_query_to_its_provenance(self):
        features = [
            {
                "feature_id": "payment_kind",
                "value": "ежемесячная премия",
                "status": "verified",
                "material": True,
                "source": {
                    "document_id": "applicant-cassation",
                    "quote_locator": "абзац 12",
                },
                "query_terms": ["ежемесячная премия", "депремирование"],
            },
            {
                "feature_id": "disciplinary_basis",
                "value": None,
                "status": "unknown",
                "material": True,
                "source": None,
                "query_terms": [],
            },
        ]

        first = prepare_casework(
            issue="Допустимые пределы снижения премии",
            norm_refs=["ст. 135 ТК РФ", "ст. 192 ТК РФ"],
            features=features,
        )

        fingerprint = first["fingerprint"]
        self.assertEqual(1, fingerprint["revision"])
        self.assertEqual(64, len(fingerprint["fingerprint_sha256"]))
        self.assertGreaterEqual(len(first["query_suggestions"]), 4)
        for suggestion in first["query_suggestions"]:
            provenance = suggestion["provenance"]
            self.assertEqual(fingerprint["fingerprint_sha256"], provenance["fingerprint_sha256"])
            self.assertEqual(1, provenance["fingerprint_revision"])
            self.assertTrue(provenance["derived_from"])
        self.assertEqual(
            ["disciplinary_basis"],
            [task["feature_id"] for task in first["missing_tasks"]],
        )
        self.assertTrue(first["missing_tasks"][0]["blocks_comparability"])
        self.assertFalse(first["dependency_state"]["applicant_relative_evidence_stale"])

        unchanged = prepare_casework(
            issue="Допустимые пределы снижения премии",
            norm_refs=["ст. 135 ТК РФ", "ст. 192 ТК РФ"],
            features=features,
            previous_fingerprint=fingerprint,
        )
        self.assertEqual(1, unchanged["fingerprint"]["revision"])
        self.assertEqual(
            fingerprint["fingerprint_sha256"],
            unchanged["fingerprint"]["fingerprint_sha256"],
        )

        changed_features = copy.deepcopy(features)
        changed_features[1]["value"] = "замечание работодателя"
        changed_features[1]["status"] = "verified"
        changed_features[1]["source"] = {
            "document_id": "applicant-appeal",
            "quote_locator": "страница 4",
        }
        changed_features[1]["query_terms"] = ["замечание работодателя"]
        changed = prepare_casework(
            issue="Допустимые пределы снижения премии",
            norm_refs=["ст. 135 ТК РФ", "ст. 192 ТК РФ"],
            features=changed_features,
            previous_fingerprint=fingerprint,
        )
        self.assertEqual(2, changed["fingerprint"]["revision"])
        self.assertNotEqual(
            fingerprint["fingerprint_sha256"],
            changed["fingerprint"]["fingerprint_sha256"],
        )
        self.assertTrue(
            all(
                item["provenance"]["fingerprint_revision"] == 2
                for item in changed["query_suggestions"]
            )
        )
        self.assertTrue(changed["dependency_state"]["applicant_relative_evidence_stale"])
        self.assertEqual(
            fingerprint["fingerprint_sha256"],
            changed["dependency_state"]["superseded_fingerprint_sha256"],
        )

    def test_position_card_requires_verified_court_reasoning_material_to_the_outcome(self):
        card = {
            "position_card_id": "position-1",
            "chain_id": "chain-1",
            "document_id": "document-1",
            "court_id": "2kas",
            "decision_date": "2025-12-04",
            "official_url": "https://2kas.sudrf.ru/example",
            "document_sha256": "a" * 64,
            "speaker": "court",
            "proposition": "Премия входит в систему оплаты труда.",
            "quote": "премия является составной частью заработной платы",
            "quote_locator": "абзац 18",
            "quote_verified": True,
            "full_text_reviewed": True,
            "norm_edition_id": "article-135-edition-1",
            "material_facts": ["премия входит в систему оплаты труда"],
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
            "reasoning_to_outcome": "Этот вывод повлёк взыскание удержанной суммы.",
            "outcome_materiality": "necessary_to_outcome",
            "alternative_grounds": [],
            "reading_family": "wage_component",
            "outcome": "взыскание удержанной суммы",
            "remedy": "взыскание премии",
            "coder": "И.И. Иванов",
            "human_review": "approved",
        }
        self.assertEqual([], validate_position_card(card))

        conflicting = copy.deepcopy(card)
        conflicting["alternative_grounds"] = [
            {
                "ground": "пропуск срока обращения",
                "independently_sufficient": True,
            }
        ]
        errors = validate_position_card(conflicting)
        self.assertTrue(any("самостоятель" in error.lower() for error in errors))

        unverified = copy.deepcopy(card)
        unverified["quote_verified"] = False
        unverified["full_text_reviewed"] = False
        self.assertGreaterEqual(len(validate_position_card(unverified)), 2)

    def test_feature_comparison_explains_matched_distinguishable_and_uncertain_results(self):
        applicant = [
            {
                "feature_id": "payment_kind",
                "value": "ежемесячная",
                "status": "verified",
                "material": True,
            },
            {
                "feature_id": "basis",
                "value": "дисциплинарное взыскание",
                "status": "verified",
                "material": True,
            },
        ]
        same = copy.deepcopy(applicant)
        matched = compare_case_features(applicant, same)
        self.assertEqual("matched", matched["status"])
        self.assertEqual(["basis", "payment_kind"], matched["matched_feature_ids"])

        different = copy.deepcopy(same)
        different[1]["value"] = "невыполнение показателей"
        distinguishable = compare_case_features(applicant, different)
        self.assertEqual("distinguishable", distinguishable["status"])
        self.assertEqual(["basis"], distinguishable["different_feature_ids"])

        incomplete = copy.deepcopy(same)
        incomplete[1]["value"] = None
        incomplete[1]["status"] = "unknown"
        uncertain = compare_case_features(applicant, incomplete)
        self.assertEqual("uncertain", uncertain["status"])
        self.assertEqual(["basis"], uncertain["unknown_feature_ids"])

        reviewed = compare_case_features(
            applicant,
            same,
            reviewer="Иванов И.И.",
            reviewed_at="2026-08-26T12:00:00Z",
            fingerprint_sha256="a" * 64,
        )
        self.assertEqual("approved", reviewed["review_provenance"]["status"])
        self.assertEqual("Иванов И.И.", reviewed["review_provenance"]["reviewer"])
        self.assertEqual("a" * 64, reviewed["fingerprint_sha256"])

    def test_case_relative_dynamics_uses_independent_chains_and_never_claims_causation(self):
        def card(identifier, decision_date, reading_family):
            document_id = f"document-{identifier}"
            return {
                "position_card_id": identifier,
                "chain_id": f"chain-{identifier}",
                "document_id": document_id,
                "court_id": "2kas",
                "decision_date": decision_date,
                "official_url": "https://2kas.sudrf.ru/example",
                "document_sha256": ("a" if identifier == "pre" else "b") * 64,
                "speaker": "court",
                "proposition": "Проверенная позиция суда.",
                "quote": "проверенная позиция суда",
                "quote_locator": "абзац 18",
                "quote_verified": True,
                "full_text_reviewed": True,
                "norm_edition_id": "edition-1",
                "material_facts": ["сопоставимый факт"],
                "comparison_features": [
                    {
                        "feature_id": "fact",
                        "value": "сопоставимый факт",
                        "status": "verified",
                        "material": True,
                        "source": {
                            "document_id": document_id,
                            "quote_locator": "абзац 18",
                        },
                    }
                ],
                "reasoning_to_outcome": "Позиция повлияла на исход.",
                "outcome_materiality": "necessary_to_outcome",
                "alternative_grounds": [],
                "reading_family": reading_family,
                "outcome": "отмена",
                "remedy": "отмена",
                "coder": "И.И. Иванов",
                "human_review": "approved",
            }

        cards = [
            card("pre", "2022-06-01", "employer_discretion"),
            card("post", "2024-06-01", "proportionality"),
        ]
        comparisons = {
            item["position_card_id"]: {
                "status": "matched",
                "fingerprint_sha256": "f" * 64,
                "review_provenance": {"status": "approved"},
            }
            for item in cards
        }
        relations = {
            "pre": {
                "relation": "adverse",
                "fingerprint_sha256": "f" * 64,
                "human_review": "approved",
                "stale": False,
            },
            "post": {
                "relation": "supports",
                "fingerprint_sha256": "f" * 64,
                "human_review": "approved",
                "stale": False,
            },
        }
        result = analyze_case_relative_dynamics(
            cards,
            comparisons,
            relations,
            fingerprint_sha256="f" * 64,
            temporal_strata=[
                {"id": "pre-event", "date_from": "2020-01-01", "date_to": "2023-05-31"},
                {"id": "post-event", "date_from": "2023-06-01", "date_to": "2026-12-31"},
            ],
        )
        self.assertTrue(result["temporal_analysis_complete"])
        self.assertEqual(2, result["independent_chain_count"])
        self.assertEqual(
            "descriptive_distribution_changed", result["transitions"][0]["status"]
        )
        self.assertFalse(result["transitions"][0]["causal_claim_permitted"])
        self.assertIn("не доказывает", result["claim_limit"])

        del relations["post"]
        blocked = analyze_case_relative_dynamics(
            cards,
            comparisons,
            relations,
            fingerprint_sha256="f" * 64,
        )
        self.assertFalse(blocked["temporal_analysis_complete"])
        self.assertEqual("post", blocked["unresolved_position_cards"][0]["position_card_id"])

    def test_applicant_relation_depends_on_comparability_before_reading_family(self):
        applicant_position = {
            "supportive_reading_families": ["wage_component"],
            "adverse_reading_families": ["employer_discretion"],
            "human_review": "approved",
        }
        supportive_card = {
            "position_card_id": "position-1",
            "reading_family": "wage_component",
            "speaker": "court",
            "quote_verified": True,
            "full_text_reviewed": True,
            "outcome_materiality": "necessary_to_outcome",
            "human_review": "approved",
        }
        adverse_card = {
            "position_card_id": "position-2",
            "reading_family": "employer_discretion",
            "speaker": "court",
            "quote_verified": True,
            "full_text_reviewed": True,
            "outcome_materiality": "necessary_to_outcome",
            "human_review": "approved",
        }

        matched_comparison = {
            "status": "matched",
            "fingerprint_sha256": "a" * 64,
            "review_provenance": {"status": "approved"},
        }

        supports = classify_applicant_relation(
            supportive_card,
            matched_comparison,
            applicant_position,
            current_fingerprint_sha256="a" * 64,
        )
        self.assertEqual("supports", supports["relation"])
        self.assertIn("wage_component", supports["reason"])

        adverse = classify_applicant_relation(
            adverse_card,
            matched_comparison,
            applicant_position,
            current_fingerprint_sha256="a" * 64,
        )
        self.assertEqual("adverse", adverse["relation"])

        distinguished = classify_applicant_relation(
            supportive_card,
            {
                "status": "distinguishable",
                "different_feature_ids": ["basis"],
                "fingerprint_sha256": "a" * 64,
                "review_provenance": {"status": "approved"},
            },
            applicant_position,
            current_fingerprint_sha256="a" * 64,
        )
        self.assertEqual("distinguishes", distinguished["relation"])
        self.assertIn("basis", distinguished["reason"])

        unresolved = classify_applicant_relation(
            supportive_card,
            {
                "status": "uncertain",
                "unknown_feature_ids": ["payment_kind"],
                "fingerprint_sha256": "a" * 64,
                "review_provenance": {"status": "approved"},
            },
            applicant_position,
            current_fingerprint_sha256="a" * 64,
        )
        self.assertEqual("unresolved", unresolved["relation"])

        stale = classify_applicant_relation(
            supportive_card,
            matched_comparison,
            applicant_position,
            current_fingerprint_sha256="b" * 64,
        )
        self.assertEqual("unresolved", stale["relation"])
        self.assertTrue(stale["stale"])
        self.assertIn("измен", stale["reason"].lower())

        pending_review = classify_applicant_relation(
            supportive_card,
            {
                "status": "matched",
                "fingerprint_sha256": "a" * 64,
                "review_provenance": {"status": "pending_human_review"},
            },
            applicant_position,
            current_fingerprint_sha256="a" * 64,
        )
        self.assertEqual("unresolved", pending_review["relation"])

        contextual = copy.deepcopy(supportive_card)
        contextual["outcome_materiality"] = "contextual"
        result = classify_applicant_relation(
            contextual,
            matched_comparison,
            applicant_position,
            current_fingerprint_sha256="a" * 64,
        )
        self.assertEqual("neutral", result["relation"])
        self.assertIn("не считается прямой", result["reason"])

    def test_explainable_queue_preserves_every_candidate_and_every_resolution_reason(self):
        candidates = [
            {"candidate_id": "candidate-1", "chain_id": "chain-1", "document_id": "doc-1"},
            {"candidate_id": "candidate-2", "chain_id": "chain-2", "document_id": "doc-2"},
            {"candidate_id": "candidate-3", "chain_id": "chain-3", "document_id": "doc-3"},
        ]
        resolutions = {
            "candidate-1": {
                "decision": "position_card",
                "position_card_id": "position-1",
                "reason": "Суд принял исходозначимое толкование.",
            },
            "candidate-2": {
                "decision": "exclude",
                "reason": "Позиция приведена только в доводах стороны.",
                "human_review": "approved",
            },
        }

        queue = build_explainable_queue(candidates, resolutions)

        self.assertEqual(3, queue["input_count"])
        self.assertEqual(3, queue["output_count"])
        self.assertEqual(
            ["coded_position", "reviewed_exclusion", "pending_review"],
            [item["status"] for item in queue["items"]],
        )
        self.assertEqual(["candidate-3"], queue["unresolved_candidate_ids"])
        self.assertTrue(all(item["explanation"] for item in queue["items"]))
        self.assertTrue(all(item["reason_codes"] for item in queue["items"]))

    def test_queue_applies_court_stratum_and_lane_quotas_without_dropping_candidates(self):
        candidates = [
            {
                "candidate_id": "candidate-1",
                "chain_id": "chain-1",
                "document_id": "doc-1",
                "court_id": "2kas",
                "stratum_id": "post-event",
                "lane": "exact_norm",
            },
            {
                "candidate_id": "candidate-2",
                "chain_id": "chain-2",
                "document_id": "doc-2",
                "court_id": "2kas",
                "stratum_id": "post-event",
                "lane": "exact_norm",
            },
            {
                "candidate_id": "candidate-3",
                "chain_id": "chain-3",
                "document_id": "doc-3",
                "court_id": "1kas",
                "stratum_id": "pre-event",
                "lane": "adverse",
            },
        ]
        queue = build_explainable_queue(
            candidates,
            quotas={
                "court_id": {"2kas": 1, "1kas": 1},
                "stratum_id": {"post-event": 1, "pre-event": 1},
                "lane": {"exact_norm": 1, "adverse": 1},
            },
        )
        self.assertEqual(3, queue["output_count"])
        self.assertEqual(2, len(queue["priority_candidate_ids"]))
        self.assertEqual("candidate-1", queue["priority_candidate_ids"][0])
        self.assertIn("quota_not_selected", queue["items"][1]["reason_codes"])
        self.assertTrue(queue["all_candidates_preserved"])

    def test_adverse_review_always_exposes_four_buckets_and_never_converts_no_hits_to_absence(self):
        def adverse_card(identifier, buckets):
            return {
                "position_card_id": identifier,
                "chain_id": f"chain-{identifier}",
                "document_id": f"document-{identifier}",
                "court_id": "2kas",
                "decision_date": "2025-12-04",
                "official_url": "https://2kas.sudrf.ru/example",
                "document_sha256": "a" * 64,
                "speaker": "court",
                "proposition": "Проверенная позиция.",
                "quote": "проверенная позиция суда",
                "quote_locator": "абзац 18",
                "quote_verified": True,
                "full_text_reviewed": True,
                "norm_edition_id": "edition-1",
                "material_facts": ["проверенный факт"],
                "comparison_features": [
                    {
                        "feature_id": "fact",
                        "value": "проверенный факт",
                        "status": "verified",
                        "material": True,
                        "source": {
                            "document_id": f"document-{identifier}",
                            "quote_locator": "абзац 18",
                        },
                    }
                ],
                "reasoning_to_outcome": "Позиция повлияла на исход.",
                "outcome_materiality": "necessary_to_outcome",
                "alternative_grounds": [],
                "reading_family": "reading-a",
                "outcome": "отмена",
                "remedy": "отмена",
                "coder": "И.И. Иванов",
                "human_review": "approved",
                "adverse_buckets": buckets,
            }

        cards = [
            adverse_card(
                "position-adverse-1", ["opposite_reading", "alternative_ground"]
            ),
            adverse_card("position-adverse-2", ["later_authority"]),
        ]

        review = build_adverse_review(
            cards,
            completed_buckets=ADVERSE_BUCKETS,
            executed_query_ids_by_bucket={
                bucket: [f"query-{bucket}"] for bucket in ADVERSE_BUCKETS
            },
            unresolved_segments_by_bucket={bucket: [] for bucket in ADVERSE_BUCKETS},
            maximum_claim_effect_by_bucket={
                bucket: "Ограничить вывод раскрытым корпусом."
                for bucket in ADVERSE_BUCKETS
            },
        )

        self.assertEqual(set(ADVERSE_BUCKETS), set(review["buckets"]))
        self.assertTrue(review["completed"])
        self.assertEqual(["position-adverse-1"], review["buckets"]["opposite_reading"])
        self.assertEqual(["narrower_reading"], review["no_hit_buckets"])
        self.assertIn("раскрытом", review["no_hit_wording"].lower())
        self.assertIn("не доказано", review["no_hit_wording"].lower())
        self.assertEqual(
            ["query-opposite_reading"],
            review["bucket_reviews"]["opposite_reading"]["executed_query_ids"],
        )

        incomplete = build_adverse_review(
            cards,
            completed_buckets=["opposite_reading", "narrower_reading", "alternative_ground"],
            executed_query_ids_by_bucket={
                bucket: [f"query-{bucket}"] for bucket in ADVERSE_BUCKETS
            },
            unresolved_segments_by_bucket={bucket: [] for bucket in ADVERSE_BUCKETS},
            maximum_claim_effect_by_bucket={
                bucket: "Ограничить вывод раскрытым корпусом."
                for bucket in ADVERSE_BUCKETS
            },
        )
        self.assertFalse(incomplete["completed"])
        self.assertEqual(["later_authority"], incomplete["missing_buckets"])

    def test_normative_bridge_requires_all_links_and_rejects_frequency_as_proof(self):
        bridge = {
            "norm_ref": "ст. 135 ТК РФ",
            "applicant_case_meaning": "Работодатель вправе полностью не начислить премию.",
            "corpus_observation": "В сопоставимых делах обнаружены два исходозначимых чтения.",
            "constitutional_consequence": "Непредсказуемость затрагивает право на вознаграждение за труд.",
            "ordinary_remedy_analysis": "Дефект не устраняется проверкой расчёта, поскольку связан с открытым смыслом нормы.",
            "supporting_position_card_ids": ["position-1"],
            "adverse_position_card_ids": ["position-2"],
            "fingerprint_sha256": "a" * 64,
            "maximum_permitted_claim": "corroborated_observed_corpus",
            "claim_wording": "В раскрытом сопоставимом корпусе наблюдаются два исходозначимых чтения.",
            "reviewer": "И.И. Иванов",
            "reviewed_at": "2026-08-26T00:00:00Z",
            "human_review": "approved",
        }
        supporting = {
            "position-1": {
                "position_card_id": "position-1",
                "speaker": "court",
                "quote_verified": True,
                "full_text_reviewed": True,
                "outcome_materiality": "necessary_to_outcome",
                "human_review": "approved",
            },
            "position-2": {
                "position_card_id": "position-2",
                "speaker": "court",
                "quote_verified": True,
                "full_text_reviewed": True,
                "outcome_materiality": "necessary_to_outcome",
                "human_review": "approved",
            },
        }
        comparisons = {
            "position-1": {
                "status": "matched",
                "fingerprint_sha256": "a" * 64,
                "review_provenance": {"status": "approved"},
            },
            "position-2": {
                "status": "matched",
                "fingerprint_sha256": "a" * 64,
                "review_provenance": {"status": "approved"},
            },
        }
        relations = {
            "position-1": {"relation": "supports", "stale": False, "human_review": "approved"},
            "position-2": {"relation": "adverse", "stale": False, "human_review": "approved"},
        }
        self.assertEqual(
            [],
            validate_normative_bridge(
                bridge,
                current_fingerprint_sha256="a" * 64,
                maximum_permitted_claim="corroborated_observed_corpus",
                position_cards=supporting,
                comparisons=comparisons,
                applicant_relations=relations,
                adverse_review={"completed": True},
            ),
        )

        incomplete = copy.deepcopy(bridge)
        incomplete["ordinary_remedy_analysis"] = ""
        self.assertTrue(validate_normative_bridge(incomplete))

        overstated = copy.deepcopy(bridge)
        overstated["corpus_observation"] = "Частота решений доказывает неконституционность нормы."
        errors = validate_normative_bridge(overstated)
        self.assertTrue(any("не доказывает" in error.lower() for error in errors))

        excessive = copy.deepcopy(bridge)
        excessive["maximum_permitted_claim"] = "all_practice"
        errors = validate_normative_bridge(
            excessive,
            current_fingerprint_sha256="a" * 64,
            maximum_permitted_claim="corroborated_observed_corpus",
            position_cards=supporting,
            comparisons=comparisons,
            applicant_relations=relations,
            adverse_review={"completed": True},
        )
        self.assertTrue(any("maximum_permitted_claim" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
