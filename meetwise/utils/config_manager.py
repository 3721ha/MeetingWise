# -*- coding: utf-8 -*-
"""
配置管理模块
负责读取和写入 config.json 配置文件，提供全局配置访问接口
"""

import json
import os

# 默认配置项
DEFAULT_CONFIG = {
    "glm_api_key": "",
    "glm_base_url": "https://open.bigmodel.cn/api/paas/v4/",
    "glm_model": "glm-4.5-air",
    "hf_token": "",
    "whisper_model_size": "base",
    "pyannote_model": "pyannote/embedding",
    "speaker_threshold": 0.7,
    "audio_sample_rate": 16000,
    "transcribe_interval": 3,
    "voiceprint_dir": "data/voiceprints",
    "recording_dir": "data/recordings",
    "db_path": "data/meetwise.db"
}


class ConfigManager:
    """配置管理器（单例模式）"""

    _instance = None
    _config = None

    def __new__(cls, config_path=None):
        """单例模式：确保全局只有一个配置管理器实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path=None):
        """初始化配置管理器，加载配置文件"""
        if self._initialized:
            return
        self._initialized = True

        # 配置文件路径：优先使用传入路径，否则使用项目根目录下的 resources/config.json
        if config_path is None:
            self._config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "resources", "config.json")
        else:
            self._config_path = config_path

        # 加载配置
        self._load()

    def _load(self):
        """从 config.json 加载配置，文件不存在则创建默认配置"""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                # 补齐缺失的默认配置项
                for key, value in DEFAULT_CONFIG.items():
                    if key not in self._config:
                        self._config[key] = value
            except (json.JSONDecodeError, IOError) as e:
                print(f"[ConfigManager] 配置文件读取失败，使用默认配置: {e}")
                self._config = DEFAULT_CONFIG.copy()
                self.save()
        else:
            # 配置文件不存在，创建默认配置
            self._config = DEFAULT_CONFIG.copy()
            self.save()

    def get(self, key, default=None):
        """获取配置项的值"""
        return self._config.get(key, default)

    def set(self, key, value):
        """设置配置项的值"""
        self._config[key] = value

    def save(self):
        """保存配置到 config.json"""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[ConfigManager] 配置文件保存失败: {e}")

    def get_all(self):
        """获取所有配置项"""
        return self._config.copy()

    @classmethod
    def reset(cls):
        """重置单例（仅用于测试）"""
        cls._instance = None
        cls._config = None
