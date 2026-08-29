from pathlib import Path
import sys
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from install_skillset import InstallationError, _validate_target, copy_skillset  # noqa: E402
from skillset_file_contract import SKILL_NAMES, payload_files, tree_digest  # noqa: E402


class ExactSkillsetInstallTests(unittest.TestCase):
    def _source(self, root: Path) -> Path:
        source = root / "source"
        source.mkdir()
        for name in SKILL_NAMES:
            skill = source / name
            (skill / "nested").mkdir(parents=True)
            (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
            (skill / "nested" / "allowed.txt").write_text("allowed\n", encoding="utf-8")
            (skill / ".env.example").write_text("PUBLIC_EXAMPLE=1\n", encoding="utf-8")
            (skill / ".env").write_text("SECRET=1\n", encoding="utf-8")
            (skill / "secrets.json").write_text("{}\n", encoding="utf-8")
            (skill / "nested" / "ignored.pyc").write_bytes(b"ignored")
            cache = skill / "__pycache__"
            cache.mkdir()
            (cache / "ignored.txt").write_text("ignored\n", encoding="utf-8")
        return source

    def test_copy_is_exact_manifest_payload_and_removes_stale_destination_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source(root)
            target = root / "target"
            stale_skill = target / SKILL_NAMES[0]
            stale_skill.mkdir(parents=True)
            (stale_skill / "stale.txt").write_text("stale\n", encoding="utf-8")

            copy_skillset(source, target)

            for name in SKILL_NAMES:
                source_skill = source / name
                installed_skill = target / name
                source_files = payload_files(source_skill)
                installed_files = payload_files(installed_skill)
                self.assertEqual(
                    [path.relative_to(source_skill) for path in source_files],
                    [path.relative_to(installed_skill) for path in installed_files],
                )
                self.assertEqual(
                    tree_digest(source_skill, source_files),
                    tree_digest(installed_skill, installed_files),
                )
                self.assertTrue((installed_skill / ".env.example").is_file())
                self.assertFalse((installed_skill / ".env").exists())
                self.assertFalse((installed_skill / "secrets.json").exists())
                self.assertFalse((installed_skill / "nested" / "ignored.pyc").exists())
                self.assertFalse((installed_skill / "__pycache__").exists())
            self.assertFalse((target / SKILL_NAMES[0] / "stale.txt").exists())

    def test_refuses_broad_target(self) -> None:
        with self.assertRaisesRegex(InstallationError, "broad install target"):
            _validate_target(Path("/"))
        with self.assertRaisesRegex(InstallationError, "broad install target"):
            _validate_target(Path.home())

    def test_refuses_symlinked_target_and_destination_before_copy(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source(root)
            real_target = root / "real-target"
            real_target.mkdir()
            marker = real_target / "marker.txt"
            marker.write_text("unchanged\n", encoding="utf-8")
            target_link = root / "target-link"
            target_link.symlink_to(real_target, target_is_directory=True)
            with self.assertRaisesRegex(InstallationError, "symlinked install target"):
                copy_skillset(source, target_link)
            self.assertEqual(marker.read_text(encoding="utf-8"), "unchanged\n")

            target = root / "target"
            target.mkdir()
            destination_link = target / SKILL_NAMES[0]
            destination_link.symlink_to(real_target, target_is_directory=True)
            with self.assertRaisesRegex(InstallationError, "symlinked skill destination"):
                copy_skillset(source, target)
            self.assertTrue(destination_link.is_symlink())

    def test_refuses_non_directory_target_before_copy(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source(root)
            target = root / "target-file"
            target.write_text("unchanged\n", encoding="utf-8")
            with self.assertRaisesRegex(InstallationError, "not a directory"):
                copy_skillset(source, target)
            self.assertEqual(target.read_text(encoding="utf-8"), "unchanged\n")

    def test_refuses_nested_source_symlink_before_changing_target(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source(root)
            external_secret = root / "external-secret.txt"
            external_secret.write_text("must-not-be-copied\n", encoding="utf-8")
            (source / SKILL_NAMES[0] / "nested" / "leak.txt").symlink_to(external_secret)

            target = root / "target"
            existing_skill = target / SKILL_NAMES[0]
            existing_skill.mkdir(parents=True)
            marker = existing_skill / "existing.txt"
            marker.write_text("unchanged\n", encoding="utf-8")

            with self.assertRaisesRegex(InstallationError, "symlink inside payload tree"):
                copy_skillset(source, target)
            self.assertEqual(marker.read_text(encoding="utf-8"), "unchanged\n")
            self.assertFalse((existing_skill / "nested" / "leak.txt").exists())


if __name__ == "__main__":
    unittest.main()
