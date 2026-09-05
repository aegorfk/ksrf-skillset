from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
METHODS = {
    "ksrf-doctrine-research": "archived-submissions-and-role-transitions.md",
    "ksrf-rights-argument-builder": "proportionality-and-social-protection.md",
}
COHORTS = {
    "ksrf-doctrine-research": range(25, 31),
    "ksrf-rights-argument-builder": range(47, 53),
}


class ArchivedSubmissionMethodsTests(unittest.TestCase):
    def method(self, owner: str) -> str:
        return (REPO / "skills" / owner / "references" / METHODS[owner]).read_text()

    def test_routes_and_local_links(self) -> None:
        for owner, filename in METHODS.items():
            for entrypoint in (owner, "ksrf-complaint-cycle", "ksrf-complaint-qa"):
                with self.subTest(owner=owner, entrypoint=entrypoint):
                    self.assertIn(filename, (REPO / "skills" / entrypoint / "SKILL.md").read_text())
            content = self.method(owner)
            self.assertEqual(content.count("## Первый проход"), 1)
            self.assertEqual(content.count("## Второй проход"), 1)
            parent = REPO / "skills" / owner / "references"
            for target in re.findall(r"\]\(([^)]+)\)", content):
                if not target.startswith(("https://", "http://", "#")):
                    resolved = (parent / target.split("#")[0]).resolve()
                    self.assertTrue(resolved.is_relative_to(REPO / "skills"))
                    self.assertTrue(resolved.is_file())

    def test_first_pass_does_not_leak_historical_outcome(self) -> None:
        for owner in METHODS:
            first_pass = self.method(owner).split("## Второй проход")[0]
            self.assertNotRegex(first_pass, r"KSRFDecision|№ \d+[-‑][ПО]|ЮКОС")
            for forbidden in ("gold_label", "held_out", "eval_input", "runner_input", "judge_score"):
                self.assertNotIn(forbidden, first_pass)

    def test_archive_and_judicial_boundaries(self) -> None:
        content = self.method("ksrf-doctrine-research")
        for marker in (
            "Дата снимка не является датой составления или подачи",
            "Не удваивай поддержку",
            "Донор, издатель, разработчик, подписант",
            "носителя нарушенного права, первоначального заявителя",
            "Не рассмотрено не означает отклонено",
            "полный первичный текст",
            "на с. 32 Суд прямо воздержался",
            "на с. 33 не разрешал вопросы",
            "не являются позицией большинства",
            "не исходные документы, OCR",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, content)

    def test_doctrine_is_not_new_law_or_numeric_proof(self) -> None:
        content = self.method("ksrf-rights-argument-builder")
        for marker in (
            "конституционное право, законодательный способ",
            "не доказывает право на любую желаемую сумму",
            "При недостаточной защите",
            "сопоставимую эффективность",
            "придуманную арифметику",
            "не создаёт новое бремя доказывания",
            "спор о компетенции",
            "одна работа, не два независимых подтверждения",
            "не заявляется постраничная экспертиза",
            "не доказывает наличия таких полномочий сегодня",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, content)

    def test_new_scenarios_need_no_private_files(self) -> None:
        for owner, identifiers in COHORTS.items():
            payload = json.loads((REPO / "skills" / owner / "evals/evals.json").read_text())
            entries = {entry["id"]: entry for entry in payload["evals"]}
            self.assertEqual(len(entries), len(payload["evals"]))
            for identifier in identifiers:
                entry = entries[identifier]
                with self.subTest(owner=owner, identifier=identifier):
                    self.assertEqual(entry["files"], [])
                    self.assertTrue(entry["prompt"].startswith("Синтетический сценарий."))
                    self.assertTrue(entry["expected_output"])
                    self.assertGreaterEqual(len(entry["expectations"]), 3)
                    serialized = json.dumps(entry, ensure_ascii=False)
                    for forbidden in ("ЮКОС", "Осборн", "Лаптев", "Должиков", "http", "/Users/", "ТЗ/", ".pdf", "1-П/2017"):
                        self.assertNotIn(forbidden, serialized)

    def test_public_sources_have_exact_snapshots_and_roles(self) -> None:
        docs = (REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md").read_text()
        authors = (REPO / "docs/KSRF_ANALYZED_AUTHORS.md").read_text()
        for document in (docs, authors, self.method("ksrf-doctrine-research")):
            for timestamp in ("20200820081835", "20170329055734", "20200816041522", "20200818131702", "20191016153058", "20191016153018", "20200927091650"):
                self.assertIn("https://web.archive.org/web/" + timestamp + "id_/http://www.ksrf.ru", document)
            self.assertIn("KSRFDecision258613.pdf", document)
        self.assertIn("Internet Archive", docs)
        self.assertIn("не личное заключение А.В. Должикова", docs)
        self.assertIn("подтверждённый канал публикации", docs)
        for document in (docs, authors):
            self.assertIn("https://disser.spbu.ru/files/2022/disser_dolzhikov.pdf", document)
            for author in ("Е.К. Манжосова", "Д.С. Медников", "И.Е. Османкина", "Н.М. Секретарева", "И.В. Рачков"):
                self.assertIn(author, document)
        self.assertEqual(re.findall(r"^## .+$", authors, flags=re.MULTILINE), ["## Основной реестр"])


if __name__ == "__main__":
    unittest.main()
