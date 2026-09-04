from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

PARSER_COUNTS = {
    "argument": 1,
    "authority": 1,
    "autocollect": 1,
    "doctrine": 6,
    "judicial": 66,
    "ksrf": 15,
    "practice": 18,
    "validator": 1,
}

_PARSER_INVENTORY_CODE = r"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
skills_root = root / "skills" if (root / "skills").is_dir() else root

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

sys.path.insert(0, str(skills_root / "ksrf-cassation-judicial-meaning" / "lib"))
from judicial_meaning.cli import build_parser as build_judicial_parser

sys.path.insert(0, str(skills_root / "ksrf-complaint-cycle" / "lib"))
from ksrf.filing.cli import build_parser as build_ksrf_parser

practice = load(
    "runtime_option_exactness_practice",
    skills_root / "ksrf-complaint-cycle" / "scripts" / "ksrf_practice_analysis.py",
)
autocollect = load(
    "runtime_option_exactness_autocollect",
    skills_root / "ksrf-complaint-cycle" / "scripts" / "ksrf_autocollect.py",
)
doctrine = load(
    "runtime_option_exactness_doctrine",
    skills_root / "ksrf-doctrine-research" / "scripts" / "doctrine_research.py",
)
authority = load(
    "runtime_option_exactness_authority",
    skills_root
    / "ksrf-practice-authority-builder"
    / "scripts"
    / "validate_authority_ledger.py",
)
argument = load(
    "runtime_option_exactness_argument",
    skills_root
    / "ksrf-explore-arguments"
    / "scripts"
    / "validate_argument_research.py",
)
validator = load(
    "runtime_option_exactness_validator",
    skills_root
    / "ksrf-complaint-cycle"
    / "scripts"
    / "validate_ksrf_skillset.py",
)

class _ParserCaptured(RuntimeError):
    pass

captured = []
original_parse_args = argparse.ArgumentParser.parse_args
def capture_parser(self, args=None, namespace=None):
    captured.append(self)
    raise _ParserCaptured

argparse.ArgumentParser.parse_args = capture_parser
try:
    validator.main([])
except _ParserCaptured:
    pass
finally:
    argparse.ArgumentParser.parse_args = original_parse_args
if len(captured) != 1:
    raise RuntimeError(f"validator parser capture count: {len(captured)}")

families = {
    "argument": argument._build_help_parser(),
    "authority": authority._RussianArgumentParser(prog="validate_authority_ledger.py"),
    "autocollect": autocollect._build_parser(),
    "doctrine": doctrine.build_parser(),
    "judicial": build_judicial_parser(),
    "ksrf": build_ksrf_parser(),
    "practice": practice._build_parser(),
    "validator": captured[0],
}

counts = {}
violations = []
for family, parser in families.items():
    seen = set()
    pending = [([], parser)]
    while pending:
        route, current = pending.pop()
        identity = id(current)
        if identity in seen:
            continue
        seen.add(identity)
        if current.allow_abbrev is not False:
            violations.append({"family": family, "route": route})
        for action in current._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, child in action.choices.items():
                    pending.append(([*route, name], child))
    counts[family] = len(seen)

print(json.dumps({"counts": counts, "violations": violations}, sort_keys=True))
"""


class RuntimeOptionExactnessTests(unittest.TestCase):
    def test_every_public_custom_parser_disables_abbreviation_in_source_and_install(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            self._install(installed, cwd=root)

            for location, payload_root in (("source", REPO), ("installed", installed)):
                with self.subTest(location=location):
                    inventory = self._inventory(payload_root)
                    self.assertEqual(inventory["counts"], PARSER_COUNTS)
                    self.assertEqual(inventory["violations"], [])

    def test_abbreviated_matter_options_are_rejected_before_source_or_installed_writes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            self._install(installed, cwd=root)

            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                script = (
                    skills_root
                    / "ksrf-complaint-cycle"
                    / "scripts"
                    / "ksrf.py"
                )
                abbreviated_cases = (
                    (
                        "required-prefixes",
                        ("--matter-i", "CASE-ABBREV", "--worksp"),
                    ),
                    (
                        "optional-prefix",
                        ("--matter-id", "CASE-ABBREV", "--workspace"),
                    ),
                )
                for case_name, option_tokens in abbreviated_cases:
                    with self.subTest(location=location, case=case_name):
                        case_root = root / f"{location}-{case_name}"
                        case_root.mkdir()
                        workspace = case_root / "matter"
                        arguments = ["matter", "init"]
                        if case_name == "required-prefixes":
                            arguments.extend(
                                [
                                    option_tokens[0],
                                    option_tokens[1],
                                    option_tokens[2],
                                    str(workspace),
                                    "--json",
                                ]
                            )
                        else:
                            arguments.extend(
                                [
                                    option_tokens[0],
                                    option_tokens[1],
                                    option_tokens[2],
                                    str(workspace),
                                    "--jso",
                                ]
                            )

                        before = self._snapshot(case_root)
                        completed = self._run(script, arguments, cwd=case_root)

                        self.assertEqual(completed.returncode, 2)
                        self.assertEqual(completed.stdout, "")
                        self.assertIn("Ошибка:", completed.stderr)
                        if case_name == "optional-prefix":
                            self.assertIn("--jso", completed.stderr)
                        self.assertEqual(self._snapshot(case_root), before)
                        self.assertFalse(workspace.exists())

                exact_root = root / f"{location}-exact"
                exact_root.mkdir()
                exact_workspace = exact_root / "matter"
                exact = self._run(
                    script,
                    [
                        "matter",
                        "init",
                        "--matter-id",
                        "CASE-EXACT",
                        "--workspace",
                        str(exact_workspace),
                        "--json",
                    ],
                    cwd=exact_root,
                )
                self.assertEqual(exact.returncode, 0, exact.stderr)
                self.assertEqual(
                    json.loads(exact.stdout)["matter"]["matter_identifier"],
                    "CASE-EXACT",
                )
                self.assertTrue((exact_workspace / "matter.json").is_file())

                alias_root = root / f"{location}-exact-alias"
                alias_root.mkdir()
                alias_workspace = alias_root / "matter"
                alias = self._run(
                    script,
                    [
                        "matter",
                        "init",
                        "--id=CASE-ALIAS",
                        f"--destination={alias_workspace}",
                        "--json",
                    ],
                    cwd=alias_root,
                )
                self.assertEqual(alias.returncode, 0, alias.stderr)
                self.assertEqual(
                    json.loads(alias.stdout)["matter"]["matter_identifier"],
                    "CASE-ALIAS",
                )
                self.assertTrue((alias_workspace / "matter.json").is_file())

    def test_bare_runtime_validator_rejects_abbreviated_json_option(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            self._install(installed, cwd=root)

            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                with self.subTest(location=location):
                    script = (
                        skills_root
                        / "ksrf-complaint-cycle"
                        / "scripts"
                        / "validate_ksrf_skillset.py"
                    )
                    completed = self._run(script, ["--jso"], cwd=root)

                    self.assertEqual(completed.returncode, 2)
                    self.assertEqual(completed.stdout, "")
                    self.assertIn("--jso", completed.stderr)

    def test_argument_validator_rejects_help_prefix_forms_before_file_read(
        self,
    ) -> None:
        valid_artifact = {
            "case_id": "CASE-ARGUMENT",
            "findings": [],
            "hypotheses": [],
            "portfolio": {
                "human_approval": "pending",
                "principal_hypothesis_id": None,
                "reserve_hypothesis_ids": [],
                "experimental_hypothesis_ids": [],
                "rejected_hypothesis_ids": [],
            },
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            self._install(installed, cwd=root)

            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                script = (
                    skills_root
                    / "ksrf-explore-arguments"
                    / "scripts"
                    / "validate_argument_research.py"
                )
                for index, filename in enumerate(("--he", "--he=case.json")):
                    with self.subTest(location=location, filename=filename):
                        case_root = root / f"argument-prefix-{location}-{index}"
                        case_root.mkdir()
                        disguised_input = case_root / filename
                        original = (
                            json.dumps(valid_artifact, ensure_ascii=False) + "\n"
                        )
                        disguised_input.write_text(original, encoding="utf-8")

                        completed = self._run(script, [filename], cwd=case_root)

                        self.assertEqual(completed.returncode, 2)
                        self.assertEqual(completed.stdout, "")
                        self.assertIn(filename, completed.stderr)
                        self.assertEqual(
                            disguised_input.read_text(encoding="utf-8"),
                            original,
                        )

    def test_argument_validator_preserves_other_dash_prefixed_paths(self) -> None:
        valid_artifact = {
            "case_id": "CASE-DASH-PATH",
            "findings": [],
            "hypotheses": [],
            "portfolio": {
                "human_approval": "pending",
                "principal_hypothesis_id": None,
                "reserve_hypothesis_ids": [],
                "experimental_hypothesis_ids": [],
                "rejected_hypothesis_ids": [],
            },
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            self._install(installed, cwd=root)

            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                script = (
                    skills_root
                    / "ksrf-explore-arguments"
                    / "scripts"
                    / "validate_argument_research.py"
                )
                for index, filename in enumerate(
                    (
                        "-case.json",
                        "--case.json",
                        "--case=value.json",
                        "--helpful.json",
                        "--helpful=case.json",
                        "--help=case.json",
                        "-",
                        "--",
                    )
                ):
                    with self.subTest(location=location, filename=filename):
                        case_root = (
                            root
                            / f"argument-{location}-{index}-{filename.lstrip('-')}"
                        )
                        case_root.mkdir()
                        artifact = case_root / filename
                        artifact.write_text(
                            json.dumps(valid_artifact, ensure_ascii=False) + "\n",
                            encoding="utf-8",
                        )

                        completed = self._run(script, [filename], cwd=case_root)

                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        self.assertEqual(
                            completed.stdout,
                            "OK: базовая структура и ссылки соответствуют "
                            "контракту; юридическая готовность не проверялась\n",
                        )
                        self.assertEqual(completed.stderr, "")

    def _install(self, target: Path, *, cwd: Path) -> None:
        completed = subprocess.run(
            [str(REPO / "install.sh"), "--target", str(target)],
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def _inventory(self, root: Path) -> dict[str, object]:
        completed = subprocess.run(
            [PYTHON, "-c", _PARSER_INVENTORY_CODE, str(root)],
            cwd=root,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def _run(
        self,
        script: Path,
        arguments: list[str],
        *,
        cwd: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(script), *arguments],
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )

    def _snapshot(self, root: Path) -> list[str]:
        return sorted(str(path.relative_to(root)) for path in root.rglob("*"))


if __name__ == "__main__":
    unittest.main()
