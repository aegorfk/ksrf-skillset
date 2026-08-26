from __future__ import annotations

import json
import unittest
from pathlib import Path


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "source_registry" / "sources.v1.json"


class SecondaryRouteRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.sources = {source["id"]: source for source in registry["sources"]}

    def test_second_ksoyu_result_search_has_a_bounded_manifest(self) -> None:
        source = self.sources["2kas_civil_result_date_search"]
        self.assertEqual(source["role"], "official_secondary")
        self.assertIsNone(source["adapter"])
        self.assertEqual(source["enumerator_contract"], "2kas_civil_result_date_search_v1")
        self.assertEqual(source["operational_status"], "contract_only_not_wired")
        self.assertEqual(source["parser_version"], "1.0")
        self.assertEqual(source["institutional_regime"], "ksoyu_post_2019")
        self.assertEqual(source["applicable_from"], "2019-10-01")
        self.assertIsNone(source["applicable_to"])
        self.assertEqual(source["courts"], [{"code": "2kas", "host": "2kas.sudrf.ru"}])
        self.assertEqual(source["case_scope"]["jurisdiction"], "civil_cassation")
        self.assertEqual(source["case_scope"]["delo_table"], "g33_case")
        self.assertEqual(source["case_scope"]["case_type"], "0")
        self.assertEqual(source["case_scope"]["delo_id"], "2800001")
        self.assertEqual(source["date_basis"], "result_date")
        self.assertEqual(source["coverage_claim"], "bounded_declared_search_results")
        self.assertEqual(source["enumeration_unit"], "official_result_date_search_page")
        self.assertEqual(
            source["closure_rule"],
            "all_observed_pagination_pages_terminal_success_or_exact_zero_marker",
        )
        self.assertEqual(
            source["denominator_scope"],
            "2kas_civil_cassation_official_search_results_by_result_date_not_all_court_output",
        )

    def test_manifest_never_upgrades_search_results_to_all_court_output(self) -> None:
        source = self.sources["2kas_civil_result_date_search"]
        self.assertTrue(source["official_page_publication_limited"])
        self.assertIn("не все", source["publication_limit_notice_ru"].casefold())
        self.assertEqual(source["official_page_notice_url"], source["official_search_url"])
        self.assertEqual(source["route_verified_at"], "2026-08-26")
        self.assertFalse(source["closed_for_declared_enumeration"])
        self.assertEqual("contract_only_not_wired", source["operational_status"])
        for broader_claim in (
            "closed_for_official_output",
            "closed_for_all_decided_cases",
            "closed_for_all_published_acts",
            "closed_for_all_court_case_types",
        ):
            with self.subTest(claim=broader_claim):
                self.assertIs(source[broader_claim], False)

    def test_pre_2019_regional_presidia_remain_not_configured(self) -> None:
        source = self.sources["regional_presidia_pre_2019"]
        self.assertEqual(source["enumeration"], "not_configured")
        self.assertIsNone(source["adapter"])
        self.assertFalse(source["closed_for_official_output"])


if __name__ == "__main__":
    unittest.main()
