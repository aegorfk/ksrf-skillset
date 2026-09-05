from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import CASE_SURFACE, EXAMPLES, copy_skillset


REPO = Path(__file__).resolve().parents[1]
FACTS = REPO / "skills/ksrf-complaint-facts-demands"
METHOD = FACTS / "references/reparative-guarantee-access.md"


class ReparativeGuaranteeAccessTests(unittest.TestCase):
    def test_method_preserves_eligibility_application_and_remedy_limits(self) -> None:
        method = METHOD.read_text()
        for wording in (
            "ReparativeGuaranteeAccessMatrix",
            "восстановительную гарантию от обычной социальной помощи",
            "родство само по себе не даёт всем потомкам одинакового права",
            "Пустое поле не считается подтверждением",
            "Предполагаемый будущий отказ",
            "не заменяет доказательство решающей роли",
            "Не переноси срок или последнюю инстанцию из одной цепочки в другую",
            "не персональный прогноз срока",
            "поступления и выбытия",
            "компетенцию законодателя",
            "не откладывает этот пересмотр до принятия поправок",
            "проверь последующие изменения и действующий механизм",
            "Выбор правовой позиции остаётся за человеком",
        ):
            with self.subTest(wording=wording):
                self.assertIn(wording, method)

    def test_routes_remain_inside_the_workflow_and_resolve(self) -> None:
        facts = (FACTS / "SKILL.md").read_text()
        self.assertLess(facts.index("\n5."), facts.index(METHOD.name))
        self.assertLess(facts.index(METHOD.name), facts.index("\n6."))
        qa = (REPO / "skills/ksrf-complaint-qa/SKILL.md").read_text()
        self.assertLess(qa.index("\n5.3."), qa.index("\n5.4."))
        self.assertLess(qa.index("\n5.4."), qa.index("\n6."))
        self.assertIn(METHOD.name, qa)
        self.assertIn(METHOD.name, EXAMPLES["39"].read_text())
        for path in (METHOD, EXAMPLES["39"]):
            for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                if not target.startswith(("https://", "http://", "#")):
                    self.assertTrue((path.parent / target.split("#")[0]).resolve().is_file(), target)

    def test_card_preserves_source_actor_and_operative_boundaries(self) -> None:
        card = EXAMPLES["39"].read_text()
        for wording in (
            "Жалобы двух других заявительниц здесь не анализировались",
            "Мнение судьи К.В. Арановского",
            "не является позицией большинства",
            "свежая доступность не подтверждена",
            "а не новая успешная сетевая загрузка",
            "п. 3 резолютивной части, с. 28",
            "п. 2 и 4 резолютивной части, с. 27–28",
            "пересмотр не отложен до поправок",
            "немедленная выдача квартиры не установлены",
            "единоличное авторство",
        ):
            self.assertIn(wording.casefold(), card.casefold())

    def test_public_credit_is_complete_and_inside_existing_tables(self) -> None:
        for path in (
            EXAMPLES["39"],
            REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md",
            REPO / "docs/KSRF_ANALYZED_AUTHORS.md",
        ):
            text = path.read_text()
            for url in CASE_SURFACE["39"]["urls"]:
                self.assertIn(url, text)
            self.assertIn("Григорий Викторович Вайпан", text)
        sources = (REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md").read_text()
        row = next(line for line in sources.splitlines() if line.startswith("| Евгения Борисовна Шашева;"))
        self.assertEqual(row.count("|"), 6)
        self.assertIn(row + "\n| Семья Однодворцевых;", sources)
        authors = (REPO / "docs/KSRF_ANALYZED_AUTHORS.md").read_text()
        author_row = next(line for line in authors.splitlines() if line.startswith("| 18 |"))
        self.assertEqual(author_row.count("|"), 5)
        self.assertTrue(author_row.endswith(" |"))
        self.assertIn("жалобы Е.Б. Шашевой", author_row)

    def test_synthetic_evals_are_complete_without_source_files(self) -> None:
        suites = {
            "ksrf-explore-arguments": (13, 16),
            "ksrf-complaint-qa": (26, 40),
        }
        for skill, (first, last) in suites.items():
            payload = json.loads((REPO / "skills" / skill / "evals/evals.json").read_text())
            cases = {entry["id"]: entry for entry in payload["evals"]}
            self.assertEqual(len(cases), len(payload["evals"]))
            self.assertEqual(set(cases), set(range(1, last + 1)))
            for number in range(first, last + 1):
                entry = cases[number]
                self.assertEqual(entry["files"], [])
                self.assertGreaterEqual(len(entry["expectations"]), 3)
                self.assertTrue(entry["prompt"] and entry["expected_output"])
        exploration = json.loads((REPO / "skills/ksrf-explore-arguments/evals/evals.json").read_text())
        joined = json.dumps(exploration["evals"][-4:], ensure_ascii=False)
        for trap in ("внуком", "50000", "мнение судьи", "10 лет"):
            self.assertIn(trap.casefold(), joined.casefold())

    def test_new_method_and_card_install_without_eval_or_original(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            installed = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", installed)
            for path in (METHOD, EXAMPLES["39"]):
                target = installed / path.relative_to(REPO / "skills")
                self.assertEqual(target.read_bytes(), path.read_bytes())
            self.assertFalse(list(installed.rglob("evals")))
            self.assertFalse(list(installed.rglob("*.pdf")))
            self.assertFalse(list(installed.rglob("Шашева*")))


if __name__ == "__main__":
    unittest.main()
