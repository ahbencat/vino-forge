#!/usr/bin/env python3
"""
Whisper 内部时间戳字幕生成工具

使用 Whisper 模型输出的内部 chunk 时间戳（而非 VAD 段边界）生成 SRT，
提供更精确的字幕时间轴。

对比 video_to_subtitle.py 的 VAD 边界模式：
  - 本脚本：每段音频交给 Whisper 后，取其内部各子句的时间戳
  - VAD 模式：整个 VAD 段作为一个字幕条目

用法:
  python script/whisper_timestamp_srt.py video.mkv
  python script/whisper_timestamp_srt.py audio.wav --audio-only
  python script/whisper_timestamp_srt.py video.mkv --device GPU.1 --language zh --task transcribe
  python script/whisper_timestamp_srt.py video.mkv --vad-merge-gap 1000 --vad-padding 500
"""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from lib.paths import ASR_MODEL_DIR, CACHE_DIR, FFMPEG_PATH, VAD_MODEL_PATH

import numpy as np
import soundfile as sf
import torch
import transformers

transformers.logging.set_verbosity_error()

try:
    from optimum.intel import OVModelForSpeechSeq2Seq
    from transformers import AutoProcessor, pipeline
except ImportError as e:
    print("缺少依赖:", e)
    print("请运行: pip install optimum-intel[openvino] transformers")
    sys.exit(1)


# ============= 配置 =============
DEFAULT_MODEL_DIR = ASR_MODEL_DIR
DEFAULT_DEVICE = "GPU.1"
DEFAULT_TASK = "translate"
DEFAULT_LANGUAGE = "en"


# ============= 音频提取 =============

def extract_audio(video_path, output_wav=None, sample_rate=16000):
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError("视频文件不存在: " + str(video_path))

    if output_wav is None:
        output_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    output_wav = Path(output_wav)

    print("\n[extract_audio]", video_path.name)

    cmd = [
        FFMPEG_PATH,
        "-copyts",
        "-start_at_zero",
        "-i", str(video_path),
        "-map", "0:a:0",
        "-vn",
        "-af", "aresample=async=1:first_pts=0",
        "-ar", str(sample_rate),
        "-ac", "1",
        "-c:a", "pcm_s16le",
        "-f", "wav",
        "-y",
        str(output_wav),
    ]

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start

    if result.returncode != 0:
        print("ffmpeg 错误:\n", result.stderr[-1000:])
        raise RuntimeError("音频提取失败")

    if not output_wav.exists() or output_wav.stat().st_size == 0:
        raise RuntimeError("生成的音频文件为空")

    size_mb = output_wav.stat().st_size / (1024 * 1024)
    print(f"OK ({size_mb:.1f} MB, {elapsed:.1f}s)")

    return str(output_wav)


# ============= 时间戳格式 =============

def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# ============= Silero VAD =============
def load_vad_model():
    if not hasattr(load_vad_model, "model"):
        if not VAD_MODEL_PATH.exists():
            raise FileNotFoundError("VAD 模型文件未找到: " + str(VAD_MODEL_PATH))
        print("\n[load_vad]", VAD_MODEL_PATH.name)
        start = time.time()
        from silero_vad import load_silero_vad, get_speech_timestamps
        load_vad_model.model = load_silero_vad(str(VAD_MODEL_PATH))
        load_vad_model.get_speech_timestamps = get_speech_timestamps
        print("OK ({:.1f}s)".format(time.time() - start))
    return load_vad_model.model, load_vad_model.get_speech_timestamps


def vad_get_segments(audio_path, model, get_speech_timestamps,
                     threshold=0.5, min_speech_duration_ms=250,
                     min_silence_duration_ms=100, merge_gap_ms=500,
                     padding_ms=300):
    audio, sr = sf.read(audio_path, dtype="float32")
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)

    raw_segments = get_speech_timestamps(
        audio, model, sampling_rate=sr,
        threshold=threshold,
        min_speech_duration_ms=min_speech_duration_ms,
        min_silence_duration_ms=min_silence_duration_ms,
        return_seconds=True
    )

    duration = len(audio) / sr

    # 合并间隙小的相邻段
    merged = []
    for seg in raw_segments:
        s, e = seg["start"], seg["end"]
        if merged and s - merged[-1][1] < merge_gap_ms / 1000:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    # 加 padding
    padded = []
    for s, e in merged:
        start = max(0, s - padding_ms / 1000)
        end = min(duration, e + padding_ms / 1000)
        padded.append({"padded_start": start, "padded_end": end,
                       "speech_start": s, "speech_end": e})

    # 拆分超长段（超过 30s 的拆小，避免 Whisper 截断）
    max_duration = 30.0
    split_segments = []
    for seg in padded:
        dur = seg["padded_end"] - seg["padded_start"]
        if dur <= max_duration:
            split_segments.append(seg)
        else:
            n = int(math.ceil(dur / max_duration))
            chunk_len = dur / n
            for i in range(n):
                s = seg["padded_start"] + i * chunk_len
                e = seg["padded_start"] + (i + 1) * chunk_len if i < n - 1 else seg["padded_end"]
                speech_s = max(s, seg["speech_start"])
                speech_e = min(e, seg["speech_end"])
                split_segments.append({
                    "padded_start": s, "padded_end": e,
                    "speech_start": speech_s, "speech_end": speech_e,
                })

    return split_segments, audio, sr, raw_segments


# ============= Whisper 时间戳转录 =============

class WhisperTimestampGenerator:
    """使用 Whisper 内部 chunk 时间戳生成字幕。"""

    def __init__(self, model_dir=DEFAULT_MODEL_DIR, device=DEFAULT_DEVICE,
                 chunk_length_s=30, batch_size=1, cache_dir=CACHE_DIR):
        self.model_dir = model_dir
        self.device = device
        self.chunk_length_s = chunk_length_s
        self.batch_size = batch_size
        self.cache_dir = Path(cache_dir).absolute()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.pipe = None

    def load_model(self):
        print(f"\n[load_model] Whisper Large-v3 (OpenVINO)")
        print(f"   model: {self.model_dir}")
        print(f"   device: {self.device}")
        start = time.time()

        model = OVModelForSpeechSeq2Seq.from_pretrained(
            self.model_dir, device=self.device,
            ov_config={"CACHE_DIR": str(self.cache_dir)},
        )
        processor = AutoProcessor.from_pretrained(self.model_dir)

        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            chunk_length_s=self.chunk_length_s,
            batch_size=self.batch_size,
        )

        print(f"OK ({time.time() - start:.1f}s)")

    def transcribe_with_vad(self, audio_path, task=DEFAULT_TASK, language=DEFAULT_LANGUAGE,
                            vad_threshold=0.5, vad_merge_gap_ms=500, vad_padding_ms=300,
                            num_beams=None):
        """VAD 分段 + Whisper 内部 chunk 时间戳"""
        if not self.pipe:
            self.load_model()

        print(f"\n[transcribe] {Path(audio_path).name}")
        print(f"   task: {task} | language: {language}")

        gen_kwargs = {"task": task}
        if language and language != "auto":
            gen_kwargs["language"] = language
        if num_beams is not None and num_beams > 1:
            gen_kwargs["num_beams"] = num_beams
            gen_kwargs["early_stopping"] = True
        print(f"   generate_kwargs: {gen_kwargs}")

        total_start = time.time()

        # 1. VAD 检测
        vad_model, get_speech_timestamps = load_vad_model()
        vad_start = time.time()
        segments, audio, sr, raw_segments = vad_get_segments(
            audio_path, vad_model, get_speech_timestamps,
            threshold=vad_threshold,
            merge_gap_ms=vad_merge_gap_ms,
            padding_ms=vad_padding_ms,
        )
        print(f"   VAD: {len(segments)} segments (from {len(raw_segments)} raw) [{time.time() - vad_start:.1f}s]")

        if not segments:
            print("WARN: no speech detected by VAD")
            return {"text": "", "chunks": []}

        # 2. 逐段转录，收集 Whisper 内部 chunk 时间戳
        all_chunks = []
        full_text_parts = []
        total_segments = len(segments)

        for idx, seg in enumerate(segments):
            seg_start = seg["padded_start"]
            seg_end = seg["padded_end"]
            speech_start = seg["speech_start"]
            speech_end = seg["speech_end"]

            print(f"\r   [{idx+1}/{total_segments}] {seg_start:.1f}s-{seg_end:.1f}s ({seg_end-seg_start:.1f}s)", end="", flush=True)

            start_sample = int(seg_start * sr)
            end_sample = int(seg_end * sr)
            seg_audio = audio[start_sample:end_sample]

            result = self.pipe(
                {"array": seg_audio, "sampling_rate": int(sr)},
                generate_kwargs=gen_kwargs,
                return_timestamps=True,
            )

            seg_text = result["text"].strip()
            if not seg_text:
                continue

            full_text_parts.append(seg_text)

            # Whisper 内部 chunk 时间戳：相对于 seg_start 偏移
            chunks = result.get("chunks", [])
            if chunks:
                for chunk in chunks:
                    raw_start, raw_end = chunk.get("timestamp", (None, None))
                    if raw_start is None:
                        raw_start = 0
                    if raw_end is None:
                        raw_end = raw_start + 5
                    all_chunks.append({
                        "timestamp": (seg_start + raw_start, seg_start + raw_end),
                        "text": chunk["text"],
                    })
            else:
                # Fallback: 使用 VAD 边界
                if speech_end <= speech_start:
                    continue
                all_chunks.append({
                    "timestamp": (speech_start, speech_end),
                    "text": seg_text,
                })

        elapsed = time.time() - total_start

        result = {
            "text": " ".join(full_text_parts),
            "chunks": all_chunks,
        }

        print(f"\nOK ({elapsed:.1f}s)")
        print(f"   text length: {len(result['text'])}")
        print(f"   segments: {len(all_chunks)}")

        return result


# ============= SRT 写入 =============

def write_srt(chunks, output_path):
    output_path = Path(output_path)
    print(f"\n[SRT write] {output_path}")

    entries = []
    SUBTITLE_GAP = 0.1

    for chunk in chunks:
        start, end = chunk["timestamp"]
        text = chunk["text"].strip()

        if not text:
            continue

        if entries and entries[-1][1] >= start:
            prev_start, prev_end, prev_text = entries[-1]
            entries[-1] = (prev_start, max(prev_start + 0.1, start - SUBTITLE_GAP), prev_text)
        if end <= start:
            end = start + 1.0

        entries.append((start, end, text))

    with open(output_path, "w", encoding="utf-8") as f:
        for idx, (start, end, text) in enumerate(entries, 1):
            f.write(f"{idx}\n")
            f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
            f.write(f"{text}\n\n")

    print(f"OK {len(entries)} segments")
    return str(output_path)


# ============= Main =============

def main():
    parser = argparse.ArgumentParser(
        description="Whisper 内部时间戳字幕生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整流程（视频提取 + 转录）
  python script/whisper_timestamp_srt.py video.mkv

  # 直接处理音频
  python script/whisper_timestamp_srt.py audio.wav --audio-only

  # 指定语言和设备
  python script/whisper_timestamp_srt.py video.mkv --language zh --task transcribe --device GPU.1

  # 自定义 VAD 参数
  python script/whisper_timestamp_srt.py video.mkv --vad-merge-gap 1000 --vad-padding 500

  # 导出 JSON
  python script/whisper_timestamp_srt.py video.mkv --output-json data.json
        """,
    )

    parser.add_argument("input", help="输入视频或音频文件路径")
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR, help="OpenVINO 模型目录")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="推理设备 (默认: GPU.1)")
    parser.add_argument("--task", default=DEFAULT_TASK, choices=["transcribe", "translate"],
                        help="任务 (默认: translate)")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="语言 (默认: en)")
    parser.add_argument("--output", "-o", help="SRT 输出路径 (默认: 同目录同名.srt)")
    parser.add_argument("--output-json", help="额外输出 JSON 文件路径")
    parser.add_argument("--audio-only", action="store_true", help="输入是音频文件，跳过 ffmpeg")
    parser.add_argument("--keep-audio", action="store_true", help="保留中间 wav 文件")
    parser.add_argument("--cache-dir", default=str(CACHE_DIR),
                        help="OpenVINO 模型缓存目录 (默认: ./model_cache)")
    parser.add_argument("--beam-search", action="store_true", dest="beam_search",
                        help="启用 beam search")
    parser.add_argument("--num-beams", type=int, default=5, help="beam 数量 (默认: 5)")
    parser.add_argument("--vad-threshold", type=float, default=0.5, help="VAD 阈值 (默认: 0.5)")
    parser.add_argument("--vad-merge-gap", type=int, default=500, help="VAD 合并间隙 ms (默认: 500)")
    parser.add_argument("--vad-padding", type=int, default=300, help="VAD 填充 ms (默认: 300)")
    parser.add_argument("--chunk-length", type=int, default=30, help="音频分块秒数 (默认: 30)")
    parser.add_argument("--batch-size", type=int, default=1, help="推理批大小 (默认: 1)")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("WHISPER TIMESTAMP SUBTITLE GENERATOR")
    print("=" * 60)

    # 1. 提取音频
    if args.audio_only:
        audio_path = args.input
    else:
        temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        try:
            audio_path = extract_audio(args.input, temp_audio)
        except Exception:
            if not args.keep_audio and Path(temp_audio).exists():
                os.unlink(temp_audio)
            raise

    # 2. 转录（VAD + Whisper 时间戳）
    num_beams = args.num_beams if args.beam_search else None
    generator = WhisperTimestampGenerator(
        model_dir=args.model_dir,
        device=args.device,
        chunk_length_s=args.chunk_length,
        batch_size=args.batch_size,
        cache_dir=args.cache_dir,
    )

    result = generator.transcribe_with_vad(
        audio_path,
        task=args.task,
        language=args.language,
        vad_threshold=args.vad_threshold,
        vad_merge_gap_ms=args.vad_merge_gap,
        vad_padding_ms=args.vad_padding,
        num_beams=num_beams,
    )

    # 3. 写 SRT
    if args.output:
        srt_path = args.output
    else:
        srt_path = Path(args.input).with_suffix(".srt")

    write_srt(result["chunks"], srt_path)

    # 4. 输出 JSON（可选）
    if args.output_json:
        json_path = Path(args.output_json)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[JSON] saved: {json_path}")

    # 5. 清理
    if not args.keep_audio and not args.audio_only and Path(temp_audio).exists():
        try:
            os.unlink(temp_audio)
        except Exception:
            pass

    print(f"\n[DONE] SRT: {srt_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()