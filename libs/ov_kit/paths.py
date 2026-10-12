"""Repository paths shared by CLI and GUI entry points."""

import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # PyInstaller: models/cache 在 exe 同级目录，而非解包临时目录
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT_DIR / "models"
ASR_MODEL_DIR = MODEL_DIR / "whisper-large-v3-fp16-ov"
TRANSLATION_MODEL_DIR = MODEL_DIR / "Hy-MT2-7B-ov-int4"
VAD_MODEL_PATH = MODEL_DIR / "SILERO_VAD" / "silero_vad.onnx"
TIMESTAMP_MODEL_DIR = MODEL_DIR / "Hy-MT2-1.8B-ov-optimum"
CACHE_DIR = ROOT_DIR / "model_cache"
SOURCE_MODEL_ROOT = ROOT_DIR.parent
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")
