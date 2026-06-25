# -*- coding: utf-8 -*-
"""
说话人识别模块
使用 pyannote.audio 提取声纹特征向量，与已注册声纹库进行余弦相似度比对
"""

import numpy as np
import torch
import logging

logger = logging.getLogger(__name__)

logging.getLogger("pyannote").setLevel(logging.WARNING)


class SpeakerRecognizer:
    """说话人识别器：声纹特征提取 + 余弦相似度比对"""

    def __init__(self, model_name="pyannote/embedding", hf_token=None):
        """
        初始化说话人识别器
        :param model_name: pyannote 模型名称
        :param hf_token: HuggingFace 访问令牌
        """
        self._model_name = model_name
        self._hf_token = hf_token
        self._model = None  # 懒加载
        self._unknown_counter = 0  # 陌生人编号计数器
        self._unknown_map = {}  # 音频特征hash -> 陌生人编号映射
        self._last_unknown_label = None  # 最近分配的陌生人标签（embedding为None时复用）

    def load_model(self):
        """加载 pyannote 声纹模型（耗时操作，需在子线程调用）"""
        if self._model is not None:
            return

        logger.info(f"[SpeakerRecognizer] 正在加载声纹模型: {self._model_name}...")
        try:
            from pyannote.audio import Model
            self._model = Model.from_pretrained(
                self._model_name,
                use_auth_token=self._hf_token,
                strict=False
            )
            logger.info("[SpeakerRecognizer] 声纹模型加载完成")
        except Exception as e:
            logger.error(f"[SpeakerRecognizer] 声纹模型加载失败: {e}")
            raise

    def extract_embedding(self, audio_data, sample_rate=16000):
        """
        提取音频的声纹特征向量
        :param audio_data: numpy 数组，16kHz 单声道
        :param sample_rate: 采样率
        :return: 512 维 float32 numpy 数组
        """
        if self._model is None:
            logger.warning("[SpeakerRecognizer] 模型未加载，无法提取声纹特征")
            return None

        if audio_data is None or len(audio_data) == 0:
            return None

        try:
            from pyannote.audio import Inference
            # 创建推理管道
            inference = Inference(self._model, window="whole")

            # 确保是 float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # pyannote 要求 waveform 格式为 (channels, time) 的 torch.Tensor
            # 单声道: shape = (1, N)
            if audio_data.ndim == 1:
                waveform = torch.from_numpy(audio_data).unsqueeze(0)  # (N,) -> (1, N)
            elif audio_data.ndim == 2:
                # 如果是 (N, 1) 或 (N, channels)，转置为 (channels, N)
                if audio_data.shape[0] > audio_data.shape[1]:
                    waveform = torch.from_numpy(audio_data.T)  # (N, C) -> (C, N)
                else:
                    waveform = torch.from_numpy(audio_data)
            else:
                logger.warning(f"[SpeakerRecognizer] 音频维度异常: {audio_data.shape}")
                return None

            # 提取声纹特征
            embedding = inference({"waveform": waveform, "sample_rate": sample_rate})

            # 归一化
            embedding = embedding / np.linalg.norm(embedding)

            return embedding.astype(np.float32)

        except Exception as e:
            logger.error(f"[SpeakerRecognizer] 声纹提取失败: {e}")
            return None

    def identify_speaker(self, embedding, voiceprints, threshold=0.7):
        """
        识别说话人：与已注册声纹库比对
        :param embedding: 当前音频的声纹特征向量
        :param voiceprints: 已注册声纹库 {name: embedding_array}
        :param threshold: 余弦相似度阈值
        :return: 发言人姓名（匹配成功）或 None（匹配失败，需要分配陌生人编号）
        """
        if embedding is None or not voiceprints:
            return None

        best_name = None
        best_similarity = -1

        for name, ref_embedding in voiceprints.items():
            similarity = self._cosine_similarity(embedding, ref_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_name = name

        # 超过阈值则返回匹配的姓名
        if best_similarity >= threshold:
            logger.debug(f"[SpeakerRecognizer] 匹配成功: {best_name} (相似度: {best_similarity:.3f})")
            return best_name

        return None

    def get_unknown_speaker_label(self, embedding=None):
        """
        获取陌生人编号标签
        :param embedding: 可选的声纹特征，用于判断是否是同一个陌生人
        :return: "陌生人A"、"陌生人B" 等；embedding 为 None 时返回 "未知说话人"
        """
        # 声纹提取失败时，返回通用标签，不分配新编号
        if embedding is None:
            if self._last_unknown_label:
                return self._last_unknown_label
            return "未知说话人"

        # 根据 embedding 指纹判断是否是同一个陌生人
        emb_key = tuple(np.round(embedding[:10], 2))  # 取前10维作为简易指纹
        if emb_key in self._unknown_map:
            self._last_unknown_label = self._unknown_map[emb_key]
            return self._unknown_map[emb_key]

        # 分配新编号（限制在 A-Z，共26个）
        self._unknown_counter += 1
        if self._unknown_counter <= 26:
            label = f"陌生人{chr(64 + self._unknown_counter)}"  # A=65
        else:
            label = f"陌生人{self._unknown_counter}"

        self._unknown_map[emb_key] = label
        self._last_unknown_label = label

        logger.info(f"[SpeakerRecognizer] 新陌生人: {label}")
        return label

    def register_voiceprint(self, audio_data, sample_rate=16000):
        """
        从音频中提取声纹特征用于注册
        :param audio_data: numpy 数组
        :param sample_rate: 采样率
        :return: 声纹特征向量
        """
        return self.extract_embedding(audio_data, sample_rate)

    def reset_unknown_counter(self):
        """重置陌生人计数器"""
        self._unknown_counter = 0
        self._unknown_map = {}
        self._last_unknown_label = None

    @staticmethod
    def _cosine_similarity(a, b):
        """计算两个向量的余弦相似度"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def is_loaded(self):
        """检查模型是否已加载"""
        return self._model is not None
