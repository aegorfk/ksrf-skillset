from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "validate_ksrf_skillset.py"
)
CANONICAL_AUTHORITY_CORPUS = (
    SCRIPT.parents[2]
    / "ksrf-argument-patterns"
    / "references"
    / "constitutionalist-authority-corpus.json"
)
SPEC = importlib.util.spec_from_file_location("validate_ksrf_skillset", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Не удалось подготовить импорт {SCRIPT}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_valid_skill(root: Path, name: str = "ksrf-test") -> Path:
    skill = root / name
    _write(
        skill / "SKILL.md",
        f"""---
name: {name}
description: Скилл проверяет тестовый пакет жалобы в КС РФ. Он применяется, когда нужно проверить упаковку, ссылки и сценарии запуска перед публикацией.
allowed-tools:
  - Read
  - mcp__casuslegal__search_practice
---

# Тестовый KSRF skill

Прочитай [маршрут](references/guide.md).
""",
    )
    _write(
        skill / "agents" / "openai.yaml",
        f"""interface:
  display_name: "Тестовый KSRF skill"
  short_description: "Проверка упаковки тестового KSRF skill"
  default_prompt: "Используй ${name} для проверки пакета."
tools:
  - Read
  - mcp__casuslegal__search_practice
policy:
  allow_implicit_invocation: true
""",
    )
    _write(
        skill / "references" / "guide.md",
        "# Маршрут\n\nКороткая проверяемая инструкция.\n",
    )
    _write(
        skill / "evals" / "evals.json",
        json.dumps(
            {
                "skill_name": name,
                "evals": [
                    {
                        "id": index,
                        "prompt": f"Проверь сценарий {index} для жалобы в КС РФ.",
                        "expected_output": "Проверяемый результат с явным ограничением.",
                        "files": [],
                        "expectations": ["Результат содержит проверяемый вывод."],
                    }
                    for index in range(1, 4)
                ],
            },
            ensure_ascii=False,
        ),
    )
    _write(
        skill / "evals" / "trigger-evals.json",
        json.dumps(
            [
                {
                    "query": "Проверь пакет жалобы в КС РФ перед публикацией.",
                    "should_trigger": True,
                },
                {
                    "query": "Составь договор аренды квартиры.",
                    "should_trigger": False,
                },
            ],
            ensure_ascii=False,
        ),
    )
    if name == "ksrf-argument-patterns":
        _write(
            skill
            / "references"
            / "constitutionalist-authority-corpus.json",
            CANONICAL_AUTHORITY_CORPUS.read_text(encoding="utf-8"),
        )
        for reference in (
            "constitutional-review-methods.md",
            "science-support-pack.md",
            "workflow-reference.md",
            "sko-complaint-methods-2017-2026.md",
            "evidence-impact-method.md",
            "strategic-complaint-design.md",
        ):
            _write(
                skill / "references" / reference,
                f"# Тестовая цель {reference}\n",
            )
        for referenced_skill in (
            "ksrf-case-triage",
            "ksrf-court-request-motion",
            "ksrf-decision-execution",
        ):
            _write(root / referenced_skill / "SKILL.md", "# Тестовая цель\n")
    return skill


EXACT_MAINTAINER_FILES = (
    ("ksrf-argument-patterns", Path("references/hearing_argument_techniques.json")),
    ("ksrf-argument-patterns", Path("references/language_formulas.json")),
    ("ksrf-argument-patterns", Path("references/evidence_maps.json")),
    (
        "ksrf-argument-patterns",
        Path("references/argument_techniques_from_decisions.json"),
    ),
    (
        "ksrf-argument-patterns",
        Path("references/complaint-methodology-sources.md"),
    ),
    (
        "ksrf-argument-patterns",
        Path("references/automation-backlog.md"),
    ),
    ("ksrf-complaint-cycle", Path("scripts/add_reference_tocs.py")),
    (
        "ksrf-argument-patterns",
        Path("scripts/enrich_ksrf_argument_patterns.py"),
    ),
    (
        "ksrf-argument-patterns",
        Path("scripts/extract_ksrf_argument_patterns.py"),
    ),
)


def _codes(report: dict[str, Any]) -> set[str]:
    return {
        str(item["code"])
        for item in report["findings"]
        if isinstance(item, dict)
    }


def _semantic_digest(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _minimal_authority_corpus() -> dict[str, Any]:
    status_legend = dict(
        getattr(
            VALIDATOR,
            "AUTHORITY_CORPUS_STATUS_LABELS",
            {
                "method_integrated": "метод проверен",
                "full_text_available": "доступен полный текст",
                "triangulated_academic": "академический след подтверждён",
                "academic_indexed": "автор есть в указателе",
                "bibliographic_lead": "библиографический ориентир",
                "discovery_only": "только разведочный кандидат",
            },
        )
    )
    route_legend = dict(
        getattr(
            VALIDATOR,
            "AUTHORITY_CORPUS_ROUTE_LABELS",
            {"admissibility_and_route": "Тестовый маршрут"},
        )
    )
    route = "admissibility_and_route"
    return {
        "schema_version": "2.0",
        "as_of": "2026-09-02",
        "purpose": "Тестовый пользовательский корпус",
        "warning": getattr(
            VALIDATOR,
            "AUTHORITY_CORPUS_WARNING",
            "Корпус не заменяет официальные источники.",
        ),
        "status_legend": status_legend,
        "route_legend": route_legend,
        "sources": [
            {
                "kind": "blokhin_bibliography",
                "label": "Тестовая библиография",
                "coverage": "тестовый охват библиографии",
            },
            {
                "kind": "sko_index",
                "label": "Публичный указатель",
                "coverage": "тестовый охват",
                "url": "https://example.com/index.pdf",
            },
            {
                "kind": "mp_index",
                "label": "Второй публичный указатель",
                "coverage": "второй тестовый охват",
            },
            {
                "kind": "zakon_discovery",
                "label": "Разведочный источник",
                "coverage": "разведочный тестовый охват",
            },
            {
                "kind": "curated_method",
                "label": "Проверенная карточка",
                "coverage": "проверенные тестовые карточки",
            },
        ],
        "summary": {
            "authorities_total": 1,
            "status_counts": {"academic_indexed": 1},
            "source_people_counts": {"sko_index": 1},
            "route_counts": {route: 1},
            "works_total": 1,
            "needs_review_total": 1,
        },
        "authorities": [
            {
                "id": "authority-test",
                "identity_key": "тестовый|автор",
                "canonical_name": "Тестовый автор",
                "status": "academic_indexed",
                "status_label": status_legend["academic_indexed"],
                "method_integrated": False,
                "needs_identity_or_method_review": True,
                "routes": [route],
                "source_counts": {"sko_index": 1},
                "full_text_sources": [],
                "method_cards": [],
                "works": [
                    {
                        "source": "sko_index",
                        "title": "Тестовая работа",
                        "url": "https://example.com/work",
                    }
                ],
            }
        ],
    }


class KSRFSkillsetValidatorTests(unittest.TestCase):
    def test_canonical_package_allowlist_has_exactly_fifteen_skills(self) -> None:
        self.assertEqual(len(VALIDATOR.CANONICAL_KSRF_PACKAGES), 15)
        self.assertNotIn(
            "ksrf-complaint-cycle-workspace",
            VALIDATOR.CANONICAL_KSRF_PACKAGES,
        )

    def test_nested_snapshot_cannot_duplicate_a_canonical_skill_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            nested = (
                root
                / "ksrf-test-workspace"
                / "skill-snapshot"
                / "ksrf-test"
                / "SKILL.md"
            )
            _write(nested, (skill / "SKILL.md").read_text(encoding="utf-8"))

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-test",),
            )

            self.assertEqual(report["status"], "fail")
            self.assertIn("NESTED_SKILL_DUPLICATE", _codes(report))

    def test_valid_package_passes_and_publish_manifest_is_relative_and_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(skill / ".serena" / "project.yml", "project: local\n")
            _write(skill / "scripts" / "__pycache__" / "helper.pyc", "compiled")
            _write(skill / "tests" / "test_source_only.py", "def test_source_only(): pass\n")
            _write(skill / "tests" / "fixtures" / "case.json", "{}\n")

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            self.assertEqual(report["status"], "pass")
            paths = [item["path"] for item in report["publish_manifest"]["files"]]
            self.assertIn("ksrf-test/SKILL.md", paths)
            self.assertTrue(all(not Path(path).is_absolute() for path in paths))
            self.assertTrue(all(".." not in Path(path).parts for path in paths))
            self.assertTrue(all(".serena" not in path for path in paths))
            self.assertTrue(all("__pycache__" not in path for path in paths))
            self.assertTrue(all("tests" not in Path(path).parts for path in paths))
            self.assertTrue(all("evals" not in Path(path).parts for path in paths))
            self.assertTrue(all(not path.endswith(".pyc") for path in paths))
            self.assertIn("RUNTIME_ARTIFACT_EXCLUDED", _codes(report))

    def test_frontmatter_name_description_and_line_limit_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            long_body = "\n".join(f"строка {index}" for index in range(505))
            _write(
                skill / "SKILL.md",
                """---
name: wrong-name
description: Используй этот навык для всего.
---
"""
                + long_body,
            )

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            codes = _codes(report)
            self.assertEqual(report["status"], "fail")
            self.assertIn("FRONTMATTER_NAME_MISMATCH", codes)
            self.assertIn("DESCRIPTION_NOT_THIRD_PERSON", codes)
            self.assertIn("DESCRIPTION_TRIGGER_NOT_PRECISE", codes)
            self.assertIn("SKILL_TOO_LONG", codes)

    def test_malformed_yaml_is_reported_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(
                skill / "SKILL.md",
                "---\nname: [broken\ndescription: malformed\n---\n# Body\n",
            )

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            self.assertIn("FRONTMATTER_INVALID", _codes(report))
            self.assertEqual(report["status"], "fail")

    def test_duplicate_eval_json_keys_are_reported_without_crashing(self) -> None:
        cases = (
            (
                Path("evals/evals.json"),
                '{"skill_name":"ksrf-test","skill_name":"other","evals":[]}',
                "BEHAVIORAL_EVALS_INVALID",
            ),
            (
                Path("evals/trigger-evals.json"),
                '[{"query":"первая","query":"вторая","should_trigger":true}]',
                "TRIGGER_EVALS_INVALID",
            ),
        )
        for relative, content, expected_code in cases:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                skill = _make_valid_skill(root)
                _write(skill / relative, content)

                report = VALIDATOR.validate_skillset(
                    root,
                    package_names=("ksrf-test",),
                )

                self.assertEqual(report["status"], "fail")
                self.assertIn(expected_code, _codes(report))

    def test_broken_or_escaping_markdown_links_and_late_toc_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(
                skill / "SKILL.md",
                (skill / "SKILL.md").read_text(encoding="utf-8")
                + "\n[Нет файла](references/missing.md)\n"
                + "[Выход наружу](../../outside.md)\n",
            )
            _write(
                skill / "references" / "long.md",
                "# Большой справочник\n\n" + "\n".join(f"Раздел {index}" for index in range(105)),
            )

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            codes = _codes(report)
            self.assertIn("BROKEN_MARKDOWN_LINK", codes)
            self.assertIn("MARKDOWN_LINK_ESCAPES_SKILLSET", codes)
            self.assertIn("REFERENCE_TOC_MISSING", codes)

    def test_early_toc_satisfies_progressive_disclosure_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            long_reference = """# Большой справочник

## Содержание

- [Первая часть](#первая-часть)
- [Вторая часть](#вторая-часть)

## Первая часть
""" + "\n".join(f"Строка {index}" for index in range(105))
            _write(skill / "references" / "long.md", long_reference)

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            self.assertNotIn("REFERENCE_TOC_MISSING", _codes(report))

    def test_reference_over_one_hundred_lines_requires_early_toc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            exactly_one_hundred = "\n".join(f"Строка {index}" for index in range(100))
            over_one_hundred = "\n".join(f"Строка {index}" for index in range(101))
            _write(skill / "references" / "exactly-100.md", exactly_one_hundred)
            _write(skill / "references" / "over-100.md", over_one_hundred)

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            toc_findings = [
                item
                for item in report["findings"]
                if item.get("code") == "REFERENCE_TOC_MISSING"
            ]
            self.assertEqual(
                [item.get("path") for item in toc_findings],
                ["ksrf-test/references/over-100.md"],
            )

    def test_early_index_with_anchor_link_is_accepted_as_toc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            long_reference = """# Большой справочник

## Индекс

- [Единственный раздел](#единственный-раздел)

## Единственный раздел
""" + "\n".join(f"Строка {index}" for index in range(105))
            _write(skill / "references" / "indexed.md", long_reference)

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            self.assertNotIn("REFERENCE_TOC_MISSING", _codes(report))

    def test_behavioral_and_trigger_eval_minimums_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(
                skill / "evals" / "evals.json",
                json.dumps(
                    {
                        "skill_name": "ksrf-test",
                        "evals": [
                            {
                                "id": 1,
                                "prompt": "Один сценарий",
                                "expected_output": "Один результат",
                                "files": [],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            )
            _write(
                skill / "evals" / "trigger-evals.json",
                json.dumps(
                    [{"query": "Только положительный", "should_trigger": True}],
                    ensure_ascii=False,
                ),
            )

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            codes = _codes(report)
            self.assertIn("BEHAVIORAL_EVALS_INSUFFICIENT", codes)
            self.assertIn("TRIGGER_EVAL_POLARITY_MISSING", codes)

    def test_source_profile_is_default_and_missing_evals_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            (skill / "evals" / "evals.json").unlink()
            (skill / "evals" / "trigger-evals.json").unlink()
            (skill / "evals").rmdir()

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            self.assertEqual(report["validation_profile"], "source")
            self.assertEqual(report["validation_coverage"]["evals"], "validated")
            self.assertFalse(report["source_release_eligible"])
            self.assertIn("BEHAVIORAL_EVALS_MISSING", _codes(report))
            self.assertIn("TRIGGER_EVALS_MISSING", _codes(report))

    def test_runtime_profile_passes_without_evals_and_discloses_limited_scope(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            (skill / "evals" / "evals.json").unlink()
            (skill / "evals" / "trigger-evals.json").unlink()
            (skill / "evals").rmdir()

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-test",),
                profile="runtime",
            )

            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["validation_profile"], "runtime")
            self.assertEqual(report["validation_coverage"]["evals"], "not_checked")
            self.assertEqual(
                report["validation_coverage"]["public_source_safety"],
                "not_checked",
            )
            self.assertEqual(
                report["validation_coverage"]["public_repository_safety"],
                "not_checked",
            )
            self.assertFalse(report["source_release_eligible"])
            self.assertIsNone(report["publish_manifest"])
            self.assertNotIn("BEHAVIORAL_EVALS_MISSING", _codes(report))
            self.assertNotIn("TRIGGER_EVALS_MISSING", _codes(report))
            rendered = VALIDATOR._render_text(report)
            self.assertIn("Профиль: runtime", rendered)
            self.assertIn("не заменяет source/release QA", rendered)

    def test_runtime_profile_rejects_source_only_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_valid_skill(root)

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-test",),
                profile="runtime",
            )

            self.assertEqual(report["status"], "fail")
            self.assertIn("SOURCE_ONLY_ARTIFACT_PRESENT", _codes(report))

    def test_runtime_profile_keeps_non_eval_validation_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            (skill / "evals" / "evals.json").unlink()
            (skill / "evals" / "trigger-evals.json").unlink()
            (skill / "evals").rmdir()
            _write(
                skill / "SKILL.md",
                (skill / "SKILL.md").read_text(encoding="utf-8")
                + "\n[Нет файла](references/missing.md)\n",
            )
            _write(
                skill / "references" / "leak.md",
                "api_key = 'synthetic-live-value-123456789012345'\n",
            )

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-test",),
                profile="runtime",
            )

            codes = _codes(report)
            self.assertEqual(report["status"], "fail")
            self.assertIn("BROKEN_MARKDOWN_LINK", codes)
            self.assertIn("POTENTIAL_SECRET", codes)
            self.assertNotIn("BEHAVIORAL_EVALS_MISSING", codes)
            self.assertNotIn("TRIGGER_EVALS_MISSING", codes)

    def test_both_profiles_reject_runtime_local_coordinates(self) -> None:
        cases = (
            (
                Path("references/local-coordinate.md"),
                "Открой <project-root>/private/source.pdf\n",
            ),
            (
                Path("references/repository-coordinate.md"),
                "Открой ТЗ/private/source.pdf\n",
            ),
            (
                Path("references/local-coordinate.json"),
                '{"path":"\\u0422\\u0417/private/source.pdf"}\n',
            ),
            (
                Path("scripts/runtime-helper.py"),
                'SOURCE = "/Users/alice/Documents/private/source.pdf"\n',
            ),
            (
                Path("scripts/linux-runtime-helper.py"),
                'SOURCE = "/home/alice/work/private/source.pdf"\n',
            ),
            (
                Path("scripts/root-runtime-helper.py"),
                'SOURCE = "/root/work/private/source.pdf"\n',
            ),
            (
                Path("scripts/windows-runtime-helper.py"),
                'SOURCE = r"C:\\Users\\alice\\work\\private\\source.pdf"\n',
            ),
            (
                Path("scripts/unc-runtime-helper.py"),
                'SOURCE = r"\\\\server\\share\\Users\\alice\\work\\source.pdf"\n',
            ),
            (
                Path("scripts/lowercase-windows-runtime-helper.py"),
                'SOURCE = r"c:\\users\\alice\\work\\source.pdf"\n',
            ),
            (
                Path("scripts/lowercase-unc-runtime-helper.py"),
                'SOURCE = r"\\\\server\\share\\users\\alice\\work\\source.pdf"\n',
            ),
            (
                Path("scripts/lowercase-macos-runtime-helper.py"),
                'SOURCE = "/users/alice/work/source.pdf"\n',
            ),
            (
                Path("scripts/unicode-macos-runtime-helper.py"),
                'SOURCE = "/Users/алиса/work/source.pdf"\n',
            ),
            (
                Path("scripts/unicode-linux-runtime-helper.py"),
                'SOURCE = "/home/пользователь/work/source.pdf"\n',
            ),
            (
                Path("scripts/unicode-windows-runtime-helper.py"),
                'SOURCE = r"C:\\Users\\Иван\\work\\source.pdf"\n',
            ),
            (
                Path("scripts/verify_offline_self_containment-copy.py"),
                'MARKER = "ТЗ/private"\n',
            ),
            (
                Path("scripts/backslash-coordinate.py"),
                'SOURCE = r"ТЗ\\private\\source.pdf"\n',
            ),
            (
                Path("scripts/mixed-slash-coordinate.py"),
                'SOURCE = r"ТЗ\\/private/source.pdf"\n',
            ),
            (
                Path("scripts/fullwidth-slash-coordinate.py"),
                'SOURCE = "ТЗ／private/source.pdf"\n',
            ),
            (
                Path("references/malformed-http-coordinate.md"),
                "https:/Users/alice/work/source.pdf\n",
            ),
            (
                Path("references/empty-host-coordinate.md"),
                "https:///ТЗ/private/source.pdf\n",
            ),
            (
                Path("references/file-url-coordinate.md"),
                "file:///Users/alice/work/source.pdf\n",
            ),
            (
                Path("references/bad-port-coordinate.md"),
                "https://example.org:bad/ТЗ/private/source.pdf\n",
            ),
            (
                Path("references/repeated-macos-separator.md"),
                "/Users//alice/private/source.pdf\n",
            ),
            (
                Path("references/repeated-linux-separator.md"),
                "/home//alice/private/source.pdf\n",
            ),
            (
                Path("references/repeated-windows-separator.md"),
                "C:/Users//alice/private/source.pdf\n",
            ),
            (
                Path("references/prefixed-http-coordinate.md"),
                "xhttps://example.org/ТЗ/private/source.pdf\n",
            ),
            (
                Path("references/compound-scheme-coordinate.md"),
                "ftphttps://example.org/Users/alice/private/source.pdf\n",
            ),
            (
                Path("references/javascript-scheme-coordinate.md"),
                "javascript:https://example.org/ТЗ/private/source.pdf\n",
            ),
            (
                Path("references/runtime.ini"),
                "source=/Users/alice/work/source.pdf\n",
            ),
            (
                Path("references/disguised.png"),
                "ТЗ/private/source.pdf\n",
            ),
            (
                Path("scripts/escaped-repository-route.js"),
                'const source = "ТЗ\\/private\\/source.pdf";\n',
            ),
            (
                Path("references/lowercase-repository-coordinate.md"),
                "тз/private/source.pdf\n",
            ),
            (
                Path("references/mixed-case-repository-coordinate.md"),
                "Тз/private/source.pdf\n",
            ),
            (
                Path("references/mixed-case-project-root.md"),
                "<Project-Root>/private/source.pdf\n",
            ),
            (
                Path("references/fullwidth-project-root.md"),
                "<PROJECT－ROOT>／private/source.pdf\n",
            ),
        )
        for profile in ("source", "runtime"):
            for relative, content in cases:
                with (
                    self.subTest(profile=profile, relative=relative),
                    tempfile.TemporaryDirectory() as tmp,
                ):
                    root = Path(tmp)
                    skill = _make_valid_skill(root)
                    if profile == "runtime":
                        for path in (skill / "evals").iterdir():
                            path.unlink()
                        (skill / "evals").rmdir()
                    _write(skill / relative, content)

                    report = VALIDATOR.validate_skillset(
                        root,
                        package_names=("ksrf-test",),
                        profile=profile,
                    )

                    self.assertIn("RUNTIME_LOCAL_COORDINATE", _codes(report))

    def test_runtime_coordinate_gate_allows_portable_runtime_routes(self) -> None:
        content = "\n".join(
            (
                "<skill-dir>/references/source.md",
                "$KSRF_SKILLS_ROOT/ksrf-complaint-cycle/references/source.md",
                "$HUDOC_ARCHIVE_ROOT/documents/source.pdf",
                "~/.codex/skills/ksrf-complaint-cycle/references/source.md",
                "/path/to/case-folder/source.pdf",
                "path/to/file.json",
                "/rooted/project/source.pdf",
                "/root@work/source.pdf",
                "/root+tmp/source.pdf",
                "/root:tmp/source.pdf",
                "https://example.org/Users/alice/work/source.pdf",
                "https://example.org/ТЗ/public/source.pdf",
                "https://[2001:db8::1]/Users/alice/work/source.pdf",
                "https://user@example.org/Users/alice/work/source.pdf",
                "(https://example.org/Users/alice/work/source.pdf)",
                'const u = "https:\\/\\/example.org\\/Users\\/alice\\/work.pdf";',
            )
        )
        for profile in ("source", "runtime"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                skill = _make_valid_skill(root)
                if profile == "runtime":
                    for path in (skill / "evals").iterdir():
                        path.unlink()
                    (skill / "evals").rmdir()
                _write(skill / "references" / "portable-routes.md", content)
                _write(
                    skill / "scripts" / "portable-routes.js",
                    'const u = "https:\\/\\/example.org\\/Users\\/alice\\/work.pdf";\n',
                )
                _write(
                    skill / "references" / "portable-routes.json",
                    (
                        "{\n"
                        '  "home": "https:\\/\\/example.org\\/Users\\/alice\\/work.pdf",\n'
                        '  "repository": "https:\\/\\/example.org\\/ТЗ\\/public.pdf"\n'
                        "}\n"
                    ),
                )

                report = VALIDATOR.validate_skillset(
                    root,
                    package_names=("ksrf-test",),
                    profile=profile,
                )

                self.assertNotIn("RUNTIME_LOCAL_COORDINATE", _codes(report))
                self.assertNotIn("ABSOLUTE_RUNTIME_PATH", _codes(report))
                self.assertEqual(
                    report["validation_coverage"]["runtime_self_containment"],
                    "validated",
                )

    def test_runtime_coordinate_gate_allows_declared_non_text_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            (skill / "references" / "image.png").write_bytes(
                b"\x89PNG\r\n\x1a\n\xff"
            )

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-test",),
                profile="source",
            )

            self.assertNotIn("RUNTIME_LOCAL_COORDINATE", _codes(report))
            self.assertNotIn("RUNTIME_FORMAT_UNCHECKED", _codes(report))

    def test_runtime_coordinate_gate_rejects_duplicate_or_invalid_runtime_json(
        self,
    ) -> None:
        cases = (
            '{"path":"\\u0422\\u0417/private","path":"safe"}\n',
            '{"path": ',
            '{"value":NaN}\n',
            '{"value":Infinity}\n',
            '{"value":-Infinity}\n',
        )
        for content in cases:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                skill = _make_valid_skill(root)
                _write(skill / "references" / "runtime.json", content)

                report = VALIDATOR.validate_skillset(
                    root,
                    package_names=("ksrf-test",),
                    profile="source",
                )

                self.assertIn("RUNTIME_REFERENCE_JSON_INVALID", _codes(report))

    def test_runtime_coordinate_gate_reports_json_recursion_without_crashing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(skill / "references" / "runtime.json", "{}\n")

            with mock.patch.object(
                VALIDATOR,
                "parse_runtime_json_strict",
                side_effect=RecursionError("nested JSON"),
            ):
                report = VALIDATOR.validate_skillset(
                    root,
                    package_names=("ksrf-test",),
                    profile="source",
                )

            self.assertIn("RUNTIME_REFERENCE_JSON_INVALID", _codes(report))

    def test_runtime_coordinate_gate_fails_closed_on_unreadable_runtime_text(
        self,
    ) -> None:
        cases = (
            ("runtime.csv", "RUNTIME_TEXT_UNREADABLE"),
            ("runtime.bin", "RUNTIME_FORMAT_UNCHECKED"),
        )
        for filename, expected_code in cases:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                skill = _make_valid_skill(root)
                (skill / "references" / filename).write_bytes(b"\xff\xfe")

                report = VALIDATOR.validate_skillset(
                    root,
                    package_names=("ksrf-test",),
                    profile="source",
                )

                self.assertIn(expected_code, _codes(report))

    def test_runtime_coordinate_gate_skips_generated_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(
                skill / "__pycache__" / "ignored.md",
                "Служебный путь: ТЗ/private/source.pdf\n",
            )

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-test",),
                profile="source",
            )

            self.assertNotIn("RUNTIME_LOCAL_COORDINATE", _codes(report))

    def test_runtime_coordinate_gate_skips_only_exact_source_artifacts(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root, name="ksrf-argument-patterns")
            _write(
                skill / "references" / "complaint-methodology-sources.md",
                "Служебный источник: ТЗ/private/source.pdf\n",
            )

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-argument-patterns",),
            )

            self.assertNotIn("RUNTIME_LOCAL_COORDINATE", _codes(report))

        for policy_owner in (
            "validate_ksrf_skillset.py",
            "verify_offline_self_containment.py",
        ):
            for profile in ("source", "runtime"):
                with (
                    self.subTest(policy_owner=policy_owner, profile=profile),
                    tempfile.TemporaryDirectory() as tmp,
                ):
                    root = Path(tmp)
                    skill = _make_valid_skill(root, name="ksrf-complaint-cycle")
                    if profile == "runtime":
                        for path in (skill / "evals").iterdir():
                            path.unlink()
                        (skill / "evals").rmdir()
                    _write(
                        skill / "scripts" / policy_owner,
                        'OPERATIONAL_SOURCE = "ТЗ/private/source.pdf"\n',
                    )

                    report = VALIDATOR.validate_skillset(
                        root,
                        package_names=("ksrf-complaint-cycle",),
                        profile=profile,
                    )

                    self.assertIn("RUNTIME_LOCAL_COORDINATE", _codes(report))

    def test_source_profile_still_security_scans_excluded_evals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(skill / "evals" / ".env", "API_TOKEN=real-secret-value-1234567890\n")
            _write(
                skill / "evals" / "local.json",
                '{"source": "/Users/alice/Documents/private-case/source.pdf"}\n',
            )
            _write(
                skill / "evals" / "leak.json",
                "api_key = 'synthetic-live-value-123456789012345'\n",
            )
            _write(
                skill / "evals" / "private.md",
                """В Конституционный Суд Российской Федерации

Заявитель: Иванов Иван Иванович

ЖАЛОБА

ПРОШУ:
""",
            )

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            codes = _codes(report)
            paths = [item["path"] for item in report["publish_manifest"]["files"]]
            self.assertEqual(report["status"], "fail")
            self.assertIn("FORBIDDEN_SECRET_FILE", codes)
            self.assertIn("ABSOLUTE_RUNTIME_PATH", codes)
            self.assertIn("POTENTIAL_SECRET", codes)
            self.assertIn("FORBIDDEN_PUBLIC_SOURCE_ARTIFACT", codes)
            self.assertEqual(
                report["validation_coverage"]["public_source_safety"],
                "validated",
            )
            self.assertEqual(
                report["validation_coverage"]["public_repository_safety"],
                "not_checked",
            )
            self.assertFalse(any("/evals/" in path for path in paths))

    def test_source_profile_excludes_and_scans_exact_maintainer_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_valid_skill(root, name="ksrf-argument-patterns")
            _make_valid_skill(root, name="ksrf-complaint-cycle")
            for package, relative in EXACT_MAINTAINER_FILES:
                _write(root / package / relative, "maintainer only\n")
            _write(
                root
                / "ksrf-argument-patterns"
                / "references"
                / "language_formulas.json",
                "api_key = 'synthetic-live-value-123456789012345'\n",
            )
            _write(
                root
                / "ksrf-argument-patterns"
                / "references"
                / "evidence_maps.json",
                """В Конституционный Суд Российской Федерации

Заявитель: Иванов Иван Иванович

ЖАЛОБА

ПРОШУ:
""",
            )
            _write(
                root
                / "ksrf-argument-patterns"
                / "references"
                / "hearing_argument_techniques.json",
                '{"source": "/Users/example/Documents/private/hearing-notes.json"}\n',
            )
            _write(
                root
                / "ksrf-argument-patterns"
                / "references"
                / "complaint-methodology-sources.md",
                "api_key = 'synthetic-live-value-123456789012345'\n",
            )
            symlink_path = (
                root
                / "ksrf-argument-patterns"
                / "references"
                / "argument_techniques_from_decisions.json"
            )
            symlink_path.unlink()
            symlink_target = symlink_path.parent / "maintainer-source.json"
            _write(symlink_target, "{}\n")
            symlink_path.symlink_to(symlink_target.name)
            _write(
                root
                / "ksrf-argument-patterns"
                / "references"
                / "constitutional_graph.json",
                "{}\n",
            )
            _write(
                root
                / "ksrf-argument-patterns"
                / "references"
                / "evidence_maps-guide.json",
                "{}\n",
            )

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-argument-patterns", "ksrf-complaint-cycle"),
            )

            paths = {item["path"] for item in report["publish_manifest"]["files"]}
            for package, relative in EXACT_MAINTAINER_FILES:
                self.assertNotIn(f"{package}/{relative.as_posix()}", paths)
            self.assertIn(
                "ksrf-argument-patterns/references/constitutional_graph.json",
                paths,
            )
            self.assertIn(
                "ksrf-argument-patterns/references/evidence_maps-guide.json",
                paths,
            )
            self.assertIn("POTENTIAL_SECRET", _codes(report))
            self.assertIn("ABSOLUTE_RUNTIME_PATH", _codes(report))
            self.assertIn("SYMLINK_NOT_PUBLISHABLE", _codes(report))
            self.assertIn("FORBIDDEN_PUBLIC_SOURCE_ARTIFACT", _codes(report))

    def test_source_profile_scans_exact_provenance_journal(self) -> None:
        samples = {
            "benign": ("# Provenance\n", None),
            "secret": (
                "api_key = 'synthetic-live-value-123456789012345'\n",
                "POTENTIAL_SECRET",
            ),
            "local_path": (
                '{"source": "/Users/example/Documents/private/source.pdf"}\n',
                "ABSOLUTE_RUNTIME_PATH",
            ),
            "complaint": (
                """В Конституционный Суд Российской Федерации

Заявитель: Иванов Иван Иванович

ЖАЛОБА

ПРОШУ:
""",
                "FORBIDDEN_PUBLIC_SOURCE_ARTIFACT",
            ),
        }
        relative = Path("references/complaint-methodology-sources.md")
        for label, (content, expected_code) in samples.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    skill = _make_valid_skill(root, name="ksrf-argument-patterns")
                    _write(skill / relative, content)

                    report = VALIDATOR.validate_skillset(
                        root,
                        package_names=("ksrf-argument-patterns",),
                    )

                    paths = {
                        item["path"] for item in report["publish_manifest"]["files"]
                    }
                    self.assertNotIn(
                        f"ksrf-argument-patterns/{relative.as_posix()}",
                        paths,
                    )
                    if expected_code is not None:
                        self.assertIn(expected_code, _codes(report))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root, name="ksrf-argument-patterns")
            journal = skill / relative
            target = journal.parent / "provenance-source.md"
            _write(target, "# Tracked source\n")
            journal.symlink_to(target.name)

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-argument-patterns",),
            )

            self.assertIn("SYMLINK_NOT_PUBLISHABLE", _codes(report))

    def test_source_profile_scans_exact_automation_backlog(self) -> None:
        samples = {
            "benign": ("# Maintainer backlog\n", None),
            "secret": (
                "api_key = 'synthetic-live-value-123456789012345'\n",
                "POTENTIAL_SECRET",
            ),
            "local_path": (
                '{"source": "/Users/example/Documents/private/backlog.md"}\n',
                "ABSOLUTE_RUNTIME_PATH",
            ),
            "complaint": (
                """В Конституционный Суд Российской Федерации

Заявитель: Иванов Иван Иванович

ЖАЛОБА

ПРОШУ:
""",
                "FORBIDDEN_PUBLIC_SOURCE_ARTIFACT",
            ),
        }
        relative = Path("references/automation-backlog.md")
        for label, (content, expected_code) in samples.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    skill = _make_valid_skill(root, name="ksrf-argument-patterns")
                    _write(skill / relative, content)

                    report = VALIDATOR.validate_skillset(
                        root,
                        package_names=("ksrf-argument-patterns",),
                    )

                    paths = {
                        item["path"] for item in report["publish_manifest"]["files"]
                    }
                    self.assertNotIn(
                        f"ksrf-argument-patterns/{relative.as_posix()}",
                        paths,
                    )
                    if expected_code is not None:
                        self.assertIn(expected_code, _codes(report))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root, name="ksrf-argument-patterns")
            backlog = skill / relative
            target = backlog.parent / "maintainer-backlog.md"
            _write(target, "# Tracked source\n")
            backlog.symlink_to(target.name)

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-argument-patterns",),
            )

            self.assertIn("SYMLINK_NOT_PUBLISHABLE", _codes(report))

    def test_runtime_profile_rejects_exact_maintainer_file_without_overmatching(self) -> None:
        for package, relative in EXACT_MAINTAINER_FILES:
            with self.subTest(package=package, relative=relative.as_posix()):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    skill = _make_valid_skill(root, name=package)
                    (skill / "evals" / "evals.json").unlink()
                    (skill / "evals" / "trigger-evals.json").unlink()
                    (skill / "evals").rmdir()
                    _write(skill / relative, "maintainer only\n")

                    report = VALIDATOR.validate_skillset(
                        root,
                        package_names=(package,),
                        profile="runtime",
                    )

                    self.assertIn("SOURCE_ONLY_ARTIFACT_PRESENT", _codes(report))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root, name="ksrf-argument-patterns")
            (skill / "evals" / "evals.json").unlink()
            (skill / "evals" / "trigger-evals.json").unlink()
            (skill / "evals").rmdir()
            _write(skill / "references" / "evidence_maps-guide.json", "{}\n")
            _write(
                skill / "references" / "constitutional_graph.json",
                '{"nodes": [], "edges": []}\n',
            )
            _write(
                skill / "references" / "complaint-methodology-sources-runtime.md",
                "# Runtime guide\n",
            )
            _write(
                skill / "references" / "automation-backlog-runtime.md",
                "# Runtime guide\n",
            )

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-argument-patterns",),
                profile="runtime",
            )

            self.assertEqual(report["status"], "pass")
            self.assertNotIn("SOURCE_ONLY_ARTIFACT_PRESENT", _codes(report))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root, name="ksrf-case-triage")
            (skill / "evals" / "evals.json").unlink()
            (skill / "evals" / "trigger-evals.json").unlink()
            (skill / "evals").rmdir()
            _write(
                skill / "references" / "complaint-methodology-sources.md",
                "# Same basename in another package\n",
            )
            _write(
                skill / "references" / "automation-backlog.md",
                "# Same basename in another package\n",
            )

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-case-triage",),
                profile="runtime",
            )

            self.assertEqual(report["status"], "pass")
            self.assertNotIn("SOURCE_ONLY_ARTIFACT_PRESENT", _codes(report))

    def test_source_profile_rejects_benign_root_only_skill_duplicate(self) -> None:
        for relative in (
            Path("scripts/build_constitutionalist_authority_corpus.py"),
            Path("scripts/enrich_ksrf_argument_patterns.py"),
            Path("scripts/extract_ksrf_argument_patterns.py"),
        ):
            with self.subTest(relative=relative.as_posix()):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    skill = _make_valid_skill(root, name="ksrf-argument-patterns")
                    _write(skill / relative, "# benign duplicate\n")

                    report = VALIDATOR.validate_skillset(
                        root,
                        package_names=("ksrf-argument-patterns",),
                        profile="source",
                    )

                    self.assertIn("ROOT_ONLY_DUPLICATE_PRESENT", _codes(report))

    def test_source_profile_discloses_unavailable_public_source_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_valid_skill(root)

            with mock.patch.object(
                VALIDATOR,
                "PUBLIC_SOURCE_CONTRACT_PATH",
                root / "missing-public-source-contract.py",
            ):
                report = VALIDATOR.validate_skillset(
                    root,
                    package_names=("ksrf-test",),
                )

            self.assertEqual(
                report["validation_coverage"]["public_source_safety"],
                "not_checked",
            )
            self.assertEqual(
                report["validation_coverage"]["public_repository_safety"],
                "not_checked",
            )
            self.assertFalse(report["source_release_eligible"])
            self.assertIn("PUBLIC_SOURCE_SAFETY_NOT_CHECKED", _codes(report))

    def test_unknown_validation_profile_is_rejected_by_python_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_valid_skill(root)

            with self.assertRaisesRegex(ValueError, "validation profile"):
                VALIDATOR.validate_skillset(
                    root,
                    package_names=("ksrf-test",),
                    profile="unknown",
                )

    def test_runtime_cli_refuses_standalone_publish_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            (skill / "evals" / "evals.json").unlink()
            (skill / "evals" / "trigger-evals.json").unlink()
            (skill / "evals").rmdir()
            manifest_out = root / "runtime-manifest.json"
            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = VALIDATOR.main(
                [
                    "--skills-root",
                    str(root),
                    "--package",
                    "ksrf-test",
                    "--profile",
                    "runtime",
                    "--manifest-out",
                    str(manifest_out),
                ],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 2)
            self.assertFalse(manifest_out.exists())
            self.assertIn("runtime", stderr.getvalue().lower())

    def test_agent_metadata_must_reference_exact_skill_and_mcp_names_are_qualified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(
                skill / "agents" / "openai.yaml",
                """interface:
  display_name: "Несинхронный агент"
  short_description: "Проверка"
  default_prompt: "Используй $wrong-skill."
tools:
  - casuslegal_search_practice
""",
            )
            _write(
                skill / "references" / "mcp.md",
                """# Маршрутизация MCP

## MCP-инструменты

- сначала используй `casuslegal_find_term`;
- затем используй `mcp__casuslegal__get_case_details`.
""",
            )

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            codes = _codes(report)
            self.assertIn("AGENT_SKILL_REFERENCE_MISMATCH", codes)
            self.assertIn("MCP_TOOL_NOT_FULLY_QUALIFIED", codes)

    def test_secrets_and_absolute_runtime_paths_never_enter_publish_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(skill / ".env", "API_TOKEN=real-secret-value-1234567890\n")
            _write(
                skill / "references" / "local.md",
                "Локальный источник: /Users/alice/Documents/private-case/source.pdf\n",
            )
            _write(
                skill / "references" / "leak.md",
                "api_key = 'synthetic-live-value-123456789012345'\n",
            )

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            codes = _codes(report)
            paths = [item["path"] for item in report["publish_manifest"]["files"]]
            self.assertEqual(report["status"], "fail")
            self.assertIn("FORBIDDEN_SECRET_FILE", codes)
            self.assertIn("ABSOLUTE_RUNTIME_PATH", codes)
            self.assertIn("POTENTIAL_SECRET", codes)
            self.assertNotIn("ksrf-test/.env", paths)
            self.assertNotIn("ksrf-test/references/local.md", paths)
            self.assertNotIn("ksrf-test/references/leak.md", paths)

    def test_skill_and_sko_identifiers_are_not_mistaken_for_openai_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(
                skill / "references" / "ordinary-identifiers.md",
                """# Обычные идентификаторы

`skill_reference`: `sko-complaint-methods-2017-2026.md`.
`skill_reference`: `science-support-pack.md`.
""",
            )

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            self.assertNotIn("POTENTIAL_SECRET", _codes(report))

    def test_missing_expected_package_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = VALIDATOR.validate_skillset(
                Path(tmp), package_names=("ksrf-missing",)
            )

            self.assertEqual(report["status"], "fail")
            self.assertIn("PACKAGE_MISSING", _codes(report))

    def test_argument_graph_contract_accepts_only_non_capability_lookalikes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "ksrf-argument-patterns"
            _write(
                skill / "references" / "constitutional_graph.json",
                json.dumps(
                    {
                        "nodes": [
                            {
                                "id": "toolkit:manual",
                                "kind": "automation_hook_note",
                                "label": "Описание ручной проверки",
                            }
                        ],
                        "edges": [
                            {
                                "from": "toolkit:manual",
                                "to": "toolkit:manual",
                                "type": "supported_by_note",
                            }
                        ],
                    }
                ),
            )
            findings: list[dict[str, object]] = []
            checker = getattr(VALIDATOR, "_validate_argument_graph_contract", None)

            self.assertTrue(
                callable(checker),
                "validator must expose the runtime argument-graph contract checker",
            )
            assert callable(checker)
            checker(findings, skill, root)

            self.assertEqual(findings, [])

    def test_argument_graph_contract_rejects_unshipped_tool_projection(self) -> None:
        samples = {
            "kind": {
                "nodes": [
                    {"id": "note:manual", "kind": "automation_hook", "label": "x"}
                ],
                "edges": [],
            },
            "node_id": {
                "nodes": [{"id": "tool:missing", "kind": "note", "label": "x"}],
                "edges": [],
            },
            "edge_type": {
                "nodes": [
                    {"id": "pattern:x", "kind": "pattern", "label": "x"},
                    {"id": "note:x", "kind": "note", "label": "x"},
                ],
                "edges": [
                    {"from": "pattern:x", "to": "note:x", "type": "supported_by"}
                ],
            },
            "edge_endpoint": {
                "nodes": [
                    {"id": "pattern:x", "kind": "pattern", "label": "x"},
                    {"id": "tool:missing", "kind": "note", "label": "x"},
                ],
                "edges": [
                    {"from": "pattern:x", "to": "tool:missing", "type": "note"}
                ],
            },
        }
        for label, graph in samples.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    skill = root / "ksrf-argument-patterns"
                    _write(
                        skill / "references" / "constitutional_graph.json",
                        json.dumps(graph),
                    )
                    findings: list[dict[str, object]] = []

                    VALIDATOR._validate_argument_graph_contract(findings, skill, root)

                    self.assertEqual(len(findings), 1)
                    self.assertEqual(
                        findings[0]["code"],
                        "UNSHIPPED_AUTOMATION_IN_RUNTIME_GRAPH",
                    )

    def test_argument_graph_contract_rejects_malformed_structure(self) -> None:
        valid_node = {"id": "pattern:x", "kind": "pattern", "label": "x"}
        samples = {
            "empty_node": {"nodes": [{}], "edges": []},
            "non_string_node_id": {
                "nodes": [{"id": 7, "kind": "pattern"}],
                "edges": [],
            },
            "blank_node_kind": {
                "nodes": [{"id": "pattern:x", "kind": ""}],
                "edges": [],
            },
            "duplicate_node_id": {
                "nodes": [valid_node, valid_node],
                "edges": [],
            },
            "empty_edge": {"nodes": [valid_node], "edges": [{}]},
            "non_string_edge_type": {
                "nodes": [valid_node],
                "edges": [
                    {"from": "pattern:x", "to": "pattern:x", "type": 7}
                ],
            },
            "dangling_edge": {
                "nodes": [valid_node],
                "edges": [
                    {
                        "from": "pattern:x",
                        "to": "pattern:missing",
                        "type": "may_trigger",
                    }
                ],
            },
        }
        for label, graph in samples.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    skill = root / "ksrf-argument-patterns"
                    _write(
                        skill / "references" / "constitutional_graph.json",
                        json.dumps(graph),
                    )
                    findings: list[dict[str, object]] = []

                    VALIDATOR._validate_argument_graph_contract(findings, skill, root)

                    self.assertEqual(len(findings), 1)
                    self.assertEqual(
                        findings[0]["code"],
                        "ARGUMENT_GRAPH_CONTRACT_INVALID",
                    )

    def test_validate_skillset_enforces_argument_graph_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root, name="ksrf-argument-patterns")
            _write(
                skill / "references" / "constitutional_graph.json",
                json.dumps(
                    {
                        "nodes": [
                            {"id": "tool:missing", "kind": "automation_hook"}
                        ],
                        "edges": [],
                    }
                ),
            )

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-argument-patterns",),
            )

            self.assertIn(
                "UNSHIPPED_AUTOMATION_IN_RUNTIME_GRAPH",
                _codes(report),
            )

    def test_application_evidence_contract_helper_accepts_exact_ordered_enum(
        self,
    ) -> None:
        expected = [
            "raised_and_reviewed",
            "raised_but_not_addressed",
            "not_raised",
            "record_missing",
            "unclear",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "ksrf-complaint-cycle"
            _write(
                skill
                / "schemas"
                / "ksrf_filing"
                / "application-evidence.schema.json",
                json.dumps(
                    {
                        "properties": {
                            "preservation_exhaustion": {"enum": expected}
                        }
                    }
                ),
            )
            _write(
                skill / "references" / "implicit-application-gate.md",
                "# Gate\n\n"
                "### `preservation_exhaustion`\n\n"
                + "".join(f"- `{value}`;\n" for value in expected)
                + "\n### Следующий раздел\n",
            )
            findings: list[dict[str, object]] = []
            checker = getattr(
                VALIDATOR, "_validate_application_evidence_contract", None
            )

            self.assertTrue(
                callable(checker),
                "validator must expose the application-evidence contract checker",
            )
            assert callable(checker)
            checker(findings, skill, root)

            self.assertEqual(findings, [])

    def test_validate_skillset_reports_preservation_enum_drift(self) -> None:
        expected = [
            "raised_and_reviewed",
            "raised_but_not_addressed",
            "not_raised",
            "record_missing",
            "unclear",
        ]
        actual = [
            "raised_and_reviewed",
            "raised_not_addressed",
            "not_raised",
            "record_missing",
            "unclear",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root, name="ksrf-complaint-cycle")
            _write(
                skill
                / "schemas"
                / "ksrf_filing"
                / "application-evidence.schema.json",
                json.dumps(
                    {
                        "properties": {
                            "preservation_exhaustion": {"enum": expected}
                        }
                    }
                ),
            )
            _write(
                skill / "references" / "implicit-application-gate.md",
                "# Gate\n\n"
                "### `preservation_exhaustion`\n\n"
                + "".join(f"- `{value}`;\n" for value in actual)
                + "\n### Следующий раздел\n",
            )

            report = VALIDATOR.validate_skillset(
                root, package_names=("ksrf-complaint-cycle",)
            )
            drift_findings = [
                item
                for item in report["findings"]
                if isinstance(item, dict)
                and item.get("code") == "APPLICATION_EVIDENCE_ENUM_DRIFT"
            ]

            self.assertEqual(report["status"], "fail")
            self.assertEqual(len(drift_findings), 1)
            self.assertEqual(drift_findings[0]["severity"], "error")
            self.assertEqual(
                drift_findings[0]["evidence"],
                {"expected": expected, "actual": actual},
            )

    def test_application_evidence_contract_rejects_extra_backtick_token(
        self,
    ) -> None:
        expected = [
            "raised_and_reviewed",
            "raised_but_not_addressed",
            "not_raised",
            "record_missing",
            "unclear",
        ]
        actual = [
            "raised_and_reviewed",
            "invented_authority_expansion",
            "raised_but_not_addressed",
            "not_raised",
            "record_missing",
            "unclear",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "ksrf-complaint-cycle"
            _write(
                skill
                / "schemas"
                / "ksrf_filing"
                / "application-evidence.schema.json",
                json.dumps(
                    {
                        "properties": {
                            "preservation_exhaustion": {"enum": expected}
                        }
                    }
                ),
            )
            _write(
                skill / "references" / "implicit-application-gate.md",
                "# Gate\n\n"
                "### `preservation_exhaustion`\n\n"
                "- `raised_and_reviewed` (alias `invented_authority_expansion`);\n"
                + "".join(f"- `{value}`;\n" for value in expected[1:])
                + "\n### Следующий раздел\n",
            )
            findings: list[dict[str, object]] = []

            VALIDATOR._validate_application_evidence_contract(findings, skill, root)

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["code"], "APPLICATION_EVIDENCE_ENUM_DRIFT")
            self.assertEqual(
                findings[0]["evidence"],
                {"expected": expected, "actual": actual},
            )

    def test_authority_corpus_contract_accepts_clean_schema_two_payload(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "ksrf-argument-patterns"
            _write(
                skill / "references" / "constitutionalist-authority-corpus.json",
                json.dumps(_minimal_authority_corpus(), ensure_ascii=False),
            )
            findings: list[dict[str, object]] = []
            checker = getattr(VALIDATOR, "_validate_authority_corpus_contract", None)

            self.assertTrue(callable(checker))
            assert callable(checker)
            checker(
                findings,
                skill,
                root,
                expected_semantic_sha256=_semantic_digest(
                    _minimal_authority_corpus()
                ),
            )

            self.assertEqual(findings, [])

    def test_authority_corpus_contract_accepts_full_text_without_method_card(
        self,
    ) -> None:
        payload = _minimal_authority_corpus()
        authority = payload["authorities"][0]
        full_text_title = "Проверенный полный текст"
        authority.update(
            {
                "status": "full_text_available",
                "status_label": payload["status_legend"]["full_text_available"],
                "needs_identity_or_method_review": False,
                "source_counts": {
                    "sko_index": 1,
                    "curated_method": 1,
                    "local_full_text": 1,
                },
                "full_text_sources": [full_text_title],
                "method_cards": [],
                "works": [
                    *authority["works"],
                    {
                        "source": "curated_method",
                        "title": full_text_title,
                    },
                ],
            }
        )
        payload["summary"] = {
            **payload["summary"],
            "status_counts": {"full_text_available": 1},
            "source_people_counts": {
                "sko_index": 1,
                "curated_method": 1,
                "local_full_text": 1,
            },
            "works_total": 2,
            "needs_review_total": 0,
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "ksrf-argument-patterns"
            _write(
                skill / "references" / "constitutionalist-authority-corpus.json",
                json.dumps(payload, ensure_ascii=False),
            )
            findings: list[dict[str, object]] = []

            VALIDATOR._validate_authority_corpus_contract(
                findings,
                skill,
                root,
                expected_semantic_sha256=_semantic_digest(payload),
            )

            self.assertEqual(findings, [])

    def test_authority_corpus_rejects_unresolvable_method_reference(self) -> None:
        payload = _minimal_authority_corpus()
        authority = payload["authorities"][0]
        full_text_title = "Проверенный полный текст"
        authority.update(
            {
                "status": "method_integrated",
                "status_label": payload["status_legend"]["method_integrated"],
                "method_integrated": True,
                "needs_identity_or_method_review": False,
                "source_counts": {
                    "sko_index": 1,
                    "curated_method": 1,
                    "local_full_text": 1,
                },
                "full_text_sources": [full_text_title],
                "method_cards": [
                    {
                        "method": "Проверять связь метода с источником",
                        "usable_for": "контроль методической карточки",
                        "guardrail": "Не использовать без доступного справочника",
                        "skill_reference": "missing-reference.md",
                    }
                ],
                "works": [
                    *authority["works"],
                    {
                        "source": "curated_method",
                        "title": full_text_title,
                    },
                ],
            }
        )
        payload["summary"] = {
            **payload["summary"],
            "status_counts": {"method_integrated": 1},
            "source_people_counts": {
                "sko_index": 1,
                "curated_method": 1,
                "local_full_text": 1,
            },
            "works_total": 2,
            "needs_review_total": 0,
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "ksrf-argument-patterns"
            _write(
                skill / "references" / "constitutionalist-authority-corpus.json",
                json.dumps(payload, ensure_ascii=False),
            )
            findings: list[dict[str, object]] = []

            VALIDATOR._validate_authority_corpus_contract(
                findings,
                skill,
                root,
                expected_semantic_sha256=_semantic_digest(payload),
            )

            self.assertEqual(
                [item["code"] for item in findings],
                ["AUTHORITY_CORPUS_CONTRACT_INVALID"],
            )

    def test_authority_corpus_rejects_duplicate_json_key_with_hidden_coordinate(
        self,
    ) -> None:
        payload_text = json.dumps(
            _minimal_authority_corpus(),
            ensure_ascii=False,
        )
        payload_text = payload_text.replace(
            '"coverage": "тестовый охват библиографии"',
            '"coverage": "ТЗ/private/hidden.pdf", '
            '"coverage": "тестовый охват библиографии"',
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "ksrf-argument-patterns"
            _write(
                skill / "references" / "constitutionalist-authority-corpus.json",
                payload_text,
            )
            findings: list[dict[str, object]] = []

            VALIDATOR._validate_authority_corpus_contract(
                findings,
                skill,
                root,
                expected_semantic_sha256=_semantic_digest(
                    _minimal_authority_corpus()
                ),
            )

            self.assertEqual(
                [item["code"] for item in findings],
                ["AUTHORITY_CORPUS_MAINTAINER_METADATA_PRESENT"],
            )

    def test_json_loader_rejects_duplicate_object_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            _write(path, '{"status": "candidate", "status": "approved"}')

            with self.assertRaisesRegex(ValueError, "duplicate key: status"):
                VALIDATOR._read_json(path)

    def test_authority_corpus_contract_rejects_malformed_and_maintainer_data(
        self,
    ) -> None:
        cases = (
            (
                "old schema",
                {**_minimal_authority_corpus(), "schema_version": "1.0"},
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "missing sources",
                {key: value for key, value in _minimal_authority_corpus().items() if key != "sources"},
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "missing warning boundary",
                {
                    key: value
                    for key, value in _minimal_authority_corpus().items()
                    if key != "warning"
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "unknown promoted status",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "status": "PROMOTED_WITHOUT_REVIEW",
                        }
                    ],
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "known promotion without method card",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "status": "method_integrated",
                            "status_label": _minimal_authority_corpus()[
                                "status_legend"
                            ]["method_integrated"],
                            "method_integrated": True,
                        }
                    ],
                    "summary": {
                        **_minimal_authority_corpus()["summary"],
                        "status_counts": {"method_integrated": 1},
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "fake full-text promotion",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "status": "full_text_available",
                            "status_label": _minimal_authority_corpus()[
                                "status_legend"
                            ]["full_text_available"],
                            "needs_identity_or_method_review": False,
                            "source_counts": {
                                "sko_index": 1,
                                "local_full_text": 1,
                            },
                            "full_text_sources": [
                                "Несуществующий локальный полный текст"
                            ],
                        }
                    ],
                    "summary": {
                        **_minimal_authority_corpus()["summary"],
                        "status_counts": {"full_text_available": 1},
                        "source_people_counts": {
                            "sko_index": 1,
                            "local_full_text": 1,
                        },
                        "needs_review_total": 0,
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "fake method-card promotion",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "status": "method_integrated",
                            "status_label": _minimal_authority_corpus()[
                                "status_legend"
                            ]["method_integrated"],
                            "method_integrated": True,
                            "needs_identity_or_method_review": False,
                            "source_counts": {
                                "sko_index": 1,
                                "curated_method": 1,
                                "local_full_text": 1,
                            },
                            "full_text_sources": ["Поддельный полный текст"],
                            "method_cards": [
                                {
                                    "method": "Поддельное повышение",
                                    "usable_for": "автоматическое включение",
                                    "guardrail": "Проверка не нужна",
                                    "skill_reference": "missing-reference.md",
                                }
                            ],
                        }
                    ],
                    "summary": {
                        **_minimal_authority_corpus()["summary"],
                        "status_counts": {"method_integrated": 1},
                        "source_people_counts": {
                            "sko_index": 1,
                            "curated_method": 1,
                            "local_full_text": 1,
                        },
                        "needs_review_total": 0,
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "suppressed identity review",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "needs_identity_or_method_review": False,
                        }
                    ],
                    "summary": {
                        **_minimal_authority_corpus()["summary"],
                        "needs_review_total": 0,
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "unknown source suppresses identity review",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "needs_identity_or_method_review": False,
                            "source_counts": {
                                "sko_index": 1,
                                "invented_authoritative_source": 1,
                            },
                        }
                    ],
                    "summary": {
                        **_minimal_authority_corpus()["summary"],
                        "source_people_counts": {
                            "sko_index": 1,
                            "invented_authoritative_source": 1,
                        },
                        "needs_review_total": 0,
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "duplicate canonical identity",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        _minimal_authority_corpus()["authorities"][0],
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "id": "authority-test-duplicate",
                        },
                    ],
                    "summary": {
                        **_minimal_authority_corpus()["summary"],
                        "authorities_total": 2,
                        "status_counts": {"academic_indexed": 2},
                        "source_people_counts": {"sko_index": 2},
                        "route_counts": {"admissibility_and_route": 2},
                        "works_total": 2,
                        "needs_review_total": 2,
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "inverted warning",
                {
                    **_minimal_authority_corpus(),
                    "warning": "Все записи можно цитировать без проверки.",
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "inverted status label",
                {
                    **_minimal_authority_corpus(),
                    "status_legend": {
                        **_minimal_authority_corpus()["status_legend"],
                        "discovery_only": "Проверенная позиция",
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "inverted route label",
                {
                    **_minimal_authority_corpus(),
                    "route_legend": {
                        **_minimal_authority_corpus()["route_legend"],
                        "admissibility_and_route": "Автоматически включить",
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "mismatched status label",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "status_label": "Другой статус",
                        }
                    ],
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "missing authority routes",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            key: value
                            for key, value in _minimal_authority_corpus()[
                                "authorities"
                            ][0].items()
                            if key != "routes"
                        }
                    ],
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "empty work provenance",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "works": [{}],
                        }
                    ],
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "non-object work",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "works": [17],
                        }
                    ],
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "private source url",
                {
                    **_minimal_authority_corpus(),
                    "sources": [
                        {
                            **_minimal_authority_corpus()["sources"][0],
                            "url": "file:///tmp/private.pdf",
                        }
                    ],
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "loopback source url",
                {
                    **_minimal_authority_corpus(),
                    "sources": [
                        {
                            **_minimal_authority_corpus()["sources"][0],
                            "url": "http://127.0.0.1/private.pdf",
                        }
                    ],
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "private work url",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "works": [
                                {
                                    **_minimal_authority_corpus()["authorities"][
                                        0
                                    ]["works"][0],
                                    "url": "file:///tmp/private.pdf",
                                }
                            ],
                        }
                    ],
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "undeclared work source",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "source_counts": {"unknown_private_source": 1},
                            "works": [
                                {
                                    **_minimal_authority_corpus()["authorities"][
                                        0
                                    ]["works"][0],
                                    "source": "unknown_private_source",
                                }
                            ],
                        }
                    ],
                    "summary": {
                        **_minimal_authority_corpus()["summary"],
                        "source_people_counts": {"unknown_private_source": 1},
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "duplicate authority route",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "routes": [
                                "admissibility_and_route",
                                "admissibility_and_route",
                            ],
                        }
                    ],
                    "summary": {
                        **_minimal_authority_corpus()["summary"],
                        "route_counts": {"admissibility_and_route": 2},
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "forged derived summary",
                {
                    **_minimal_authority_corpus(),
                    "summary": {
                        **_minimal_authority_corpus()["summary"],
                        "status_counts": {"discovery_only": 1},
                        "route_counts": {},
                        "source_people_counts": {"sko_index": 99},
                        "needs_review_total": 0,
                    },
                },
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
            ),
            (
                "retired queue",
                {**_minimal_authority_corpus(), "next_extraction_wave": []},
                "AUTHORITY_CORPUS_MAINTAINER_METADATA_PRESENT",
            ),
            (
                "nested retired queue",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "next_extraction_wave": [],
                        }
                    ],
                },
                "AUTHORITY_CORPUS_MAINTAINER_METADATA_PRESENT",
            ),
            (
                "local hint",
                {
                    **_minimal_authority_corpus(),
                    "sources": [
                        {
                            **_minimal_authority_corpus()["sources"][0],
                            "local_source_hint": "ТЗ/private/source.pdf",
                        }
                    ],
                },
                "AUTHORITY_CORPUS_MAINTAINER_METADATA_PRESENT",
            ),
            (
                "nested local hint without coordinate marker",
                {
                    **_minimal_authority_corpus(),
                    "authorities": [
                        {
                            **_minimal_authority_corpus()["authorities"][0],
                            "local_source_hint": "private/source.pdf",
                        }
                    ],
                },
                "AUTHORITY_CORPUS_MAINTAINER_METADATA_PRESENT",
            ),
            (
                "local coordinate",
                {
                    **_minimal_authority_corpus(),
                    "sources": [
                        {
                            **_minimal_authority_corpus()["sources"][0],
                            "coverage": "ТЗ/private/source.pdf",
                        }
                    ],
                },
                "AUTHORITY_CORPUS_MAINTAINER_METADATA_PRESENT",
            ),
        )
        for label, payload, expected_code in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                skill = root / "ksrf-argument-patterns"
                _write(
                    skill
                    / "references"
                    / "constitutionalist-authority-corpus.json",
                    json.dumps(payload, ensure_ascii=False),
                )
                findings: list[dict[str, object]] = []
                checker = getattr(
                    VALIDATOR,
                    "_validate_authority_corpus_contract",
                    None,
                )

                self.assertTrue(callable(checker))
                assert callable(checker)
                checker(
                    findings,
                    skill,
                    root,
                    expected_semantic_sha256=_semantic_digest(payload),
                )

                self.assertEqual([item["code"] for item in findings], [expected_code])

    def test_authority_corpus_rejects_non_public_url_forms(self) -> None:
        invalid_urls = (
            "http://127.1/private.pdf",
            "http://2130706433/private.pdf",
            "http://0x7f000001/private.pdf",
            "http://%31%32%37.0.0.1/private.pdf",
            "http://intranet/private.pdf",
            "https://source.internal/private.pdf",
            "https://source.local/private.pdf",
            "https://source.test/private.pdf",
            "https://bad_host.com/private.pdf",
            "https://bad..host.com/private.pdf",
            "https://-bad.example.com/private.pdf",
            "https://bad-.example.com/private.pdf",
            "https://.example.com/private.pdf",
            "https://example.onion/private.pdf",
            "https://router.home.arpa/private.pdf",
            "https://name.alt/private.pdf",
            "http://foo.ｌｏｃａｌｈｏｓｔ/private.pdf",
            "http://[v1.fe80]/private.pdf",
            "https://example.com /private.pdf",
            "http://example.com:abc/private.pdf",
            "http://example.com:99999/private.pdf",
        )
        for url in invalid_urls:
            with self.subTest(url=url), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                skill = root / "ksrf-argument-patterns"
                payload = {
                    **_minimal_authority_corpus(),
                    "sources": [
                        {
                            **_minimal_authority_corpus()["sources"][0],
                            "url": url,
                        },
                        *_minimal_authority_corpus()["sources"][1:],
                    ],
                }
                _write(
                    skill
                    / "references"
                    / "constitutionalist-authority-corpus.json",
                    json.dumps(payload, ensure_ascii=False),
                )
                findings: list[dict[str, object]] = []

                VALIDATOR._validate_authority_corpus_contract(
                    findings,
                    skill,
                    root,
                    expected_semantic_sha256=_semantic_digest(payload),
                )

                self.assertEqual(
                    [item["code"] for item in findings],
                    ["AUTHORITY_CORPUS_CONTRACT_INVALID"],
                )

    def test_authority_corpus_semantic_seal_rejects_structurally_valid_substitute(
        self,
    ) -> None:
        payload = _minimal_authority_corpus()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "ksrf-argument-patterns"
            _write(
                skill / "references" / "constitutionalist-authority-corpus.json",
                json.dumps(payload, ensure_ascii=False),
            )
            findings: list[dict[str, object]] = []

            VALIDATOR._validate_authority_corpus_contract(findings, skill, root)

            self.assertEqual(
                [item["code"] for item in findings],
                ["AUTHORITY_CORPUS_CONTRACT_INVALID"],
            )

    def test_both_profiles_enforce_authority_corpus_contract(self) -> None:
        for profile in ("source", "runtime"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                skill = _make_valid_skill(root, name="ksrf-argument-patterns")
                if profile == "runtime":
                    for path in (skill / "evals").iterdir():
                        path.unlink()
                    (skill / "evals").rmdir()
                payload = {
                    **_minimal_authority_corpus(),
                    "next_extraction_wave": [],
                }
                _write(
                    skill
                    / "references"
                    / "constitutionalist-authority-corpus.json",
                    json.dumps(payload, ensure_ascii=False),
                )

                report = VALIDATOR.validate_skillset(
                    root,
                    package_names=("ksrf-argument-patterns",),
                    profile=profile,
                )

                self.assertIn(
                    "AUTHORITY_CORPUS_MAINTAINER_METADATA_PRESENT",
                    _codes(report),
                )

    def test_both_profiles_reject_missing_authority_corpus(self) -> None:
        for profile in ("source", "runtime"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                skill = _make_valid_skill(root, name="ksrf-argument-patterns")
                (
                    skill
                    / "references"
                    / "constitutionalist-authority-corpus.json"
                ).unlink()
                if profile == "runtime":
                    for path in (skill / "evals").iterdir():
                        path.unlink()
                    (skill / "evals").rmdir()

                report = VALIDATOR.validate_skillset(
                    root,
                    package_names=("ksrf-argument-patterns",),
                    profile=profile,
                )

                self.assertIn(
                    "AUTHORITY_CORPUS_CONTRACT_INVALID",
                    _codes(report),
                )


if __name__ == "__main__":
    unittest.main()
