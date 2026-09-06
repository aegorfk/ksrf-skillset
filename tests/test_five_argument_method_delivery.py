"""Delivery checks only: these tests do not evaluate legal argument quality."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "skills/ksrf-rights-argument-builder/references/five-argument-transformations.md"


class FiveArgumentMethodDeliveryTests(unittest.TestCase):
    def test_five_sections_are_ordered_and_unique(self):
        text = REFERENCE.read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"^## (H\d+)\.", text, re.MULTILINE),
                         ["H1", "H2", "H3", "H4", "H5"])

    def test_each_section_has_trigger_output_and_review(self):
        sections = re.split(r"^## H\d+\.", REFERENCE.read_text(encoding="utf-8"),
                            flags=re.MULTILINE)[1:]
        for index, section in enumerate(sections, start=1):
            with self.subTest(hypothesis=index):
                for marker in ("**Триггер:**", "**Выход:**", "**QA:**"):
                    self.assertIn(marker, section)

    def test_reference_links_resolve_inside_runtime_skills(self):
        links = re.findall(r"\]\(([^)]+)\)", REFERENCE.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(links), 5)
        for link in links:
            target = (REFERENCE.parent / link.split("#", 1)[0]).resolve()
            with self.subTest(link=link):
                self.assertTrue(target.is_relative_to(ROOT / "skills"))
                self.assertTrue(target.is_file())
                self.assertNotIn("evals", target.parts)

    def test_builder_and_qa_route_to_same_reference(self):
        entries = {
            "ksrf-rights-argument-builder": "references/five-argument-transformations.md",
            "ksrf-complaint-qa": "../ksrf-rights-argument-builder/references/five-argument-transformations.md",
        }
        for skill, link in entries.items():
            entry = ROOT / "skills" / skill / "SKILL.md"
            with self.subTest(skill=skill):
                self.assertIn(f"]({link})", entry.read_text(encoding="utf-8"))
                self.assertEqual((entry.parent / link).resolve(), REFERENCE)

    def test_candidate_status_and_no_quality_claim_are_disclosed(self):
        text = REFERENCE.read_text(encoding="utf-8")
        self.assertIn("кандидатные приёмы", text)
        self.assertIn("ещё не измерен", text)
        self.assertIn("независимое человеческое юридическое сравнение", text)

    def test_public_readme_routes_to_reference(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("](" + str(REFERENCE.relative_to(ROOT)) + ")", readme)


if __name__ == "__main__":
    unittest.main()
