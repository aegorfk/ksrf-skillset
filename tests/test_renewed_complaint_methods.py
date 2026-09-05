from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills/ksrf-complaint-qa"
FILENAME = "renewed-complaint-and-remedy-gap.md"
METHOD = SKILL / "references" / FILENAME
URLS = (
    "https://www.advgazeta.ru/upload/medialibrary/02a/zhaloba_sherbakov_14_04_2018.pdf",
    "https://advokat39.ru/",
    "https://doc.ksrf.ru/decision/KSRFDecision324961.pdf",
    "https://doc.ksrf.ru/decision/KSRFDecision338686.pdf",
)


class RenewedComplaintMethodsTests(unittest.TestCase):
    def test_method_has_reachable_two_pass_routes(self) -> None:
        content = METHOD.read_text()
        for owner in (SKILL / "SKILL.md", REPO / "skills/ksrf-complaint-cycle/SKILL.md"):
            self.assertIn(FILENAME, owner.read_text())
        for heading in ("## Первый проход", "## Второй проход"):
            self.assertIn(heading, content)
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if not target.startswith(("https://", "http://", "#")):
                resolved = (METHOD.parent / target.split("#")[0]).resolve()
                self.assertTrue(resolved.is_relative_to(REPO / "skills"))
                self.assertTrue(resolved.is_file())

    def test_prior_refusal_is_not_the_later_complaint_outcome(self) -> None:
        content = METHOD.read_text()
        for boundary in (
            "Прежний акт — [№ 265-О от 27.02.2018]",
            "Итог повторного обращения — [№ 1367-О от 29.05.2018]",
            "14.04.2018",
            "05.03.2018",
            "Исходная жалоба, разрешённая в феврале, не подменяется апрельской",
            "Эти самостоятельные основания нельзя приписывать прежнему № 265-О",
            "не подтверждает точную отправленную редакцию",
            "Оба акта — отказы в принятии",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_method_preserves_delta_application_and_factual_limits(self) -> None:
        content = METHOD.read_text()
        for boundary in (
            "сама по себе не устанавливает отличия",
            "Реальное изменение нельзя отклонять лишь из-за прежнего отказа",
            "не означает отсутствие действующего прежнего решения",
            "кто вправе её запустить",
            "не становится применённой только из-за её включения",
            "не удаляй норму молча",
            "ст. 401.12, 401.13 и 413–417",
            "не представлены материалы о содержании без судебного решения",
            "не является слепой проверкой или доказательством судебной эффективности",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, content)

    def test_synthetic_cases_are_self_contained_and_source_free(self) -> None:
        payload = json.loads((SKILL / "evals/evals.json").read_text())
        cases = {entry["id"]: entry for entry in payload["evals"]}
        self.assertEqual(len(cases), len(payload["evals"]))
        for number in range(31, 41):
            with self.subTest(number=number):
                entry = cases[number]
                self.assertEqual(entry["files"], [])
                self.assertTrue(entry["prompt"] and entry["expected_output"])
                self.assertGreaterEqual(len(entry["expectations"]), 3)
                serialized = json.dumps(entry, ensure_ascii=False)
                for prohibited in ("/Users/", "/private/tmp/", "Щербаков", "Филатьев", "324961", "338686", "ФКУ ИК-"):
                    self.assertNotIn(prohibited, serialized)

    def test_cases_distinguish_real_delta_from_unsupported_claims(self) -> None:
        payload = json.loads((SKILL / "evals/evals.json").read_text())
        cases = {entry["id"]: entry for entry in payload["evals"]}
        traps = {
            31: "Прежний отказ не назван результатом",
            32: "Новое слово",
            33: "инициатор",
            34: "Нормы не удалены молча",
            35: "действующего прежнего решения",
            36: "непосредственное прекращение",
            37: "не стал автоматическим запретом",
            38: "Личное предпочтение",
            39: "Отсутствие фразы",
            40: "криптографической проверкой",
        }
        for number, trap in traps.items():
            with self.subTest(number=number):
                self.assertIn(trap, " ".join(cases[number]["expectations"]))

    def test_public_credits_have_all_source_roles(self) -> None:
        for path in (METHOD, REPO / "docs/KSRF_ANALYZED_AUTHORS.md", REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"):
            content = path.read_text()
            with self.subTest(path=path):
                for url in URLS:
                    self.assertIn(f"]({url})", content)
                self.assertIn("Владислав", content)
                self.assertIn("Филатьев", content)
                self.assertRegex(content.lower(), r"прежний (?:отказ|акт)")
                self.assertIn("итог повторного обращения", content.lower())
                self.assertNotIn("ФКУ ИК-", content)

    def test_runtime_install_excludes_originals_and_evals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            installed = target / "ksrf-complaint-qa/references" / FILENAME
            self.assertEqual(installed.read_bytes(), METHOD.read_bytes())
            self.assertFalse((target / "ksrf-complaint-qa/evals").exists())
            self.assertFalse(list(target.rglob("*.pdf")))
            self.assertFalse(list(target.rglob("*.doc")))


if __name__ == "__main__":
    unittest.main()
