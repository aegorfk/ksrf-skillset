from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
CARD = Path("ksrf-rights-argument-builder/references/qualification-and-safeguard-cascade.md")
CASE_IDS = {
    "ksrf-rights-argument-builder": (82, 83, 84, 85),
    "ksrf-complaint-qa": (46, 47),
}
OFFICIAL_URL = "https://www.ksrf.ru/doc/KSRFDecision810564.pdf"


class QualificationSafeguardMethodsTests(unittest.TestCase):
    def test_two_pass_route_and_link_integrity(self) -> None:
        source = (REPO / "skills" / CARD).read_text()
        first, second = source.split("## Второй проход:", 1)
        self.assertIn("## Первый проход:", first)
        self.assertNotRegex(first, r"KSRFDecision|3-П|2025|gold_label|held_out")
        self.assertIn(OFFICIAL_URL, second)
        for skill in CASE_IDS:
            owner = REPO / "skills" / skill / "SKILL.md"
            links = re.findall(r"\]\(([^)]+)\)", owner.read_text())
            routed = [link for link in links if link.endswith(CARD.name)]
            with self.subTest(skill=skill):
                self.assertEqual(len(routed), 1)
                self.assertEqual((owner.parent / routed[0]).resolve(), (REPO / "skills" / CARD).resolve())
        for link in re.findall(r"\]\(([^)]+)\)", source):
            if not link.startswith(("http:", "https:", "#")):
                target = (REPO / "skills" / CARD.parent / link).resolve()
                self.assertTrue(target.is_relative_to(REPO / "skills"))
                self.assertTrue(target.is_file())

    def test_method_keeps_distinct_conditions(self) -> None:
        source = (REPO / "skills" / CARD).read_text()
        for marker in (
            "Одинаковая потеря не доказывает тождество правовых режимов",
            "Раздели факт, запись и правовую презумпцию",
            "Знание одного публичного органа не считается автоматически знанием другого",
            "Самая ранняя дата сама по себе не запускает срок",
            "не исцеляет дефект первоначального основания права",
            "Если гарантия уже установлена",
            "Если остаётся иной нормативный вопрос",
            "Не заменяй акт удобным решением молча",
            "Несколько жалоб не доказывают устойчивую судебную практику",
            "Не считай его итогом любого похожего проекта жалобы",
            "единство публичной власти",
            "не позволяет игнорировать установленное правом правило вменения знания",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_scenarios_are_self_contained_and_nonreconstructive(self) -> None:
        for skill, identifiers in CASE_IDS.items():
            data = json.loads((REPO / "skills" / skill / "evals/evals.json").read_text())
            cases = {case["id"]: case for case in data["evals"]}
            self.assertEqual(len(cases), len(data["evals"]))
            for identifier in identifiers:
                case = cases[identifier]
                with self.subTest(skill=skill, identifier=identifier):
                    self.assertTrue(case["prompt"].startswith("Синтетический сценарий."))
                    self.assertEqual(case["files"], [])
                    self.assertTrue(case["expected_output"])
                    self.assertGreaterEqual(len(case["expectations"]), 4)
                    self.assertNotRegex(
                        json.dumps(case, ensure_ascii=False),
                        r"https?://|/Users/|ТЗ/|KSRFDecision|\.pdf|3-П|земельн|лесног",
                    )

    def test_source_documentation_links_to_method_not_private_material(self) -> None:
        docs = (REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md").read_text()
        paragraph = next(line for line in docs.splitlines() if CARD.name in line)
        self.assertIn(OFFICIAL_URL, paragraph)
        self.assertNotRegex(paragraph, r"/Users/|ТЗ/|mail.google|частный проект|SHA-256")
        self.assertIn("уже разрешённый вопрос", paragraph)

    def test_clean_install_has_method_without_source_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            self.assertEqual((target / CARD).read_bytes(), (REPO / "skills" / CARD).read_bytes())
            for suffix in ("*.doc", "*.docx", "*.pdf", "*.eml", "*.ocr"):
                self.assertFalse(list(target.rglob(suffix)))

    def test_public_credits_preserve_confirmed_roles(self) -> None:
        source_url = "https://constitutional-center.ru/delo-sochinskih-sadovodov-v-konstituczionnom-sude-rf/"
        card = (REPO / "skills" / CARD).read_text()
        first, second = card.split("## Второй проход:", 1)
        self.assertNotIn("Озов", first)
        self.assertIn(source_url, second)
        self.assertIn("не доказательство авторства любой обезличенной версии жалобы", second)
        for filename in ("KSRF_ANALYZED_AUTHORS.md", "KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"):
            content = (REPO / "docs" / filename).read_text()
            with self.subTest(filename=filename):
                self.assertIn("Надежда Алексеевна Озова", content)
                self.assertIn(source_url, content)
                self.assertIn(OFFICIAL_URL, content)
                rows = [
                    int(value)
                    for value in re.findall(r"^\| (\d+) \|", content, re.MULTILINE)
                ]
                self.assertEqual(rows, list(range(1, len(rows) + 1)))


if __name__ == "__main__":
    unittest.main()
