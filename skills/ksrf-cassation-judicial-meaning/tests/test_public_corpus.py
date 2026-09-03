import json
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from judicial_meaning.public_corpus import (
    FunnelTransitionError,
    PrivacyBoundaryError,
    PublicCorpus,
    PublicCorpusError,
    RunPinConflict,
    SeedRoleError,
    TreatmentReviewError,
    _identifier,
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

    def _verified_treatment(self):
        snapshot = self._snapshot(raw="Проверенная позиция суда.".encode("utf-8"))
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Проверенная позиция суда.",
            document_id="document-history-integrity",
            chain_candidate_id="chain-history-integrity",
            query_lane="higher_authority",
        )
        treatment = self.corpus.propose_treatment(
            source_chain_id="chain-history-integrity",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.corpus.review_treatment(
            treatment["treatment_id"],
            decision="verified",
            reviewer="И.И. Иванов",
            quote="Проверенная позиция суда",
            locator="абз. 1",
            speaker="court",
            confirmed_target_authority_id="ksrf-32-p-2023",
            target_identity_confirmed=True,
        )
        return treatment

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
            source_role="official_user_seed",
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
                source_role="official_user_seed",
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
            quote="Суд взыскал премию",
            locator="абз. 14",
            speaker="court",
            confirmed_target_authority_id="ksrf-32-p-2023",
            target_identity_confirmed=True,
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

    def test_portable_import_rejects_funnel_role_not_bound_to_observation(self):
        snapshot = self._snapshot(raw=b"portable role binding")
        self.corpus.record_funnel(
            "chain-role-binding",
            "enumerated",
            snapshot_id=snapshot["snapshot_id"],
            source_role="official_user_seed",
            court_id="2kas",
        )
        self.corpus.create_run("role-binding", [snapshot["snapshot_id"]])
        package_root = self.root / "role-binding-package"
        package = self.corpus.export_run("role-binding", package_root)
        package["funnel"]["states"][0]["source_role"] = (
            "official_authority_seed"
        )
        unsigned = {
            key: value for key, value in package.items() if key != "manifest_sha256"
        }
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
            json.dumps(
                package,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        with PublicCorpus(self.root / "role-binding-target") as target:
            with self.assertRaisesRegex(ValueError, "not bound"):
                target.import_run(package_root)
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
            "chain-1", "enumerated", source_role="official_user_seed",
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
                source_role="official_user_seed", court_id="2kas",
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

    def test_funnel_rejects_inherited_role_for_a_different_snapshot(self):
        first = self._snapshot(raw=b"first role-bound snapshot")
        second_seed = self.corpus.register_seed(
            url=OFFICIAL_URL + "&authority=1",
            role="official_authority_seed",
            public=True,
        )
        second = self.corpus.store_snapshot(
            seed_id=second_seed["seed_id"],
            raw=b"second role-bound snapshot",
            content_type="text/html",
            fetched_at="2026-08-01T00:00:00Z",
            parser_manifest={"parser_version": "1.0"},
        )
        self.corpus.record_funnel(
            "chain-role-drift",
            "enumerated",
            source_role="official_user_seed",
            court_id="2kas",
        )
        self.corpus.record_funnel(
            "chain-role-drift",
            "card",
            snapshot_id=first["snapshot_id"],
            source_role="official_user_seed",
        )
        with self.assertRaisesRegex(FunnelTransitionError, "effective snapshot"):
            self.corpus.record_funnel(
                "chain-role-drift",
                "document_link",
                snapshot_id=second["snapshot_id"],
            )

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
        self.assertEqual(
            [
                {
                    "court_id": "2kas",
                    "period_id": "2016-2019",
                    "enumerator_id": "pre-2019",
                }
            ],
            plan["coverage_requirements"],
        )
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

    def test_refresh_plan_rejects_lossy_coverage_requirements(self):
        invalid_requirements = (
            [{}],
            [{"court_id": ""}],
            [{"court_id": 2}],
            [{"court_id": " 2kas "}],
            [{"court_id": "2kas\u200b"}],
            [{"source_role": "claimed_official"}],
            [{"unknown_dimension": "2kas"}],
        )
        for requirements in invalid_requirements:
            with self.subTest(requirements=requirements), self.assertRaises(
                PublicCorpusError
            ):
                self.corpus.plan_refresh(
                    as_of="2026-08-26T00:00:00Z",
                    max_age_seconds=604800,
                    coverage_requirements=requirements,
                )

    def test_refresh_plan_keeps_blocked_chain_with_retained_snapshot_as_gap(self):
        snapshot = self._snapshot(raw=b"blocked coverage")
        self.corpus.record_funnel(
            "chain-blocked",
            "enumerated",
            snapshot_id=snapshot["snapshot_id"],
            source_role="official_user_seed",
            court_id="2kas",
            period_id="2026-q3",
            enumerator_id="2kas-daily",
        )
        self.corpus.record_funnel(
            "chain-blocked",
            "blocked",
            reason="Источник временно недоступен.",
        )
        retained = self.corpus.conn.execute(
            "SELECT status, snapshot_id FROM funnel_state WHERE chain_id=?",
            ("chain-blocked",),
        ).fetchone()
        self.assertEqual("blocked", retained["status"])
        self.assertEqual(snapshot["snapshot_id"], retained["snapshot_id"])

        plan = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=7 * 24 * 60 * 60,
            coverage_requirements=[
                {
                    "court_id": "2kas",
                    "period_id": "2026-q3",
                    "enumerator_id": "2kas-daily",
                }
            ],
        )
        self.assertEqual(1, len(plan["coverage_gaps"]))
        self.assertEqual(
            "coverage_gap_not_observed",
            plan["coverage_gaps"][0]["reason"],
        )

    def test_refresh_plan_requires_intact_content_for_observed_coverage(self):
        snapshot = self._snapshot(raw="Проверенный текст.".encode("utf-8"))
        self.corpus.record_funnel(
            "chain-integrity-coverage",
            "enumerated",
            source_role="official_user_seed",
            court_id="2kas",
            period_id="2026-q3",
        )
        for status in (
            "card",
            "document_link",
            "payload_validated",
            "full_text_extracted",
        ):
            self.corpus.record_funnel(
                "chain-integrity-coverage",
                status,
                snapshot_id=snapshot["snapshot_id"],
                source_role="official_user_seed",
                court_id="2kas",
                period_id="2026-q3",
            )
        requirements = [{"court_id": "2kas", "period_id": "2026-q3"}]
        intact = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=7 * 24 * 60 * 60,
            coverage_requirements=requirements,
        )
        self.assertEqual([], intact["coverage_gaps"])

        object_path = Path(snapshot["object_path"])
        original = object_path.read_bytes()
        object_path.write_bytes(b"corrupt")
        corrupted_snapshot = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=7 * 24 * 60 * 60,
            coverage_requirements=requirements,
        )
        self.assertEqual(1, len(corrupted_snapshot["coverage_gaps"]))

        object_path.write_bytes(original)
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Проверенный текст.",
            document_id="document-integrity-coverage",
            chain_candidate_id="chain-integrity-coverage",
            query_lane="general",
        )
        self.corpus.record_funnel(
            "chain-integrity-coverage",
            "indexed",
            snapshot_id=snapshot["snapshot_id"],
            source_role="official_user_seed",
            court_id="2kas",
            period_id="2026-q3",
        )
        with self.corpus.conn:
            self.corpus.conn.execute(
                "UPDATE indexed_texts SET original_text=? WHERE snapshot_id=?",
                ("Подменённый текст.", snapshot["snapshot_id"]),
            )
        corrupted_index = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=7 * 24 * 60 * 60,
            coverage_requirements=requirements,
        )
        self.assertEqual(1, len(corrupted_index["coverage_gaps"]))

    def test_successful_chain_does_not_hide_blocked_sibling_in_same_scope(self):
        snapshot = self._snapshot(raw=b"successful sibling")
        dimensions = {
            "source_role": "official_user_seed",
            "court_id": "2kas",
            "period_id": "2026-q3",
            "enumerator_id": "daily",
        }
        self.corpus.record_funnel("chain-success", "enumerated", **dimensions)
        for status in (
            "card",
            "document_link",
            "payload_validated",
            "full_text_extracted",
        ):
            self.corpus.record_funnel(
                "chain-success",
                status,
                snapshot_id=snapshot["snapshot_id"],
                **dimensions,
            )
        self.corpus.record_funnel("chain-blocked-sibling", "enumerated", **dimensions)
        self.corpus.record_funnel(
            "chain-blocked-sibling",
            "blocked",
            reason="Источник недоступен.",
        )
        plan = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=604800,
            coverage_requirements=[
                {
                    "court_id": "2kas",
                    "period_id": "2026-q3",
                    "enumerator_id": "daily",
                }
            ],
        )
        self.assertEqual(1, len(plan["coverage_gaps"]))

    def test_plan_refresh_requires_aware_full_rfc3339_timestamp(self):
        for invalid_as_of in (
            "2026-08-26",
            "2026-08-26T00:00Z",
            "2026-W35-3T00:00:00Z",
            "2026-08-26T00:00:00",
        ):
            with self.subTest(invalid_as_of=invalid_as_of):
                with self.assertRaises(PublicCorpusError):
                    self.corpus.plan_refresh(
                        as_of=invalid_as_of,
                        max_age_seconds=7 * 24 * 60 * 60,
                    )

        for aware_as_of in (
            "2026-08-26T00:00:00Z",
            "2026-08-26T03:00:00+03:00",
        ):
            with self.subTest(aware_as_of=aware_as_of):
                plan = self.corpus.plan_refresh(
                    as_of=aware_as_of,
                    max_age_seconds=7 * 24 * 60 * 60,
                )
                self.assertEqual(aware_as_of, plan["as_of"])
                self.assertTrue(plan["plan_id"].startswith("refresh-plan-sha256:"))

    def test_store_snapshot_rejects_malformed_or_future_fetched_at(self):
        seed = self._official_seed("&strict-fetched-at=1")
        for fetched_at in (
            "2026-08-26",
            "2026-08-26T00:00Z",
            "2026-08-26T00:00:00",
            "2999-01-01T00:00:00Z",
        ):
            with self.subTest(fetched_at=fetched_at):
                with self.assertRaises(PublicCorpusError):
                    self.corpus.store_snapshot(
                        seed_id=seed["seed_id"],
                        raw=b"rejected timestamp",
                        content_type="text/html; charset=utf-8",
                        fetched_at=fetched_at,
                        parser_manifest={"parser_version": "2.0"},
                    )
        observation_count = self.corpus.conn.execute(
            "SELECT COUNT(*) AS count FROM observations WHERE seed_id=?",
            (seed["seed_id"],),
        ).fetchone()
        self.assertEqual(0, int(observation_count["count"]))

    def test_refresh_plan_surfaces_legacy_invalid_and_future_observations(self):
        legacy_cases = (
            ("invalid", "2026-08-26T00:00Z", "invalid_fetched_at"),
            ("future", "2026-08-27T00:00:00Z", "future_fetched_at"),
        )
        expected_reasons = {}
        for suffix, fetched_at, expected_reason in legacy_cases:
            snapshot = self._snapshot(
                raw=f"legacy-{suffix}".encode("utf-8"),
                suffix=f"&legacy-{suffix}=1",
                fetched_at="2026-08-01T00:00:00Z",
            )
            with self.corpus.conn:
                self.corpus.conn.execute(
                    "DELETE FROM observations WHERE seed_id=?",
                    (snapshot["seed_id"],),
                )
                self.corpus.conn.execute(
                    """
                    INSERT INTO observations(
                        observation_id, seed_id, snapshot_id, fetched_at,
                        content_type, parser_manifest_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"legacy-observation-{suffix}",
                        snapshot["seed_id"],
                        snapshot["snapshot_id"],
                        fetched_at,
                        "text/html; charset=utf-8",
                        json.dumps({"parser_version": "legacy"}),
                    ),
                )
            expected_reasons[snapshot["seed_id"]] = expected_reason

        plan = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=7 * 24 * 60 * 60,
        )
        self.assertEqual(
            expected_reasons,
            {entry["seed_id"]: entry["reason"] for entry in plan["entries"]},
        )
        self.assertEqual(
            plan,
            self.corpus.plan_refresh(
                as_of="2026-08-26T00:00:00Z",
                max_age_seconds=7 * 24 * 60 * 60,
            ),
        )

    def test_treatment_stays_candidate_until_quote_level_review(self):
        snapshot = self._snapshot()
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Суд применяет правовую позицию Конституционного Суда.",
            document_id="document-chain-1",
            chain_candidate_id="chain-1",
            query_lane="higher_authority",
        )
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
        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                decision="verified",
                reviewer="И.И. Иванов",
                quote="Суд применяет правовую позицию Конституционного Суда",
                locator="абз. 14",
                speaker="court",
                confirmed_target_authority_id="ksrf-32-p-2023",
                target_identity_confirmed=True,
                decision_reason="Этот текст относится только к отклонению.",
                reviewed_at="2026-08-26T00:00:00Z",
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
        )
        self.assertEqual("verified", verified["status"])
        self.assertEqual(1, len(self.corpus.list_treatments(verified_only=True)))

    def test_verified_treatment_review_cannot_be_rewritten(self):
        snapshot = self._snapshot()
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Первоначально проверенная цитата содержится в акте.",
            document_id="document-chain-1",
            chain_candidate_id="chain-1",
            query_lane="higher_authority",
        )
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

    def test_quality_export_binds_complete_treatment_population(self):
        snapshot = self._snapshot(raw=b"treatment population")
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Суд применяет правовую позицию Конституционного Суда.",
            document_id="document-quality-export",
            chain_candidate_id="chain-quality-export",
            query_lane="higher_authority",
        )
        digest_before = self.corpus.evidence_digest()
        candidate = self.corpus.propose_treatment(
            source_chain_id="chain-quality-export",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П", "act_date": "2023-06-15"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.assertNotEqual(digest_before, self.corpus.evidence_digest())
        pending = self.corpus.treatment_quality_export()
        self.assertEqual([candidate["treatment_id"]], pending["treatment_ids"])
        self.assertEqual("candidate", pending["items"][0]["status"])
        self.assertIn("review_pending", pending["items"][0]["quality_blockers"])

        self.corpus.review_treatment(
            candidate["treatment_id"],
            decision="verified",
            reviewer="И.И. Иванов",
            quote="Суд применяет правовую позицию Конституционного Суда",
            locator="абз. 14",
            speaker="court",
            confirmed_target_authority_id="ksrf-32-p-2023",
            target_identity_confirmed=True,
        )
        resolved = self.corpus.treatment_quality_export()
        item = resolved["items"][0]
        self.assertEqual("verified", item["status"])
        self.assertEqual("document-quality-export", item["document_id"])
        self.assertEqual(snapshot["raw_sha256"], item["document_sha256"])
        self.assertTrue(item["official_url"].startswith("https://2kas.sudrf.ru/"))
        self.assertRegex(item["source_binding_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(resolved["treatment_population_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(resolved["set_sha256"], r"^[0-9a-f]{64}$")

        with self.corpus.conn:
            self.corpus.conn.execute(
                "UPDATE seeds SET role='discovery_only' WHERE seed_id=?",
                (snapshot["seed_id"],),
            )
        drifted = self.corpus.treatment_quality_export()["items"][0]
        self.assertEqual("candidate", drifted["status"])
        self.assertIn("official_source_role_missing", drifted["quality_blockers"])

    def test_quality_export_detects_snapshot_and_index_content_tampering(self):
        snapshot = self._snapshot(raw="Проверяемый полный текст.".encode("utf-8"))
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Проверяемый полный текст.",
            document_id="document-integrity",
            chain_candidate_id="chain-integrity",
            query_lane="higher_authority",
        )
        candidate = self.corpus.propose_treatment(
            source_chain_id="chain-integrity",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.corpus.review_treatment(
            candidate["treatment_id"],
            decision="verified",
            reviewer="И.И. Иванов",
            quote="Проверяемый полный текст",
            locator="абз. 1",
            speaker="court",
            confirmed_target_authority_id="ksrf-32-p-2023",
            target_identity_confirmed=True,
        )
        intact_digest = self.corpus.evidence_digest()
        self.assertEqual(
            "verified", self.corpus.treatment_quality_export()["items"][0]["status"]
        )

        Path(snapshot["object_path"]).write_bytes(b"tampered snapshot bytes")
        snapshot_tampered = self.corpus.treatment_quality_export()["items"][0]
        self.assertEqual("candidate", snapshot_tampered["status"])
        self.assertIn(
            "snapshot_object_integrity_invalid",
            snapshot_tampered["quality_blockers"],
        )
        self.assertNotEqual(intact_digest, self.corpus.evidence_digest())

        Path(snapshot["object_path"]).write_bytes("Проверяемый полный текст.".encode("utf-8"))
        restored_digest = self.corpus.evidence_digest()
        with self.corpus.conn:
            self.corpus.conn.execute(
                "UPDATE indexed_texts SET original_text=? WHERE snapshot_id=?",
                ("Подменённый индексированный текст.", snapshot["snapshot_id"]),
            )
        index_tampered = self.corpus.treatment_quality_export()["items"][0]
        self.assertEqual("candidate", index_tampered["status"])
        self.assertIn(
            "indexed_text_integrity_invalid", index_tampered["quality_blockers"]
        )
        self.assertNotEqual(restored_digest, self.corpus.evidence_digest())

    def test_snapshot_integrity_rejects_symlinked_storage_components(self):
        snapshot = self._snapshot(raw=b"symlink containment")
        object_path = Path(snapshot["object_path"])
        prefix_directory = object_path.parent
        external_prefix = self.root / "external-prefix"
        prefix_directory.rename(external_prefix)
        prefix_directory.symlink_to(external_prefix, target_is_directory=True)
        self.assertFalse(
            self.corpus._snapshot_integrity(snapshot["snapshot_id"])["valid"]
        )

    def test_snapshot_integrity_rejects_symlinked_objects_directory(self):
        snapshot = self._snapshot(raw=b"symlink objects")
        objects_directory = self.root / "objects"
        external_objects = self.root / "external-objects"
        objects_directory.rename(external_objects)
        objects_directory.symlink_to(external_objects, target_is_directory=True)
        self.assertFalse(
            self.corpus._snapshot_integrity(snapshot["snapshot_id"])["valid"]
        )

    def test_treatment_review_rejects_corrupt_source_before_decision(self):
        snapshot = self._snapshot(raw=b"source before decision")
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Источник до решения.",
            document_id="document-before-decision",
            chain_candidate_id="chain-before-decision",
            query_lane="higher_authority",
        )
        candidate = self.corpus.propose_treatment(
            source_chain_id="chain-before-decision",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        Path(snapshot["object_path"]).write_bytes(b"corrupt")
        with self.assertRaisesRegex(TreatmentReviewError, "intact"):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                decision="verified",
                reviewer="И.И. Иванов",
                quote="Источник до решения",
                locator="абз. 1",
                speaker="court",
                confirmed_target_authority_id="ksrf-32-p-2023",
                target_identity_confirmed=True,
                reviewed_at="2026-08-26T00:00:00Z",
            )

    def test_concurrent_treatment_review_has_exactly_one_decision(self):
        snapshot = self._snapshot(raw=b"concurrent review")
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Конкурентная проверка полного текста.",
            document_id="document-concurrent",
            chain_candidate_id="chain-concurrent",
            query_lane="higher_authority",
        )
        candidate = self.corpus.propose_treatment(
            source_chain_id="chain-concurrent",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        barrier = threading.Barrier(2)
        results: list[str] = []
        results_lock = threading.Lock()

        def review(reviewer: str) -> None:
            try:
                with PublicCorpus(self.root) as corpus:
                    barrier.wait(timeout=5)
                    corpus.review_treatment(
                        candidate["treatment_id"],
                        decision="verified",
                        reviewer=reviewer,
                        quote="Конкурентная проверка полного текста",
                        locator="абз. 1",
                        speaker="court",
                        confirmed_target_authority_id="ksrf-32-p-2023",
                        target_identity_confirmed=True,
                    )
            except Exception as exc:
                outcome = f"error:{type(exc).__name__}"
            else:
                outcome = "success"
            with results_lock:
                results.append(outcome)

        workers = [
            threading.Thread(target=review, args=(reviewer,))
            for reviewer in ("И.И. Иванов", "П.П. Петров")
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=10)
        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertEqual(1, results.count("success"), results)
        history = self.corpus.treatment_history(candidate["treatment_id"])
        self.assertEqual(2, len(history))
        self.assertEqual("candidate_created", history[0]["event_type"])
        self.assertEqual("verified", history[1]["event_type"])

    def test_quality_export_keeps_orphan_treatment_visible(self):
        snapshot_id = f"snapshot-sha256:{'f' * 64}"
        treatment_id = "treatment-orphan"
        created_at = "2026-08-26T00:00:00Z"
        self.corpus.conn.execute("PRAGMA foreign_keys=OFF")
        with self.corpus.conn:
            self.corpus.conn.execute(
                """
                INSERT INTO treatments(
                    treatment_id, source_chain_id, source_court_id,
                    target_authority_id, target_kind, target_identity_json,
                    treatment_type, snapshot_id, supersedes_treatment_id,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 'candidate', ?)
                """,
                (
                    treatment_id,
                    "chain-orphan",
                    "2kas",
                    "ksrf-32-p-2023",
                    "constitutional_court_act",
                    json.dumps({"act_number": "32-П"}, ensure_ascii=False),
                    "applies",
                    snapshot_id,
                    created_at,
                ),
            )
        exported = self.corpus.treatment_quality_export()
        self.assertEqual([treatment_id], exported["treatment_ids"])
        self.assertEqual("candidate", exported["items"][0]["status"])
        self.assertIn("snapshot_missing", exported["items"][0]["quality_blockers"])

    def test_orphan_review_history_blocks_live_binding(self):
        self.corpus.conn.execute("PRAGMA foreign_keys=OFF")
        with self.corpus.conn:
            self.corpus.conn.execute(
                """
                INSERT INTO treatment_review_history(
                    history_id, treatment_id, event_type, reviewer,
                    payload_json, event_at
                ) VALUES (?, ?, ?, NULL, ?, ?)
                """,
                (
                    "history-orphan",
                    "treatment-missing",
                    "candidate_created",
                    "{}",
                    "2026-08-26T00:00:00Z",
                ),
            )
        plan = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=604800,
            coverage_requirements=[{"court_id": "missing-court"}],
        )
        treatment_set = self.corpus.treatment_quality_export()
        self.assertTrue(treatment_set["integrity_issue_ids"])
        binding = self.corpus.verify_prefiling_inputs(
            refresh_plan=plan,
            treatment_set=treatment_set,
            current_corpus_digest=str(plan["evidence_digest"]).removeprefix(
                "corpus-evidence-sha256:"
            ),
        )
        self.assertFalse(binding["verified"])
        self.assertIn("live_cache_integrity_invalid", binding["issue_ids"])

    def test_rejected_treatment_requires_reason_and_exports_as_resolved(self):
        snapshot = self._snapshot(raw=b"rejected treatment")
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Полный текст проверен, но заявленная связь не подтверждена.",
            document_id="document-rejected",
            chain_candidate_id="chain-rejected",
            query_lane="higher_authority",
        )
        candidate = self.corpus.propose_treatment(
            source_chain_id="chain-rejected",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                decision="rejected",
                reviewer="И.И. Иванов",
                reviewed_at="2026-08-26T00:00:00Z",
            )
        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                decision="rejected",
                reviewer="И.И. Иванов",
                locator="абз. 2",
                speaker="court",
                decision_reason="Полный текст не подтверждает заявленное отношение.",
                reviewed_at="2026-08-26T00:00:00Z",
            )
        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                decision="rejected",
                reviewer="И.И. Иванов",
                confirmed_target_authority_id="другой-акт",
                target_identity_confirmed=True,
                decision_reason="Полный текст не подтверждает заявленное отношение.",
                reviewed_at="2026-08-26T00:00:00Z",
            )
        self.corpus.review_treatment(
            candidate["treatment_id"],
            decision="rejected",
            reviewer="И.И. Иванов",
            decision_reason="Полный текст не подтверждает заявленное отношение.",
        )
        exported = self.corpus.treatment_quality_export()["items"][0]
        self.assertEqual("rejected", exported["status"])
        self.assertEqual(
            "Полный текст не подтверждает заявленное отношение.",
            exported["decision_reason"],
        )
        self.assertIn("Проверяющий отклонил", exported["proposition"])
        self.assertNotIn("содержит проверенное отношение", exported["proposition"])
        self.assertIs(exported["quote_verified"], False)

    def test_treatment_review_rejects_reduced_or_future_timestamps(self):
        snapshot = self._snapshot(raw=b"timestamp treatment")
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Суд применяет правовую позицию.",
            document_id="document-time",
            chain_candidate_id="chain-time",
            query_lane="higher_authority",
        )
        candidate = self.corpus.propose_treatment(
            source_chain_id="chain-time",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        for reviewed_at in ("2026-08-26T00:00Z", "2026-08-26T00:00:00", "2099-01-01T00:00:00Z"):
            with self.subTest(reviewed_at=reviewed_at), self.assertRaises(
                TreatmentReviewError
            ):
                self.corpus.review_treatment(
                    candidate["treatment_id"],
                    decision="verified",
                    reviewer="И.И. Иванов",
                    quote="Суд применяет правовую позицию",
                    locator="абз. 1",
                    speaker="court",
                    confirmed_target_authority_id="ksrf-32-p-2023",
                    target_identity_confirmed=True,
                    reviewed_at=reviewed_at,
                )

    def test_supersession_is_effective_and_single_successor(self):
        snapshot = self._snapshot(raw=b"supersession full text")
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Суд применяет правовую позицию. Суд уточняет правовую позицию.",
            document_id="document-supersession",
            chain_candidate_id="chain-supersession",
            query_lane="higher_authority",
        )
        first = self.corpus.propose_treatment(
            source_chain_id="chain-supersession",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.corpus.review_treatment(
            first["treatment_id"],
            decision="verified",
            reviewer="И.И. Иванов",
            quote="Суд применяет правовую позицию",
            locator="абз. 1",
            speaker="court",
            confirmed_target_authority_id="ksrf-32-p-2023",
            target_identity_confirmed=True,
        )
        replacement = self.corpus.propose_treatment(
            source_chain_id="chain-supersession",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="limits",
            snapshot_id=snapshot["snapshot_id"],
            supersedes_treatment_id=first["treatment_id"],
        )
        pending = {
            item["treatment_id"]: item
            for item in self.corpus.treatment_quality_export()["items"]
        }
        self.assertEqual("superseded", pending[first["treatment_id"]]["status"])
        self.assertEqual(
            replacement["treatment_id"],
            pending[first["treatment_id"]]["superseded_by_treatment_id"],
        )
        self.assertEqual("candidate", pending[replacement["treatment_id"]]["status"])
        self.assertEqual(
            first["treatment_id"],
            pending[replacement["treatment_id"]]["supersedes_treatment_id"],
        )
        self.assertEqual([], self.corpus.list_treatments(verified_only=True))

        with self.assertRaisesRegex(TreatmentReviewError, "replacement"):
            self.corpus.propose_treatment(
                source_chain_id="chain-supersession",
                source_court_id="2kas",
                target_authority_id="ksrf-32-p-2023",
                target_kind="constitutional_court_act",
                target_identity={"act_number": "32-П"},
                treatment_type="distinguishes",
                snapshot_id=snapshot["snapshot_id"],
                supersedes_treatment_id=first["treatment_id"],
            )

        self.corpus.review_treatment(
            replacement["treatment_id"],
            decision="verified",
            reviewer="П.П. Петров",
            quote="Суд уточняет правовую позицию",
            locator="абз. 2",
            speaker="court",
            confirmed_target_authority_id="ksrf-32-p-2023",
            target_identity_confirmed=True,
        )
        resolved = {
            item["treatment_id"]: item
            for item in self.corpus.treatment_quality_export()["items"]
        }
        self.assertEqual("superseded", resolved[first["treatment_id"]]["status"])
        self.assertEqual("verified", resolved[replacement["treatment_id"]]["status"])
        active = self.corpus.list_treatments(verified_only=True)
        self.assertEqual([replacement["treatment_id"]], [item["treatment_id"] for item in active])
        self.assertEqual("verified", active[0]["review_decision"])

    def test_treatment_review_rejects_precreation_empty_time_and_nan_identity(self):
        snapshot = self._snapshot(raw=b"chronology full text")
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Суд применяет правовую позицию.",
            document_id="document-chronology",
            chain_candidate_id="chain-chronology",
            query_lane="higher_authority",
        )
        with self.assertRaises(TreatmentReviewError):
            self.corpus.propose_treatment(
                source_chain_id="chain-chronology",
                source_court_id="2kas",
                target_authority_id="ksrf-32-p-2023",
                target_kind="constitutional_court_act",
                target_identity={"invalid": float("nan")},
                treatment_type="applies",
                snapshot_id=snapshot["snapshot_id"],
            )
        candidate = self.corpus.propose_treatment(
            source_chain_id="chain-chronology",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        for reviewed_at in ("", "2000-01-01T00:00:00Z"):
            with self.subTest(reviewed_at=reviewed_at), self.assertRaises(
                TreatmentReviewError
            ):
                self.corpus.review_treatment(
                    candidate["treatment_id"],
                    decision="verified",
                    reviewer="И.И. Иванов",
                    quote="Суд применяет правовую позицию",
                    locator="абз. 1",
                    speaker="court",
                    confirmed_target_authority_id="ksrf-32-p-2023",
                    target_identity_confirmed=True,
                    reviewed_at=reviewed_at,
                )
        self.assertEqual(
            ["candidate_created"],
            [item["event_type"] for item in self.corpus.treatment_history(candidate["treatment_id"])],
        )

    def test_legacy_branched_supersession_reopens_and_quality_export_fails_closed(self):
        snapshot = self._snapshot(
            raw="Исходная позиция. Уточнённая позиция.".encode("utf-8")
        )
        self.corpus.index_text(
            snapshot["snapshot_id"],
            "Исходная позиция. Уточнённая позиция.",
            document_id="document-legacy-branch",
            chain_candidate_id="chain-legacy-branch",
            query_lane="higher_authority",
        )
        first = self.corpus.propose_treatment(
            source_chain_id="chain-legacy-branch",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="applies",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.corpus.review_treatment(
            first["treatment_id"],
            decision="verified",
            reviewer="И.И. Иванов",
            quote="Исходная позиция",
            locator="абз. 1",
            speaker="court",
            confirmed_target_authority_id="ksrf-32-p-2023",
            target_identity_confirmed=True,
        )
        replacement = self.corpus.propose_treatment(
            source_chain_id="chain-legacy-branch",
            source_court_id="2kas",
            target_authority_id="ksrf-32-p-2023",
            target_kind="constitutional_court_act",
            target_identity={"act_number": "32-П"},
            treatment_type="limits",
            snapshot_id=snapshot["snapshot_id"],
            supersedes_treatment_id=first["treatment_id"],
        )
        legacy_replacement_id = "treatment-legacy-second-successor"
        with self.corpus.conn:
            self.corpus.conn.execute(
                "DROP INDEX idx_treatments_one_replacement"
            )
            self.corpus.conn.execute(
                """
                INSERT INTO treatments(
                    treatment_id, source_chain_id, source_court_id,
                    target_authority_id, target_kind, target_identity_json,
                    treatment_type, snapshot_id, supersedes_treatment_id,
                    status, reviewer, quote, locator, speaker, created_at,
                    reviewed_at
                )
                SELECT ?, source_chain_id, source_court_id,
                       target_authority_id, target_kind, target_identity_json,
                       'distinguishes', snapshot_id, supersedes_treatment_id,
                       status, reviewer, quote, locator, speaker, created_at,
                       reviewed_at
                FROM treatments WHERE treatment_id=?
                """,
                (legacy_replacement_id, replacement["treatment_id"]),
            )

        self.corpus.close()
        with PublicCorpus(self.root) as reopened:
            self.assertIsNone(
                reopened.conn.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name='idx_treatments_one_replacement'
                    """
                ).fetchone()
            )
            exported = reopened.treatment_quality_export()

        by_id = {item["treatment_id"]: item for item in exported["items"]}
        self.assertEqual(
            {
                first["treatment_id"],
                replacement["treatment_id"],
                legacy_replacement_id,
            },
            set(by_id),
        )
        for treatment_id in by_id:
            with self.subTest(treatment_id=treatment_id):
                self.assertEqual("candidate", by_id[treatment_id]["status"])
                self.assertIn(
                    "supersession_branch_invalid",
                    by_id[treatment_id]["quality_blockers"],
                )

    def test_quality_export_downgrades_tampered_candidate_and_review_history_ids(self):
        treatment = self._verified_treatment()
        history_rows = self.corpus.conn.execute(
            """
            SELECT rowid AS history_rowid, history_id, event_type
            FROM treatment_review_history
            WHERE treatment_id=? ORDER BY rowid
            """,
            (treatment["treatment_id"],),
        ).fetchall()
        cases = (
            (history_rows[0], "review_history_cardinality_invalid"),
            (history_rows[1], "review_history_binding_invalid"),
        )
        for row, expected_blocker in cases:
            with self.subTest(event_type=row["event_type"]):
                with self.corpus.conn:
                    self.corpus.conn.execute(
                        """
                        UPDATE treatment_review_history SET history_id=?
                        WHERE rowid=?
                        """,
                        (
                            f"history-tampered-{row['event_type']}",
                            row["history_rowid"],
                        ),
                    )
                item = self.corpus.treatment_quality_export()["items"][0]
                self.assertEqual("candidate", item["status"])
                self.assertEqual("verified", item["recorded_status"])
                self.assertIn(expected_blocker, item["quality_blockers"])
                with self.corpus.conn:
                    self.corpus.conn.execute(
                        """
                        UPDATE treatment_review_history SET history_id=?
                        WHERE rowid=?
                        """,
                        (row["history_id"], row["history_rowid"]),
                    )
                self.assertEqual(
                    "verified",
                    self.corpus.treatment_quality_export()["items"][0]["status"],
                )

    def test_quality_export_downgrades_verified_decision_with_rejection_reason(self):
        treatment = self._verified_treatment()
        decision = self.corpus.conn.execute(
            """
            SELECT rowid AS history_rowid, reviewer, payload_json, event_at
            FROM treatment_review_history
            WHERE treatment_id=? AND event_type='verified'
            """,
            (treatment["treatment_id"],),
        ).fetchone()
        payload = json.loads(decision["payload_json"])
        payload["decision_reason"] = "Эта связь должна была быть отклонена."
        tampered_history_id = _identifier(
            "treatment-history",
            {
                "treatment_id": treatment["treatment_id"],
                "event_type": "verified",
                "reviewer": decision["reviewer"],
                "payload": payload,
                "event_at": decision["event_at"],
            },
        )
        with self.corpus.conn:
            self.corpus.conn.execute(
                """
                UPDATE treatment_review_history
                SET history_id=?, payload_json=? WHERE rowid=?
                """,
                (
                    tampered_history_id,
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    decision["history_rowid"],
                ),
            )

        item = self.corpus.treatment_quality_export()["items"][0]
        self.assertEqual("candidate", item["status"])
        self.assertEqual("verified", item["recorded_status"])
        self.assertIn(
            "verified_decision_reason_invalid",
            item["quality_blockers"],
        )

    def test_evidence_digest_binds_seed_snapshot_relation_not_refetch_metadata(self):
        first = self._snapshot(raw=b"stable bytes")
        digest = self.corpus.evidence_digest()
        self.corpus.store_snapshot(
            seed_id=first["seed_id"],
            raw=b"stable bytes",
            content_type="application/octet-stream",
            fetched_at="2026-08-02T00:00:00Z",
            parser_manifest={"parser_version": "different"},
        )
        self.assertEqual(digest, self.corpus.evidence_digest())
        second_seed = self.corpus.register_seed(
            url="https://ksrf.ru/ru/Decision/Pages/default.aspx?stable=1",
            role="official_authority_seed",
            public=True,
        )
        self.corpus.store_snapshot(
            seed_id=second_seed["seed_id"],
            raw=b"stable bytes",
            content_type="application/octet-stream",
            fetched_at="2026-08-03T00:00:00Z",
            parser_manifest={"parser_version": "different"},
        )
        self.assertNotEqual(digest, self.corpus.evidence_digest())

    def test_read_only_binding_rechecks_static_store_sidecars(self):
        plan = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=0,
            coverage_requirements=[{"court_id": "2kas"}],
        )
        treatment_set = self.corpus.treatment_quality_export()
        current_digest = self.corpus.evidence_digest().removeprefix(
            "corpus-evidence-sha256:"
        )
        self.corpus.close()
        with PublicCorpus.open_read_only(self.root) as read_only:
            Path(str(self.root / "public-corpus.sqlite3") + "-journal").write_bytes(b"")
            binding = read_only.verify_prefiling_inputs(
                refresh_plan=plan,
                treatment_set=treatment_set,
                current_corpus_digest=current_digest,
            )
        self.assertIs(binding["verified"], False)
        self.assertIs(binding["live_cache_stable"], False)
        self.assertIn("live_cache_journal_present", binding["issue_ids"])

    def test_read_only_binding_rechecks_static_store_after_transaction(self):
        plan = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=0,
            coverage_requirements=[{"court_id": "2kas"}],
        )
        treatment_set = self.corpus.treatment_quality_export()
        current_digest = self.corpus.evidence_digest().removeprefix(
            "corpus-evidence-sha256:"
        )
        self.corpus.close()
        with PublicCorpus.open_read_only(self.root) as read_only:
            transaction_states = []
            original_check = read_only._read_only_store_issue_ids

            def observed_check():
                transaction_states.append(read_only.conn.in_transaction)
                return original_check()

            with patch.object(
                read_only,
                "_read_only_store_issue_ids",
                side_effect=observed_check,
            ):
                binding = read_only.verify_prefiling_inputs(
                    refresh_plan=plan,
                    treatment_set=treatment_set,
                    current_corpus_digest=current_digest,
                )
        self.assertIs(binding["verified"], True)
        self.assertIs(transaction_states[0], False)
        self.assertIn(True, transaction_states[1:-1])
        self.assertIs(transaction_states[-1], False)

    def test_read_only_binding_refuses_a_caller_owned_transaction(self):
        plan = self.corpus.plan_refresh(
            as_of="2026-08-26T00:00:00Z",
            max_age_seconds=0,
            coverage_requirements=[{"court_id": "2kas"}],
        )
        treatment_set = self.corpus.treatment_quality_export()
        current_digest = self.corpus.evidence_digest().removeprefix(
            "corpus-evidence-sha256:"
        )
        self.corpus.close()
        with PublicCorpus.open_read_only(self.root) as read_only:
            read_only.conn.execute("BEGIN")
            try:
                with self.assertRaisesRegex(
                    PublicCorpusError,
                    "ownership of its read transaction",
                ):
                    read_only.verify_prefiling_inputs(
                        refresh_plan=plan,
                        treatment_set=treatment_set,
                        current_corpus_digest=current_digest,
                    )
            finally:
                read_only.conn.rollback()


if __name__ == "__main__":
    unittest.main()
