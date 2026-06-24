# 智会 MeetWise - AI 会议纪要生成器

基于 Python 的桌面客户端，支持实时语音转写、声纹识别说话人、AI 摘要生成与会议对话。

## 功能特性

- 实时录音转写：sounddevice 流式采集 + faster-whisper 增量识别
- 说话人识别：pyannote.audio 声纹特征提取，余弦相似度自动匹配已注册成员
- 陌生人管理：未注册发言人自动编号（A-Z，超限转数字编号），支持右键重命名并全局同步
- AI 摘要生成：一键调用智谱 GLM-4.5-Air 生成关键点 / 待办 / 结论
- AI 对话：基于会议全文上下文的多轮追问，历史记录可回溯
- 语音回放定位：点击转写气泡跳转到对应语音位置播放
- 会议管理：历史会议列表、详情查看、级联删除

## 技术栈

| 模块 | 技术 |
| --- | --- |
| GUI | PySide6 (Qt for Python) |
| 录音 | sounddevice (PortAudio) |
| 转写 | faster-whisper (CTranslate2) |
| 声纹 | pyannote.audio + PyTorch |
| 大模型 | 智谱 GLM-4.5-Air (OpenAI 兼容接口) |
| 数据库 | SQLite |
| 打包 | PyInstaller |

## 快速开始

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置 API 密钥（编辑 config.json）
# 填入 glm_api_key 和 hf_token

# （可选）预下载模型，避免首次启动耗时
python download_models.py

# 启动
python main.py
```

首次运行需联网下载模型（faster-whisper base 约 140MB，pyannote/embedding 约 100MB），后续自动使用本地缓存。国内网络建议先执行 `python download_models.py` 预下载。

## 项目结构

```
MeetWise/
├── controllers/
│   └── main.py                # 程序入口
├── models/
│   ├── database.py            # SQLite 数据库管理
│   ├── whisper_client.py      # faster-whisper 封装
│   ├── llm_client.py          # 智谱 GLM API 封装
│   ├── speaker_recognizer.py  # 说话人识别（声纹提取与比对）
│   ├── voiceprint_manager.py   # 声纹注册管理
│   └── realtime_transcriber.py # 实时转写引擎（录音+转写+识别）
├── views/
│   ├── main_window.py         # 主窗口 UI 与交互逻辑
│   └── ui_styles.py           # 深色主题 QSS 样式
├── utils/
│   └── config_manager.py      # 配置管理
├── scripts/
│   └── download_models.py     # 模型预下载脚本
├── config.json                # 配置文件
├── requirements.txt           # 依赖清单
├── meetwise.spec              # PyInstaller 打包配置
├── docs/                      # 文档目录
│   ├── requirements_spec.md
│   ├── deployment_guide.md
│   └── design.md
├── voiceprints/              # 声纹数据（运行时自动创建）
└── recordings/               # 录音文件（运行时自动创建）
```

## 环境要求

| 项目 | 要求 |
| --- | --- |
| Python | 3.10+ |
| 内存 | 8 GB+（推荐 16 GB） |
| 硬盘 | 5 GB+（含模型文件） |
| 系统 | Windows 10/11（主要目标平台） |

## 相关文档

- [需求规格说明书](docs/requirements_spec.md) — 功能需求详细规格
- [开发与部署运维手册](docs/deployment_guide.md) — 环境配置、使用指南、打包部署、常见问题
- [设计文档](docs/design.md) — 系统架构、目录结构、数据库设计、数据流

## 许可证

本项目仅供学习和答辩演示使用。

---
