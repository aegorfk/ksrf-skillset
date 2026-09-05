from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills/ksrf-rights-argument-builder"
FILENAME = "environmental-compensation-and-restoration.md"
METHOD = SKILL / "references" / FILENAME
COHORTS = {
    "ksrf-rights-argument-builder": range(24, 33),
    "ksrf-decision-execution": range(9, 12),
}
URLS = (
    "https://www.pgplaw.ru/our-experience/13862/",
    "https://zakon.ru/Tools/DownloadFileRecord/1878",
    "https://zakon.ru/blog/2015/06/08/ekologicheskaya_spravedlivost_non_bis_in_idem",
    "https://zakon.ru/fatherdure",
    "https://www.pgplaw.ru/news/press-releases/the-russian-constitutional-court-confirmed-the-correctness-of-the-position-of-lawyers-llc-zapolarnef/",
    "https://www.ksrf.ru/doc/KSRFDecision197747.pdf",
    "https://t.me/pgEcology",
)


class EnvironmentalCompensationMethodsTests(unittest.TestCase):
    def test_two_pass_method_is_reachable_without_private_inputs(self) -> None:
        content = METHOD.read_text()
        for name in (
            "ksrf-rights-argument-builder",
            "ksrf-complaint-cycle",
            "ksrf-complaint-qa",
            "ksrf-decision-execution",
        ):
            owner = REPO / "skills" / name / "SKILL.md"
            self.assertIn(FILENAME, owner.read_text())
        for heading in ("## Первый проход", "## Второй проход"):
            self.assertIn(heading, content)
        for link in re.findall(r"\]\(([^)]+)\)", content):
            if not link.startswith(("https://", "http://", "#")):
                resolved = (METHOD.parent / link.split("#")[0]).resolve()
                self.assertTrue(resolved.is_relative_to(REPO / "skills"))
                self.assertTrue(resolved.is_file())

    def test_method_preserves_normative_cause_and_public_interest(self) -> None:
        content = METHOD.read_text()
        for boundary in (
            "Расходы не равны результату восстановления",
            "отсутствие деревьев само по себе",
            "Связь норм не доказывает применение каждой",
            "обычную судебную ошибку",
            "Отсутствие найденных взысканий",
            "Более выгодная водная формула".lower(),
            "необходимость и разумность затрат",
            "не независимое исследование и рабочий проект",
            "не добавляй его без проверки применённой нормы",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_historical_success_does_not_expand_the_holding(self) -> None:
        content = METHOD.read_text()
        for boundary in (
            "бюджетные нормы не оспорены",
            "ч. 2 ст. 100 ЛК РФ признана не противоречащей Конституции",
            "Не вся гражданская или экологическая ответственность объявлена штрафной",
            "законодателю не предписана единственная модель",
            "не автоматически вычитать любые счета",
            "non bis in idem и комментарии участников не заменяют точный вывод Суда",
            "п. 2 резолютивной части, с. 29",
            "П. 5 резолютивной части, с. 30",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_reopening_requires_result_and_current_procedure(self) -> None:
        content = METHOD.read_text()
        for boundary in (
            "исключение переноса в соседние среды",
            "возможность целевого использования либо надлежащей консервации",
            "Историческое временное правило не объявляй действующим сегодня",
            "пересмотр дела заявителя обусловлен",
            "не подтверждает последующее выполнение этих условий",
            "не является слепой проверкой или доказательством судебной эффективности",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_synthetic_scenarios_are_self_contained(self) -> None:
        for name, cohort in COHORTS.items():
            payload = json.loads((REPO / "skills" / name / "evals/evals.json").read_text())
            cases = {entry["id"]: entry for entry in payload["evals"]}
            self.assertEqual(len(cases), len(payload["evals"]))
            for number in cohort:
                with self.subTest(skill=name, number=number):
                    entry = cases[number]
                    self.assertEqual(entry["files"], [])
                    self.assertTrue(entry["prompt"].startswith("Синтетический"))
                    self.assertTrue(entry["expected_output"])
                    self.assertGreaterEqual(len(entry["expectations"]), 3)
                    serialized = json.dumps(entry, ensure_ascii=False)
                    for prohibited in (
                        "/Users/", "/private/tmp/", "Заполярнефть", "Пепеляев",
                        "Бевзенко", "Квитко", "197747", "DownloadFileRecord",
                        "А81-", "2014.pdf",
                    ):
                        self.assertNotIn(prohibited, serialized)

    def test_scenarios_cover_both_supported_and_unsupported_branches(self) -> None:
        expectations = {
            "ksrf-rights-argument-builder": {
                24: "Связывает неопределённость",
                25: "Отличает оценку счетов",
                26: "Не делает автоматический зачёт",
                27: "остаточный экологический вред",
                28: "Пробел поиска",
                29: "возможность доказать необоснованное различие",
                30: "Не считает отсутствующие заключения прочитанными",
                31: "Продолжает рабочий проект",
                32: "Не удаляет требование молча",
            },
            "ksrf-decision-execution": {
                9: "Различает признанное неконституционным",
                10: "Не утверждает, что условие выполнено",
                11: "Не отказывает в подготовке только потому",
            },
        }
        for name, markers in expectations.items():
            payload = json.loads((REPO / "skills" / name / "evals/evals.json").read_text())
            cases = {entry["id"]: entry for entry in payload["evals"]}
            for number, marker in markers.items():
                with self.subTest(skill=name, number=number):
                    self.assertIn(marker, " ".join(cases[number]["expectations"]))

    def test_public_credits_separate_source_and_professional_roles(self) -> None:
        for path in (
            METHOD,
            REPO / "docs/KSRF_ANALYZED_AUTHORS.md",
            REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md",
        ):
            content = path.read_text()
            with self.subTest(path=path):
                for url in URLS:
                    self.assertIn(f"]({url})", content)
                for name in ("Пепеляев", "Бевзенко", "Попов", "Квитко", "Муранов и Черняков"):
                    self.assertIn(name, content)
                self.assertNotIn("публичная ссылка на сам текст пока не установлена", content)
        content = METHOD.read_text()
        self.assertIn("не удостоверяет точную отправленную редакцию", content)
        self.assertIn("печатный подписной блок", content)
        self.assertIn("в этом разборе отдельно не исследованы", content)
        for line in (REPO / "docs/KSRF_ANALYZED_AUTHORS.md").read_text().splitlines():
            if line.startswith(("| 48 |", "| 49 |")):
                self.assertEqual(line.count("|"), 5)

    def test_cleanroom_method_has_no_originals_or_maintainer_evals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            installed = target / "ksrf-rights-argument-builder/references" / FILENAME
            self.assertEqual(installed.read_bytes(), METHOD.read_bytes())
            for name in COHORTS:
                self.assertFalse((target / name / "evals").exists())
            for suffix in ("*.pdf", "*.docx", "*.doc", "*.png"):
                self.assertFalse(list(target.rglob(suffix)))


if __name__ == "__main__":
    unittest.main()
