#!/usr/bin/env python3
"""Regression tests for the authority-corpus JSON input contract."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "build_constitutionalist_authority_corpus.py"
MIRRORED_TOOL = SKILL_ROOT.parents[1] / "tools" / "build_constitutionalist_authority_corpus.py"


class AuthorityCorpusJsonContractTests(unittest.TestCase):
    def run_entrypoint(
        self, script: Path, zakon_json: str
    ) -> tuple[subprocess.CompletedProcess[str], bool, bool, bool]:
        with tempfile.TemporaryDirectory(prefix="ksrf-authority-json-") as temporary:
            root = Path(temporary)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake_pdftohtml = bin_dir / "pdftohtml"
            fake_pdftohtml.write_text(
                "#!/bin/sh\nprintf '<pdf2xml></pdf2xml>\\n'\n", encoding="utf-8"
            )
            fake_pdftohtml.chmod(fake_pdftohtml.stat().st_mode | stat.S_IXUSR)

            blokhin_text = root / "blokhin.txt"
            sko_pdf = root / "sko.pdf"
            mp_pdf = root / "mp.pdf"
            zakon = root / "zakon.json"
            output_root = root / "output"
            output_json = output_root / "corpus.json"
            output_md = output_root / "corpus.md"
            blokhin_text.write_text("", encoding="utf-8")
            sko_pdf.write_bytes(b"%PDF-1.4\n")
            mp_pdf.write_bytes(b"%PDF-1.4\n")
            zakon.write_text(zakon_json, encoding="utf-8")

            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["PATH"] = str(bin_dir) + os.pathsep + environment.get("PATH", "")
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--blokhin-text",
                    str(blokhin_text),
                    "--sko-index-pdf",
                    str(sko_pdf),
                    "--mp-index-pdf",
                    str(mp_pdf),
                    "--zakon-json",
                    str(zakon),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                    "--as-of",
                    "2026-08-30",
                ],
                capture_output=True,
                text=True,
                env=environment,
                check=False,
            )
            return result, output_root.exists(), output_json.is_file(), output_md.is_file()

    def test_malformed_json_roots_are_controlled_before_output(self) -> None:
        cases = (
            ("top-level-object", "{}\n", "array of objects"),
            ("row-scalar", "[1]\n", "item 0 must be an object"),
        )
        for script in (SCRIPT, MIRRORED_TOOL):
            for label, payload, message in cases:
                with self.subTest(script=script.name, case=label):
                    result, output_exists, json_exists, md_exists = self.run_entrypoint(
                        script, payload
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("ERROR:", result.stderr)
                    self.assertIn(message, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertFalse(output_exists)
                    self.assertFalse(json_exists)
                    self.assertFalse(md_exists)

    def test_empty_json_array_remains_valid(self) -> None:
        for script in (SCRIPT, MIRRORED_TOOL):
            with self.subTest(script=script.name):
                result, output_exists, json_exists, md_exists = self.run_entrypoint(
                    script, "[]\n"
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertTrue(output_exists)
                self.assertTrue(json_exists)
                self.assertTrue(md_exists)
                self.assertIn("authorities_total", result.stdout)


if __name__ == "__main__":
    unittest.main()
