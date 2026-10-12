"""GUI bilingual strings (Chinese / English).

Usage:
    from gui.i18n import T, get_default_lang, set_lang

    button.setText(T("start"))          # UI label by key
    self._log(T("model_loaded"))        # log line by key

Language is chosen once at startup from QSettings ("gui_lang"), falling
back to the OS locale. Changing language requires restarting the GUI.
"""

from __future__ import annotations

_LANG = "zh"

STRINGS: dict[str, dict[str, str]] = {
    # ---- dialogs ----
    "vad_title": {"zh": "VAD 设置", "en": "VAD Settings"},
    "vad_threshold": {"zh": "判定阈值:", "en": "Threshold:"},
    "vad_merge_gap": {"zh": "合并间隙:", "en": "Merge gap:"},
    "vad_padding": {"zh": "段前后填充:", "en": "Segment padding:"},
    "vad_use_whisper_ts": {"zh": "使用 Whisper 内部时间戳", "en": "Use Whisper internal timestamps"},
    "beam_title": {"zh": "Beam Search 设置", "en": "Beam Search Settings"},
    "beam_count": {"zh": "Beam 数量:", "en": "Beam count:"},
    "beam_hint": {"zh": "数量越大越精确，但速度越慢（默认 5）", "en": "Higher is more accurate but slower (default 5)"},
    # ---- top input row ----
    "input_group": {"zh": "输入文件", "en": "Input File"},
    "input_placeholder": {"zh": "选择视频/音频文件，或文件夹进行批量处理...", "en": "Select a video/audio file, or a folder for batch processing..."},
    "browse": {"zh": "浏览...", "en": "Browse..."},
    "browse_folder": {"zh": "文件夹...", "en": "Folder..."},
    # ---- model & device card ----
    "model_group": {"zh": "模型与设备", "en": "Model & Device"},
    "model_dir": {"zh": "模型目录:", "en": "Model dir:"},
    "asr_device": {"zh": "推理设备:", "en": "ASR device:"},
    "cache_dir": {"zh": "缓存目录:", "en": "Cache dir:"},
    "task": {"zh": "任务:", "en": "Task:"},
    "src_lang": {"zh": "源语言:", "en": "Source lang:"},
    "batch_size": {"zh": "批大小:", "en": "Batch size:"},
    "gui_lang": {"zh": "界面语言:", "en": "Language:"},
    "lang_apply": {"zh": "应用并重启", "en": "Apply & Restart"},
    "lang_apply_hint": {"zh": "点击后自动重启应用", "en": "Restarts the app automatically"},
    "warn_busy": {"zh": "正在处理中，请先停止当前任务再切换语言", "en": "Processing in progress — stop the current task before switching language"},
    # ---- advanced card ----
    "adv_group": {"zh": "高级选项", "en": "Advanced"},
    "vad_row": {"zh": "语音检测:", "en": "VAD:"},
    "vad_enable": {"zh": "启用 VAD", "en": "Enable VAD"},
    "settings_btn": {"zh": "设置...", "en": "Settings..."},
    "beam_row": {"zh": "解码方式:", "en": "Decoding:"},
    "beam_enable": {"zh": "启用 Beam Search", "en": "Enable Beam Search"},
    "other_row": {"zh": "其他:", "en": "Other:"},
    "keep_audio": {"zh": "保留中间音频文件", "en": "Keep intermediate audio"},
    "batch_row": {"zh": "批量:", "en": "Batch:"},
    "batch_skip_existing": {"zh": "跳过已有字幕", "en": "Skip existing"},
    "batch_recursive": {"zh": "递归子目录", "en": "Recursive"},
    "batch_skip_marker": {"zh": "跳过 -C/-CH 目录", "en": "Skip -C/-CH"},
    # ---- output card ----
    "output_group": {"zh": "输出", "en": "Output"},
    "output_placeholder": {"zh": "默认: 与输入文件同名 .srt", "en": "Default: same name as input (.srt)"},
    # ---- translation card ----
    "translate_group": {"zh": "字幕翻译 (Hy-MT2 OpenVINO)", "en": "Subtitle Translation (Hy-MT2 OpenVINO)"},
    "translate_enable": {"zh": "转录后启用翻译", "en": "Enable translation"},
    "translate_model": {"zh": "翻译模型:", "en": "MT model:"},
    "translate_device": {"zh": "翻译设备:", "en": "MT device:"},
    "tgt_lang": {"zh": "目标语言:", "en": "Target lang:"},
    "merge_chars": {"zh": "合并字符数:", "en": "Merge chars:"},
    "translate_line_by_line": {"zh": "逐条翻译", "en": "Line by line"},
    # ---- buttons ----
    "start": {"zh": "开 始", "en": "Start"},
    "stop": {"zh": "停 止", "en": "Stop"},
    # ---- status ----
    "ready": {"zh": "就绪", "en": "Ready"},
    "done": {"zh": "完成", "en": "Done"},
    "stopped": {"zh": "已停止", "en": "Stopped"},
    "failed": {"zh": "失败", "en": "Failed"},
    "log_group": {"zh": "日志", "en": "Log"},
    # ---- file dialogs ----
    "dlg_open_media": {"zh": "选择视频或音频文件", "en": "Select a video or audio file"},
    "dlg_media_filter": {
        "zh": "视频文件 (*.mp4 *.mkv *.avi *.mov *.flv *.wmv);;音频文件 (*.wav *.mp3 *.flac *.m4a *.ogg);;所有文件 (*.*)",
        "en": "Video files (*.mp4 *.mkv *.avi *.mov *.flv *.wmv);;Audio files (*.wav *.mp3 *.flac *.m4a *.ogg);;All files (*.*)",
    },
    "dlg_open_folder": {"zh": "选择视频文件夹（批量处理）", "en": "Select a video folder (batch)"},
    "dlg_model_dir": {"zh": "选择模型目录", "en": "Select model directory"},
    "dlg_translate_model_dir": {"zh": "选择翻译模型目录", "en": "Select translation model directory"},
    "dlg_save_srt": {"zh": "保存字幕文件", "en": "Save subtitle file"},
    "dlg_srt_filter": {"zh": "SRT 字幕 (*.srt);;所有文件 (*.*)", "en": "SRT subtitles (*.srt);;All files (*.*)"},
    # ---- message boxes ----
    "warn_title": {"zh": "警告", "en": "Warning"},
    "warn_no_input": {"zh": "请选择输入文件或文件夹", "en": "Please select an input file or folder"},
    "warn_no_path": {"zh": "输入路径不存在", "en": "Input path does not exist"},
    "warn_batch_output": {"zh": "批量处理会为每个输入文件生成同名 SRT，请清空自定义输出路径", "en": "Batch mode writes one SRT per input file; please clear the custom output path"},
    "done_title": {"zh": "完成", "en": "Done"},
    "done_msg": {"zh": "字幕生成成功!\n\n保存位置:\n", "en": "Subtitles generated!\n\nSaved to:\n"},
    "error_title": {"zh": "错误", "en": "Error"},
    "error_msg": {"zh": "处理失败:\n", "en": "Processing failed:\n"},
    # ---- worker log lines ----
    "log_stopped": {"zh": "\n[INFO] 已停止", "en": "\n[INFO] Stopped"},
    "log_stopping": {"zh": "[INFO] 正在停止...", "en": "[INFO] Stopping..."},
    "log_batch": {"zh": "批量处理: ", "en": "Batch: "},
    "log_found_media": {"zh": "  找到 {n} 个媒体文件", "en": "  Found {n} media files"},
    "log_no_media": {"zh": "[提示] 目录下没有可处理的媒体文件", "en": "[Hint] No processable media files in folder"},
    "log_no_media_msg": {"zh": "没有可处理的媒体文件", "en": "No processable media files"},
    "log_skip_marker": {"zh": "[跳过] 文件夹含 -C/-CH 标记: ", "en": "[Skip] Folder has -C/-CH marker: "},
    "log_skip_existing": {"zh": "[跳过] 字幕已存在: ", "en": "[Skip] SRT already exists: "},
    "log_batch_all_skipped": {"zh": "批量处理完成: 成功 0 | 失败 0 | 跳过 {skipped} | 总计 {total}", "en": "Batch done: success 0 | failed 0 | skipped {skipped} | total {total}"},
    "log_batch_all_skipped_msg": {"zh": "批量完成: 成功 0 / 失败 0 / 跳过 {skipped} (共 {total})", "en": "Batch done: success 0 / failed 0 / skipped {skipped} (of {total})"},
    "stage_load_model": {"zh": "加载模型...", "en": "Loading model..."},
    "log_load_model": {"zh": "加载模型: ", "en": "Loading model: "},
    "log_device": {"zh": "设备: ", "en": "Device: "},
    "log_model_loaded": {"zh": "模型加载完成", "en": "Model loaded"},
    "log_failed": {"zh": "[失败] ", "en": "[Failed] "},
    "log_batch_done": {"zh": "批量处理完成", "en": "Batch done"},
    "log_total": {"zh": "  总计: {total} | 成功: {ok} | 失败: {fail} | 跳过: {skipped}", "en": "  Total: {total} | Success: {ok} | Failed: {fail} | Skipped: {skipped}"},
    "log_elapsed_min": {"zh": "  总耗时: {s:.1f}s ({m:.1f} min)", "en": "  Elapsed: {s:.1f}s ({m:.1f} min)"},
    "log_failed_files": {"zh": "  失败文件: ", "en": "  Failed files: "},
    "log_batch_done_msg": {"zh": "批量完成: 成功 {ok} / 失败 {fail} / 跳过 {skipped} (共 {total})\n总耗时 {m:.1f} 分钟", "en": "Batch done: success {ok} / failed {fail} / skipped {skipped} (of {total})\nElapsed {m:.1f} min"},
    "log_elapsed_s": {"zh": "  总耗时: {s:.1f}s", "en": "  Elapsed: {s:.1f}s"},
    "log_audio_input": {"zh": "输入是音频文件: ", "en": "Audio input: "},
    "stage_extract_audio": {"zh": "提取音频...", "en": "Extracting audio..."},
    "log_audio_done": {"zh": "  音频提取完成: ", "en": "  Audio extracted: "},
    "stage_transcribe": {"zh": "转录中...", "en": "Transcribing..."},
    "log_task": {"zh": "  任务: ", "en": "  Task: "},
    "log_lang": {"zh": "  语言: ", "en": "  Language: "},
    "log_vad_on": {"zh": "  VAD: 启用", "en": "  VAD: enabled"},
    "log_vad_off": {"zh": "  VAD: 禁用", "en": "  VAD: disabled"},
    "log_use_vad": {"zh": "  使用 VAD 模式...", "en": "  Using VAD mode..."},
    "log_use_direct": {"zh": "  使用直接转录模式...", "en": "  Using direct transcription..."},
    "log_transcribe_done": {"zh": "\n[transcribe_done] 耗时: {s:.1f}s", "en": "\n[transcribe_done] Elapsed: {s:.1f}s"},
    "log_text_len": {"zh": "  文本长度: {n}", "en": "  Text length: {n}"},
    "log_chunk_count": {"zh": "  分段数: {n}", "en": "  Chunk count: {n}"},
    "stage_make_srt": {"zh": "生成字幕...", "en": "Writing subtitles..."},
    "log_srt_saved": {"zh": "  SRT 已保存: ", "en": "  SRT saved: "},
    "stage_translate": {"zh": "翻译字幕...", "en": "Translating..."},
    "log_translate_failed": {"zh": "[翻译失败] ", "en": "[Translation failed] "},
    "log_done_src": {"zh": "[完成] 原字幕: ", "en": "[Done] Source SRT: "},
    "log_done_translated": {"zh": "[完成] 翻译字幕: ", "en": "[Done] Translated SRT: "},
    "log_done_srt": {"zh": "[完成] SRT 已保存: ", "en": "[Done] SRT saved: "},
    "log_file_elapsed": {"zh": "  本文件耗时: {s:.1f}s", "en": "  File elapsed: {s:.1f}s"},
    "log_mt_model": {"zh": "  模型: ", "en": "  Model: "},
    "log_mt_device": {"zh": "  设备: ", "en": "  Device: "},
    "log_tgt_lang": {"zh": "  目标语言: ", "en": "  Target language: "},
    "log_no_segments": {"zh": "  没有可翻译的字幕", "en": "  No translatable subtitles"},
    "log_segment_count": {"zh": "  共 {n} 条字幕", "en": "  {n} subtitle(s)"},
    "log_translate_elapsed": {"zh": "  翻译耗时: {s:.1f}s", "en": "  Translation elapsed: {s:.1f}s"},
    "log_translated_saved": {"zh": "  翻译字幕已保存: ", "en": "  Translated SRT saved: "},
    "log_start": {"zh": "开始处理...", "en": "Starting..."},
    "log_success_saved": {"zh": "\n[成功] 字幕已保存: ", "en": "\n[Success] Subtitles saved: "},
    "log_failed_msg": {"zh": "\n[失败] ", "en": "\n[Failed] "},
}


def set_lang(lang: str) -> None:
    """Set the active language ('zh' or 'en')."""
    global _LANG
    _LANG = "en" if lang == "en" else "zh"


def current_lang() -> str:
    """Return the active language code."""
    return _LANG


def T(key: str, **kwargs) -> str:
    """Look up a UI/log string by key, with optional .format() kwargs."""
    text = STRINGS.get(key, {}).get(_LANG, key)
    return text.format(**kwargs) if kwargs else text


def get_default_lang() -> str:
    """Guess initial language from the OS locale (zh* -> zh, else en)."""
    try:
        from PySide6.QtCore import QLocale

        if QLocale().name().lower().startswith("zh"):
            return "zh"
    except Exception:
        pass
    return "en"
