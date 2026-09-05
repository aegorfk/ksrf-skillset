from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
METHODS = {
    "ksrf-rights-argument-builder": "procedural-obstacles-and-benefit-comparators.md",
    "ksrf-doctrine-research": "institutional-opinions-and-normative-uncertainty.md",
}
COHORTS = {
    "ksrf-rights-argument-builder": range(39, 47),
    "ksrf-doctrine-research": range(17, 25),
}


class SourceOutcomeComparisonTests(unittest.TestCase):
    def method(self, owner: str) -> str:
        return (REPO / "skills" / owner / "references" / METHODS[owner]).read_text()

    def test_methods_are_two_pass_and_reachable(self) -> None:
        for owner, filename in METHODS.items():
            for entrypoint in (owner, "ksrf-complaint-cycle", "ksrf-complaint-qa"):
                with self.subTest(owner=owner, entrypoint=entrypoint):
                    self.assertIn(filename, (REPO / "skills" / entrypoint / "SKILL.md").read_text())
            content = self.method(owner)
            self.assertIn("## Первый проход", content)
            self.assertIn("## Второй проход", content)
            parent = REPO / "skills" / owner / "references"
            for target in re.findall(r"\]\(([^)]+)\)", content):
                if not target.startswith(("https://", "http://", "#")):
                    resolved = (parent / target.split("#")[0]).resolve()
                    self.assertTrue(resolved.is_relative_to(REPO / "skills"))
                    self.assertTrue(resolved.is_file())

    def test_procedural_and_benefit_boundaries(self) -> None:
        content = self.method("ksrf-rights-argument-builder")
        for marker in (
            "Отдели молчание закона от запрета",
            "Право инициировать дело не предрешает его исход",
            "сравнимую группу и носителя расходов",
            "письменного ответа",
            "не принятие жалобы КС РФ",
            "неограниченного права любого лица",
            "собственные итоговые акты не установлены",
            "Указание на пересмотр не доказывает фактическое восстановление права",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, content)

    def test_expert_and_court_roles_remain_distinct(self) -> None:
        content = self.method("ksrf-doctrine-research")
        for marker in (
            "Донор не равен автору",
            "Не восстанавливай скрытые имена",
            "Свобода выбора и обязанность зарегистрировать выбор",
            "Фискальный платёж и обеспечение",
            "Не исправляй противоречивые даты источника молча",
            "принадлежность мнения к этому производству не подтверждена",
            "Суд не утвердил все предложенные экспертом ограничения",
            "Не представляй его как удовлетворённую индивидуальную жалобу",
            "мнение большинства и особые мнения",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, content)

    def test_scenarios_are_self_contained_and_synthetic(self) -> None:
        for owner, identifiers in COHORTS.items():
            payload = json.loads((REPO / "skills" / owner / "evals/evals.json").read_text())
            entries = {entry["id"]: entry for entry in payload["evals"]}
            self.assertEqual(len(entries), len(payload["evals"]))
            for identifier in identifiers:
                with self.subTest(owner=owner, identifier=identifier):
                    entry = entries[identifier]
                    self.assertEqual(entry["files"], [])
                    self.assertTrue(entry["prompt"].startswith("Синтетический сценарий."))
                    self.assertTrue(entry["expected_output"])
                    self.assertGreaterEqual(len(entry["expectations"]), 3)
                    serialized = json.dumps(entry, ensure_ascii=False)
                    for forbidden in ("Тимошенко", "Исарлов", "Ермилова", "Понятовский", "Рощин", "Качанов", "Толстой", "Анцинова", "Жуковский", "Делова", "http", "/Users/", "ТЗ/", ".pdf", "КС РФ №"):
                        self.assertNotIn(forbidden, serialized)

    def test_public_attribution_preserves_document_roles(self) -> None:
        docs = (REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md").read_text()
        authors = (REPO / "docs/KSRF_ANALYZED_AUTHORS.md").read_text()
        for document in (docs, authors):
            for url in (
                "http://sutyajnik.ru/documents/551.html",
                "http://sutyajnik.ru/documents/2498.html",
                "http://sutyajnik.ru/documents/4423.html",
                "http://sutyajnik.ru/documents/4440.html",
                "http://sutyajnik.ru/rus/actions/p_v_gov/complaint.htm",
                "https://spbu.ru/sites/default/files/expert_zapros_judge_constitutional.pdf",
            ):
                self.assertIn(url, document)
        self.assertIn("Р.Е. Качанов", authors)
        self.assertIn("Антон Леонидович Бурков", authors)
        self.assertIn("не заполнены реквизиты заявителя", docs)
        self.assertIn("тематический ориентир", docs)
        self.assertIn("исходники и извлечённые тексты не размещаются", docs)

    def test_first_pass_has_no_case_outcome_answer_key(self) -> None:
        for owner in METHODS:
            first_pass = self.method(owner).split("## Второй проход")[0]
            self.assertNotRegex(first_pass, r"KSRFDecision|№ \d+[-‑][ПО]")
            for forbidden in ("gold_label", "held_out", "eval_input", "runner_input", "judge_score"):
                self.assertNotIn(forbidden, first_pass)


if __name__ == "__main__":
    unittest.main()
