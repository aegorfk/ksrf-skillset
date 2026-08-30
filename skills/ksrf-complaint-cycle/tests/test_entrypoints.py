from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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

    def test_doctor_rejects_unhashable_capability_profile_requirement(self) -> None:
        manifest_path = SKILL_ROOT / "configs" / "ksrf_filing_capabilities.v1.json"
        with manifest_path.open(encoding="utf-8") as handle:
            manifest = json.load(handle)

        for invalid_value in ([], {}):
            with self.subTest(invalid_value=invalid_value), tempfile.TemporaryDirectory() as directory:
                bad_manifest = Path(directory) / "capabilities.json"
                manifest_copy = json.loads(json.dumps(manifest, ensure_ascii=False))
                manifest_copy["capabilities"][0]["profiles"]["basic"] = invalid_value
                with bad_manifest.open("w", encoding="utf-8") as handle:
                    json.dump(manifest_copy, handle, ensure_ascii=False)

                result = subprocess.run(
                    [
                        sys.executable,
                        str(ENTRYPOINT),
                        "doctor",
                        "--manifest",
                        str(bad_manifest),
                        "--json",
                    ],
                    cwd=SKILL_ROOT,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    capture_output=True,
                    text=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("Ошибка:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
