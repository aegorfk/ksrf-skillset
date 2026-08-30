#!/usr/bin/env python3
"""Regression tests for the offline argument-pattern enrichment entrypoints."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "enrich_ksrf_argument_patterns.py"
MIRRORED_TOOL = SKILL_ROOT.parents[1] / "tools" / "enrich_ksrf_argument_patterns.py"
PATTERN_CODES = (
    "practice-split",
    "legal-certainty",
    "constitutional-meaning",
    "proportionality",
    "interest-balance",
    "effective-remedy",
    "procedural-guarantees",
    "equality-differentiation",
    "legitimate-expectations",
    "retroactivity",
    "non-mechanical-application",
    "liability-fairness",
    "property-compensation",
    "social-state-positive-obligation",
    "federalism-competence",
    "legislative-gap",
    "good-faith-abuse",
    "constitutional-identity-human-dignity",
    "international-standards",
    "reconsideration-execution",
)


def valid_registry() -> dict[str, list[dict[str, str]]]:
    return {
        code: [{"number": f"{index + 1}-П"}]
        for index, code in enumerate(PATTERN_CODES)
    }


class EnrichmentRegistryContractTests(unittest.TestCase):
    def run_entrypoint(
        self,
        script: Path,
        registry: object,
        *,
        raw_json: str | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], bool, bool]:
        with tempfile.TemporaryDirectory(prefix="ksrf-enrich-test-") as temporary:
            root = Path(temporary)
            analysis = root / "analysis"
            skill = root / "skill"
            (analysis / "texts").mkdir(parents=True)
            registry_path = analysis / "expanded_pattern_registry.json"
            registry_path.write_text(
                raw_json
                if raw_json is not None
                else json.dumps(registry, ensure_ascii=False),
                encoding="utf-8",
            )
            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--analysis",
                    str(analysis),
                    "--skill",
                    str(skill),
                ],
                capture_output=True,
                text=True,
                env=environment,
                check=False,
            )
            summary_exists = (analysis / "enrichment_summary.json").is_file()
            graph_exists = (skill / "references" / "constitutional-graph.md").is_file()
            return result, summary_exists, graph_exists

    def run_without_registry(
        self, script: Path
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="ksrf-enrich-missing-") as temporary:
            root = Path(temporary)
            analysis = root / "analysis"
            skill = root / "skill"
            (analysis / "texts").mkdir(parents=True)
            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            return subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--analysis",
                    str(analysis),
                    "--skill",
                    str(skill),
                ],
                capture_output=True,
                text=True,
                env=environment,
                check=False,
            )

    def test_valid_registry_keeps_both_entrypoints_successful(self) -> None:
        for script in (SCRIPT, MIRRORED_TOOL):
            with self.subTest(script=script.name, path=str(script)):
                result, summary_exists, graph_exists = self.run_entrypoint(
                    script, valid_registry()
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('"graph_nodes"', result.stdout)
                self.assertNotIn("Traceback", result.stderr)
                self.assertTrue(summary_exists)
                self.assertTrue(graph_exists)

    def test_malformed_registry_is_controlled_before_output(self) -> None:
        cases: list[tuple[str, object | None, str | None]] = [
            ("missing-patterns", {}, None),
            ("top-level-list", [], None),
            ("top-level-scalar", "registry", None),
            (
                "pattern-scalar",
                {**valid_registry(), "practice-split": "not-an-array"},
                None,
            ),
            (
                "row-scalar",
                {**valid_registry(), "practice-split": ["not-an-object"]},
                None,
            ),
            (
                "row-object-without-number",
                {**valid_registry(), "practice-split": [{}]},
                None,
            ),
            (
                "row-number-wrong-type",
                {**valid_registry(), "practice-split": [{"number": []}]},
                None,
            ),
            ("invalid-json", None, "{\"practice-split\": ["),
        ]
        for script in (SCRIPT, MIRRORED_TOOL):
            for label, registry, raw_json in cases:
                with self.subTest(script=script.name, case=label):
                    result, summary_exists, graph_exists = self.run_entrypoint(
                        script,
                        registry,
                        raw_json=raw_json,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("ERROR:", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse(summary_exists)
                    self.assertFalse(graph_exists)

    def test_missing_registry_is_controlled(self) -> None:
        for script in (SCRIPT, MIRRORED_TOOL):
            with self.subTest(script=script.name, path=str(script)):
                result = self.run_without_registry(script)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("ERROR:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
