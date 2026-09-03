from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
COMPLAINT_SKILL = REPO / "skills" / "ksrf-complaint-cycle"
JUDICIAL_SKILL = REPO / "skills" / "ksrf-cassation-judicial-meaning"
LAUNCHERS = (
    (
        "judicial_meaning",
        JUDICIAL_SKILL / "scripts" / "judicial_meaning.py",
        JUDICIAL_SKILL / "lib",
        "judicial_meaning",
    ),
    (
        "ksrf",
        COMPLAINT_SKILL / "scripts" / "ksrf.py",
        COMPLAINT_SKILL / "lib",
        "ksrf",
    ),
    (
        "ksrf_filing_pack",
        COMPLAINT_SKILL / "scripts" / "ksrf_filing_pack.py",
        COMPLAINT_SKILL / "lib",
        "ksrf",
    ),
    (
        "ksrf_setup_doctor",
        COMPLAINT_SKILL / "scripts" / "ksrf_setup_doctor.py",
        COMPLAINT_SKILL / "lib",
        "ksrf",
    ),
)


class RuntimeLauncherImportPrecedenceTests(unittest.TestCase):
    def test_bundled_package_wins_when_its_lib_is_already_on_pythonpath(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temporary_root = Path(temp_dir)
            poison_root = temporary_root / "ambient"
            run_from = temporary_root / "outside-skill"
            run_from.mkdir()
            for package in {row[3] for row in LAUNCHERS}:
                package_root = poison_root / package
                package_root.mkdir(parents=True)
                (package_root / "__init__.py").write_text(
                    f'raise RuntimeError("ambient {package} package imported")\n',
                    encoding="utf-8",
                )

            for name, script, bundled_lib, _package in LAUNCHERS:
                with self.subTest(launcher=name):
                    env = dict(os.environ)
                    env["PYTHONPATH"] = os.pathsep.join(
                        (str(poison_root), str(bundled_lib))
                    )
                    completed = subprocess.run(
                        [sys.executable, str(script), "--help"],
                        cwd=run_from,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(0, completed.returncode, completed.stderr)
                    self.assertEqual("", completed.stderr)
                    self.assertIn("использование:", completed.stdout.casefold())
                    self.assertNotIn("ambient ", completed.stdout.casefold())

    def test_bootstrap_keeps_only_one_owned_lib_and_preserves_other_paths(self):
        probe = "\n".join(
            (
                "import json, runpy, sys",
                "before = list(sys.path)",
                "runpy.run_path(sys.argv[1], run_name='launcher_probe')",
                "print(json.dumps({'before': before, 'after': sys.path}))",
            )
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temporary_root = Path(temp_dir)
            poison_root = temporary_root / "ambient-first"
            ambient_last = temporary_root / "ambient-last"
            run_from = temporary_root / "outside-skill"
            ambient_last.mkdir()
            run_from.mkdir()
            for package in {row[3] for row in LAUNCHERS}:
                package_root = poison_root / package
                package_root.mkdir(parents=True)
                (package_root / "__init__.py").write_text(
                    f'raise RuntimeError("ambient {package} package imported")\n',
                    encoding="utf-8",
                )

            for name, script, bundled_lib, _package in LAUNCHERS:
                with self.subTest(launcher=name):
                    env = dict(os.environ)
                    owned_path = str(bundled_lib)
                    env["PYTHONPATH"] = os.pathsep.join(
                        (str(poison_root), owned_path, str(ambient_last), owned_path)
                    )
                    completed = subprocess.run(
                        [sys.executable, "-c", probe, str(script)],
                        cwd=run_from,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(0, completed.returncode, completed.stderr)
                    payload = json.loads(completed.stdout)
                    before = payload["before"]
                    after = payload["after"]
                    self.assertEqual(owned_path, after[0])
                    self.assertEqual(1, after.count(owned_path))
                    self.assertEqual(
                        [entry for entry in before if entry != owned_path],
                        after[1:],
                    )

    def test_clean_installed_launchers_ignore_ambient_package_collision(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temporary_root = Path(temp_dir)
            target = temporary_root / "installed-skills"
            installed = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(target)],
                cwd=temporary_root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, installed.returncode, installed.stderr)
            installed_root = target.resolve()

            poison_root = temporary_root / "ambient"
            run_from = temporary_root / "outside-skill"
            run_from.mkdir()
            for package in {row[3] for row in LAUNCHERS}:
                package_root = poison_root / package
                package_root.mkdir(parents=True)
                (package_root / "__init__.py").write_text(
                    f'raise RuntimeError("ambient {package} package imported")\n',
                    encoding="utf-8",
                )

            for name, source_script, source_lib, _package in LAUNCHERS:
                with self.subTest(launcher=name):
                    script = installed_root / source_script.relative_to(REPO / "skills")
                    bundled_lib = installed_root / source_lib.relative_to(REPO / "skills")
                    env = dict(os.environ)
                    env["PYTHONDONTWRITEBYTECODE"] = "1"
                    env["PYTHONPATH"] = os.pathsep.join(
                        (str(poison_root), str(bundled_lib))
                    )
                    completed = subprocess.run(
                        [sys.executable, str(script), "--help"],
                        cwd=run_from,
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(0, completed.returncode, completed.stderr)
                    self.assertEqual("", completed.stderr)
                    self.assertIn("использование:", completed.stdout.casefold())


if __name__ == "__main__":
    unittest.main()
