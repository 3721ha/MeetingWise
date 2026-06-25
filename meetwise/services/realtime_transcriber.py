# -*- coding: utf-8 -*-
"""
实时转写引擎模块
核心模块：协调录音、转写、说话人识别，通过 Qt 信号与 UI 通信
所有耗时操作在子线程执行，确保 UI 不卡顿
"""

import numpy as np
import sounddevice as sd
import queue
import time
import threading
import os
import soundfile as sf
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from PySide6.QtCore import QThread, Signal

from meetwise.services.whisper_client import WhisperClient
from meetwise.services.speaker_recognizer import SpeakerRecognizer


class RealtimeTranscriber(QThread):
    """
    实时转写引擎（QThread 子线程）
    
    工作流程：
    1. sounddevice 回调采集音频 -> 入队（极快操作）
    2. 主循环每 N 秒从队列取出音频 -> 声纹识别 -> 转写
    3. 通过 Signal 将结果发送到 UI 线程
    
    关键：sounddevice 回调只做 queue.put，绝不做耗时操作
    """

    # Qt 信号定义
    utterance_ready = Signal(str, str, float, float, float)  # (speaker, text, timestamp, audio_start, audio_end)
    status_changed = Signal(str)  # 状态信息
    error_occurred = Signal(str)  # 错误信息
    meeting_ended = Signal(str)  # 会议结束，参数为录音文件路径
    duration_updated = Signal(float)  # 录音时长更新（秒）

    # 状态常量
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"

    def __init__(self, whisper_client, speaker_recognizer, database, meeting_id, config):
        """
        初始化转写引擎
        :param whisper_client: WhisperClient 实例
        :param speaker_recognizer: SpeakerRecognizer 实例
        :param database: Database 实例
        :param meeting_id: 当前会议 ID
        :param config: ConfigManager 实例
        """
        super().__init__()
        self._whisper = whisper_client
        self._recognizer = speaker_recognizer
        self._db = database
        self._meeting_id = meeting_id
        self._config = config

        self._sample_rate = config.get("audio_sample_rate", 16000)
        self._transcribe_interval = config.get("transcribe_interval", 3)
        self._threshold = config.get("speaker_threshold", 0.7)
        self._recording_dir = config.get("recording_dir", "data/recordings")

        # 音频队列（sounddevice回调 -> 转写线程）
        self._audio_queue = queue.Queue()

        # 累积音频缓冲
        self._audio_buffer = []
        self._buffer_start_time = 0  # 缓冲区起始时间（相对于会议开始）

        # 完整录音保存
        self._all_audio_chunks = []
        self._current_time = 0  # 当前录音时间（秒）

        # 状态控制
        self._state = self.IDLE
        self._stream = None

        # 已注册声纹库缓存
        self._voiceprints = {}

    def run(self):
        """QThread 主循环（在子线程中执行）"""
        self._state = self.RECORDING

        # 检查模型是否已加载，未加载则发出加载状态
        need_load = not self._whisper.is_loaded() or not self._recognizer.is_loaded()
        if need_load:
            self.status_changed.emit("正在加载模型...")

        # 加载模型
        try:
            self._whisper.load_model()
            self._recognizer.load_model()
        except Exception as e:
            self.error_occurred.emit(f"模型加载失败: {str(e)}")
            self._state = self.STOPPED
            return

        # 加载声纹库
        self._voiceprints = self._db.get_all_voiceprints()
        self._recognizer.reset_unknown_counter()

        # 创建录音目录
        os.makedirs(self._recording_dir, exist_ok=True)

        self.status_changed.emit("开始录音...")
        self._buffer_start_time = 0

        # 启动 sounddevice 音频流
        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1024,
                callback=self._audio_callback
            )
            self._stream.start()
        except Exception as e:
            self.error_occurred.emit(f"麦克风启动失败: {str(e)}")
            self._state = self.STOPPED
            return

        # 主循环：定期从队列取音频进行转写
        last_transcribe_time = time.time()

        try:
            while self._state in (self.RECORDING, self.PAUSED):
                # 从队列中取出所有可用音频
                while not self._audio_queue.empty():
                    try:
                        chunk = self._audio_queue.get_nowait()
                        self._audio_buffer.append(chunk)
                        self._all_audio_chunks.append(chunk)
                        self._current_time += len(chunk) / self._sample_rate
                    except queue.Empty:
                        break

                # 更新录音时长
                self.duration_updated.emit(self._current_time)

                # 每 N 秒执行一次转写
                now = time.time()
                if self._state == self.RECORDING and (now - last_transcribe_time) >= self._transcribe_interval:
                    if self._audio_buffer:
                        self._process_buffer()
                    last_transcribe_time = now

                # 短暂休眠，避免 CPU 空转
                self.msleep(50)

        except Exception as e:
            self.error_occurred.emit(f"转写引擎异常: {str(e)}")

        finally:
            # 停止音频流
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            # 处理剩余缓冲
            if self._audio_buffer:
                self._process_buffer()

            # 保存完整录音
            recording_path = self._save_recording()

            self._state = self.STOPPED
            self.meeting_ended.emit(recording_path or "")

    def _audio_callback(self, indata, frames, time_info, status):
        """
        sounddevice 音频回调函数（在 PortAudio C 线程中执行）
        关键：只做 queue.put，绝不做任何耗时操作！
        """
        if status:
            logger.debug(f"[Transcriber] 音频状态: {status}")
        # 将音频块放入队列
        self._audio_queue.put(indata.copy())

    def _process_buffer(self):
        """处理音频缓冲：声纹识别 + 转写"""
        if not self._audio_buffer:
            return

        # 合并缓冲区中的音频
        audio_data = np.concatenate(self._audio_buffer, axis=0).flatten()
        buffer_duration = len(audio_data) / self._sample_rate
        audio_end_time = self._current_time
        audio_start_time = audio_end_time - buffer_duration

        # 清空缓冲区
        self._audio_buffer = []

        # 检查音频是否太短
        if len(audio_data) < self._sample_rate * 0.5:
            return

        # 步骤1：声纹识别
        self.status_changed.emit("识别说话人...")
        embedding = self._recognizer.extract_embedding(audio_data, self._sample_rate)
        speaker = None

        if embedding is not None:
            speaker = self._recognizer.identify_speaker(
                embedding, self._voiceprints, self._threshold
            )

        if speaker is None:
            speaker = self._recognizer.get_unknown_speaker_label(embedding)

        # 步骤2：语音转写
        self.status_changed.emit("转写中...")
        segments = self._whisper.transcribe(audio_data)

        if not segments:
            self.status_changed.emit("等待语音输入...")
            return

        # 步骤3：发送转写结果
        for seg in segments:
            text = seg["text"].strip()
            if text:
                # 计算绝对时间戳
                seg_start = audio_start_time + seg["start"]
                seg_end = audio_start_time + seg["end"]

                # 发射信号到 UI
                self.utterance_ready.emit(
                    speaker, text, seg_start, seg_start, seg_end
                )

                # 保存到数据库
                self._db.save_utterance(
                    meeting_id=self._meeting_id,
                    speaker=speaker,
                    text=text,
                    timestamp=seg_start,
                    audio_start=seg_start,
                    audio_end=seg_end
                )

        self.status_changed.emit("录音中...")

    def _save_recording(self):
        """保存完整录音为 WAV 文件"""
        if not self._all_audio_chunks:
            return None

        audio = np.concatenate(self._all_audio_chunks, axis=0).flatten()
        file_path = os.path.join(self._recording_dir, f"meeting_{self._meeting_id}.wav")

        try:
            sf.write(file_path, audio, self._sample_rate)
            logger.info(f"[Transcriber] 录音已保存: {file_path}")

            # 更新数据库中的录音路径
            self._db.end_meeting(self._meeting_id, recording_path=file_path)

            return file_path
        except Exception as e:
            logger.error(f"[Transcriber] 录音保存失败: {e}")
            return None

    def pause(self):
        """暂停录音"""
        if self._state == self.RECORDING:
            self._state = self.PAUSED
            self.status_changed.emit("已暂停")

    def resume(self):
        """恢复录音"""
        if self._state == self.PAUSED:
            self._state = self.RECORDING
            self.status_changed.emit("录音中...")

    def stop(self):
        """停止录音"""
        self._state = self.STOPPED

    @property
    def state(self):
        """当前状态"""
        return self._state

    @property
    def current_time(self):
        """当前录音时长（秒）"""
        return self._current_time
