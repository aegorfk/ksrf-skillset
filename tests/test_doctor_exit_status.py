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
KSRF = Path("ksrf-complaint-cycle/scripts/ksrf.py")
DOCTOR = Path("ksrf-complaint-cycle/scripts/ksrf_setup_doctor.py")

DOCTOR_HELP_REQUIRED = (
    "Коды завершения диагностики:",
    (
        "0 — основные возможности готовы (ready) либо работа возможна "
        "с показанными ограничениями (degraded)"
    ),
    (
        "2 — некорректные параметры либо файл описания возможностей "
        "не найден или повреждён"
    ),
    (
        "3 — есть блокирующие пробелы (blocked) либо итоговое состояние "
        "отчёта не распознано"
    ),
    (
        "При коде 3 полный отчёт с причинами и следующим действием остаётся "
        "в стандартном выводе (stdout)"
    ),
    "Диагностика ничего не устанавливает и не исправляет автоматически",
    "Ни один код не подтверждает юридическую готовность жалобы",
    "не разрешает её подачу или передачу документов",
)


def _manifest(*, requirement: str, blocking: bool, path: Path) -> dict[str, object]:
    return {
        "$schema": "capability-manifest.setup-or-matter.v1.json",
        "schema_version": "1.0.0",
        "manifest_id": f"doctor-exit-{requirement}-{str(blocking).lower()}",
        "initial_state": "skills_only",
        "safety": {
            "external_transmission_default": False,
            "automatic_installation": False,
            "automatic_account_creation": False,
            "secret_values_reported": False,
            "network_requires_explicit_authorization": True,
        },
        "profiles": {
            profile: {
                "title": profile,
                "purpose": "Детерминированная проверка кода завершения.",
            }
            for profile in ("basic", "research", "expert")
        },
        "capabilities": [
            {
                "id": "deterministic_directory",
                "title": "Проверяемая локальная папка",
                "purpose": "Проверить согласованность состояния и кода.",
                "privacy": "Содержимое не читается и не передаётся.",
                "cost": "Без оплаты.",
                "dependency": "Папка задаёт детерминированное состояние.",
                "remediation": "Создайте папку и повторите проверку.",
                "profiles": {
                    profile: requirement
                    for profile in ("basic", "research", "expert")
                },
                "dependent_gates": ["test_gate"],
                "blocking_when_missing": blocking,
                "probe": {
                    "kind": "directory",
                    "path": str(path),
                    "write_required": False,
                },
            }
        ],
    }


class DoctorExitStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.installed = cls.root / "installed skills"
        completed = subprocess.run(
            [str(REPO / "install.sh"), "--target", str(cls.installed)],
            cwd=cls.root,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)

        cls.available = cls.root / "available"
        cls.available.mkdir()
        cls.missing = cls.root / "must remain absent"
        cls.manifests: dict[str, Path] = {}
        for state, manifest in (
            (
                "ready",
                _manifest(
                    requirement="required",
                    blocking=True,
                    path=cls.available,
                ),
            ),
            (
                "degraded",
                _manifest(
                    requirement="optional",
                    blocking=False,
                    path=cls.missing,
                ),
            ),
            (
                "blocked",
                _manifest(
                    requirement="required",
                    blocking=True,
                    path=cls.missing,
                ),
            ),
        ):
            path = cls.root / f"{state}.json"
            path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            cls.manifests[state] = path
        cls.invalid_manifest = cls.root / "invalid.json"
        cls.invalid_manifest.write_text("{}\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_ready_and_degraded_reports_remain_successful(self) -> None:
        for state in ("ready", "degraded"):
            for location, skills_root in self._locations():
                for launcher, prefix in self._launchers():
                    with self.subTest(
                        state=state,
                        location=location,
                        launcher=launcher,
                    ):
                        completed = self._run(
                            skills_root / launcher,
                            [
                                *prefix,
                                "--profile",
                                "basic",
                                "--manifest",
                                str(self.manifests[state]),
                                "--json",
                            ],
                        )
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        self.assertEqual(completed.stderr, "")
                        report = json.loads(completed.stdout)
                        self.assertEqual(report["state"], state)
                        self.assertFalse(report["network_probe_authorized"])
                        self.assertFalse(report["external_transmission_performed"])
                        self.assertNotIn("exit_code", report)

    def test_blocked_report_returns_three_from_both_launchers(self) -> None:
        original = self.manifests["blocked"].read_bytes()
        for location, skills_root in self._locations():
            for launcher, prefix in self._launchers():
                with self.subTest(location=location, launcher=launcher):
                    completed = self._run(
                        skills_root / launcher,
                        [
                            *prefix,
                            "--profile",
                            "expert",
                            "--manifest",
                            str(self.manifests["blocked"]),
                            "--json",
                        ],
                    )
                    self.assertEqual(completed.returncode, 3, completed.stderr)
                    self.assertEqual(completed.stderr, "")
                    report = json.loads(completed.stdout)
                    self.assertEqual(report["state"], "blocked")
                    self.assertEqual(
                        report["blocking_capabilities"],
                        ["deterministic_directory"],
                    )
                    self.assertFalse(report["network_probe_authorized"])
                    self.assertFalse(report["external_transmission_performed"])

        self.assertEqual(self.manifests["blocked"].read_bytes(), original)
        self.assertFalse(self.missing.exists())

    def test_human_blocked_report_stays_actionable_on_stdout(self) -> None:
        for location, skills_root in self._locations():
            for launcher, prefix in self._launchers():
                with self.subTest(location=location, launcher=launcher):
                    completed = self._run(
                        skills_root / launcher,
                        [
                            *prefix,
                            "--profile",
                            "basic",
                            "--manifest",
                            str(self.manifests["blocked"]),
                        ],
                    )
                    self.assertEqual(completed.returncode, 3, completed.stderr)
                    self.assertEqual(completed.stderr, "")
                    self.assertIn(
                        "Состояние: есть блокирующие пробелы",
                        completed.stdout,
                    )
                    self.assertIn("Следующее действие:", completed.stdout)

    def test_invalid_manifest_remains_a_usage_error(self) -> None:
        for location, skills_root in self._locations():
            for launcher, prefix in self._launchers():
                with self.subTest(location=location, launcher=launcher):
                    completed = self._run(
                        skills_root / launcher,
                        [*prefix, "--manifest", str(self.invalid_manifest), "--json"],
                    )
                    self.assertEqual(completed.returncode, 2)
                    self.assertEqual(completed.stdout, "")
                    self.assertTrue(completed.stderr.startswith("Ошибка: "))

    def test_non_doctor_start_route_keeps_success_code(self) -> None:
        for location, skills_root in self._locations():
            with self.subTest(location=location):
                completed = self._run(
                    skills_root / KSRF,
                    ["start", "--profile", "basic", "--json"],
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stderr, "")
                self.assertEqual(json.loads(completed.stdout)["state"], "skills_only")

    def test_unrecognized_or_missing_top_level_state_fails_closed(self) -> None:
        probe = (
            "import json\n"
            "from ksrf.filing.cli import _doctor_exit_code\n"
            "states = ('ready', 'degraded', 'blocked', 'unknown', None)\n"
            "print(json.dumps([_doctor_exit_code({'state': value}) "
            "for value in states]))\n"
        )
        for location, skills_root in self._locations():
            with self.subTest(location=location):
                environment = {
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONPATH": str(skills_root / "ksrf-complaint-cycle" / "lib"),
                }
                completed = subprocess.run(
                    [PYTHON, "-c", probe],
                    cwd=self.root,
                    env=environment,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stderr, "")
                self.assertEqual(json.loads(completed.stdout), [0, 0, 3, 3, 3])

    def test_help_explains_exit_contract_from_both_launchers(self) -> None:
        for location, skills_root in self._locations():
            for launcher, prefix in self._launchers():
                for help_flag in ("--help", "-h"):
                    with self.subTest(
                        location=location,
                        launcher=launcher,
                        help_flag=help_flag,
                    ):
                        completed = self._run(
                            skills_root / launcher,
                            [*prefix, help_flag],
                        )
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        self.assertEqual(completed.stderr, "")
                        normalized = " ".join(completed.stdout.split())
                        for required in DOCTOR_HELP_REQUIRED:
                            self.assertIn(required, normalized)

    def test_installed_help_contract_works_with_supported_legacy_python(self) -> None:
        legacy_python = Path("/usr/bin/python3")
        if not legacy_python.is_file():
            self.skipTest("Системный Python не установлен")
        for launcher, prefix in self._launchers():
            with self.subTest(launcher=launcher):
                completed = subprocess.run(
                    [
                        str(legacy_python),
                        str(self.installed / launcher),
                        *prefix,
                        "--help",
                    ],
                    cwd=self.root,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stderr, "")
                normalized = " ".join(completed.stdout.split())
                for required in DOCTOR_HELP_REQUIRED:
                    self.assertIn(required, normalized)

    def _locations(self) -> tuple[tuple[str, Path], ...]:
        return (
            ("source", REPO / "skills"),
            ("installed", self.installed),
        )

    def _launchers(self) -> tuple[tuple[Path, list[str]], ...]:
        return (
            (KSRF, ["doctor"]),
            (DOCTOR, []),
        )

    def _run(
        self,
        script: Path,
        arguments: list[str],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(script), *arguments],
            cwd=self.root,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
