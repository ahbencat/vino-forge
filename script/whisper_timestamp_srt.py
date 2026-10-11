#!/usr/bin/env python3
"""Compatibility entry point for Whisper's internal timestamp pipeline."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from lib.timestamp_asr import main


if __name__ == "__main__":
    main()
