from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class HudocSkillInterfaceContractTest(unittest.TestCase):
    def test_resolvers_discover_version_checked_cli_from_configured_repository_worktree(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            worktree = root / "worktree"
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
            self._write_fake_repository(worktree)

            environment = self._isolated_environment(home)
            environment["HUDOC_KS_PARSER_REPO"] = str(repository)
            knowledge = self._run_resolver(
                "hudoc_kb_cli.py", environment=environment, cwd=home
            )
            vector = self._run_resolver(
                "hudoc_vector_cli.py", environment=environment, cwd=home
            )

            self.assertEqual(knowledge.returncode, 0, knowledge.stderr)
            self.assertIn("knowledge-cli-help-v3.7-v6", knowledge.stdout)
            self.assertEqual(vector.returncode, 0, vector.stderr)
            self.assertIn("vector-cli-help-v3.7-v6", vector.stdout)

    def test_resolvers_fail_closed_for_pre_v6_research_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            home = root / "home"
            home.mkdir()
            self._write_fake_repository(
                repository,
                research_version="hudoc-research-extractive-v5",
            )
            environment = self._isolated_environment(home)
            environment["HUDOC_KS_PARSER_REPO"] = str(repository)

            for resolver in ("hudoc_kb_cli.py", "hudoc_vector_cli.py"):
                with self.subTest(resolver=resolver):
                    result = self._run_resolver(
                        resolver, environment=environment, cwd=home
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("hudoc-research-extractive-v6", result.stderr)

    def test_resolvers_fail_closed_for_pre_v37_knowledge_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            home = root / "home"
            home.mkdir()
            self._write_fake_repository(
                repository,
                knowledge_version="hudoc-knowledge-indexer-v3.6",
            )
            environment = self._isolated_environment(home)
            environment["HUDOC_KS_PARSER_REPO"] = str(repository)

            for resolver in ("hudoc_kb_cli.py", "hudoc_vector_cli.py"):
                with self.subTest(resolver=resolver):
                    result = self._run_resolver(
                        resolver, environment=environment, cwd=home
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("hudoc-knowledge-indexer-v3.7", result.stderr)

    def test_resolvers_are_portable_and_pin_current_interface_versions(self) -> None:
        knowledge = self._read("scripts/hudoc_kb_cli.py")
        vector = self._read("scripts/hudoc_vector_cli.py")

        for resolver in (knowledge, vector):
            self.assertNotIn("/Users/", resolver)
            self.assertNotIn(".removeprefix(", resolver)
            self.assertIn("HUDOC_KS_PARSER_REPO", resolver)
            self.assertIn("hudoc-knowledge-indexer-v3.7", resolver)
            self.assertIn("hudoc-research-extractive-v6", resolver)
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

        self.assertIn("hudoc-research-extractive-v6", corpus)
        self.assertIn("hudoc-research-extractive-v6", knowledge)
        self.assertIn("hudoc-knowledge-indexer-v3.7", knowledge)
        self.assertIn("hudoc-vector-indexer-v2", knowledge)
        self.assertIn("hudoc-vector-evaluator-v2", knowledge)

    def _read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def _run_resolver(
        self,
        name: str,
        *,
        environment: dict[str, str],
        cwd: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / name), "--help"],
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
        research_version: str = "hudoc-research-extractive-v6",
        knowledge_version: str = "hudoc-knowledge-indexer-v3.7",
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
            f'KNOWLEDGE_INDEXER_VERSION = "{knowledge_version}"\n',
            encoding="utf-8",
        )
        (source / "hudoc_vector_search.py").write_text(
            'VECTOR_INDEXER_VERSION = "hudoc-vector-indexer-v2"\n'
            'RELEASE_EVALUATOR_VERSION = "hudoc-vector-evaluator-v2"\n',
            encoding="utf-8",
        )
        (scripts / "hudoc_knowledge_base.py").write_text(
            'print("knowledge-cli-help-v3.7-v6")\n',
            encoding="utf-8",
        )
        (scripts / "hudoc_vector_search.py").write_text(
            'print("vector-cli-help-v3.7-v6")\n',
            encoding="utf-8",
        )

    def _run(self, command: list[str]) -> None:
        subprocess.run(command, check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
