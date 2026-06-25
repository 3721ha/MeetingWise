# -*- coding: utf-8 -*-
"""
声纹管理模块
提供声纹注册、列表查看、删除等业务逻辑
协调 sounddevice 录音和 speaker_recognizer 声纹提取
"""

import numpy as np
import sounddevice as sd
import threading
import os
import time
import logging

logger = logging.getLogger(__name__)


class VoiceprintManager:
    """声纹管理器"""

    def __init__(self, speaker_recognizer, database, config):
        """
        初始化声纹管理器
        :param speaker_recognizer: SpeakerRecognizer 实例
        :param database: Database 实例
        :param config: ConfigManager 实例
        """
        self._recognizer = speaker_recognizer
        self._db = database
        self._config = config
        self._sample_rate = config.get("audio_sample_rate", 16000)
        self._voiceprint_dir = config.get("voiceprint_dir", "data/voiceprints")

        # 录音状态
        self._is_recording = False
        self._audio_chunks = []
        self._record_thread = None

    def start_recording(self, callback=None):
        """
        开始录音
        :param callback: 录音进度回调 callback(duration_seconds)
        """
        if self._is_recording:
            return

        self._is_recording = True
        self._audio_chunks = []
        self._start_time = time.time()
        self._callback = callback

        # 在独立线程中录音
        self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()

    def _record_loop(self):
        """录音循环，使用 sounddevice 流式采集"""
        try:
            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"[VoiceprintManager] 录音状态: {status}")
                if self._is_recording:
                    self._audio_chunks.append(indata.copy())
                    # 回调录音时长
                    if self._callback:
                        duration = len(self._audio_chunks) * len(indata) / self._sample_rate
                        self._callback(duration)

            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1024,
                callback=audio_callback
            ):
                while self._is_recording:
                    sd.sleep(100)

        except Exception as e:
            print(f"[VoiceprintManager] 录音异常: {e}")
            self._is_recording = False

    def stop_recording(self):
        """
        停止录音
        :return: 录制的音频数据（numpy 数组）
        """
        self._is_recording = False

        # 等待录音线程结束
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=2)

        # 合并音频数据
        if not self._audio_chunks:
            return None

        audio_data = np.concatenate(self._audio_chunks, axis=0).flatten()
        return audio_data

    def register_voiceprint(self, name, audio_data):
        """
        注册声纹
        :param name: 发言人姓名
        :param audio_data: 录制的音频数据
        :return: (success: bool, message: str)
        """
        if audio_data is None or len(audio_data) < self._sample_rate * 3:
            return False, "录音时间太短，请重新录制（至少 3 秒）"

        # 检查姓名是否已存在
        existing = self._db.get_voiceprint_names()
        names = [v["name"] for v in existing]
        if name in names:
            return False, f"姓名「{name}」已注册，请使用其他名称"

        try:
            # 提取声纹特征
            embedding = self._recognizer.register_voiceprint(audio_data, self._sample_rate)
            if embedding is None:
                return False, "声纹特征提取失败，请检查模型是否正确加载"

            # 保存到数据库和文件
            self._db.save_voiceprint(name, embedding, self._voiceprint_dir)
            return True, f"声纹注册成功：{name}"

        except Exception as e:
            return False, f"声纹注册失败: {str(e)}"

    def list_voiceprints(self):
        """获取所有已注册的声纹列表"""
        return self._db.get_voiceprint_names()

    def delete_voiceprint(self, name):
        """删除声纹注册"""
        try:
            self._db.delete_voiceprint(name, self._voiceprint_dir)
            return True, f"已删除声纹：{name}"
        except Exception as e:
            return False, f"删除失败: {str(e)}"

    def get_recording_duration(self):
        """获取当前录音时长（秒）"""
        if not self._audio_chunks:
            return 0
        total_samples = sum(len(chunk) for chunk in self._audio_chunks)
        return total_samples / self._sample_rate

    @property
    def is_recording(self):
        """是否正在录音"""
        return self._is_recording
