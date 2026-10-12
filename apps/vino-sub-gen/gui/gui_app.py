#!/usr/bin/env python3
"""
视频字幕生成工具 - PySide6 GUI 版本
基于 OpenVINO + Whisper Large-v3

直接调用现有的 video_to_subtitle.py 推理代码
"""

import sys
import time
import traceback
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QFileDialog,
    QTextEdit, QProgressBar, QCheckBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QMessageBox, QSplitter,
    QDialog, QDialogButtonBox
)


def _style_form_labels(container, width=72):
    """在容器 widget 上设置样式表，约束其下所有 QLabel 的最小宽度"""
    container.setStyleSheet(f"QLabel {{ min-width: {width}px; }}")
from PySide6.QtCore import (
    QThread, Signal, Qt, QSettings
)
from PySide6.QtGui import QFont, QTextCursor


ROOT_DIR = Path(__file__).resolve().parents[3]
APP_ROOT = ROOT_DIR / "apps" / "vino-sub-gen"
sys.path.insert(0, str(ROOT_DIR / "libs"))
sys.path.insert(0, str(APP_ROOT))

from lib.asr import VideoSubtitleGenerator, extract_audio, write_srt
from ov_kit.devices import populate_device_combo
from ov_kit.paths import CACHE_DIR
from lib.translate import Translator, parse_srt, translate_segments, write_srt as write_translated_srt
from gui.i18n import T, get_default_lang, set_lang


def _default_model_dir(name):
    """优先使用仓库模型；模型权重未放入仓库时兼容本机模型目录。"""
    repo_model = ROOT_DIR / "models" / name
    candidates = (
        repo_model,
        ROOT_DIR.parent / "video_parse_public" / "models" / name,
        ROOT_DIR.parent / name,
    )
    return next((p for p in candidates if (p / "config.json").is_file()), repo_model)


# ==================== 全局样式 ====================

STYLESHEET = """
/* ===== 全局 ===== */
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 9pt;
    color: #2f3b47;
}
QMainWindow, QDialog {
    background-color: #eef1f5;
}

/* ===== 卡片式分组框 ===== */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #dde3ea;
    border-radius: 8px;
    margin-top: 16px;
    padding: 14px 10px 10px 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    top: 3px;
    padding: 0 8px;
    background-color: #eef1f5;
    color: #7a8899;
    font-size: 9pt;
}

/* ===== 输入控件 ===== */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    border: 1px solid #d3dae2;
    border-radius: 5px;
    padding: 4px 8px;
    background-color: #ffffff;
    min-height: 22px;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #3b82f6;
}
QLineEdit:read-only { background-color: #f6f8fa; }
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    border: 1px solid #d3dae2;
    border-radius: 4px;
    background: white;
    selection-background-color: #e8f1fe;
    selection-color: #2f3b47;
    outline: none;
}

/* ===== 按钮 ===== */
QPushButton {
    border: 1px solid #d3dae2;
    border-radius: 5px;
    padding: 5px 14px;
    background-color: #ffffff;
}
QPushButton:hover { background-color: #f2f5f8; border-color: #b9c3ce; }
QPushButton:pressed { background-color: #e6ebf1; }
QPushButton:disabled { color: #a8b1bb; background-color: #f4f6f8; border-color: #e4e9ee; }

#startBtn {
    background-color: #22a55b;
    border: none;
    color: white;
    font-weight: bold;
    font-size: 10pt;
    padding: 9px 28px;
    border-radius: 6px;
}
#startBtn:hover { background-color: #28b866; }
#startBtn:pressed { background-color: #1d9150; }
#startBtn:disabled { background-color: #a9dfc0; }

#stopBtn {
    background-color: #e05252;
    border: none;
    color: white;
    font-weight: bold;
    font-size: 10pt;
    padding: 9px 28px;
    border-radius: 6px;
}
#stopBtn:hover { background-color: #ea6464; }
#stopBtn:pressed { background-color: #c94646; }
#stopBtn:disabled { background-color: #f0b6b6; }

#linkBtn {
    border: 1px solid #d3dae2;
    background-color: #f8fafc;
}

/* ===== 复选框（保留原生勾选图，仅统一间距）===== */
QCheckBox { spacing: 6px; }
QCheckBox:disabled { color: #a8b1bb; }

/* ===== 进度条 ===== */
QProgressBar {
    border: none;
    border-radius: 6px;
    background-color: #dde3ea;
    text-align: center;
    color: #2f3b47;
    font-size: 9pt;
    height: 18px;
}
QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #22a55b, stop:1 #3b82f6);
}

/* ===== 日志区（暗色终端风格）===== */
QTextEdit#logView {
    background-color: #1b2430;
    color: #c9d4e0;
    border: 1px solid #10161d;
    border-radius: 6px;
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 9pt;
    padding: 6px;
}

/* ===== 分割条 ===== */
QSplitter::handle { background-color: #eef1f5; width: 8px; }

/* ===== 滚动条 ===== */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #c3ccd6;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #a9b5c1; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar:horizontal { height: 10px; background: transparent; }
QScrollBar::handle:horizontal { background: #c3ccd6; border-radius: 5px; min-width: 30px; }

/* ===== 状态栏 ===== */
QStatusBar {
    background-color: #e4e9ef;
    color: #7a8899;
    border-top: 1px solid #dde3ea;
}
"""

# ==================== 设置对话框 ====================

class VadSettingsDialog(QDialog):
    """VAD 详细参数设置对话框"""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(T("vad_title"))
        self.setMinimumWidth(380)

        layout = QFormLayout(self)
        layout.setVerticalSpacing(10)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setValue(float(settings.value("vad_threshold", 0.5)))
        layout.addRow(T("vad_threshold"), self.threshold_spin)

        self.merge_spin = QSpinBox()
        self.merge_spin.setRange(0, 2000)
        self.merge_spin.setSuffix(" ms")
        self.merge_spin.setValue(int(settings.value("vad_merge_gap", 500)))
        layout.addRow(T("vad_merge_gap"), self.merge_spin)

        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 1000)
        self.padding_spin.setSuffix(" ms")
        self.padding_spin.setValue(int(settings.value("vad_padding", 300)))
        layout.addRow(T("vad_padding"), self.padding_spin)

        self.whisper_ts_check = QCheckBox(T("vad_use_whisper_ts"))
        self.whisper_ts_check.setChecked(
            settings.value("whisper_timestamps", False, type=bool)
        )
        layout.addRow("", self.whisper_ts_check)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def accept(self):
        self.settings.setValue("vad_threshold", self.threshold_spin.value())
        self.settings.setValue("vad_merge_gap", self.merge_spin.value())
        self.settings.setValue("vad_padding", self.padding_spin.value())
        self.settings.setValue("whisper_timestamps", self.whisper_ts_check.isChecked())
        super().accept()


class BeamSettingsDialog(QDialog):
    """Beam Search 参数设置对话框"""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(T("beam_title"))
        self.setMinimumWidth(350)

        layout = QFormLayout(self)
        layout.setVerticalSpacing(10)

        self.num_beams_spin = QSpinBox()
        self.num_beams_spin.setRange(1, 10)
        self.num_beams_spin.setValue(int(settings.value("num_beams", 5)))
        layout.addRow(T("beam_count"), self.num_beams_spin)

        hint = QLabel(T("beam_hint"))
        hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addRow("", hint)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def accept(self):
        self.settings.setValue("num_beams", self.num_beams_spin.value())
        super().accept()


# ==================== 后台工作线程 ====================

class _LogWriter:
    """将 print 输出转发到日志信号的 writer"""
    def __init__(self, signal, orig=None):
        self._signal = signal
        self._orig = orig
        self._buf = ""

    def write(self, text):
        if self._orig:
            self._orig.write(text)
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self._signal.emit(line.rstrip())

    def flush(self):
        if self._orig:
            self._orig.flush()
        if self._buf.strip():
            self._signal.emit(self._buf.rstrip())
        self._buf = ""

    def isatty(self):
        return False


class _Cancelled(Exception):
    """用户请求停止"""


# 批量扫描的媒体扩展名（与 video_parse_public/batch_generate.py 行为一致）
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpeg", ".mpg"}
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg", ".wma"}


def collect_media(root: Path, recursive: bool = True) -> list[Path]:
    """收集目录下的视频/音频文件（批量处理用）"""
    it = root.rglob("*") if recursive else root.glob("*")
    exts = VIDEO_EXTS | AUDIO_EXTS
    return sorted(p for p in it if p.is_file() and p.suffix.lower() in exts)


def has_skip_marker(media: Path, root: Path) -> bool:
    """路径中的文件夹名含 -C/-CH 标记则跳过（与 batch_generate.py 相同规则）"""
    rel = media.relative_to(root)
    for part in (root.name, *rel.parts[:-1]):
        if any(seg in ("C", "CH") for seg in part.upper().split("-")):
            return True
    return False


class SubtitleWorker(QThread):
    """后台推理线程，避免 GUI 卡顿"""

    # 信号定义
    log_signal = Signal(str)           # 日志输出
    progress_signal = Signal(int)      # 进度 0-100
    stage_signal = Signal(str)         # 当前阶段描述
    finished_signal = Signal(str, str)  # 完成 (状态: success/error/cancelled, 消息)
    chunk_signal = Signal(int, int, str)  # (当前块, 总块数, 块文本)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.generator = None
        self._is_running = True
        self._temp_audio = None
        self._translator = None
        self._translator_key = None
        self._file_index = 0
        self._file_total = 1
        self._is_batch = False

    def run(self):
        """主推理流程"""
        import sys
        orig_stdout, orig_stderr = sys.stdout, sys.stderr
        sys.stdout = _LogWriter(self.log_signal, orig_stdout)
        sys.stderr = _LogWriter(self.log_signal, orig_stderr)
        try:
            self._run_pipeline()
        except _Cancelled:
            self.log_signal.emit(T("log_stopped"))
            self.finished_signal.emit("cancelled", T("stopped"))
        except Exception as e:
            self.log_signal.emit(f"[ERROR] {str(e)}")
            self.log_signal.emit(traceback.format_exc())
            self.finished_signal.emit("error", str(e))
        finally:
            self._cleanup_temp_audio()
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except:
                pass
            sys.stdout, sys.stderr = orig_stdout, orig_stderr

    def stop(self):
        """请求停止"""
        self._is_running = False

    def _check_cancel(self):
        """供推理循环调用的取消钩子，请求停止时抛出 _Cancelled 中止流程"""
        if not self._is_running:
            raise _Cancelled()

    def _progress(self, pct):
        """把单文件内部进度映射到批量总进度"""
        if self._is_batch:
            pct = (self._file_index * 100 + pct) / self._file_total
        self.progress_signal.emit(int(pct))

    def _stage(self, text):
        """更新阶段描述，批量模式下带 [i/N] 前缀"""
        if self._is_batch:
            text = f"[{self._file_index + 1}/{self._file_total}] {text}"
        self.stage_signal.emit(text)

    def _cleanup_temp_audio(self):
        """清理提取的临时 wav（正常结束和取消/异常时都会执行）"""
        if self._temp_audio:
            try:
                Path(self._temp_audio).unlink(missing_ok=True)
            except:
                pass
            self._temp_audio = None

    def _log(self, msg):
        """线程安全地发送日志"""
        self.log_signal.emit(msg)

    def _run_pipeline(self):
        """完整的视频字幕生成流程（支持单文件 / 批量目录）"""
        cfg = self.config
        input_path = Path(cfg["input_path"])
        is_batch = input_path.is_dir()
        self._is_batch = is_batch

        # ===== 1. 构建文件列表 =====
        if is_batch:
            items = collect_media(input_path, cfg.get("batch_recursive", True))
            self._log("=" * 60)
            self._log(T("log_batch") + str(input_path))
            self._log(T("log_found_media", n=len(items)))
        else:
            items = [input_path]
        self._file_total = max(len(items), 1)

        if not items:
            self._log(T("log_no_media"))
            self.finished_signal.emit("success", T("log_no_media_msg"))
            return

        skipped = 0
        queued = []
        for idx, item in enumerate(items):
            self._check_cancel()
            if is_batch and cfg.get("batch_skip_marker") and has_skip_marker(item, input_path):
                self._log(T("log_skip_marker") + str(item.parent))
                skipped += 1
            elif is_batch and cfg.get("batch_skip_existing") and item.with_suffix(".srt").exists():
                self._log(T("log_skip_existing") + item.with_suffix('.srt').name)
                skipped += 1
            else:
                queued.append((idx, item))

        if not queued:
            self._log(T("log_batch_all_skipped", skipped=skipped, total=len(items)))
            self.progress_signal.emit(100)
            self.finished_signal.emit("success", T("log_batch_all_skipped_msg", skipped=skipped, total=len(items)))
            return
        self._file_total = len(items)

        # ===== 2. 加载模型（批量时全程只加载一次） =====
        self._stage(T("stage_load_model"))
        self._log("=" * 60)
        self._log(T("log_load_model") + cfg["model_dir"])
        self._log(T("log_device") + cfg["device"])
        self._progress(2)

        self._check_cancel()
        self.generator = VideoSubtitleGenerator(
            model_dir=cfg["model_dir"],
            device=cfg["device"],
            cache_dir=cfg.get("cache_dir", str(CACHE_DIR))
        )
        self.generator.load_model()
        self.generator.build_pipeline(
            chunk_length_s=cfg.get("chunk_length", 30),
            batch_size=cfg.get("batch_size", 1)
        )
        self._log(T("log_model_loaded"))

        # ===== 3. 逐文件处理 =====
        success, failed = 0, 0
        fail_names = []
        batch_start = time.time()

        for idx, item in queued:
            self._file_index = idx
            self._check_cancel()

            if is_batch:
                self._log("\n" + "=" * 60)
                self._log(f"[{idx + 1}/{len(items)}] {item.name}")
                self._log("=" * 60)

            try:
                self._process_one(item, cfg)
                success += 1
            except _Cancelled:
                raise
            except Exception as e:
                self._log(f"{T('log_failed')}{item.name}: {str(e)}")
                self._log(traceback.format_exc())
                fail_names.append(item.name)
                failed += 1
                self._cleanup_temp_audio()
                if not is_batch:
                    raise

        # ===== 4. 汇总 =====
        elapsed = time.time() - batch_start
        self.progress_signal.emit(100)
        if is_batch:
            self._log("\n" + "=" * 60)
            self._log(T("log_batch_done"))
            self._log(T("log_total", total=len(items), ok=success, fail=failed, skipped=skipped))
            self._log(T("log_elapsed_min", s=elapsed, m=elapsed / 60))
            if fail_names:
                self._log(T("log_failed_files") + ", ".join(fail_names))
            msg = T("log_batch_done_msg", ok=success, fail=failed, skipped=skipped, total=len(items), m=elapsed / 60)
            self.finished_signal.emit("success" if failed == 0 else "error", msg)
        else:
            self._log(T("log_elapsed_s", s=elapsed))

    def _process_one(self, input_path: Path, cfg):
        """处理单个文件：提取音频 → 转录 → 生成 SRT → 翻译"""
        is_audio = input_path.suffix.lower() in AUDIO_EXTS

        # ===== 提取音频 =====
        self._check_cancel()
        if is_audio:
            audio_path = str(input_path)
            self._log(T("log_audio_input") + input_path.name)
        else:
            self._stage(T("stage_extract_audio"))
            self._log("\n[extract_audio] " + input_path.name)
            self._progress(15)

            if cfg.get("keep_audio"):
                audio_path = str(input_path.with_suffix(".wav"))
            else:
                import tempfile
                audio_path = tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ).name
                self._temp_audio = audio_path

            extract_audio(input_path, audio_path)
            self._log(T("log_audio_done") + audio_path)
            self._progress(25)

        # ===== 转录 =====
        self._check_cancel()
        self._stage(T("stage_transcribe"))
        self._log("\n[transcribe] " + Path(audio_path).name)
        self._log(T("log_task") + str(cfg['task']))
        self._log(T("log_lang") + str(cfg['language']))
        self._log(T("log_vad_on") if cfg.get('use_vad', True) else T("log_vad_off"))

        # 计算 num_beams
        num_beams = cfg.get("num_beams") if cfg.get("beam_search") else None

        start_time = time.time()

        if cfg.get("use_vad", True):
            # VAD 模式
            self._log(T("log_use_vad"))
            result = self.generator.transcribe_with_vad(
                audio_path,
                task=cfg["task"],
                language=cfg["language"],
                vad_threshold=cfg.get("vad_threshold", 0.5),
                vad_merge_gap_ms=cfg.get("vad_merge_gap", 500),
                vad_padding_ms=cfg.get("vad_padding", 300),
                chunk_length_s=cfg.get("chunk_length", 30),
                batch_size=cfg.get("batch_size", 1),
                num_beams=num_beams,
                whisper_timestamps=cfg.get("whisper_timestamps", False),
                whisper_start_offset=cfg.get("whisper_start_offset", 0.0),
                whisper_end_offset=cfg.get("whisper_end_offset", 0.0),
                check_cancel=self._check_cancel,
            )
        else:
            # 直接转录
            self._log(T("log_use_direct"))
            result = self.generator.transcribe(
                audio_path,
                task=cfg["task"],
                language=cfg["language"],
                num_beams=num_beams,
                check_cancel=self._check_cancel,
            )

        self._check_cancel()
        elapsed = time.time() - start_time
        self._progress(90)
        self._log(T("log_transcribe_done", s=elapsed))
        self._log(T("log_text_len", n=len(result['text'])))
        self._log(T("log_chunk_count", n=len(result.get('chunks', []))))

        # 发送 chunk 信息
        for i, chunk in enumerate(result.get("chunks", []), 1):
            self._check_cancel()
            text = chunk.get("text", "")[:50]
            self.chunk_signal.emit(i, len(result["chunks"]), text)

        # ===== 生成 SRT =====
        self._stage(T("stage_make_srt"))
        output_path = (
            str(input_path.with_suffix(".srt"))
            if self._is_batch
            else cfg.get("output_path") or str(input_path.with_suffix(".srt"))
        )
        self._log(f"\n[write_srt] {output_path}")

        if "chunks" in result and result["chunks"]:
            srt_path = write_srt(result["chunks"], output_path)
        else:
            srt_path = write_srt(
                [{"timestamp": (0, 0), "text": result["text"]}],
                output_path
            )
        self._log(T("log_srt_saved") + str(srt_path))
        self._progress(95)

        # ===== 翻译 (Hy-MT2) =====
        translated_path = None
        if cfg.get("enable_translate"):
            self._check_cancel()
            self._stage(T("stage_translate"))
            try:
                translated_path = self._translate_srt(srt_path, cfg)
            except _Cancelled:
                raise
            except Exception as e:
                self._log(f"{T('log_translate_failed')}{str(e)}")
                import traceback as _tb
                self._log(_tb.format_exc())
                translated_path = None

        self._log("=" * 60)
        if translated_path:
            self._log(T("log_done_src") + str(srt_path))
            self._log(T("log_done_translated") + str(translated_path))
        else:
            self._log(T("log_done_srt") + str(srt_path))
        self._log(T("log_file_elapsed", s=elapsed))
        self._cleanup_temp_audio()

        if not self._is_batch:
            final_msg = f"{srt_path}\n{translated_path}" if translated_path else srt_path
            self.finished_signal.emit("success", final_msg)

    def _translate_srt(self, srt_path, cfg):
        """使用 Hy-MT2 翻译 SRT 字幕，返回翻译后的路径"""
        srt_path = Path(srt_path)
        translated_path = srt_path.with_stem(srt_path.stem + "_translated")

        self._log(f"\n[translate] {srt_path.name} -> {translated_path.name}")
        self._log(T("log_mt_model") + str(cfg['translate_model_dir']))
        self._log(T("log_mt_device") + str(cfg['translate_device']))
        self._log(T("log_tgt_lang") + str(cfg['tgt_lang']))

        # 解析 SRT
        segments = parse_srt(srt_path)
        if not segments:
            self._log(T("log_no_segments"))
            return None
        self._log(T("log_segment_count", n=len(segments)))

        # 加载翻译模型（批量处理时跨文件复用同一实例）
        key = (str(cfg["translate_model_dir"]), cfg["translate_device"])
        if self._translator is None or self._translator_key != key:
            self._translator = Translator(cfg["translate_model_dir"], cfg["translate_device"])
            self._translator_key = key
        translator = self._translator

        # 翻译（逐条或合并）
        translate_start = time.time()
        translate_segments(
            translator, segments,
            target_lang=cfg["tgt_lang"],
            merge_chars=cfg.get("merge_chars", 0),
            check_cancel=self._check_cancel,
        )
        translate_time = time.time() - translate_start
        self._log(T("log_translate_elapsed", s=translate_time))

        # 写回 SRT
        write_translated_srt(segments, translated_path)
        self._log(T("log_translated_saved") + str(translated_path))

        return str(translated_path)


# ==================== 主窗口 ====================

class MainWindow(QMainWindow):
    # 设置版本：默认值变更时递增，触发清除旧设置
    SETTINGS_VERSION = 2

    def __init__(self):
        super().__init__()
        self.settings = QSettings("VideoSubGen", "GUI")
        # 版本变更时清除旧设置，让新默认值生效
        if self.settings.value("settings_version", 1, type=int) < self.SETTINGS_VERSION:
            self.settings.clear()
            self.settings.setValue("settings_version", self.SETTINGS_VERSION)
        # 界面语言必须在建 UI 之前确定
        set_lang(self.settings.value("gui_lang", get_default_lang()))
        self.worker = None
        self.init_ui()
        self.load_settings()

    def on_gui_lang_changed(self, index):
        """保存界面语言选择（重启 GUI 生效）"""
        self.settings.setValue("gui_lang", self.gui_lang_combo.itemData(index))

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("Vino Sub Gen")
        # 不设置硬编码最小尺寸，让布局的 minimumSizeHint 自行约束，避免窗口缩到布局装不下
        # 默认高度需 ≥ minimumSizeHint（含批量两行复选框后约 830），留 30px 余量
        self.resize(1280, 860)

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 12, 16, 12)

        # ===== 顶部：输入文件路径 =====
        file_group = QGroupBox(T("input_group"))
        file_layout = QHBoxLayout(file_group)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText(T("input_placeholder"))
        self.file_path_edit.setMinimumWidth(400)

        browse_btn = QPushButton(T("browse"))
        browse_btn.clicked.connect(self.browse_file)

        browse_dir_btn = QPushButton(T("browse_folder"))
        browse_dir_btn.clicked.connect(self.browse_input_dir)

        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(browse_btn)
        file_layout.addWidget(browse_dir_btn)
        main_layout.addWidget(file_group)

        # ===== 主体左右分栏: 左=工具与设定, 右=状态与日志 =====
        body_splitter = QSplitter(Qt.Horizontal)

        # 左侧：工具与设定区
        left_widget = QWidget()
        left_col = QVBoxLayout(left_widget)
        left_col.setContentsMargins(0, 0, 8, 0)
        left_col.setSpacing(10)

        # 模型与设备（卡片）
        model_group = QGroupBox(T("model_group"))
        left_layout = QFormLayout(model_group)
        left_layout.setVerticalSpacing(8)
        left_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        left_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        # 让标签列宽度足够显示中文
        _style_form_labels(model_group, 72)

        # 模型目录
        model_layout = QHBoxLayout()
        self.model_dir_edit = QLineEdit()
        # 默认使用仓库内模型目录
        default_model_dir = _default_model_dir("whisper-large-v3-fp16-ov")
        saved_model_dir = self.settings.value("model_dir", str(default_model_dir))
        if not Path(saved_model_dir).exists():
            saved_model_dir = str(default_model_dir)
            self.settings.setValue("model_dir", saved_model_dir)
        self.model_dir_edit.setText(saved_model_dir)
        model_browse_btn = QPushButton("...")
        model_browse_btn.clicked.connect(self.browse_model_dir)
        model_layout.addWidget(self.model_dir_edit)
        model_layout.addWidget(model_browse_btn)
        left_layout.addRow(T("model_dir"), model_layout)

        # 设备选择
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(260)
        populate_device_combo(self.device_combo, self.settings.value("device", "GPU.1"))
        left_layout.addRow(T("asr_device"), self.device_combo)

        # 缓存目录
        self.cache_dir_edit = QLineEdit()
        cache_dir = self.settings.value("cache_dir", str(CACHE_DIR))
        if cache_dir in ("./model_cache", "model_cache"):
            cache_dir = str(CACHE_DIR)
        self.cache_dir_edit.setText(cache_dir)
        left_layout.addRow(T("cache_dir"), self.cache_dir_edit)

        # 任务选择
        self.task_combo = QComboBox()
        self.task_combo.addItems(["transcribe", "translate"])
        self.task_combo.setCurrentText(self.settings.value("task", "transcribe"))
        left_layout.addRow(T("task"), self.task_combo)

        # 语言选择
        self.language_combo = QComboBox()
        self.language_combo.setEditable(True)
        self.language_combo.addItems(["auto", "en", "zh", "ja", "ko", "fr", "de", "es"])
        self.language_combo.setCurrentText(self.settings.value("language", "auto"))
        left_layout.addRow(T("src_lang"), self.language_combo)

        # Batch size
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 4)
        self.batch_size_spin.setValue(int(self.settings.value("batch_size", 1)))
        left_layout.addRow(T("batch_size"), self.batch_size_spin)

        # 界面语言
        self.gui_lang_combo = QComboBox()
        self.gui_lang_combo.addItem("中文", "zh")
        self.gui_lang_combo.addItem("English", "en")
        saved_gui_lang = self.settings.value("gui_lang", get_default_lang())
        idx = self.gui_lang_combo.findData(saved_gui_lang)
        if idx >= 0:
            self.gui_lang_combo.setCurrentIndex(idx)
        self.gui_lang_combo.currentIndexChanged.connect(self.on_gui_lang_changed)
        lang_row = QHBoxLayout()
        lang_row.addWidget(self.gui_lang_combo)
        lang_hint = QLabel(T("lang_restart_hint"))
        lang_hint.setStyleSheet("color: gray; font-size: 11px;")
        lang_row.addWidget(lang_hint)
        lang_row.addStretch()
        left_layout.addRow(T("gui_lang"), lang_row)

        left_col.addWidget(model_group)

        # 高级选项（卡片：简洁开关 + 弹出设置）
        # 标签列放宽以容纳英文（如 "Decoding:"），复选框固定自然宽度防止均分时文字省略
        adv_group = QGroupBox(T("adv_group"))
        right_layout = QFormLayout(adv_group)
        right_layout.setVerticalSpacing(10)
        right_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        _style_form_labels(adv_group, 112)

        # VAD 开关 + 设置按钮
        vad_row = QHBoxLayout()
        self.vad_check = QCheckBox(T("vad_enable"))
        self.vad_check.setChecked(self.settings.value("use_vad", True, type=bool))
        self.vad_settings_btn = QPushButton(T("settings_btn"))
        self.vad_settings_btn.clicked.connect(self.open_vad_settings)
        vad_row.addWidget(self.vad_check)
        vad_row.addWidget(self.vad_settings_btn)
        vad_row.addStretch()
        right_layout.addRow(T("vad_row"), vad_row)

        # Beam Search 开关 + 设置按钮
        beam_row = QHBoxLayout()
        self.beam_search_check = QCheckBox(T("beam_enable"))
        self.beam_search_check.setChecked(
            self.settings.value("beam_search", False, type=bool)
        )
        self.beam_settings_btn = QPushButton(T("settings_btn"))
        self.beam_settings_btn.clicked.connect(self.open_beam_settings)
        beam_row.addWidget(self.beam_search_check)
        beam_row.addWidget(self.beam_settings_btn)
        beam_row.addStretch()
        right_layout.addRow(T("beam_row"), beam_row)

        # 保留音频
        self.keep_audio_check = QCheckBox(T("keep_audio"))
        self.keep_audio_check.setChecked(
            self.settings.value("keep_audio", False, type=bool)
        )
        right_layout.addRow(T("other_row"), self.keep_audio_check)

        # 批量处理选项（输入为文件夹时生效，与 batch_generate.py 行为一致）
        # 英文标签较长，三个复选框一行放不下，分两行展示
        batch_row1 = QHBoxLayout()
        self.batch_skip_existing_check = QCheckBox(T("batch_skip_existing"))
        self.batch_skip_existing_check.setChecked(
            self.settings.value("batch_skip_existing", True, type=bool)
        )
        self.batch_recursive_check = QCheckBox(T("batch_recursive"))
        self.batch_recursive_check.setChecked(
            self.settings.value("batch_recursive", True, type=bool)
        )
        batch_row1.addWidget(self.batch_skip_existing_check)
        batch_row1.addWidget(self.batch_recursive_check)
        batch_row1.addStretch()
        right_layout.addRow(T("batch_row"), batch_row1)

        batch_row2 = QHBoxLayout()
        self.batch_skip_marker_check = QCheckBox(T("batch_skip_marker"))
        self.batch_skip_marker_check.setChecked(
            self.settings.value("batch_skip_marker", True, type=bool)
        )
        batch_row2.addWidget(self.batch_skip_marker_check)
        batch_row2.addStretch()
        right_layout.addRow("", batch_row2)

        left_col.addWidget(adv_group)

        # ===== 输出路径 =====
        output_group = QGroupBox(T("output_group"))
        output_layout = QHBoxLayout(output_group)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText(T("output_placeholder"))
        output_browse_btn = QPushButton("...")
        output_browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_browse_btn)
        left_col.addWidget(output_group)

        # ===== 翻译设置 (Hy-MT2) =====
        translate_group = QGroupBox(T("translate_group"))
        translate_layout = QFormLayout(translate_group)
        translate_layout.setVerticalSpacing(8)
        translate_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        translate_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        _style_form_labels(translate_group, 72)

        self.translate_check = QCheckBox(T("translate_enable"))
        self.translate_check.setChecked(
            self.settings.value("enable_translate", True, type=bool)
        )
        translate_layout.addRow("", self.translate_check)

        # 翻译模型目录
        tl_layout = QHBoxLayout()
        self.translate_model_edit = QLineEdit()
        default_trans_model = _default_model_dir("Hy-MT2-7B-ov-int4")
        saved_tl_dir = self.settings.value("translate_model_dir", str(default_trans_model))
        if not Path(saved_tl_dir).exists():
            saved_tl_dir = str(default_trans_model)
        self.translate_model_edit.setText(saved_tl_dir)
        tl_browse_btn = QPushButton("...")
        tl_browse_btn.clicked.connect(self.browse_translate_model)
        tl_layout.addWidget(self.translate_model_edit)
        tl_layout.addWidget(tl_browse_btn)
        translate_layout.addRow(T("translate_model"), tl_layout)

        # 翻译设备
        self.translate_device_combo = QComboBox()
        self.translate_device_combo.setMinimumWidth(260)
        populate_device_combo(self.translate_device_combo, self.settings.value("translate_device", "GPU"))
        translate_layout.addRow(T("translate_device"), self.translate_device_combo)

        # 目标语言
        self.tgt_lang_combo = QComboBox()
        self.tgt_lang_combo.setEditable(True)
        self.tgt_lang_combo.addItems([
            "中文", "English", "日本語", "한국어",
            "Français", "Deutsch", "Español"
        ])
        self.tgt_lang_combo.setCurrentText(
            self.settings.value("tgt_lang", "中文")
        )
        translate_layout.addRow(T("tgt_lang"), self.tgt_lang_combo)

        # 合并字符数
        self.merge_chars_spin = QSpinBox()
        self.merge_chars_spin.setRange(0, 500)
        self.merge_chars_spin.setSpecialValueText(T("translate_line_by_line"))
        self.merge_chars_spin.setValue(
            int(self.settings.value("merge_chars", 200))
        )
        translate_layout.addRow(T("merge_chars"), self.merge_chars_spin)

        left_col.addWidget(translate_group)

        # ===== 按钮区域（左栏底部） =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.start_btn = QPushButton(T("start"))
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setFixedWidth(120)
        self.start_btn.clicked.connect(self.start_processing)

        self.stop_btn = QPushButton(T("stop"))
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setFixedWidth(120)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_processing)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        left_col.addStretch()
        left_col.addLayout(btn_layout)

        body_splitter.addWidget(left_widget)

        # ===== 右侧：状态与日志 =====
        right_widget = QWidget()
        right_col = QVBoxLayout(right_widget)
        right_col.setContentsMargins(8, 0, 0, 0)
        right_col.setSpacing(10)

        # 进度条
        self.stage_label = QLabel(T("ready"))
        right_col.addWidget(self.stage_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        right_col.addWidget(self.progress_bar)

        # 日志区域
        log_group = QGroupBox(T("log_group"))
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logView")
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        right_col.addWidget(log_group)

        right_col.setStretchFactor(log_group, 1)
        body_splitter.addWidget(right_widget)

        # 左侧设定区宽度固定偏好, 日志占余下宽度; 禁止把设定区拖到字段裁切
        body_splitter.setCollapsible(0, False)
        left_widget.setMinimumWidth(500)
        body_splitter.setSizes([520, 720])
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        main_layout.addWidget(body_splitter)
        main_layout.setStretchFactor(body_splitter, 1)

        # 状态栏
        self.statusBar().showMessage(T("ready"))

    # ===== 事件处理 =====

    def browse_file(self):
        """浏览输入文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, T("dlg_open_media"), "",
            T("dlg_media_filter")
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            # 自动设置输出路径
            p = Path(file_path)
            self.output_edit.setText(str(p.with_suffix(".srt")))

    def browse_input_dir(self):
        """浏览输入文件夹（批量处理）"""
        dir_path = QFileDialog.getExistingDirectory(self, T("dlg_open_folder"))
        if dir_path:
            self.file_path_edit.setText(dir_path)
            self.output_edit.clear()

    def browse_model_dir(self):
        """浏览模型目录"""
        dir_path = QFileDialog.getExistingDirectory(self, T("dlg_model_dir"))
        if dir_path:
            self.model_dir_edit.setText(dir_path)

    def browse_translate_model(self):
        """浏览翻译模型目录"""
        dir_path = QFileDialog.getExistingDirectory(self, T("dlg_translate_model_dir"))
        if dir_path:
            self.translate_model_edit.setText(dir_path)

    def open_vad_settings(self):
        """打开 VAD 设置对话框"""
        dialog = VadSettingsDialog(self.settings, self)
        dialog.exec()

    def open_beam_settings(self):
        """打开 Beam Search 设置对话框"""
        dialog = BeamSettingsDialog(self.settings, self)
        dialog.exec()

    def browse_output(self):
        """浏览输出路径"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, T("dlg_save_srt"), "", T("dlg_srt_filter")
        )
        if file_path:
            self.output_edit.setText(file_path)

    def start_processing(self):
        """开始处理"""
        input_path = self.file_path_edit.text().strip()
        if not input_path:
            QMessageBox.warning(self, T("warn_title"), T("warn_no_input"))
            return
        if not Path(input_path).exists():
            QMessageBox.warning(self, T("warn_title"), T("warn_no_path"))
            return
        if Path(input_path).is_dir() and self.output_edit.text().strip():
            QMessageBox.warning(self, T("warn_title"), T("warn_batch_output"))
            return

        # 收集配置
        config = {
            "input_path": input_path,
            "model_dir": self.model_dir_edit.text(),
            "device": self.device_combo.currentData(),
            "cache_dir": self.cache_dir_edit.text(),
            "task": self.task_combo.currentText(),
            "language": self.language_combo.currentText(),
            "batch_size": self.batch_size_spin.value(),
            "use_vad": self.vad_check.isChecked(),
            "vad_threshold": float(self.settings.value("vad_threshold", 0.5)),
            "vad_merge_gap": int(self.settings.value("vad_merge_gap", 500)),
            "vad_padding": int(self.settings.value("vad_padding", 300)),
            "whisper_timestamps": self.settings.value("whisper_timestamps", False, type=bool),
            "beam_search": self.beam_search_check.isChecked(),
            "num_beams": int(self.settings.value("num_beams", 5)),
            "keep_audio": self.keep_audio_check.isChecked(),
            "output_path": self.output_edit.text() or None,
            # 批量处理
            "batch_skip_existing": self.batch_skip_existing_check.isChecked(),
            "batch_recursive": self.batch_recursive_check.isChecked(),
            "batch_skip_marker": self.batch_skip_marker_check.isChecked(),
            # 翻译配置
            "enable_translate": self.translate_check.isChecked(),
            "translate_model_dir": self.translate_model_edit.text(),
            "translate_device": self.translate_device_combo.currentData() or "CPU",
            "tgt_lang": self.tgt_lang_combo.currentText(),
            "merge_chars": self.merge_chars_spin.value(),
        }

        # 保存设置
        self.save_settings(config)

        # 更新 UI 状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.log_text.append("=" * 60)
        self.log_text.append(T("log_start"))
        self.log_text.append("=" * 60)

        # 启动工作线程
        self.worker = SubtitleWorker(config)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.stage_signal.connect(self.update_stage)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.chunk_signal.connect(self.on_chunk_done)
        self.worker.start()

    def stop_processing(self):
        """停止处理"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.append_log(T("log_stopping"))
            self.stop_btn.setEnabled(False)

    def on_finished(self, status, message):
        """处理完成回调: status = success / error / cancelled"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if status == "success":
            self.stage_label.setText(T("done"))
            self.progress_bar.setValue(100)
            self.append_log(T("log_success_saved") + message)
            QMessageBox.information(self, T("done_title"), T("done_msg") + message)
        elif status == "cancelled":
            self.stage_label.setText(T("stopped"))
            self.statusBar().showMessage(T("stopped"))
        else:
            self.stage_label.setText(T("failed"))
            self.append_log(T("log_failed_msg") + message)
            QMessageBox.critical(self, T("error_title"), T("error_msg") + message)

    def on_chunk_done(self, current, total, text):
        """每个 chunk 完成（进度条由 worker 的 _progress 驱动）"""
        self.append_log(f"  [{current}/{total}] {text}")

    # ===== 辅助方法 =====

    def append_log(self, text):
        """追加日志"""
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertPlainText(text + "\n")
        self.log_text.ensureCursorVisible()

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)

    def update_stage(self, text):
        """更新阶段标签"""
        self.stage_label.setText(text)
        self.statusBar().showMessage(text)

    def save_settings(self, config):
        """保存设置"""
        self.settings.setValue("model_dir", config["model_dir"])
        self.settings.setValue("device", config["device"])
        self.settings.setValue("cache_dir", config["cache_dir"])
        self.settings.setValue("task", config["task"])
        self.settings.setValue("language", config["language"])
        self.settings.setValue("batch_size", config["batch_size"])
        self.settings.setValue("use_vad", config["use_vad"])
        self.settings.setValue("vad_threshold", config["vad_threshold"])
        self.settings.setValue("vad_merge_gap", config["vad_merge_gap"])
        self.settings.setValue("vad_padding", config["vad_padding"])
        self.settings.setValue("whisper_timestamps", config["whisper_timestamps"])
        self.settings.setValue("beam_search", config["beam_search"])
        self.settings.setValue("num_beams", config["num_beams"])
        self.settings.setValue("keep_audio", config["keep_audio"])
        self.settings.setValue("batch_skip_existing", config["batch_skip_existing"])
        self.settings.setValue("batch_recursive", config["batch_recursive"])
        self.settings.setValue("batch_skip_marker", config["batch_skip_marker"])
        # 翻译设置
        self.settings.setValue("enable_translate", config["enable_translate"])
        self.settings.setValue("translate_model_dir", config["translate_model_dir"])
        self.settings.setValue("translate_device", config["translate_device"])
        self.settings.setValue("tgt_lang", config["tgt_lang"])
        self.settings.setValue("merge_chars", config["merge_chars"])

    def load_settings(self):
        """加载设置"""
        # 已在 init_ui 中处理
        pass

    def closeEvent(self, event):
        """关闭窗口时确保线程停止"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        event.accept()


# ==================== 入口 ====================

def main():
    # 无窗口时先用裸 QSettings 读语言，保证首个窗口就是正确语言
    from PySide6.QtCore import QCoreApplication
    QCoreApplication.setOrganizationName("VideoSubGen")
    QCoreApplication.setApplicationName("GUI")
    set_lang(QSettings().value("gui_lang", get_default_lang()))

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    # 设置全局字体
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
