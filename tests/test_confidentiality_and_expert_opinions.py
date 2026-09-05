from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
METHODS = {
    "ksrf-rights-argument-builder": "confidentiality-and-procedural-safeguards.md",
    "ksrf-doctrine-research": "protected-interest-and-official-publication.md",
}
COHORTS = {
    "ksrf-rights-argument-builder": range(33, 39),
    "ksrf-doctrine-research": range(11, 17),
    "ksrf-decision-execution": range(12, 14),
}


class ConfidentialityAndExpertOpinionsTests(unittest.TestCase):
    def method_text(self, owner: str) -> str:
        return (REPO / "skills" / owner / "references" / METHODS[owner]).read_text()

    def test_methods_are_two_pass_and_reachable(self) -> None:
        for owner, filename in METHODS.items():
            for skill in (owner, "ksrf-complaint-cycle", "ksrf-complaint-qa"):
                with self.subTest(owner=owner, skill=skill):
                    self.assertIn(filename, (REPO / "skills" / skill / "SKILL.md").read_text())
            content = self.method_text(owner)
            for heading in ("## Первый проход", "## Второй проход"):
                self.assertIn(heading, content)
            method = REPO / "skills" / owner / "references" / filename
            for target in re.findall(r"\]\(([^)]+)\)", content):
                if not target.startswith(("https://", "http://", "#")):
                    resolved = (method.parent / target.split("#")[0]).resolve()
                    self.assertTrue(resolved.is_relative_to(REPO / "skills"))
                    self.assertTrue(resolved.is_file())
        self.assertIn(
            METHODS["ksrf-rights-argument-builder"],
            (REPO / "skills/ksrf-decision-execution/SKILL.md").read_text(),
        )

    def test_confidentiality_does_not_create_absolute_immunity(self) -> None:
        content = self.method_text("ksrf-rights-argument-builder")
        for marker in (
            "докажи общий предмет защиты и нормативную связь",
            "Само судебное разрешение не доказывает достаточность гарантий",
            "Отсутствие подозрения в отношении адвоката не создаёт абсолютного иммунитета",
            "обычным нарушением исполнения, а не дефектом нормы",
            "не обязательно устанавливает основания решения",
            "пробел по этому доводу не отменяет самостоятельную линию",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, content)

    def test_historical_remedy_and_partial_result_remain_distinct(self) -> None:
        content = self.method_text("ksrf-rights-argument-builder")
        for marker in (
            "до Постановления от 17.12.2015 № 33-П",
            "Суд не поддержал эту часть довода",
            "если нет иных препятствий",
            "не доказательство состоявшегося пересмотра",
            "Историческое условие не заменяет действующие правила пересмотра",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, content)

    def test_expert_roles_and_publication_status_are_not_inferred(self) -> None:
        content = self.method_text("ksrf-doctrine-research")
        for marker in (
            "Предоставление файла не устанавливает его авторство",
            "Адресат-судья не является автором",
            "Доступ в обычный суд не равен допустимости жалобы в КС РФ",
            "официальная интернет-публикация может быть надлежащей",
            "Отсутствие результата поиска не доказывает неопубликование",
            "В предоставленной версии нет авторского или подписного блока",
            "Сопоставление заключений с актами не доказывает",
            "Трёхмесячное поручение законодателю не является сроком подачи жалобы",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, content)

    def test_synthetic_inputs_do_not_require_private_files(self) -> None:
        for name, identifiers in COHORTS.items():
            payload = json.loads((REPO / "skills" / name / "evals/evals.json").read_text())
            cases = {entry["id"]: entry for entry in payload["evals"]}
            self.assertEqual(len(cases), len(payload["evals"]))
            for identifier in identifiers:
                with self.subTest(name=name, identifier=identifier):
                    case = cases[identifier]
                    self.assertEqual(case["files"], [])
                    self.assertTrue(case["prompt"].startswith("Синтетический сценарий."))
                    self.assertTrue(case["expected_output"])
                    self.assertGreaterEqual(len(case["expectations"]), 3)
                    content = json.dumps(case, ensure_ascii=False)
                    for forbidden in (
                        "/Users/", "/private/tmp/", "Мошкин", "Должиков", "Невинский",
                        "Ушаков", "Серебряков", "223461", "94337", "128782",
                        "08.10.2015", "50/1988", "a.dolzhikov@",
                    ):
                        self.assertNotIn(forbidden, content)

    def test_cases_cover_supported_routes_and_specific_failure_modes(self) -> None:
        markers = {
            "ksrf-rights-argument-builder": {
                33: "Продолжает рабочую аргументацию",
                34: "абсолютный иммунитет",
                35: "нарушение исполнения",
                36: "Сохраняет самостоятельную проверку",
                37: "каждый тип сведений",
                38: "Продолжает рабочий проект",
            },
            "ksrf-doctrine-research": {
                11: "Сохраняет отдельные версии",
                12: "Поддерживает узкую линию",
                13: "личную связь",
                14: "электронную форму",
                15: "Не выводит неопубликование",
                16: "Продолжает проверку самостоятельной линии",
            },
            "ksrf-decision-execution": {
                12: "прямое указание на пересмотр",
                13: "Не переносит чужое индивидуальное предписание",
            },
        }
        for name, expected in markers.items():
            payload = json.loads((REPO / "skills" / name / "evals/evals.json").read_text())
            cases = {entry["id"]: entry for entry in payload["evals"]}
            for identifier, marker in expected.items():
                with self.subTest(name=name, identifier=identifier):
                    self.assertIn(marker, " ".join(cases[identifier]["expectations"]))

    def test_public_credits_preserve_roles_and_active_final_act_links(self) -> None:
        for filename in ("KSRF_ANALYZED_AUTHORS.md", "KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"):
            content = (REPO / "docs" / filename).read_text()
            for name in ("Мошкин", "Должиков", "Невинский"):
                self.assertIn(name, content)
            for decision in ("223461", "94337", "128782"):
                self.assertIn(f"](https://www.ksrf.ru/doc/KSRFDecision{decision}.pdf)", content)
            self.assertIn("](https://pureportal.spbu.ru/ru/persons/", content)
            self.assertIn("](https://test.law.asu.ru/kafedra-konstitutsionnogo-i-mezhdunarodnogo-prava/)", content)
            self.assertIn("авторск", content)
            self.assertIn("исходник", content.lower())
            self.assertNotIn("a.dolzhikov@", content)
        authors = (REPO / "docs/KSRF_ANALYZED_AUTHORS.md").read_text()
        for line in authors.splitlines():
            if line.startswith(("| 50 |", "| 51 |", "| 52 |")):
                self.assertEqual(line.count("|"), 5)
        public_text = (REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md").read_text()
        self.assertIn("авторский блок отсутствует", public_text)
        self.assertIn("не копия жалобы и не личный сайт", public_text)

    def test_cleanroom_installs_methods_without_originals_or_evals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            for owner, filename in METHODS.items():
                source = REPO / "skills" / owner / "references" / filename
                self.assertEqual(
                    source.read_bytes(),
                    (target / owner / "references" / filename).read_bytes(),
                )
            for owner in COHORTS:
                self.assertFalse((target / owner / "evals").exists())
            for suffix in ("*.doc", "*.docx", "*.pdf", "*.png"):
                self.assertFalse(list(target.rglob(suffix)))
