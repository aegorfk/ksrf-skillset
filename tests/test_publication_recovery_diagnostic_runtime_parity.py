from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SKILL = "ksrf-cassation-judicial-meaning"
SOURCE_SKILL = REPO / "skills" / SKILL

COMMANDS = (
    "coding-audit-prepare",
    "coding-audit-review-import",
    "coding-audit-finalize",
)
ERROR_CODES = (
    "staging_cleanup_uncertain",
    "publication_state_uncertain",
    "publication_durability_uncertain",
    "publication_finalization_uncertain",
    "confirmation_delivery_uncertain",
)
ROUTES = {
    "staging_cleanup_uncertain": "administrator_only",
    "publication_state_uncertain": "administrator_only",
    "publication_durability_uncertain": "repeat_then_compare_candidate",
    "publication_finalization_uncertain": "repeat_then_compare_candidate",
    "confirmation_delivery_uncertain": "repeat_then_compare_candidate",
}

_MAIN_PROBE = r"""
import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

skill_root = Path(sys.argv[1])
sys.path.insert(0, str(skill_root / "lib"))

import judicial_meaning.cli as cli
from judicial_meaning.practice_quality import (
    CODING_AUDIT_PUBLICATION_RECOVERY_COMMANDS,
    CODING_AUDIT_PUBLICATION_RECOVERY_ERROR_CODES,
)


class StaticParser:
    def __init__(self, namespace):
        self.namespace = namespace

    def parse_args(self, argv):
        return self.namespace


def classified(error_code):
    def run(_args):
        raise cli._PublicationRecoveryError(
            "Классифицированная неопределённость: " + error_code + ".",
            error_code=error_code,
        )

    return run


def generic(_args):
    raise OSError(
        "publication_state_uncertain выглядит похоже, но это обычный OSError."
    )


def returning(exit_code, line):
    def run(_args):
        sys.stdout.write(line)
        sys.stdout.flush()
        return exit_code

    return run


scenarios = []
for command in CODING_AUDIT_PUBLICATION_RECOVERY_COMMANDS:
    for error_code in CODING_AUDIT_PUBLICATION_RECOVERY_ERROR_CODES:
        scenarios.append(
            (
                "structured:" + command + ":" + error_code,
                command,
                True,
                classified(error_code),
            )
        )
        scenarios.append(
            (
                "human:" + command + ":" + error_code,
                command,
                False,
                classified(error_code),
            )
        )

for enabled in (False, True):
    scenarios.append(
        (
            "generic:" + str(enabled).lower(),
            "coding-audit-prepare",
            enabled,
            generic,
        )
    )

for exit_code, line in (
    (0, '{"artifact_type":"stub_success"}\n'),
    (3, '{"artifact_type":"stub_incomplete","complete":false}\n'),
):
    for enabled in (False, True):
        scenarios.append(
            (
                "return:" + str(exit_code) + ":" + str(enabled).lower(),
                "coding-audit-finalize",
                enabled,
                returning(exit_code, line),
            )
        )

results = []
for scenario_id, command, enabled, func in scenarios:
    namespace = argparse.Namespace(
        func=func,
        command="quality",
        quality_command=command,
        recovery_diagnostic_json=enabled,
    )
    cli.build_parser = lambda namespace=namespace: StaticParser(namespace)
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = cli.main([])
    results.append(
        {
            "id": scenario_id,
            "exit_code": exit_code,
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
        }
    )

sys.stdout.write(
    json.dumps(
        results,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    + "\n"
)
"""


def _tree_snapshot(root: Path) -> dict[str, tuple[str, bytes | None]]:
    result: dict[str, tuple[str, bytes | None]] = {".": ("dir", None)}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = ("symlink", os.readlink(path).encode("utf-8"))
        elif path.is_dir():
            result[relative] = ("dir", None)
        elif path.is_file():
            result[relative] = ("file", path.read_bytes())
        else:
            result[relative] = ("other", None)
    return result


class PublicationRecoveryDiagnosticRuntimeParityTests(unittest.TestCase):
    maxDiff = None

    def test_clean_install_serializes_all_commands_and_states_like_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            completed = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(installed)],
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)

            installed_skill = installed / SKILL
            for excluded in ("tests", "evals", "openspec"):
                self.assertFalse((installed_skill / excluded).exists())

            probe_directory = root / "empty probe directory"
            probe_directory.mkdir()
            before_probe = _tree_snapshot(probe_directory)
            before_installed = _tree_snapshot(installed_skill)

            observed: dict[str, bytes] = {}
            for location, skill_root in (
                ("source", SOURCE_SKILL),
                ("installed", installed_skill),
            ):
                with self.subTest(location=location):
                    run = subprocess.run(
                        [sys.executable, "-c", _MAIN_PROBE, str(skill_root)],
                        cwd=probe_directory,
                        env={
                            **os.environ,
                            "PYTHONDONTWRITEBYTECODE": "1",
                            "PYTHONIOENCODING": "ascii",
                            "PYTHONPATH": "",
                        },
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(0, run.returncode, run.stderr)
                    self.assertEqual(b"", run.stderr)
                    self.assertTrue(run.stdout.endswith(b"\n"))
                    self.assertTrue(run.stdout.isascii())
                    self.assertNotIn(str(root).encode("utf-8"), run.stdout)
                    observed[location] = run.stdout

            self.assertEqual(observed["source"], observed["installed"])
            records = json.loads(observed["source"])
            self.assertEqual(
                len(COMMANDS) * len(ERROR_CODES) * 2 + 2 + 4,
                len(records),
            )
            by_id = {record["id"]: record for record in records}
            self.assertEqual(len(records), len(by_id))

            for command in COMMANDS:
                for error_code in ERROR_CODES:
                    structured = by_id[f"structured:{command}:{error_code}"]
                    self.assertEqual(2, structured["exit_code"])
                    self.assertEqual("", structured["stdout"])
                    self.assertTrue(structured["stderr"].isascii())
                    self.assertEqual(1, len(structured["stderr"].splitlines()))
                    payload = json.loads(structured["stderr"])
                    self.assertEqual(command, payload["command"])
                    self.assertEqual(error_code, payload["error_code"])
                    self.assertEqual(ROUTES[error_code], payload["recovery_route"])
                    self.assertEqual(2, payload["exit_code"])
                    self.assertEqual(
                        json.dumps(
                            payload,
                            ensure_ascii=True,
                            sort_keys=True,
                            separators=(",", ":"),
                            allow_nan=False,
                        )
                        + "\n",
                        structured["stderr"],
                    )
                    self.assertIs(payload["scope"]["diagnostic_only"], True)
                    self.assertIs(
                        payload["scope"]["recovery_action_authorized"],
                        False,
                    )
                    self.assertIs(
                        payload["scope"]["downstream_use_allowed"],
                        False,
                    )
                    self.assertIs(payload["scope"]["publication_safe"], False)
                    self.assertIs(payload["scope"]["legal_readiness"], False)
                    self.assertIs(payload["scope"]["filing_authorized"], False)

                    human = by_id[f"human:{command}:{error_code}"]
                    self.assertEqual(2, human["exit_code"])
                    self.assertEqual("", human["stdout"])
                    self.assertEqual(
                        "Ошибка: Классифицированная неопределённость: "
                        f"{error_code}.\n",
                        human["stderr"],
                    )

            generic_stderr = (
                "Ошибка: publication_state_uncertain выглядит похоже, но это "
                "обычный OSError.\n"
            )
            for enabled in (False, True):
                generic = by_id[f"generic:{str(enabled).lower()}"]
                self.assertEqual(2, generic["exit_code"])
                self.assertEqual("", generic["stdout"])
                self.assertEqual(generic_stderr, generic["stderr"])

            for exit_code, stdout in (
                (0, '{"artifact_type":"stub_success"}\n'),
                (3, '{"artifact_type":"stub_incomplete","complete":false}\n'),
            ):
                without_flag = by_id[f"return:{exit_code}:false"]
                with_flag = by_id[f"return:{exit_code}:true"]
                self.assertEqual(
                    without_flag["exit_code"],
                    with_flag["exit_code"],
                )
                self.assertEqual(without_flag["stdout"], with_flag["stdout"])
                self.assertEqual(without_flag["stderr"], with_flag["stderr"])
                self.assertEqual(exit_code, without_flag["exit_code"])
                self.assertEqual(stdout, without_flag["stdout"])
                self.assertEqual("", without_flag["stderr"])

            self.assertEqual(before_probe, _tree_snapshot(probe_directory))
            self.assertEqual(before_installed, _tree_snapshot(installed_skill))


if __name__ == "__main__":
    unittest.main()
