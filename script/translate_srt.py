#!/usr/bin/env python3
"""CLI entry point for SRT translation."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from lib.translate import main


if __name__ == "__main__":
    main()
