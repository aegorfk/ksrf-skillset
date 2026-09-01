from __future__ import annotations

import importlib.util
import json
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
                "ksrf-argument-patterns/references/evidence_maps.json",
                "ksrf-argument-patterns/references/hearing_argument_techniques.json",
                "ksrf-argument-patterns/references/language_formulas.json",
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


if __name__ == "__main__":
    unittest.main()
