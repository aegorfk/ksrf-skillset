from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
SKILL = REPO / "skills" / "ksrf-argument-patterns"
GRAPH_JSON = SKILL / "references" / "constitutional_graph.json"
GRAPH_GUIDE = SKILL / "references" / "constitutional-graph.md"
EVIDENCE_JSON = SKILL / "references" / "evidence_maps.json"
EVIDENCE_GUIDE = SKILL / "references" / "evidence-maps.md"

sys.path.insert(0, str(TOOLS))

import skillset_file_contract as contract  # noqa: E402


EXPECTED_NON_AUTOMATION_GRAPH_SHA256 = (
    "9fd839ea969abaa233f06cd4fa628fa1a1ed270e4df0d7de785bdb7938db6325"
)


def _load_enricher():
    path = TOOLS / "enrich_ksrf_argument_patterns.py"
    spec = importlib.util.spec_from_file_location("runtime_graph_enricher", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Не удалось загрузить {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _graph_digest(graph: dict) -> str:
    canonical = json.dumps(
        {"nodes": graph["nodes"], "edges": graph["edges"]},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RuntimeArgumentGraphTests(unittest.TestCase):
    def test_generator_keeps_source_metadata_out_of_runtime_graph(self) -> None:
        module = _load_enricher()

        field_names = {field.name for field in dataclasses.fields(module.PatternEnrichment)}
        self.assertIn("automation_hooks", field_names)
        self.assertTrue(module.P)
        hooks = [hook for item in module.P.values() for hook in item.automation_hooks]
        self.assertEqual(len(hooks), 60)
        self.assertEqual(len(set(hooks)), 58)

        graph = module.build_graph({})
        self.assertEqual(len(graph["nodes"]), 179)
        self.assertEqual(len(graph["edges"]), 329)
        self.assertFalse(
            any(node.get("kind") == "automation_hook" for node in graph["nodes"])
        )
        self.assertFalse(
            any(str(node.get("id", "")).startswith("tool:") for node in graph["nodes"])
        )
        self.assertFalse(
            any(edge.get("type") == "supported_by" for edge in graph["edges"])
        )

    def test_committed_graph_is_exact_non_automation_projection(self) -> None:
        graph = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))

        self.assertEqual(len(graph["nodes"]), 262)
        self.assertEqual(len(graph["edges"]), 489)
        self.assertFalse(
            any(node.get("kind") == "automation_hook" for node in graph["nodes"])
        )
        self.assertFalse(
            any(str(node.get("id", "")).startswith("tool:") for node in graph["nodes"])
        )
        self.assertFalse(
            any(edge.get("type") == "supported_by" for edge in graph["edges"])
        )
        self.assertEqual(
            Counter(node["kind"] for node in graph["nodes"]),
            {
                "ksrf_decision": 83,
                "norm_type": 69,
                "harm_type": 59,
                "constitutional_article": 31,
                "pattern": 20,
            },
        )
        self.assertEqual(
            Counter(edge["type"] for edge in graph["edges"]),
            {
                "has_anchor": 160,
                "may_trigger": 153,
                "uses_article": 87,
                "reinforces_with": 49,
                "can_be_saved_by": 20,
                "remedy_with": 20,
            },
        )
        node_ids = {node["id"] for node in graph["nodes"]}
        self.assertTrue(
            all(
                edge["from"] in node_ids and edge["to"] in node_ids
                for edge in graph["edges"]
            )
        )
        self.assertEqual(_graph_digest(graph), EXPECTED_NON_AUTOMATION_GRAPH_SHA256)

    def test_evidence_maps_keep_metadata_source_only_and_runtime_truthful(self) -> None:
        module = _load_enricher()
        evidence = json.loads(EVIDENCE_JSON.read_text(encoding="utf-8"))
        guide = EVIDENCE_GUIDE.read_text(encoding="utf-8")

        self.assertEqual(
            hashlib.sha256(EVIDENCE_JSON.read_bytes()).hexdigest(),
            "54122e7543c72095497ecb4a8147afa62d8bcdbf19193ca09e1438db7d5fb4be",
        )
        self.assertEqual(list(evidence), module.PATTERN_ORDER)
        for code, item in evidence.items():
            with self.subTest(code=code):
                self.assertTrue(item["automation_hooks"])
                for key in ("proof_tasks", "evidence", "falsifiers", "decision_anchors"):
                    self.assertTrue(item[key], f"{code}: empty {key}")
                self.assertIn(f"## {code}: {item['title']}", guide)

        self.assertIn("## Admissibility overlay для любой жалобы", guide)
        self.assertNotIn("**Автоматизация:**", guide)

    def test_graph_guide_does_not_describe_removed_capabilities(self) -> None:
        guide = GRAPH_GUIDE.read_text(encoding="utf-8")
        graph = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
        relation_types = {edge["type"] for edge in graph["edges"]}

        self.assertNotIn("automation_hook", guide)
        self.assertNotIn("supported_by", guide)
        self.assertNotIn("инструментам", guide)
        for relation_type in relation_types:
            self.assertIn(f"`{relation_type}`", guide)

    def test_generator_never_overwrites_curated_evidence_guide(self) -> None:
        module = _load_enricher()
        with tempfile.TemporaryDirectory() as temporary:
            refs = Path(temporary)
            guide = refs / "evidence-maps.md"
            sentinel = "# Curated runtime guide\n\nAdmissibility overlay must survive.\n"
            guide.write_text(sentinel, encoding="utf-8")

            module.write_evidence_maps(refs, {})

            self.assertEqual(guide.read_text(encoding="utf-8"), sentinel)
            metadata = json.loads(
                (refs / "evidence_maps.json").read_text(encoding="utf-8")
            )
            self.assertEqual(list(metadata), module.PATTERN_ORDER)
            self.assertTrue(
                all(item["automation_hooks"] for item in metadata.values())
            )

    def test_generator_requires_curated_evidence_guide_before_writing(self) -> None:
        module = _load_enricher()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            analysis = root / "analysis"
            skill = root / "skill"
            analysis.mkdir()

            with mock.patch.object(
                sys,
                "argv",
                [
                    "enrich_ksrf_argument_patterns.py",
                    "--analysis",
                    str(analysis),
                    "--skill",
                    str(skill),
                ],
            ):
                with self.assertRaisesRegex(
                    SystemExit,
                    "curated runtime evidence guide",
                ):
                    module.main()

            self.assertFalse(
                (skill / "references" / "constitutional_graph.json").exists()
            )
            self.assertFalse((skill / "references" / "evidence_maps.json").exists())

    def test_runtime_payload_has_no_removed_capability_vocabulary(self) -> None:
        forbidden = ('"automation_hooks"', '"automation_hook"', '"tool:', "**Автоматизация:**")
        for path in contract.payload_files(SKILL):
            if path.suffix not in {".md", ".json"}:
                continue
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                with self.subTest(path=path.relative_to(SKILL), marker=marker):
                    self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
