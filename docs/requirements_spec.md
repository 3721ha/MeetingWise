# 需求规格说明书

> 智会 MeetWise — 功能需求详细规格与数据库设计

---

## 1. 需求规格总览

| 编号 | 功能名称 | 触发方式 | 核心技术 |
| --- | --- | --- | --- |
| REQ-001 | 声纹注册 | 用户点击"声纹管理"按钮 | pyannote.audio 声纹特征提取 |
| REQ-002 | 实时录音转写 | 用户点击"开始会议" | sounddevice + faster-whisper |
| REQ-003 | 说话人识别 | 每次转写前自动触发 | pyannote.audio + 余弦相似度 |
| REQ-004 | 陌生人重命名 | 右键点击气泡选择"重命名" | 数据库批量更新 |
| REQ-005 | AI 摘要生成 | 用户点击"生成摘要"按钮 | 智谱 GLM-4.5-Air API |
| REQ-006 | AI 对话 | 用户输入问题并发送 | 智谱 GLM-4.5-Air API |
| REQ-007 | 会议列表管理 | 左侧面板自动加载 | SQLite 查询与级联删除 |
| REQ-008 | 语音回放定位 | 左键点击转写气泡 | 录音文件 + 时间戳定位 |

---

## 2. 详细需求规格

### REQ-001 声纹注册

| 项目 | 描述 |
| --- | --- |
| 功能名称 | 声纹注册（会前准备） |
| 触发方式 | 用户点击"声纹管理"按钮，弹出注册对话框 |
| 输入 | 用户姓名（文本）+ 10-30 秒语音录音（16kHz 单声道） |
| 输出 | 512 维声纹特征向量（.npy 文件），注册成功提示 |
| 处理流程 | 开始录音 → sounddevice 流式采集 → 停止录音 → pyannote.audio 提取 embedding → 保存为 data/voiceprints/{name}.npy → 数据库记录路径 |
| 数据库存储 | voiceprints 表：id（自增主键）、name（姓名，唯一）、embedding_path（.npy 文件路径）、created_at（注册时间） |
| 文件存储 | data/voiceprints/{name}.npy（numpy 数组，512 维 float32 向量） |
| 关键约束 | 录音时长至少 3 秒，低于 3 秒提示"录音时间太短"；同名已存在时提示"该姓名已注册" |
| 线程要求 | 录音在子线程，embedding 提取在子线程，UI 不阻塞 |

### REQ-002 实时录音转写

| 项目 | 描述 |
| --- | --- |
| 功能名称 | 实时会议录音与转写 |
| 触发方式 | 用户点击"开始会议"按钮 |
| 输入 | 麦克风实时音频流（16kHz、单声道、float32） |
| 输出 | 实时气泡消息"发言人：对话内容"，自动滚动显示 |
| 处理流程 | sounddevice 回调采集音频 → queue.put → 每 3 秒取出累积音频 → faster-whisper 转写 → Signal 发送到 UI → 保存到数据库 → 同步保存完整音频到 data/recordings/ |
| 数据库存储 | meetings 表：id、title、start_time、end_time、status（recording/ended）、recording_path |
| 数据库存储 | utterances 表：id、meeting_id、speaker、speaker_id、text、timestamp、audio_start、audio_end |
| 关键约束 | sounddevice 回调只做 queue.put，严禁耗时操作；转写间隔可配置（默认 3 秒）；自动滚动到底部；完整录音保存为 WAV |
| 线程要求 | 录音回调在 PortAudio C 线程；转写在 QThread 子线程；UI 更新通过 Signal/Slot |

### REQ-003 说话人识别

| 项目 | 描述 |
| --- | --- |
| 功能名称 | 实时说话人识别 |
| 触发方式 | 每次转写前自动触发 |
| 输入 | 音频片段（numpy 数组）+ 已注册声纹库（dict） |
| 输出 | 发言人名称（已注册姓名 或 "陌生人A/B/C..."） |
| 处理流程 | pyannote.audio 提取当前片段 embedding → 遍历声纹库计算余弦相似度 → 最高相似度 >= 0.7 返回对应姓名；否则分配陌生人编号 |
| 数据来源 | 读取 voiceprints 表获取已注册声纹；读取 data/voiceprints/{name}.npy 加载声纹向量 |
| 关键约束 | 余弦相似度阈值 0.7（可在 config.json 调整）；陌生人编号按字母序递增（A-Z），超过 26 个后转为数字编号；声纹提取失败时返回"未知说话人" |
| 相似度公式 | cosine_similarity = dot(a, b) / (norm(a) * norm(b)) |

### REQ-004 陌生人重命名

| 项目 | 描述 |
| --- | --- |
| 功能名称 | 陌生人重命名 |
| 触发方式 | 用户右键点击陌生人气泡 → 选择"重命名" → 弹出输入框 |
| 输入 | 旧名称（如"陌生人A"）+ 新名称（用户输入） |
| 输出 | 更新后的气泡显示 + 数据库同步更新 |
| 处理流程 | 弹出 QInputDialog → 用户输入新名字 → 更新当前气泡 UI → UPDATE utterances SET speaker 同步所有会议 |
| 数据库更新 | `UPDATE utterances SET speaker = '新名字' WHERE speaker = '陌生人A'`（所有会议同步） |
| 关键约束 | 重命名后所有历史会议中该陌生人都显示新名字；与已注册声纹重名时提示冲突 |
| UI 交互 | 右键菜单仅在陌生人/未注册发言人气泡上显示"重命名"选项 |

### REQ-005 AI 摘要生成

| 项目 | 描述 |
| --- | --- |
| 功能名称 | AI 智能摘要生成 |
| 触发方式 | 用户点击右侧"生成摘要"按钮 |
| 输入 | 本次会议全部转写文本（格式："发言人1：内容\n发言人2：内容..."） |
| 输出 | 结构化 Markdown 摘要（关键点 / 待办事项 / 结论） |
| 处理流程 | 拼接全文 → 构造 Prompt → 调用智谱 GLM-4.5-Air API → 解析返回文本 → 右侧卡片分区显示 → 保存到数据库 |
| 数据库存储 | summaries 表：id、meeting_id（UNIQUE）、content、created_at |
| API 参数 | model: glm-4.5-air, temperature: 0.3, max_tokens: 2000 |
| Prompt 模板 | "你是一位专业的会议纪要助手。请根据以下会议转写内容，生成结构化摘要，包含：1. 关键点（3-5 个核心讨论要点）2. 待办事项（标注负责人）3. 结论（共识和决定）\n\n会议内容：\n{transcript}" |
| 线程要求 | API 调用在 QThread 子线程，UI 显示"生成中..."加载状态 |
| 关键约束 | 支持会议进行中或结束后生成；已生成过可重新生成（覆盖）；网络错误时显示友好提示 |

### REQ-006 AI 对话

| 项目 | 描述 |
| --- | --- |
| 功能名称 | 会议内 AI 对话（追问） |
| 触发方式 | 用户输入问题，点击"发送"或按 Enter |
| 输入 | 用户问题 + 会议全文（上下文）+ 历史对话记录 |
| 输出 | AI 回答文本，显示在对话区 |
| 处理流程 | 拼接全文 + 历史问答 + 用户问题 → 构造 messages 数组 → 调用智谱 GLM API → 显示回答 → 保存到数据库 |
| 数据库存储 | chat_history 表：id、meeting_id、question、answer、created_at |
| API 参数 | model: glm-4.5-air, temperature: 0.5, max_tokens: 1500 |
| Prompt 结构 | system: "你是会议纪要助手，请基于以下会议内容回答用户问题。" + 会议全文 + 历史对话（最近 5 轮）+ 当前问题 |
| 关键约束 | 对话历史自动保存；支持 Enter 快捷发送；空内容不可发送 |

### REQ-007 会议列表管理

| 项目 | 描述 |
| --- | --- |
| 功能名称 | 历史会议列表管理 |
| 触发方式 | 左侧面板自动加载，用户点击/右键操作 |
| 输入 | 用户在会议列表中的操作（点击查看详情 / 右键删除） |
| 输出 | 会议详情（转写内容 + 摘要 + 对话记录）或确认删除 |
| 处理流程 | 启动时查询所有会议 → 按时间倒序显示 → 点击加载详情（转写气泡 + 摘要 + 对话）→ 右键弹出确认对话框 → 确认后级联删除 |
| 数据库查询 | `SELECT * FROM meetings ORDER BY start_time DESC` |
| 级联删除顺序 | chat_history → summaries → utterances → meetings |
| 关键约束 | 删除前弹出二次确认；删除后刷新列表；当前查看的会议被删除时清空右侧面板 |
| UI 交互 | 列表项显示会议标题 + 时间；选中项高亮；右键菜单："查看详情"/"删除" |

### REQ-008 语音回放定位

| 项目 | 描述 |
| --- | --- |
| 功能名称 | 点击气泡跳转语音回放 |
| 触发方式 | 用户左键点击任意转写气泡 |
| 输入 | 点击的 utterance 记录（包含 audio_start 和 audio_end 时间戳） |
| 输出 | 从对应时间位置开始播放会议录音 |
| 处理流程 | 点击气泡 → 获取 audio_start → 加载会议录音文件（data/recordings/{meeting_id}.wav）→ 从 audio_start 位置播放 → 播放时高亮当前气泡 → 播放完毕取消高亮 |
| 数据来源 | meetings 表 recording_path 字段；utterances 表 audio_start/audio_end 字段 |
| 关键约束 | 录音文件在会议结束时保存为完整 WAV；支持播放中点击其他气泡跳转；播放时气泡边框紫色高亮 |
| UI 交互 | 悬停气泡显示手型光标；点击后边框紫色高亮 |

---
