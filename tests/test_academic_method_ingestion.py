import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def section(body: str, start: str, end: str) -> str:
    return body.split(start, 1)[1].split(end, 1)[0]


class RuntimeMethodDeltaTests(unittest.TestCase):
    def test_process_workbook_is_self_contained_and_directly_routed(self):
        workbook = text("skills/ksrf-rights-argument-builder/references/process-based-rights-review-workbook.md")
        for marker in (
            "ProcessQualityCard",
            "review_intensity",
            "MicroMesoMacroTrace",
            "substantive_fallback",
            "window_dressing_risk",
            "russian_anchor",
        ):
            self.assertIn(marker, workbook)
        self.assertNotIn("https://", workbook)
        self.assertNotIn("DOI", workbook)
        self.assertNotIn("SHA-256", workbook)
        for skill in (
            "skills/ksrf-rights-argument-builder/SKILL.md",
            "skills/ksrf-complaint-qa/SKILL.md",
            "skills/ksrf-complaint-cycle/SKILL.md",
        ):
            self.assertIn("process-based-rights-review-workbook.md", text(skill))

    def test_fact_reasoning_and_gap_deltas_are_operational(self):
        facts = text("skills/ksrf-complaint-facts-demands/references/constitutional-facts-evidence-ledger.md")
        for marker in (
            "stage_fact_type",
            "forecast_or_counterfactual",
            "source_provenance",
            "premise_date",
            "revision_trigger",
            "web_selection_bias",
            "inference_gap",
            "FactWorkOversightMap",
            "fact_assembly",
            "fact_deployment",
            "reviewer_own_assembly",
            "SystemicDataAcquisitionGap",
            "acquisition_gap_candidate",
            "HistoricalClaimRoleAndFactualPrecedentAudit",
            "FactualPrecedentRevalidation",
            "stale_or_unrevalidated_factual_precedent",
        ):
            self.assertIn(marker, facts)

        reasoning = text("skills/ksrf-argument-patterns/references/reasoning-lab-workflow.md")
        for marker in ("bounded_point", "qualitative_only", "noncomparable", "rival hypothesis"):
            self.assertIn(marker, reasoning)

        gap = text("skills/ksrf-complaint-facts-demands/references/norm-system-and-gap-qualification.md")
        for marker in ("normative_gap", "knowledge_gap", "recognition_gap", "axiological_gap"):
            self.assertIn(marker, gap)

    def test_attack_procedure_and_institutional_guards_are_distinct(self):
        precedent = text("skills/ksrf-argument-patterns/references/precedent-analogy-and-justification.md")
        for marker in ("`rebut`", "`undermine`", "`undercut`", "dominance_check"):
            self.assertIn(marker, precedent)
        self.assertIn("атакует существование, истинность, допустимость или актуальность premise", precedent)
        self.assertIn("атакует warrant или связь premise → conclusion", precedent)

        qa = text("skills/ksrf-complaint-qa/references/procedural-adequacy-and-cure.md")
        for marker in ("ConstitutionalArgumentResponseLedger", "later_instance_cure", "remaining_normative_harm"):
            self.assertIn(marker, qa)

        architecture = text("skills/ksrf-argument-patterns/references/constitutional-argument-architecture.md")
        for marker in ("abstract_right", "triggering_right", "scrutiny_right", "ultimate_right", "authority", "capability"):
            self.assertIn(marker, architecture)
        self.assertIn("`weaken`: подтверждённо снижен вес конкретного основания", architecture)
        self.assertEqual(architecture.count("- `undercut`:"), 1)

    def test_wave_eight_methods_are_operational_routed_and_source_independent(self):
        facts = text("skills/ksrf-complaint-facts-demands/references/constitutional-facts-evidence-ledger.md")
        for marker in (
            "ConstitutionalFactProofRoute",
            "route_id",
            "channel_instance_id",
            "case_specific_mode",
            "proof_channel",
            "dependency_dag_evidence_id",
            "origin_id",
            "dependency_group",
            "acquisition_and_inference_method",
            "adversarial_test_available",
            "maximum_supported_inference",
            "dependency_status",
            "independent_support",
            "dependent_repetition",
            "unknown_dependency",
            "support_status",
            "insufficient_record",
        ):
            self.assertIn(marker, facts)
        self.assertIn("dependency-dag-и-запрет-двойного-счёта", facts)
        self.assertIn("числом независимых `dependency_group`", facts)
        self.assertIn("допустимы только как legacy-вход", facts)

        reasoning = text("skills/ksrf-argument-patterns/references/reasoning-lab-workflow.md")
        for marker in (
            "QuestionSubstitutionAndExposureCheck",
            "FrozenBaseline",
            "pre_exposure_frozen",
            "PostExposureReconstruction",
            "post_exposure_reconstruction",
            "hard_question",
            "easy_proxy",
            "context_exposure_order",
            "ContextExposureLedger",
            "reviewer_context_id",
            "reverse_order_result",
            "reverse_order_unavailable",
            "non_independent",
            "context_contaminated",
        ):
            self.assertIn(marker, reasoning)
        self.assertIn("Только до раскрытия такого контекста создай `FrozenBaseline`", reasoning)
        self.assertIn("Обратный порядок проверяет только новый изолированный reviewer/context", reasoning)
        self.assertIn("Не называй мысленное переставление", reasoning)
        self.assertIn("документов слепым тестом", reasoning)

        advice = text("skills/ksrf-doctrine-research/references/constitutional-advice-function-and-effect.md")
        for marker in (
            "ConstitutionalAdviceFunctionAndEffectCard",
            "advice_document_id",
            "advice_source_ref",
            "advisor",
            "advisee",
            "decision_lock_in_status",
            "delivery_evidence_ref",
            "influence_opportunity_status",
            "stated_function",
            "inferred_function_candidate",
            "function_evidence_ref",
            "observed_effect",
            "legal_bindingness",
            "uptake_record_ref",
            "actual_uptake",
            "record_conflict",
            "application_record_ref",
            "application_status",
            "explicitly_applied",
            "implicitly_applied_proven",
            "application_unclear",
            "not_applied",
            "documented_mechanism",
            "independent_ground",
            "late_window_candidate",
            "record_status=verified|limited|insufficient_record",
            "legal_use_status=research_only|candidate",
            "research_only",
        ):
            self.assertIn(marker, advice)
        self.assertIn("`candidate` допустим только одновременно", advice)
        self.assertIn("`causal_status=officially_linked|documented_mechanism`", advice)
        self.assertIn("отсутствии контролирующего `independent_ground`", advice)
        self.assertIn("Неизвестное самостоятельное основание также блокирует", advice)

        risk = text("skills/ksrf-complaint-facts-demands/references/quantified-risk-communication.md")
        for marker in (
            "RiskCommunicationCard",
            "claim_type",
            "reference_population",
            "time_horizon",
            "assessment_method_type",
            "range_status / calibration_status",
            "measurement_status",
            "representation_format",
            "method_supports_representation",
            "representation_status",
            "comparison_group_status",
            "threshold_owner",
            "legal_threshold_status",
            "false_positive",
            "false_negative",
            "application_status",
            "causation_status",
            "outcome_material",
            "causation_unknown",
            "risk_representation_unknown",
            "independent_ground",
            "stage_application_record_ref",
            "indicator_passport_ref / automated_decision_record_ref",
            "record_conflict",
            "permitted_expression_mode",
        ):
            self.assertIn(marker, risk)
        self.assertIn("Сначала верни пять независимых layer-status полей", risk)
        self.assertIn("Не сворачивай их в общий score или единый pass", risk)
        self.assertIn("Reliance на", risk)
        self.assertIn("не доказывают\n   применение оспариваемой нормы друг через друга", risk)

        argument_router = text("skills/ksrf-argument-patterns/SKILL.md")
        facts_router = text("skills/ksrf-complaint-facts-demands/SKILL.md")
        doctrine_router = text("skills/ksrf-doctrine-research/SKILL.md")
        qa_router = text("skills/ksrf-complaint-qa/SKILL.md")
        explore_router = text("skills/ksrf-explore-arguments/SKILL.md")
        cycle_router = text("skills/ksrf-complaint-cycle/SKILL.md")
        implicit_gate = text("skills/ksrf-complaint-cycle/references/implicit-application-gate.md")

        self.assertIn("reasoning-lab-workflow.md", argument_router)
        self.assertIn("reasoning-lab-workflow.md#questionsubstitutionandexposurecheck", explore_router)
        self.assertIn("ConstitutionalFactProofRoute", facts_router)
        self.assertIn("quantified-risk-communication.md", facts_router)
        self.assertIn("constitutional-advice-function-and-effect.md", doctrine_router)
        self.assertIn("constitutional-advice-function-and-effect.md", qa_router)
        self.assertIn("quantified-risk-communication.md", qa_router)
        self.assertIn("constitutional-advice-function-and-effect.md", cycle_router)
        for marker in (
            "norm_use_status=reasoning_linked_implicit",
            "outcome_causation=independent_sufficient_ground",
            "application_status` для admissibility остаётся `application_unclear`",
            "явного **и имплицитного** нормативного использования",
        ):
            self.assertIn(marker, implicit_gate)

        runtime = "\n".join(
            (
                facts,
                reasoning,
                advice,
                risk,
                argument_router,
                facts_router,
                doctrine_router,
                qa_router,
                explore_router,
                cycle_router,
                implicit_gate,
            )
        )
        for forbidden in (
            "David L. Faigman",
            "Thomas Lundmark",
            "Jürgen de Poorter",
            "Gerhard van der Schyff",
            "Maarten Stremler",
            "Maartje De Visser",
            "Willem Mingelen",
            "Jerfi Uzman",
            "Monica K. Miller",
            "Logan A. Yelderman",
            "Matthew T. Huss",
            "Jason A. Cantone",
            "Jeremy Fogel",
            "Mary Hoopes",
            "Bethany Growns",
            "Tess M. S. Neal",
            "Daniel A. Krauss",
            "William Ellsworth",
            "Jane Goodman-Delahunty",
            "William E. Foote",
            "Constitutional Fictions",
            "Universals of Legal Reasoning by Judges",
            "European Yearbook",
            "Cambridge Handbook",
            "10.1007/978-94-6265-535-5",
            "10.1017/9781009119375",
            "d649dec16162de8ec536d0e0925c68999a56fdd8ae8b45ab7e2b518973a57d06",
            "62346344eec01e5889822b66812003990223be7e10c1974d1effefb5e129b054",
            "202a735ef7754187a88e0fefd16c9c6dd53f88b61b6e8b959dc78e5071b8c22a",
            "c1606f3f13dceec8e426647725924f0ee3dee58064570d4f351e6bec2ac72565",
            "Constitutional fictions.pdf",
            "European Yearbook of Constitutional Law 2021.pdf",
            "The Cambridge Handbook of Psychology and L",
            "9. Chapter Nine ThL 2023 09 08.pdf",
            "https://",
            "http://",
            "/tmp/ksrf-new-books",
            "ТЗ/Гайды/Новое",
        ):
            self.assertNotIn(forbidden, runtime)

        for forbidden in ("DOI", "ISBN"):
            self.assertNotIn(forbidden, "\n".join((facts, reasoning, advice, risk)))

    def test_late_journal_deltas_are_effect_based_and_source_independent(self):
        exhaustion = text("skills/ksrf-exhaustion-planner/references/workflow-reference.md")
        self.assertIn("ProceduralCommunicationFunctionCard", exhaustion)
        self.assertIn("communication_effect_unclear", exhaustion)
        self.assertIn("procedural_act_candidate", exhaustion)
        self.assertIn("informational_candidate", exhaustion)

        reasoning = text("skills/ksrf-argument-patterns/references/legal-reasoning-model-branches.md")
        self.assertIn("JudicialTermOperationalizationRecord", reasoning)
        self.assertIn("term_effect_unclear", reasoning)
        self.assertIn("term_scope_unknown", reasoning)

        continuity = text("skills/ksrf-complaint-cycle/references/norm-meaning-continuity.md")
        self.assertIn("PostDecisionRelatedNormCard", continuity)
        self.assertIn("DerivativeNormRouteCard", continuity)
        self.assertIn("related_norm_continuity_unknown", continuity)

        norm_map = text("skills/ksrf-complaint-facts-demands/references/norm-application-defect-map.md")
        self.assertIn("NonApplicationEffectRecord", norm_map)
        self.assertIn("AuthoritativeNonApplicationEffectCard", norm_map)
        self.assertIn("authoritative_inapplicability", norm_map)

        proportionality = text("skills/ksrf-rights-argument-builder/references/proportionality-and-lawmaking-workbook.md")
        self.assertIn("SpecialRegimeExternalityCard", proportionality)
        self.assertIn("downstream_effects", proportionality)

        automated = text("skills/ksrf-complaint-facts-demands/references/automated-adverse-decision-record.md")
        for marker in (
            "AutomatedAdverseDecisionRecord",
            "authorization_and_version",
            "input_sources",
            "human_review",
            "audit_trace",
            "ABSTAIN_NORMATIVE_BRIDGE",
        ):
            self.assertIn(marker, automated)
        for forbidden in ("https://", "DOI", "SHA-256"):
            self.assertNotIn(forbidden, automated)
        self.assertIn("automated-adverse-decision-record.md", text("skills/ksrf-complaint-facts-demands/SKILL.md"))
        self.assertIn("automated-adverse-decision-record.md", text("skills/ksrf-complaint-qa/SKILL.md"))
        self.assertIn("automated-adverse-decision-record.md", text("skills/ksrf-rights-argument-builder/SKILL.md"))

        generic_sections = (
            section(exhaustion, "## Функция процессуального сообщения", "## Аудит применения"),
            section(reasoning, "### 5B.1. Операционализация судебного термина", "### 5C."),
            section(continuity, "## 2A. После позиции КС: связанные нормы", "## 3."),
            section(norm_map, "## Классификация неприменения", "## Рабочая таблица"),
        )
        for extracted in generic_sections:
            for forbidden in ("https://", "DOI", "SHA-256"):
                self.assertNotIn(forbidden, extracted)

    def test_new_behavioral_evals_are_valid_and_present(self):
        expected = {
            "skills/ksrf-complaint-facts-demands/evals/evals.json": (14, 15, 16, 17, 18, 19, 20, 21),
            "skills/ksrf-rights-argument-builder/evals/evals.json": (74, 75),
            "skills/ksrf-complaint-qa/evals/evals.json": (41, 42),
            "skills/constitutional-comparative-research/evals/evals.json": (22,),
            "skills/ksrf-exhaustion-planner/evals/evals.json": (4,),
            "skills/ksrf-argument-patterns/evals/evals.json": (25, 26, 27, 28),
            "skills/ksrf-doctrine-research/evals/evals.json": (46, 47, 48),
            "skills/ksrf-complaint-cycle/evals/evals.json": (27,),
            "skills/ksrf-decision-execution/evals/evals.json": (16,),
        }
        for path, expected_ids in expected.items():
            payload = json.loads(text(path))
            ids = [item["id"] for item in payload["evals"]]
            self.assertEqual(len(ids), len(set(ids)), path)
            for eval_id in expected_ids:
                self.assertIn(eval_id, ids, path)

    def test_wave_eight_trigger_evals_cover_positive_and_near_miss_queries(self):
        expected_cases = {
            "skills/ksrf-argument-patterns/evals/trigger-evals.json": (
                ("До чтения известного исхода", True),
                ("Просто сообщи номер и резолютивную часть", False),
            ),
            "skills/ksrf-complaint-facts-demands/evals/trigger-evals.json": (
                ("Один отчёт повторили сторона, эксперт и суд", True),
                ("Акт называет меня лицом высокого риска", True),
                ("Оцени только процессуальный риск", False),
            ),
            "skills/ksrf-doctrine-research/evals/trigger-evals.json": (
                ("могло ли экспертное заключение повлиять", True),
                ("Найди только официальный текст итогового акта", False),
            ),
            "skills/ksrf-complaint-qa/evals/trigger-evals.json": (
                ("Перед release проверь", True),
                ("Рассчитай математическую вероятность", False),
            ),
            "skills/ksrf-explore-arguments/evals/trigger-evals.json": (
                ("изолируй известный исход", True),
                ("Перескажи уже известный итог", False),
            ),
            "skills/ksrf-complaint-cycle/evals/trigger-evals.json": (
                ("отдельно докажи дату передачи совета", True),
                ("Кратко перескажи научную статью", False),
            ),
        }

        for path, cases in expected_cases.items():
            payload = json.loads(text(path))
            self.assertIsInstance(payload, list, path)
            queries = [item["query"] for item in payload]
            self.assertEqual(len(queries), len(set(queries)), path)
            for fragment, should_trigger in cases:
                matched = [item for item in payload if fragment in item["query"]]
                self.assertEqual(len(matched), 1, (path, fragment))
                self.assertIs(matched[0]["should_trigger"], should_trigger)

    def test_wave_eight_forward_contract_snapshots_are_exact_and_non_authoritative(self):
        payload = json.loads(text("tests/fixtures/academic_wave_8_forward_contracts.json"))
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["scope"], "synthetic_method_contract_only")
        cases = {item["id"]: item for item in payload["cases"]}
        self.assertEqual(
            set(cases),
            {
                "dependent_fact_channels",
                "already_exposed_outcome",
                "late_publication_unknown_delivery",
                "quantified_risk_independent_ground",
                "implicit_norm_use_with_independent_ground",
            },
        )
        for item in cases.values():
            self.assertRegex(item["input_manifest_sha256"], r"^[0-9a-f]{64}$")
            canonical = json.dumps(
                item["input_manifest"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            self.assertEqual(
                hashlib.sha256(canonical).hexdigest(),
                item["input_manifest_sha256"],
            )

        fact = cases["dependent_fact_channels"]["expected"]
        self.assertEqual(fact["channel_instance_count"], 3)
        self.assertEqual(fact["independent_dependency_group_count"], 1)
        self.assertEqual(
            fact["unknown_origin_result"],
            {
                "dependency_status": "unknown_dependency",
                "support_status": "insufficient_record",
            },
        )

        exposed = cases["already_exposed_outcome"]["expected"]
        self.assertEqual(exposed["object_type"], "PostExposureReconstruction")
        self.assertFalse(exposed["outcome_blind_claim_allowed"])
        self.assertEqual(exposed["implicit_application_status"], "application_unclear")

        advice = cases["late_publication_unknown_delivery"]["expected"]
        self.assertEqual(advice["timing_result"], "timing_unclear")
        self.assertFalse(advice["late_window_candidate"])
        self.assertEqual(advice["record_status"], "insufficient_record")
        self.assertEqual(advice["legal_use_status"], "research_only")

        risk = cases["quantified_risk_independent_ground"]["expected"]
        self.assertEqual(risk["measurement_status"], "supported")
        self.assertEqual(risk["causation_status"], "independent_ground_controls")
        self.assertFalse(risk["complaint_ready"])

        implicit = cases["implicit_norm_use_with_independent_ground"]["expected"]
        self.assertEqual(implicit["norm_use_status"], "reasoning_linked_implicit")
        self.assertEqual(implicit["outcome_causation"], "independent_sufficient_ground")
        self.assertEqual(implicit["application_status"], "application_unclear")
        self.assertFalse(implicit["not_applied"])


class ProvenanceDocumentationTests(unittest.TestCase):
    def test_academic_provenance_is_source_only_and_absent_from_runtime(self):
        provenance = text("docs/KSRF_ACADEMIC_RUNTIME_PROVENANCE.md")
        self.assertIn("status: source_only", provenance)
        self.assertIn("runtime_dependency: false", provenance)

        runtime_paths = (
            "skills/ksrf-argument-patterns/references/constitutional-argument-architecture.md",
            "skills/ksrf-argument-patterns/references/constitutional-review-methods.md",
            "skills/ksrf-argument-patterns/references/institutional-discourse-and-comparative-transfer.md",
            "skills/ksrf-argument-patterns/references/legal-reasoning-model-branches.md",
            "skills/ksrf-argument-patterns/references/precedent-analogy-and-justification.md",
            "skills/ksrf-complaint-cycle/references/norm-meaning-continuity.md",
            "skills/ksrf-complaint-facts-demands/references/constitutional-facts-evidence-ledger.md",
            "skills/ksrf-complaint-facts-demands/references/norm-application-defect-map.md",
            "skills/ksrf-complaint-facts-demands/references/norm-system-and-gap-qualification.md",
            "skills/ksrf-complaint-facts-demands/references/remedy-design-matrix.md",
            "skills/ksrf-complaint-qa/references/procedural-adequacy-and-cure.md",
            "skills/ksrf-rights-argument-builder/references/constitutional-institutions-access-and-remedy.md",
            "skills/ksrf-rights-argument-builder/references/proportionality-and-lawmaking-workbook.md",
        )
        runtime = "\n".join(text(path) for path in runtime_paths)
        for forbidden in (
            "Joe Tomlinson",
            "Caitlin Goss",
            "Leonie M. Huijbers",
            "Anne Carter",
            "Aharon Barak",
            "John R. Welch",
            "doi.org",
            "ISBN",
            "Hart Publishing",
            "Bloomsbury",
        ):
            self.assertNotIn(forbidden, runtime)

        for marker in ("Joe Tomlinson", "Caitlin Goss", "Aharon Barak", "ISBN", "SHA-256"):
            self.assertIn(marker, provenance + text("docs/KSRF_ACADEMIC_METHOD_SOURCES_2026-09.md"))

    def test_forty_one_source_records_and_forty_families_are_documented_outside_runtime(self):
        registry = text("docs/KSRF_ACADEMIC_METHOD_SOURCES_2026-09.md")
        self.assertIn("source_count: 41", registry)
        self.assertIn("independent_source_family_count: 40", registry)
        self.assertIn("`source_count` считает проверенные file-level records", registry)
        self.assertIn("`independent_source_family_count` — самостоятельные интеллектуальные источники", registry)
        for token in (
            "Douglas Walton",
            "John R. Welch",
            "Richard H. Fallon",
            "Paul Yowell",
            "R. C. van Caenegem",
            "Janneke Gerards",
            "Alec Stone Sweet",
            "Anne Carter",
            "Luiz Guilherme Marinoni",
            "Rosalind Dixon",
            "Leonie M. Huijbers",
            "Е. В. Тимошина",
            "А. Р. Султанов",
            "Conseil national des barreaux",
            "Nikoleta Bitterová",
        ):
            self.assertIn(token, registry)
        self.assertIn("Joe Tomlinson", registry)
        for token in (
            "Joanna Bell",
            "Cassandra Somers-Joce",
            "Caitlin Goss",
            "10.5040/9781509957415.ch-007",
            "10.5040/9781509957415.ch-009",
            "10.5040/9781509957415.ch-014",
        ):
            self.assertIn(token, registry)
        self.assertEqual(registry.count("| KB-"), 41)
        self.assertIn("exact binary duplicate", registry)
        self.assertIn("no_new_source_family", registry)

        rows = {
            source_id: next(
                line
                for line in registry.splitlines()
                if line.startswith(f"| {source_id} |")
            )
            for source_id in ("KB-38", "KB-39", "KB-40", "KB-41")
        }

        expected_sha = {
            "KB-38": "c1606f3f13dceec8e426647725924f0ee3dee58064570d4f351e6bec2ac72565",
            "KB-39": "62346344eec01e5889822b66812003990223be7e10c1974d1effefb5e129b054",
            "KB-40": "d649dec16162de8ec536d0e0925c68999a56fdd8ae8b45ab7e2b518973a57d06",
            "KB-41": "202a735ef7754187a88e0fefd16c9c6dd53f88b61b6e8b959dc78e5071b8c22a",
        }
        for source_id, sha256 in expected_sha.items():
            self.assertIn(f"SHA-256 `{sha256}`", rows[source_id])

        self.assertIn("Thomas Lundmark", rows["KB-38"])
        self.assertIn("unedited draft гл. 9", rows["KB-38"])
        self.assertIn("техническое metadata-имя `Kim Vollrodt` не является авторством", rows["KB-38"])

        self.assertIn("David L. Faigman", rows["KB-39"])
        self.assertIn("exact binary duplicate", rows["KB-39"])
        self.assertIn("no_new_source_family", rows["KB-39"])

        for editor in (
            "Jürgen de Poorter",
            "Gerhard van der Schyff",
            "Maarten Stremler",
            "Maartje De Visser",
        ):
            self.assertIn(editor, rows["KB-40"])
        self.assertIn("(eds.)", rows["KB-40"])
        self.assertIn("Методическая глава: Willem Mingelen, Jerfi Uzman", rows["KB-40"])
        self.assertIn("Редакторы являются авторами только вводной гл. 1", rows["KB-40"])

        for editor in (
            "Monica K. Miller",
            "Logan A. Yelderman",
            "Matthew T. Huss",
            "Jason A. Cantone",
        ):
            self.assertIn(editor, rows["KB-41"])
        self.assertIn("(eds.)", rows["KB-41"])
        self.assertIn("Авторы проверенных глав:", rows["KB-41"])
        for chapter_authors in (
            "Jason A. Cantone, Jeremy Fogel, Mary Hoopes",
            "Bethany Growns, Tess M. S. Neal",
            "Daniel A. Krauss, William Ellsworth",
            "Jane Goodman-Delahunty, William E. Foote",
        ):
            self.assertIn(chapter_authors, rows["KB-41"])
        self.assertIn("Редакторы тома не считаются авторами иных глав", rows["KB-41"])

        authors_doc = text("docs/KSRF_ANALYZED_AUTHORS.md")
        self.assertIn("41 локально проверенной файловой записи", authors_doc)
        self.assertIn("40 независимых source families", authors_doc)
        for token in (
            "Thomas Lundmark — автор проверенного unedited draft главы 9",
            "Jürgen de Poorter, Gerhard van der Schyff, Maarten Stremler и Maartje De Visser — редакторы тома",
            "методическая глава 11 принадлежит Willem Mingelen и Jerfi Uzman",
            "Monica K. Miller, Logan A. Yelderman, Matthew T. Huss и Jason A. Cantone — редакторы тома",
        ):
            self.assertIn(token, authors_doc)

        old_provenance = text("docs/KSRF_ACADEMIC_RUNTIME_PROVENANCE.md")
        self.assertIn("Жалоба А. Д. Краснощекова", old_provenance)
        self.assertIn("Авторство текста отдельно не установлено", old_provenance)
        self.assertNotIn("жалобы Крылова", old_provenance)
        self.assertGreaterEqual(old_provenance.count("тот же exact binary"), 2)
        self.assertGreaterEqual(old_provenance.count("same_binary_reused_source"), 2)
        self.assertIn("ID остаются стабильными", registry)

    def test_public_authorship_and_method_docs_link_registry(self):
        registry_name = "KSRF_ACADEMIC_METHOD_SOURCES_2026-09.md"
        self.assertIn(registry_name, text("docs/KSRF_ANALYZED_AUTHORS.md"))
        self.assertIn(registry_name, text("docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"))
        provenance_name = "KSRF_ACADEMIC_RUNTIME_PROVENANCE.md"
        self.assertIn(provenance_name, text("README.md"))
        self.assertIn(provenance_name, text("docs/KSRF_ANALYZED_AUTHORS.md"))

    def test_readme_keeps_methodology_before_case_start_and_installation_below(self):
        readme = text("README.md")
        methodology = readme.index("## Методология как цифровой маршрут")
        case_start = readme.index("## С чего начать по своему делу")
        installation = readme.index("## Установка на чистый ноутбук")
        self.assertLess(methodology, case_start)
        self.assertLess(case_start, installation)

    def test_package_manifest_stays_at_sixteen(self):
        manifest = json.loads(text("skills-manifest.json"))
        self.assertEqual(manifest["total_skills"], 16)


if __name__ == "__main__":
    unittest.main()
