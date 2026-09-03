#!/usr/bin/env python3
"""Portable entry point for the judicial-meaning research bundle."""

from __future__ import annotations

import sys
from pathlib import Path


# Public read-only commands must not mutate a clean installed skill with bytecode
# caches merely because the user asked for help or ran a quality gate.
sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB = SKILL_ROOT / "lib"
LIB_PATH = str(LIB)
sys.path[:] = [entry for entry in sys.path if entry != LIB_PATH]
sys.path.insert(0, LIB_PATH)

from judicial_meaning.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
