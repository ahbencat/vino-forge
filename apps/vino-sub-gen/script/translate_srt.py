#!/usr/bin/env python3
"""CLI entry point for SRT translation."""

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT / "libs"))
sys.path.insert(0, str(APP_ROOT))

from lib.translate import main


if __name__ == "__main__":
    main()
