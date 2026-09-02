from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills" / "ksrf-complaint-cycle" / "scripts"
sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location(
    "ksrf_verify_offline_self_containment_tests",
    SCRIPTS / "verify_offline_self_containment.py",
)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class OfflineSelfContainmentPolicyTests(unittest.TestCase):
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
