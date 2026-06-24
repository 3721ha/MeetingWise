# MeetWise 设计文档

## 1. 项目概述

**智会 MeetWise** 是一款基于 AI 的会议纪要生成器，通过实时录音转写、说话人识别、AI 摘要生成，实现会议内容的自动化记录与整理。

### 核心功能
- 实时录音转写（faster-whisper）
- 说话人识别（pyannote.audio 声纹识别）
- 声纹注册管理
- AI 摘要生成（智谱 GLM-4.5-Air）
- AI 对话追问
- 会议列表管理
- 语音回放定位

---

## 2. 技术架构

### 2.1 架构模式

采用 **MVC（Model-View-Controller）** 分层架构：

```
┌─────────────────────────────────────────────────────────┐
│                    View Layer (视图层)                    │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │  MainWindow     │  │  UI Styles      │              │
│  │  (PySide6)      │  │  (QSS)          │              │
│  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │ 信号槽通信
                            │
┌─────────────────────────────────────────────────────────┐
│                Controller Layer (控制层)                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │  main.py (程序入口)                              │   │
│  │  - 初始化 QApplication                           │   │
│  │  - 创建 MainWindow                               │   │
│  │  - 全局异常处理                                   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │ 调用
                            │
┌─────────────────────────────────────────────────────────┐
│                  Model Layer (模型层)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Whisper     │  │  Speaker     │  │  LLM         │ │
│  │  Client      │  │  Recognizer  │  │  Client      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Voiceprint  │  │  Realtime    │  │  Database    │ │
│  │  Manager     │  │  Transcriber │  │  (SQLite)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │ 依赖
                            │
┌─────────────────────────────────────────────────────────┐
│                   Utils Layer (工具层)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ConfigManager (配置管理)                        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 线程模型

```
主线程 (UI)
  ├─ MainWindow (PySide6 事件循环)
  └─ ModelLoaderThread (后台模型加载)

录音线程 (sounddevice 回调)
  └─ 音频采集 → 音频队列

转写线程 (RealtimeTranscriber QThread)
  ├─ WhisperClient (语音转写)
  └─ SpeakerRecognizer (说话人识别)

播放线程 (QTimer)
  └─ 音频播放进度更新
```

---

## 3. 目录结构

```
MeetWise/
├── controllers/                    # 控制层
│   └── main.py                     # 程序入口
│
├── models/                         # 模型层
│   ├── database.py                 # SQLite 数据库管理
│   ├── whisper_client.py           # faster-whisper 封装
│   ├── llm_client.py               # 智谱 GLM API 封装
│   ├── speaker_recognizer.py       # 说话人识别（声纹提取与比对）
│   ├── voiceprint_manager.py       # 声纹注册管理
│   └── realtime_transcriber.py     # 实时转写引擎（录音+转写+识别）
│
├── views/                          # 视图层
│   ├── main_window.py              # 主窗口 UI 与交互逻辑
│   └── ui_styles.py                # 深色主题 QSS 样式
│
├── utils/                          # 工具层
│   └── config_manager.py           # 配置管理
│
├── scripts/                        # 脚本工具
│   └── download_models.py          # 模型预下载脚本
│
├── docs/                           # 文档
│   ├── requirements_spec.md
│   ├── deployment_guide.md
│   └── design.md                   # 本文档
│
├── voiceprints/                    # 声纹数据（运行时自动创建）
│   └── {name}.npy                  # 声纹特征向量文件
│
├── recordings/                     # 录音文件（运行时自动创建）
│   └── meeting_{id}.wav            # 会议录音文件
│
├── config.json                     # 配置文件
├── requirements.txt                # 依赖清单
├── meetwise.spec                   # PyInstaller 打包配置
└── README.md                       # 项目说明
```

---

## 4. 核心模块说明

### 4.1 Controller 层

#### `controllers/main.py`
**职责**：程序入口，应用生命周期管理
**关键功能**：
- 初始化 PySide6 应用
- 创建并显示主窗口
- 全局异常处理
- 高 DPI 支持

### 4.2 Model 层

#### `models/database.py`
**职责**：数据持久化
**数据库类型**：SQLite（文件型数据库，无需独立服务）
**外键约束**：启用 `PRAGMA foreign_keys = ON`，支持级联删除

##### 数据表结构

**meetings（会议表）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 会议唯一标识 |
| title | TEXT | NOT NULL | 会议标题 |
| start_time | TEXT | NOT NULL | 开始时间（ISO 格式） |
| end_time | TEXT | | 结束时间（ISO 格式） |
| status | TEXT | DEFAULT 'recording' | 状态：recording / ended |
| recording_path | TEXT | | 录音文件路径 |

**utterances（发言记录表）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 发言唯一标识 |
| meeting_id | INTEGER | NOT NULL, FOREIGN KEY | 关联会议 ID |
| speaker | TEXT | NOT NULL | 发言人姓名 |
| speaker_id | TEXT | | 说话人标识符（内部使用） |
| text | TEXT | NOT NULL | 转写文本 |
| timestamp | REAL | NOT NULL | 发言时间戳（秒） |
| audio_start | REAL | DEFAULT 0 | 音频起始位置（秒） |
| audio_end | REAL | DEFAULT 0 | 音频结束位置（秒） |

**summaries（会议摘要表）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 摘要唯一标识 |
| meeting_id | INTEGER | NOT NULL UNIQUE, FOREIGN KEY | 关联会议 ID |
| content | TEXT | NOT NULL | 摘要内容（Markdown 格式） |
| created_at | TEXT | NOT NULL | 创建时间（ISO 格式） |

**chat_history（AI 对话历史表）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 对话唯一标识 |
| meeting_id | INTEGER | NOT NULL, FOREIGN KEY | 关联会议 ID |
| question | TEXT | NOT NULL | 用户问题 |
| answer | TEXT | NOT NULL | AI 回答 |
| created_at | TEXT | NOT NULL | 创建时间（ISO 格式） |

**voiceprints（声纹注册表）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 声纹唯一标识 |
| name | TEXT | NOT NULL UNIQUE | 发言人姓名 |
| embedding_path | TEXT | NOT NULL | 声纹特征文件路径（.npy） |
| created_at | TEXT | NOT NULL | 注册时间（ISO 格式） |

##### 核心方法

| 方法 | 说明 |
|------|------|
| `create_meeting(title)` | 创建新会议，返回会议 ID |
| `end_meeting(meeting_id, recording_path)` | 结束会议，更新状态和录音路径 |
| `get_all_meetings()` | 获取所有会议列表（按时间倒序） |
| `get_meeting(meeting_id)` | 获取单个会议详情 |
| `delete_meeting(meeting_id)` | 删除会议及所有关联数据（级联删除） |
| `save_utterance(meeting_id, speaker, text, ...)` | 保存一条发言记录 |
| `get_utterances(meeting_id)` | 获取会议的所有发言记录 |
| `update_speaker_name(old_name, new_name)` | 更新发言人名称（用于陌生人重命名） |
| `get_full_transcript(meeting_id)` | 获取会议完整转写文本 |
| `save_summary(meeting_id, content)` | 保存/更新会议摘要 |
| `get_summary(meeting_id)` | 获取会议摘要 |
| `save_chat(meeting_id, question, answer)` | 保存 AI 对话 |
| `get_chats(meeting_id)` | 获取会议的所有对话记录 |
| `save_voiceprint(name, embedding, voiceprint_dir)` | 保存声纹（文件 + 数据库） |
| `get_all_voiceprints()` | 获取所有已注册声纹 {name: embedding_array} |
| `get_voiceprint_names()` | 获取所有声纹名称列表 |
| `delete_voiceprint(name, voiceprint_dir)` | 删除声纹（文件 + 数据库） |

#### `models/whisper_client.py`
**职责**：语音转写
**核心方法**：
- `load_model()`：懒加载 Whisper 模型
- `transcribe(audio_data, language)`：转写音频为文本
- `is_loaded()`：检查模型状态

#### `models/speaker_recognizer.py`
**职责**：说话人识别
**核心方法**：
- `load_model()`：加载 pyannote/embedding 模型
- `extract_embedding(audio_data)`：提取声纹特征向量
- `identify_speaker(embedding, voiceprints)`：与声纹库比对
- `get_unknown_speaker_label()`：分配陌生人编号

#### `models/llm_client.py`
**职责**：AI 对话与摘要生成
**核心方法**：
- `generate_summary(transcript)`：生成会议摘要
- `chat(question, context)`：多轮对话

#### `models/voiceprint_manager.py`
**职责**：声纹注册管理
**核心方法**：
- `start_recording()` / `stop_recording()`：录音控制
- `register_voiceprint(name, audio_data)`：注册声纹
- `list_voiceprints()`：获取声纹列表
- `delete_voiceprint(name)`：删除声纹

#### `models/realtime_transcriber.py`
**职责**：实时转写引擎
**核心方法**：
- `start()` / `stop()`：会议控制
- `transcribe_chunk(audio_data)`：分片转写
- `identify_speaker(audio_data)`：说话人识别
**信号**：
- `transcribed`：转写完成
- `speaker_identified`：说话人识别完成
- `status_changed`：状态变化

### 4.3 View 层

#### `views/main_window.py`
**职责**：主窗口 UI 与交互
**关键组件**：
- 会议列表（左侧）
- 录音控制 + 转写区域（中间）
- AI 摘要 + 对话（右侧）
- 声纹管理对话框
**关键方法**：
- `_on_start_clicked()`：开始会议
- `_on_pause_clicked()`：暂停会议
- `_on_stop_clicked()`：结束会议
- `_generate_summary()`：生成 AI 摘要
- `_chat()`：AI 对话

#### `views/ui_styles.py`
**职责**：UI 样式定义
**内容**：
- 深色主题 QSS
- 颜色常量（Colors）
- 气泡样式生成器

### 4.4 Utils 层

#### `utils/config_manager.py`
**职责**：配置管理
**配置项**：
- `glm_api_key`：智谱 API Key
- `hf_token`：HuggingFace Token
- `whisper_model_size`：Whisper 模型大小
- `speaker_threshold`：说话人相似度阈值
- `audio_sample_rate`：音频采样率

---

## 5. 数据流

### 5.1 会议录制流程

```
用户点击"开始"
    ↓
RealtimeTranscriber.start()
    ↓
sounddevice.InputStream (录音线程)
    ↓
音频队列 (Audio Queue)
    ↓
RealtimeTranscriber.transcribe_chunk() (转写线程)
    ├─ WhisperClient.transcribe() → 文本
    └─ SpeakerRecognizer.identify_speaker() → 说话人
    ↓
信号发送 → MainWindow._on_transcribed()
    ↓
UI 更新 (气泡显示)
    ↓
Database.save_transcript() (数据库存储)
```

### 5.2 声纹注册流程

```
用户输入姓名 + 录音
    ↓
VoiceprintManager.start_recording()
    ↓
sounddevice.InputStream (录音线程)
    ↓
VoiceprintManager.stop_recording() → audio_data
    ↓
SpeakerRecognizer.extract_embedding(audio_data)
    ↓
Database.save_voiceprint(name, embedding)
    ↓
UI 刷新声纹列表
```

### 5.3 AI 摘要生成流程

```
用户点击"生成摘要"
    ↓
Database.get_transcripts(meeting_id) → 完整转写文本
    ↓
LLMClient.generate_summary(transcript)
    ↓
智谱 GLM-4.5-Air API 调用
    ↓
Database.save_summary(meeting_id, summary)
    ↓
UI 显示摘要
```

---

## 6. 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| **UI 框架** | PySide6 (Qt6) | 跨平台桌面应用 |
| **语音转写** | faster-whisper | 实时语音转写 |
| **声纹识别** | pyannote.audio | 说话人识别 |
| **LLM** | 智谱 GLM-4.5-Air | 摘要生成 + 对话 |
| **数据库** | SQLite | 数据持久化 |
| **音频处理** | sounddevice, soundfile | 录音 + 播放 |
| **数值计算** | NumPy, PyTorch | 音频数据处理 |
| **配置管理** | JSON | 配置文件 |

---

## 7. 部署架构

### 7.1 开发环境

```
Python 3.8+
├── .venv/ (虚拟环境)
│   ├── PySide6
│   ├── faster-whisper
│   ├── pyannote.audio
│   ├── torch
│   └── ...
├── config.json
└── meetwise.db
```

### 7.2 生产环境

```
MeetWise.exe (PyInstaller 打包)
├── models/ (模型缓存)
│   ├── faster-whisper/
│   └── pyannote/embedding/
├── voiceprints/ (声纹数据)
├── recordings/ (录音文件)
├── meetwise.db
└── config.json
```

---

## 8. 性能优化

### 8.1 模型加载
- **懒加载**：模型首次使用时加载
- **后台预加载**：启动时异步加载，避免 UI 阻塞
- **缓存机制**：模型文件缓存到本地，避免重复下载

### 8.2 实时转写
- **分片处理**：音频分片转写，降低延迟
- **VAD 过滤**：静音段自动过滤，减少无效转写
- **线程隔离**：转写在独立线程，不影响 UI 响应

### 8.3 数据库
- **批量插入**：转写分段批量写入
- **索引优化**：关键字段建立索引
- **连接池**：复用数据库连接

---

## 9. 安全考虑

### 9.1 API 密钥
- 配置文件存储（不提交到版本控制）
- 环境变量支持（可选）

### 9.2 数据隐私
- 本地数据库存储，不上传云端
- 声纹数据本地保存
- 录音文件本地存储

### 9.3 输入验证
- 音频数据长度检查
- 用户输入格式验证
- SQL 注入防护（参数化查询）

---

## 10. 扩展性设计

### 10.1 插件化架构
- 模型接口抽象（WhisperClient、LLMClient）
- 支持替换不同模型（如 OpenAI Whisper、GPT-4）

### 10.2 配置化
- 所有阈值、参数可配置
- 支持多语言扩展

### 10.3 国际化
- UI 文本提取到配置文件
- 支持多语言切换

---

## 11. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-06-24 | 初始版本，MVC 架构重构 |

---

## 12. 参考资料

- [PySide6 官方文档](https://doc.qt.io/qtforpython/)
- [faster-whisper 文档](https://github.com/SYSTRAN/faster-whisper)
- [pyannote.audio 文档](https://github.com/pyannote/pyannote-audio)
- [智谱 GLM API 文档](https://open.bigmodel.cn/dev/api)