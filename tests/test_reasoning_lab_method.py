"""Packaging invariants; semantic behavior is documented separately."""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from install_skillset import copy_skillset


class ReasoningLabMethodTests(unittest.TestCase):
    def test_new_reference_is_reachable_and_installed_without_research_corpus(self):
        source = REPO / "skills" / "ksrf-argument-patterns"
        relative = Path("references/reasoning-lab-workflow.md")
        self.assertIn(str(relative), (source / "SKILL.md").read_text())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            copy_skillset(REPO / "skills", target)
            installed = target / "ksrf-argument-patterns"
            self.assertEqual((source / relative).read_bytes(), (installed / relative).read_bytes())
            self.assertTrue((installed / "references/universal-methods.json").is_file())
            self.assertFalse((target / "artifacts").exists())
            self.assertFalse((target / "experiments").exists())

    def test_causal_and_stage_guidance_is_in_the_portable_reference(self):
        # Packaging assertions only: these do not measure legal reasoning quality.
        reference = REPO / "skills/ksrf-argument-patterns/references/reasoning-lab-workflow.md"
        body = reference.read_text()
        for section in ("Последний барьер и определяющая его квалификация",
                        "Сравнение режимов целиком", "Стадия наблюдения и проверка пары",
                        "Как именно суд установил посылку", "Оставшееся основание и объём меры"):
            self.assertIn("## " + section, body)
        self.assertIn("Вымышленный пример", body)
        self.assertIn("evaluator-derived", body)


if __name__ == "__main__":
    unittest.main()
