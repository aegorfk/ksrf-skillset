from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "validate_ksrf_skillset.py"
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
        """---
name: ksrf-test
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
        """interface:
  display_name: "Тестовый KSRF skill"
  short_description: "Проверка упаковки тестового KSRF skill"
  default_prompt: "Используй $ksrf-test для проверки пакета."
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
    return skill


def _codes(report: dict[str, object]) -> set[str]:
    return {
        str(item["code"])
        for item in report["findings"]
        if isinstance(item, dict)
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

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            self.assertEqual(report["status"], "pass")
            paths = [item["path"] for item in report["publish_manifest"]["files"]]
            self.assertIn("ksrf-test/SKILL.md", paths)
            self.assertTrue(all(not Path(path).is_absolute() for path in paths))
            self.assertTrue(all(".." not in Path(path).parts for path in paths))
            self.assertTrue(all(".serena" not in path for path in paths))
            self.assertTrue(all("__pycache__" not in path for path in paths))
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

    def test_secret_shaped_token_in_env_example_never_enters_publish_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(skill / ".env.example", "GITHUB_TOKEN=ghp_" + ("A" * 24) + "\n")

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            secret_findings = [
                item for item in report["findings"] if item.get("code") == "POTENTIAL_SECRET"
            ]
            paths = [item["path"] for item in report["publish_manifest"]["files"]]
            self.assertEqual(report["status"], "fail")
            self.assertEqual(
                [(item.get("path"), item.get("line")) for item in secret_findings],
                [("ksrf-test/.env.example", 1)],
            )
            self.assertNotIn("ksrf-test/.env.example", paths)

    def test_safe_env_example_placeholder_remains_publishable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_valid_skill(root)
            _write(skill / ".env.example", "GITHUB_TOKEN=replace-with-your-value\n")

            report = VALIDATOR.validate_skillset(root, package_names=("ksrf-test",))

            paths = [item["path"] for item in report["publish_manifest"]["files"]]
            self.assertEqual(report["status"], "pass")
            self.assertNotIn("POTENTIAL_SECRET", _codes(report))
            self.assertIn("ksrf-test/.env.example", paths)

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


if __name__ == "__main__":
    unittest.main()
