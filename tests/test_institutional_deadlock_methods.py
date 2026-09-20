from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import copy_skillset


REPO = Path(__file__).resolve().parents[1]
CARD = Path("ksrf-rights-argument-builder/references/institutional-deadlock-and-safeguards.md")
ROUTES = ("ksrf-rights-argument-builder", "ksrf-complaint-qa", "ksrf-decision-execution")
CASE_IDS = {
    "ksrf-rights-argument-builder": (80, 81),
    "ksrf-complaint-qa": (45,),
    "ksrf-decision-execution": (19,),
}


class InstitutionalDeadlockMethodsTests(unittest.TestCase):
    def test_routes_resolve_and_first_pass_is_unanchored(self) -> None:
        source = (REPO / "skills" / CARD).read_text()
        first, second = source.split("## Второй проход:", 1)
        self.assertIn("## Первый проход:", first)
        self.assertNotRegex(first, r"Кобринск|Литейн|50-П|2021|KSRFDecision568237")
        self.assertIn("KSRFDecision568237.pdf", second)
        for skill in ROUTES:
            owner = REPO / "skills" / skill / "SKILL.md"
            links = re.findall(r"\]\(([^)]+)\)", owner.read_text())
            routed = [link for link in links if link.endswith(CARD.name)]
            with self.subTest(skill=skill):
                self.assertEqual(len(routed), 1)
                self.assertEqual((owner.parent / routed[0]).resolve(), (REPO / "skills" / CARD).resolve())

    def test_scenarios_are_self_contained_and_ids_unique(self) -> None:
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
                    self.assertGreaterEqual(len(case["expectations"]), 3)
                    self.assertNotRegex(
                        json.dumps(case, ensure_ascii=False),
                        r"https?://|/Users/|ТЗ/|Кобринск|Литейн|50-П|Карпенков",
                    )

    def test_public_credit_and_no_private_email(self) -> None:
        for filename in ("KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md", "KSRF_ANALYZED_AUTHORS.md"):
            content = (REPO / "docs" / filename).read_text()
            with self.subTest(filename=filename):
                self.assertIn("Александр Аркадьевич Кобринский", content)
                self.assertIn("https://spb.yabloko.ru/people/kobrinsky-aleksandr-arkadievich/", content)
                self.assertIn("https://www.yabloko.ru/regnews/Spb/2021/08/02-0", content)
                self.assertIn("https://www.ksrf.ru/doc/KSRFDecision568237.pdf", content)
                self.assertNotIn("mail.google.com", content)
                self.assertNotIn("Жалоба!.doc", content)
                numbers = [int(value) for value in re.findall(r"^\| (\d+) \|", content, re.MULTILINE)]
                self.assertEqual(numbers, list(range(1, len(numbers) + 1)))

    def test_clean_install_retains_method_without_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            self.assertEqual((target / CARD).read_bytes(), (REPO / "skills" / CARD).read_bytes())
            for suffix in ("*.doc", "*.docx", "*.pdf", "*.eml"):
                self.assertFalse(list(target.rglob(suffix)))


if __name__ == "__main__":
    unittest.main()
