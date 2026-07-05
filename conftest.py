"""Ensure the repo root is importable as ``tec`` without an editable install."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
