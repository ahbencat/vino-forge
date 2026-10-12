# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（onedir）。

用法（仓库根目录）:
    pyinstaller apps/vino-sub-gen/vino-sub-gen.spec --noconfirm

产物: dist/VinoSubGen/VinoSubGen.exe

模型不打进 exe：将 Whisper / Hy-MT2 权重和 silero_vad.onnx 放到
exe 同级目录的 models/ 下（结构见 models/ 内各 README），或在 GUI 中点
"浏览..." 指定路径。
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# silero_vad: 运行时才 import，且包内含数据文件，整体收集
silero_datas, silero_binaries, silero_hidden = collect_all("silero_vad")

# sympy 由 optimum-intel 在 import 期拉入（运行时确实加载 sympy.matrices），
# 必须整体收集：CPython 3.10.0 的 dis bug 会让部分 sympy 模块的字节码扫描
# 截断（见 build_exe.py），显式收集子模块防止漏打包。
sympy_hidden = collect_submodules("sympy")

a = Analysis(
    ["gui/gui_app.py"],
    pathex=[".", "../../libs"],
    binaries=silero_binaries,
    datas=silero_datas,
    hiddenimports=[
        *silero_hidden,
        *sympy_hidden,
        "ov_kit.paths",
        "ov_kit.devices",
        "lib.asr",
        "lib.translate",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # GUI 用不到的大依赖，缩小体积（被间接依赖拽入的 cv2/sklearn/llvmlite/numba/pandas 等）。
    # 注意：librosa/scipy 不能排除 —— transformers.audio_utils 在 import 期硬依赖
    # librosa（做重采样/特征），transformers.feature_extraction_sequence_utils
    # 也 import scipy；onnxruntime 不能排除 —— Silero VAD 的 ONNX 含动态 rank，
    # OpenVINO 读不了，silero_vad 包内部即 onnxruntime 推理（已验证）。
    excludes=[
        "tkinter",
        "matplotlib",
        "cv2",
        "sklearn",
        "llvmlite",
        "numba",
        "pandas",
        "PIL",
        "cvxopt",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.Qt3DCore",
        "PySide6.QtWebEngineCore",
        "PySide6.QtMultimedia",
        "PySide6.QtDataVisualization",
        "PySide6.QtCharts",
        "IPython",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VinoSubGen",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX 压缩易触发杀毒误报，且可能破坏部分 DLL
    console=False,      # 窗口程序，无控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VinoSubGen",
)
