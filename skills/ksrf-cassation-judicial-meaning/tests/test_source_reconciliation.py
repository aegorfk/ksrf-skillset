import json
import unittest
from pathlib import Path

from judicial_meaning.source_reconciliation import (
    EnumeratorManifestError,
    PromotionGateError,
    promote_discovery,
    promote_enumerator,
    reconcile_sources,
    validate_enumerator_manifest,
)


def manifest(identifier, *, configured=True, applicable_from="2019-10-01", applicable_to=None):
    return {
        "enumerator_id": identifier,
        "version": "1.0",
        "source_role": "official",
        "institutional_regime": "ksoyu_post_2019" if configured else "regional_presidia_pre_2019",
        "applicable_from": applicable_from,
        "applicable_to": applicable_to,
        "courts": ["2kas"] if configured else ["moscow_city_presidium"],
        "enumeration_unit": "official_route_segment",
        "closure_rule": "all_declared_segments_terminal_success" if configured else None,
        "denominator_scope": "official_daily_scheduled_listing_not_all_acts",
        "adapter_id": f"{identifier}_v1" if configured else None,
        "configured": configured,
    }


def verification(identifier):
    return {
        "adapter_id": f"{identifier}_v1",
        "closure_rule": "all_declared_segments_terminal_success",
        "registry_verified": True,
        "applicability_verified": True,
        "identity_verified": True,
        "terminal_states_verified": True,
        "fixtures_passed": True,
        "resume_passed": True,
        "live_smoke_passed": True,
    }


def promoted_manifest(identifier):
    candidate = manifest(identifier, configured=False)
    candidate["institutional_regime"] = "ksoyu_post_2019"
    candidate["courts"] = ["2kas"]
    return promote_enumerator(
        candidate,
        verification=verification(identifier),
        reviewer="И.И. Иванов",
        reviewed_at="2026-08-26T00:00:00Z",
    )["manifest"]


def closed_coverage(identifier, *, total=1, status="success_empty"):
    return {
        "enumerator_id": identifier,
        "total_segments": total,
        "successful_segments": total,
        "statuses": {status: total},
        "terminal_snapshot_sha256": "a" * 64,
        "terminal_rule_verified": True,
        "pagination_complete": True,
        "resume_verified": True,
        "live_smoke_verified": True,
    }


class SourceReconciliationTests(unittest.TestCase):
    def test_manifest_requires_explicit_scope_and_adapter_for_configured_route(self):
        valid = validate_enumerator_manifest(manifest("daily"))
        self.assertEqual("daily", valid["enumerator_id"])

        missing_scope = manifest("search")
        missing_scope["denominator_scope"] = ""
        with self.assertRaises(EnumeratorManifestError):
            validate_enumerator_manifest(missing_scope)

        missing_adapter = manifest("search")
        missing_adapter["adapter_id"] = None
        with self.assertRaises(EnumeratorManifestError):
            validate_enumerator_manifest(missing_adapter)

    def test_reconciliation_reports_found_by_intersection_and_directional_gaps(self):
        result = reconcile_sources(
            manifests=[promoted_manifest("daily"), promoted_manifest("search")],
            observations=[
                {"enumerator_id": "daily", "chain_id": "chain-1", "document_id": "doc-1", "identity_status": "confirmed"},
                {"enumerator_id": "search", "chain_id": "chain-1", "document_id": "doc-1", "identity_status": "confirmed"},
                {"enumerator_id": "daily", "chain_id": "chain-2", "document_id": "doc-2", "identity_status": "confirmed"},
            ],
            route_coverage=[
                closed_coverage("daily", total=2, status="success_nonempty"),
                closed_coverage("search", status="success_nonempty"),
            ],
            requested_from="2024-01-01",
            requested_to="2024-12-31",
        )
        self.assertEqual(["daily", "search"], result["found_by"]["chain-1"])
        self.assertEqual(["chain-1"], result["intersection_chain_ids"])
        self.assertIn(
            {"chain_id": "chain-2", "missing_from": "search", "reason": "not_observed_in_route"},
            result["gaps"],
        )
        self.assertEqual(2, result["independent_chain_count"])

    def test_uncertain_identity_does_not_inflate_intersection(self):
        result = reconcile_sources(
            manifests=[promoted_manifest("daily"), promoted_manifest("search")],
            observations=[
                {"enumerator_id": "daily", "chain_id": "chain-1", "document_id": "doc-1", "identity_status": "confirmed"},
                {"enumerator_id": "search", "chain_id": "chain-1", "document_id": "doc-X", "identity_status": "needs_merge_split_review"},
            ],
            route_coverage=[],
            requested_from="2024-01-01",
            requested_to="2024-12-31",
        )
        self.assertEqual([], result["intersection_chain_ids"])
        self.assertEqual(1, len(result["unresolved_identity_observations"]))

    def test_coverage_remains_per_route_and_blocked_route_keeps_overall_open(self):
        blocked_search = closed_coverage("search", total=2, status="success_nonempty")
        blocked_search.update(
            {"successful_segments": 1, "statuses": {"success_nonempty": 1, "blocked": 1}}
        )
        result = reconcile_sources(
            manifests=[promoted_manifest("daily"), promoted_manifest("search")],
            observations=[],
            route_coverage=[
                closed_coverage("daily", total=2),
                blocked_search,
            ],
            requested_from="2024-01-01",
            requested_to="2024-12-31",
        )
        self.assertEqual("closed_declared_enumeration", result["route_coverage"]["daily"]["status"])
        self.assertEqual("observed_only", result["route_coverage"]["search"]["status"])
        self.assertIn(
            "segments_not_terminal_success",
            result["route_coverage"]["search"]["closure_blockers"],
        )
        self.assertEqual("observed_only", result["overall_status"])
        self.assertFalse(result["all_routes_closed"])

    def test_arbitrary_configured_manifest_and_success_counts_cannot_close_route(self):
        result = reconcile_sources(
            manifests=[manifest("unverified")],
            observations=[],
            route_coverage=[closed_coverage("unverified")],
            requested_from="2024-01-01",
            requested_to="2024-12-31",
        )
        route = result["route_coverage"]["unverified"]
        self.assertEqual("observed_only", route["status"])
        self.assertIn("enumerator_contract_not_promoted", route["closure_blockers"])
        self.assertFalse(result["all_routes_closed"])

    def test_promoted_route_needs_terminal_snapshot_and_all_runtime_proofs(self):
        incomplete = closed_coverage("daily")
        incomplete.pop("terminal_snapshot_sha256")
        incomplete["resume_verified"] = False
        result = reconcile_sources(
            manifests=[promoted_manifest("daily")],
            observations=[],
            route_coverage=[incomplete],
            requested_from="2024-01-01",
            requested_to="2024-12-31",
        )
        route = result["route_coverage"]["daily"]
        self.assertEqual("observed_only", route["status"])
        self.assertIn("terminal_snapshot_sha256_missing_or_invalid", route["closure_blockers"])
        self.assertIn("resume_not_verified", route["closure_blockers"])

    def test_promoted_route_with_terminal_evidence_may_close_declared_denominator(self):
        result = reconcile_sources(
            manifests=[promoted_manifest("daily")],
            observations=[],
            route_coverage=[closed_coverage("daily")],
            requested_from="2024-01-01",
            requested_to="2024-12-31",
        )
        self.assertEqual(
            "closed_declared_enumeration", result["route_coverage"]["daily"]["status"]
        )
        self.assertTrue(result["all_routes_closed"])

    def test_discovery_promotion_requires_official_snapshot_and_identity_review(self):
        candidate = {
            "candidate_id": "candidate-1",
            "source_role": "discovery_only",
            "url": "https://mirror.example.invalid/case-1",
        }
        with self.assertRaises(PromotionGateError):
            promote_discovery(
                candidate,
                official_snapshot_id=None,
                official_url=None,
                official_source_role=None,
                identity_status="confirmed",
                reviewer="И.И. Иванов",
            )
        with self.assertRaises(PromotionGateError):
            promote_discovery(
                candidate,
                official_snapshot_id="snapshot-sha256:" + "a" * 64,
                official_url="https://2kas.sudrf.ru/case-1",
                official_source_role="official",
                identity_status="needs_merge_split_review",
                reviewer="И.И. Иванов",
            )
        with self.assertRaises(PromotionGateError):
            promote_discovery(
                candidate,
                official_snapshot_id="snapshot-sha256:" + "a" * 64,
                official_url="https://mirror.example.invalid/case-1",
                official_source_role="discovery_only",
                identity_status="confirmed",
                reviewer="И.И. Иванов",
            )
        promoted = promote_discovery(
            candidate,
            official_snapshot_id="snapshot-sha256:" + "a" * 64,
            official_url="https://2kas.sudrf.ru/case-1",
            official_source_role="official",
            identity_status="confirmed",
            reviewer="И.И. Иванов",
            reviewed_at="2026-08-26T00:00:00Z",
        )
        self.assertEqual("official_verified", promoted["status"])
        self.assertEqual("candidate-1", promoted["candidate_id"])

    def test_enumerator_promotion_requires_every_operational_gate(self):
        candidate = manifest("secondary-search", configured=False)
        verification_record = verification("secondary-search")
        verification_record["adapter_id"] = "ksoyu_result_date_search_v1"
        verification_record["closure_rule"] = "all_observed_result_pages_terminal_success"
        incomplete = dict(verification_record)
        incomplete["resume_passed"] = False
        with self.assertRaises(PromotionGateError):
            promote_enumerator(
                candidate,
                verification=incomplete,
                reviewer="И.И. Иванов",
                reviewed_at="2026-08-26T00:00:00Z",
            )

        event = promote_enumerator(
            candidate,
            verification=verification_record,
            reviewer="И.И. Иванов",
            reviewed_at="2026-08-26T00:00:00Z",
        )
        self.assertEqual("official_enumerator_verified", event["status"])
        self.assertTrue(event["manifest"]["configured"])
        self.assertEqual("ksoyu_result_date_search_v1", event["manifest"]["adapter_id"])
        self.assertTrue(event["promotion_id"].startswith("enumerator-promotion-sha256:"))
        self.assertEqual(event["promotion_id"], event["manifest"]["promotion"]["promotion_id"])

        tampered = dict(event["manifest"])
        tampered["promotion"] = dict(tampered["promotion"])
        tampered["promotion"]["verification"] = dict(
            tampered["promotion"]["verification"], resume_passed=False
        )
        with self.assertRaises(EnumeratorManifestError):
            validate_enumerator_manifest(tampered)

    def test_historical_unconfigured_route_is_a_gap_not_an_empty_population(self):
        historical = manifest(
            "regional-presidia",
            configured=False,
            applicable_from="2016-01-01",
            applicable_to="2019-09-30",
        )
        result = reconcile_sources(
            manifests=[historical, promoted_manifest("daily")],
            observations=[],
            route_coverage=[closed_coverage("daily")],
            requested_from="2016-01-01",
            requested_to="2026-08-26",
        )
        self.assertIn(
            {
                "enumerator_id": "regional-presidia",
                "institutional_regime": "regional_presidia_pre_2019",
                "status": "not_configured",
                "applicable_from": "2016-01-01",
                "applicable_to": "2019-09-30",
            },
            result["historical_gaps"],
        )
        self.assertEqual("not_configured", result["route_coverage"]["regional-presidia"]["status"])
        self.assertEqual("observed_only", result["overall_status"])

    def test_reconciliation_digest_is_independent_of_manifest_input_order(self):
        kwargs = {
            "observations": [
                {"enumerator_id": "daily", "chain_id": "chain-1", "document_id": "doc-1", "identity_status": "confirmed"}
            ],
            "route_coverage": [
                closed_coverage("daily", status="success_nonempty"),
                closed_coverage("search"),
            ],
            "requested_from": "2024-01-01",
            "requested_to": "2024-12-31",
        }
        first = reconcile_sources(
            manifests=[promoted_manifest("daily"), promoted_manifest("search")], **kwargs
        )
        second = reconcile_sources(
            manifests=[promoted_manifest("search"), promoted_manifest("daily")], **kwargs
        )
        self.assertEqual(first["reconciliation_digest"], second["reconciliation_digest"])

    def test_contract_only_2kas_registry_route_is_explicitly_open(self):
        registry_path = (
            Path(__file__).resolve().parents[1] / "source_registry" / "sources.v1.json"
        )
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        route = next(
            source
            for source in registry["sources"]
            if source["id"] == "2kas_civil_result_date_search"
        )
        self.assertEqual("contract_only_not_wired", route["operational_status"])
        self.assertFalse(route["closed_for_declared_enumeration"])


if __name__ == "__main__":
    unittest.main()
