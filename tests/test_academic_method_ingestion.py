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
            "skills/ksrf-complaint-facts-demands/evals/evals.json": (14, 15, 16, 17, 18),
            "skills/ksrf-rights-argument-builder/evals/evals.json": (74, 75),
            "skills/ksrf-complaint-qa/evals/evals.json": (41,),
            "skills/constitutional-comparative-research/evals/evals.json": (22,),
            "skills/ksrf-exhaustion-planner/evals/evals.json": (4,),
            "skills/ksrf-argument-patterns/evals/evals.json": (25,),
            "skills/ksrf-decision-execution/evals/evals.json": (16,),
        }
        for path, expected_ids in expected.items():
            payload = json.loads(text(path))
            ids = [item["id"] for item in payload["evals"]]
            self.assertEqual(len(ids), len(set(ids)), path)
            for eval_id in expected_ids:
                self.assertIn(eval_id, ids, path)


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

    def test_thirty_seven_sources_are_documented_outside_runtime(self):
        registry = text("docs/KSRF_ACADEMIC_METHOD_SOURCES_2026-09.md")
        self.assertIn("source_count: 37", registry)
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
        self.assertEqual(registry.count("| KB-"), 37)

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
