from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
DOCTRINE_SOURCE = (
    REPO
    / "skills"
    / "ksrf-doctrine-research"
    / "scripts"
    / "doctrine_research.py"
)


def _load_doctrine_module():
    spec = importlib.util.spec_from_file_location(
        "doctrine_research_cli_help_contract",
        DOCTRINE_SOURCE,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Не удалось загрузить {DOCTRINE_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DOCTRINE = _load_doctrine_module()


class RuntimeCLIRussianHelpTests(unittest.TestCase):
    def test_documented_installed_help_routes_are_russian(self) -> None:
        doctrine_routes = (
            (
                (),
                (
                    "Спланировать и выполнить ограниченный поиск правовой доктрины.",
                    "команды:",
                    "КОМАНДА",
                    "route",
                    "plan",
                    "search",
                    "validate",
                    "rerank",
                ),
            ),
            (
                ("route",),
                (
                    "Выбрать безопасный режим исследования доктрины",
                    "--request",
                    "ФАЙЛ",
                    "Путь к JSON-файлу с параметрами исследования.",
                ),
            ),
            (
                ("plan",),
                (
                    "Создать воспроизводимый план поисковых запросов",
                    "--request",
                    "--workspace",
                    "--providers",
                    "ПАПКА",
                    "КАНАЛЫ",
                    "Путь к JSON-файлу с параметрами исследования.",
                    "по умолчанию ни один не выбран",
                ),
            ),
            (
                ("search",),
                (
                    "Выполнить поиск через выбранные каналы поиска.",
                    "--max-queries",
                    "--max-results",
                    "--timeout",
                    "--request-delay",
                    "--approved-query-plan-hash",
                    "ФАЙЛ",
                    "ПАПКА",
                    "КАНАЛЫ",
                    "ЧИСЛО",
                    "СЕКУНДЫ",
                    "ХЕШ",
                    "Путь к JSON-файлу с параметрами исследования.",
                    "Точное значение query_plan_hash",
                ),
            ),
            (
                ("validate",),
                (
                    "Проверить план или завершённую рабочую папку",
                    "--workspace",
                    "ПАПКА",
                ),
            ),
            (
                ("rerank",),
                (
                    "Повторно оценить найденные материалы по правовой теме",
                    "--request",
                    "--workspace",
                    "ФАЙЛ",
                    "ПАПКА",
                    "Путь к JSON-файлу с параметрами исследования.",
                ),
            ),
        )
        forbidden_english = (
            "usage:",
            "positional arguments:",
            "optional arguments:",
            "options:",
            "show this help message and exit",
            "Plan and run bounded legal-doctrine discovery.",
            "Validate a KSRF practice authority ledger JSON file.",
            "Path to authority ledger JSON",
            "Reject access/query tokens in URLs",
            "Require human approval and at least one drafting block",
            "REQUEST",
            "WORKSPACE",
            "PROVIDERS",
            "MAX_QUERIES",
            "MAX_RESULTS",
            "TIMEOUT",
            "REQUEST_DELAY",
            "APPROVED_QUERY_PLAN_HASH",
            "Select the safest doctrine-research mode before planning or search.",
            "Create deterministic query and provider-routing artifacts.",
            "Run selected documented API adapters.",
            (
                "Required for case_scoped and hypothesis_verification after "
                "human review of query-plan.json."
            ),
            "Validate a plan or completed bounded search workspace.",
            "Reapply the current legal-topic heuristic without network calls.",
        )

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            install = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(installed)],
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            doctrine = (
                installed
                / "ksrf-doctrine-research"
                / "scripts"
                / "doctrine_research.py"
            )
            for route, required in doctrine_routes:
                with self.subTest(cli="doctrine", route=route):
                    completed = subprocess.run(
                        [sys.executable, str(doctrine), *route, "--help"],
                        cwd=root,
                        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(completed.stderr, "")
                    self.assertIn("Использование:", completed.stdout)
                    self.assertIn("параметры:", completed.stdout)
                    self.assertIn("показать эту справку и выйти", completed.stdout)
                    normalized_stdout = " ".join(completed.stdout.split())
                    for anchor in required:
                        self.assertIn(" ".join(anchor.split()), normalized_stdout)
                    for forbidden in forbidden_english:
                        self.assertNotIn(
                            " ".join(forbidden.split()),
                            normalized_stdout,
                        )
                    self.assertNotIn("--offline-fixtures", completed.stdout)

            authority = (
                installed
                / "ksrf-practice-authority-builder"
                / "scripts"
                / "validate_authority_ledger.py"
            )
            completed = subprocess.run(
                [sys.executable, str(authority), "--help"],
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        normalized_stdout = " ".join(completed.stdout.split())
        for anchor in (
            "Использование:",
            "позиционные аргументы:",
            "параметры:",
            "ПУТЬ",
            "Проверить JSON-реестр источников судебной практики для жалобы в КС РФ.",
            "Путь к JSON-реестру источников судебной практики.",
            "Отклонять URL с токенами доступа",
            "Требовать одобрения человеком",
            "показать эту справку и выйти",
            "--public",
            "--require-drafting",
        ):
            self.assertIn(" ".join(anchor.split()), normalized_stdout)
        for forbidden in forbidden_english:
            self.assertNotIn(" ".join(forbidden.split()), normalized_stdout)

    def test_non_help_usage_and_errors_remain_unchanged(self) -> None:
        cases = (
            (
                DOCTRINE_SOURCE,
                (),
                (
                    (
                        "usage: doctrine_research.py [-h] "
                        "{route,plan,search,validate,rerank} ..."
                    ),
                    (
                        "doctrine_research.py: error: the following "
                        "arguments are required: command"
                    ),
                ),
            ),
            (
                DOCTRINE_SOURCE,
                ("search",),
                (
                    "usage: doctrine_research.py search",
                    "--request REQUEST",
                    "--workspace WORKSPACE",
                    "--offline-fixtures OFFLINE_FIXTURES",
                    (
                        "doctrine_research.py search: error: the following "
                        "arguments are required: --request, --workspace"
                    ),
                ),
            ),
            (
                REPO
                / "skills"
                / "ksrf-practice-authority-builder"
                / "scripts"
                / "validate_authority_ledger.py",
                (),
                (
                    "usage: validate_authority_ledger.py",
                    "[--require-drafting] path",
                    (
                        "validate_authority_ledger.py: error: the following "
                        "arguments are required: path"
                    ),
                ),
            ),
        )
        for script, arguments, required in cases:
            with self.subTest(script=script.name):
                completed = subprocess.run(
                    [sys.executable, str(script), *arguments],
                    cwd=REPO,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                normalized_stderr = " ".join(completed.stderr.split())
                for anchor in required:
                    self.assertIn(" ".join(anchor.split()), normalized_stderr)
                self.assertNotIn("Использование:", completed.stderr)

    def test_legacy_system_python_help_heading_is_russian(self) -> None:
        legacy_python = Path("/usr/bin/python3")
        if not legacy_python.is_file():
            self.skipTest("Системный Python не установлен")
        cases = (
            (DOCTRINE_SOURCE, ()),
            (DOCTRINE_SOURCE, ("search",)),
            (
                REPO
                / "skills"
                / "ksrf-practice-authority-builder"
                / "scripts"
                / "validate_authority_ledger.py",
                (),
            ),
        )
        for script, route in cases:
            with self.subTest(script=script.name, route=route):
                completed = subprocess.run(
                    [str(legacy_python), str(script), *route, "--help"],
                    cwd=REPO,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stderr, "")
                self.assertIn("Использование:", completed.stdout)
                self.assertIn("параметры:", completed.stdout)
                self.assertNotIn("optional arguments:", completed.stdout)
                self.assertNotIn("show this help message and exit", completed.stdout)

    def test_hidden_fixture_option_remains_registered_but_suppressed(self) -> None:
        parser = DOCTRINE.build_parser()
        subparsers = next(
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        self.assertEqual(
            set(subparsers.choices),
            {"route", "plan", "search", "validate", "rerank"},
        )
        search = subparsers.choices["search"]
        option = search._option_string_actions["--offline-fixtures"]
        self.assertIs(option.help, argparse.SUPPRESS)
        self.assertIsNone(option.default)
        parsed = parser.parse_args(
            [
                "search",
                "--request",
                "request.json",
                "--workspace",
                "/tmp/workspace",
                "--offline-fixtures",
                "/tmp/fixtures",
            ]
        )
        self.assertEqual(parsed.request, "request.json")
        self.assertEqual(parsed.offline_fixtures, "/tmp/fixtures")
        self.assertEqual(parsed.providers, "openalex,crossref")
        self.assertEqual(parsed.max_queries, 12)
        self.assertEqual(parsed.max_results, 10)
        self.assertEqual(parsed.timeout, 20.0)
        self.assertEqual(parsed.request_delay, 0.15)


if __name__ == "__main__":
    unittest.main()
