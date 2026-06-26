# 智会 MeetWise 设计文档

## 1. 项目概述

### 1.1 项目名称
智会 MeetWise - AI 会议纪要生成器

### 1.2 项目定位
一款基于 Python 的桌面客户端应用，通过实时录音、语音转写、说话人识别和大语言模型摘要生成，为用户提供从会议记录到结构化纪要的全流程自动化解决方案。

### 1.3 核心能力
- **实时录音与转写**：基于麦克风采集音频，使用 Faster-Whisper 模型进行离线语音转写
- **说话人识别**：基于 pyannote.audio 声纹模型，自动区分不同发言人
- **声纹注册与管理**：支持用户预先注册声纹，实现个性化说话人识别
- **AI 智能摘要**：调用智谱 GLM-4.5-Air 大语言模型，自动生成结构化会议纪要
- **AI 对话问答**：基于会议内容，支持自然语言问答交互
- **会议历史管理**：基于 SQLite 本地存储，支持会议记录的增删查改

### 1.4 技术特点
- **全离线语音处理**：Whisper 和 pyannote 模型本地运行，无需联网即可转写
- **实时性**：每 3 秒自动执行一次转写，延迟可控
- **线程安全**：所有耗时操作在子线程执行，UI 始终保持响应
- **单文件部署**：通过 PyInstaller 打包为单个 .exe 文件

---

## 2. 目录结构

```
MeetWise/
│
├── main.py                          # 程序入口
├── requirements.txt                 # Python 依赖清单
├── meetwise.spec                    # PyInstaller 打包配置
│
├── meetwise/                        # 应用源代码包
│   ├── __init__.py                  # 包标识文件
│   ├── database.py                  # 数据库访问层（SQLite CRUD）
│   │
│   ├── view/                        # 视图层（UI 界面）
│   │   ├── __init__.py
│   │   ├── main_window.py           # 主窗口（UI 布局 + 交互逻辑）
│   │   └── ui_styles.py            # 样式定义（深色主题、配色常量）
│   │
│   ├── services/                    # 业务服务层
│   │   ├── __init__.py
│   │   ├── realtime_transcriber.py  # 实时转写引擎（协调录音/转写/识别）
│   │   ├── speaker_recognizer.py    # 说话人识别（声纹特征提取与比对）
│   │   ├── voiceprint_manager.py    # 声纹注册管理
│   │   ├── whisper_client.py        # Whisper 语音转写封装
│   │   └── llm_client.py           # 智谱 GLM API 客户端
│   │
│   └── utils/                       # 工具/基础设施层
│       ├── __init__.py
│       └── config_manager.py        # 配置管理（单例模式）
│
├── resources/                       # 静态资源（打包时附带）
│   └── config.json                  # 应用配置文件
│
├── data/                            # 运行时数据（不打包，需 gitignore）
│   ├── meetwise.db                  # SQLite 数据库文件
│   ├── recordings/                  # 录音文件（WAV 格式）
│   │   └── meeting_{id}.wav
│   └── voiceprints/                 # 声纹数据（NumPy 数组）
│       └── {name}.npy
│
├── scripts/                         # 工具脚本
│   └── download_models.py           # 模型预下载脚本
│
└── docs/                            # 项目文档
    ├── requirements_spec.md         # 需求规格说明书
    ├── deployment_guide.md          # 开发与部署运维手册
    └── design.md                    # 设计文档（本文件）
```

### 2.1 目录职责说明

| 目录 | 职责 | 打包行为 |
|------|------|---------|
| `meetwise/` | 应用源代码，包含所有 Python 模块 | 打包进 exe |
| `meetwise/view/` | 视图层，负责 UI 界面展示和用户交互 | 打包进 exe |
| `meetwise/services/` | 业务服务层，封装核心算法和外部 API 调用 | 打包进 exe |
| `meetwise/utils/` | 工具层，提供配置管理等基础设施 | 打包进 exe |
| `resources/` | 静态配置文件 | 打包时附带 |
| `data/` | 运行时生成的数据文件 | 不打包，用户机器上运行时创建 |
| `scripts/` | 辅助脚本，开发阶段使用 | 不打包 |
| `docs/` | 项目文档 | 不打包 |

---

## 3. 技术栈

### 3.1 核心框架

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| GUI 框架 | PySide6 | 6.8.3 | 桌面应用界面 |
| 编程语言 | Python | 3.12+ | 应用开发 |
| 数据库 | SQLite3 | 内置 | 本地数据持久化 |
| 打包工具 | PyInstaller | latest | 单文件 exe 打包 |

### 3.2 AI 与语音处理

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 语音转写 | Faster-Whisper | >=0.10.0 | 离线语音识别（CTranslate2 加速） |
| 声纹模型 | pyannote.audio | >=3.1.0 | 说话人嵌入向量提取 |
| 深度学习 | PyTorch | >=2.0.0 | pyannote 模型的推理后端 |
| 音频处理 | torchaudio | >=2.0.0 | 音频格式转换 |
| 大语言模型 | 智谱 GLM-4.5-Air | API | 会议摘要生成与对话 |
| LLM SDK | openai | >=1.0.0 | 调用 GLM API（兼容 OpenAI 接口） |

### 3.3 音频采集与处理

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 实时录音 | sounddevice | >=0.4.6 | 麦克风音频流采集（PortAudio） |
| 音频文件 I/O | soundfile | >=0.12.0 | WAV 文件读写 |
| 音频处理 | numpy | >=1.24.0 | 音频数据矩阵运算 |
| 音频处理 | pydub | >=0.25.1 | 音频片段操作 |
| 文本转换 | zhconv | >=1.4.0 | 简繁转换（统一转写结果为简体中文） |

### 3.4 日志系统

| 类别 | 技术 | 用途 |
|------|------|------|
| 日志模块 | logging | 控制台显示 WARNING 及以上，文件保留详细日志 |
| 日志文件 | meetwise.log | 记录所有 INFO/DEBUG/ERROR 日志，方便排查问题 |

### 3.5 开发环境

| 项目 | 规格 |
|------|------|
| 操作系统 | Windows 10/11 |
| IDE | PyCharm |
| Python 版本 | 3.12+ |
| PySide6 版本 | 6.8.3（不建议升级到 6.11.x，存在 DLL 兼容性问题） |

---

## 4. 架构设计

### 4.1 分层架构

```
┌─────────────────────────────────────────────────────┐
│                    main.py (入口)                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │              view/ (视图层)                   │    │
│  │  main_window.py    ui_styles.py             │    │
│  │  - 界面布局         - 深色主题样式             │    │
│  │  - 用户交互         - 配色常量                │    │
│  │  - 信号槽连接       - 气泡组件样式            │    │
│  └──────────┬──────────────────┬───────────────┘    │
│             │                  │                     │
│             ▼                  ▼                     │
│  ┌────────────────────┐ ┌────────────────────────┐  │
│  │  services/ (服务层)  │ │  utils/ (工具层)       │  │
│  │                    │ │                        │  │
│  │  RealtimeTranscriber│ │  ConfigManager        │  │
│  │  SpeakerRecognizer  │ │  (单例，全局配置)       │  │
│  │  VoiceprintManager  │ │                        │  │
│  │  WhisperClient      │ │                        │  │
│  │  LLMClient          │ │                        │  │
│  └────────┬───────────┘ └────────────────────────┘  │
│           │                                          │
│           ▼                                          │
│  ┌─────────────────────────────────────────────┐    │
│  │           database.py (数据层)               │    │
│  │  - SQLite 连接管理                           │    │
│  │  - 会议/发言/摘要/对话/声纹 CRUD             │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
├─────────────────────────────────────────────────────┤
│              resources/ (静态资源)                    │
│              config.json (配置文件)                   │
├─────────────────────────────────────────────────────┤
│              data/ (运行时数据)                       │
│              meetwise.db / recordings/ / voiceprints/│
└─────────────────────────────────────────────────────┘
```

### 4.2 模块职责

#### 视图层（view/）

| 模块 | 类名 | 职责 |
|------|------|------|
| main_window.py | MainWindow | 主窗口，负责界面布局、用户交互、信号槽连接、协调各服务模块 |
| ui_styles.py | - | 深色主题样式表（QSS）、Colors 配色常量类、气泡组件样式函数 |

#### 服务层（services/）

| 模块 | 类名 | 职责 |
|------|------|------|
| realtime_transcriber.py | RealtimeTranscriber(QThread) | 核心引擎：协调录音采集、声纹识别、语音转写，通过 Qt 信号通知 UI |
| speaker_recognizer.py | SpeakerRecognizer | 声纹特征提取（pyannote）+ 余弦相似度比对 + 陌生人编号管理 |
| voiceprint_manager.py | VoiceprintManager | 声纹注册流程管理：录音采样、特征提取、保存到数据库 |
| whisper_client.py | WhisperClient | Faster-Whisper 模型封装：加载模型、执行转写、返回分段文本 |
| llm_client.py | LLMClient | 智谱 GLM API 封装：生成会议摘要、基于会议内容的 AI 对话 |

#### 工具层（utils/）

| 模块 | 类名 | 职责 |
|------|------|------|
| config_manager.py | ConfigManager | 配置管理（单例模式）：加载/保存 config.json、提供全局配置访问接口 |

#### 数据层

| 模块 | 类名 | 职责 |
|------|------|------|
| database.py | Database | SQLite 数据库管理：建表、连接、会议/发言/摘要/对话/声纹的 CRUD 操作 |

### 4.3 模块依赖关系

```
main.py
  └── view/main_window.py (MainWindow)
        ├── services/realtime_transcriber.py (RealtimeTranscriber)
        │     ├── services/whisper_client.py (WhisperClient)
        │     └── services/speaker_recognizer.py (SpeakerRecognizer)
        ├── services/speaker_recognizer.py (SpeakerRecognizer)
        ├── services/voiceprint_manager.py (VoiceprintManager)
        │     └── services/speaker_recognizer.py (SpeakerRecognizer)
        ├── services/llm_client.py (LLMClient)
        ├── services/whisper_client.py (WhisperClient)
        ├── database.py (Database)
        ├── utils/config_manager.py (ConfigManager)
        └── view/ui_styles.py (样式常量与函数)
```

**依赖规则：**
- view/ 可以调用 services/、utils/ 和 database
- services/ 之间通过构造函数注入依赖，不直接 import 同层模块（除 realtime_transcriber 调用 whisper_client 和 speaker_recognizer）
- services/ 可以调用 database 和 utils
- database 和 utils 不依赖其他任何模块（最底层）

---

## 5. 数据库设计

### 5.1 数据库类型
SQLite3（本地文件数据库，无需额外安装数据库服务）

### 5.2 数据库文件路径
`data/meetwise.db`

### 5.3 表结构设计

#### meetings（会议表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 会议 ID |
| title | TEXT | NOT NULL | 会议标题 |
| start_time | TEXT | NOT NULL | 开始时间（ISO 8601 格式） |
| end_time | TEXT | 可空 | 结束时间 |
| status | TEXT | DEFAULT 'recording' | 状态：recording / ended |
| recording_path | TEXT | 可空 | 录音文件路径 |
| is_pinned | INTEGER | DEFAULT 0 | 是否置顶（0=否，1=是） |

#### utterances（发言记录表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 记录 ID |
| meeting_id | INTEGER | NOT NULL, FK → meetings.id | 所属会议 |
| speaker | TEXT | NOT NULL | 发言人名称（如"张三"或"陌生人A"） |
| speaker_id | TEXT | 可空 | 发言人标识（声纹匹配的名称） |
| text | TEXT | NOT NULL | 转写文本内容 |
| timestamp | REAL | NOT NULL | 时间戳（秒，相对于会议开始） |
| audio_start | REAL | NOT NULL, DEFAULT 0 | 音频片段起始时间 |
| audio_end | REAL | NOT NULL, DEFAULT 0 | 音频片段结束时间 |

**外键约束：** ON DELETE CASCADE（删除会议时自动删除关联发言）

#### summaries（摘要表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 摘要 ID |
| meeting_id | INTEGER | NOT NULL, UNIQUE, FK → meetings.id | 所属会议（一对一） |
| content | TEXT | NOT NULL | 摘要内容（Markdown 格式） |
| created_at | TEXT | NOT NULL | 生成时间 |

**外键约束：** ON DELETE CASCADE

#### chat_history（对话历史表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 对话 ID |
| meeting_id | INTEGER | NOT NULL, FK → meetings.id | 所属会议 |
| question | TEXT | NOT NULL | 用户问题 |
| answer | TEXT | NOT NULL | AI 回答 |
| created_at | TEXT | NOT NULL | 对话时间 |

**外键约束：** ON DELETE CASCADE

#### voiceprints（声纹注册表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 声纹 ID |
| name | TEXT | NOT NULL, UNIQUE | 注册人姓名 |
| embedding_path | TEXT | NOT NULL | 声纹向量文件路径（.npy） |
| created_at | TEXT | NOT NULL | 注册时间 |

### 5.4 ER 关系图

```
┌──────────┐       1:N       ┌──────────────┐
│ meetings │────────────────►│ utterances    │
│          │                 │              │
│    1:1   │                 └──────────────┘
│          │       1:N       ┌──────────────┐
│          │────────────────►│ chat_history  │
│          │                 └──────────────┘
│          │       1:1       ┌──────────────┐
│          │────────────────►│ summaries     │
└──────────┘                 └──────────────┘

┌──────────────┐
│ voiceprints   │  (独立表，不依赖会议)
│              │
│  name (UNIQUE)│
│  embedding_path│
└──────────────┘
```

---

## 6. 核心流程

### 6.1 会议录制与转写流程

```
用户点击「开始会议」
    │
    ▼
创建会议记录 (database.create_meeting)
    │
    ▼
初始化服务组件：
    ├── ConfigManager 读取配置
    ├── WhisperClient 加载 Faster-Whisper 模型
    ├── SpeakerRecognizer 加载 pyannote 声纹模型
    └── 从数据库加载已注册声纹库
    │
    ▼
启动 RealtimeTranscriber 子线程 (QThread)
    │
    ▼
┌─────────────────────────────────────────┐
│          子线程主循环                      │
│                                         │
│  ┌──────────────┐                       │
│  │ PortAudio 回调 │──── queue.put ────►  │
│  │ (C 线程)       │   (只做入队操作)      │
│  └──────────────┘                       │
│                                         │
│  每 3 秒：                               │
│  ┌─────────────────────────────────┐    │
│  │ 1. 从队列取出音频缓冲             │    │
│  │ 2. 声纹识别 (SpeakerRecognizer)  │    │
│  │ 3. 语音转写 (WhisperClient)      │    │
│  │ 4. Signal 发送结果到 UI          │    │
│  │ 5. 保存到数据库 (Database)       │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
    │
    ▼ (用户点击「结束会议」)
    │
停止音频流 → 处理剩余缓冲 → 保存完整录音 WAV
    │
    ▼
更新会议状态为 ended → 保存录音路径
    │
    ▼
弹出命名对话框 → 用户输入会议名称（默认格式：会议--日期--时长）
    │
    ▼
更新会议标题 (database.update_meeting_title)
    │
    ▼
刷新会议列表（显示时长、置顶优先）
```

### 6.2 说话人识别流程

```
音频片段 (16kHz, float32, 单声道)
    │
    ▼
pyannote Inference 提取 512 维声纹向量
    │
    ▼
L2 归一化
    │
    ▼
与已注册声纹库逐一计算余弦相似度
    │
    ├── 最高相似度 >= 0.7 → 返回注册人姓名
    │
    └── 最高相似度 < 0.7 → 分配陌生人编号
          │
          ├── embedding 指纹匹配已有陌生人 → 复用编号
          │
          └── 全新陌生人 → 分配新编号（陌生人A, B, C...）
```

### 6.3 声纹注册流程

```
用户在 UI 中点击「注册声纹」
    │
    ▼
录制 3-5 秒音频样本
    │
    ▼
SpeakerRecognizer.extract_embedding 提取特征向量
    │
    ▼
Database.save_voiceprint 保存：
    ├── .npy 文件 → data/voiceprints/{name}.npy
    └── 数据库记录 → voiceprints 表
    │
    ▼
注册完成，后续会议中可自动识别该说话人
```

### 6.4 AI 摘要生成流程

```
会议结束后
    │
    ▼
Database.get_full_transcript 获取完整转写文本
    │
    ▼
构造 Prompt：
    ├── System: "你是专业的会议纪要助手..."
    └── User: 转写文本 + 摘要要求（关键点/待办/结论）
    │
    ▼
LLMClient → 智谱 GLM-4.5-Air API
    │
    ▼
返回 Markdown 格式结构化摘要
    │
    ▼
Database.save_summary 保存到数据库
```

---

## 7. 线程模型

### 7.1 线程架构

```
┌──────────────────────────────────────────────────┐
│                 主线程 (UI 线程)                    │
│  QApplication → MainWindow                        │
│  - 界面渲染、用户交互、事件循环                      │
│  - 接收子线程 Signal 更新 UI                        │
└───────────────────┬──────────────────────────────┘
                    │ Signal/Slot
                    │
┌───────────────────▼──────────────────────────────┐
│          RealtimeTranscriber (QThread 子线程)      │
│  - 音频缓冲管理与转写调度                           │
│  - 调用 WhisperClient.transcribe()                 │
│  - 调用 SpeakerRecognizer.extract_embedding()      │
│  - 通过 Signal 发送结果到主线程                      │
└───────────────────┬──────────────────────────────┘
                    │ queue.put (线程安全队列)
                    │
┌───────────────────▼──────────────────────────────┐
│       PortAudio 音频回调线程 (C 语言层)             │
│  - sounddevice InputStream 回调                    │
│  - 只做 queue.put，绝不做耗时操作                   │
└──────────────────────────────────────────────────┘
```

### 7.2 线程安全原则

| 原则 | 说明 |
|------|------|
| 音频回调只做入队 | sounddevice 回调只执行 `queue.put(indata.copy())`，不做任何处理 |
| UI 操作只在主线程 | 子线程通过 Qt Signal/Slot 机制通知主线程更新界面 |
| 子线程启动前检查 | 发射信号前检查窗口是否已关闭（RuntimeError 捕获 + `_closing` 标志） |
| 模型加载在子线程 | Whisper 和 pyannote 模型加载耗时较长，在 QThread.run() 中执行 |

### 7.3 Qt 信号定义（RealtimeTranscriber）

| 信号 | 参数 | 用途 |
|------|------|------|
| utterance_ready | (speaker, text, timestamp, audio_start, audio_end) | 转写结果就绪 |
| status_changed | (status_text) | 状态信息更新 |
| error_occurred | (error_msg) | 错误信息 |
| meeting_ended | (recording_path) | 会议结束，返回录音路径 |
| duration_updated | (duration_seconds) | 录音时长更新 |

---

## 8. 配置管理

### 8.1 配置文件位置
`resources/config.json`

### 8.2 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| glm_api_key | string | "" | 智谱 API Key |
| glm_base_url | string | "https://open.bigmodel.cn/api/paas/v4/" | 智谱 API 接口地址 |
| glm_model | string | "glm-4.5-air" | 使用的 GLM 模型名称 |
| hf_token | string | "" | HuggingFace 访问令牌（pyannote 模型需要） |
| whisper_model_size | string | "base" | Whisper 模型大小（tiny/base/small/medium/large） |
| pyannote_model | string | "pyannote/embedding" | 声纹嵌入模型名称 |
| speaker_threshold | float | 0.7 | 说话人识别余弦相似度阈值 |
| audio_sample_rate | int | 16000 | 音频采样率（Hz） |
| transcribe_interval | int | 3 | 转写间隔（秒） |
| voiceprint_dir | string | "voiceprints" | 声纹数据存储目录 |
| recording_dir | string | "recordings" | 录音文件存储目录 |
| db_path | string | "meetwise.db" | 数据库文件路径 |

### 8.3 ConfigManager 设计

- **单例模式**：全局只有一个 ConfigManager 实例，确保配置一致性
- **懒加载**：首次访问时加载配置文件
- **自动补齐**：如果 config.json 缺少某些配置项，自动用默认值补齐
- **文件不存在时自动创建**：首次运行自动生成带默认值的 config.json

---

## 9. 外部接口

### 9.1 智谱 GLM API

| 接口 | 方法 | 用途 |
|------|------|------|
| chat/completions | POST | 生成摘要、AI 对话 |

调用方式：通过 openai SDK，兼容 OpenAI 接口格式。

请求示例：
```python
client = OpenAI(api_key=api_key, base_url=base_url)
response = client.chat.completions.create(
    model="glm-4.5-air",
    messages=[
        {"role": "system", "content": "你是一位专业的会议纪要助手..."},
        {"role": "user", "content": transcript}
    ],
    temperature=0.3,
    max_tokens=2000
)
```

### 9.2 HuggingFace 模型

| 模型 | 用途 | 大小 | 下载方式 |
|------|------|------|---------|
| Systran/faster-whisper-base | 语音转写 | ~140MB | 首次运行时自动下载 |
| pyannote/embedding | 声纹特征提取 | ~100MB | 需要 hf_token 授权 |

---

## 10. 样式设计

### 10.1 配色方案

采用深色主题，以深蓝/黑/紫色为主色调：

| 常量名 | 色值 | 用途 |
|--------|------|------|
| BG_DARKEST | #0a0e1a | 最深背景（窗口底色） |
| BG_DARK | #111827 | 深色背景（侧边栏） |
| BG_CARD | #1a1f36 | 卡片背景（内容区） |
| ACCENT_PURPLE | #7c3aed | 主色调紫（按钮、强调） |
| ACCENT_INDIGO | #6366f1 | 靛蓝色（辅助） |
| ACCENT_LIGHT | #8b5cf6 | 浅紫色（悬停、高亮） |

### 10.2 UI 组件规范

- **气泡组件**：用于显示实时转写文本，按说话人区分颜色
- **侧边栏**：会议列表，支持选中/新建/删除操作
- **主内容区**：转写文本展示 + AI 摘要展示
- **底部栏**：录音控制按钮 + 状态指示器 + 录音时长

---

## 11. 打包部署

### 11.1 打包工具
PyInstaller，使用 meetwise.spec 配置文件

### 11.2 打包命令
```bash
pyinstaller meetwise.spec
```

### 11.3 关键配置项

| 配置 | 说明 |
|------|------|
| hiddenimports | 需要显式声明所有动态导入的模块（faster_whisper、pyannote、torch 等） |
| datas | 需要打包的资源文件（resources/config.json） |
| pathex | Python 路径搜索目录 |
| onefile | 打包为单个 exe 文件 |

### 11.4 首次运行流程

1. 用户双击 exe 文件
2. 程序自动创建 data/ 目录（recordings/、voiceprints/、meetwise.db）
3. 自动创建 resources/config.json（如不存在）
4. 用户首次使用时，需填入 glm_api_key 和 hf_token
5. 首次会议时，自动下载 Whisper 和 pyannote 模型（需联网）
6. 也可提前运行 scripts/download_models.py 预下载模型

---

## 12. 数据流向总览

```
麦克风 (PortAudio)
    │
    ▼ queue.put
音频缓冲 (numpy float32, 16kHz)
    │
    ├──► SpeakerRecognizer ──► pyannote 模型 ──► 声纹向量 (512维)
    │                                              │
    │                                    余弦相似度比对
    │                                              │
    │                                    说话人标签 (string)
    │
    └──► WhisperClient ──► faster-whisper 模型 ──► 转写文本 (segments)
                                                     │
                              ┌──────────────────────┘
                              ▼
                    utterance_ready Signal
                              │
                              ▼
                    MainWindow (UI 线程)
                    ├── 显示气泡组件
                    └── Database.save_utterance
                              │
                    (会议结束后)
                              ▼
                    LLMClient ──► 智谱 GLM API ──► 结构化摘要
                              │
                              ▼
                    Database.save_summary
```

---

> 
