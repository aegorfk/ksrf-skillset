import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from judicial_meaning.public_corpus import (
    FunnelTransitionError,
    PrivacyBoundaryError,
    PublicCorpus,
    RunPinConflict,
    SeedRoleError,
    TreatmentReviewError,
)


OFFICIAL_URL = "https://2kas.sudrf.ru/modules.php?name=sud_delo&name_op=doc&number=1"


class PublicCorpusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.corpus = PublicCorpus(self.root)

    def tearDown(self):
        self.corpus.close()
        self.tmp.cleanup()

    def _official_seed(self, suffix=""):
        return self.corpus.register_seed(
            url=OFFICIAL_URL + suffix,
            role="official_user_seed",
            public=True,
        )

    def _snapshot(self, raw=b"official act", suffix="", fetched_at="2026-08-01T00:00:00Z"):
        seed = self._official_seed(suffix)
        return self.corpus.store_snapshot(
            seed_id=seed["seed_id"],
            raw=raw,
            content_type="text/html; charset=utf-8",
            fetched_at=fetched_at,
            parser_manifest={"adapter_id": "ksoyu_daily_v2", "parser_version": "2.0"},
        )

    def test_private_seed_never_enters_reusable_cache(self):
        with self.assertRaises(PrivacyBoundaryError):
            self.corpus.register_seed(
                url="file:///private/applicant-act.pdf",
                role="applicant_private",
                public=False,
            )
        with self.assertRaises(PrivacyBoundaryError):
            self.corpus.register_seed(
                url=OFFICIAL_URL,
                role="official_user_seed",
                public=False,
            )
        self.assertEqual([], self.corpus.list_seeds())

    def test_public_seed_url_rejects_private_hosts_credentials_and_secret_query_keys(self):
        rejected_urls = (
            "https://user:secret@2kas.sudrf.ru/act",
            "https://localhost/act",
            "https://court.localhost/act",
            "https://127.0.0.1/act",
            "https://10.1.2.3/act",
            "https://169.254.10.20/act",
            "https://192.0.2.10/act",
            "https://[::1]/act",
            "https://2130706433/act",
            "https://0177.0.0.1/act",
            "https://2kas.sudrf.ru/act?access_token=should-not-enter-cache",
            "https://2kas.sudrf.ru/act?X-Amz-Signature=should-not-enter-cache",
        )
        for url in rejected_urls:
            with self.subTest(url=url), self.assertRaises(PrivacyBoundaryError):
                self.corpus.register_seed(
                    url=url,
                    role="official_user_seed",
                    public=True,
                )
        self.assertEqual([], self.corpus.list_seeds())

    def test_public_url_validation_never_resolves_dns(self):
        with patch("socket.getaddrinfo", side_effect=AssertionError("DNS must not be used")):
            seed = self.corpus.register_seed(
                url="https://2kas.sudrf.ru/public-act?name=sud_delo",
                role="official_user_seed",
                public=True,
            )
        self.assertEqual("official_user_seed", seed["role"])

    def test_seed_roles_are_explicit_and_invalid_role_is_rejected(self):
        seed = self._official_seed()
        self.assertEqual("official_user_seed", seed["role"])
        with self.assertRaises(SeedRoleError):
            self.corpus.register_seed(
                url="https://example.invalid/mirror",
                role="probably_official",
                public=True,
            )
        with self.assertRaises(SeedRoleError):
            self.corpus.register_seed(
                url="https://example.org/claimed-official-act",
                role="official_user_seed",
                public=True,
            )

        discovery = self.corpus.register_seed(
            url="https://example.org/public-mirror",
            role="discovery_only",
            public=True,
        )
        with self.assertRaises(PrivacyBoundaryError):
            self.corpus.store_snapshot(
                seed_id=discovery["seed_id"],
                raw=b"mirror bytes must not enter evidence objects",
                content_type="text/html",
                fetched_at="2026-08-01T00:00:00Z",
                parser_manifest={"parser_version": "1"},
            )
        self.assertEqual("discovery_only", self.corpus.list_seeds()[-1]["role"])

    def test_snapshots_are_immutable_and_run_pins_do_not_move(self):
        first = self._snapshot(raw=b"version one", fetched_at="2026-08-01T00:00:00Z")
        digest_before_refresh = self.corpus.evidence_digest()
        repeated = self.corpus.store_snapshot(
            seed_id=first["seed_id"],
            raw=b"version one",
            content_type="text/html",
            fetched_at="2026-08-02T00:00:00Z",
            parser_manifest={"adapter_id": "ksoyu_daily_v2", "parser_version": "2.0"},
        )
        self.assertEqual(first["snapshot_id"], repeated["snapshot_id"])
        self.assertEqual(digest_before_refresh, self.corpus.evidence_digest())

        run = self.corpus.create_run("matter-run", [first["snapshot_id"]])
        changed = self.corpus.store_snapshot(
            seed_id=first["seed_id"],
            raw=b"version two",
            content_type="text/html",
            fetched_at="2026-08-03T00:00:00Z",
            parser_manifest={"adapter_id": "ksoyu_daily_v2", "parser_version": "2.0"},
        )
        self.assertNotEqual(first["snapshot_id"], changed["snapshot_id"])
        self.assertEqual([first["snapshot_id"]], self.corpus.run_snapshots(run["run_id"]))
        self.assertEqual(b"version one", self.corpus.snapshot_bytes(first["snapshot_id"]))
        with self.assertRaises(RunPinConflict):
            self.corpus.create_run("matter-run", [changed["snapshot_id"]])

    def test_public_run_exchange_is_portable_searchable_and_tamper_evident(self):
        snapshot = self._snapshot(raw="Суд взыскал премию".encode("utf-8"))
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Суд взыскал премию работнику.",
            document_id="document-2kas-1",
            chain_candidate_id="chain-2kas-1",
            query_lane="exact_norm",
        )
        self.corpus.record_funnel(
            "chain-2kas-1",
            "enumerated",
            source_role="official_enumerator_observation",
            court_id="2kas",
            period_id="post-23-p",
            enumerator_id="2kas-daily",
        )
        for status in (
            "card",
            "document_link",
            "payload_validated",
            "full_text_extracted",
            "indexed",
            "screened",
            "coded",
            "approved_independent_chain",
        ):
            self.corpus.record_funnel(
                "chain-2kas-1",
                status,
                snapshot_id=snapshot["snapshot_id"],
                source_role="official_enumerator_observation",
                court_id="2kas",
                period_id="post-23-p",
                enumerator_id="2kas-daily",
            )
        treatment = self.corpus.propose_treatment(
            source_chain_id="chain-2kas-1",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П", "act_date": "2023-06-15"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.corpus.review_treatment(
            treatment["treatment_id"],
            decision="verified",
            reviewer="И.И. Иванов",
            quote="Суд применяет правовую позицию КС РФ",
            locator="абз. 14",
            speaker="court",
            confirmed_target_authority_id="ksrf-32-p-2023",
            target_identity_confirmed=True,
            reviewed_at="2026-08-26T00:00:00Z",
        )
        self.corpus.create_run("public-run", [snapshot["snapshot_id"]])
        package = self.root / "exchange"

        exported = self.corpus.export_run("public-run", package)
        self.assertEqual("1.0", exported["schema_version"])
        self.assertTrue(exported["public_only"])
        self.assertEqual("document-2kas-1", exported["indexed_texts"][0]["document_id"])
        self.assertEqual("chain-2kas-1", exported["indexed_texts"][0]["chain_candidate_id"])
        self.assertEqual("exact_norm", exported["indexed_texts"][0]["query_lane"])
        self.assertEqual("approved_independent_chain", exported["funnel"]["states"][0]["status"])
        self.assertEqual(9, len(exported["funnel"]["events"]))
        self.assertEqual(2, len(exported["treatments"][0]["review_history"]))

        second_package = self.root / "exchange-again"
        repeated = self.corpus.export_run("public-run", second_package)
        self.assertEqual(exported, repeated)
        self.assertEqual(
            (package / "manifest.json").read_bytes(),
            (second_package / "manifest.json").read_bytes(),
        )

        schema_path = Path(__file__).parents[1] / "schemas" / "public-corpus-package.v1.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            Draft202012Validator = None
        if Draft202012Validator is not None:
            Draft202012Validator(schema).validate(exported)

        imported_root = self.root / "imported"
        with PublicCorpus(imported_root) as imported:
            receipt = imported.import_run(package)
            self.assertEqual("public-run", receipt["run_id"])
            self.assertEqual([snapshot["snapshot_id"]], imported.run_snapshots("public-run"))
            hit = imported.search("премию")[0]
            self.assertEqual(snapshot["snapshot_id"], hit["snapshot_id"])
            self.assertEqual("document-2kas-1", hit["document_id"])
            self.assertEqual("chain-2kas-1", hit["chain_candidate_id"])
            self.assertEqual("exact_norm", hit["query_lane"])
            self.assertEqual(1, imported.funnel_report()["approved_independent_chain"])
            self.assertEqual(
                self.corpus.list_treatments(),
                imported.list_treatments(),
            )
            self.assertEqual(
                self.corpus.treatment_history(treatment["treatment_id"]),
                imported.treatment_history(treatment["treatment_id"]),
            )
            imported_events = imported.conn.execute(
                "SELECT COUNT(*) AS count FROM funnel_events WHERE chain_id=?",
                ("chain-2kas-1",),
            ).fetchone()
            self.assertEqual(9, int(imported_events["count"]))
            funnel_columns = (
                "event_id, chain_id, status, snapshot_id, reason, source_role, "
                "court_id, period_id, enumerator_id, event_at"
            )
            original_history = [
                dict(row)
                for row in self.corpus.conn.execute(
                    f"SELECT {funnel_columns} FROM funnel_events WHERE chain_id=? ORDER BY rowid",
                    ("chain-2kas-1",),
                ).fetchall()
            ]
            imported_history = [
                dict(row)
                for row in imported.conn.execute(
                    f"SELECT {funnel_columns} FROM funnel_events WHERE chain_id=? ORDER BY rowid",
                    ("chain-2kas-1",),
                ).fetchall()
            ]
            self.assertEqual(original_history, imported_history)
            self.assertEqual(
                dict(
                    self.corpus.conn.execute(
                        "SELECT * FROM funnel_state WHERE chain_id=?",
                        ("chain-2kas-1",),
                    ).fetchone()
                ),
                dict(
                    imported.conn.execute(
                        "SELECT * FROM funnel_state WHERE chain_id=?",
                        ("chain-2kas-1",),
                    ).fetchone()
                ),
            )
            reexported = imported.export_run("public-run", self.root / "reexported")
            self.assertEqual(exported, reexported)
            repeated_receipt = imported.import_run(package)
            self.assertEqual(receipt, repeated_receipt)

        object_path = next((package / "objects").glob("*.bin"))
        object_path.write_bytes(b"tampered")
        with PublicCorpus(self.root / "tampered-target") as target:
            with self.assertRaises(ValueError):
                target.import_run(package)
            self.assertEqual([], target.list_seeds())

    def test_portable_import_runtime_validation_rejects_missing_index_provenance(self):
        snapshot = self._snapshot(raw=b"portable provenance")
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Премия выплачена",
            document_id="document-1",
            chain_candidate_id="chain-1",
            query_lane="court_language",
        )
        self.corpus.create_run("runtime-validation", [snapshot["snapshot_id"]])
        package_root = self.root / "invalid-package"
        package = self.corpus.export_run("runtime-validation", package_root)
        del package["indexed_texts"][0]["document_id"]
        unsigned = {key: value for key, value in package.items() if key != "manifest_sha256"}
        import hashlib

        package["manifest_sha256"] = hashlib.sha256(
            json.dumps(
                unsigned,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        (package_root / "manifest.json").write_text(
            json.dumps(package, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        with PublicCorpus(self.root / "invalid-import-target") as target:
            with self.assertRaisesRegex(ValueError, "provenance"):
                target.import_run(package_root)
            self.assertEqual([], target.list_seeds())

    def test_fts_and_fallback_search_return_snapshot_and_locator(self):
        first = self._snapshot(raw=b"first", suffix="&text=1")
        second = self._snapshot(raw=b"second", suffix="&text=2")
        self.corpus.index_text(
            first["snapshot_id"],
            "Суд взыскал премию работнику.",
            document_id="document-1",
            chain_candidate_id="chain-1",
            query_lane="exact_norm",
        )
        self.corpus.index_text(second["snapshot_id"], "Спор касался увольнения.")

        hits = self.corpus.search("премию")
        self.assertEqual([first["snapshot_id"]], [hit["snapshot_id"] for hit in hits])
        self.assertEqual("премию", hits[0]["matched_text"])
        self.assertGreaterEqual(hits[0]["start"], 0)
        self.assertIn(self.corpus.search_backend, {"fts5", "fallback"})
        self.assertEqual("document-1", hits[0]["document_id"])
        self.assertEqual("chain-1", hits[0]["chain_candidate_id"])
        self.assertEqual("exact_norm", hits[0]["query_lane"])
        self.assertEqual("official_user_seed", hits[0]["source_role"])
        self.assertEqual(OFFICIAL_URL + "&text=1", hits[0]["source_url"])
        self.assertEqual("discovery_needs_full_text_legal_coding", hits[0]["evidence_role"])

        fallback_root = self.root / "fallback"
        with PublicCorpus(fallback_root, force_fallback_search=True) as fallback:
            seed = fallback.register_seed(url=OFFICIAL_URL, role="official_user_seed", public=True)
            snapshot = fallback.store_snapshot(
                seed_id=seed["seed_id"],
                raw=b"fallback",
                content_type="text/plain",
                fetched_at="2026-08-01T00:00:00Z",
                parser_manifest={"parser_version": "2.0"},
            )
            fallback.index_text(snapshot["snapshot_id"], "Ежемесячная премия сохранена")
            self.assertEqual("fallback", fallback.search_backend)
            self.assertEqual(snapshot["snapshot_id"], fallback.search("ПРЕМИЯ")[0]["snapshot_id"])

    def test_fallback_index_is_backfilled_if_fts5_becomes_available_later(self):
        transition_root = self.root / "backend-transition"
        with PublicCorpus(transition_root, force_fallback_search=True) as fallback:
            seed = fallback.register_seed(url=OFFICIAL_URL, role="official_user_seed", public=True)
            snapshot = fallback.store_snapshot(
                seed_id=seed["seed_id"],
                raw=b"transition",
                content_type="text/plain",
                fetched_at="2026-08-01T00:00:00Z",
                parser_manifest={"parser_version": "2.0"},
            )
            fallback.index_text(snapshot["snapshot_id"], "Премия входит в систему оплаты труда")

        with PublicCorpus(transition_root) as reopened:
            if reopened.search_backend != "fts5":
                self.skipTest("SQLite runtime has no FTS5")
            self.assertEqual(snapshot["snapshot_id"], reopened.search("премия")[0]["snapshot_id"])

    def test_full_text_funnel_is_ordered_and_reported_by_chain(self):
        snapshot = self._snapshot()
        self.corpus.record_funnel(
            "chain-1", "enumerated", source_role="official_enumerator_observation",
            court_id="2kas", period_id="post-23-p", enumerator_id="2kas-daily",
        )
        with self.assertRaises(FunnelTransitionError):
            self.corpus.record_funnel("chain-1", "approved_independent_chain", snapshot_id=snapshot["snapshot_id"])
        for status in (
            "card",
            "document_link",
            "payload_validated",
            "full_text_extracted",
            "indexed",
            "screened",
            "coded",
            "approved_independent_chain",
        ):
            self.corpus.record_funnel(
                "chain-1", status, snapshot_id=snapshot["snapshot_id"],
                source_role="official_enumerator_observation", court_id="2kas",
                period_id="post-23-p", enumerator_id="2kas-daily",
            )
        self.corpus.record_funnel("chain-2", "enumerated", court_id="2kas", period_id="pre-23-p")
        self.corpus.record_funnel(
            "chain-2",
            "official_page_no_text",
            reason="Карточка не содержит полного текста",
        )
        report = self.corpus.funnel_report()
        self.assertEqual(1, report["approved_independent_chain"])
        self.assertEqual(1, report["official_page_no_text"])
        self.assertEqual(1, report["strata"]["court_id"]["2kas"]["approved_independent_chain"])
        self.assertEqual(1, report["strata"]["period_id"]["pre-23-p"]["official_page_no_text"])

    def test_refresh_plan_is_deterministic_and_content_digest_ignores_unchanged_fetch(self):
        old = self._snapshot(raw=b"old", suffix="&old=1", fetched_at="2026-07-01T00:00:00Z")
        recent = self._snapshot(raw=b"recent", suffix="&recent=1", fetched_at="2026-08-25T00:00:00Z")
        plan = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=7 * 24 * 60 * 60,
            coverage_requirements=[
                {"court_id": "2kas", "period_id": "2016-2019", "enumerator_id": "pre-2019"}
            ],
        )
        self.assertEqual([old["seed_id"]], [entry["seed_id"] for entry in plan["entries"] if entry.get("seed_id")])
        self.assertEqual("coverage_gap_not_observed", plan["coverage_gaps"][0]["reason"])
        self.assertEqual(
            plan,
            self.corpus.plan_refresh(
                as_of="2026-08-26T00:00:00Z",
                max_age_seconds=7 * 24 * 60 * 60,
                coverage_requirements=[
                    {"court_id": "2kas", "period_id": "2016-2019", "enumerator_id": "pre-2019"}
                ],
            ),
        )

        digest = self.corpus.evidence_digest()
        self.corpus.store_snapshot(
            seed_id=recent["seed_id"],
            raw=b"recent",
            content_type="text/html",
            fetched_at="2026-08-26T00:00:00Z",
            parser_manifest={"parser_version": "2.0"},
        )
        self.assertEqual(digest, self.corpus.evidence_digest())
        self.corpus.store_snapshot(
            seed_id=recent["seed_id"],
            raw=b"recent changed",
            content_type="text/html",
            fetched_at="2026-08-26T01:00:00Z",
            parser_manifest={"parser_version": "2.0"},
        )
        self.assertNotEqual(digest, self.corpus.evidence_digest())

    def test_treatment_stays_candidate_until_quote_level_review(self):
        snapshot = self._snapshot()
        candidate = self.corpus.propose_treatment(
            source_chain_id="chain-1",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П", "act_date": "2023-06-15"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.assertEqual("candidate", candidate["status"])
        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                decision="verified",
                reviewer="И.И. Иванов",
            )
        verified = self.corpus.review_treatment(
            candidate["treatment_id"],
            decision="verified",
            reviewer="И.И. Иванов",
            quote="Суд применяет правовую позицию Конституционного Суда",
            locator="абз. 14",
            speaker="court",
            confirmed_target_authority_id="ksrf-32-p-2023",
            target_identity_confirmed=True,
            reviewed_at="2026-08-26T00:00:00Z",
        )
        self.assertEqual("verified", verified["status"])
        self.assertEqual(1, len(self.corpus.list_treatments(verified_only=True)))

    def test_verified_treatment_review_cannot_be_rewritten(self):
        snapshot = self._snapshot()
        candidate = self.corpus.propose_treatment(
            source_chain_id="chain-1",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П", "act_date": "2023-06-15"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.corpus.review_treatment(
            candidate["treatment_id"],
            decision="verified",
            reviewer="И.И. Иванов",
            quote="Первоначально проверенная цитата",
            locator="абз. 14",
            speaker="court",
            confirmed_target_authority_id="ksrf-32-p-2023",
            target_identity_confirmed=True,
            reviewed_at="2026-08-26T00:00:00Z",
        )
        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                decision="verified",
                reviewer="П.П. Петров",
                quote="Подменённая цитата",
                locator="абз. 99",
                speaker="court",
                confirmed_target_authority_id="ksrf-32-p-2023",
                target_identity_confirmed=True,
                reviewed_at="2026-08-27T00:00:00Z",
            )
        history = self.corpus.treatment_history(candidate["treatment_id"])
        self.assertEqual(["candidate_created", "verified"], [item["event_type"] for item in history])

        replacement = self.corpus.propose_treatment(
            source_chain_id="chain-1",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П", "act_date": "2023-06-15"},
            treatment_type="supersedes",
            snapshot_id=snapshot["snapshot_id"],
            supersedes_treatment_id=candidate["treatment_id"],
        )
        self.assertEqual(candidate["treatment_id"], replacement["supersedes_treatment_id"])


if __name__ == "__main__":
    unittest.main()
