from __future__ import annotations

import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import skillset_file_contract as contract  # noqa: E402
from generate_skills_manifest import build_manifest  # noqa: E402


ROOT_ONLY = (
    "build_constitutionalist_authority_corpus.py",
    "enrich_ksrf_argument_patterns.py",
    "extract_ksrf_argument_patterns.py",
)
ACTIVE_MIRRORED: tuple[str, ...] = ()
RETIRED_MIRRORED: tuple[str, ...] = ()
AUTHORITY_BUILDER_SHA256 = (
    "aef53ee039439a74c937a32189bdfaa3d31edc5fb98f822f2bc41994614f999f"
)


class ToolOwnershipContractTests(unittest.TestCase):
    def _minimal_release_source(self, root: Path) -> None:
        for name in contract.SKILL_NAMES:
            skill = root / "skills" / name
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
        for relative_name in contract.RELEASE_FILE_PATHS:
            release_file = root / relative_name
            release_file.parent.mkdir(parents=True, exist_ok=True)
            release_file.write_text("# safe release fixture\n", encoding="utf-8")

    def test_tool_ownership_classes_are_exact_disjoint_and_release_covered(self) -> None:
        mirrored = tuple(contract.MIRRORED_TOOL_NAMES)
        root_only = tuple(getattr(contract, "ROOT_ONLY_TOOL_NAMES", ()))
        retired = tuple(contract.RETIRED_MIRRORED_TOOL_NAMES)

        self.assertEqual(mirrored, ACTIVE_MIRRORED)
        self.assertEqual(root_only, ROOT_ONLY)
        self.assertEqual(retired, RETIRED_MIRRORED)
        self.assertFalse(set(mirrored) & set(root_only))
        self.assertFalse(set(mirrored) & set(retired))
        self.assertFalse(set(root_only) & set(retired))
        for name in ROOT_ONLY:
            self.assertIn(f"tools/{name}", contract.RELEASE_FILE_PATHS)

    def test_root_only_tools_have_one_source_owner_and_no_skill_duplicate(self) -> None:
        for name in ROOT_ONLY:
            with self.subTest(name=name):
                root_tool = TOOLS / name
                nested = REPO / "skills" / "ksrf-argument-patterns" / "scripts" / name
                self.assertTrue(root_tool.is_file())
                self.assertFalse(root_tool.is_symlink())
                self.assertTrue(root_tool.stat().st_mode & stat.S_IXUSR)
                self.assertFalse(nested.exists())

    def test_manifest_hashes_root_only_tools_outside_runtime_skill_rows(self) -> None:
        manifest = json.loads(
            (REPO / "skills-manifest.json").read_text(encoding="utf-8")
        )
        release_rows = {row["path"]: row for row in manifest["release_files"]}

        for name in ROOT_ONLY:
            with self.subTest(name=name):
                relative = f"tools/{name}"
                root_tool = REPO / relative
                self.assertEqual(
                    release_rows[relative]["sha256"],
                    contract.file_digest(root_tool),
                )
                self.assertIn(
                    f"ksrf-argument-patterns/scripts/{name}",
                    manifest["exclusions"],
                )

    def test_manifest_generation_rejects_root_only_duplicate_or_unsafe_owner(self) -> None:
        for name in ROOT_ONLY:
            with self.subTest(name=name, case="duplicate"):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    self._minimal_release_source(root)
                    duplicate = (
                        root / "skills" / "ksrf-argument-patterns" / "scripts" / name
                    )
                    duplicate.parent.mkdir(parents=True)
                    duplicate.write_text("# benign duplicate\n", encoding="utf-8")
                    with self.assertRaisesRegex(
                        SystemExit, "root-only tool duplicate is forbidden"
                    ):
                        build_manifest(root, "a" * 40)

            with self.subTest(name=name, case="unsafe owner"):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    self._minimal_release_source(root)
                    (root / "tools" / name).write_text(
                        'SOURCE = "/Users/alice/Documents/private/input.pdf"\n',
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(
                        SystemExit, "unsafe root-only release tool content"
                    ):
                        build_manifest(root, "a" * 40)

    def test_mirror_clis_are_empty_after_runtime_builder_retirement(self) -> None:
        for option, expected in (
            ("--active-mirrored-tools", ACTIVE_MIRRORED),
            ("--retired-mirrored-tools", RETIRED_MIRRORED),
        ):
            with self.subTest(option=option):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(TOOLS / "skillset_file_contract.py"),
                        option,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                self.assertEqual(result.stdout.splitlines(), list(expected))

    def test_root_authority_builder_bytes_remain_frozen(self) -> None:
        self.assertEqual(
            contract.file_digest(
                TOOLS / "build_constitutionalist_authority_corpus.py"
            ),
            AUTHORITY_BUILDER_SHA256,
        )

    def test_root_enrich_default_targets_argument_pattern_skill(self) -> None:
        path = TOOLS / "enrich_ksrf_argument_patterns.py"
        spec = importlib.util.spec_from_file_location("root_pattern_enricher", path)
        if spec is None or spec.loader is None:
            self.fail(f"Не удалось загрузить {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        self.assertEqual(
            module.DEFAULT_SKILL,
            REPO / "skills" / "ksrf-argument-patterns",
        )

    def test_root_only_tool_help_does_not_require_optional_pdf_dependencies(self) -> None:
        for name in ROOT_ONLY:
            with self.subTest(name=name):
                result = subprocess.run(
                    [sys.executable, str(TOOLS / name), "--help"],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())

    def test_user_guides_do_not_route_to_retired_nested_generators(self) -> None:
        guides = list((REPO / "skills").glob("ksrf-*/SKILL.md"))
        guides.extend((REPO / "skills").glob("ksrf-*/references/*.md"))
        for guide in guides:
            text = guide.read_text(encoding="utf-8")
            for name in ROOT_ONLY:
                with self.subTest(guide=guide, name=name):
                    self.assertNotIn(f"scripts/{name}", text)

        active_design = (
            REPO
            / "openspec"
            / "changes"
            / "extract-ksrf-argument-pattern-skills"
            / "design.md"
        ).read_text(encoding="utf-8")
        active_spec = (
            REPO
            / "openspec"
            / "changes"
            / "extract-ksrf-argument-pattern-skills"
            / "specs"
            / "ksrf-argument-patterns"
            / "spec.md"
        ).read_text(encoding="utf-8")
        self.assertIn("tools/extract_ksrf_argument_patterns.py", active_design)
        self.assertIn("tools/extract_ksrf_argument_patterns.py", active_spec)


if __name__ == "__main__":
    unittest.main()
