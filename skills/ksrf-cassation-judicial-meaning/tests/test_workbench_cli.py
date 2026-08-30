import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from judicial_meaning.cli import (
    _approval_evidence_sha256,
    _build_reviewed_handoff_payload,
    _default_report_model,
    _validation_state,
    main,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)
from judicial_meaning.handoff_workbench import (
    artifact_sha256,
    bind_request_payload,
    create_handoff,
)


class WorkbenchCliTests(unittest.TestCase):
    def run_cli(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    @staticmethod
    def answers(value="ежемесячная премия"):
        return {
            "issue": "Допустимые пределы снижения премии",
            "norm_refs": ["ст. 135 ТК РФ"],
            "features": [
                {
                    "feature_id": "payment_kind",
                    "value": value,
                    "status": "verified",
                    "material": True,
                    "source": {
                        "document_id": "applicant-cassation",
                        "quote_locator": "абзац 12",
                    },
                    "query_terms": [value],
                }
            ],
        }

    @staticmethod
    def position_card():
        return {
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
            "adverse_buckets": ["opposite_reading"],
        }

    @staticmethod
    def seed_applicant_intake(workspace):
        record = {
            "document_id": "applicant-cassation",
            "sha256": "1" * 64,
            "extraction_status": "extracted",
            "role": "applicant_judicial_act",
        }
        write_json(
            workspace / "applicant-chain.json",
            {"documents": [record["document_id"]]},
        )
        from judicial_meaning.cli import write_jsonl

        write_jsonl(workspace / "intake" / "applicant-manifest.jsonl", [record])
        write_jsonl(
            workspace / "intake" / "applicant-private.jsonl",
            [{**record, "text": "Суд исследовал порядок начисления премии."}],
        )

    @classmethod
    def complete_answers(cls):
        source = {
            "document_id": "applicant-cassation",
            "quote_locator": "абзац 12",
        }
        return {
            "issue": "Допустимые пределы снижения премии",
            "norm_refs": ["ст. 135 ТК РФ"],
            "features": [
                {
                    "feature_id": "norm_edition",
                    "value": "редакция на дату спорной выплаты",
                    "status": "verified",
                    "material": True,
                    "source": source,
                    "query_terms": [],
                },
                {
                    "feature_id": "applicant_case_meaning",
                    "value": "суд допустил снижение без проверяемого критерия",
                    "status": "verified",
                    "material": True,
                    "source": source,
                    "query_terms": ["снижение премии без критерия"],
                },
                {
                    "feature_id": "procedural_posture",
                    "value": "кассация оставила отказ в иске без изменения",
                    "status": "verified",
                    "material": True,
                    "source": source,
                    "query_terms": [],
                },
            ],
        }

    def test_case_prepare_is_noninteractive_fail_closed_and_persists_versioned_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            code, _, stderr = self.run_cli(["case", "prepare", "--workspace", str(workspace)])
            self.assertEqual(2, code)
            self.assertIn("--answers", stderr)

            answers = Path(tmp) / "answers.json"
            self.seed_applicant_intake(workspace)
            write_json(answers, self.answers())
            code, stdout, stderr = self.run_cli(
                ["case", "prepare", "--workspace", str(workspace), "--answers", str(answers)]
            )
            self.assertEqual(0, code, stderr)
            summary = json.loads(stdout)
            self.assertEqual(1, summary["fingerprint_revision"])
            self.assertEqual(1, read_json(workspace / "case-fingerprint.json")["revision"])
            self.assertTrue(read_jsonl(workspace / "query-suggestions.jsonl"))
            self.assertTrue((workspace / "casework-dependencies.json").exists())
            version_one = workspace / "casework" / "fingerprints" / "fingerprint-v1.json"
            self.assertTrue(version_one.exists())
            version_one_sha = read_json(version_one)["fingerprint_sha256"]

            write_json(answers, self.answers("квартальная премия"))
            code, stdout, stderr = self.run_cli(
                ["case", "prepare", "--workspace", str(workspace), "--answers", str(answers)]
            )
            self.assertEqual(0, code, stderr)
            summary = json.loads(stdout)
            self.assertEqual(2, summary["fingerprint_revision"])
            self.assertTrue(summary["applicant_relative_evidence_stale"])
            self.assertTrue((workspace / "casework" / "fingerprints" / "fingerprint-v2.json").exists())
            self.assertEqual(version_one_sha, read_json(version_one)["fingerprint_sha256"])

    def test_query_confirmation_enters_frozen_hash_and_supplement_stays_outside_denominator(self):
        from tests.test_intake_and_plan import complete_plan

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "matter"
            self.seed_applicant_intake(workspace)
            answers = root / "answers.json"
            write_json(answers, self.answers())
            code, _, stderr = self.run_cli(
                ["case", "prepare", "--workspace", str(workspace), "--answers", str(answers)]
            )
            self.assertEqual(0, code, stderr)
            suggestion = read_jsonl(workspace / "query-suggestions.jsonl")[0]
            code, stdout, stderr = self.run_cli(
                [
                    "query",
                    "accept",
                    "--workspace",
                    str(workspace),
                    "--query-id",
                    suggestion["query_id"],
                    "--reviewer",
                    "И.И. Иванов",
                    "--confirmed-at",
                    "2026-08-27T09:00:00Z",
                ]
            )
            self.assertEqual(0, code, stderr)
            self.assertEqual(
                [suggestion["query_id"]], json.loads(stdout)["accepted_query_ids"]
            )

            plan_path = root / "plan.json"
            write_json(plan_path, complete_plan())
            code, stdout, stderr = self.run_cli(
                [
                    "plan",
                    "freeze",
                    "--workspace",
                    str(workspace),
                    "--plan",
                    str(plan_path),
                ]
            )
            self.assertEqual(0, code, stderr)
            frozen = read_json(workspace / "plans" / "plan-v1.json")
            original_plan_sha256 = frozen["plan_sha256"]
            self.assertEqual(
                suggestion["query_id"],
                frozen["accepted_query_suggestions"][0]["query_id"],
            )
            frozen_query = next(
                item
                for item in read_jsonl(workspace / "queries.jsonl")
                if item.get("query_id") == suggestion["query_id"]
            )
            self.assertEqual("accepted_pre_freeze", frozen_query["plan_relationship"])
            self.assertEqual(suggestion["provenance"], frozen_query["provenance"])

            code, stdout, stderr = self.run_cli(
                [
                    "query",
                    "supplement",
                    "--workspace",
                    str(workspace),
                    "--lane",
                    "narrower_reading",
                    "--query",
                    "более узкое толкование премии",
                    "--reason",
                    "обнаружена новая формулировка суда после freeze",
                    "--reviewer",
                    "И.И. Иванов",
                    "--confirmed-at",
                    "2026-08-27T10:00:00Z",
                ]
            )
            self.assertEqual(0, code, stderr)
            supplemental = json.loads(stdout)
            self.assertEqual("post_freeze_supplemental", supplemental["plan_relationship"])
            self.assertFalse(supplemental["changes_original_denominator"])
            self.assertEqual(
                original_plan_sha256,
                read_json(workspace / "plans" / "plan-v1.json")["plan_sha256"],
            )

            code, _, stderr = self.run_cli(
                [
                    "query",
                    "accept",
                    "--workspace",
                    str(workspace),
                    "--query-id",
                    suggestion["query_id"],
                    "--reviewer",
                    "И.И. Иванов",
                    "--confirmed-at",
                    "2026-08-27T10:05:00Z",
                ]
            )
            self.assertEqual(2, code)
            self.assertIn("уже заморожен", stderr.lower())

    def test_query_accept_rejects_non_object_fingerprint_without_traceback_or_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            write_json(workspace / "case-fingerprint.json", [])
            write_jsonl(
                workspace / "query-suggestions.jsonl",
                [{"query_id": "q1"}],
            )

            code, stdout, stderr = self.run_cli(
                [
                    "query",
                    "accept",
                    "--workspace",
                    str(workspace),
                    "--query-id",
                    "q1",
                    "--reviewer",
                    "reviewer",
                    "--confirmed-at",
                    "2026-08-30T12:00:00Z",
                ]
            )

            self.assertEqual(2, code)
            self.assertEqual("", stdout)
            self.assertIn("case-fingerprint.json", stderr)
            self.assertIn("JSON-объектом", stderr)
            self.assertNotIn("Traceback", stderr)
            self.assertFalse((workspace / "query-decisions.jsonl").exists())

    def test_plan_freeze_rejects_non_object_fingerprint_without_traceback_or_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "matter"
            write_json(workspace / "case-fingerprint.json", [])
            write_jsonl(workspace / "query-decisions.jsonl", [{}])
            plan_path = root / "draft-plan.json"
            write_json(plan_path, {})

            code, stdout, stderr = self.run_cli(
                [
                    "plan",
                    "freeze",
                    "--workspace",
                    str(workspace),
                    "--plan",
                    str(plan_path),
                ]
            )

            self.assertEqual(2, code)
            self.assertEqual("", stdout)
            self.assertIn("case-fingerprint.json", stderr)
            self.assertIn("JSON-объектом", stderr)
            self.assertNotIn("Traceback", stderr)
            self.assertFalse((workspace / "plans" / "plan-v1.json").exists())

    def test_query_supplement_rejects_non_object_fingerprint_without_traceback_or_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            (workspace / "plans").mkdir(parents=True)
            write_json(
                workspace / "plans" / "plan-v1.json",
                {"plan_sha256": "a" * 64},
            )
            write_json(workspace / "case-fingerprint.json", [])
            supplemental = workspace / "supplemental-queries.jsonl"
            queries = workspace / "queries.jsonl"
            supplemental.write_text("existing-supplement\n", encoding="utf-8")
            queries.write_text("existing-query\n", encoding="utf-8")
            original_supplemental = supplemental.read_bytes()
            original_queries = queries.read_bytes()

            code, stdout, stderr = self.run_cli(
                [
                    "query",
                    "supplement",
                    "--workspace",
                    str(workspace),
                    "--lane",
                    "exact_norm",
                    "--query",
                    "test query",
                    "--reason",
                    "test reason",
                    "--reviewer",
                    "reviewer",
                    "--confirmed-at",
                    "2026-08-30T12:00:00Z",
                ]
            )

            self.assertEqual(2, code)
            self.assertEqual("", stdout)
            self.assertIn("case-fingerprint.json", stderr)
            self.assertIn("JSON-объектом", stderr)
            self.assertNotIn("Traceback", stderr)
            self.assertEqual(original_supplemental, supplemental.read_bytes())
            self.assertEqual(original_queries, queries.read_bytes())

    def test_fingerprint_readiness_recomputes_hash_core_fields_and_intake_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "matter"
            (workspace / "plans").mkdir(parents=True)
            write_json(
                workspace / "plans" / "plan-v1.json",
                {"frozen": True, "plan_sha256": "a" * 64},
            )
            self.seed_applicant_intake(workspace)
            answers = root / "answers.json"
            write_json(answers, self.complete_answers())
            code, _, stderr = self.run_cli(
                ["case", "prepare", "--workspace", str(workspace), "--answers", str(answers)]
            )
            self.assertEqual(0, code, stderr)
            self.assertTrue(_validation_state(workspace)["case_fingerprint_ready"])

            fingerprint = read_json(workspace / "case-fingerprint.json")
            fingerprint["issue"] = "подменённый вопрос"
            write_json(workspace / "case-fingerprint.json", fingerprint)
            self.assertFalse(_validation_state(workspace)["case_fingerprint_ready"])

    def test_approval_evidence_digest_binds_file_boundaries_and_missing_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            workspace.mkdir()
            analysis = workspace / "analysis.json"
            screening = workspace / "screening-candidates.jsonl"
            analysis.write_bytes(b"a")
            screening.write_bytes(b"bc")
            first = _approval_evidence_sha256(workspace)

            analysis.write_bytes(b"ab")
            screening.write_bytes(b"c")
            second = _approval_evidence_sha256(workspace)
            self.assertNotEqual(first, second)

            screening.unlink()
            missing = _approval_evidence_sha256(workspace)
            screening.write_bytes(b"")
            empty = _approval_evidence_sha256(workspace)
            self.assertNotEqual(missing, empty)

    def test_case_relative_review_commands_are_explainable_and_persist_when_workspace_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "matter"
            (workspace / "plans").mkdir(parents=True)
            write_json(
                workspace / "plans" / "plan-v1.json",
                {
                    "frozen": True,
                    "plan_sha256": "9" * 64,
                    "maximum_claim_if_incomplete": "unproven_research_question",
                },
            )
            card_path = root / "card.json"
            applicant_path = root / "applicant.json"
            candidate_path = root / "candidate.json"
            candidates_path = root / "candidates.json"
            resolutions_path = root / "resolutions.json"
            quotas_path = root / "quotas.json"
            bridge_path = root / "bridge.json"
            applicant_position_path = root / "applicant-position.json"
            adverse_queries_path = root / "adverse-queries.json"
            adverse_unresolved_path = root / "adverse-unresolved.json"
            adverse_effects_path = root / "adverse-effects.json"
            write_json(
                workspace / "case-fingerprint.json",
                {"revision": 1, "fingerprint_sha256": "f" * 64, "features": self.answers()["features"]},
            )
            write_json(card_path, self.position_card())
            write_json(applicant_path, self.answers()["features"])
            write_json(candidate_path, self.position_card()["comparison_features"])
            write_json(
                applicant_position_path,
                {
                    "supportive_reading_families": ["wage_component"],
                    "adverse_reading_families": ["employer_discretion"],
                    "human_review": "approved",
                },
            )
            write_json(
                candidates_path,
                [{
                    "candidate_id": "candidate-1", "chain_id": "chain-1", "document_id": "document-1",
                    "court_id": "2kas", "stratum_id": "post-event", "lane": "exact_norm",
                }],
            )
            write_json(
                quotas_path,
                {"court_id": {"2kas": 1}, "stratum_id": {"post-event": 1}, "lane": {"exact_norm": 1}},
            )
            write_json(
                resolutions_path,
                {
                    "candidate-1": {
                        "decision": "position_card",
                        "position_card_id": "position-1",
                        "reason": "Полный текст проверен.",
                    }
                },
            )
            write_json(
                bridge_path,
                {
                    "norm_ref": "ст. 135 ТК РФ",
                    "applicant_case_meaning": "Премия снижена без проверяемого критерия.",
                    "corpus_observation": "В сопоставимых делах выявлены два раскрытых прочтения.",
                    "constitutional_consequence": "Право на вознаграждение становится непредсказуемым.",
                    "ordinary_remedy_analysis": "Обычная проверка не устранила неопределённость смысла.",
                    "supporting_position_card_ids": ["position-1"],
                    "adverse_position_card_ids": [],
                    "fingerprint_sha256": "f" * 64,
                    "maximum_permitted_claim": "unproven_research_question",
                    "claim_wording": "В раскрытом сопоставимом корпусе наблюдается одна проверенная позиция.",
                    "reviewer": "И.И. Иванов",
                    "reviewed_at": "2026-08-26T00:10:00Z",
                    "human_review": "approved",
                },
            )
            write_json(
                adverse_queries_path,
                {bucket: [f"query-{bucket}"] for bucket in ("opposite_reading", "narrower_reading", "alternative_ground", "later_authority")},
            )
            write_json(
                adverse_unresolved_path,
                {bucket: [] for bucket in ("opposite_reading", "narrower_reading", "alternative_ground", "later_authority")},
            )
            write_json(
                adverse_effects_path,
                {bucket: "Только раскрытый корпус." for bucket in ("opposite_reading", "narrower_reading", "alternative_ground", "later_authority")},
            )

            commands = [
                (["position", "check", "--input", str(card_path), "--workspace", str(workspace)], "valid", True),
                (["compare", "--applicant", str(applicant_path), "--candidate", str(candidate_path), "--workspace", str(workspace), "--reviewer", "И.И. Иванов", "--reviewed-at", "2026-08-26T00:00:00Z"], "status", "matched"),
                (["relation", "classify", "--position-card", str(card_path), "--comparison", str(workspace / "case-comparison.json"), "--applicant-position", str(applicant_position_path), "--workspace", str(workspace), "--reviewer", "И.И. Иванов", "--reviewed-at", "2026-08-26T00:05:00Z"], "relation", "supports"),
                (["case", "dynamics", "--workspace", str(workspace)], "temporal_analysis_complete", True),
                (["queue", "build", "--candidates", str(candidates_path), "--resolutions", str(resolutions_path), "--quotas", str(quotas_path), "--workspace", str(workspace)], "all_candidates_preserved", True),
                (["adverse", "build", "--cards", str(card_path), "--completed-buckets", "opposite_reading", "narrower_reading", "alternative_ground", "later_authority", "--searched-buckets", "opposite_reading", "narrower_reading", "alternative_ground", "later_authority", "--executed-query-ids", str(adverse_queries_path), "--unresolved-segments", str(adverse_unresolved_path), "--maximum-claim-effects", str(adverse_effects_path), "--workspace", str(workspace)], "completed", True),
                (["bridge", "check", "--input", str(bridge_path), "--workspace", str(workspace), "--maximum-permitted-claim", "unproven_research_question"], "valid", True),
            ]
            for argv, key, expected in commands:
                with self.subTest(command=argv[0]):
                    code, stdout, stderr = self.run_cli(argv)
                    self.assertEqual(0, code, stderr)
                    self.assertEqual(expected, json.loads(stdout)[key])

            for relative in (
                "position-cards.jsonl",
                "case-comparison.json",
                "comparability-matrix.jsonl",
                "applicant-relations.jsonl",
                "case-temporal-analysis.json",
                "review-queue.json",
                "case-adverse-review.json",
                "normative-bridge.json",
            ):
                self.assertTrue((workspace / relative).exists(), relative)
            comparison = read_json(workspace / "case-comparison.json")
            self.assertEqual("approved", comparison["review_provenance"]["status"])
            self.assertEqual("f" * 64, comparison["fingerprint_sha256"])
            self.assertEqual("position-1", comparison["position_card_id"])
            self.assertEqual(["candidate-1"], read_json(workspace / "review-queue.json")["priority_candidate_ids"])

            tampered_applicant = root / "tampered-applicant.json"
            applicant_features = self.answers()["features"]
            applicant_features[0]["value"] = "подменённый признак"
            write_json(tampered_applicant, applicant_features)
            code, _, stderr = self.run_cli(
                [
                    "compare",
                    "--applicant",
                    str(tampered_applicant),
                    "--candidate",
                    str(candidate_path),
                    "--workspace",
                    str(workspace),
                    "--reviewer",
                    "И.И. Иванов",
                    "--reviewed-at",
                    "2026-08-26T00:20:00Z",
                ]
            )
            self.assertEqual(2, code)
            self.assertIn("подмен", stderr.lower())

            tampered_comparison = root / "tampered-comparison.json"
            write_json(tampered_comparison, {**comparison, "status": "distinguishable"})
            code, _, stderr = self.run_cli(
                [
                    "relation",
                    "classify",
                    "--position-card",
                    str(card_path),
                    "--comparison",
                    str(tampered_comparison),
                    "--applicant-position",
                    str(applicant_position_path),
                    "--workspace",
                    str(workspace),
                    "--reviewer",
                    "И.И. Иванов",
                    "--reviewed-at",
                    "2026-08-26T00:25:00Z",
                ]
            )
            self.assertEqual(2, code)
            self.assertIn("не совпадает", stderr.lower())

    def test_status_report_handoff_cache_and_source_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty_workspace = root / "empty"
            code, stdout, stderr = self.run_cli(["status", "--workspace", str(empty_workspace)])
            self.assertEqual(0, code, stderr)
            self.assertEqual("plan_not_frozen", json.loads(stdout)["status"]["code"])

            model_path = root / "model.json"
            write_json(
                model_path,
                {
                    "title": "Проверка премий",
                    "run_id": "run-1",
                    "plan_sha256": "a" * 64,
                    "evidence_sha256": "b" * 64,
                    "state": {"plan_frozen": False},
                    "coverage_gaps": [],
                    "findings": [],
                    "safe_wording": {"allowed": "Вывод пока не готов.", "forbidden": [], "next_steps": []},
                },
            )
            code, stdout, stderr = self.run_cli(
                ["report", "--workspace", str(empty_workspace), "--model", str(model_path)]
            )
            self.assertEqual(0, code, stderr)
            report = json.loads(stdout)
            self.assertTrue(Path(report["html_path"]).exists())
            self.assertTrue(Path(report["manifest_path"]).exists())

            workspace = root / "matter"
            (workspace / "plans").mkdir(parents=True)
            write_json(workspace / "plans" / "plan-v1.json", {"frozen": True, "plan_sha256": "a" * 64})
            write_json(workspace / "case-fingerprint.json", {"revision": 1, "fingerprint_sha256": "b" * 64})
            payload_path = root / "payload.json"
            handoff_path = root / "handoff.json"
            write_json(
                payload_path,
                {
                    "drafting_ready": False,
                    "questions": ["Что показывает корпус?"],
                    "claim_bindings": [
                        {
                            "claim_id": "claim-1",
                            "claim_sha256": "1" * 64,
                            "source_locator": "жалоба.md#абзац-12",
                        }
                    ],
                },
            )
            code, stdout, stderr = self.run_cli(
                [
                    "handoff", "create", "--workspace", str(workspace),
                    "--target-skill", "ksrf-complaint-cycle",
                    "--payload-type", "unproven_research_questions",
                    "--payload", str(payload_path), "--output", str(handoff_path),
                    "--created-at", "2026-08-26T00:00:00Z",
                ]
            )
            self.assertEqual(0, code, stderr)
            request_handoff = json.loads(stdout)
            self.assertEqual("2.0", request_handoff["schema_version"])
            self.assertEqual("unproven_research_questions", request_handoff["payload_type"])
            self.assertRegex(request_handoff["payload"]["claim_set_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(request_handoff["payload"]["request_sha256"], r"^[0-9a-f]{64}$")

            approved_payload_path = root / "approved-payload.json"
            write_json(
                approved_payload_path,
                {
                    "drafting_ready": True,
                    "maximum_permitted_claim": "bounded_observed_corpus",
                    "findings": [{"candidate_id": "thesis-1"}],
                    "supporting_position_card_ids": ["position-1"],
                    "adverse_position_card_ids": [],
                },
            )
            code, _, stderr = self.run_cli(
                [
                    "handoff", "create", "--workspace", str(workspace),
                    "--target-skill", "ksrf-complaint-cycle",
                    "--payload-type", "approved_bounded_findings",
                    "--payload", str(approved_payload_path),
                    "--limitation", "Только раскрытый наблюдаемый корпус.",
                ]
            )
            self.assertEqual(2, code)
            self.assertIn("произволь", stderr.lower())
            code, stdout, stderr = self.run_cli(
                ["handoff", "check", "--input", str(handoff_path), "--expected-target", "ksrf-complaint-cycle"]
            )
            self.assertEqual(0, code, stderr)
            self.assertTrue(json.loads(stdout)["valid"])
            ledger = root / "inbox.jsonl"
            code, stdout, stderr = self.run_cli(
                ["handoff", "import", "--input", str(handoff_path), "--ledger", str(ledger), "--expected-target", "ksrf-complaint-cycle"]
            )
            self.assertEqual(0, code, stderr)
            self.assertTrue(json.loads(stdout)["imported"])

            cache = root / "cache"
            for argv in (
                ["cache", "init", "--root", str(cache)],
                ["cache", "register-seed", "--root", str(cache), "--url", "https://2kas.sudrf.ru/modules.php?name=sud_delo", "--role", "official_user_seed"],
                ["cache", "search", "--root", str(cache), "--query", "премия"],
                ["cache", "refresh-plan", "--root", str(cache), "--as-of", "2026-08-26T00:00:00Z", "--max-age-seconds", "86400"],
            ):
                code, _, stderr = self.run_cli(argv)
                self.assertEqual(0, code, stderr)

    def test_status_rejects_non_object_fingerprint_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            (workspace / "plans").mkdir(parents=True)
            write_json(workspace / "plans" / "plan-v1.json", {})
            write_json(workspace / "case-fingerprint.json", [])

            code, stdout, stderr = self.run_cli(
                ["status", "--workspace", str(workspace)]
            )

            self.assertEqual(0, code)
            self.assertEqual("", stderr)
            self.assertNotIn("Traceback", stderr)
            payload = json.loads(stdout)
            self.assertFalse(payload["state"]["case_fingerprint_ready"])
            self.assertEqual(
                "case-fingerprint.json должен быть JSON-объектом.",
                payload["state"]["workspace_error"],
            )

    def test_status_rejects_non_object_coverage_without_traceback_or_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            (workspace / "plans").mkdir(parents=True)
            write_json(workspace / "plans" / "plan-v1.json", {})
            write_json(workspace / "exports" / "coverage.json", [])
            before = {
                path.relative_to(workspace): path.read_bytes()
                for path in workspace.rglob("*")
                if path.is_file()
            }

            code, stdout, stderr = self.run_cli(
                ["status", "--workspace", str(workspace)]
            )

            self.assertEqual(0, code)
            self.assertEqual("", stderr)
            self.assertNotIn("Traceback", stderr)
            payload = json.loads(stdout)
            self.assertFalse(payload["state"]["case_fingerprint_ready"])
            self.assertEqual(
                "exports/coverage.json должен быть JSON-объектом.",
                payload["state"]["workspace_error"],
            )
            after = {
                path.relative_to(workspace): path.read_bytes()
                for path in workspace.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)

    def test_practice_quality_cli_persists_content_bound_chain_and_audit_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observations = root / "observations.json"
            chain_output = root / "chain-propagation.json"
            write_json(
                observations,
                [
                    {
                        "observation_id": "observation-1",
                        "chain_id": "chain-1",
                        "source_stage": "first_instance",
                        "position_actor_stage": "first_instance",
                        "evidence_role": "actor_primary_text",
                        "document_id": "document-1",
                        "document_sha256": "a" * 64,
                        "official_url": "https://2kas.sudrf.ru/example",
                        "speaker": "court",
                        "proposition": "Премия входит в систему оплаты труда.",
                        "quote": "премия является частью заработной платы",
                        "quote_locator": "абзац 18",
                        "quote_verified": True,
                        "full_text_reviewed": True,
                        "treatment_of_prior": "originates",
                        "disposition": "claim_granted",
                        "outcome_materiality": "necessary_to_outcome",
                        "alternative_grounds": [],
                        "reading_family": "wage_component",
                        "reviewer": "И.И. Иванов",
                        "reviewed_at": "2026-08-27T12:00:00Z",
                        "human_review": "approved",
                    },
                    {
                        "observation_id": "observation-2",
                        "chain_id": "chain-1",
                        "source_stage": "cassation",
                        "position_actor_stage": "cassation",
                        "evidence_role": "actor_primary_text",
                        "document_id": "document-2",
                        "document_sha256": "b" * 64,
                        "official_url": "https://2kas.sudrf.ru/example-2",
                        "speaker": "court",
                        "proposition": "Кассация прямо поддержала толкование.",
                        "quote": "судебная коллегия соглашается с данным выводом",
                        "quote_locator": "абзац 22",
                        "quote_verified": True,
                        "full_text_reviewed": True,
                        "treatment_of_prior": "expressly_adopts",
                        "disposition": "left_unchanged",
                        "outcome_materiality": "necessary_to_outcome",
                        "alternative_grounds": [],
                        "reading_family": "wage_component",
                        "reviewer": "П.П. Петров",
                        "reviewed_at": "2026-08-27T12:05:00Z",
                        "human_review": "approved",
                    },
                ],
            )
            code, stdout, stderr = self.run_cli(
                [
                    "quality",
                    "chain-propagation",
                    "--observations",
                    str(observations),
                    "--required-chain-id",
                    "chain-1",
                    "--output",
                    str(chain_output),
                ]
            )
            self.assertEqual(0, code, stderr)
            self.assertTrue(json.loads(stdout)["review_complete"])

            self.assertRegex(read_json(chain_output)["evidence_sha256"], r"^[0-9a-f]{64}$")

            screening = root / "screening.json"
            primary = root / "primary.json"
            audit_output = root / "coding-audit-plan.json"
            write_json(screening, [{"candidate_id": "candidate-1"}])
            write_json(
                primary,
                [{"candidate_id": "candidate-1", "label": "core_merits"}],
            )
            code, stdout, stderr = self.run_cli(
                [
                    "quality",
                    "coding-audit-plan",
                    "--screening-candidates",
                    str(screening),
                    "--primary-decisions",
                    str(primary),
                    "--plan-sha256",
                    "b" * 64,
                    "--sample-size",
                    "1",
                    "--exclusion-sample-size",
                    "0",
                    "--output",
                    str(audit_output),
                ]
            )
            self.assertEqual(0, code, stderr)
            self.assertEqual(["candidate-1"], json.loads(stdout)["required_candidate_ids"])
            self.assertTrue(read_json(audit_output)["frozen"])

    def test_reviewed_handoff_receiver_cli_requires_external_anchor_and_target(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(["handoff", "check", "--input", "portable.json"])
            with self.assertRaises(SystemExit):
                main(
                    [
                        "handoff",
                        "import",
                        "--input",
                        "portable.json",
                        "--ledger",
                        "inbox.jsonl",
                        "--source-workspace",
                        "source",
                    ]
                )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            portable = root / "reviewed.json"
            write_json(portable, {"payload_type": "approved_bounded_findings"})
            code, _, stderr = self.run_cli(
                [
                    "handoff",
                    "check",
                    "--input",
                    str(portable),
                    "--expected-target",
                    "ksrf-complaint-cycle",
                ]
            )
            self.assertEqual(2, code)
            self.assertIn("--source-workspace", stderr)

    def test_reviewed_handoff_payload_is_derived_from_request_and_selected_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "matter"
            workspace.mkdir()
            plan_sha256 = "a" * 64
            evidence_sha256 = "b" * 64
            fingerprint_sha256 = "c" * 64
            card = self.position_card()
            comparison = {
                "comparison_id": "comparison-position-1",
                "position_card_id": "position-1",
                "position_card_sha256": artifact_sha256(card),
                "status": "matched",
                "fingerprint_sha256": fingerprint_sha256,
                "review_provenance": {
                    "status": "approved",
                    "reviewer": "И.И. Иванов",
                    "reviewed_at": "2026-08-27T12:00:00Z",
                },
            }
            relation = {
                "position_card_id": "position-1",
                "position_card_sha256": artifact_sha256(card),
                "comparison_id": comparison["comparison_id"],
                "comparison_sha256": artifact_sha256(comparison),
                "relation": "supports",
                "fingerprint_sha256": fingerprint_sha256,
                "human_review": "approved",
                "stale": False,
            }
            adverse = {
                "completed": True,
                "completed_buckets": [
                    "opposite_reading",
                    "narrower_reading",
                    "alternative_ground",
                    "later_authority",
                ],
                "missing_buckets": [],
                "buckets": {
                    "opposite_reading": [],
                    "narrower_reading": [],
                    "alternative_ground": [],
                    "later_authority": [],
                },
            }
            bridge = {
                "supporting_position_card_ids": ["position-1"],
                "adverse_position_card_ids": [],
                "fingerprint_sha256": fingerprint_sha256,
                "maximum_permitted_claim": "bounded_observed_corpus",
                "claim_wording": "В раскрытом корпусе наблюдается проверенная позиция.",
                "reviewer": "И.И. Иванов",
                "reviewed_at": "2026-08-27T12:10:00Z",
                "human_review": "approved",
            }
            decision = {
                "decision": "approved",
                "reviewer": "И.И. Иванов",
                "decided_at": "2026-08-27T12:20:00Z",
                "plan_sha256": plan_sha256,
                "evidence_sha256": evidence_sha256,
                "candidate_ids": ["thesis-1"],
            }
            validation = {
                "valid": True,
                "plan_sha256": plan_sha256,
                "evidence_sha256": evidence_sha256,
                "fingerprint_sha256": fingerprint_sha256,
            }
            candidate = {
                "candidate_id": "thesis-1",
                "plan_sha256": plan_sha256,
                "human_review": "approved",
                "drafting_ready": True,
                "limitations": ["Только раскрытый корпус."],
            }
            write_jsonl(workspace / "position-cards.jsonl", [card])
            write_jsonl(workspace / "comparability-matrix.jsonl", [comparison])
            write_jsonl(workspace / "applicant-relations.jsonl", [relation])
            write_jsonl(workspace / "thesis-candidates.jsonl", [candidate])
            write_json(workspace / "case-adverse-review.json", adverse)
            write_json(workspace / "normative-bridge.json", bridge)
            write_json(workspace / "human-decision.json", decision)
            write_json(workspace / "validation-report.json", validation)

            request_payload = bind_request_payload(
                {
                    "drafting_ready": False,
                    "questions": ["Каков судебный смысл нормы?"],
                    "claim_bindings": [
                        {
                            "claim_id": "claim-1",
                            "claim_sha256": "1" * 64,
                            "source_locator": "жалоба.md#абзац-12",
                        }
                    ],
                }
            )
            request = create_handoff(
                source_skill="ksrf-complaint-cycle",
                target_skill="ksrf-cassation-judicial-meaning",
                run_id="request-1",
                plan_sha256="d" * 64,
                evidence_sha256="e" * 64,
                payload_type="unproven_research_questions",
                payload=request_payload,
                limitations=[],
                created_at="2026-08-27T12:00:00Z",
            )
            request_path = root / "request.json"
            write_json(request_path, request)
            args = SimpleNamespace(
                request=str(request_path),
                claim_id=[],
                candidate_id=[],
                position_card_id=[],
                payload_type="approved_bounded_findings",
            )
            payload = _build_reviewed_handoff_payload(
                workspace,
                args,
                plan_sha256=plan_sha256,
                evidence_sha256=evidence_sha256,
                fingerprint_sha256=fingerprint_sha256,
                maximum_permitted_claim="bounded_observed_corpus",
                limitations=["Только раскрытый корпус."],
            )
            self.assertEqual(request["handoff_id"], payload["request_handoff_id"])
            self.assertEqual(["claim-1"], payload["findings"][0]["claim_ids"])
            self.assertEqual(candidate, payload["findings"][0]["candidate"])
            self.assertEqual(7, len(payload["artifact_manifest"]["files"]))

            args.position_card_id = ["invented-position"]
            with self.assertRaisesRegex(ValueError, "нормативным мостом"):
                _build_reviewed_handoff_payload(
                    workspace,
                    args,
                    plan_sha256=plan_sha256,
                    evidence_sha256=evidence_sha256,
                    fingerprint_sha256=fingerprint_sha256,
                    maximum_permitted_claim="bounded_observed_corpus",
                    limitations=["Только раскрытый корпус."],
                )

            wider_request_payload = bind_request_payload(
                {
                    "drafting_ready": False,
                    "questions": ["Каков смысл?", "Какова динамика?"],
                    "claim_bindings": [
                        *request_payload["claim_bindings"],
                        {
                            "claim_id": "claim-2",
                            "claim_sha256": "2" * 64,
                            "source_locator": "жалоба.md#абзац-18",
                        },
                    ],
                }
            )
            wider_request = create_handoff(
                source_skill="ksrf-complaint-cycle",
                target_skill="ksrf-cassation-judicial-meaning",
                run_id="request-2",
                plan_sha256="d" * 64,
                evidence_sha256="e" * 64,
                payload_type="unproven_research_questions",
                payload=wider_request_payload,
                limitations=[],
                created_at="2026-08-27T12:01:00Z",
            )
            wider_request_path = root / "wider-request.json"
            write_json(wider_request_path, wider_request)
            args.request = str(wider_request_path)
            args.position_card_id = []
            args.claim_id = ["claim-1"]
            with self.assertRaisesRegex(ValueError, "Частичный reviewed result запрещён"):
                _build_reviewed_handoff_payload(
                    workspace,
                    args,
                    plan_sha256=plan_sha256,
                    evidence_sha256=evidence_sha256,
                    fingerprint_sha256=fingerprint_sha256,
                    maximum_permitted_claim="bounded_observed_corpus",
                    limitations=["Только раскрытый корпус."],
                )

            manifests = root / "manifests.json"
            observations = root / "observations.json"
            coverage = root / "coverage.json"
            write_json(
                manifests,
                [{
                    "enumerator_id": "regional-pre-2019",
                    "version": "1",
                    "source_role": "official_unconfigured",
                    "institutional_regime": "regional_presidia_pre_2019",
                    "applicable_from": "2016-01-01",
                    "applicable_to": "2019-09-30",
                    "courts": [],
                    "enumeration_unit": "declared_route_segment",
                    "closure_rule": None,
                    "denominator_scope": "not configured",
                    "adapter_id": None,
                    "configured": False,
                }],
            )
            write_json(observations, [])
            write_json(coverage, [])
            single_manifest = root / "manifest.json"
            write_json(single_manifest, read_json(manifests)[0])
            code, stdout, stderr = self.run_cli(
                ["source", "verify-manifest", "--input", str(single_manifest)]
            )
            self.assertEqual(0, code, stderr)
            self.assertTrue(json.loads(stdout)["valid"])
            code, stdout, stderr = self.run_cli(
                ["source", "reconcile", "--manifests", str(manifests), "--observations", str(observations), "--route-coverage", str(coverage), "--requested-from", "2016-01-01", "--requested-to", "2026-08-26", "--workspace", str(workspace)]
            )
            self.assertEqual(0, code, stderr)
            self.assertEqual("observed_only", json.loads(stdout)["overall_status"])
            self.assertTrue((workspace / "source-reconciliation.json").exists())

    def test_default_report_discloses_historical_and_open_route_gaps_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            (workspace / "plans").mkdir(parents=True)
            write_json(
                workspace / "plans" / "plan-v1.json",
                {"frozen": True, "plan_sha256": "a" * 64},
            )
            write_json(
                workspace / "case-fingerprint.json",
                {"fingerprint_sha256": "b" * 64, "features": [], "revision": 1},
            )
            write_json(
                workspace / "source-reconciliation.json",
                {
                    "overall_status": "observed_only",
                    "gaps": [],
                    "historical_gaps": [
                        {
                            "enumerator_id": "regional-pre-2019",
                            "institutional_regime": "regional_presidia_pre_2019",
                            "status": "not_configured",
                            "applicable_from": "2016-01-01",
                            "applicable_to": "2019-09-30",
                        }
                    ],
                    "route_coverage": {
                        "2kas-search": {
                            "status": "observed_only",
                            "closure_blockers": ["enumerator_contract_not_promoted"],
                        }
                    },
                    "unresolved_identity_observations": [],
                    "denominator_limit": "Только заявленные и проверенные маршруты.",
                },
            )
            model = _default_report_model(workspace)
            self.assertEqual("b" * 64, model["fingerprint_sha256"])
            gap_ids = {item["id"] for item in model["coverage_gaps"]}
            self.assertIn("historical-1", gap_ids)
            self.assertIn("route-2kas-search", gap_ids)
            self.assertIn("overall-observed-only", gap_ids)

            code, stdout, stderr = self.run_cli(
                ["report", "--workspace", str(workspace)]
            )
            self.assertEqual(0, code, stderr)
            manifest = json.loads(stdout)
            self.assertEqual("b" * 64, manifest["fingerprint_sha256"])
            html = Path(manifest["html_path"]).read_text(encoding="utf-8")
            self.assertIn("Исторический режим не настроен", html)
            self.assertIn("enumerator_contract_not_promoted", html)

    def test_public_cache_cli_ingests_pins_exports_and_imports_a_searchable_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "cache"
            imported_cache = root / "imported-cache"
            raw_path = root / "act.html"
            text_path = root / "act.txt"
            parser_path = root / "parser.json"
            target_identity_path = root / "target-identity.json"
            package = root / "package"
            raw_path.write_bytes("<html>Премия взыскана</html>".encode("utf-8"))
            text_path.write_text("Суд взыскал премию работнику.", encoding="utf-8")
            write_json(parser_path, {"adapter_id": "manual_public_import", "parser_version": "1"})
            write_json(
                target_identity_path,
                {"authority_type": "constitutional_decision", "number": "23-П"},
            )

            code, stdout, stderr = self.run_cli(
                [
                    "cache", "register-seed", "--root", str(cache),
                    "--url", "https://2kas.sudrf.ru/example-act",
                    "--role", "official_user_seed",
                ]
            )
            self.assertEqual(0, code, stderr)
            seed_id = json.loads(stdout)["seed_id"]
            code, stdout, stderr = self.run_cli(
                [
                    "cache", "ingest", "--root", str(cache),
                    "--seed-id", seed_id, "--raw", str(raw_path),
                    "--content-type", "text/html; charset=utf-8",
                    "--fetched-at", "2026-08-26T00:00:00Z",
                    "--parser-manifest", str(parser_path), "--text", str(text_path),
                ]
            )
            self.assertEqual(0, code, stderr)
            snapshot_id = json.loads(stdout)["snapshot_id"]
            code, _, stderr = self.run_cli(
                [
                    "cache", "funnel", "record", "--root", str(cache),
                    "--chain-id", "chain-public", "--status", "enumerated",
                    "--snapshot-id", snapshot_id, "--source-role", "official_user_seed",
                    "--court-id", "2kas", "--period-id", "post-23p",
                    "--enumerator-id", "manual-user-seed",
                ]
            )
            self.assertEqual(0, code, stderr)
            code, stdout, stderr = self.run_cli(
                [
                    "cache", "treatment", "discover", "--root", str(cache),
                    "--source-chain-id", "chain-public", "--source-court-id", "2kas",
                    "--target-authority-id", "ksrf-23p", "--target-kind", "decision",
                    "--target-identity", str(target_identity_path),
                    "--treatment-type", "applies", "--snapshot-id", snapshot_id,
                ]
            )
            self.assertEqual(0, code, stderr)
            treatment_id = json.loads(stdout)["treatment_id"]
            code, stdout, stderr = self.run_cli(
                [
                    "cache", "treatment", "review", "--root", str(cache),
                    "--treatment-id", treatment_id, "--decision", "verified",
                    "--reviewer", "И.И. Иванов", "--quote", "Суд применил 23-П",
                    "--locator", "абзац 17", "--speaker", "court",
                    "--confirmed-target-authority-id", "ksrf-23p",
                    "--target-identity-confirmed", "--reviewed-at", "2026-08-26T00:05:00Z",
                ]
            )
            self.assertEqual(0, code, stderr)
            self.assertEqual("verified", json.loads(stdout)["status"])
            code, _, stderr = self.run_cli(
                [
                    "cache", "pin-run", "--root", str(cache), "--run-id", "run-public",
                    "--snapshot", snapshot_id,
                ]
            )
            self.assertEqual(0, code, stderr)
            code, _, stderr = self.run_cli(
                [
                    "cache", "export-run", "--root", str(cache),
                    "--run-id", "run-public", "--output", str(package),
                ]
            )
            self.assertEqual(0, code, stderr)
            code, stdout, stderr = self.run_cli(
                [
                    "cache", "import-run", "--root", str(imported_cache),
                    "--input", str(package),
                ]
            )
            self.assertEqual(0, code, stderr)
            self.assertEqual("run-public", json.loads(stdout)["run_id"])
            code, stdout, stderr = self.run_cli(
                ["cache", "search", "--root", str(imported_cache), "--query", "премию"]
            )
            self.assertEqual(0, code, stderr)
            self.assertEqual(snapshot_id, json.loads(stdout)["hits"][0]["snapshot_id"])
            code, stdout, stderr = self.run_cli(
                ["cache", "funnel", "report", "--root", str(imported_cache)]
            )
            self.assertEqual(0, code, stderr)
            self.assertEqual(1, json.loads(stdout)["enumerated"])
            code, stdout, stderr = self.run_cli(
                [
                    "cache", "treatment", "list", "--root", str(imported_cache),
                    "--verified-only",
                ]
            )
            self.assertEqual(0, code, stderr)
            self.assertEqual(1, json.loads(stdout)["count"])
            code, stdout, stderr = self.run_cli(
                [
                    "cache", "treatment", "history", "--root", str(imported_cache),
                    "--treatment-id", treatment_id,
                ]
            )
            self.assertEqual(0, code, stderr)
            self.assertEqual(2, json.loads(stdout)["count"])

    def test_fingerprint_revision_makes_previous_human_approval_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "matter"
            (workspace / "plans").mkdir(parents=True)
            write_json(workspace / "plans" / "plan-v1.json", {"frozen": True, "plan_sha256": "a" * 64})
            answers = root / "answers.json"
            self.seed_applicant_intake(workspace)
            write_json(answers, self.answers())
            code, _, stderr = self.run_cli(
                ["case", "prepare", "--workspace", str(workspace), "--answers", str(answers)]
            )
            self.assertEqual(0, code, stderr)
            write_json(
                workspace / "human-decision.json",
                {
                    "decision": "approved",
                    "plan_sha256": "a" * 64,
                    "evidence_sha256": _approval_evidence_sha256(workspace),
                    "adverse_review_complete": True,
                    "coverage_review_complete": True,
                },
            )
            self.assertTrue(_validation_state(workspace)["approval_hashes_match"])

            write_json(answers, self.answers("годовая премия"))
            code, _, stderr = self.run_cli(
                ["case", "prepare", "--workspace", str(workspace), "--answers", str(answers)]
            )
            self.assertEqual(0, code, stderr)
            state = _validation_state(workspace)
            self.assertFalse(state["approval_hashes_match"])
            self.assertFalse(state["human_approved"])
            code, stdout, stderr = self.run_cli(
                ["status", "--workspace", str(workspace)]
            )
            self.assertEqual(0, code, stderr)
            self.assertEqual("approval_stale", json.loads(stdout)["status"]["code"])

    def test_case_relative_validation_cannot_bypass_comparison_bridge_and_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "matter"
            (workspace / "plans").mkdir(parents=True)
            write_json(
                workspace / "plans" / "plan-v1.json",
                {
                    "schema_version": "1.0",
                    "frozen": True,
                    "plan_sha256": "a" * 64,
                    "maximum_claim_if_incomplete": "unproven_research_question",
                },
            )
            answers = root / "answers.json"
            self.seed_applicant_intake(workspace)
            write_json(answers, self.answers())
            code, _, stderr = self.run_cli(
                ["case", "prepare", "--workspace", str(workspace), "--answers", str(answers)]
            )
            self.assertEqual(0, code, stderr)

            code, stdout, stderr = self.run_cli(["validate", "--workspace", str(workspace)])
            self.assertEqual(2, code, stderr)
            report = json.loads(stdout)
            self.assertFalse(report["valid"])
            joined = " ".join(report["errors"]).lower()
            self.assertIn("сопостав", joined)
            self.assertIn("нормативн", joined)
            self.assertFalse(_validation_state(workspace)["validation_current"])


if __name__ == "__main__":
    unittest.main()
