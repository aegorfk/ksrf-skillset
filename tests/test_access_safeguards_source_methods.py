from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
METHODS = {
    "ksrf-rights-argument-builder": "inspection-recording-and-reviewability.md",
    "ksrf-doctrine-research": "social-support-opinions-and-beneficiary.md",
}
CASE_IDS = {
    "ksrf-rights-argument-builder": range(61, 68),
    "ksrf-doctrine-research": range(37, 42),
}


class AccessSafeguardsSourceMethodsTests(unittest.TestCase):
    def method_text(self, skill: str) -> str:
        return (REPO / "skills" / skill / "references" / METHODS[skill]).read_text()

    def test_routes_and_two_pass_structure(self) -> None:
        for skill, filename in METHODS.items():
            with self.subTest(skill=skill):
                for owner in (skill, "ksrf-complaint-cycle", "ksrf-complaint-qa"):
                    self.assertIn(filename, (REPO / "skills" / owner / "SKILL.md").read_text())
                content = self.method_text(skill)
                first, second = content.split("## Второй проход:", 1)
                self.assertIn("## Первый проход:", first)
                self.assertNotRegex(first, r"Идиятдинов|Передрук|Мошовец|38-П|30-П")
                self.assertTrue(second.strip())
                for target in re.findall(r"\]\(([^)]+)\)", content):
                    if not target.startswith(("https://", "http://", "#")):
                        resolved = (REPO / "skills" / skill / "references" / target).resolve()
                        self.assertTrue(resolved.is_relative_to(REPO / "skills"))
                        self.assertTrue(resolved.is_file())

    def test_inspection_conditions_and_result_are_preserved(self) -> None:
        content = self.method_text("ksrf-rights-argument-builder")
        for boundary in (
            "не означает иммунитета",
            "при версии фактов, установленной судами",
            "не универсальная обязанность заранее",
            "Наличие камеры не доказывает",
            "независимо от требования адвоката",
            "согласием адвоката или его предложением",
            "Дело заявителя не подлежит пересмотру",
            "не всеобщая обязанность составлять протокол",
            "Отношение режимного досмотра к мерам КоАП Суд здесь не разрешал",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_family_positions_are_not_merged(self) -> None:
        content = self.method_text("ksrf-doctrine-research")
        for boundary in (
            "Имя папки не определяет",
            "Отсутствие в Конституции права на конкретную выплату",
            "ни один член семьи",
            "поддержка уже родившегося ребёнка",
            "Если вывод расходится с мотивировкой",
            "не считаются отдельно проанализированными полными актами",
            "не являются его авторскими текстами",
            "служебный исполнитель",
            "отдельное приложение не подменяется",
            "А.Н. Пудов",
            "А.Ю. Кузнецова",
            "М.М. Бесхмельницын",
            "И.В. Ткачев",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_synthetic_scenarios_do_not_require_sources(self) -> None:
        for skill, required in CASE_IDS.items():
            data = json.loads((REPO / "skills" / skill / "evals/evals.json").read_text())
            identifiers = [case["id"] for case in data["evals"]]
            self.assertEqual(len(identifiers), len(set(identifiers)))
            cases = {case["id"]: case for case in data["evals"]}
            for number in required:
                with self.subTest(skill=skill, number=number):
                    case = cases[number]
                    self.assertTrue(case["prompt"].startswith("Синтетический сценарий."))
                    self.assertEqual(case["files"], [])
                    self.assertGreaterEqual(len(case["expectations"]), 3)
                    self.assertTrue(case["expected_output"])
                    self.assertNotRegex(
                        json.dumps(case, ensure_ascii=False),
                        r"https?://|/Users/|ТЗ/|IMG_\d|Идиятдинов|Передрук|Мошовец|Конаков|38-П|30-П",
                    )

    def test_public_attribution_and_active_links(self) -> None:
        for filename in ("KSRF_ANALYZED_AUTHORS.md", "KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"):
            content = (REPO / "docs" / filename).read_text()
            for url in (
                "https://peredruk.ru/",
                "https://mintrud.gov.ru/",
                "https://deti.gov.ru/",
                "https://minjust.gov.ru/ru/",
                "https://epp.genproc.gov.ru/",
                "https://doc.ksrf.ru/decision/KSRFDecision546957.pdf",
                "https://doc.ksrf.ru/decision/KSRFDecision543098.pdf",
                "https://fparf.ru/news/fpa/predusmotret-vozmozhnost-fiksatsii-osnovaniy-khoda-i-rezultatov-dosmotra-/",
            ):
                with self.subTest(filename=filename, url=url):
                    self.assertIn(f"]({url})", content)
            for name in ("Александр Дмитриевич Передрук", "Рамиль Рашитович Идиятдинов", "Р.А. Мошовец"):
                self.assertIn(name, content)
            numbers = [int(number) for number in re.findall(r"^\| (\d+) \|", content, re.MULTILINE)]
            self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
            headings = re.findall(r"^#{2,3} .+$", content, re.MULTILINE)
            self.assertEqual(len(headings), len(set(headings)))

    def test_methods_install_without_private_inputs_or_source_evals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            for skill, filename in METHODS.items():
                relative = Path(skill) / "references" / filename
                self.assertEqual((target / relative).read_bytes(), (REPO / "skills" / relative).read_bytes())
                self.assertFalse((target / skill / "evals").exists())
            for suffix in ("*.doc", "*.docx", "*.jpg", "*.JPG", "*.pdf", "*ocr*"):
                self.assertFalse(list(target.rglob(suffix)))


if __name__ == "__main__":
    unittest.main()
