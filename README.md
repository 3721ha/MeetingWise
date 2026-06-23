# 智会 MeetWise - AI 会议纪要生成器

> 一款基于 Python 的桌面客户端，支持实时语音转写、说话人声纹识别、AI 智能摘要生成与会议内容对话，帮助你高效记录和管理每一次会议。

---

## 项目简介

**智会 MeetWise** 是一款面向团队协作场景的 AI 会议纪要生成工具。通过麦克风实时录音，结合语音识别与声纹识别技术，自动将会议内容转写为"发言人：对话内容"的结构化文本，并支持一键生成会议摘要、与 AI 对话回顾会议细节。

最终产物可打包为 `.exe` 可执行文件，开箱即用，无需安装 Python 环境。

---

## 核心功能

| 功能模块 | 说明 | 技术方案 |
| --- | --- | --- |
| 声纹注册 | 会前录制 10-30 秒语音，注册发言人声纹特征 | pyannote.audio 提取声纹向量，SQLite 存储 |
| 实时录音转写 | 点击"开始会议"后，实时捕获麦克风音频并转写为文字 | sounddevice 流式录音 + faster-whisper 增量转写 |
| 说话人识别 | 自动识别当前发言人是已注册的哪位成员 | pyannote.audio 声纹特征 + 余弦相似度比对（阈值 0.7） |
| 陌生人管理 | 未注册的发言人自动编号（陌生人A/B/C），支持右键重命名 | 自动分配编号 + 数据库同步更新 |
| AI 摘要生成 | 会议结束后一键生成结构化摘要（关键点、待办、结论） | 智谱 GLM-4.5-Air API |
| AI 对话 | 针对会议内容向 AI 提问，支持多轮对话 | 智谱 GLM-4.5-Air API + 全文上下文 |
| 会议管理 | 历史会议列表、查看详情、删除会议 | SQLite 数据库，左侧面板按时间排序 |
| 语音回放定位 | 点击任意转写气泡，自动跳转到对应语音位置播放 | 完整录音保存 + 时间戳定位 + 内置播放器 |

---

## 详细需求规格

### 需求 1：声纹注册

| 项目 | 描述 |
| --- | --- |
| 需求编号 | REQ-001 |
| 功能名称 | 声纹注册（会前准备） |
| 触发方式 | 用户点击"声纹管理"按钮，弹出注册对话框 |
| 输入 | 用户姓名（文本）+ 10-30 秒语音录音（16kHz 单声道） |
| 输出 | 512 维声纹特征向量（.npy 文件），注册成功提示 |
| 处理流程 | 开始录音 - sounddevice 流式采集 - 停止录音 - pyannote.audio 提取 embedding - 保存为 voiceprints/{name}.npy - 数据库记录路径 |
| 数据库存储 | voiceprints 表：id（自增主键）、name（姓名，唯一）、embedding_path（.npy 文件路径）、created_at（注册时间） |
| 文件存储 | voiceprints/{name}.npy（numpy 数组，512 维 float32 向量） |
| 关键约束 | 录音时长 10-30 秒，低于 10 秒提示"录音太短"；同名已存在时提示"该姓名已注册" |
| 线程要求 | 录音在子线程，embedding 提取在子线程，UI 不阻塞 |

### 需求 2：实时录音转写

| 项目 | 描述 |
| --- | --- |
| 需求编号 | REQ-002 |
| 功能名称 | 实时会议录音与转写 |
| 触发方式 | 用户点击"开始会议"按钮 |
| 输入 | 麦克风实时音频流（16kHz、单声道、float32） |
| 输出 | 实时气泡消息"发言人：对话内容"，自动滚动显示 |
| 处理流程 | sounddevice 回调采集音频 - 入队（queue.put） - 每 3 秒取出累积音频 - faster-whisper 转写 - 通过 Signal 发送到 UI - 同时保存到数据库 - 同步保存完整音频到 recordings/ 目录 |
| 数据库存储 | meetings 表：id（自增主键）、title（会议标题）、start_time（开始时间）、end_time（结束时间）、status（状态：recording/ended）、recording_path（录音文件路径） |
| 数据库存储 | utterances 表：id（自增主键）、meeting_id（关联会议）、speaker（发言人名称）、speaker_id（声纹ID或陌生人编号）、text（转写文本）、timestamp（时间戳，秒）、audio_start（音频起始时间）、audio_end（音频结束时间） |
| 关键约束 | sounddevice 回调只做 queue.put，严禁耗时操作；转写间隔可配置（默认 3 秒）；自动滚动到底部；完整录音保存为 WAV 文件供回放 |
| 线程要求 | 录音回调在 PortAudio C 线程；转写在 QThread 子线程；UI 更新通过 Signal/Slot |

### 需求 3：说话人识别

| 项目 | 描述 |
| --- | --- |
| 需求编号 | REQ-003 |
| 功能名称 | 实时说话人识别 |
| 触发方式 | 每次转写前自动触发 |
| 输入 | 音频片段（numpy 数组）+ 已注册声纹库（dict） |
| 输出 | 发言人名称（已注册姓名 或 "陌生人A/B/C..."） |
| 处理流程 | pyannote.audio 提取当前片段 embedding - 遍历声纹库计算余弦相似度 - 最高相似度 >= 0.7 返回对应姓名；否则分配陌生人编号 |
| 数据库存储 | 读取 voiceprints 表获取所有已注册声纹 |
| 文件存储 | 读取 voiceprints/{name}.npy 加载声纹向量 |
| 关键约束 | 余弦相似度阈值 0.7（可在 config.json 调整）；陌生人编号按字母序递增（A-B-C）；同一段音频内多个陌生人分别编号 |
| 相似度公式 | cosine_similarity = dot(a, b) / (norm(a) * norm(b))，使用 numpy 计算 |

### 需求 4：陌生人重命名

| 项目 | 描述 |
| --- | --- |
| 需求编号 | REQ-004 |
| 功能名称 | 陌生人重命名 |
| 触发方式 | 用户右键点击陌生人气泡 - 选择"重命名" - 弹出输入框 |
| 输入 | 旧名称（如"陌生人A"）+ 新名称（用户输入的姓名） |
| 输出 | 更新后的气泡显示 + 数据库同步更新 |
| 处理流程 | 弹出 QInputDialog - 用户输入新名字 - 更新当前气泡 UI - 更新数据库中所有 speaker=旧名称 的 utterances 记录 - 后续该编号发言人也使用新名字 |
| 数据库更新 | UPDATE utterances SET speaker = '新名字' WHERE speaker = '陌生人A'（所有会议同步） |
| 关键约束 | 重命名后所有历史会议中的该陌生人都显示新名字；如果新名字与已注册声纹重名，提示冲突 |
| UI 交互 | 右键菜单仅在陌生人/未注册发言人气泡上显示"重命名"选项 |

### 需求 5：AI 摘要生成

| 项目 | 描述 |
| --- | --- |
| 需求编号 | REQ-005 |
| 功能名称 | AI 智能摘要生成 |
| 触发方式 | 用户点击右侧"生成摘要"按钮 |
| 输入 | 本次会议全部转写文本（格式："发言人1：内容\n发言人2：内容..."） |
| 输出 | 结构化 Markdown 摘要（关键点 / 待办事项 / 结论） |
| 处理流程 | 拼接全文 - 构造 Prompt（系统提示词 + 全文） - 调用智谱 GLM-4.5-Air API - 解析返回文本 - 右侧卡片分区显示 - 保存到数据库 |
| 数据库存储 | summaries 表：id（自增主键）、meeting_id（关联会议）、content（摘要全文）、created_at（生成时间） |
| API 参数 | model: glm-4.5-air，temperature: 0.3，max_tokens: 2000 |
| Prompt 模板 | "你是一位专业的会议纪要助手。请根据以下会议转写内容，生成结构化摘要，包含三个部分：\n1. **关键点**：列出 3-5 个核心讨论要点\n2. **待办事项**：列出需要后续跟进的任务，标注负责人\n3. **结论**：总结会议达成的共识和决定\n\n会议内容：\n{transcript}" |
| 线程要求 | API 调用在 QThread 子线程，UI 显示"生成中..."加载状态 |
| 关键约束 | 支持会议进行中或结束后生成；已生成过摘要时可重新生成（覆盖）；网络错误时显示友好提示 |

### 需求 6：AI 对话

| 项目 | 描述 |
| --- | --- |
| 需求编号 | REQ-006 |
| 功能名称 | 会议内 AI 对话（追问） |
| 触发方式 | 用户在右侧下方输入框输入问题 - 点击"发送"或按 Enter |
| 输入 | 用户问题 + 会议全文（作为上下文）+ 历史对话记录 |
| 输出 | AI 回答文本，显示在对话区 |
| 处理流程 | 拼接全文+历史问答+用户问题 - 构造 messages 数组 - 调用智谱 GLM API - 显示回答 - 保存到数据库 |
| 数据库存储 | chat_history 表：id（自增主键）、meeting_id（关联会议）、question（用户问题）、answer（AI 回答）、created_at（提问时间） |
| API 参数 | model: glm-4.5-air，temperature: 0.5，max_tokens: 1500 |
| Prompt 结构 | system: "你是会议纪要助手，请基于以下会议内容回答用户问题。"\n+ 会议全文\n+ 历史对话（最近 5 轮）\n+ 当前问题 |
| 线程要求 | API 调用在 QThread 子线程 |
| 关键约束 | 对话历史自动保存，下次打开会议可查看；支持 Enter 快捷发送；空内容不可发送 |

### 需求 7：会议列表管理

| 项目 | 描述 |
| --- | --- |
| 需求编号 | REQ-007 |
| 功能名称 | 历史会议列表管理 |
| 触发方式 | 左侧面板自动加载，用户点击/右键操作 |
| 输入 | 用户在会议列表中的操作（点击查看详情 / 右键删除） |
| 输出 | 会议详情（转写内容 + 摘要 + 对话记录）或确认删除 |
| 处理流程 | 启动时查询所有会议 - 按时间倒序显示在左侧列表 - 点击加载详情（转写气泡 + 摘要 + 对话） - 右键弹出确认对话框 - 确认后级联删除 |
| 数据库查询 | SELECT * FROM meetings ORDER BY start_time DESC |
| 级联删除 | DELETE FROM chat_history WHERE meeting_id = ? - DELETE FROM summaries WHERE meeting_id = ? - DELETE FROM utterances WHERE meeting_id = ? - DELETE FROM meetings WHERE id = ? |
| 关键约束 | 删除前弹出二次确认对话框；删除后刷新列表；当前正在查看的会议被删除时清空右侧面板 |
| UI 交互 | 列表项显示会议标题 + 时间；选中项高亮；右键菜单："查看详情"/"删除" |

### 需求 8：语音回放定位

| 项目 | 描述 |
| --- | --- |
| 需求编号 | REQ-008 |
| 功能名称 | 点击气泡跳转语音回放 |
| 触发方式 | 用户左键点击任意转写气泡 |
| 输入 | 点击的 utterance 记录（包含 audio_start 和 audio_end 时间戳） |
| 输出 | 从对应时间位置开始播放会议录音 |
| 处理流程 | 点击气泡 - 获取该条 utterance 的 audio_start 时间 - 加载会议的完整录音文件（recordings/{meeting_id}.wav） - 从 audio_start 位置开始播放 - 播放时高亮当前气泡 - 播放完毕取消高亮 |
| 数据库存储 | 读取 meetings 表的 recording_path 字段获取录音文件路径；读取 utterances 表的 audio_start/audio_end 字段 |
| 关键约束 | 录音文件在会议结束时保存为完整 WAV；播放使用 sounddevice 或 pygame.mixer；支持播放中再次点击其他气泡跳转；播放时气泡边框高亮（紫色） |
| UI 交互 | 鼠标悬停气泡时显示手型光标（提示可点击）；点击后气泡边框变为紫色高亮；播放进度条显示当前播放位置 |

---

## 数据库设计

### 表结构总览

| 表名 | 说明 | 主要关联 |
| --- | --- | --- |
| meetings | 会议基本信息 | 被 utterances/summaries/chat_history 引用 |
| utterances | 发言记录（转写文本） | meeting_id 关联 meetings |
| summaries | AI 生成的会议摘要 | meeting_id 关联 meetings（一对一） |
| chat_history | AI 对话记录 | meeting_id 关联 meetings |
| voiceprints | 已注册的声纹信息 | 被 speaker_recognizer 读取 |

### meetings 表

| 字段名 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 会议唯一标识 |
| title | TEXT | NOT NULL | 会议标题（默认"会议 YYYY-MM-DD HH:mm"） |
| start_time | TEXT | NOT NULL | 会议开始时间（ISO 格式） |
| end_time | TEXT | NULL | 会议结束时间（进行中为 NULL） |
| status | TEXT | DEFAULT 'recording' | 会议状态：recording / ended |
| recording_path | TEXT | NULL | 录音文件路径（recordings/{id}.wav） |

### utterances 表

| 字段名 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 发言记录唯一标识 |
| meeting_id | INTEGER | FOREIGN KEY - meetings.id | 所属会议 |
| speaker | TEXT | NOT NULL | 发言人名称（注册姓名或"陌生人X"） |
| speaker_id | TEXT | NULL | 声纹ID（已注册用户）或陌生人编号 |
| text | TEXT | NOT NULL | 转写文本内容 |
| timestamp | REAL | NOT NULL | 发言时间戳（秒，相对于会议开始） |
| audio_start | REAL | NOT NULL | 该段语音在录音文件中的起始时间（秒） |
| audio_end | REAL | NOT NULL | 该段语音在录音文件中的结束时间（秒） |

### summaries 表

| 字段名 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 摘要唯一标识 |
| meeting_id | INTEGER | FOREIGN KEY - meetings.id, UNIQUE | 所属会议（一对一） |
| content | TEXT | NOT NULL | 摘要内容（Markdown 格式） |
| created_at | TEXT | NOT NULL | 摘要生成时间 |

### chat_history 表

| 字段名 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 对话记录唯一标识 |
| meeting_id | INTEGER | FOREIGN KEY - meetings.id | 所属会议 |
| question | TEXT | NOT NULL | 用户提问内容 |
| answer | TEXT | NOT NULL | AI 回答内容 |
| created_at | TEXT | NOT NULL | 提问时间 |

### voiceprints 表

| 字段名 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 声纹记录唯一标识 |
| name | TEXT | NOT NULL, UNIQUE | 发言人姓名 |
| embedding_path | TEXT | NOT NULL | 声纹向量文件路径（.npy） |
| created_at | TEXT | NOT NULL | 注册时间 |

---

## 技术栈

| 层级 | 技术 | 版本要求 | 说明 |
| --- | --- | --- | --- |
| 开发语言 | Python | 3.10+ | 主开发语言 |
| GUI 框架 | PySide6 (Qt for Python) | 6.5+ | 桌面界面框架 |
| 实时录音 | sounddevice | 0.4.6+ | 基于 PortAudio 的流式音频捕获 |
| 语音转写 | faster-whisper | 0.10+ | 基于 CTranslate2 的 Whisper 加速推理 |
| 说话人识别 | pyannote.audio | 3.1+ | 声纹特征提取与比对 |
| 深度学习框架 | PyTorch + torchaudio | 2.0+ | pyannote.audio 的底层依赖 |
| 大语言模型 | 智谱 GLM-4.5-Air | - | 摘要生成 & 对话（兼容 OpenAI 接口） |
| 数据库 | SQLite | - | 本地轻量数据存储 |
| 配置管理 | JSON | - | config.json 配置文件 |
| 打包工具 | PyInstaller | 6.0+ | 打包为 .exe |

---

## 环境要求

| 项目 | 最低要求 | 推荐配置 |
| --- | --- | --- |
| 操作系统 | Windows 10 / macOS 12 / Ubuntu 20.04 | Windows 10/11 |
| Python | 3.10 | 3.11+ |
| 内存 (RAM) | 8 GB | 16 GB+ |
| 硬盘空间 | 5 GB（含模型文件） | 10 GB+ |
| 麦克风 | 必备 | 指向性麦克风效果更佳 |
| 网络 | 首次运行需联网下载模型 & 调用 API | 稳定网络连接 |

> 性能说明：
> - faster-whisper 的 base 模型约 140MB，CPU 模式下转写延迟约 2-3 秒/片段
> - pyannote.audio 依赖 PyTorch，模型约 100MB，首次加载需 10-20 秒
> - 所有耗时操作均在子线程执行，不会导致界面卡顿
> - 如有 NVIDIA GPU，可自动加速推理（需安装 CUDA 版 PyTorch）

---

## 安装步骤

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd MeetWise
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 HuggingFace Token

pyannote.audio 的模型托管在 HuggingFace 上，需要：

1. 注册 HuggingFace 账号（https://huggingface.co/join）
2. 访问 pyannote/embedding 页面（https://huggingface.co/pyannote/embedding），同意用户协议
3. 在 HuggingFace Settings - Access Tokens 中创建 Token
4. 将 Token 填入 config.json 的 hf_token 字段

### 5. 配置智谱 API Key

1. 注册智谱 AI 开放平台（https://open.bigmodel.cn/）
2. 创建 API Key
3. 将 API Key 填入 config.json 的 glm_api_key 字段

---

## 配置说明

项目根目录下的 config.json 包含所有可配置项：

```json
{
  "glm_api_key": "智谱API Key",
  "glm_base_url": "https://open.bigmodel.cn/api/paas/v4/",
  "glm_model": "glm-4.5-air",
  "hf_token": "HuggingFace Token",
  "whisper_model_size": "base",
  "pyannote_model": "pyannote/embedding",
  "speaker_threshold": 0.7,
  "audio_sample_rate": 16000,
  "transcribe_interval": 3,
  "voiceprint_dir": "voiceprints",
  "recording_dir": "recordings",
  "db_path": "meetwise.db"
}
```

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| glm_api_key | 智谱 GLM API 密钥 | 必填 |
| glm_base_url | GLM API 接口地址 | https://open.bigmodel.cn/api/paas/v4/ |
| glm_model | 使用的 GLM 模型名 | glm-4.5-air |
| hf_token | HuggingFace 访问令牌 | 必填 |
| whisper_model_size | Whisper 模型大小（tiny/base/small/medium/large） | base |
| pyannote_model | 声纹识别模型 | pyannote/embedding |
| speaker_threshold | 说话人识别相似度阈值（0-1） | 0.7 |
| audio_sample_rate | 录音采样率 (Hz) | 16000 |
| transcribe_interval | 转写间隔 (秒) | 3 |
| voiceprint_dir | 声纹数据存储目录 | voiceprints |
| recording_dir | 录音文件存储目录 | recordings |
| db_path | SQLite 数据库文件路径 | meetwise.db |

> Whisper 模型选择建议：
> - tiny：约 75MB，速度最快，准确率一般，适合快速测试
> - base：约 140MB，速度与准确率平衡，推荐 CPU 用户
> - small：约 460MB，准确率较高，需要更多内存
> - medium：约 1.5GB，高准确率，建议有 GPU 时使用

---

## 运行方式

### 开发模式运行

```bash
python main.py
```

### 打包为 exe（Windows）

```bash
# 安装 PyInstaller
pip install pyinstaller

# 使用 spec 文件打包
pyinstaller meetwise.spec

# 产物在 dist/ 目录下
```

---

## 使用指南

### 一、声纹注册（会前准备）

1. 点击顶部菜单栏的「声纹管理」按钮
2. 在弹出的对话框中输入发言人姓名
3. 点击「开始录音」，朗读一段 10-30 秒的内容（建议念一段新闻或文章）
4. 录音完成后点击「注册」
5. 系统提取声纹特征并保存，注册成功后会在列表中显示

> 声纹注册只需要做一次，后续会议会自动识别已注册的发言人。

### 二、开始会议

1. 在主界面点击「新建会议」或直接点击「开始会议」
2. 进入实时录音转写模式
3. 转写结果以气泡形式实时显示：
   - 已注册的发言人显示姓名（如"张三："）
   - 未注册的发言人显示编号（如"陌生人A："）
4. 可通过暂停/继续按钮控制录音
5. 点击停止结束会议

### 三、语音回放定位

1. 在转写区域找到任意气泡消息
2. 左键点击该气泡
3. 系统自动从该段语音对应的时间位置开始播放会议录音
4. 播放时当前气泡边框高亮为紫色
5. 播放过程中可点击其他气泡跳转到新位置

### 四、重命名陌生人

1. 在转写区域找到陌生人的气泡消息
2. 右键点击该气泡
3. 选择「重命名」
4. 输入真实姓名，点击确认
5. 系统自动更新当前会议和所有历史会议中的显示

### 五、生成 AI 摘要

1. 会议进行中或结束后，点击右侧「生成摘要」按钮
2. 系统将全部转写文本发送给智谱 GLM
3. 生成结构化摘要，包含：
   - 关键点：会议核心讨论内容
   - 待办事项：需要后续跟进的任务
   - 结论：会议达成的共识和决定

### 六、AI 对话

1. 在右侧下方的输入框中输入问题
2. 系统会将本次会议全部内容作为背景上下文
3. 支持多轮对话，对话历史自动保存
4. 示例问题：
   - "这次会议决定了哪些事项？"
   - "张三负责什么任务？"
   - "帮我整理一下待办清单"

### 七、管理历史会议

1. 左侧面板显示所有历史会议（按时间排序）
2. 点击某条会议可查看完整详情（转写内容、摘要、对话记录）
3. 右键点击可删除会议（级联删除所有关联数据）

---

## 项目结构

```
MeetWise/
|-- main.py                    # 程序入口
|-- main_window.py             # 主窗口 UI 布局与交互逻辑
|-- voiceprint_manager.py      # 声纹管理业务逻辑
|-- realtime_transcriber.py    # 实时转写引擎（录音 + 转写 + 识别）
|-- speaker_recognizer.py      # 说话人识别（声纹特征提取与比对）
|-- whisper_client.py          # faster-whisper 语音转写封装
|-- llm_client.py              # 智谱 GLM API 调用封装
|-- database.py                # SQLite 数据库管理
|-- config_manager.py          # 配置管理（读写 config.json）
|-- ui_styles.py               # 深色主题 QSS 样式表
|-- requirements.txt           # Python 依赖清单
|-- config.json                # 配置文件（API Key、模型参数等）
|-- meetwise.spec              # PyInstaller 打包配置
|-- README.md                  # 项目说明文档
|-- voiceprints/               # 声纹特征数据存储目录
|-- recordings/                # 会议录音文件存储目录
```

---

## UI 设计

采用深色主题，以深蓝、黑、紫为主色调，简洁专业，适合答辩演示：

| 区域 | 位置 | 功能 |
| --- | --- | --- |
| 会议列表 | 左侧面板 | 历史会议列表，按时间排序，点击查看/右键删除 |
| 录音控制区 | 中间顶部 | 开始/暂停/停止按钮 + 录音时长显示 |
| 转写气泡区 | 中间主体 | 实时转写结果，气泡滚动显示，自动滚到底部，点击可跳转语音 |
| 摘要卡片 | 右侧上方 | 关键点/待办/结论 分区展示 |
| AI 对话区 | 右侧下方 | 历史对话 + 输入框 + 发送按钮 |

配色方案：
- 主背景：#0a0e1a（深黑蓝）
- 面板背景：#111827（暗灰蓝）
- 卡片背景：#1a1f36（深蓝灰）
- 主强调色：#7c3aed（紫色）
- 次强调色：#6366f1（靛蓝）
- 高亮色：#8b5cf6（亮紫）
- 主文字：#e2e8f0（浅灰白）
- 次要文字：#94a3b8（灰蓝）
- 气泡（自己）：#1e1b4b（深紫蓝）
- 气泡（他人）：#172554（深蓝）

---

## 常见问题

### Q1: 启动后提示"模型加载中"，很久没有响应？
首次运行会自动下载 faster-whisper 和 pyannote 模型，需要联网。base 模型约 140MB，pyannote/embedding 约 100MB。下载完成后会缓存到本地，后续启动不再需要下载。

### Q2: 说话人识别不准确？
- 检查声纹注册时的录音质量（建议安静环境、正常语速朗读 15 秒以上）
- 适当降低 config.json 中的 speaker_threshold（如 0.6）可提高召回率
- 增加注册时长可提升识别准确率

### Q3: 转写延迟较大？
- 可将 whisper_model_size 改为 tiny（牺牲一定准确率）
- 如有 NVIDIA GPU，安装 CUDA 版 PyTorch 可大幅加速
- 增大 transcribe_interval 可减少转写频率，降低 CPU 负载

### Q4: 打包后 exe 运行报错？
- 确保打包时 config.json 和 voiceprints/ 目录与 exe 在同一目录
- 检查 meetwise.spec 中的 hidden imports 是否完整
- 建议在打包环境中使用虚拟环境，避免打包多余依赖

### Q5: 如何切换 Whisper 模型？
修改 config.json 中的 whisper_model_size，可选值：tiny、base、small、medium、large-v3。切换后首次运行会自动下载对应模型。

### Q6: 点击气泡没有声音？
- 检查 recordings/ 目录下是否有对应会议的 .wav 录音文件
- 确认系统音频输出设备正常
- 录音文件在会议正常停止后才会保存完整

### Q7: PyCharm 中表格显示异常？
- 确保 PyCharm 启用了 GFM 支持：Settings - Languages & Frameworks - Markdown - 勾选 "GitHub Flavored Markdown"
- 本项目所有表格均使用标准 GFM 格式

---

## 许可证

本项目仅供学习和答辩演示使用。

---

## 致谢

- faster-whisper（https://github.com/SYSTRAN/faster-whisper）- 高性能语音转写
- pyannote.audio（https://github.com/pyannote/pyannote-audio）- 说话人识别
- 智谱 AI（https://open.bigmodel.cn/）- 大语言模型 API
- PySide6（https://doc.qt.io/qtforpython/）- Qt for Python GUI 框架
