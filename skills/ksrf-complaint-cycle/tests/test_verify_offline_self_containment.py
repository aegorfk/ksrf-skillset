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


if __name__ == "__main__":
    unittest.main()
