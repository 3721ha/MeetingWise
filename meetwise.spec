# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
使用方法: pyinstaller meetwise.spec
"""

import os

block_cipher = None

# 获取当前目录
base_dir = os.path.dirname(os.path.abspath(SPECPATH))

a = Analysis(
    ['controllers/main.py'],
    pathex=[base_dir],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('voiceprints', 'voiceprints'),
        ('recordings', 'recordings'),
    ],
    hiddenimports=[
        # faster-whisper 相关
        'faster_whisper',
        'ctranslate2',
        'huggingface_hub',
        # pyannote 相关
        'pyannote.audio',
        'pyannote.audio.pipelines',
        'pyannote.audio.models',
        'pyannote.core',
        'pyannote.database',
        'pyannote.metrics',
        # torch 相关
        'torch',
        'torchaudio',
        'torch.nn',
        'torch.nn.functional',
        # 音频相关
        'sounddevice',
        'soundfile',
        'numpy',
        'scipy',
        # Qt 相关
        'PySide6',
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        # API 相关
        'openai',
        'httpx',
        'httpcore',
        # 其他
        'onnxruntime',
        'av',
        'functorch',
        'asteroid_filterbanks',
        'julius',
        'einops',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'pandas',
        'PIL',
        'sklearn',
        'IPython',
        'notebook',
        'pytest',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MeetWise',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 窗口模式（不显示控制台）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可设置 .ico 图标路径
)
