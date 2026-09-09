from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
METHODS = {
    "ksrf-rights-argument-builder": "legal-effect-and-guarantee-timing.md",
    "ksrf-doctrine-research": "adversarial-opinions-and-tax-harm.md",
}
CASE_IDS = {
    "ksrf-rights-argument-builder": range(53, 61),
    "ksrf-doctrine-research": range(31, 37),
}


class SocialTaxSourceMethodsTests(unittest.TestCase):
    def method_text(self, skill: str) -> str:
        return (REPO / "skills" / skill / "references" / METHODS[skill]).read_text()

    def test_methods_are_reachable_and_two_pass(self) -> None:
        for skill, filename in METHODS.items():
            with self.subTest(skill=skill):
                for owner in (skill, "ksrf-complaint-cycle", "ksrf-complaint-qa"):
                    self.assertIn(filename, (REPO / "skills" / owner / "SKILL.md").read_text())
                content = self.method_text(skill)
                self.assertIn("## Первый проход", content)
                self.assertIn("## Второй проход", content)
                for target in re.findall(r"\]\(([^)]+)\)", content):
                    if not target.startswith(("https://", "http://", "#")):
                        path = (REPO / "skills" / skill / "references" / target).resolve()
                        self.assertTrue(path.is_relative_to(REPO / "skills"))
                        self.assertTrue(path.is_file())

    def test_social_and_import_limits_are_preserved(self) -> None:
        content = self.method_text("ksrf-rights-argument-builder")
        for boundary in (
            "запрос Конаковского городского суда",
            "при соблюдении остальных условий",
            "до увольнения",
            "не означает автоматического восстановления",
            "право покупателя на вычет",
            "если убытки не сопоставимы",
            "ненадлежащим качеством",
            "не устанавливает сегодняшний режим параллельного импорта",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_opinions_do_not_become_a_single_holding(self) -> None:
        content = self.method_text("ksrf-doctrine-research")
        for boundary in (
            "не три прочитанные конституционные жалобы",
            "существенное расхождение версий",
            "не содержит позиции по существу",
            "Формальная запись о ликвидации не универсальная",
            "но не налоговые штрафы организации",
            "не обладают заранее большей доказательственной силой",
            "Их неконституционность не установлена",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_scenarios_are_synthetic_and_require_no_originals(self) -> None:
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
                    self.assertNotRegex(json.dumps(case, ensure_ascii=False), r"https?://|/Users/|ТЗ/|Ахмадеев|Подоляцк|Чамин|Камснаб")

    def test_public_credit_has_six_final_act_links(self) -> None:
        for filename in ("KSRF_ANALYZED_AUTHORS.md", "KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"):
            content = (REPO / "docs" / filename).read_text()
            for decision in ("543098", "884035", "537843", "163154", "303993", "315752"):
                self.assertRegex(content, rf"\]\(https://(?:doc\.ksrf\.ru/decision|www\.ksrf\.ru/doc)/KSRFDecision{decision}\.pdf\)")
            self.assertIn("https://lfpspb.com/profsoyuz-pomog/", content)
            self.assertIn("https://www.lfpspb.com/news/", content)
            self.assertIn("Николай Сергеевич Подоляцкий", content)
            self.assertIn("Фардана Абдулловна Хафизова", content)
            self.assertIn("Максим Александрович Сосов", content)
            self.assertIn("](https://law-paragon.ru/paragonteam/)", content)
            self.assertIn("](https://profile.ru/society/neispovedimye-puti-importa-3856/)", content)
            self.assertNotIn("https://pag.company/", content)
            self.assertIn("](https://www.zdravo-expo.ru/ru/ci/20055/)", content)

    def test_pag_author_full_name_is_consistent(self) -> None:
        sources = [self.method_text("ksrf-rights-argument-builder")]
        for filename in ("KSRF_ANALYZED_AUTHORS.md", "KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"):
            sources.append((REPO / "docs" / filename).read_text())
        for content in sources:
            self.assertIn("Максим Александрович Сосов", content)
            self.assertNotIn("Соснов", content)
            self.assertNotRegex(content, r"Максим(?:а)? Сосов(?:а)?")

    def test_install_keeps_methods_without_source_evals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            for skill, filename in METHODS.items():
                relative = Path(skill) / "references" / filename
                self.assertEqual((target / relative).read_bytes(), (REPO / "skills" / relative).read_bytes())
                self.assertFalse((target / skill / "evals").exists())
            for suffix in ("*.doc", "*.docx", "*.pdf", "*ocr*"):
                self.assertFalse(list(target.rglob(suffix)))


if __name__ == "__main__":
    unittest.main()
