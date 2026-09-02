from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"
SCHEMAS = (
    "admissibility-matrix.v1.schema.json",
    "ksrf-route-recommendation.v1.schema.json",
)
DOCUMENTED_SKILLS = (
    "ksrf-complaint-cycle",
    "ksrf-case-triage",
    "ksrf-explore-arguments",
    "ksrf-complaint-qa",
)


class AdmissibilityRuntimeContractTests(unittest.TestCase):
    def test_cross_skill_guidance_routes_to_executable_contract(self) -> None:
        for package in DOCUMENTED_SKILLS:
            with self.subTest(package=package):
                text = (SKILLS / package / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("admissibility", text.casefold())
                self.assertIn("admissibility-matrix.v1.schema.json", text)
                self.assertIn("ksrf-route-recommendation.v1.schema.json", text)

        artifact_contract = (
            SKILLS
            / "ksrf-explore-arguments"
            / "references"
            / "artifact-contracts.md"
        ).read_text(encoding="utf-8")
        self.assertIn("ksrf admissibility validate", artifact_contract)
        self.assertIn("ksrf admissibility derive", artifact_contract)
        self.assertIn("ksrf admissibility status", artifact_contract)

    def test_cli_help_exposes_russian_admissibility_route(self) -> None:
        completed = subprocess.run(
            [
                "python3",
                str(
                    SKILLS
                    / "ksrf-complaint-cycle"
                    / "scripts"
                    / "ksrf.py"
                ),
                "admissibility",
                "--help",
            ],
            cwd="/tmp",
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("допустим", completed.stdout.casefold())
        self.assertIn("validate", completed.stdout)
        self.assertIn("derive", completed.stdout)
        self.assertIn("status", completed.stdout)

    def test_clean_install_keeps_route_and_schemas_without_source_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "installed skills"
            completed = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(target)],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            for schema in SCHEMAS:
                self.assertTrue(
                    (
                        target
                        / "ksrf-complaint-cycle"
                        / "schemas"
                        / "ksrf_filing"
                        / schema
                    ).is_file()
                )
            self.assertTrue(
                (
                    target
                    / "ksrf-complaint-cycle"
                    / "lib"
                    / "ksrf"
                    / "filing"
                    / "admissibility.py"
                ).is_file()
            )
            self.assertTrue(
                (
                    target
                    / "ksrf-complaint-cycle"
                    / "references"
                    / "admissibility-matrix-template.v1.json"
                ).is_file()
            )
            self.assertFalse(any(target.glob("ksrf-*/evals")))
            self.assertFalse(any(target.glob("ksrf-*/tests")))

    def test_cli_exit_codes_distinguish_blocked_status_from_invalid_input(self) -> None:
        script = SKILLS / "ksrf-complaint-cycle" / "scripts" / "ksrf.py"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "matter"
            initialized = subprocess.run(
                [
                    "python3",
                    str(script),
                    "matter",
                    "init",
                    "--matter-id",
                    "CASE-ADMISSIBILITY-CLI",
                    "--workspace",
                    str(workspace),
                    "--json",
                ],
                cwd="/tmp",
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)

            status = subprocess.run(
                [
                    "python3",
                    str(script),
                    "admissibility",
                    "status",
                    "--workspace",
                    str(workspace),
                    "--json",
                ],
                cwd="/tmp",
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(status.returncode, 3, status.stderr)
            self.assertEqual(json.loads(status.stdout)["state"], "blocked")

            invalid_path = Path(tmp) / "invalid-matrix.json"
            invalid_path.write_text(
                json.dumps({"schema_version": "1.0.0"}),
                encoding="utf-8",
            )
            invalid = subprocess.run(
                [
                    "python3",
                    str(script),
                    "admissibility",
                    "validate",
                    "--workspace",
                    str(workspace),
                    "--payload",
                    str(invalid_path),
                    "--json",
                ],
                cwd="/tmp",
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(invalid.returncode, 2, invalid.stderr)
            self.assertIn("Матрица допустимости некорректна", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
