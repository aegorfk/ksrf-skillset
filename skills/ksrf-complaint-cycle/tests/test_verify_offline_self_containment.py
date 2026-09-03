from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
import importlib.util
from io import StringIO
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills" / "ksrf-complaint-cycle" / "scripts"
TOOLS = REPO / "tools"
sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location(
    "ksrf_verify_offline_self_containment_tests",
    SCRIPTS / "verify_offline_self_containment.py",
)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)

sys.path.insert(0, str(TOOLS))
from install_skillset import copy_skillset  # noqa: E402


SCRIPT = SCRIPTS / "verify_offline_self_containment.py"
EXPECTED_HELP = """Использование: verify_offline_self_containment.py [-h | --help]

Проверить без сети автономность установленного набора навыков КС РФ,
который содержит этот скрипт.

Параметры:
  -h, --help  показать эту справку и выйти

Для проверки явно выбранной папки используйте из доверенной копии репозитория:
  ./install.sh --verify --target ПУТЬ
"""
EXPECTED_ARGUMENT_ERROR = """Использование: verify_offline_self_containment.py [-h | --help]
verify_offline_self_containment.py: ошибка: допустим запуск без параметров либо ровно с одним флагом -h или --help.
"""


def _invoke_main(arguments: list[str]) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        return_code = VERIFIER.main(arguments)
    return return_code, stdout.getvalue(), stderr.getvalue()


def _run_script(
    script: Path,
    arguments: list[str],
    *,
    cwd: Path,
    suppress_bytecode_from_environment: bool,
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = ""
    environment.pop("PYTHONPYCACHEPREFIX", None)
    if suppress_bytecode_from_environment:
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
    else:
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _tree_snapshot(root: Path) -> tuple[tuple[object, ...], ...]:
    rows: list[tuple[object, ...]] = []
    for path in [root, *sorted(root.rglob("*"), key=lambda item: item.as_posix())]:
        metadata = path.lstat()
        relative = "." if path == root else path.relative_to(root).as_posix()
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            rows.append((relative, "symlink", mode, os.readlink(path)))
        elif stat.S_ISDIR(metadata.st_mode):
            rows.append((relative, "directory", mode))
        elif stat.S_ISREG(metadata.st_mode):
            rows.append(
                (
                    relative,
                    "file",
                    mode,
                    metadata.st_size,
                    sha256(path.read_bytes()).hexdigest(),
                )
            )
        else:
            rows.append((relative, "special", mode, stat.S_IFMT(metadata.st_mode)))
    return tuple(rows)


class OfflineSelfContainmentPolicyTests(unittest.TestCase):
    def test_module_import_restores_interpreter_bytecode_setting(self) -> None:
        original = sys.dont_write_bytecode
        try:
            for initial in (False, True):
                with self.subTest(initial=initial):
                    sys.dont_write_bytecode = initial
                    spec = importlib.util.spec_from_file_location(
                        f"ksrf_offline_bytecode_restore_{initial}",
                        SCRIPT,
                    )
                    assert spec is not None and spec.loader is not None
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.assertIs(sys.dont_write_bytecode, initial)
        finally:
            sys.dont_write_bytecode = original

    def test_no_argument_main_preserves_exact_success_and_failure_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            skills_root = Path(raw) / "skills"
            for name in ("ksrf-alpha", "ksrf-beta"):
                skill = skills_root / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text("# Test\n", encoding="utf-8")
            core = skills_root / "ksrf-complaint-cycle" / "references" / "core.md"

            with (
                mock.patch.object(VERIFIER, "SKILLS_ROOT", skills_root),
                mock.patch.object(VERIFIER, "CORE", core),
                mock.patch.object(
                    VERIFIER,
                    "validate_offline_self_containment",
                    return_value=[],
                ) as validate,
            ):
                return_code, stdout, stderr = _invoke_main([])

            self.assertEqual(return_code, 0)
            self.assertEqual(
                stdout,
                f"Offline self-containment verified: 2 KSRF skills, core={core}\n",
            )
            self.assertEqual(stderr, "")
            validate.assert_called_once_with(skills_root)

            findings = ["first finding", "second finding"]
            with mock.patch.object(
                VERIFIER,
                "validate_offline_self_containment",
                return_value=findings,
            ) as validate:
                return_code, stdout, stderr = _invoke_main([])

            self.assertEqual(return_code, 1)
            self.assertEqual(
                stdout,
                "Offline self-containment verification failed:\n"
                "- first finding\n"
                "- second finding\n",
            )
            self.assertEqual(stderr, "")
            validate.assert_called_once_with(VERIFIER.SKILLS_ROOT)

    def test_help_and_invalid_arguments_stop_before_validation_or_enumeration(
        self,
    ) -> None:
        for arguments in (["-h"], ["--help"]):
            with self.subTest(arguments=arguments):
                with (
                    mock.patch.object(
                        VERIFIER,
                        "validate_offline_self_containment",
                        side_effect=AssertionError("validation scan was reached"),
                    ) as validate,
                    mock.patch.object(
                        Path,
                        "glob",
                        side_effect=AssertionError("skill enumeration was reached"),
                    ) as enumerate_skills,
                ):
                    return_code, stdout, stderr = _invoke_main(arguments)

                self.assertEqual(return_code, 0)
                self.assertEqual(stdout, EXPECTED_HELP)
                self.assertEqual(stderr, "")
                validate.assert_not_called()
                enumerate_skills.assert_not_called()

        invalid_arguments = (
            ["--strcit"],
            ["unexpected"],
            ["--he"],
            ["--skills-root", "/tmp/other-skills"],
            ["--help", "unexpected"],
            ["--"],
            ["--help", "--help"],
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with (
                    mock.patch.object(
                        VERIFIER,
                        "validate_offline_self_containment",
                        side_effect=AssertionError("validation scan was reached"),
                    ) as validate,
                    mock.patch.object(
                        Path,
                        "glob",
                        side_effect=AssertionError("skill enumeration was reached"),
                    ) as enumerate_skills,
                ):
                    return_code, stdout, stderr = _invoke_main(list(arguments))

                self.assertEqual(return_code, 2)
                self.assertEqual(stdout, "")
                self.assertEqual(stderr, EXPECTED_ARGUMENT_ERROR)
                self.assertNotIn("Offline self-containment", stdout + stderr)
                validate.assert_not_called()
                enumerate_skills.assert_not_called()

    def test_public_subprocess_binds_closed_argument_surface(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            cwd = Path(raw)
            cases = (
                (["-h"], 0, EXPECTED_HELP, ""),
                (["--help"], 0, EXPECTED_HELP, ""),
                (["--strcit"], 2, "", EXPECTED_ARGUMENT_ERROR),
                (["unexpected"], 2, "", EXPECTED_ARGUMENT_ERROR),
                (["--help", "unexpected"], 2, "", EXPECTED_ARGUMENT_ERROR),
                (
                    ["--skills-root", "DOES-NOT-EXIST"],
                    2,
                    "",
                    EXPECTED_ARGUMENT_ERROR,
                ),
            )
            for arguments, expected_code, expected_stdout, expected_stderr in cases:
                with self.subTest(arguments=arguments):
                    completed = _run_script(
                        SCRIPT,
                        arguments,
                        cwd=cwd,
                        suppress_bytecode_from_environment=True,
                    )
                    self.assertEqual(completed.returncode, expected_code)
                    self.assertEqual(completed.stdout, expected_stdout)
                    self.assertEqual(completed.stderr, expected_stderr)

    def test_clean_runtime_cli_does_not_generate_bytecode_or_other_artifacts(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed_root = root / "installed-skills"
            copy_skillset(REPO / "skills", installed_root)
            script = (
                installed_root
                / "ksrf-complaint-cycle"
                / "scripts"
                / "verify_offline_self_containment.py"
            )
            foreign_cwd = root / "foreign-cwd"
            foreign_cwd.mkdir()
            before = _tree_snapshot(installed_root)
            resolved_installed_root = installed_root.resolve()
            healthy_success = (
                "Offline self-containment verified: 15 KSRF skills, "
                f"core={resolved_installed_root / 'ksrf-complaint-cycle' / 'references' / 'offline-practice-core.md'}\n"
            )
            cases = (
                (["--help"], 0, EXPECTED_HELP, ""),
                (["--strcit"], 2, "", EXPECTED_ARGUMENT_ERROR),
                ([], 0, healthy_success, ""),
            )
            for arguments, expected_code, expected_stdout, expected_stderr in cases:
                with self.subTest(arguments=arguments):
                    completed = _run_script(
                        script,
                        arguments,
                        cwd=foreign_cwd,
                        suppress_bytecode_from_environment=False,
                    )
                    self.assertEqual(completed.returncode, expected_code)
                    self.assertEqual(completed.stdout, expected_stdout)
                    self.assertEqual(completed.stderr, expected_stderr)
                    self.assertEqual(before, _tree_snapshot(installed_root))

            core = (
                installed_root
                / "ksrf-complaint-cycle"
                / "references"
                / "offline-practice-core.md"
            )
            core.unlink()
            broken_before = _tree_snapshot(installed_root)
            for arguments, expected_code in ((["--help"], 0), (["--wat"], 2)):
                with self.subTest(broken_arguments=arguments):
                    completed = _run_script(
                        script,
                        arguments,
                        cwd=foreign_cwd,
                        suppress_bytecode_from_environment=False,
                    )
                    self.assertEqual(completed.returncode, expected_code)
                    self.assertEqual(broken_before, _tree_snapshot(installed_root))

            completed = _run_script(
                script,
                [],
                cwd=foreign_cwd,
                suppress_bytecode_from_environment=False,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertTrue(
                completed.stdout.startswith(
                    "Offline self-containment verification failed:\n"
                )
            )
            self.assertEqual(completed.stderr, "")
            self.assertEqual(broken_before, _tree_snapshot(installed_root))

    def test_repo_side_policy_accepts_explicit_runtime_root(self) -> None:
        errors = VERIFIER.validate_offline_self_containment(REPO / "skills")

        self.assertEqual(errors, [])

    def test_repo_side_policy_checks_explicit_target_instead_of_script_location(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            shutil.copytree(REPO / "skills", target)
            core = (
                target
                / "ksrf-complaint-cycle"
                / "references"
                / "offline-practice-core.md"
            )
            text = core.read_text(encoding="utf-8")
            core.write_text(
                text.replace("## 0. Контракт автономности", "## Удалено", 1),
                encoding="utf-8",
            )

            errors = VERIFIER.validate_offline_self_containment(target)

        self.assertTrue(
            any("core missing required section" in error for error in errors),
            errors,
        )

    def test_runtime_coordinate_gate_uses_only_logical_payload_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            external_root = (
                Path(raw)
                / "Users"
                / "alice"
                / "OpenSpecChange-external-root"
            )
            skill = external_root / "ksrf-clean"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text("# Чистый runtime\n", encoding="utf-8")
            (skill / "references" / "guide.md").write_text(
                "Пользовательская инструкция без локальных координат.\n",
                encoding="utf-8",
            )
            errors: list[str] = []

            VERIFIER.validate_runtime_payload_coordinates(errors, [skill])

        self.assertEqual(errors, [])

    def test_runtime_coordinate_gate_scans_logical_path_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            skill = Path(raw) / "ksrf-clean"
            (skill / "references").mkdir(parents=True)
            (skill / "references" / "OpenSpecChange-binary.pdf").write_bytes(
                b"\xff\xfe\x00"
            )
            errors: list[str] = []

            VERIFIER.validate_runtime_payload_coordinates(errors, [skill])

        self.assertEqual(len(errors), 1)
        self.assertIn("runtime maintainer workflow", errors[0])
        self.assertIn("ksrf-clean/references/OpenSpecChange-binary.pdf", errors[0])


if __name__ == "__main__":
    unittest.main()
