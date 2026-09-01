from pathlib import Path
import sys
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from install_skillset import InstallationError, _validate_target, copy_skillset  # noqa: E402
from skillset_file_contract import SKILL_NAMES, payload_files, tree_digest  # noqa: E402


EXACT_MAINTAINER_FILES = (
    ("ksrf-argument-patterns", Path("references/hearing_argument_techniques.json")),
    ("ksrf-argument-patterns", Path("references/language_formulas.json")),
    ("ksrf-argument-patterns", Path("references/evidence_maps.json")),
    (
        "ksrf-argument-patterns",
        Path("references/argument_techniques_from_decisions.json"),
    ),
    ("ksrf-complaint-cycle", Path("scripts/add_reference_tocs.py")),
)


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

    def test_copy_excludes_development_tests_and_evals(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source(root)
            skill = source / SKILL_NAMES[0]
            fixtures = skill / "tests" / "fixtures"
            fixtures.mkdir(parents=True)
            (skill / "tests" / "test_runtime.py").write_text(
                "def test_source_only():\n    assert True\n", encoding="utf-8"
            )
            (fixtures / "example.json").write_text("{}\n", encoding="utf-8")
            evals = skill / "evals"
            evals.mkdir()
            (evals / "evals.json").write_text("{}\n", encoding="utf-8")
            references = skill / "references"
            references.mkdir()
            (references / "evals-guide.md").write_text(
                "runtime guide\n", encoding="utf-8"
            )
            target = root / "target"

            copy_skillset(source, target)

            self.assertTrue((skill / "tests" / "test_runtime.py").is_file())
            self.assertTrue((skill / "evals" / "evals.json").is_file())
            self.assertFalse((target / SKILL_NAMES[0] / "tests").exists())
            self.assertFalse((target / SKILL_NAMES[0] / "evals").exists())
            self.assertTrue(
                (target / SKILL_NAMES[0] / "references" / "evals-guide.md").is_file()
            )

    def test_copy_excludes_only_exact_maintainer_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source(root)
            for package, relative in EXACT_MAINTAINER_FILES:
                path = source / package / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("maintainer only\n", encoding="utf-8")

            controls = (
                source
                / "ksrf-case-triage"
                / "references"
                / "evidence_maps.json",
                source
                / "ksrf-argument-patterns"
                / "references"
                / "evidence_maps-guide.json",
                source
                / "ksrf-argument-patterns"
                / "references"
                / "constitutional_graph.json",
                source
                / "ksrf-complaint-cycle"
                / "scripts"
                / "runtime-helper.py",
            )
            for path in controls:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("runtime\n", encoding="utf-8")
            target = root / "target"
            for package, relative in EXACT_MAINTAINER_FILES:
                stale = target / package / relative
                stale.parent.mkdir(parents=True, exist_ok=True)
                stale.write_text("stale installed bytes\n", encoding="utf-8")

            copy_skillset(source, target)

            for package, relative in EXACT_MAINTAINER_FILES:
                self.assertTrue((source / package / relative).is_file())
                self.assertFalse((target / package / relative).exists())
            for path in controls:
                relative = path.relative_to(source)
                self.assertTrue((target / relative).is_file())

    def test_source_sync_preserves_exact_maintainer_files_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source(root)
            target = root / "target"
            for package, relative in EXACT_MAINTAINER_FILES:
                incoming = source / package / relative
                incoming.parent.mkdir(parents=True, exist_ok=True)
                incoming.write_bytes(b"unexpected incoming runtime bytes\n")
                preserved = target / package / relative
                preserved.parent.mkdir(parents=True, exist_ok=True)
                preserved.write_bytes(b"tracked source bytes\n")

            copy_skillset(source, target, preserve_target_development=True)

            for package, relative in EXACT_MAINTAINER_FILES:
                self.assertEqual(
                    (target / package / relative).read_bytes(),
                    b"tracked source bytes\n",
                )

    def test_source_sync_preserves_target_tests_and_evals_while_replacing_runtime_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source(root)
            target = root / "target"
            target_skill = target / SKILL_NAMES[0]
            target_tests = target_skill / "tests" / "fixtures"
            target_tests.mkdir(parents=True)
            (target_skill / "tests" / "test_source_contract.py").write_text(
                "def test_source_contract():\n    assert True\n", encoding="utf-8"
            )
            (target_tests / "case.json").write_text("{}\n", encoding="utf-8")
            target_evals = target_skill / "evals"
            target_evals.mkdir()
            (target_evals / "evals.json").write_text(
                '{"source": "preserve"}\n', encoding="utf-8"
            )
            (target_evals / "trigger-evals.json").write_text(
                "[]\n", encoding="utf-8"
            )
            (target_skill / "stale-runtime.txt").write_text(
                "stale\n", encoding="utf-8"
            )

            copy_skillset(source, target, preserve_target_development=True)

            self.assertTrue(
                (target_skill / "tests" / "test_source_contract.py").is_file()
            )
            self.assertTrue((target_tests / "case.json").is_file())
            self.assertEqual(
                (target_evals / "evals.json").read_text(encoding="utf-8"),
                '{"source": "preserve"}\n',
            )
            self.assertEqual(
                (target_evals / "trigger-evals.json").read_text(encoding="utf-8"),
                "[]\n",
            )
            self.assertFalse((target_skill / "stale-runtime.txt").exists())
            self.assertTrue((target_skill / "nested" / "allowed.txt").is_file())

    def test_refuses_broad_target(self) -> None:
        with self.assertRaisesRegex(InstallationError, "broad install target"):
            _validate_target(Path("/"))
        with self.assertRaisesRegex(InstallationError, "broad install target"):
            _validate_target(Path.home())

    def test_refuses_source_target_overlap_before_changing_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._source(root)
            test_file = source / SKILL_NAMES[0] / "tests" / "test_source_only.py"
            test_file.parent.mkdir()
            test_file.write_text("source marker\n", encoding="utf-8")

            overlapping_targets = (
                source,
                source / "nested-install",
                source.parent,
            )
            for target in overlapping_targets:
                with self.subTest(target=target):
                    with self.assertRaisesRegex(
                        InstallationError, "source and target paths overlap"
                    ):
                        copy_skillset(source, target)
                    self.assertEqual(
                        test_file.read_text(encoding="utf-8"), "source marker\n"
                    )

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

    def test_sync_handles_an_empty_retired_tool_allowlist_on_macos_bash(self) -> None:
        sync_script = (TOOLS / "sync_global_skills.sh").read_text(encoding="utf-8")

        self.assertNotIn('retired_mirrored_tools=()', sync_script)
        self.assertNotIn('${retired_mirrored_tools[@]}', sync_script)
        self.assertIn('--retired-mirrored-tools', sync_script)
        self.assertIn('--preserve-target-development', sync_script)


if __name__ == "__main__":
    unittest.main()
