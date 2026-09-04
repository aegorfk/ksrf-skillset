from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO / "tools" / "skillset_file_contract.py"
SPEC = importlib.util.spec_from_file_location("skillset_file_contract", CONTRACT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Не удалось загрузить {CONTRACT_PATH}")
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)

CANONICAL_ROOT = (
    'KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"'
)
CLI_PACKAGES = {
    "doctrine_research.py": "ksrf-doctrine-research",
    "judicial_meaning.py": "ksrf-cassation-judicial-meaning",
    "ksrf_autocollect.py": "ksrf-complaint-cycle",
    "ksrf.py": "ksrf-complaint-cycle",
    "ksrf_practice_analysis.py": "ksrf-complaint-cycle",
    "ksrf_setup_doctor.py": "ksrf-complaint-cycle",
    "validate_argument_research.py": "ksrf-explore-arguments",
    "validate_authority_ledger.py": "ksrf-practice-authority-builder",
}
CLI_COUNTS = {
    "doctrine_research.py": 5,
    "judicial_meaning.py": 39,
    "ksrf_autocollect.py": 1,
    "ksrf.py": 5,
    "ksrf_practice_analysis.py": 2,
    "ksrf_setup_doctor.py": 1,
    "validate_argument_research.py": 1,
    "validate_authority_ledger.py": 3,
}
UNRESOLVED_MARKERS = (
    "<skill" + "-dir>",
    "<skill" + "-root>",
    "/path/to/installed/" + "skills",
    "~/" + ".codex/skills",
)
COMMAND_START = re.compile(
    r'^\s*python3\s+(?P<program>"[^"\n]+/scripts/(?P<quoted>[^/"\s]+\.py)"|'
    r"\S+/scripts/(?P<plain>[^/\s]+\.py))(?P<tail>.*)$"
)
COMMAND_TAILS_SHA256 = "61367fe7f79edcd6199b12245075e5739499e730747f28f5b0eec6a58b8fff17"


def _user_markdown() -> list[tuple[str, str]]:
    payload: list[tuple[str, str]] = []
    for package in CONTRACT.SKILL_NAMES:
        package_root = REPO / "skills" / package
        for path in CONTRACT.payload_files(package_root):
            if path.suffix.casefold() != ".md":
                continue
            logical = f"{package}/{path.relative_to(package_root).as_posix()}"
            payload.append((logical, path.read_text(encoding="utf-8")))
    payload.append(("README.md", (REPO / "README.md").read_text(encoding="utf-8")))
    return sorted(payload)


def _commands() -> list[tuple[str, str, str, str]]:
    commands: list[tuple[str, str, str, str]] = []
    for logical, text in _user_markdown():
        lines = text.splitlines()
        for index, line in enumerate(lines):
            match = COMMAND_START.match(line)
            if not match:
                continue
            cli = match.group("quoted") or match.group("plain")
            if cli not in CLI_PACKAGES:
                continue
            parts = [match.group("tail").strip()]
            cursor = index
            while lines[cursor].rstrip().endswith("\\"):
                cursor += 1
                if cursor >= len(lines):
                    raise AssertionError(f"Незавершённая команда: {logical}:{index + 1}")
                parts.append(lines[cursor].strip())
            normalized_tail = " ".join(
                part[:-1].rstrip() if part.endswith("\\") else part
                for part in parts
                if part
            )
            commands.append(
                (logical, cli, match.group("program"), normalized_tail)
            )
    return commands


def _command_blocks() -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for logical, text in _user_markdown():
        inside = False
        language = ""
        body: list[str] = []
        for line in text.splitlines():
            if line.startswith("```"):
                if inside:
                    if language in {"bash", "sh", "shell"}:
                        blocks.append((logical, "\n".join(body)))
                    inside = False
                    language = ""
                    body = []
                else:
                    inside = True
                    language = line.removeprefix("```").strip().casefold()
                continue
            if inside:
                body.append(line)
    return blocks


class RuntimeCommandPathContractTests(unittest.TestCase):
    def test_all_bundled_commands_use_one_quoted_portable_root(self) -> None:
        commands = _commands()
        counts = {cli: 0 for cli in CLI_PACKAGES}
        for logical, cli, program, _tail in commands:
            counts[cli] += 1
            expected = f'"$KSRF_SKILLS_ROOT/{CLI_PACKAGES[cli]}/scripts/{cli}"'
            self.assertEqual(program, expected, f"Непереносимый путь: {logical}")

        self.assertEqual(len(commands), 57)
        self.assertEqual(counts, CLI_COUNTS)

        offenders = [
            f"{logical}: {marker}"
            for logical, text in _user_markdown()
            for marker in UNRESOLVED_MARKERS
            if marker in text
        ]
        self.assertEqual(offenders, [])

        missing_preamble = [
            logical
            for logical, block in _command_blocks()
            if any(f"/scripts/{cli}" in block for cli in CLI_PACKAGES)
            and CANONICAL_ROOT not in block
        ]
        self.assertEqual(missing_preamble, [])

    def test_command_tails_and_cli_inventory_are_preserved(self) -> None:
        projection = [
            {"file": logical, "cli": cli, "tail": tail}
            for logical, cli, _program, tail in _commands()
        ]
        digest = hashlib.sha256(
            json.dumps(
                projection,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(digest, COMMAND_TAILS_SHA256)

    def test_install_reports_shell_safe_root_and_commands_run_from_spaced_path(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "isolated home"
            home.mkdir()
            profile = home / ".zshrc"
            profile.write_text("# sentinel\n", encoding="utf-8")
            target = root / "installed skills with spaces and 'quote'"
            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(home),
                    "CODEX_HOME": str(root / "unrelated codex home"),
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )

            installed = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(target)],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            resolved = target.resolve()
            self.assertIn(
                f"export KSRF_SKILLS_ROOT={shlex.quote(str(resolved))}",
                installed.stdout,
            )
            self.assertEqual(profile.read_text(encoding="utf-8"), "# sentinel\n")

            for cli, package in CLI_PACKAGES.items():
                with self.subTest(cli=cli):
                    completed = subprocess.run(
                        [
                            os.environ.get("PYTHON", "python3"),
                            str(resolved / package / "scripts" / cli),
                            "--help",
                        ],
                        cwd=root,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(
                        completed.returncode,
                        0,
                        completed.stdout + completed.stderr,
                    )

    def test_authority_corpus_companion_route_resolves(self) -> None:
        skill = REPO / "skills" / "ksrf-argument-patterns" / "SKILL.md"
        text = skill.read_text(encoding="utf-8")
        target = "references/constitutionalist-authority-corpus.json"
        self.assertIn(target, text)
        self.assertTrue((skill.parent / target).is_file())
        self.assertNotIn(
            "`constitutionalist-authority-corpus.json` — широкий корпус",
            text,
        )

    def test_offline_verifier_rejects_command_and_ambient_repository_routes(
        self,
    ) -> None:
        cases = (
            (
                Path("ksrf-complaint-cycle/references/unresolved-command.md"),
                "python3 <skill-dir>/scripts/tool.py --help\n",
                "unresolved-command-root",
            ),
            (
                Path("ksrf-complaint-cycle/scripts/implicit-repository.py"),
                'repository = Path.home() / "Documents" / "ks_parser"\n',
                "implicit-home-repository-discovery",
            ),
        )
        for relative, content, marker_class in cases:
            with (
                self.subTest(relative=relative),
                tempfile.TemporaryDirectory() as tmp,
            ):
                root = Path(tmp)
                target = root / "skills with spaces"
                installed = subprocess.run(
                    [str(REPO / "install.sh"), "--target", str(target)],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(installed.returncode, 0, installed.stderr)
                mutated = target / relative
                mutated.parent.mkdir(parents=True, exist_ok=True)
                mutated.write_text(content, encoding="utf-8")

                verifier = (
                    target
                    / "ksrf-complaint-cycle"
                    / "scripts"
                    / "verify_offline_self_containment.py"
                )
                completed = subprocess.run(
                    [os.environ.get("PYTHON", "python3"), str(verifier)],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                output = completed.stdout + completed.stderr
                self.assertNotEqual(completed.returncode, 0, output)
                self.assertIn(marker_class, output)


if __name__ == "__main__":
    unittest.main()
