from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
METHODS = {
    "ksrf-rights-argument-builder": "electoral-status-and-time-sensitive-remedy.md",
    "ksrf-doctrine-research": "official-reports-and-normative-defects.md",
}
ROUTES = {
    "electoral-status-and-time-sensitive-remedy.md": (
        "ksrf-rights-argument-builder",
        "ksrf-complaint-cycle",
        "ksrf-complaint-qa",
        "ksrf-decision-execution",
    ),
    "official-reports-and-normative-defects.md": (
        "ksrf-doctrine-research",
        "ksrf-complaint-qa",
        "ksrf-decision-execution",
    ),
}
CASE_IDS = {
    "ksrf-rights-argument-builder": (76, 77),
    "ksrf-complaint-qa": (43,),
    "ksrf-decision-execution": (17,),
    "ksrf-doctrine-research": (49,),
}


class ElectoralStatusAndExecutionMethodsTests(unittest.TestCase):
    def test_method_routes_and_first_pass_boundaries(self) -> None:
        for owner, filename in METHODS.items():
            content = (REPO / "skills" / owner / "references" / filename).read_text()
            for route_owner in ROUTES[filename]:
                with self.subTest(filename=filename, route_owner=route_owner):
                    self.assertIn(
                        filename,
                        (REPO / "skills" / route_owner / "SKILL.md").read_text(),
                    )

            if filename == "electoral-status-and-time-sensitive-remedy.md":
                first, second = content.split("## Второй проход:", 1)
                self.assertIn("## Первый проход:", first)
                self.assertNotRegex(first, r"Силаев|27-П|НПД|самозанят")
                for boundary in (
                    "равными во всех правовых целях",
                    "каскад",
                    "само по себе не доказывает конституционный дефект",
                    "пересмотр конкретного дела и компенсаторный маршрут",
                ):
                    self.assertIn(boundary, content)
                self.assertIn("Постановление КС РФ от 30.05.2024 № 27-П", second)
            else:
                for boundary in (
                    "institutional_method_signal",
                    "Обычная ошибка по делу",
                    "Риск практикообразующего единичного применения",
                    "не доказывают фактическое исполнение",
                    "не устанавливает современный срок",
                ):
                    self.assertIn(boundary, content)

    def test_public_sources_do_not_become_binding_or_reconstruct_private_text(self) -> None:
        status = (
            REPO
            / "skills/ksrf-rights-argument-builder/references"
            / METHODS["ksrf-rights-argument-builder"]
        ).read_text()
        reports = (
            REPO / "skills/ksrf-doctrine-research/references" / METHODS["ksrf-doctrine-research"]
        ).read_text()

        for forbidden in ("ТЗ/", "/Users/", "Жалоба ФЗ-67", "Final.pdf", "OCR"):
            self.assertNotIn(forbidden, status)
            self.assertNotIn(forbidden, reports)
        self.assertIn("не самостоятельный источник обязательного правила", status)
        self.assertIn("не доказывает действующее право", reports)

    def test_synthetic_evals_are_portable(self) -> None:
        forbidden = r"https?://|/Users/|ТЗ/|Силаев|27-П|Зорькин|Report2009"
        for skill, identifiers in CASE_IDS.items():
            data = json.loads((REPO / "skills" / skill / "evals/evals.json").read_text())
            cases = {case["id"]: case for case in data["evals"]}
            for identifier in identifiers:
                case = cases[identifier]
                with self.subTest(skill=skill, identifier=identifier):
                    self.assertTrue(case["prompt"].startswith("Синтетический сценарий."))
                    self.assertEqual(case["files"], [])
                    self.assertGreaterEqual(len(case["expectations"]), 3)
                    self.assertTrue(case["expected_output"])
                    self.assertNotRegex(json.dumps(case, ensure_ascii=False), forbidden)

    def test_public_credit_and_numbered_registries(self) -> None:
        project = (REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md").read_text()
        authors = (REPO / "docs/KSRF_ANALYZED_AUTHORS.md").read_text()
        for required in (
            "Екатерина Силаева",
            "https://constitutional-center.ru/",
            "https://publication.pravo.gov.ru/document/0001202405310002",
            "https://www.ksrf.ru/news/38193/",
            "https://www.ksrf.ru/about/Maintenance/Documents/Report2009.pdf",
        ):
            with self.subTest(required=required):
                self.assertIn(required, project)
        for required in ("Центр конституционного правосудия", "Валерий Дмитриевич Зорькин", "| 79 |"):
            self.assertIn(required, authors)

        for content in (project, authors):
            numbers = [int(value) for value in re.findall(r"^\| (\d+) \|", content, re.MULTILINE)]
            self.assertEqual(numbers, list(range(1, len(numbers) + 1)))

    def test_cleanroom_install_keeps_cards_without_originals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            for owner, filename in METHODS.items():
                relative = Path(owner) / "references" / filename
                self.assertEqual(
                    (target / relative).read_bytes(),
                    (REPO / "skills" / relative).read_bytes(),
                )
            for suffix in ("*.pdf", "*.docx", "*.png", "*ocr*"):
                self.assertFalse(list(target.rglob(suffix)))


if __name__ == "__main__":
    unittest.main()
