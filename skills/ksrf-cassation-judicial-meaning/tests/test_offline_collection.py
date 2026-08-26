import json
import tempfile
import unittest
from pathlib import Path

from judicial_meaning.collection import HttpResponse, load_source_registry, run_collection
from judicial_meaning.ksoyu import build_listing_url


FIXTURES = Path(__file__).parent / "fixtures"


def frozen_plan():
    return {
        "schema_version": "1.0",
        "frozen": True,
        "plan_sha256": "a" * 64,
        "population": {
            "unit": "independent_case_chain",
            "date_from": "2024-03-07",
            "date_to": "2024-03-07",
            "courts": ["1kas"],
            "regimes": ["ksoyu_post_2019"],
        },
    }


class MappingTransport:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if url not in self.mapping:
            raise TimeoutError(f"unexpected URL {url}")
        status, fixture = self.mapping[url]
        return HttpResponse(
            status=status,
            final_url=url,
            headers={"content-type": "text/html; charset=utf-8"},
            body=(FIXTURES / fixture).read_bytes(),
        )


class OfflineCollectionTests(unittest.TestCase):
    def test_bundled_registry_is_loaded_relative_to_skill(self):
        registry = load_source_registry()
        sources = {source["id"]: source for source in registry["sources"]}
        self.assertEqual(9, len(sources["ksoyu_post_2019"]["courts"]))
        self.assertEqual("ksoyu_daily_v2", sources["ksoyu_post_2019"]["adapter"])
        self.assertIsNone(sources["regional_presidia_pre_2019"]["adapter"])

    def test_real_empty_day_closes_without_source_tasks_and_exports_evidence(self):
        root = build_listing_url("1kas.sudrf.ru", "2024-03-07")
        transport = MappingTransport({root: (200, "listing_empty_sudrf.html")})
        with tempfile.TemporaryDirectory() as tmp:
            result = run_collection(Path(tmp), plan=frozen_plan(), transport=transport, resume=False)
            self.assertEqual(1, result["coverage"]["success_empty"])
            self.assertEqual(0, result["source_acquisition"]["total"])
            self.assertTrue(result["coverage"]["collection_complete"])
            self.assertTrue(result["coverage"]["closed_declared_enumeration_observed"])
            self.assertEqual(
                "closed_declared_enumeration_observed",
                result["coverage"]["declared_enumeration_status"],
            )
            self.assertEqual(
                "official_daily_scheduled_listing_route_not_all_decided_or_published_acts",
                result["coverage"]["denominator_scope"],
            )
            sources = [
                json.loads(line)
                for line in (Path(tmp) / "exports" / "sources.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            listing = next(source for source in sources if source["kind"] == "listing")
            metadata = json.loads(listing["metadata_json"])
            self.assertEqual("ksoyu_daily_v2", metadata["adapter_id"])
            self.assertEqual("ksoyu_daily_v2", metadata["adapter_version"])
            self.assertEqual("2.0", metadata["parser_version"])
            self.assertEqual("dated_no_scheduled_cases", metadata["empty_evidence_code"])
            self.assertTrue(metadata["date_confirmed"])

    def test_resume_rejects_adapter_change_before_fetching(self):
        root = build_listing_url("1kas.sudrf.ru", "2024-03-07")
        with tempfile.TemporaryDirectory() as tmp:
            first_transport = MappingTransport({root: (200, "listing_empty_sudrf.html")})
            run_collection(Path(tmp), plan=frozen_plan(), transport=first_transport, resume=False)
            run_path = Path(tmp) / "run.json"
            run_metadata = json.loads(run_path.read_text(encoding="utf-8"))
            run_metadata["adapter_ids"]["ksoyu_post_2019"] = "ksoyu_daily_v1"
            run_path.write_text(json.dumps(run_metadata), encoding="utf-8")
            second_transport = MappingTransport({})
            with self.assertRaisesRegex(ValueError, "adapter"):
                run_collection(Path(tmp), plan=frozen_plan(), transport=second_transport, resume=True)
            self.assertEqual([], second_transport.calls)

    def test_resume_rejects_tampered_run_identity_before_fetching(self):
        root = build_listing_url("1kas.sudrf.ru", "2024-03-07")
        for field, replacement in (("run_id", "run-tampered"), ("plan_sha256", "0" * 64)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                run_collection(
                    Path(tmp),
                    plan=frozen_plan(),
                    transport=MappingTransport({root: (200, "listing_empty_sudrf.html")}),
                    resume=False,
                )
                run_path = Path(tmp) / "run.json"
                run_metadata = json.loads(run_path.read_text(encoding="utf-8"))
                run_metadata[field] = replacement
                run_path.write_text(json.dumps(run_metadata), encoding="utf-8")
                transport = MappingTransport({})
                with self.assertRaisesRegex(ValueError, "run_id|plan_sha256"):
                    run_collection(Path(tmp), plan=frozen_plan(), transport=transport, resume=True)
                self.assertEqual([], transport.calls)

    def test_resume_rejects_parser_or_registry_manifest_change(self):
        root = build_listing_url("1kas.sudrf.ru", "2024-03-07")
        for field in ("parser_version", "registry_version"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                run_collection(
                    Path(tmp),
                    plan=frozen_plan(),
                    transport=MappingTransport({root: (200, "listing_empty_sudrf.html")}),
                    resume=False,
                )
                run_path = Path(tmp) / "run.json"
                run_metadata = json.loads(run_path.read_text(encoding="utf-8"))
                manifest = run_metadata["collector_manifest"]
                if field == "registry_version":
                    manifest[field] = "tampered"
                else:
                    manifest["regimes"]["ksoyu_post_2019"][field] = "tampered"
                run_path.write_text(json.dumps(run_metadata), encoding="utf-8")
                transport = MappingTransport({})
                with self.assertRaisesRegex(ValueError, "collector manifest"):
                    run_collection(Path(tmp), plan=frozen_plan(), transport=transport, resume=True)
                self.assertEqual([], transport.calls)

    def test_end_to_end_pagination_card_doc_and_resume(self):
        root = build_listing_url("1kas.sudrf.ru", "2024-03-07")
        page2 = root + "&page=2"
        case = "https://1kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=case&case_id=101&case_uid=UID-001&delo_id=2800001&new=2800001"
        direct_doc = "https://1kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=doc&number=101&delo_id=2800001&new=2800001&text_number=1"
        card_doc2 = "https://1kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=doc&number=102&delo_id=2800001&text_number=2"
        transport = MappingTransport(
            {
                root: (200, "listing_pagination.html"),
                page2: (200, "listing_nonempty.html"),
                case: (200, "card.html"),
                direct_doc: (200, "doc.html"),
                card_doc2: (200, "doc.html"),
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            applicant_chain = Path(tmp) / "applicant-chain.json"
            applicant_chain.write_text(
                json.dumps({"run_id": None, "propositions": []}), encoding="utf-8"
            )
            result = run_collection(Path(tmp), plan=frozen_plan(), transport=transport, resume=False)
            self.assertEqual("closed_official_population_observed", result["coverage"]["population_status"])
            self.assertEqual(2, result["coverage"]["successful_segments"])
            self.assertGreaterEqual(result["independence"]["sources"], 3)
            self.assertEqual(1, result["independence"]["case_chains"])
            calls_after_first = list(transport.calls)
            resumed = run_collection(Path(tmp), plan=frozen_plan(), transport=transport, resume=True)
            self.assertEqual(calls_after_first, transport.calls)
            self.assertEqual(result["run_id"], resumed["run_id"])
            self.assertTrue((Path(tmp) / "exports" / "coverage.json").exists())
            self.assertTrue((Path(tmp) / "exports" / "sources.jsonl").exists())
            self.assertTrue((Path(tmp) / "exports" / "case-chains.jsonl").exists())
            self.assertEqual(
                result["run_id"],
                json.loads(applicant_chain.read_text(encoding="utf-8"))["run_id"],
            )

    def test_protective_page_is_not_empty_or_complete(self):
        root = build_listing_url("1kas.sudrf.ru", "2024-03-07")
        transport = MappingTransport({root: (200, "protective.html")})
        with tempfile.TemporaryDirectory() as tmp:
            result = run_collection(Path(tmp), plan=frozen_plan(), transport=transport, resume=False, max_attempts=1)
            self.assertEqual(1, result["coverage"]["blocked"])
            self.assertEqual(0, result["coverage"]["success_empty"])
            self.assertFalse(result["coverage"]["closed_official_population_observed"])

    def test_retry_limit_becomes_terminal_without_becoming_empty(self):
        root = build_listing_url("1kas.sudrf.ru", "2024-03-07")
        transport = MappingTransport({root: (503, "listing_nonempty.html")})
        with tempfile.TemporaryDirectory() as tmp:
            result = run_collection(Path(tmp), plan=frozen_plan(), transport=transport, resume=False, max_attempts=1)
            self.assertEqual(1, result["coverage"]["terminal_error"])
            self.assertEqual(0, result["coverage"]["success_empty"])
            self.assertEqual(0, result["coverage"]["retryable_error"])

    def test_source_failures_are_durable_and_resume_without_refetching_listing(self):
        root = build_listing_url("1kas.sudrf.ru", "2024-03-07")
        case = "https://1kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=case&case_id=101&case_uid=UID-001&delo_id=2800001&new=2800001"
        direct_doc = "https://1kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=doc&number=101&delo_id=2800001&new=2800001&text_number=1"
        card_doc2 = "https://1kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1&name_op=doc&number=102&delo_id=2800001&text_number=2"
        first_transport = MappingTransport({root: (200, "listing_nonempty.html")})
        second_transport = MappingTransport(
            {
                case: (200, "card.html"),
                direct_doc: (200, "doc.html"),
                card_doc2: (200, "doc.html"),
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            first = run_collection(
                Path(tmp),
                plan=frozen_plan(),
                transport=first_transport,
                resume=False,
                max_source_tasks=0,
            )
            self.assertEqual([root], first_transport.calls)
            self.assertGreater(first["source_acquisition"]["unresolved"], 0)
            self.assertFalse(first["coverage"]["collection_complete"])
            second = run_collection(
                Path(tmp),
                plan=frozen_plan(),
                transport=second_transport,
                resume=True,
                retry_now=True,
            )
            self.assertNotIn(root, second_transport.calls)
            self.assertEqual(0, second["source_acquisition"]["unresolved"])
            self.assertTrue(second["coverage"]["collection_complete"])

    def test_pre_reform_period_is_reported_as_unconfigured_not_silently_dropped(self):
        plan = frozen_plan()
        plan["population"]["date_from"] = "2019-09-30"
        plan["population"]["date_to"] = "2019-10-01"
        plan["population"]["regimes"] = ["regional_presidia_pre_2019", "ksoyu_post_2019"]
        root = build_listing_url("1kas.sudrf.ru", "2019-10-01")
        transport = MappingTransport({root: (200, "listing_empty.html")})
        with tempfile.TemporaryDirectory() as tmp:
            result = run_collection(Path(tmp), plan=plan, transport=transport, resume=False)
            self.assertEqual("regional_presidia_pre_2019", result["coverage"]["regime_gaps"][0]["regime"])
            self.assertEqual("not_configured", result["coverage"]["regime_gaps"][0]["status"])
            self.assertFalse(result["coverage"]["collection_complete"])
            self.assertEqual("observed_corpus_only", result["coverage"]["population_status"])


if __name__ == "__main__":
    unittest.main()
