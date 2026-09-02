from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import skillset_file_contract as canonical  # noqa: E402


VALIDATOR_PATH = (
    REPO
    / "skills"
    / "ksrf-complaint-cycle"
    / "scripts"
    / "validate_ksrf_skillset.py"
)
SPEC = importlib.util.spec_from_file_location("portable_ksrf_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Не удалось загрузить {VALIDATOR_PATH}")
portable = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(portable)


class SourceOnlyContractParityTests(unittest.TestCase):
    def test_canonical_provenance_journal_remains_a_regular_source_file(self) -> None:
        journal = (
            REPO
            / "skills"
            / "ksrf-argument-patterns"
            / "references"
            / "complaint-methodology-sources.md"
        )
        self.assertTrue(journal.is_file())
        self.assertFalse(journal.is_symlink())

    def test_canonical_automation_backlog_remains_a_regular_source_file(self) -> None:
        backlog = (
            REPO
            / "skills"
            / "ksrf-argument-patterns"
            / "references"
            / "automation-backlog.md"
        )
        self.assertTrue(backlog.is_file())
        self.assertFalse(backlog.is_symlink())
        self.assertEqual(
            hashlib.sha256(backlog.read_bytes()).hexdigest(),
            "d25a9df36f6c1d7d995deae35f22a6b9875ac6597251342492ae69a111d75e94",
        )

    def test_canonical_and_portable_exact_source_only_paths_match(self) -> None:
        canonical_paths = set(
            getattr(canonical, "SOURCE_ONLY_SKILLSET_PATHS", frozenset())
        )
        portable_paths = set(
            getattr(portable, "SOURCE_ONLY_SKILLSET_PATHS", frozenset())
        )

        self.assertEqual(
            canonical_paths,
            {
                "ksrf-argument-patterns/references/argument_techniques_from_decisions.json",
                "ksrf-argument-patterns/references/automation-backlog.md",
                "ksrf-argument-patterns/references/complaint-methodology-sources.md",
                "ksrf-argument-patterns/references/evidence_maps.json",
                "ksrf-argument-patterns/references/hearing_argument_techniques.json",
                "ksrf-argument-patterns/references/language_formulas.json",
                "ksrf-argument-patterns/scripts/build_constitutionalist_authority_corpus.py",
                "ksrf-argument-patterns/scripts/enrich_ksrf_argument_patterns.py",
                "ksrf-argument-patterns/scripts/extract_ksrf_argument_patterns.py",
                "ksrf-complaint-cycle/scripts/add_reference_tocs.py",
            },
        )
        self.assertEqual(canonical_paths, portable_paths)
        self.assertEqual(
            set(canonical.ROOT_ONLY_TOOL_SKILL_PATHS),
            set(portable.ROOT_ONLY_TOOL_SKILL_PATHS),
        )

    def test_markdown_runtime_successors_remain_routed_from_skill(self) -> None:
        skill = REPO / "skills" / "ksrf-argument-patterns" / "SKILL.md"
        skill_text = skill.read_text(encoding="utf-8")
        reference_root = skill.parent / "references"
        for name in (
            "argument-techniques-from-decisions.md",
            "evidence-maps.md",
            "hearing-argument-techniques.md",
            "language-formulas.md",
        ):
            self.assertIn(f"references/{name}", skill_text)
            self.assertTrue((reference_root / name).is_file())

    def test_versioned_manifest_discloses_exact_source_only_paths(self) -> None:
        manifest = json.loads((REPO / "skills-manifest.json").read_text(encoding="utf-8"))

        self.assertTrue(
            set(canonical.SOURCE_ONLY_SKILLSET_PATHS).issubset(manifest["exclusions"])
        )

    def test_runtime_user_material_contains_no_source_only_markdown_backlink(self) -> None:
        excluded_basenames = {
            "automation-backlog.md",
            "complaint-methodology-sources.md",
        }
        text_suffixes = {".json", ".md", ".txt", ".yaml", ".yml"}

        for package in canonical.SKILL_NAMES:
            skill_root = REPO / "skills" / package
            for path in canonical.payload_files(skill_root):
                if path.name != "SKILL.md" and "references" not in path.parts:
                    continue
                if path.suffix.lower() not in text_suffixes:
                    continue
                text = path.read_text(encoding="utf-8")
                for excluded_basename in excluded_basenames:
                    with self.subTest(
                        path=path.relative_to(REPO).as_posix(),
                        excluded_basename=excluded_basename,
                    ):
                        self.assertNotIn(excluded_basename, text)

    def test_automation_backlog_routes_are_replaced_by_shipped_checks(self) -> None:
        live_patterns = (
            REPO
            / "skills"
            / "ksrf-complaint-cycle"
            / "references"
            / "ksrf-live-argument-patterns.md"
        ).read_text(encoding="utf-8")
        court_request = (
            REPO / "skills" / "ksrf-court-request-motion" / "SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertNotIn("automation-backlog.md", live_patterns)
        self.assertNotIn("automation-backlog.md", court_request)
        self.assertIn("argument-package-builder.md", live_patterns)
        self.assertIn("evidence-maps.md", live_patterns)
        self.assertIn("../ksrf-argument-patterns/references/pattern-matrix.md", court_request)
        self.assertIn("../ksrf-argument-patterns/references/evidence-maps.md", court_request)
        self.assertIn("references/workflow-reference.md", court_request)

        for relative in (
            "skills/ksrf-argument-patterns/references/argument-package-builder.md",
            "skills/ksrf-argument-patterns/references/evidence-maps.md",
            "skills/ksrf-argument-patterns/references/pattern-matrix.md",
            "skills/ksrf-court-request-motion/references/workflow-reference.md",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((REPO / relative).is_file())

    def test_operational_scripts_contain_no_source_only_markdown_backlink(self) -> None:
        excluded_basenames = {
            "automation-backlog.md",
            "complaint-methodology-sources.md",
        }
        paths = (
            REPO / "tools" / "build_constitutionalist_authority_corpus.py",
            REPO
            / "skills"
            / "ksrf-complaint-cycle"
            / "scripts"
            / "verify_offline_self_containment.py",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for excluded_basename in excluded_basenames:
                with self.subTest(
                    path=path.relative_to(REPO).as_posix(),
                    excluded_basename=excluded_basename,
                ):
                    self.assertNotIn(excluded_basename, text)

    def test_offline_verifier_accepts_source_only_provenance_journal(self) -> None:
        verifier = (
            REPO
            / "skills"
            / "ksrf-complaint-cycle"
            / "scripts"
            / "verify_offline_self_containment.py"
        )
        completed = subprocess.run(
            [sys.executable, str(verifier)],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_runtime_successors_close_provenance_methodology_gaps(self) -> None:
        strategic = (
            REPO
            / "skills"
            / "ksrf-complaint-cycle"
            / "references"
            / "strategic-complaint-design.md"
        ).read_text(encoding="utf-8")
        offline = (
            REPO
            / "skills"
            / "ksrf-complaint-cycle"
            / "references"
            / "offline-practice-core.md"
        ).read_text(encoding="utf-8")

        for axis in ("Незаконность", "Причинность", "Вина", "Способ восстановления"):
            with self.subTest(axis=axis):
                self.assertIn(f"| {axis} |", strategic)
        self.assertIn("### После принятия обращения: отдельный gate слушания", offline)
        self.assertIn("Не предполагай автоматическое устное слушание", offline)
        self.assertIn("`remedy-access counterfactual`", strategic)
        self.assertIn(
            "сохраняется, сужается или исчезает юридический доступ к специальной компенсации",
            strategic,
        )

    def test_runtime_backlog_contains_no_source_maintenance_routes(self) -> None:
        backlog = (
            REPO
            / "skills"
            / "ksrf-argument-patterns"
            / "references"
            / "automation-backlog.md"
        ).read_text(encoding="utf-8")
        for marker in (
            "methodology-source-crawler",
            "zakon-rubric-methodology-ingestor",
            "crawl_constitutional_methodology_sources.py",
            "ТЗ/Гайды/Новое/constitutional_methodology_sources",
            "source-only журнал происхождения",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, backlog)

    def test_corpus_metadata_routes_to_retained_runtime_successors(self) -> None:
        excluded_basename = "complaint-methodology-sources.md"
        expected_reference = (
            '"skill_reference": '
            '"strategic-complaint-design.md; science-support-pack.md"'
        )
        root_builder = REPO / "tools" / "build_constitutionalist_authority_corpus.py"
        nested_builder = (
            REPO
            / "skills"
            / "ksrf-argument-patterns"
            / "scripts"
            / "build_constitutionalist_authority_corpus.py"
        )
        generated = (
            REPO
            / "skills"
            / "ksrf-argument-patterns"
            / "references"
            / "constitutionalist-authority-corpus.json"
        )

        self.assertFalse(nested_builder.exists())

        for path in (root_builder, generated):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(REPO).as_posix()):
                self.assertNotIn(excluded_basename, text)
                self.assertIn(expected_reference, text)

        parsed = ast.parse(root_builder.read_text(encoding="utf-8"))
        curated = None
        for node in parsed.body:
            if not isinstance(node, ast.Assign):
                continue
            if any(isinstance(target, ast.Name) and target.id == "CURATED" for target in node.targets):
                curated = ast.literal_eval(node.value)
                break
        self.assertIsInstance(curated, list)
        generated_by_name = {
            item["canonical_name"]: item
            for item in json.loads(generated.read_text(encoding="utf-8"))["authorities"]
        }
        for item in curated:
            with self.subTest(canonical_name=item["canonical_name"]):
                self.assertEqual(
                    item["method_cards"],
                    generated_by_name[item["canonical_name"]]["method_cards"],
                )

        reference_root = (
            REPO / "skills" / "ksrf-complaint-cycle" / "references"
        )
        for name in ("strategic-complaint-design.md", "science-support-pack.md"):
            self.assertTrue((reference_root / name).is_file())

    def test_authority_builder_is_source_only_while_prebuilt_corpus_remains_runtime(self) -> None:
        root_builder = REPO / "tools" / "build_constitutionalist_authority_corpus.py"
        nested_builder = (
            REPO
            / "skills"
            / "ksrf-argument-patterns"
            / "scripts"
            / "build_constitutionalist_authority_corpus.py"
        )
        reference_root = REPO / "skills" / "ksrf-argument-patterns" / "references"
        json_corpus = reference_root / "constitutionalist-authority-corpus.json"
        markdown_corpus = reference_root / "constitutionalist-authority-corpus.md"
        skill = REPO / "skills" / "ksrf-argument-patterns" / "SKILL.md"
        skill_text = skill.read_text(encoding="utf-8")

        expected_digests = {
            root_builder: "b1c393460420cc1c3382720d60188dbe4e52f9c72a78d87457f833682f67c33f",
            json_corpus: "285b854f9d53a0a1ce3fa38c59f9d9ddeed8bd199979a40be6fa95b4570b7015",
            markdown_corpus: "58405ad08d408147b72ee952b5e6422963e62da19c31c8b13a5c8d91a2375e98",
        }
        for path, expected in expected_digests.items():
            with self.subTest(path=path.relative_to(REPO).as_posix()):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

        self.assertFalse(nested_builder.exists())
        payload = canonical.payload_files(REPO / "skills" / "ksrf-argument-patterns")
        self.assertIn(json_corpus, payload)
        self.assertIn(markdown_corpus, payload)
        self.assertNotIn(nested_builder, payload)
        self.assertNotIn(
            "scripts/build_constitutionalist_authority_corpus.py",
            skill_text,
        )
        self.assertIn("references/constitutionalist-authority-corpus.md", skill_text)
        self.assertIn("references/constitutionalist-authority-corpus.json", skill_text)
        self.assertIn("зафиксируй пробел", skill_text)
        self.assertIn("Пересборка реестра не входит", skill_text)


if __name__ == "__main__":
    unittest.main()
