from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
import importlib.util
from io import StringIO
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
RESOLVER_SPECS = (
    (
        "hudoc_kb_cli.py",
        "HUDOC_KB_CLI",
        "scripts/hudoc_knowledge_base.py",
    ),
    (
        "hudoc_vector_cli.py",
        "HUDOC_VECTOR_CLI",
        "scripts/hudoc_vector_search.py",
    ),
)
BOOTSTRAP_HELP = {
    "hudoc_kb_cli.py": """Использование: hudoc_kb_cli.py [-h | --help]

Справка по первоначальной настройке команды базы знаний HUDOC.
Переменные запуска не заданы; внешний движок и его индекс не входят в пакет
навыков и не проверялись.

Настройте один из вариантов:
  HUDOC_KB_CLI=/полный/путь/scripts/hudoc_knowledge_base.py
  HUDOC_KS_PARSER_REPO=/полный/путь/к/ks_parser

Требуемые версии: hudoc-knowledge-indexer-v3.8 +
hudoc-research-extractive-v7 + hudoc-knowledge-privacy-sanitizer-v2.
Автопоиск по HOME и текущему Git-репозиторию отключён.
После настройки снова запустите --help: совместимый движок покажет свои параметры.
Код 0 этой справки не подтверждает доступность движка, покрытие или актуальность
корпуса, юридическую силу результатов либо готовность материалов для жалобы.
""",
    "hudoc_vector_cli.py": """Использование: hudoc_vector_cli.py [-h | --help]

Справка по первоначальной настройке команды гибридного поиска HUDOC.
Переменные запуска не заданы; внешний движок и его индекс не входят в пакет
навыков и не проверялись.

Настройте один из вариантов:
  HUDOC_VECTOR_CLI=/полный/путь/scripts/hudoc_vector_search.py
  HUDOC_KS_PARSER_REPO=/полный/путь/к/ks_parser

Требуемые версии: hudoc-vector-indexer-v2 + hudoc-vector-evaluator-v2 +
hudoc-knowledge-indexer-v3.8 + hudoc-research-extractive-v7 +
hudoc-knowledge-privacy-sanitizer-v2.
Автопоиск по HOME и текущему Git-репозиторию отключён.
После настройки снова запустите --help: совместимый движок покажет свои параметры.
Код 0 этой справки не подтверждает доступность движка, покрытие или актуальность
корпуса, юридическую силу результатов либо готовность материалов для жалобы.
""",
}
UNCONFIGURED_ERROR = {
    "hudoc_kb_cli.py": (
        "Движок HUDOC knowledge CLI не настроен и не входит в пакет skills. "
        "Укажите HUDOC_KB_CLI (точный путь к scripts/hudoc_knowledge_base.py) "
        "или HUDOC_KS_PARSER_REPO (корень ks_parser). Автопоиск по HOME и "
        "текущему git-репозиторию отключён.\n"
    ),
    "hudoc_vector_cli.py": (
        "Движок HUDOC vector CLI не настроен и не входит в пакет skills. "
        "Укажите HUDOC_VECTOR_CLI (точный путь к scripts/hudoc_vector_search.py) "
        "или HUDOC_KS_PARSER_REPO (корень ks_parser). Автопоиск по HOME и "
        "текущему git-репозиторию отключён.\n"
    ),
}


class HudocSkillInterfaceContractTest(unittest.TestCase):
    def test_fully_unconfigured_resolvers_offer_exact_bootstrap_help(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            foreign_cwd = root / "foreign cwd"
            home.mkdir()
            foreign_cwd.mkdir()
            environment = self._isolated_environment(home)

            for resolver, _, _ in RESOLVER_SPECS:
                for help_flag in ("-h", "--help"):
                    with self.subTest(resolver=resolver, help_flag=help_flag):
                        result = self._run_resolver(
                            resolver,
                            environment=environment,
                            cwd=foreign_cwd,
                            arguments=(help_flag,),
                        )

                        self.assertEqual(result.returncode, 0)
                        self.assertEqual(result.stdout, BOOTSTRAP_HELP[resolver])
                        self.assertEqual(result.stderr, "")

    def test_bootstrap_help_stops_before_discovery_or_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            environment = self._isolated_environment(home)

            for resolver, _, _ in RESOLVER_SPECS:
                module = self._load_resolver(resolver)
                for help_flag in ("-h", "--help"):
                    with self.subTest(resolver=resolver, help_flag=help_flag):
                        stdout = StringIO()
                        stderr = StringIO()
                        sentinels = (
                            mock.patch.object(
                                module,
                                "candidates",
                                side_effect=AssertionError("candidate discovery ran"),
                            ),
                            mock.patch.object(
                                module,
                                "configured_path",
                                side_effect=AssertionError("configuration read ran"),
                            ),
                            mock.patch.object(
                                module,
                                "repository_worktrees",
                                side_effect=AssertionError("git discovery ran"),
                            ),
                            mock.patch.object(
                                module,
                                "module_version",
                                side_effect=AssertionError("version file read ran"),
                            ),
                            mock.patch.object(
                                module,
                                "is_expected_version",
                                side_effect=AssertionError("version gate ran"),
                            ),
                            mock.patch.object(
                                module.subprocess,
                                "run",
                                side_effect=AssertionError("subprocess ran"),
                            ),
                            mock.patch.object(
                                module.os,
                                "chdir",
                                side_effect=AssertionError("cwd changed"),
                            ),
                            mock.patch.object(
                                module.os,
                                "execve",
                                side_effect=AssertionError("exec ran"),
                            ),
                        )
                        with ExitStack() as stack:
                            stack.enter_context(
                                mock.patch.dict(os.environ, environment, clear=True)
                            )
                            stack.enter_context(
                                mock.patch.object(
                                    sys,
                                    "argv",
                                    [str(SKILL_ROOT / "scripts" / resolver), help_flag],
                                )
                            )
                            stack.enter_context(redirect_stdout(stdout))
                            stack.enter_context(redirect_stderr(stderr))
                            for sentinel in sentinels:
                                stack.enter_context(sentinel)
                            result = module.main()

                        self.assertIsNone(result)
                        self.assertEqual(stdout.getvalue(), BOOTSTRAP_HELP[resolver])
                        self.assertEqual(stderr.getvalue(), "")

    def test_unconfigured_nonexact_help_remains_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            cwd = root / "cwd"
            home.mkdir()
            cwd.mkdir()
            environment = self._isolated_environment(home)
            argument_sets = (
                (),
                ("status",),
                ("--he",),
                ("--help=x",),
                ("--help", "status"),
                ("status", "--help"),
                ("-h", "status"),
                ("--help", "--help"),
            )

            for resolver, _, _ in RESOLVER_SPECS:
                for arguments in argument_sets:
                    with self.subTest(resolver=resolver, arguments=arguments):
                        result = self._run_resolver(
                            resolver,
                            environment=environment,
                            cwd=cwd,
                            arguments=arguments,
                        )

                        self.assertEqual(result.returncode, 1)
                        self.assertEqual(result.stdout, "")
                        self.assertEqual(result.stderr, UNCONFIGURED_ERROR[resolver])

    def test_present_blank_configuration_is_not_masked_by_bootstrap_help(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()

            for resolver, direct_env, _ in RESOLVER_SPECS:
                for variable in (direct_env, "HUDOC_KS_PARSER_REPO"):
                    for blank in ("", " \t"):
                        with self.subTest(
                            resolver=resolver,
                            variable=variable,
                            blank=blank,
                        ):
                            environment = self._isolated_environment(home)
                            environment[variable] = blank
                            result = self._run_resolver(
                                resolver,
                                environment=environment,
                                cwd=home,
                            )

                            self.assertEqual(result.returncode, 1)
                            self.assertEqual(result.stdout, "")
                            self.assertIn(
                                f"{variable} задан, но значение пусто",
                                result.stderr,
                            )
                            self.assertNotIn("первоначальной настройке", result.stderr)

    def test_other_resolver_variable_does_not_block_bootstrap_help(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            for resolver, _, _ in RESOLVER_SPECS:
                environment = self._isolated_environment(home)
                unrelated = (
                    "HUDOC_VECTOR_CLI"
                    if resolver == "hudoc_kb_cli.py"
                    else "HUDOC_KB_CLI"
                )
                environment[unrelated] = "/unrelated/configuration"

                result = self._run_resolver(
                    resolver,
                    environment=environment,
                    cwd=home,
                )

                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, BOOTSTRAP_HELP[resolver])
                self.assertEqual(result.stderr, "")

    def test_resolvers_discover_version_checked_cli_from_configured_repository_worktree(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository with spaces"
            worktree = root / "worktree with spaces"
            home = root / "home"
            home.mkdir()
            self._run(["git", "init", str(repository)])
            (repository / "README.md").write_text("fixture\n", encoding="utf-8")
            self._run(["git", "-C", str(repository), "add", "README.md"])
            self._run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "-c",
                    "user.name=HUDOC fixture",
                    "-c",
                    "user.email=hudoc-fixture@example.invalid",
                    "commit",
                    "-m",
                    "fixture",
                ]
            )
            self._run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "worktree",
                    "add",
                    "-b",
                    "hudoc-interface-fixture",
                    str(worktree),
                ]
            )
            self._write_fake_repository(worktree, record_runtime_context=True)

            environment = self._isolated_environment(home)
            environment["HUDOC_KS_PARSER_REPO"] = str(repository)
            existing_pythonpath = os.pathsep.join(
                (str(root / "existing one"), str(root / "existing two"))
            )
            environment["PYTHONPATH"] = existing_pythonpath
            knowledge = self._run_resolver(
                "hudoc_kb_cli.py", environment=environment, cwd=home
            )
            vector = self._run_resolver(
                "hudoc_vector_cli.py", environment=environment, cwd=home
            )

            self.assertEqual(knowledge.returncode, 0, knowledge.stderr)
            self.assertEqual(vector.returncode, 0, vector.stderr)
            for result, marker in (
                (knowledge, "knowledge-cli-help-v3.8-v7-v2"),
                (vector, "vector-cli-help-v3.8-v7-v2"),
            ):
                payload = json.loads(result.stdout)
                self.assertEqual(payload["marker"], marker)
                self.assertEqual(payload["cwd"], str(worktree.resolve()))
                self.assertEqual(
                    payload["pythonpath"],
                    f"{worktree.resolve()}{os.pathsep}{existing_pythonpath}",
                )
                self.assertEqual(payload["argv"], ["--help"])

    def test_resolvers_require_explicit_configuration_and_ignore_current_git_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "current repository"
            home = root / "home"
            home.mkdir()
            self._run(["git", "init", str(repository)])
            self._write_fake_repository(repository)
            environment = self._isolated_environment(home)

            for resolver, direct_env, _ in RESOLVER_SPECS:
                with self.subTest(resolver=resolver):
                    result = self._run_resolver(
                        resolver,
                        environment=environment,
                        cwd=repository,
                        arguments=(),
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(direct_env, result.stderr)
                    self.assertIn("HUDOC_KS_PARSER_REPO", result.stderr)
                    self.assertIn("не входит в пакет skills", result.stderr)
                    self.assertIn("Автопоиск", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_resolvers_require_explicit_configuration_and_ignore_home_default(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            repository = home / "Documents" / "ks_parser"
            unrelated_cwd = root / "unrelated cwd"
            unrelated_cwd.mkdir()
            self._write_fake_repository(repository)
            environment = self._isolated_environment(home)

            for resolver, direct_env, _ in RESOLVER_SPECS:
                with self.subTest(resolver=resolver):
                    result = self._run_resolver(
                        resolver,
                        environment=environment,
                        cwd=unrelated_cwd,
                        arguments=(),
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(direct_env, result.stderr)
                    self.assertIn("HUDOC_KS_PARSER_REPO", result.stderr)
                    self.assertIn("не входит в пакет skills", result.stderr)
                    self.assertIn("Автопоиск", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_direct_cli_environment_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "valid configured repository"
            home = root / "home"
            home.mkdir()
            self._write_fake_repository(repository)

            for resolver, direct_env, relative_cli in RESOLVER_SPECS:
                with self.subTest(resolver=resolver):
                    missing_cli = root / "missing direct CLI" / Path(relative_cli).name
                    environment = self._isolated_environment(home)
                    environment["HUDOC_KS_PARSER_REPO"] = str(repository)
                    environment[direct_env] = str(missing_cli)
                    result = self._run_resolver(
                        resolver, environment=environment, cwd=home
                    )

                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(direct_env, result.stderr)
                    self.assertIn(str(missing_cli), result.stderr)
                    self.assertIn("Другие пути не проверялись", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_repository_environment_is_exclusive_from_cwd_and_home(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configured_repository = root / "configured incompatible repository"
            current_repository = root / "current valid repository"
            home = root / "home"
            home_repository = home / "Documents" / "ks_parser"
            home.mkdir()
            self._write_fake_repository(
                configured_repository,
                research_version="hudoc-research-extractive-v6",
            )
            self._run(["git", "init", str(current_repository)])
            self._write_fake_repository(current_repository)
            self._write_fake_repository(home_repository)
            environment = self._isolated_environment(home)
            environment["HUDOC_KS_PARSER_REPO"] = str(configured_repository)

            for resolver, direct_env, _ in RESOLVER_SPECS:
                with self.subTest(resolver=resolver):
                    result = self._run_resolver(
                        resolver,
                        environment=environment,
                        cwd=current_repository,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(direct_env, result.stderr)
                    self.assertIn(
                        str(configured_repository.resolve()), result.stderr
                    )
                    self.assertIn("Другие каталоги не проверялись", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_direct_cli_preserves_cwd_pythonpath_and_argv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "direct repository with spaces"
            home = root / "home"
            unrelated_cwd = root / "unrelated cwd"
            home.mkdir()
            unrelated_cwd.mkdir()
            self._write_fake_repository(repository, record_runtime_context=True)
            existing_pythonpath = os.pathsep.join(
                (str(root / "existing one"), str(root / "existing two"))
            )

            for resolver, direct_env, relative_cli in RESOLVER_SPECS:
                with self.subTest(resolver=resolver):
                    environment = self._isolated_environment(home)
                    environment["PYTHONPATH"] = existing_pythonpath
                    environment[direct_env] = str(repository / relative_cli)
                    result = self._run_resolver(
                        resolver,
                        environment=environment,
                        cwd=unrelated_cwd,
                        arguments=("--probe", "value with spaces"),
                    )

                    self.assertEqual(result.returncode, 0, result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["cwd"], str(repository.resolve()))
                    self.assertEqual(
                        payload["pythonpath"],
                        f"{repository.resolve()}{os.pathsep}{existing_pythonpath}",
                    )
                    self.assertEqual(
                        payload["argv"], ["--probe", "value with spaces"]
                    )

    def test_compatible_direct_cli_receives_help_flags_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "direct repository"
            home = root / "home"
            home.mkdir()
            self._write_fake_repository(repository, record_runtime_context=True)

            for resolver, direct_env, relative_cli in RESOLVER_SPECS:
                for arguments in (("-h",), ("--help",), ("--help", "extra")):
                    with self.subTest(resolver=resolver, arguments=arguments):
                        environment = self._isolated_environment(home)
                        environment[direct_env] = str(repository / relative_cli)
                        environment["HUDOC_KS_PARSER_REPO"] = " \t"
                        result = self._run_resolver(
                            resolver,
                            environment=environment,
                            cwd=home,
                            arguments=arguments,
                        )

                        self.assertEqual(result.returncode, 0, result.stderr)
                        payload = json.loads(result.stdout)
                        self.assertEqual(payload["argv"], list(arguments))
                        self.assertEqual(payload["cwd"], str(repository.resolve()))

    def test_resolvers_fail_closed_for_pre_v7_research_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            home = root / "home"
            home.mkdir()
            self._write_fake_repository(
                repository,
                research_version="hudoc-research-extractive-v6",
            )
            environment = self._isolated_environment(home)
            environment["HUDOC_KS_PARSER_REPO"] = str(repository)

            for resolver in ("hudoc_kb_cli.py", "hudoc_vector_cli.py"):
                with self.subTest(resolver=resolver):
                    result = self._run_resolver(
                        resolver, environment=environment, cwd=home
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("hudoc-research-extractive-v7", result.stderr)

    def test_resolvers_fail_closed_for_pre_v38_knowledge_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            home = root / "home"
            home.mkdir()
            self._write_fake_repository(
                repository,
                knowledge_version="hudoc-knowledge-indexer-v3.7",
            )
            environment = self._isolated_environment(home)
            environment["HUDOC_KS_PARSER_REPO"] = str(repository)

            for resolver in ("hudoc_kb_cli.py", "hudoc_vector_cli.py"):
                with self.subTest(resolver=resolver):
                    result = self._run_resolver(
                        resolver, environment=environment, cwd=home
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("hudoc-knowledge-indexer-v3.8", result.stderr)

    def test_resolvers_fail_closed_for_pre_v2_privacy_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            home = root / "home"
            home.mkdir()
            self._write_fake_repository(
                repository,
                privacy_version="hudoc-knowledge-privacy-sanitizer-v1",
            )
            environment = self._isolated_environment(home)
            environment["HUDOC_KS_PARSER_REPO"] = str(repository)

            for resolver in ("hudoc_kb_cli.py", "hudoc_vector_cli.py"):
                with self.subTest(resolver=resolver):
                    result = self._run_resolver(
                        resolver, environment=environment, cwd=home
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(
                        "hudoc-knowledge-privacy-sanitizer-v2", result.stderr
                    )

    def test_vector_resolver_fails_closed_for_pre_v2_indexer_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            home = root / "home"
            home.mkdir()
            self._write_fake_repository(
                repository,
                vector_indexer_version="hudoc-vector-indexer-v1",
            )
            environment = self._isolated_environment(home)
            environment["HUDOC_KS_PARSER_REPO"] = str(repository)

            result = self._run_resolver(
                "hudoc_vector_cli.py", environment=environment, cwd=home
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("hudoc-vector-indexer-v2", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_vector_resolver_fails_closed_for_pre_v2_evaluator_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            home = root / "home"
            home.mkdir()
            self._write_fake_repository(
                repository,
                vector_evaluator_version="hudoc-vector-evaluator-v1",
            )
            environment = self._isolated_environment(home)
            environment["HUDOC_KS_PARSER_REPO"] = str(repository)

            result = self._run_resolver(
                "hudoc_vector_cli.py", environment=environment, cwd=home
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("hudoc-vector-evaluator-v2", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_resolvers_are_portable_and_pin_current_interface_versions(self) -> None:
        knowledge = self._read("scripts/hudoc_kb_cli.py")
        vector = self._read("scripts/hudoc_vector_cli.py")

        for resolver in (knowledge, vector):
            self.assertNotIn("/Users/", resolver)
            self.assertNotIn(".removeprefix(", resolver)
            self.assertIn("HUDOC_KS_PARSER_REPO", resolver)
            self.assertIn("hudoc-knowledge-indexer-v3.8", resolver)
            self.assertIn("hudoc-research-extractive-v7", resolver)
            self.assertIn("hudoc-knowledge-privacy-sanitizer-v2", resolver)
        self.assertIn("hudoc-vector-indexer-v2", vector)
        self.assertIn("hudoc-vector-evaluator-v2", vector)

    def test_output_contract_requires_source_attribution(self) -> None:
        skill = self._read("SKILL.md")
        result_contract = skill.split("## Результат", 1)[1].split(
            "## Особые правила", 1
        )[0]

        self.assertNotIn("`Тезис ЕСПЧ`", result_contract)
        self.assertIn("`Проверяемый тезис источника`", result_contract)
        for field in (
            "`source_actor`",
            "`source_function`",
            "`source_form`",
            "`court_treatment`",
        ):
            self.assertIn(field, result_contract)

    def test_fixture_exercises_mixed_applicant_and_court_attribution(self) -> None:
        fixture = self._read("references/verified-hudoc-pilot-fixture.md")

        self.assertIn("Fixture 4: mixed applicant/Court negative control", fixture)
        self.assertIn("The applicant argued that the rule was automatic.", fixture)
        self.assertIn(
            "The Court considers that an individual assessment was required.",
            fixture,
        )
        for marker in (
            "`source_actor=applicant`",
            "`source_function=submission`",
            "`source_form=reproduced_in_public_act`",
            "`court_treatment=unclear`",
            "`authority_status=non_authority`",
            "`promotion_eligible=false`",
        ):
            self.assertIn(marker, fixture)

    def test_russian_anchor_exception_is_exactly_scoped_to_method_only_lane(
        self,
    ) -> None:
        corpus = self._read("references/local-hudoc-corpus.md")
        knowledge = self._read("references/local-hudoc-knowledge-base.md")
        exact_exception = (
            "`authority_status=non_authority`, "
            "`reuse_target=research_checklist_only` и "
            "`substantive_rule_changed=false`"
        )

        self.assertIn(exact_exception, corpus)
        self.assertIn(exact_exception, knowledge)
        self.assertIn("Во всех остальных случаях российский якорь обязателен", corpus)
        self.assertIn("Во всех остальных случаях российский якорь обязателен", knowledge)

    def test_references_name_current_hudoc_interface_versions(self) -> None:
        corpus = self._read("references/local-hudoc-corpus.md")
        knowledge = self._read("references/local-hudoc-knowledge-base.md")

        self.assertIn("hudoc-research-extractive-v7", corpus)
        self.assertIn("hudoc-research-extractive-v7", knowledge)
        self.assertIn("hudoc-knowledge-indexer-v3.8", knowledge)
        self.assertIn("hudoc-knowledge-privacy-sanitizer-v2", knowledge)
        self.assertIn("hudoc-vector-indexer-v2", knowledge)
        self.assertIn("hudoc-vector-evaluator-v2", knowledge)

    def test_reference_explains_bootstrap_and_delegated_help_boundary(self) -> None:
        knowledge = self._read("references/local-hudoc-knowledge-base.md")

        self.assertIn("справку по первоначальной настройке", knowledge)
        self.assertIn("только когда обе переменные настройки отсутствуют", knowledge)
        self.assertIn("после настройки передаётся совместимому движку", knowledge)
        self.assertIn("не подтверждает доступность движка", knowledge)

    def _read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def _load_resolver(self, name: str):
        spec = importlib.util.spec_from_file_location(
            f"ksrf_hudoc_resolver_{name.replace('.', '_')}",
            SKILL_ROOT / "scripts" / name,
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _run_resolver(
        self,
        name: str,
        *,
        environment: dict[str, str],
        cwd: Path,
        arguments: tuple[str, ...] = ("--help",),
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / name), *arguments],
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def _isolated_environment(self, home: Path) -> dict[str, str]:
        environment = dict(os.environ)
        environment["HOME"] = str(home)
        environment.pop("HUDOC_KB_CLI", None)
        environment.pop("HUDOC_VECTOR_CLI", None)
        environment.pop("HUDOC_KS_PARSER_REPO", None)
        return environment

    def _write_fake_repository(
        self,
        repository: Path,
        *,
        research_version: str = "hudoc-research-extractive-v7",
        knowledge_version: str = "hudoc-knowledge-indexer-v3.8",
        privacy_version: str = "hudoc-knowledge-privacy-sanitizer-v2",
        vector_indexer_version: str = "hudoc-vector-indexer-v2",
        vector_evaluator_version: str = "hudoc-vector-evaluator-v2",
        record_runtime_context: bool = False,
    ) -> None:
        scripts = repository / "scripts"
        source = repository / "src"
        scripts.mkdir(parents=True, exist_ok=True)
        source.mkdir(parents=True, exist_ok=True)
        (source / "hudoc_research.py").write_text(
            f'RESEARCH_EXTRACTOR_VERSION = "{research_version}"\n',
            encoding="utf-8",
        )
        (source / "hudoc_knowledge_base.py").write_text(
            f'KNOWLEDGE_INDEXER_VERSION = "{knowledge_version}"\n'
            f'PRIVACY_SANITIZER_VERSION = "{privacy_version}"\n',
            encoding="utf-8",
        )
        (source / "hudoc_vector_search.py").write_text(
            f'VECTOR_INDEXER_VERSION = "{vector_indexer_version}"\n'
            f'RELEASE_EVALUATOR_VERSION = "{vector_evaluator_version}"\n',
            encoding="utf-8",
        )
        if record_runtime_context:
            knowledge_cli = self._runtime_context_cli_source(
                "knowledge-cli-help-v3.8-v7-v2"
            )
            vector_cli = self._runtime_context_cli_source(
                "vector-cli-help-v3.8-v7-v2"
            )
        else:
            knowledge_cli = 'print("knowledge-cli-help-v3.8-v7-v2")\n'
            vector_cli = 'print("vector-cli-help-v3.8-v7-v2")\n'
        (scripts / "hudoc_knowledge_base.py").write_text(
            knowledge_cli,
            encoding="utf-8",
        )
        (scripts / "hudoc_vector_search.py").write_text(
            vector_cli,
            encoding="utf-8",
        )

    def _runtime_context_cli_source(self, marker: str) -> str:
        return (
            "import json\n"
            "import os\n"
            "import sys\n"
            "print(json.dumps({\n"
            f'    "marker": "{marker}",\n'
            '    "cwd": os.getcwd(),\n'
            '    "pythonpath": os.environ.get("PYTHONPATH"),\n'
            '    "argv": sys.argv[1:],\n'
            "}))\n"
        )

    def _run(self, command: list[str]) -> None:
        subprocess.run(command, check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
