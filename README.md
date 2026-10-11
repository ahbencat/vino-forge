# VinoForge — OpenVINO App Series

**English** | [简体中文](README.zh-CN.md)

A monorepo for a series of OpenVINO-accelerated applications on Intel hardware.

**Current apps:**

| App | Description |
|-----|-------------|
| [vino-sub-gen](apps/vino-sub-gen/) | Video/audio subtitle generation & translation (Whisper + Hy-MT2) |

Each app lives under `apps/` and shares common infrastructure from `libs/ov_kit/`.

Developed and measured on an Intel Core Ultra 7 265K + Arc B580.

## Pipeline

```
video.mkv
    |  ffmpeg  ->  16 kHz mono wav
    v
Silero VAD  ->  speech segments
    |
    |  Whisper Large-v3 FP16 (OpenVINO, Arc GPU)
    v
source.srt
    |
    |  Hy-MT2 / Hunyuan Dense V1 (OpenVINO)
    v
translated.srt
```

Whisper's own `translate` task only ever emits English. For any other target language you must transcribe first and then translate — that is the reason for the two stages.

## Repository layout

```
vino-forge/                     ← monorepo root
  libs/ov_kit/                  ← shared: paths, device enumeration
  apps/vino-sub-gen/            ← video subtitle generation & translation
    lib/                        ← ASR, translation, timestamp modules
    script/                     ← CLI entry points, batch driver
    gui/                        ← PySide6 GUI
    tool/model_conversion/      ← Hunyuan → OpenVINO export tools
    models/                     ← model cards (weights not committed)
  models/                       ← shared model weights (not committed)
```

## Components (vino-sub-gen)

| Path | Role |
|------|------|
| `apps/vino-sub-gen/script/generate_and_translate.py` | One-shot driver: video/audio → source SRT → translated SRT |
| `apps/vino-sub-gen/script/batch_generate.py` | Batch CLI: scan a folder and process each video |
| `apps/vino-sub-gen/script/video_to_subtitle.py`, `apps/vino-sub-gen/script/translate_srt.py` | CLI entry points for transcription and translation |
| `apps/vino-sub-gen/script/whisper_timestamp_srt.py` | Optional standalone CLI for Whisper internal timestamps |
| `apps/vino-sub-gen/gui/gui_app.py` | Optional PySide6 GUI for single-file and in-process batch processing |
| `apps/vino-sub-gen/lib/` | Reusable ASR, translation, and timestamp modules |
| `apps/vino-sub-gen/tool/model_conversion/` | Hunyuan → OpenVINO export (FP16 / INT4) + inference checks |
| `models/` | Model cards; download the weights into these folders |

## Requirements

Python 3.10, plus [ffmpeg](https://ffmpeg.org/) available on `PATH` (or point the `FFMPEG_PATH` environment variable at the binary).

```bash
pip install -r requirements.txt
```

Or assemble the environment manually:

```bash
conda create -n py310_openvino python=3.10
conda activate py310_openvino

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install openvino nncf optimum[openvino] transformers soundfile silero-vad
```

`nncf` is only needed for INT4 quantization — skip it if you only download pre-converted models.

## Getting started

### 1. Get the models

Both models are needed; the weights are not committed to this repository — download or convert them into the `models/` folders so the script defaults find them:

**Whisper Large-v3 FP16 (OpenVINO)** — from [OpenVINO/whisper-large-v3-fp16-ov](https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov) (Apache-2.0):

```bash
hf download OpenVINO/whisper-large-v3-fp16-ov --local-dir models/whisper-large-v3-fp16-ov
```

**Hy-MT2** — download the pre-converted INT4 7B from ModelScope: **[ahbencat/Hy-MT2-7B-ov-int4](https://modelscope.cn/models/ahbencat/Hy-MT2-7B-ov-int4)** (~4.2 GB):

```bash
modelscope download --model ahbencat/Hy-MT2-7B-ov-int4 --local_dir models/Hy-MT2-7B-ov-int4
```

Or convert it yourself (1.8B FP16, or tweaked INT4 settings) — see [`tool/model_conversion/README.md`](tool/model_conversion/README.md).

Any other location works too; point the scripts at it with `--model-dir`.

### 2. Generate subtitles

```bash
# One file: transcribe + translate (defaults: target language 中文)
python apps/vino-sub-gen/script/generate_and_translate.py "input.mkv"

# Known source language, English output
python apps/vino-sub-gen/script/generate_and_translate.py "input.mkv" --src-lang ja --tgt-lang English

# Transcription only, no translation
python apps/vino-sub-gen/script/generate_and_translate.py "input.mkv" --tgt-lang None
```

### 3. Or batch-process a folder

```bash
# Every video under ./videos (recursive, skips ones with an existing .srt)
python apps/vino-sub-gen/script/batch_generate.py "./videos"

# Preview what would run
python apps/vino-sub-gen/script/batch_generate.py "./videos" --dry-run

# Custom languages / devices
python apps/vino-sub-gen/script/batch_generate.py "./videos" --src-lang ja --tgt-lang English --asr-device GPU.1 --trans-device GPU
```

### 4. GUI

Install the optional GUI dependency and launch:

```bash
pip install PySide6
python apps/vino-sub-gen/gui/gui_app.py
```

Choose a media file or folder in the top row. Folder input runs the in-GUI batch pipeline, reusing the Whisper and Hy-MT2 models across files. Batch options include recursive scanning, skipping existing SRTs, and skipping folders marked `-C` / `-CH`. Stop cancels after the current model segment/translation block completes.

### Individual stages

```bash
python apps/vino-sub-gen/script/video_to_subtitle.py "input.mkv" --task transcribe --language zh
python apps/vino-sub-gen/script/translate_srt.py input.srt --tgt-lang 中文
```

Reusable implementations live in `apps/vino-sub-gen/lib/`; the corresponding CLI entry points are in `apps/vino-sub-gen/script/`.

## Performance

Measured on Intel Core Ultra 7 265K + Arc B580.

**Transcription** — Whisper Large-v3 FP16, 5 minutes of audio:

| Mode | Device | batch_size | Time | Segments |
|------|--------|-----------|------|----------|
| VAD (default) | Arc B580 (`GPU.1`) | 1 | 30.0 s | 89 |
| VAD | Arc B580 | 2 | 29.5 s | 89 |
| No VAD | Arc B580 | 2 | 27.7 s | 22 |

A 2.5-hour movie completes in roughly 4.4 minutes and yields 333 subtitle entries.

**Translation** — Hy-MT2:

| Model | Device | Speed | Footprint |
|-------|--------|-------|-----------|
| 1.8B FP16 | Arc B580 | ~30+ tok/s | ~3.5 GB |
| 1.8B FP16 | CPU | ~10 tok/s | ~3.5 GB |
| 7B INT4 | Arc B580 | 7.85 tok/s | ~4.2 GB |
| 7B INT4 | CPU | 2.45 tok/s | ~4.2 GB |

## Devices

`GPU.1` is the discrete Arc GPU and the default for ASR, `GPU.0` is the integrated GPU, and `CPU` / `AUTO` work everywhere.

**NPU does not work for either model.** Intel's NPU requires fully static shapes, while both Whisper and the stateful-KV-cache LLM carry a dynamic sequence-length dimension. Use GPU or CPU.

## Documentation

| Document | Contents |
|----------|----------|
| [`apps/vino-sub-gen/tool/model_conversion/README.md`](apps/vino-sub-gen/tool/model_conversion/README.md) | Hunyuan → OpenVINO conversion and inference guide |
| [`models/SILERO_VAD/README.md`](models/SILERO_VAD/README.md) | Silero VAD model card and recovery steps |
| [`models/whisper-large-v3-fp16-ov/README.md`](models/whisper-large-v3-fp16-ov/README.md) | Whisper model card |
| [`models/Hy-MT2-7B-ov-int4/README.md`](models/Hy-MT2-7B-ov-int4/README.md) | Hy-MT2 INT4 model card |
