#!/usr/bin/env python3
"""Совместимая оболочка двухфазной сборки filing package."""

from __future__ import annotations

import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
LIB_ROOT = SKILL_ROOT / "lib"
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))

from ksrf.filing.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["release", "build", *sys.argv[1:]]))
