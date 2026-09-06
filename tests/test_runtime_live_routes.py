from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import skillset_file_contract as contract  # noqa: E402
from install_skillset import copy_skillset  # noqa: E402


TARGETS = {
    "ksrf-case-triage": (
        REPO / "skills/ksrf-case-triage/references/complaint-patterns.md",
        "d5d83aa4b9b1520ed7641e54318951e0de6a82fbdd28bce758f69e2747e8a0b8",
    ),
    "ksrf-rights-argument-builder": (
        REPO / "skills/ksrf-rights-argument-builder/references/complaint-patterns.md",
        "1f95622f887dbbff81602dcb2fbcf435864f6d04eb7c5deb0bcc674bf8766e1d",
    ),
    "ksrf-complaint-facts-demands": (
        REPO / "skills/ksrf-complaint-facts-demands/references/complaint-patterns.md",
        "0bae72ebbbb414aaef5ec15bb349b782445158e70dffd7b72f8ef671dae7a268",
    ),
}

OWNERS = {
    name: REPO / "skills" / name / "SKILL.md"
    for name in TARGETS
}

PRACTICE_GUIDE = (
    REPO
    / "skills"
    / "ksrf-practice-authority-builder"
    / "references"
    / "judicial-meaning-evidence-acquisition.md"
)
OLD_FUTURE_SENTENCE = (
    "Это метод исследования и будущий контракт автоматизации. Он не подтверждает "
    "практику сам, не запускает сборщик и не создаёт полномочий КС РФ."
)
PRACTICE_GUIDE_OUTSIDE_SHA256 = (
    "fac6ef8f3585d7f311a3ebe0cdd5a5b8180f3248a15d94c51c7cfa907f793334"
)

FORBIDDEN_PRODUCT_WORDING = (
    "## Идеи функциональности",
    "Индексатор",
    "Builder обзора практики",
    "Конструктор обзора практики",
    "Рекомендатель формулы требования",
    "Selector аргументативных блоков",
    "Выбор аргументативных блоков: решает",
    "Трекер сохранения аргумента",
    "кластеризация по толкованию и исходу",
)

COMMON_ROUTES = (
    "../../ksrf-argument-patterns/references/position-retrieval-architecture.md",
    "../../ksrf-practice-authority-builder/SKILL.md",
    "../../ksrf-complaint-cycle/references/ksrf-tool-layer.md",
    "../../ksrf-complaint-cycle/references/practice-analysis-integration.md",
    "../../ksrf-complaint-facts-demands/references/remedy-design-matrix.md",
    "../../ksrf-explore-arguments/SKILL.md",
    "../../ksrf-exhaustion-planner/SKILL.md",
)

CANDIDATE_KEYS = (
    "summary.application_bridge_candidates",
    "summary.constitutional_test_suggestions",
    "summary.request_formula_candidates",
    "summary.practice_matrix_candidates",
)

SOURCE_ONLY_FILES = {
    REPO / "skills/ksrf-argument-patterns/references/automation-backlog.md": (
        "d25a9df36f6c1d7d995deae35f22a6b9875ac6597251342492ae69a111d75e94"
    ),
    REPO / "skills/ksrf-argument-patterns/references/complaint-methodology-sources.md": (
        "6341e9870574e3473eb1831fc7eba0847f6956de06f2fd4fb200994f49b4ae26"
    ),
}

REVIEWED_RUNTIME_FILES = {
    REPO / "skills/ksrf-case-triage/SKILL.md": (
        91,
        19_276,
        "6d2dd1587aad2ab65687fcdf4d6b256e7379acb02d10566ee79d68b1e9302e87",
    ),
    REPO / "skills/ksrf-case-triage/references/complaint-patterns.md": (
        86,
        16_545,
        "75781bce49525d2413146d830a11c777db45f780689e8e6b12191367432a4927",
    ),
    REPO / "skills/ksrf-complaint-facts-demands/SKILL.md": (
        78,
        16_867,
        "cac61907cdaadfbbc2e1876b34168134da3ad4bb63c2e3b5714f9622df425652",
    ),
    REPO / "skills/ksrf-complaint-facts-demands/references/complaint-patterns.md": (
        65,
        12_033,
        "b438cf7eb91cc6415848e2efa231c7d87715ed64b29f65a1fb7ecfb4b05ddef4",
    ),
    REPO / "skills/ksrf-rights-argument-builder/SKILL.md": (
        117,
        28_581,
        "a1868451c13f8ea5b58b3219791c3661eedea7e5a8aa932ef2b1405db48e6f33",
    ),
    REPO / "skills/ksrf-rights-argument-builder/references/complaint-patterns.md": (
        74,
        15_795,
        "bb8986e2deb1b04e56b84f81e7cdecef2b15641d92eb628e2e65f51e255fea50",
    ),
    PRACTICE_GUIDE: (
        245,
        27_554,
        "603f3652000dd8122a33f7f0cca75dbdbee7994dd725793815d7f89cfd378b0c",
    ),
}

BLOCK_RE = re.compile(
    r"## (?:Идеи функциональности|Исполнимые маршруты)\n.*?(?=## Красные флаги)",
    re.DOTALL,
)


def replaceable_block(text: str) -> str:
    match = BLOCK_RE.search(text)
    if match is None:
        raise AssertionError("replaceable runtime block is missing")
    return match.group(0)


def without_replaceable_block(text: str) -> bytes:
    projected, count = BLOCK_RE.subn("", text, count=1)
    if count != 1:
        raise AssertionError(f"expected one replaceable block, got {count}")
    return projected.encode("utf-8")


def local_markdown_targets(text: str, parent: Path) -> set[Path]:
    targets: set[Path] = set()
    for raw_target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        target = raw_target.strip().strip("<>")
        if not target or target.startswith("#") or "://" in target:
            continue
        path_part = target.split("#", 1)[0].split("?", 1)[0]
        if path_part:
            targets.add((parent / path_part).resolve())
    return targets


class RuntimeLiveRoutesTests(unittest.TestCase):
    def test_reviewed_runtime_files_have_exact_digests(self) -> None:
        for path, (expected_lines, expected_bytes, expected_sha256) in (
            REVIEWED_RUNTIME_FILES.items()
        ):
            content = path.read_bytes()
            with self.subTest(path=path):
                self.assertEqual(content.count(b"\n"), expected_lines)
                self.assertEqual(len(content), expected_bytes)
                self.assertEqual(hashlib.sha256(content).hexdigest(), expected_sha256)

    def test_only_the_frozen_feature_idea_blocks_may_change(self) -> None:
        for name, (path, expected_sha256) in TARGETS.items():
            with self.subTest(skill=name):
                digest = hashlib.sha256(
                    without_replaceable_block(path.read_text(encoding="utf-8"))
                ).hexdigest()
                self.assertEqual(digest, expected_sha256)

        practice_text = PRACTICE_GUIDE.read_text(encoding="utf-8")
        projected_text, count = re.subn(
            r"(?m)^Это метод исследования.*\n", "", practice_text, count=1
        )
        self.assertEqual(count, 1)
        projected = projected_text.encode("utf-8")
        self.assertEqual(
            hashlib.sha256(projected).hexdigest(),
            PRACTICE_GUIDE_OUTSIDE_SHA256,
        )

    def test_installed_guides_have_no_future_product_claims(self) -> None:
        for name, (path, _) in TARGETS.items():
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=name):
                self.assertIn("## Исполнимые маршруты", text)
                for wording in FORBIDDEN_PRODUCT_WORDING:
                    self.assertNotIn(wording, text)

        self.assertNotIn(
            OLD_FUTURE_SENTENCE, PRACTICE_GUIDE.read_text(encoding="utf-8")
        )

        runtime_files = [
            path
            for skill_name in contract.SKILL_NAMES
            for path in contract.payload_files(REPO / "skills" / skill_name)
        ]
        matches = []
        for path in runtime_files:
            if path.suffix.lower() not in {".md", ".txt", ".json", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8")
            if "Идеи функциональности" in text or "будущий контракт автоматизации" in text:
                matches.append(path.relative_to(REPO).as_posix())
        self.assertEqual(matches, [])

    def test_each_goal_maps_to_a_shipped_route_and_bounded_output(self) -> None:
        runtime_files = {
            path.resolve()
            for skill_name in contract.SKILL_NAMES
            for path in contract.payload_files(REPO / "skills" / skill_name)
        }
        expected_routes = {
            (next(iter(TARGETS.values()))[0].parent / route).resolve()
            for route in COMMON_ROUTES
        }

        for name, (path, _) in TARGETS.items():
            block = replaceable_block(path.read_text(encoding="utf-8"))
            linked = local_markdown_targets(block, path.parent)
            with self.subTest(skill=name):
                self.assertTrue(expected_routes.issubset(linked))
                for route in linked:
                    self.assertTrue(route.is_file(), msg=route)
                    self.assertIn(route, runtime_files)
                for term in (
                    "ResearchFinding",
                    "проверенном объёме",
                    "основной и более узкий",
                    "выбор человека",
                    "точный locator",
                    "официальный акт",
                ):
                    self.assertIn(term, block)
                for key in CANDIDATE_KEYS:
                    self.assertIn(f"`{key}`", block)

    def test_preservation_and_legal_choice_remain_fail_closed(self) -> None:
        for name, (path, _) in TARGETS.items():
            block = replaceable_block(path.read_text(encoding="utf-8"))
            with self.subTest(skill=name):
                self.assertIn("документ", block)
                self.assertIn("стадию", block)
                self.assertIn("дату", block)
                self.assertIn("точный locator", block)
                self.assertIn("если такого места нет", block.lower())
                self.assertIn("не выбирает", block)
                self.assertIn("не доказывает", block)

    def test_routes_survive_cleanroom_installation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            installed_root = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", installed_root)
            for name, (source, _) in TARGETS.items():
                relative = source.relative_to(REPO / "skills")
                installed = installed_root / relative
                block = replaceable_block(source.read_text(encoding="utf-8"))
                with self.subTest(skill=name):
                    self.assertEqual(installed.read_bytes(), source.read_bytes())
                    for route in local_markdown_targets(block, source.parent):
                        installed_route = installed_root / route.relative_to(REPO / "skills")
                        self.assertTrue(installed_route.is_file(), msg=installed_route)
            self.assertFalse(any(installed_root.glob("ksrf-*/tests")))
            self.assertFalse(any(installed_root.glob("ksrf-*/evals")))

            installed_practice = installed_root / PRACTICE_GUIDE.relative_to(REPO / "skills")
            self.assertEqual(installed_practice.read_bytes(), PRACTICE_GUIDE.read_bytes())
            practice_links = local_markdown_targets(
                PRACTICE_GUIDE.read_text(encoding="utf-8"), PRACTICE_GUIDE.parent
            )
            expected_integration = (
                REPO
                / "skills/ksrf-complaint-cycle/references/practice-analysis-integration.md"
            ).resolve()
            self.assertIn(expected_integration, practice_links)
            self.assertTrue(
                (installed_root / expected_integration.relative_to(REPO / "skills")).is_file()
            )

    def test_owning_backlinks_describe_live_checks(self) -> None:
        for name, owner in OWNERS.items():
            text = owner.read_text(encoding="utf-8")
            with self.subTest(skill=name):
                self.assertEqual(text.count("references/complaint-patterns.md"), 1)
                self.assertIn("исполняемые маршруты", text)
                self.assertNotIn("идеи дополнительных", text)
                self.assertNotIn("optional drafting examples", text)

    def test_real_runtime_entrypoints_are_callable(self) -> None:
        scripts = (
            REPO / "skills/ksrf-complaint-cycle/scripts/ksrf_autocollect.py",
            REPO / "skills/ksrf-complaint-cycle/scripts/ksrf_practice_analysis.py",
            REPO / "skills/ksrf-complaint-cycle/scripts/ksrf_filing_pack.py",
        )
        for script in scripts:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, str(script), "--help"],
                    cwd=REPO,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_source_only_roadmaps_remain_unchanged_and_uninstalled(self) -> None:
        runtime_files = {
            path.resolve()
            for skill_name in contract.SKILL_NAMES
            for path in contract.payload_files(REPO / "skills" / skill_name)
        }
        for path, expected_sha256 in SOURCE_ONLY_FILES.items():
            with self.subTest(path=path):
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(), expected_sha256
                )
                self.assertNotIn(path.resolve(), runtime_files)


if __name__ == "__main__":
    unittest.main()
