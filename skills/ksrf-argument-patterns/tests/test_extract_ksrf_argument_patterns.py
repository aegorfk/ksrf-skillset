#!/usr/bin/env python3
"""Regression tests for the extract argument-patterns source contract."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "extract_ksrf_argument_patterns.py"
MIRRORED_TOOL = SKILL_ROOT.parents[1] / "tools" / "extract_ksrf_argument_patterns.py"


class ExtractSourceContractTests(unittest.TestCase):
    def test_regular_file_source_is_rejected_before_output(self) -> None:
        for script in (SCRIPT, MIRRORED_TOOL):
            with self.subTest(script=script.name):
                with tempfile.TemporaryDirectory(prefix="ksrf-extract-source-") as temporary:
                    root = Path(temporary)
                    source = root / "source.jsonl"
                    source.write_text("not-json\n", encoding="utf-8")
                    out = root / "analysis"
                    environment = dict(os.environ)
                    environment["PYTHONDONTWRITEBYTECODE"] = "1"

                    result = subprocess.run(
                        [
                            sys.executable,
                            str(script),
                            "--source",
                            str(source),
                            "--out",
                            str(out),
                        ],
                        capture_output=True,
                        text=True,
                        env=environment,
                        check=False,
                    )

                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("ERROR:", result.stderr)
                    self.assertIn("directory", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
