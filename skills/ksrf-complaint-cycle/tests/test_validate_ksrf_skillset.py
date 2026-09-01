from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
    return skill


EXACT_MAINTAINER_FILES = (
    ("ksrf-argument-patterns", Path("references/hearing_argument_techniques.json")),
    ("ksrf-argument-patterns", Path("references/language_formulas.json")),
    ("ksrf-argument-patterns", Path("references/evidence_maps.json")),
    (
        "ksrf-argument-patterns",
        Path("references/argument_techniques_from_decisions.json"),
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
            _write(skill / "references" / "constitutional_graph.json", "{}\n")

            report = VALIDATOR.validate_skillset(
                root,
                package_names=("ksrf-argument-patterns",),
                profile="runtime",
            )

            self.assertEqual(report["status"], "pass")
            self.assertNotIn("SOURCE_ONLY_ARTIFACT_PRESENT", _codes(report))

    def test_source_profile_rejects_benign_root_only_skill_duplicate(self) -> None:
        for relative in (
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


if __name__ == "__main__":
    unittest.main()
