from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
CYCLE = REPO / "skills/ksrf-complaint-cycle"
METHOD = CYCLE / "references/complaint-batch-review.md"
METHOD_ROUTES = {
    "ksrf-case-triage/references/electoral-and-supervisory-access.md": "ksrf-case-triage/SKILL.md",
    "ksrf-rights-argument-builder/references/social-entitlement-boundaries.md": "ksrf-rights-argument-builder/SKILL.md",
    "ksrf-practice-authority-builder/references/commercial-procedure-boundaries.md": "ksrf-practice-authority-builder/SKILL.md",
    "ksrf-argument-patterns/references/additional-complaint-boundaries.md": "ksrf-argument-patterns/SKILL.md",
    "ksrf-complaint-facts-demands/references/joined-applicants-individual-proof.md": "ksrf-complaint-facts-demands/SKILL.md",
    "ksrf-complaint-cycle/references/educational-complaint-source-boundaries.md": "ksrf-complaint-cycle/references/crystal-themis-mootcourt-patterns.md",
}
ADDED_EVAL_RANGES = {
    "ksrf-complaint-cycle": (18, 26),
    "ksrf-complaint-facts-demands": (10, 13),
    "ksrf-rights-argument-builder": (12, 17),
    "ksrf-practice-authority-builder": (4, 11),
    "ksrf-case-triage": (4, 11),
    "ksrf-argument-patterns": (4, 24),
}


class ComplaintBatchReviewTests(unittest.TestCase):
    def test_batch_method_preserves_coverage_and_source_boundaries(self) -> None:
        content = METHOD.read_text()
        for required in (
            "другое имя не делает его новым источником",
            "Простое упоминание фамилии в библиографии не завершает работу",
            "Прочитай весь доступный текст",
            "OCR не восстанавливает отсутствующее приложение",
            "В объединённом деле веди самостоятельную строку",
            "Известный поздний результат не выдавай",
            "Принятие к рассмотрению не равно удовлетворению",
            "Учебный заявитель, оценка жюри и конкурсная победа",
            "не старые сроки, пошлину, адрес",
            "не называй процитированное в такой жалобе решение КС РФ итогом",
            "не позволяющая восстановить жалобу",
            "Не перезаписывай и не удаляй оригинал",
            "не является доказательством судебной эффективности",
        ):
            with self.subTest(required=required):
                self.assertIn(required, content)

    def test_batch_route_is_reachable_from_cycle_and_attribution(self) -> None:
        owner = (CYCLE / "SKILL.md").read_text()
        self.assertLess(owner.index("### 5."), owner.index(METHOD.name))
        self.assertLess(owner.index(METHOD.name), owner.index("### 6."))
        source = (CYCLE / "references/source-authority-and-route.md").read_text()
        self.assertIn(METHOD.name, source)
        for target in re.findall(r"\]\(([^)]+)\)", METHOD.read_text()):
            if not target.startswith(("https://", "http://", "#")):
                self.assertTrue((METHOD.parent / target.split("#")[0]).resolve().is_file(), target)

    def test_batch_evals_are_self_contained_and_keep_distinct_traps(self) -> None:
        payload = json.loads((CYCLE / "evals/evals.json").read_text())
        cases = {entry["id"]: entry for entry in payload["evals"]}
        self.assertEqual(len(cases), len(payload["evals"]))
        traps = {18: "редакция", 19: "Фрагмент", 20: "скана", 21: "OCR", 22: "Секретариата"}
        for number, trap in traps.items():
            entry = cases[number]
            self.assertEqual(entry["files"], [])
            self.assertGreaterEqual(len(entry["expectations"]), 3)
            self.assertIn(trap.casefold(), " ".join(entry["expectations"]).casefold())
            self.assertTrue(entry["prompt"] and entry["expected_output"])

    def test_derived_methods_have_live_routes_and_no_local_source_dependencies(self) -> None:
        for relative, owner_relative in METHOD_ROUTES.items():
            path = REPO / "skills" / relative
            owner = REPO / "skills" / owner_relative
            with self.subTest(method=relative):
                self.assertTrue(path.is_file())
                self.assertIn(path.name, owner.read_text())
                content = path.read_text()
                self.assertNotIn("/Users/", content)
                self.assertNotIn("/private/tmp/", content)
                for target in re.findall(r"\]\(([^)]+)\)", content):
                    if not target.startswith(("https://", "http://", "#")):
                        linked = (path.parent / target.split("#")[0]).resolve()
                        self.assertTrue(linked.is_file(), target)
                        self.assertTrue(linked.is_relative_to(REPO / "skills"), target)

    def test_all_added_scenarios_have_explicit_source_free_expectations(self) -> None:
        for skill, (first, last) in ADDED_EVAL_RANGES.items():
            source = REPO / "skills" / skill / "evals/evals.json"
            payload = json.loads(source.read_text())
            cases = {entry["id"]: entry for entry in payload["evals"]}
            self.assertEqual(len(cases), len(payload["evals"]))
            for number in range(first, last + 1):
                with self.subTest(skill=skill, number=number):
                    entry = cases[number]
                    self.assertEqual(entry["files"], [])
                    self.assertTrue(entry["prompt"] and entry["expected_output"])
                    self.assertGreaterEqual(len(entry["expectations"]), 3)
                    serialized = json.dumps(entry, ensure_ascii=False)
                    self.assertNotIn("/Users/", serialized)
                    self.assertNotIn("/private/tmp/", serialized)

    def test_batch_method_installs_without_evals_or_historical_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            installed = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", installed)
            target = installed / METHOD.relative_to(REPO / "skills")
            self.assertEqual(target.read_bytes(), METHOD.read_bytes())
            for relative in METHOD_ROUTES:
                original = REPO / "skills" / relative
                self.assertEqual((installed / relative).read_bytes(), original.read_bytes())
            self.assertFalse(list(installed.rglob("evals")))
            self.assertFalse(list(installed.rglob("*.pdf")))
            self.assertFalse(list(installed.rglob("*.docx")))

    def test_source_identity_corrections_and_opinion_boundary(self) -> None:
        guide = (CYCLE / "references/ksrf-live-argument-patterns.md").read_text()
        self.assertNotIn("| Жалоба Королевых |", guide)
        self.assertNotIn("Компактная учебная архитектура", guide)
        self.assertIn("Реальная жалоба М.С. Филиппова", guide)
        source = REPO / "skills/ksrf-argument-patterns/evals/evals.json"
        cases = {entry["id"]: entry for entry in json.loads(source.read_text())["evals"]}
        self.assertIn("неуточнённым видом", cases[13]["expected_output"])
        self.assertNotIn("особое мнение", cases[13]["expected_output"])

    def test_public_credits_remain_inside_complete_markdown_tables(self) -> None:
        for name in ("KSRF_ANALYZED_AUTHORS.md", "KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"):
            content = (REPO / "docs" / name).read_text()
            blocks = re.findall(r"(?:^\|[^\n]*\n)+", content, re.MULTILINE)
            self.assertTrue(blocks, name)
            for block in blocks:
                rows = block.splitlines()
                self.assertGreaterEqual(len(rows), 3, name)
                self.assertRegex(rows[1], r"^[| :\-]+$", name)
                columns = rows[0].count("|")
                for row in rows:
                    self.assertEqual(row.count("|"), columns, name)


if __name__ == "__main__":
    unittest.main()
