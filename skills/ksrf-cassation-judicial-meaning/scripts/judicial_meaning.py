#!/usr/bin/env python3
"""Portable entry point for the judicial-meaning research bundle."""

from __future__ import annotations

import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
LIB = SKILL_ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from judicial_meaning.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
