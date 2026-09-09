from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
METHODS = {
    "ksrf-rights-argument-builder": "public-levy-and-independent-guarantees.md",
    "ksrf-doctrine-research": "contested-levy-opinions.md",
}
CASE_IDS = {
    "ksrf-rights-argument-builder": range(68, 74),
    "ksrf-doctrine-research": range(42, 46),
    "ksrf-decision-execution": range(14, 16),
}


class PublicLevySourceMethodsTests(unittest.TestCase):
    def method_text(self, skill: str) -> str:
        return (REPO / "skills" / skill / "references" / METHODS[skill]).read_text()

    def test_routes_and_independent_first_pass(self) -> None:
        for skill, filename in METHODS.items():
            for owner in (skill, "ksrf-complaint-cycle", "ksrf-complaint-qa"):
                self.assertIn(filename, (REPO / "skills" / owner / "SKILL.md").read_text())
            content = self.method_text(skill)
            first, second = content.split("## Второй проход:", 1)
            self.assertIn("## Первый проход:", first)
            self.assertNotRegex(first, r"Султанов|Sultanov|Нижнекамск|Газэнергосеть|11-П|449-О-Р")
            self.assertTrue(second.strip())
            for target in re.findall(r"\]\(([^)]+)\)", content):
                if not target.startswith(("https://", "http://", "#")):
                    resolved = (REPO / "skills" / skill / "references" / target).resolve()
                    self.assertTrue(resolved.is_relative_to(REPO / "skills"))
                    self.assertTrue(resolved.is_file())
        execution = (REPO / "skills/ksrf-decision-execution/SKILL.md").read_text()
        self.assertIn(METHODS["ksrf-rights-argument-builder"], execution)

    def test_guarantee_and_remedy_boundaries(self) -> None:
        content = self.method_text("ksrf-rights-argument-builder")
        for boundary in (
            "не доказывает штрафную природу",
            "весь КоАП РФ",
            "Раздели вину и бремя",
            "молчание специальной статьи",
            "солидарность требует своего основания",
            "Одинаковое число лет",
            "не устанавливает сегодняшний срок",
            "а не отменил их",
            "несогласие с отказом арбитражного суда",
            "не равна уже состоявшейся отмене",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_expert_roles_and_disagreement(self) -> None:
        content = self.method_text("ksrf-doctrine-research")
        for boundary in (
            "Автор текста — Н.И. Клейн",
            "утверждение В.М. Жуйкова",
            "письмо В.Ф. Попондопуло",
            "вина не нужна",
            "Это существенное возражение жалобам",
            "Срок исполнения и срок назначения",
            "не доказывает влияние эксперта",
            "не как отмену решения большинства",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_synthetic_cases_are_portable(self) -> None:
        for skill, required in CASE_IDS.items():
            data = json.loads((REPO / "skills" / skill / "evals/evals.json").read_text())
            identifiers = [case["id"] for case in data["evals"]]
            self.assertEqual(len(identifiers), len(set(identifiers)))
            cases = {case["id"]: case for case in data["evals"]}
            for number in required:
                case = cases[number]
                with self.subTest(skill=skill, number=number):
                    self.assertTrue(case["prompt"].startswith("Синтетический сценарий."))
                    self.assertEqual(case["files"], [])
                    self.assertGreaterEqual(len(case["expectations"]), 3)
                    self.assertTrue(case["expected_output"])
                    self.assertNotRegex(json.dumps(case, ensure_ascii=False), r"https?://|/Users/|ТЗ/|Султанов|Sultanov|Нижнекамск|Газэнергосеть|11-П|449-О-Р")

    def test_public_credit_and_final_acts(self) -> None:
        for filename in ("KSRF_ANALYZED_AUTHORS.md", "KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"):
            content = (REPO / "docs" / filename).read_text()
            for required in (
                "Aidar Sultanov", "Клейн", "Варламов", "Лебедев", "Эрделевск", "Посашков",
                "](https://urfaq.com/sultanov)",
                "](https://www.consultant.ru/document/cons_doc_LAW_89224/)",
                "](https://www.consultant.ru/document/cons_doc_LAW_128370/)",
            ):
                self.assertIn(required, content)
            numbers = [int(number) for number in re.findall(r"^\| (\d+) \|", content, re.MULTILINE)]
            self.assertEqual(numbers, list(range(1, len(numbers) + 1)))

    def test_install_preserves_methods_without_originals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            for skill, filename in METHODS.items():
                relative = Path(skill) / "references" / filename
                self.assertEqual((target / relative).read_bytes(), (REPO / "skills" / relative).read_bytes())
                self.assertFalse((target / skill / "evals").exists())
            for suffix in ("*.pdf", "*.docx", "*.png", "*ocr*"):
                self.assertFalse(list(target.rglob(suffix)))


if __name__ == "__main__":
    unittest.main()
