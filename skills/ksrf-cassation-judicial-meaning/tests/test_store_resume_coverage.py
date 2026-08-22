import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from judicial_meaning.store import RunStore


class StoreResumeCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.store = RunStore(self.workspace)
        self.run_id = self.store.create_run({"frozen": True, "plan_sha256": "a" * 64})

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_schema_and_content_addressed_storage(self):
        self.assertTrue((self.workspace / "corpus.sqlite3").exists())
        first = self.store.put_object(b"same bytes")
        second = self.store.put_object(b"same bytes")
        self.assertEqual(first, second)
        self.assertTrue((self.workspace / first).exists())
        tables = {row[0] for row in self.store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"runs", "listing_tasks", "sources", "snapshots", "events"}.issubset(tables))

    def test_resume_skips_complete_and_retries_failed(self):
        self.store.seed_calendar(self.run_id, ["1kas"], "2024-03-07", "2024-03-08")
        first = self.store.claim_next_listing(self.run_id, now="2024-03-09T00:00:00Z")
        self.store.finish_listing(first["task_id"], "success_empty", 200, row_count=0)
        second = self.store.claim_next_listing(self.run_id, now="2024-03-09T00:00:00Z")
        self.store.fail_listing(second["task_id"], "retryable_error", "timeout")
        retried = self.store.claim_next_listing(self.run_id, now="9999-01-01T00:00:00Z")
        self.assertEqual(second["task_id"], retried["task_id"])
        self.assertEqual(2, retried["attempts"])
        completed = self.store.get_listing(first["task_id"])
        self.assertEqual("success_empty", completed["status"])

    def test_recover_stale_fetching_preserves_event(self):
        self.store.seed_calendar(self.run_id, ["1kas"], "2024-03-07", "2024-03-07")
        task = self.store.claim_next_listing(self.run_id, now="2024-03-07T00:00:00Z")
        recovered = self.store.recover_stale_claims("2024-03-08T00:00:00Z")
        self.assertEqual(1, recovered)
        self.assertEqual("pending", self.store.get_listing(task["task_id"])["status"])
        reasons = [row[0] for row in self.store.conn.execute("SELECT reason_code FROM events")]
        self.assertIn("stale_claim_recovered", reasons)

    def test_coverage_never_calls_failed_page_empty_or_complete(self):
        self.store.seed_calendar(self.run_id, ["1kas"], "2024-03-07", "2024-03-08")
        first = self.store.claim_next_listing(self.run_id, now="2024-03-09T00:00:00Z")
        self.store.finish_listing(first["task_id"], "success_empty", 200, row_count=0)
        second = self.store.claim_next_listing(self.run_id, now="2024-03-09T00:00:00Z")
        self.store.fail_listing(second["task_id"], "blocked", "captcha")
        report = self.store.coverage_report(self.run_id)
        self.assertEqual(1, report["success_empty"])
        self.assertEqual(1, report["blocked"])
        self.assertFalse(report["closed_official_population_observed"])
        self.assertEqual("observed_corpus_only", report["population_status"])

    def test_dedup_preserves_sources_but_counts_content_and_chain_once(self):
        source_a = self.store.add_source(
            self.run_id,
            court_code="1kas",
            kind="doc",
            canonical_url="https://1kas.sudrf.ru/doc?a=1",
            case_uid="UID-1",
            raw=b"one act",
            text="Один и тот же акт",
        )
        source_b = self.store.add_source(
            self.run_id,
            court_code="1kas",
            kind="doc",
            canonical_url="https://1kas.sudrf.ru/doc?a=2",
            case_uid="UID-1",
            raw=b"one act",
            text="Один и тот же акт",
        )
        self.assertNotEqual(source_a["source_id"], source_b["source_id"])
        self.assertEqual(source_a["document_id"], source_b["document_id"])
        self.assertEqual(source_a["chain_id"], source_b["chain_id"])
        counts = self.store.independence_counts(self.run_id)
        self.assertEqual({"sources": 2, "documents": 1, "case_chains": 1}, counts)

    def test_deterministic_export(self):
        self.store.seed_calendar(self.run_id, ["1kas"], "2024-03-07", "2024-03-07")
        first = self.store.export_jsonl("listing_tasks")
        second = self.store.export_jsonl("listing_tasks")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        chains = self.store.export_case_chains(self.run_id)
        self.assertTrue(chains.exists())


if __name__ == "__main__":
    unittest.main()
