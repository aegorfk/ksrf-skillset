"""Make bundled tests runnable from an isolated checkout without PYTHONPATH."""

from pathlib import Path
import sys


LIB = Path(__file__).resolve().parents[1] / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))
