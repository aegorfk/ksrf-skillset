import argparse
import base64
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "doctrine_research.py"
FIXTURES = Path(__file__).parent / "fixtures"
SCHEMAS = Path(__file__).parents[1] / "references" / "schemas"
SPEC = importlib.util.spec_from_file_location("doctrine_research", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


ARTIFACT_SHA = MODULE.stable_hash({"legacy_untrusted_fixture": "artifact"})
RECEIPT_SHA = MODULE.stable_hash({"legacy_untrusted_fixture": "receipt"})
PORTFOLIO_SHA = MODULE.stable_hash({"legacy_untrusted_fixture": "portfolio"})


def selected_route_context():
    """Legacy self-issued declaration: useful only for rejection regressions."""
    return {
        "schema_version": "doctrine-route-context/1.0",
        "portfolio_id": "portfolio-generic-private-law",
        "portfolio_sha256": PORTFOLIO_SHA,
        "issue_option_id": "issue-option-generic-1",
        "selection_status": "selected",
        "selection_receipt": {
            "schema_version": "doctrine-lane-selection-receipt/1.0",
            "status": "selected",
            "portfolio_sha256": PORTFOLIO_SHA,
            "issue_option_id": "issue-option-generic-1",
            "receipt_sha256": RECEIPT_SHA,
        },
    }


def verified_reference(kind):
    """Legacy self-issued declaration: it must never produce readiness."""
    identity_key = "evidence_id" if kind == "application" else "source_id"
    provenance = "official_application_record" if kind == "application" else "lawful_fulltext_artifact"
    return {
        identity_key: f"{kind}-verified-1",
        "sha256": ARTIFACT_SHA,
        "provenance": provenance,
        "verification_receipt": {
            "schema_version": "artifact-verification-receipt/1.0",
            "status": "verified",
            "artifact_sha256": ARTIFACT_SHA,
            "receipt_sha256": RECEIPT_SHA,
        },
    }


def adverse_search_receipt(hypotheses):
    """Legacy self-issued declaration: it must never produce readiness."""
    return {
        "schema_version": "adverse-search-receipt/1.0",
        "status": "pass",
        "hypotheses_sha256": MODULE.stable_hash(hypotheses),
        "portfolio_sha256": PORTFOLIO_SHA,
        "receipt_sha256": RECEIPT_SHA,
    }


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


def attach_untrusted_but_well_shaped_lane_receipt(request):
    portfolio_bytes = b'{"portfolio":"generic-private-law","version":1}\n'
    portfolio_sha256 = MODULE.hashlib.sha256(portfolio_bytes).hexdigest()
    context = {
        "schema_version": "doctrine-route-context/1.1",
        "portfolio_id": "portfolio-generic-private-law",
        "portfolio_artifact": {
            "artifact_id": "portfolio-artifact-1",
            "sha256": portfolio_sha256,
            "size_bytes": len(portfolio_bytes),
        },
        "issue_option_id": "issue-option-generic-1",
        "trust_receipts": [],
    }
    request["doctrine_route_context"] = context
    claims = {
        "receipt_role": "lane_selection",
        "matter_id": request["matter_id"],
        "request_binding_sha256": MODULE.request_binding_sha256(request),
        "issue_option_id": context["issue_option_id"],
        "portfolio_id": context["portfolio_id"],
        "portfolio_sha256": portfolio_sha256,
        "portfolio_size_bytes": len(portfolio_bytes),
        "evidence_role": "selected_doctrine_lane",
        "artifact_id": context["portfolio_artifact"]["artifact_id"],
        "artifact_sha256": portfolio_sha256,
        "artifact_size_bytes": len(portfolio_bytes),
        "as_of_date": request["as_of_date"],
        "corpus_generation_id": None,
        "corpus_manifest_sha256": None,
        "coverage_report_sha256": None,
        "query_plan_sha256": None,
        "hypotheses_sha256": MODULE.stable_hash(request.get("hypotheses_under_test") or []),
        "freshness_policy_id": "candidate-fixture-policy",
        "revocation_registry_generation": "candidate-fixture-generation",
    }
    receipt = {
        "schema_version": "doctrine-trust-receipt/1.0",
        "receipt_id": "untrusted-candidate-receipt",
        "issuer_id": "untrusted-test-issuer",
        "key_id": "untrusted-test-key",
        "signature_algorithm": "ed25519",
        "issued_at": "2026-08-29T00:00:00Z",
        "expires_at": "2026-09-05T00:00:00Z",
        "signed_claims": claims,
        "signed_claims_sha256": MODULE.stable_hash(claims),
        "signature_base64": base64.b64encode(b"\x00" * 64).decode("ascii"),
    }
    context["trust_receipts"] = [receipt]
    return receipt


def prepare_search_plan(args):
    request = MODULE.load_json(Path(args.request))
    providers = [part for part in args.providers.split(",") if part]
    MODULE.prepare_workspace(request, Path(args.workspace), providers)


class DoctrineResearchTests(unittest.TestCase):
    def test_forged_self_issued_receipts_cannot_close_conditional_gate(self):
        case_request = request_payload(
            doctrine_route_context=selected_route_context(),
            mode="case_scoped",
            judicial_meanings=["публичная судебная формула"],
            application_evidence_refs=[verified_reference("application")],
        )
        case_request["norms"][0]["version_date"] = "2024-01-01"
        decision = MODULE.select_research_route(case_request)
        self.assertEqual("blocked", decision["status"])
        self.assertFalse(decision["promotion_eligible"])
        self.assertEqual("candidate_only_untrusted_declarations", decision["maximum_permitted_claim"])
        self.assertIn("protected_receipt_verifier_unavailable", decision["blockers"])
        with self.assertRaisesRegex(MODULE.DoctrineResearchError, "protected receipt verifier"):
            MODULE.build_query_plan(case_request)

        hypotheses = ["Поддельная adverse-квитанция не является доказательством"]
        verification_request = request_payload(
            doctrine_route_context=selected_route_context(),
            mode="hypothesis_verification",
            hypotheses_under_test=hypotheses,
            fulltext_source_refs=[verified_reference("fulltext")],
            adverse_search_required=True,
            adverse_search_status="pass",
            adverse_search_receipt=adverse_search_receipt(hypotheses),
        )
        verification = MODULE.select_research_route(verification_request)
        self.assertEqual("blocked", verification["status"])
        self.assertFalse(verification["promotion_eligible"])
        self.assertIn("protected_receipt_verifier_unavailable", verification["blockers"])
        with self.assertRaisesRegex(MODULE.DoctrineResearchError, "protected receipt verifier"):
            MODULE.build_query_plan(verification_request)

    def test_receipt_replay_across_matter_and_issue_never_becomes_ready(self):
        original = request_payload()
        receipt = attach_untrusted_but_well_shaped_lane_receipt(original)
        original_decision = MODULE.select_research_route(original)
        self.assertEqual("blocked", original_decision["status"])
        self.assertNotIn("route_context_invalid", original_decision["blockers"])
        self.assertEqual(
            [MODULE.stable_hash(receipt)],
            original_decision["receipt_canonical_sha256s"],
        )
        self.assertEqual(
            ["protected_receipt_verifier_unavailable"],
            original_decision["blockers"],
        )

        replayed_matter = json.loads(json.dumps(original))
        replayed_matter["matter_id"] = "different-matter"
        replayed_issue = json.loads(json.dumps(original))
        replayed_issue["doctrine_route_context"]["issue_option_id"] = "different-issue"

        for request in (replayed_matter, replayed_issue):
            with self.subTest(matter=request["matter_id"], issue=request["doctrine_route_context"]["issue_option_id"]):
                decision = MODULE.select_research_route(request)
                self.assertEqual("blocked", decision["status"])
                self.assertFalse(decision["promotion_eligible"])
                self.assertIn("route_context_invalid", decision["blockers"])

    def test_standalone_exploratory_v1_plans_without_portfolio_context(self):
        request = request_payload(doctrine_route_context=None)
        self.assertEqual([], MODULE.validate_request(request))
        decision = MODULE.select_research_route(request)
        self.assertEqual("not_routed", decision["status"])
        self.assertFalse(decision["promotion_eligible"])
        self.assertEqual("standalone_exploratory_discovery_only", decision["maximum_permitted_claim"])

        plan = MODULE.build_query_plan(request)
        self.assertGreater(plan["query_count"], 0)
        self.assertFalse(plan["promotion_eligible"])
        self.assertEqual("standalone_exploratory_discovery_only", plan["maximum_permitted_claim"])

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            request_path = write_request(root, request)
            self.assertEqual(
                0,
                MODULE.run_plan(
                    argparse.Namespace(
                        request=str(request_path),
                        workspace=str(root / "run"),
                        providers="",
                    )
                ),
            )

    def test_versioned_route_and_receipt_schemas_are_machine_readable(self):
        route_schema = json.loads(
            (SCHEMAS / "doctrine-route-1.1.schema.json").read_text(encoding="utf-8")
        )
        receipt_schema = json.loads(
            (SCHEMAS / "doctrine-trust-receipt-1.0.schema.json").read_text(encoding="utf-8")
        )
        verifier_schema = json.loads(
            (SCHEMAS / "doctrine-verifier-attestation-1.0.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual("doctrine-route/1.1", route_schema["properties"]["schema_version"]["const"])
        self.assertIn("signed_claims", receipt_schema["required"])
        self.assertIn("receipt_canonical_sha256", verifier_schema["required"])

    def test_route_rejects_truthy_unverified_and_malformed_inputs(self):
        router = MODULE.select_research_route

        unverified_case = request_payload(
            doctrine_route_context=selected_route_context(),
            judicial_meanings=["публичная судебная формула"],
            application_evidence_refs=["sha256:looks-real-but-has-no-receipt"],
        )
        unverified_case["norms"][0]["version_date"] = "2024-01-01"
        try:
            case_decision = router(unverified_case)
        except TypeError:
            case_decision = router(unverified_case, doctrine_lane_selected=True)
        self.assertEqual("exploratory_norm", case_decision["mode"])
        self.assertIn(
            "application_evidence_refs_invalid_or_unverified",
            case_decision["scope_limits"],
        )

        hypotheses = ["Проверяемая гипотеза"]
        unverified_hypothesis = request_payload(
            doctrine_route_context=selected_route_context(),
            mode="hypothesis_verification",
            hypotheses_under_test=hypotheses,
            fulltext_source_refs=["does-not-exist"],
            adverse_search_required=True,
        )
        try:
            hypothesis_decision = router(unverified_hypothesis)
        except TypeError:
            hypothesis_decision = router(unverified_hypothesis, doctrine_lane_selected=True)
        self.assertEqual("hypothesis_verification", hypothesis_decision["mode"])
        self.assertEqual("blocked", hypothesis_decision["status"])
        self.assertIn("fulltext_source_refs_invalid_or_unverified", hypothesis_decision["blockers"])
        self.assertIn("adverse_search_not_passed_or_unbound", hypothesis_decision["blockers"])

        malformed = request_payload(
            doctrine_route_context=selected_route_context(),
            judicial_meanings="truthy but not a list",
        )
        try:
            malformed_decision = router(malformed)
        except TypeError:
            malformed_decision = router(malformed, doctrine_lane_selected=True)
        self.assertEqual("blocked", malformed_decision["status"])
        self.assertIn("request_schema_invalid", malformed_decision["blockers"])

    def test_declared_exploratory_mode_cannot_bypass_hypothesis_route(self):
        bypass = request_payload(
            doctrine_route_context=selected_route_context(),
            mode="exploratory_norm",
            hypotheses_under_test=["Гипотеза, требующая проверки"],
            fulltext_source_refs=[],
            adverse_search_required=False,
        )
        self.assertTrue(MODULE.validate_request(bypass, for_external_search=True))
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(MODULE.DoctrineResearchError):
                MODULE.run_plan(
                    argparse.Namespace(
                        request=str(write_request(Path(raw), bypass)),
                        workspace=str(Path(raw) / "run"),
                        providers="",
                    )
                )

    def test_route_artifact_is_hash_bound_and_required_by_search(self):
        request = request_payload()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            request_path = write_request(root, request)
            workspace = root / "run"
            self.assertEqual(
                0,
                MODULE.run_plan(
                    argparse.Namespace(
                        request=str(request_path),
                        workspace=str(workspace),
                        providers="crossref",
                    )
                ),
            )
            route_path = workspace / "route-decision.json"
            self.assertTrue(route_path.is_file())
            route = json.loads(route_path.read_text(encoding="utf-8"))
            self.assertEqual(request["matter_id"], route["matter_id"])
            self.assertIsNone(route["issue_option_id"])
            self.assertIsNone(route["portfolio_sha256"])
            self.assertEqual(MODULE.stable_hash(request), route["request_sha256"])
            self.assertRegex(route["route_decision_hash"], r"^[0-9a-f]{64}$")
            self.assertFalse(route["promotion_eligible"])
            self.assertEqual("standalone_exploratory_discovery_only", route["maximum_permitted_claim"])

            route["mode"] = "case_scoped"
            route_path.write_text(json.dumps(route), encoding="utf-8")
            args = argparse.Namespace(
                request=str(request_path),
                workspace=str(workspace),
                providers="crossref",
                max_queries=1,
                max_results=1,
                timeout=1.0,
                request_delay=0,
                offline_fixtures=str(FIXTURES),
                approved_query_plan_hash=None,
            )
            with self.assertRaises(MODULE.DoctrineResearchError):
                MODULE.run_search(args)

    def test_blocked_route_cli_returns_nonzero_json(self):
        blocked = request_payload(
            doctrine_route_context=selected_route_context(),
            mode="hypothesis_verification",
            hypotheses_under_test=["Гипотеза без проверенного корпуса"],
            fulltext_source_refs=["does-not-exist"],
            adverse_search_required=True,
        )
        with tempfile.TemporaryDirectory() as raw:
            request_path = write_request(Path(raw), blocked)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = MODULE.main(["route", "--request", str(request_path)])
        self.assertEqual(2, exit_code)
        payload = json.loads(stdout.getvalue())
        self.assertEqual("blocked", payload["status"])

    def test_conditional_route_selects_safest_research_mode(self):
        router = getattr(MODULE, "select_research_route", None)
        self.assertTrue(callable(router), "conditional doctrine router is missing")

        not_selected = router(request_payload(doctrine_route_context=None))
        self.assertFalse(not_selected["routed"])
        self.assertEqual("not_routed", not_selected["status"])
        self.assertRegex(not_selected["request_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(not_selected["route_decision_hash"], r"^[0-9a-f]{64}$")

        exploratory = router(
            request_payload(doctrine_route_context=selected_route_context())
        )
        self.assertEqual("exploratory_norm", exploratory["mode"])
        self.assertEqual("blocked", exploratory["status"])
        self.assertFalse(exploratory["promotion_eligible"])
        self.assertIn("protected_receipt_verifier_unavailable", exploratory["blockers"])
        self.assertIn("judicial_meanings_missing", exploratory["scope_limits"])
        self.assertIn("application_evidence_refs_missing", exploratory["scope_limits"])
        self.assertIn("norm_version_dates_missing", exploratory["scope_limits"])

        case_request = request_payload(
            doctrine_route_context=selected_route_context(),
            mode="case_scoped",
            judicial_meanings=["публичная судебная формула"],
            application_evidence_refs=[verified_reference("application")],
        )
        case_request["norms"][0]["version_date"] = "2024-01-01"
        case_scoped = router(case_request)
        self.assertEqual("exploratory_norm", case_scoped["mode"])
        self.assertEqual("blocked", case_scoped["status"])
        self.assertIn("protected_receipt_verifier_unavailable", case_scoped["blockers"])
        self.assertIn("application_evidence_refs_invalid_or_unverified", case_scoped["scope_limits"])

        verification_request = request_payload(
            doctrine_route_context=selected_route_context(),
            hypotheses_under_test=["Устранит ли adverse-позиция исходную гипотезу?"],
        )
        blocked_verification = router(verification_request)
        self.assertEqual("hypothesis_verification", blocked_verification["mode"])
        self.assertEqual("blocked", blocked_verification["status"])
        self.assertIn("request_schema_invalid", blocked_verification["blockers"])
        self.assertIn("fulltext_source_refs_invalid_or_unverified", blocked_verification["blockers"])
        self.assertIn("adverse_search_not_passed_or_unbound", blocked_verification["blockers"])
        self.assertIn("protected_receipt_verifier_unavailable", blocked_verification["blockers"])

        verification_request.update(
            fulltext_source_refs=[verified_reference("fulltext")],
            adverse_search_required=True,
            adverse_search_status="pass",
            adverse_search_receipt=adverse_search_receipt(
                verification_request["hypotheses_under_test"]
            ),
        )
        still_blocked = router(verification_request)
        self.assertEqual("hypothesis_verification", still_blocked["mode"])
        self.assertEqual("blocked", still_blocked["status"])
        self.assertFalse(still_blocked["promotion_eligible"])
        self.assertIn("protected_receipt_verifier_unavailable", still_blocked["blockers"])

    def test_route_command_exposes_conditional_decision_before_search(self):
        with tempfile.TemporaryDirectory() as raw:
            request_path = write_request(Path(raw))
            stdout = io.StringIO()
            try:
                with redirect_stdout(stdout):
                    exit_code = MODULE.main(
                        ["route", "--request", str(request_path)]
                    )
            except SystemExit as exc:
                exit_code = int(exc.code)

        self.assertEqual(0, exit_code)
        payload = json.loads(stdout.getvalue())
        self.assertIsNone(payload["mode"])
        self.assertEqual("not_routed", payload["status"])
        self.assertEqual("standalone_exploratory_discovery_only", payload["maximum_permitted_claim"])

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
            prepare_search_plan(args)
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
            prepare_search_plan(args)
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
        self.assertTrue(any("trust-receipted reference object" in error for error in errors))

        verification = request_payload(
            mode="hypothesis_verification",
            hypotheses_under_test=[""],
            fulltext_source_refs=[""],
            adverse_search_required=True,
        )
        errors = MODULE.validate_request(verification)
        self.assertTrue(any("non-empty hypotheses_under_test" in error for error in errors))
        self.assertTrue(any("trust-receipted reference object" in error for error in errors))

    def test_hypothesis_verification_cannot_plan_without_protected_verifier(self):
        hypotheses = ["Норма оставляет чрезмерное усмотрение"]
        request = request_payload(
            doctrine_route_context=selected_route_context(),
            mode="hypothesis_verification",
            disputed_elements=[],
            hypotheses_under_test=hypotheses,
            fulltext_source_refs=[verified_reference("fulltext")],
            adverse_search_required=True,
            adverse_search_status="pass",
            adverse_search_receipt=adverse_search_receipt(hypotheses),
        )
        decision = MODULE.select_research_route(request)
        self.assertEqual("hypothesis_verification", decision["mode"])
        self.assertEqual("blocked", decision["status"])
        self.assertIn("protected_receipt_verifier_unavailable", decision["blockers"])
        with self.assertRaisesRegex(MODULE.DoctrineResearchError, "protected receipt verifier"):
            MODULE.build_query_plan(request)

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

    def test_redaction_gate_blocks_unicode_format_controls_without_mutating_query(self):
        for value in (
            "Ива\u200bнов Иван Иванович",
            "expert\u200b@example.org",
            "+7 999\u200b 123 45 67",
            "нейтральный\u00ad термин",
            "нейтральный\u200d термин",
            "нейтральный\u2060 термин",
            "нейтральный\u202e термин",
            "нейтральный\u2066 термин",
            "нейтральный\ufeff термин",
        ):
            with self.subTest(value=value):
                request = request_payload(subject_terms=[value])
                plan = MODULE.build_query_plan(request)
                original_plan = MODULE.canonical_bytes(plan)

                violations = MODULE.redaction_violations(plan, request)

                self.assertTrue(any(value in query["text"] for query in plan["queries"]))
                self.assertIn("unicode_format_control", {row["reason"] for row in violations})
                self.assertEqual(original_plan, MODULE.canonical_bytes(plan))

    def test_redaction_gate_matches_prohibited_term_split_by_format_control(self):
        protected_term = "СекретнаяФамилия"
        obfuscated_term = "Секретная\u200bФамилия"
        request = request_payload(
            subject_terms=[obfuscated_term],
            privacy={
                "class": "public_abstracted",
                "external_queries_redacted": True,
                "prohibited_external_terms": [protected_term],
            },
        )
        plan = MODULE.build_query_plan(request)
        original_plan = MODULE.canonical_bytes(plan)

        violations = MODULE.redaction_violations(plan, request)

        self.assertIn("prohibited_external_term", {row["reason"] for row in violations})
        self.assertEqual(original_plan, MODULE.canonical_bytes(plan))

    def test_redaction_gate_normalizes_unicode_compatibility_forms_for_inspection(self):
        fullwidth_email = "ｅｘｐｅｒｔ＠ｅｘａｍｐｌｅ．ｏｒｇ"
        request = request_payload(subject_terms=[fullwidth_email])
        plan = MODULE.build_query_plan(request)
        original_plan = MODULE.canonical_bytes(plan)

        violations = MODULE.redaction_violations(plan, request)

        self.assertIn("pii_like_pattern", {row["reason"] for row in violations})
        self.assertEqual(original_plan, MODULE.canonical_bytes(plan))

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
            prepare_search_plan(manual_args)
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
            prepare_search_plan(disabled_args)
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

    def test_conditional_case_search_is_blocked_before_plan_without_verifier(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = request_payload(
                doctrine_route_context=selected_route_context(),
                mode="case_scoped",
                judicial_meanings=["публичный судебный смысл"],
                application_evidence_refs=[verified_reference("application")],
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
            with self.assertRaisesRegex(MODULE.DoctrineResearchError, "protected receipt verifier"):
                prepare_search_plan(args)
            self.assertFalse((root / "run" / "search-run-config.json").exists())

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
            prepare_search_plan(args)
            self.assertEqual(0, MODULE.run_search(args))
            routing = MODULE.load_json(root / "run" / "provider-routing.json")
            for decision in routing["decisions"]:
                if decision["provider"] == "openalex":
                    decision["selected_for_automated_run"] = True
            MODULE.write_json(root / "run" / "provider-routing.json", routing)
            report = MODULE.validate_workspace(root / "run")
            self.assertEqual("fail", report["status"])
            self.assertTrue(any("provider set mismatch" in error for error in report["errors"]))

    def test_workspace_validation_rejects_tampered_query_plan_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            query_plan = MODULE.load_json(workspace / "query-plan.json")
            query_plan["queries"][0]["text"] += " tampered"
            MODULE.write_json(workspace / "query-plan.json", query_plan)

            report = MODULE.validate_workspace(workspace)

            self.assertEqual("fail", report["status"])
            self.assertTrue(any("query plan artifact/hash mismatch" in error for error in report["errors"]))

    def test_workspace_validation_rejects_non_scalar_query_id_without_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            query_plan = MODULE.load_json(workspace / "query-plan.json")
            query_plan["queries"][0]["query_id"] = ["not", "scalar"]
            MODULE.write_json(workspace / "query-plan.json", query_plan)

            report = MODULE.validate_workspace(workspace)

            self.assertEqual("fail", report["status"])
            self.assertTrue(any("query_id must be" in error for error in report["errors"]))

    def test_workspace_validation_reports_malformed_search_json_without_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            (workspace / "coverage-report.json").write_text("{not-json", encoding="utf-8")

            report = MODULE.validate_workspace(workspace)

            self.assertEqual("fail", report["status"])
            self.assertTrue(
                any("invalid JSON artifact: coverage-report.json" in error for error in report["errors"])
            )

            exit_code = MODULE.run_validate(argparse.Namespace(workspace=str(workspace)))
            self.assertEqual(2, exit_code)
            persisted = MODULE.load_json(workspace / "qa-report.json")
            self.assertEqual("fail", persisted["status"])

    def test_workspace_validation_rejects_unsupported_json_scalars_without_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            snapshot = MODULE.load_json(workspace / "request.snapshot.json")
            snapshot["problem_statement"] = "\ud800"
            (workspace / "request.snapshot.json").write_text(
                json.dumps(snapshot, ensure_ascii=True), encoding="utf-8"
            )

            report = MODULE.validate_workspace(workspace)

            self.assertEqual("fail", report["status"])
            self.assertTrue(
                any("invalid JSON artifact: request.snapshot.json" in error for error in report["errors"])
            )

    def test_workspace_validation_rejects_non_finite_json_numbers_without_crashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            (workspace / "coverage-report.json").write_text(
                '{"coverage_complete": 1e9999}', encoding="utf-8"
            )

            report = MODULE.validate_workspace(workspace)

            self.assertEqual("fail", report["status"])
            self.assertTrue(
                any("invalid JSON artifact: coverage-report.json" in error for error in report["errors"])
            )

    def test_workspace_validation_escapes_unencodable_diagnostic_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            (workspace / "source-ledger.jsonl").write_text(
                '{"source_id":"\\ud800","promotion_status":"candidate_only",'
                '"verification_status":"unexpected"}\n',
                encoding="utf-8",
            )

            exit_code = MODULE.run_validate(argparse.Namespace(workspace=str(workspace)))

            self.assertEqual(2, exit_code)
            report = MODULE.load_json(workspace / "qa-report.json")
            self.assertEqual("fail", report["status"])
            self.assertFalse(
                any(
                    0xD800 <= ord(character) <= 0xDFFF
                    for error in report["errors"]
                    for character in error
                )
            )

    def test_workspace_validation_rejects_ill_typed_search_artifacts_without_crashing(self):
        cases = (
            ("problem-candidates.json", "[]", "problem-candidates.json must be an object"),
            ("coverage-report.json", "[]", "coverage-report.json must be an object"),
            ("acquisition-queue.json", "[]", "acquisition-queue.json must be an object"),
            ("provider-routing.json", '{"decisions": "bad"}', "provider-routing.json decisions must be a list of objects"),
            ("search-log.jsonl", "[]\n", "invalid JSONL artifact: search-log.jsonl"),
        )
        for filename, payload, expected_error in cases:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temporary:
                workspace = Path(temporary)
                MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
                (workspace / filename).write_text(payload, encoding="utf-8")

                report = MODULE.validate_workspace(workspace)

                self.assertEqual("fail", report["status"])
                self.assertTrue(any(expected_error in error for error in report["errors"]))

    def test_search_rejects_malformed_bound_artifact_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = write_request(root)
            workspace = root / "run"
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            MODULE.write_json(workspace / "qa-report.json", {"status": "pass"})
            (workspace / "query-plan.json").write_text("{not-json", encoding="utf-8")

            exit_code = MODULE.main(
                [
                    "search",
                    "--request",
                    str(request_path),
                    "--workspace",
                    str(workspace),
                    "--providers",
                    "crossref",
                    "--max-queries",
                    "1",
                    "--max-results",
                    "5",
                    "--offline-fixtures",
                    str(FIXTURES),
                ]
            )

            self.assertEqual(2, exit_code)
            self.assertEqual("fail", MODULE.load_json(workspace / "qa-report.json")["status"])

    def test_rerank_rejects_ill_typed_coverage_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = write_request(root)
            workspace = root / "run"
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            MODULE.write_jsonl(workspace / "source-ledger.jsonl", [])
            MODULE.write_json(workspace / "coverage-report.json", [])
            MODULE.write_json(workspace / "qa-report.json", {"status": "pass"})

            exit_code = MODULE.main(
                [
                    "rerank",
                    "--request",
                    str(request_path),
                    "--workspace",
                    str(workspace),
                ]
            )

            self.assertEqual(2, exit_code)
            self.assertEqual("fail", MODULE.load_json(workspace / "qa-report.json")["status"])

    def test_rerank_rejects_ill_typed_source_id_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = write_request(root)
            workspace = root / "run"
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            MODULE.write_jsonl(
                workspace / "source-ledger.jsonl",
                [{"source_id": ["not", "a", "string"]}],
            )

            exit_code = MODULE.main(
                [
                    "rerank",
                    "--request",
                    str(request_path),
                    "--workspace",
                    str(workspace),
                ]
            )

            self.assertEqual(2, exit_code)

    def test_rerank_rejects_malformed_snapshot_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = write_request(root)
            workspace = root / "run"
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            MODULE.write_jsonl(workspace / "source-ledger.jsonl", [])
            MODULE.write_json(workspace / "qa-report.json", {"status": "pass"})
            (workspace / "request.snapshot.json").write_text("{not-json", encoding="utf-8")

            exit_code = MODULE.main(
                [
                    "rerank",
                    "--request",
                    str(request_path),
                    "--workspace",
                    str(workspace),
                ]
            )

            self.assertEqual(2, exit_code)
            self.assertEqual("fail", MODULE.load_json(workspace / "qa-report.json")["status"])

    def test_workspace_validation_rejects_incomplete_search_artifact_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = argparse.Namespace(
                request=str(write_request(root)),
                workspace=str(root / "complete-run"),
                providers="openalex,crossref",
                max_queries=1,
                max_results=5,
                timeout=1.0,
                request_delay=0,
                offline_fixtures=str(FIXTURES),
            )
            prepare_search_plan(args)
            self.assertEqual("pass", MODULE.validate_workspace(Path(args.workspace))["status"])
            with patch.object(MODULE.urllib.request, "urlopen", side_effect=AssertionError("network used")):
                self.assertEqual(0, MODULE.run_search(args))
            complete_run = Path(args.workspace)
            self.assertEqual("pass", MODULE.validate_workspace(complete_run)["status"])

            for missing in (
                "coverage-report.json",
                "search-run-config.json",
                "search-log.jsonl",
                "source-ledger.jsonl",
                "problem-candidates.json",
                "acquisition-queue.json",
            ):
                with self.subTest(missing=missing):
                    altered = root / f"missing-{missing}"
                    shutil.copytree(complete_run, altered)
                    (altered / missing).unlink()

                    report = MODULE.validate_workspace(altered)

                    self.assertEqual("fail", report["status"])
                    self.assertTrue(
                        any("incomplete search artifact set" in error for error in report["errors"])
                    )

    def test_manual_source_rerank_without_search_markers_remains_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = write_request(root)
            workspace = root / "manual-source"
            MODULE.prepare_workspace(request_payload(), workspace, ["crossref"])
            MODULE.write_jsonl(workspace / "source-ledger.jsonl", [])

            exit_code = MODULE.run_rerank(
                argparse.Namespace(request=str(request_path), workspace=str(workspace))
            )

            self.assertEqual(0, exit_code)
            self.assertEqual("pass", MODULE.validate_workspace(workspace)["status"])
            for marker in ("search-run-config.json", "search-log.jsonl", "coverage-report.json"):
                self.assertFalse((workspace / marker).exists())

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
            prepare_search_plan(args)
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
