# -*- coding: utf-8 -*-
"""
语音转写模块
封装 faster-whisper，提供懒加载的语音转写能力
"""

import numpy as np
import logging

logging.getLogger("faster_whisper").setLevel(logging.WARNING)

from zhconv import convert


class WhisperClient:
    """faster-whisper 语音转写客户端"""

    def __init__(self, model_size="base"):
        """
        初始化转写客户端
        :param model_size: 模型大小（tiny/base/small/medium/large-v3）
        """
        self._model_size = model_size
        self._model = None  # 懒加载，首次调用时才加载模型

    def load_model(self):
        """加载 faster-whisper 模型（耗时操作，需在子线程调用）"""
        if self._model is not None:
            return

        print(f"[WhisperClient] 正在加载模型: {self._model_size}...")
        try:
            from faster_whisper import WhisperModel
            # device="auto" 自动选择 GPU/CPU
            # compute_type: GPU用float16，CPU用int8
            self._model = WhisperModel(
                self._model_size,
                device="auto",
                compute_type="int8"
            )
            print(f"[WhisperClient] 模型加载完成: {self._model_size}")
        except Exception as e:
            print(f"[WhisperClient] 模型加载失败: {e}")
            raise

    def transcribe(self, audio_data, language="zh"):
        """
        转写音频为文本
        :param audio_data: numpy 数组，16kHz 单声道 float32
        :param language: 语言代码（zh=中文，en=英文，None=自动检测）
        :return: 列表 [{"text": str, "start": float, "end": float}, ...]
        """
        # 确保模型已加载
        if self._model is None:
            self.load_model()

        # 检查音频数据
        if audio_data is None or len(audio_data) == 0:
            return []

        # 确保是 float32 格式
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # 如果音频太短（低于 0.3 秒），直接返回空
        if len(audio_data) < 16000 * 0.3:
            return []

        try:
            # faster-whisper 转写
            segments, info = self._model.transcribe(
                audio_data,
                language=language,
                beam_size=5,
                vad_filter=True,  # 启用 VAD 过滤静音段
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            results = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    text = convert(text, "zh-hans")
                    results.append({
                        "text": text,
                        "start": segment.start,
                        "end": segment.end
                    })

            return results

        except Exception as e:
            print(f"[WhisperClient] 转写失败: {e}")
            return []

    def is_loaded(self):
        """检查模型是否已加载"""
        return self._model is not None
