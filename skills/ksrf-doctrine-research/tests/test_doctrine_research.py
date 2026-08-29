import argparse
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "doctrine_research.py"
FIXTURES = Path(__file__).parent / "fixtures"
SPEC = importlib.util.spec_from_file_location("doctrine_research", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def request_payload(**overrides):
    request = {
        "schema_version": "1.0",
        "matter_id": "generic-private-law-test",
        "mode": "exploratory_norm",
        "as_of_date": "2026-08-29",
        "jurisdiction": "RU",
        "languages": ["ru"],
        "norms": [
            {
                "citation": "ст. 10 Примерного кодекса",
                "citation_variants": ["статья 10 Примерного кодекса"],
                "title": "Пределы осуществления права",
                "version_date": None,
                "public_text_excerpt": "Не допускается произвольное осуществление права.",
            }
        ],
        "judicial_meanings": [],
        "disputed_elements": ["предел усмотрения"],
        "mechanisms": ["отказ в защите права"],
        "consequences": ["утрата способа защиты"],
        "adjacent_norms": ["ст. 11 Примерного кодекса"],
        "subject_terms": ["добросовестность в частном праве"],
        "date_range": {"from": 1992, "to": 2026},
        "material_types": ["journal-article", "book-chapter"],
        "provider_access": {},
        "privacy": {
            "class": "public_abstracted",
            "external_queries_redacted": True,
            "prohibited_external_terms": [],
        },
    }
    request.update(overrides)
    return request


def write_request(root: Path, request=None) -> Path:
    path = root / "request.json"
    path.write_text(json.dumps(request or request_payload(), ensure_ascii=False), encoding="utf-8")
    return path


class DoctrineResearchTests(unittest.TestCase):
    def test_plan_is_stable_and_contains_no_legal_conclusion(self):
        request = request_payload()
        first = MODULE.build_query_plan(request)
        second = MODULE.build_query_plan(json.loads(json.dumps(request)))
        self.assertEqual(first, second)
        self.assertEqual([], first["legal_conclusions"])
        self.assertFalse(MODULE.build_problem_profile(request)["constitutional_conclusion_preseeded"])
        self.assertNotIn("неконституц", json.dumps(first, ensure_ascii=False).casefold())

    def test_unique_strings_handles_null_and_whole_string(self):
        self.assertEqual([], MODULE.unique_strings(None))
        self.assertEqual(["единое значение"], MODULE.unique_strings("единое значение"))

    def test_router_and_queries_are_not_tied_to_labour_example(self):
        request = request_payload()
        plan = MODULE.build_query_plan(request)
        payload = json.dumps(plan, ensure_ascii=False).casefold()
        self.assertIn("примерного кодекса", payload)
        self.assertNotIn("заработ", payload)
        self.assertNotIn("индексац", payload)
        self.assertTrue(any(row["lane"] == "adverse" for row in plan["queries"]))

    def test_bounded_selection_is_balanced_across_query_lanes(self):
        plan = MODULE.build_query_plan(request_payload())
        selected = MODULE.select_bounded_queries(plan, 11)
        lanes = {row["lane"] for row in selected}
        self.assertIn("exact_norm", lanes)
        self.assertIn("problem_probe", lanes)
        self.assertIn("adverse", lanes)
        self.assertIn("procedure_evidence", lanes)
        self.assertIn("remedy", lanes)
        self.assertIn("history_update", lanes)

    def test_offline_adapters_deduplicate_same_doi_and_do_not_use_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = write_request(root)
            workspace = root / "run"
            args = argparse.Namespace(
                request=str(request_path),
                workspace=str(workspace),
                providers="openalex,crossref",
                max_queries=1,
                max_results=5,
                timeout=1.0,
                offline_fixtures=str(FIXTURES),
            )
            with patch.object(MODULE.urllib.request, "urlopen", side_effect=AssertionError("network used")):
                exit_code = MODULE.run_search(args)
            self.assertEqual(0, exit_code)
            sources = MODULE.read_jsonl(workspace / "source-ledger.jsonl")
            self.assertEqual(1, len(sources))
            self.assertEqual(["crossref", "openalex"], sources[0]["discovered_by"])
            self.assertEqual("10.5555/example.2024.1", sources[0]["doi"])
            self.assertEqual("candidate_only", sources[0]["promotion_status"])
            self.assertNotEqual("page_verified", sources[0]["verification_status"])
            coverage = MODULE.load_json(workspace / "coverage-report.json")
            self.assertTrue(coverage["bounded_search_complete"])
            self.assertFalse(coverage["coverage_complete"])
            self.assertFalse(coverage["absence_claim_permitted"])

    def test_offline_fixture_miss_never_falls_through_to_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_root = root / "empty-fixtures"
            fixture_root.mkdir()
            args = argparse.Namespace(
                request=str(write_request(root)),
                workspace=str(root / "run"),
                providers="openalex",
                max_queries=1,
                max_results=5,
                timeout=1.0,
                offline_fixtures=str(fixture_root),
            )
            with patch.object(MODULE.urllib.request, "urlopen", side_effect=AssertionError("network used")):
                exit_code = MODULE.run_search(args)
            self.assertEqual(3, exit_code)
            coverage = MODULE.load_json(root / "run" / "coverage-report.json")
            self.assertEqual("offline_fixture_miss", coverage["provider_statuses"][0]["status"])
            self.assertFalse(coverage["bounded_search_complete"])

    def test_redaction_gate_blocks_before_transport(self):
        request = request_payload(subject_terms=["expert@example.org"])
        plan = MODULE.build_query_plan(request)
        violations = MODULE.redaction_violations(plan, request)
        self.assertTrue(violations)
        self.assertTrue(all(row["reason"] == "pii_like_pattern" for row in violations))

    def test_external_privacy_and_case_inputs_fail_closed(self):
        private = request_payload(privacy={"class": "private_raw", "external_queries_redacted": True})
        self.assertTrue(any("privacy.class" in error for error in MODULE.validate_request(private, for_external_search=True)))

        malformed = request_payload(judicial_meanings="судебный смысл")
        self.assertIn("judicial_meanings must be a list", MODULE.validate_request(malformed))

        case_scoped = request_payload(
            mode="case_scoped",
            judicial_meanings=["публичная формула"],
        )
        case_scoped["norms"][0]["version_date"] = "2024-01-01"
        self.assertTrue(any("application_evidence_ref" in error for error in MODULE.validate_request(case_scoped)))

        verification = request_payload(mode="hypothesis_verification")
        errors = MODULE.validate_request(verification)
        self.assertTrue(any("hypotheses_under_test" in error for error in errors))
        self.assertTrue(any("fulltext_source_refs" in error for error in errors))
        self.assertTrue(any("adverse_search_required" in error for error in errors))

    def test_case_and_verification_inputs_reject_blank_values_and_invalid_dates(self):
        case_scoped = request_payload(
            mode="case_scoped",
            as_of_date="2026-99-99",
            judicial_meanings=[""],
            mechanisms=[""],
            consequences=[""],
            application_evidence_refs=[""],
            date_range={"from": 2000, "to": 9999},
        )
        case_scoped["norms"][0]["version_date"] = "current"
        errors = MODULE.validate_request(case_scoped)
        self.assertTrue(any("valid YYYY-MM-DD" in error for error in errors))
        self.assertTrue(any("non-empty judicial_meaning" in error for error in errors))
        self.assertTrue(any("non-empty mechanism" in error for error in errors))
        self.assertTrue(any("non-empty consequence" in error for error in errors))
        self.assertTrue(any("non-empty application_evidence_ref" in error for error in errors))

        verification = request_payload(
            mode="hypothesis_verification",
            hypotheses_under_test=[""],
            fulltext_source_refs=[""],
            adverse_search_required=True,
        )
        errors = MODULE.validate_request(verification)
        self.assertTrue(any("non-empty hypotheses_under_test" in error for error in errors))
        self.assertTrue(any("non-empty fulltext_source_refs" in error for error in errors))

    def test_hypothesis_verification_always_plans_adverse_lane(self):
        request = request_payload(
            mode="hypothesis_verification",
            disputed_elements=[],
            hypotheses_under_test=["Норма оставляет чрезмерное усмотрение"],
            fulltext_source_refs=["src-fulltext-1"],
            adverse_search_required=True,
        )
        self.assertEqual([], MODULE.validate_request(request))
        plan = MODULE.build_query_plan(request)
        self.assertTrue(any(row["lane"] == "adverse" for row in plan["queries"]))

    def test_query_fields_reject_untyped_or_unknown_mapping_items(self):
        request = request_payload(
            mode="case_scoped",
            judicial_meanings=[{"foo": "ALPHA-CONFIDENTIAL"}],
            mechanisms=[{"foo": "ALPHA-CONFIDENTIAL"}],
            consequences=[{"foo": "ALPHA-CONFIDENTIAL"}],
            application_evidence_refs=[{"foo": "ALPHA-CONFIDENTIAL"}],
        )
        request["norms"][0]["version_date"] = "2026-08-29"
        errors = MODULE.validate_request(request, for_external_search=True)
        self.assertTrue(any("judicial_meanings" in error for error in errors))
        self.assertTrue(any("mechanisms" in error for error in errors))
        self.assertTrue(any("consequences" in error for error in errors))
        self.assertTrue(any("application_evidence_refs" in error for error in errors))

    def test_norm_and_phrase_query_anchors_reject_nested_objects(self):
        for norm_field in ("citation", "title"):
            with self.subTest(norm_field=norm_field):
                request = request_payload()
                request["norms"][0][norm_field] = {"foo": "ALPHA-CONFIDENTIAL"}
                self.assertTrue(MODULE.validate_request(request, for_external_search=True))

        request = request_payload()
        request["norms"][0]["citation_variants"] = [{"foo": "ALPHA-CONFIDENTIAL"}]
        self.assertTrue(any("citation_variants" in error for error in MODULE.validate_request(request, for_external_search=True)))

        request = request_payload(judicial_meanings=[{"public_excerpt": {"foo": "ALPHA-CONFIDENTIAL"}}])
        errors = MODULE.validate_request(request, for_external_search=True)
        self.assertTrue(any("phrase values must be strings" in error for error in errors))

        request = request_payload(languages=[{"foo": "ALPHA-CONFIDENTIAL"}])
        errors = MODULE.validate_request(request, for_external_search=True)
        self.assertTrue(any("languages" in error for error in errors))

        request = request_payload(
            mode="hypothesis_verification",
            hypotheses_under_test=[{"hypothesis": {"foo": "ALPHA-CONFIDENTIAL"}}],
            fulltext_source_refs=["src-1"],
            adverse_search_required=True,
        )
        errors = MODULE.validate_request(request, for_external_search=True)
        self.assertTrue(any("phrase values must be strings" in error for error in errors))

    def test_redaction_gate_detects_identity_and_case_identifiers(self):
        for value in (
            "Иванов Иван Иванович",
            "ИНН: 7701234567",
            "ОГРН: 1234567890123",
            "дело 2-1234/2025",
            "адрес: Москва, улица Примерная, 1",
        ):
            with self.subTest(value=value):
                request = request_payload(subject_terms=[value])
                self.assertTrue(MODULE.redaction_violations(MODULE.build_query_plan(request), request))

    def test_manual_provider_and_disabled_adapter_are_not_called(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manual_args = argparse.Namespace(
                request=str(write_request(root)),
                workspace=str(root / "manual"),
                providers="elibrary",
                max_queries=1,
                max_results=5,
                timeout=1.0,
                offline_fixtures=str(FIXTURES),
            )
            with patch.object(MODULE.urllib.request, "urlopen", side_effect=AssertionError("network used")):
                with self.assertRaisesRegex(MODULE.DoctrineResearchError, "no implemented adapter"):
                    MODULE.run_search(manual_args)

            disabled = request_payload(provider_access={"openalex": {"status": "disabled"}})
            disabled_path = root / "disabled-request.json"
            disabled_path.write_text(json.dumps(disabled, ensure_ascii=False), encoding="utf-8")
            disabled_args = argparse.Namespace(
                request=str(disabled_path),
                workspace=str(root / "disabled"),
                providers="openalex",
                max_queries=1,
                max_results=5,
                timeout=1.0,
                offline_fixtures=str(FIXTURES),
            )
            with patch.object(MODULE.urllib.request, "urlopen", side_effect=AssertionError("network used")):
                with self.assertRaisesRegex(MODULE.DoctrineResearchError, "not enabled"):
                    MODULE.run_search(disabled_args)

    def test_openalex_requires_runtime_key_for_network_route(self):
        registry = MODULE.load_json(MODULE.REGISTRY_PATH)
        with patch.dict(MODULE.os.environ, {}, clear=True):
            routing = MODULE.provider_routing(request_payload(), registry, ["openalex"])
            decision = next(row for row in routing["decisions"] if row["provider"] == "openalex")
            self.assertEqual("auth_required", decision["access_status"])
            self.assertFalse(decision["automated_run_eligible"])
            with self.assertRaisesRegex(MODULE.DoctrineResearchError, "OPENALEX_API_KEY"):
                MODULE.provider_url("openalex", "example", request_payload(), 3)

    def test_public_request_url_redacts_key_and_contact(self):
        value = MODULE.public_request_url(
            "https://api.example.test/works?search=norm&api_key=secret&mailto=user%40example.org"
        )
        self.assertIn("search=norm", value)
        self.assertNotIn("secret", value)
        self.assertNotIn("user%40example.org", value)
        self.assertEqual(2, value.count("%5Bredacted%5D"))

    def test_tls_context_never_disables_verification(self):
        context = MODULE.verified_ssl_context()
        self.assertEqual(MODULE.ssl.CERT_REQUIRED, context.verify_mode)
        self.assertTrue(context.check_hostname)

    def test_legal_topic_rerank_keeps_false_positive_below_direct_title(self):
        request = request_payload(
            disputed_elements=["индексация заработной платы"],
            mechanisms=["повышение оклада"],
        )
        direct = {"title": "Правовые проблемы индексации заработной платы", "abstract": "", "fulltext_url": None}
        noise = {"title": "Проблемы применения уголовной санкции", "abstract": "", "fulltext_url": None}
        taxonomy = MODULE.load_json(MODULE.TAXONOMY_PATH)
        MODULE.enrich_record(direct, request, taxonomy)
        MODULE.enrich_record(noise, request, taxonomy)
        self.assertEqual("high_lexical_priority", direct["relevance_status"])
        self.assertEqual("weak_candidate", noise["relevance_status"])
        self.assertGreater(direct["reading_priority"]["score"], noise["reading_priority"]["score"])

    def test_workspace_validation_rejects_premature_promotion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = request_payload()
            MODULE.prepare_workspace(request, root, ["openalex"])
            source = {
                "source_id": "src-test",
                "promotion_status": "page_verified",
                "verification_status": "page_verified",
            }
            MODULE.write_jsonl(root / "source-ledger.jsonl", [source])
            report = MODULE.validate_workspace(root)
            self.assertEqual("fail", report["status"])
            self.assertTrue(any("promoted" in error for error in report["errors"]))

    def test_case_search_requires_exact_human_approved_query_plan_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = request_payload(
                mode="case_scoped",
                judicial_meanings=["публичный судебный смысл"],
                application_evidence_refs=["evidence-1"],
            )
            request["norms"][0]["version_date"] = "2026-08-29"
            args = argparse.Namespace(
                request=str(write_request(root, request)),
                workspace=str(root / "run"),
                providers="crossref",
                max_queries=1,
                max_results=5,
                timeout=1.0,
                request_delay=0,
                offline_fixtures=str(FIXTURES),
                approved_query_plan_hash="wrong",
            )
            with self.assertRaisesRegex(MODULE.DoctrineResearchError, "manual query-plan review required"):
                MODULE.run_search(args)
            self.assertFalse((root / "run").exists())

    def test_uncertain_cross_provider_records_are_not_merged_without_identifier(self):
        records = [
            {
                "provider": "alpha",
                "provider_record_id": "a1",
                "title": "Одинаковое название",
                "authors": ["Один Автор"],
                "year": 2024,
            },
            {
                "provider": "beta",
                "provider_record_id": "b1",
                "title": "Одинаковое название",
                "authors": ["Один Автор"],
                "year": 2024,
            },
        ]
        self.assertEqual(2, len(MODULE.merge_candidates(records)))

    def test_unverified_fulltext_link_stays_in_acquisition_queue(self):
        records = [
            {
                "source_id": "src-1",
                "title": "Источник",
                "authors": ["Автор"],
                "doi": "10.1/example",
                "relevance_status": "high_lexical_priority",
                "reading_priority": {"score": 10},
                "fulltext_url": "https://example.invalid/file.pdf",
                "access_status": "fulltext_link_candidate",
            }
        ]
        queue = MODULE.acquisition_queue(records)
        self.assertEqual(1, len(queue["requests"]))
        self.assertFalse(queue["requests"][0]["payment_authorized"])

    def test_workspace_identity_blocks_cross_matter_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = request_payload(matter_id="matter-a")
            MODULE.prepare_workspace(first, root, ["crossref"])
            second = request_payload(matter_id="matter-b")
            with self.assertRaisesRegex(MODULE.DoctrineResearchError, "WORKSPACE_IDENTITY_MISMATCH"):
                MODULE.prepare_workspace(second, root, ["crossref"])

    def test_workspace_validation_detects_stale_provider_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = argparse.Namespace(
                request=str(write_request(root)),
                workspace=str(root / "run"),
                providers="crossref",
                max_queries=1,
                max_results=5,
                timeout=1.0,
                request_delay=0,
                offline_fixtures=str(FIXTURES),
            )
            self.assertEqual(0, MODULE.run_search(args))
            routing = MODULE.load_json(root / "run" / "provider-routing.json")
            for decision in routing["decisions"]:
                if decision["provider"] == "openalex":
                    decision["selected_for_automated_run"] = True
            MODULE.write_json(root / "run" / "provider-routing.json", routing)
            report = MODULE.validate_workspace(root / "run")
            self.assertEqual("fail", report["status"])
            self.assertTrue(any("provider set mismatch" in error for error in report["errors"]))

    def test_partial_provider_failure_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_root = root / "fixtures"
            (fixture_root / "openalex").mkdir(parents=True)
            shutil.copy(FIXTURES / "openalex" / "default.json", fixture_root / "openalex" / "default.json")
            args = argparse.Namespace(
                request=str(write_request(root)),
                workspace=str(root / "run"),
                providers="openalex,crossref",
                max_queries=1,
                max_results=5,
                timeout=1.0,
                request_delay=0,
                offline_fixtures=str(fixture_root),
            )
            with patch.object(MODULE.urllib.request, "urlopen", side_effect=AssertionError("network used")):
                exit_code = MODULE.run_search(args)
            self.assertEqual(4, exit_code)
            coverage = MODULE.load_json(root / "run" / "coverage-report.json")
            self.assertFalse(coverage["bounded_search_complete"])

    def test_provider_schema_errors_cannot_count_as_success(self):
        query = MODULE.build_query_plan(request_payload())["queries"][0]
        with self.assertRaisesRegex(MODULE.DoctrineResearchError, "Crossref response"):
            MODULE.normalize_provider_payload(
                "crossref",
                {"status": "error", "message": "temporarily unavailable"},
                query,
            )
        with self.assertRaisesRegex(MODULE.DoctrineResearchError, "OpenAlex response"):
            MODULE.normalize_provider_payload("openalex", {"results": []}, query)
        with self.assertRaisesRegex(MODULE.DoctrineResearchError, "OpenAlex response"):
            MODULE.normalize_provider_payload(
                "openalex",
                {"meta": {"count": 0}, "results": [], "error": "denied"},
                query,
            )
        with self.assertRaisesRegex(MODULE.DoctrineResearchError, "Crossref response"):
            MODULE.normalize_provider_payload(
                "crossref",
                {"status": "ok", "message": {"total-results": -1, "items": []}},
                query,
            )


if __name__ == "__main__":
    unittest.main()
