from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = SKILL_ROOT / "scripts" / "ksrf.py"


class EntrypointTests(unittest.TestCase):
    def test_ksrf_entrypoint_starts_without_a_src_package(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, str(ENTRYPOINT), "start", "--profile", "basic", "--json"],
            cwd=SKILL_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["state"], "skills_only")
        self.assertFalse(payload["external_transmission_performed"])


if __name__ == "__main__":
    unittest.main()
