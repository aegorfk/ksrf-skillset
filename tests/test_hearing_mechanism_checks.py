from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
CARD = Path("ksrf-argument-patterns/references/hearing-mechanism-checks.md")


class HearingMechanismChecksTests(unittest.TestCase):
    def test_routes_and_source_separation(self) -> None:
        card = REPO / "skills" / CARD
        text = card.read_text()
        first, second = text.split("## Второй проход", 1)
        self.assertNotRegex(first, r"KSRFDecision|48-П|52-П|53-П|Сафонов")
        for filename in ("KSRFDecision924653.pdf", "KSRFDecision926273.pdf", "KSRFDecision926595.pdf"):
            self.assertIn(f"https://www.ksrf.ru/doc/{filename}", second)
        for skill in ("ksrf-argument-patterns", "ksrf-case-triage"):
            owner = REPO / "skills" / skill / "SKILL.md"
            links = re.findall(r"\]\(([^)]+)\)", owner.read_text())
            routed = [link for link in links if link.endswith(CARD.name)]
            self.assertEqual(len(routed), 1)
            self.assertEqual((owner.parent / routed[0]).resolve(), card.resolve())
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if not link.startswith(("http:", "https:", "#")):
                self.assertTrue((card.parent / link).resolve().is_file())

    def test_distinct_conditions_and_negative_cases(self) -> None:
        text = (REPO / "skills" / CARD).read_text()
        for marker in (
            "Позднее субъективное", "обязанность следить", "старое значение больше не влияет",
            "прежнюю функцию", "временное правило", "Пересмотр прежнего процессуального дела",
            "Специальное начало срока для заявителей", "проверить само условие",
            "бессрочное расследование", "не предрешает иск", "Вопрос судьи, довод стороны",
            "Дата в адресе медиафайла", "не переносятся на срок обращения в КС РФ",
            "специальные сроки и гарантии этой ветви", "простое отрицание причастности",
            "глубину пересмотра стоимости по периодам их дел",
            "Юридическая значимость до достаточности доказательств",
            "само по себе недостаточно без других", "воспроизводит ли он именно спорный барьер",
            "носителем защищаемого права", "итоговый акт по этому заседанию не установлен",
            "не являются проверенными", "не приписывай",
            "Исследуй и оправдание самого исключения", "не предрешает",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertNotRegex(text, r"/Users/|ТЗ/|\d+% перспектив|гарантирует успех")

    def test_prior_hearing_hypotheses_are_qualified_by_final_acts(self) -> None:
        text = (REPO / "skills" / CARD.parent / "hearing-constitutional-justifications.md").read_text()
        self.assertIn("Уточнение по итоговому акту", text)
        self.assertIn("не выводом о неконституционности любого произведения", text)
        self.assertIn("не отменяет прекращение по давности", text)
        self.assertIn(CARD.name, text)

    def test_synthetic_scenarios_have_counterexamples_without_source_answers(self) -> None:
        payload = json.loads((REPO / "tests/fixtures/hearing_mechanism_scenarios.json").read_text())
        cases = payload["cases"]
        self.assertGreaterEqual(len(cases), 11)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        for case in cases:
            self.assertTrue(case["prompt"].startswith("Синтетический сценарий."))
            self.assertGreaterEqual(len(case["expectations"]), 4)
            self.assertNotRegex(json.dumps(case, ensure_ascii=False), r"/Users/|https?://|KSRFDecision|48-П|52-П|53-П")

    def test_clean_install_retains_method_not_test_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            copy_skillset(REPO / "skills", target)
            self.assertEqual((target / CARD).read_bytes(), (REPO / "skills" / CARD).read_bytes())
            self.assertFalse(list(target.rglob("hearing_mechanism_scenarios.json")))
            self.assertFalse(list(target.rglob("*.mp3")))


if __name__ == "__main__":
    unittest.main()
