from __future__ import annotations

import hashlib
import re
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import skillset_file_contract as contract  # noqa: E402
from install_skillset import copy_skillset  # noqa: E402


SKILL_ROOT = REPO / "skills" / "ksrf-argument-patterns"
GUIDE = SKILL_ROOT / "references" / "position-retrieval-architecture.md"
SKILL = SKILL_ROOT / "SKILL.md"
ARTIFACT_CONTRACT = (
    REPO
    / "skills"
    / "ksrf-explore-arguments"
    / "references"
    / "artifact-contracts.md"
)

ABSENT_PROJECT_PATHS = (
    "docker-compose.ksrf-retrieval.yml",
    "scripts/index_ksrf_position_retrieval.py",
    "scripts/query_ksrf_position_retrieval.py",
    "tools/mcp/ksrf_qdrant_server.py",
    "tools/mcp/ksrf_neo4j_server.py",
    "scripts/export_ksrf_vector_map.py",
    "scripts/build_ksrf_corpus_enrichment.py",
    "scripts/backfill_ksrf_qdrant_payload_anchors.py",
    "scripts/backfill_ksrf_qdrant_decision_context.py",
    "scripts/profile_ksrf_complaint_query.py",
    ".env.example",
)

PROJECT_ONLY_MARKERS = (
    "ks_parser_lower_court_marker",
    "build-ksrf-position-retrieval",
    "docker compose",
    "python3 scripts/",
    "ollama serve",
    "ollama pull",
    "tail -f",
    "Qdrant",
    "Neo4j",
    "Langfuse",
    "KSRF_QDRANT_PATH",
    "localhost:6333",
    "localhost:7474",
    "localhost:3001",
    "bolt://",
    "ksrf_position_chunks",
    "ksrf_position_semantic_chunks",
    ".ksrf-retrieval/",
    "analysis_results/",
    "conceptual.qdrant",
    "conceptual.neo4j",
    "hit rate at K",
    "MRR",
    "DeepEval/LLM-judge",
    "golden dataset",
)

FRAGMENT_ROLES = (
    "case_context",
    "challenged_norm",
    "applicant_arguments",
    "court_question",
    "legal_position",
    "constitutional_test",
    "constitutional_meaning",
    "remedy",
    "dissent_or_concurrence",
)

BALANCING_CHECKS = (
    "легитимная цель",
    "пригодность меры",
    "необходимость",
    "тяжесть бремени",
    "менее обременительные альтернативы",
    "процессуальные гарантии",
    "компенсация или смягчение последствий",
    "сохранение существа права",
)

USER_OUTPUT_FIELDS = (
    "Позиция",
    "Почему похожа",
    "Графовая связь",
    "Что переносимо",
    "Что не переносимо",
    "Какие цитаты проверить",
    "Как использовать в жалобе",
)

CANONICAL_FIELDS = (
    "source_anchor",
    "locator",
    "relation",
    "verification_status",
    "limitations",
)

RELATIONS = "supports | weakens | distinguishes | blocks"
VERIFICATION_STATUSES = "candidate | verified | rejected | superseded"
GUIDE_LINES = 190
GUIDE_BYTES = 20_372
GUIDE_SHA256 = "cbc562c0fb543735afce3a09fe9494e9ee8cd55c7fd2562030db7b62f1881ef9"
SKILL_LINES = 124
SKILL_BYTES = 25_637
SKILL_SHA256 = "0850be30f4f3d78487450f3706330df17137f586042cdbca42a6a9c1b3e18fb5"


class RuntimePayloadGuidanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guide = GUIDE.read_text(encoding="utf-8")
        self.skill = SKILL.read_text(encoding="utf-8")

    def assert_runtime_truthful(self, text: str) -> None:
        for marker in (*ABSENT_PROJECT_PATHS, *PROJECT_ONLY_MARKERS):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, text)
        for stale_counter_claim in (
            "chunks: `21692`",
            "argument cards: `19433`",
            "hard-negative candidates: `500`",
            "separate opinion chunks: `304`",
            "missing local constitutional articles: `0.8481`",
            "missing decision-level constitutional articles: `0.0812`",
        ):
            with self.subTest(stale_counter_claim=stale_counter_claim):
                self.assertNotIn(stale_counter_claim, text)

    def test_reviewed_runtime_files_have_exact_digests(self) -> None:
        for path, expected_lines, expected_bytes, expected_sha256 in (
            (GUIDE, GUIDE_LINES, GUIDE_BYTES, GUIDE_SHA256),
            (SKILL, SKILL_LINES, SKILL_BYTES, SKILL_SHA256),
        ):
            with self.subTest(path=path):
                content = path.read_bytes()
                self.assertEqual(content.count(b"\n"), expected_lines)
                self.assertEqual(len(content), expected_bytes)
                self.assertEqual(hashlib.sha256(content).hexdigest(), expected_sha256)

    def test_guide_has_no_project_only_commands_paths_services_or_counters(self) -> None:
        self.assert_runtime_truthful(self.guide)
        self.assertNotIn("```bash", self.guide)

    def test_manual_method_preserves_search_transfer_and_adverse_contract(self) -> None:
        for term in (
            "оспариваемая норма",
            "буквальный смысл",
            "судебный смысл",
            "механизм вреда",
            "право или принцип",
            "статьи Конституции",
            "предлагаемый способ защиты",
            "неизвестные звенья",
            "точный поиск",
            "структурный поиск",
            "неблагоприятный поиск",
            "прямое рассуждение от официальных опор",
            "институциональный контекст",
        ):
            with self.subTest(term=term):
                self.assertIn(term.lower(), self.guide.lower())

        for role in FRAGMENT_ROLES:
            with self.subTest(role=role):
                self.assertIn(f"`{role}`", self.guide)

        graph = (
            "оспариваемая норма → буквальный смысл → судебный смысл → последствие "
            "для заявителя → право или принцип → статья Конституции → тест КС РФ → "
            "конституционно-правовой смысл или предел неконституционности → remedy"
        )
        self.assertIn(graph, self.guide)

        for check in BALANCING_CHECKS:
            with self.subTest(check=check):
                self.assertIn(check, self.guide)

        self.assertIn("минимум один неблагоприятный", self.guide)
        self.assertIn("не означает, что релевантной практики нет", self.guide)
        self.assertIn("не делает позицию юридически более сильной", self.guide)

    def test_official_source_locator_and_transfer_gates_are_fail_closed(self) -> None:
        for gate in (
            "официальный полный текст",
            "точный locator",
            "кто говорит",
            "редакцию нормы",
            "временной контекст",
            "исход и способ защиты",
            "последующие акты",
            "предел переноса",
            "ручная юридическая проверка",
        ):
            with self.subTest(gate=gate):
                self.assertIn(gate.lower(), self.guide.lower())

        self.assertIn("`verification_status=candidate`", self.guide)
        self.assertIn("нельзя ставить `verified`", self.guide)
        self.assertIn("необъяснённое противоречие блокирует", self.guide.lower())
        self.assertIn("тайм-аут", self.guide.lower())
        self.assertIn("пробел покрытия", self.guide)

    def test_output_matches_canonical_research_finding_contract(self) -> None:
        canonical = ARTIFACT_CONTRACT.read_text(encoding="utf-8")
        self.assertIn("## ResearchFinding", self.guide)
        for field in CANONICAL_FIELDS:
            with self.subTest(field=field):
                self.assertIn(f"`{field}`", self.guide)
                self.assertIn(f"`{field}`", canonical)
        for value in RELATIONS.split(" | "):
            self.assertIn(f"`{value}`", canonical)
        for value in VERIFICATION_STATUSES.split(" | "):
            self.assertIn(f"`{value}`", canonical)
        self.assertIn(RELATIONS, self.guide)
        self.assertIn(VERIFICATION_STATUSES, self.guide)
        self.assertNotIn("`candidate_only`", self.guide)
        self.assertNotIn("`quote_locator`", self.guide)
        self.assertIn("проверку источника и locator, а не юридическую правильность", self.guide)

        for field in USER_OUTPUT_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, self.guide)
        for extra in (
            "Официальный источник и locator",
            "Статус и relation",
            "Происхождение и охват поиска",
            "Неблагоприятный результат",
        ):
            self.assertIn(extra, self.guide)

    def test_bundled_routes_are_real_shipped_markdown_links(self) -> None:
        expected = {
            (GUIDE.parent / "pattern-matrix.md").resolve(),
            (GUIDE.parent / "decision-index.md").resolve(),
            (GUIDE.parent / "constitutional-graph.md").resolve(),
            (GUIDE.parent / "evidence-maps.md").resolve(),
            (GUIDE.parent / "counterargument-playbook.md").resolve(),
            ARTIFACT_CONTRACT.resolve(),
        }
        relative_links = set()
        for raw_target in re.findall(r"\[[^]]+\]\(([^)]+)\)", self.guide):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith("#") or "://" in target:
                continue
            path_part = target.split("#", 1)[0].split("?", 1)[0]
            self.assertTrue(path_part, msg=f"empty local link target: {raw_target}")
            relative_links.add((GUIDE.parent / path_part).resolve())
        self.assertTrue(expected.issubset(relative_links))

        runtime_files = set()
        for skill_name in contract.SKILL_NAMES:
            runtime_files.update(
                path.resolve()
                for path in contract.payload_files(REPO / "skills" / skill_name)
            )
        for path in relative_links:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                self.assertIn(path, runtime_files)

    def test_payload_cleanroom_and_truthful_owner_backlink(self) -> None:
        payload = {
            path.relative_to(SKILL_ROOT).as_posix()
            for path in contract.payload_files(SKILL_ROOT)
        }
        relative_guide = "references/position-retrieval-architecture.md"
        self.assertIn(relative_guide, payload)

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", target)
            installed = target / "ksrf-argument-patterns" / relative_guide
            self.assertEqual(installed.read_bytes(), GUIDE.read_bytes())
            self.assert_runtime_truthful(installed.read_text(encoding="utf-8"))
            for raw_target in re.findall(r"\[[^]]+\]\(([^)]+)\)", self.guide):
                link_target = raw_target.strip().strip("<>")
                if not link_target or link_target.startswith("#") or "://" in link_target:
                    continue
                path_part = link_target.split("#", 1)[0].split("?", 1)[0]
                source_path = (GUIDE.parent / path_part).resolve()
                installed_path = target / source_path.relative_to(REPO / "skills")
                self.assertTrue(installed_path.is_file(), msg=raw_target)

        self.assertEqual(self.skill.count("position-retrieval-architecture.md"), 1)
        self.assertIn(
            "ручной поиск, сопоставление, официальная проверка и adverse-pass",
            self.skill,
        )
        self.assertNotIn("retrieval architecture", self.skill)
        for marker in ("Qdrant/Neo4j", "штатные scripts", "golden/hard-negative"):
            self.assertNotIn(marker, self.skill)

    def test_toc_links_resolve_and_boundary_is_explicit(self) -> None:
        def anchor_for_heading(heading: str) -> str:
            anchor = re.sub(r"[^\w\- ]", "", heading.lower())
            return re.sub(r" +", "-", anchor.strip())

        toc_anchors = re.findall(r"(?m)^- \[[^]]+\]\(#([^)]+)\)$", self.guide)
        heading_anchors = [
            anchor_for_heading(heading)
            for heading in re.findall(r"(?m)^## (.+)$", self.guide)
            if heading != "Содержание"
        ]
        self.assertGreaterEqual(len(toc_anchors), 10)
        self.assertEqual(toc_anchors, heading_anchors)
        self.assertIn("не требует локального проекта", self.guide)
        self.assertIn("не готовый абзац жалобы", self.guide)
        self.assertIn("не разрешение на подачу", self.guide)


if __name__ == "__main__":
    unittest.main()
