from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
METHODS = {
    "ksrf-rights-argument-builder": "status-incompatibility-and-qualified-silence.md",
    "ksrf-doctrine-research": "amicus-interpretation-and-remedy.md",
}
CASE_IDS = {
    "ksrf-rights-argument-builder": range(18, 24),
    "ksrf-doctrine-research": range(5, 11),
}


class StatusAndAmicusMethodsTests(unittest.TestCase):
    def test_methods_have_owner_and_cycle_routes(self) -> None:
        cycle = (REPO / "skills/ksrf-complaint-cycle/SKILL.md").read_text()
        for skill, filename in METHODS.items():
            owner = REPO / "skills" / skill
            method = owner / "references" / filename
            with self.subTest(skill=skill):
                self.assertIn(filename, (owner / "SKILL.md").read_text())
                self.assertIn(filename, cycle)
                content = method.read_text()
                self.assertIn("## Первый проход", content)
                self.assertIn("## Второй проход", content)
                for target in re.findall(r"\]\(([^)]+)\)", content):
                    if not target.startswith(("https://", "http://", "#")):
                        resolved = (method.parent / target.split("#")[0]).resolve()
                        self.assertTrue(resolved.is_relative_to(REPO / "skills"))
                        self.assertTrue(resolved.is_file())

    def test_status_method_does_not_overclaim_the_holding(self) -> None:
        content = (REPO / "skills/ksrf-rights-argument-builder/references" / METHODS["ksrf-rights-argument-builder"]).read_text()
        for boundary in (
            "Не выводи разрешение только из отсутствия",
            "Угроза прекращения статуса не равна состоявшемуся прекращению",
            "Количество согласующихся норм не доказывает волю законодателя",
            "Это не признание нормы неконституционной",
            "не доказательство уже состоявшегося пересмотра",
            "Суд не исключает иное законодательное решение",
            "не является мотивировкой большинства",
            "не переносится в сегодняшнюю проверку исчерпания",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_amicus_keeps_source_and_remedy_roles(self) -> None:
        content = (REPO / "skills/ksrf-doctrine-research/references" / METHODS["ksrf-doctrine-research"]).read_text()
        for boundary in (
            "Совместное нахождение с жалобой в одной папке не связывает документы",
            "Ненайденная стенограмма не доказывает отсутствие",
            "не считай голоса методов",
            "не равен действующему сроку",
            "не № 29-П/2019",
            "Сходство рассуждения не доказывает",
            "сноске 1 на с. 2",
            "предоставление материалов: А.В. Должиков",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_synthetic_cases_have_complete_inputs_without_originals(self) -> None:
        for skill, added_ids in CASE_IDS.items():
            payload = json.loads((REPO / "skills" / skill / "evals/evals.json").read_text())
            cases = {entry["id"]: entry for entry in payload["evals"]}
            self.assertEqual(len(cases), len(payload["evals"]))
            for number in added_ids:
                with self.subTest(skill=skill, number=number):
                    entry = cases[number]
                    self.assertEqual(entry["files"], [])
                    self.assertTrue(entry["prompt"] and entry["expected_output"])
                    self.assertGreaterEqual(len(entry["expectations"]), 3)
                    serialized = json.dumps(entry, ensure_ascii=False)
                    for prohibited in ("/Users/", "/private/tmp/", "415799", "230222", "Сухов"):
                        self.assertNotIn(prohibited, serialized)

    def test_added_cases_preserve_distinct_failure_modes(self) -> None:
        required = {
            "ksrf-rights-argument-builder": {18: "угрозу", 19: "Отсутствие", 20: "Пересмотр", 21: "сравнимость", 22: "исчерпание", 23: "главную страницу"},
            "ksrf-doctrine-research": {5: "каждого", 6: "приобщению", 7: "Неполный архив", 8: "голосами", 9: "индивидуальные", 10: "применимость во времени"},
        }
        for skill, traps in required.items():
            payload = json.loads((REPO / "skills" / skill / "evals/evals.json").read_text())
            cases = {entry["id"]: entry for entry in payload["evals"]}
            for number, trap in traps.items():
                with self.subTest(skill=skill, number=number):
                    self.assertIn(trap, " ".join(cases[number]["expectations"]))

    def test_public_documentation_has_separate_active_source_links(self) -> None:
        for filename in ("KSRF_ANALYZED_AUTHORS.md", "KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"):
            content = (REPO / "docs" / filename).read_text()
            for url in (
                "https://advokatsuhovoleg.ru/",
                "https://doc.ksrf.ru/decision/KSRFDecision415799.pdf",
                "https://academia.ilpp.ru/wp-content/uploads/2021/05/2016-Amicus-Curiae-Brief.pdf",
                "https://www.ksrf.ru/doc/KSRFDecision230222.pdf",
            ):
                self.assertIn(f"]({url})", content)
            self.assertIn("предостав", content)
            self.assertIn("О.Б. Сидорович", content)

    def test_install_contains_methods_but_not_source_evals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            for skill, filename in METHODS.items():
                relative = Path(skill) / "references" / filename
                self.assertEqual((target / relative).read_bytes(), (REPO / "skills" / relative).read_bytes())
                self.assertFalse((target / skill / "evals").exists())
            self.assertFalse(list(target.rglob("*.doc")))
            self.assertFalse(list(target.rglob("*.pdf")))


if __name__ == "__main__":
    unittest.main()
