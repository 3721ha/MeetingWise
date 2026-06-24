# 开发与部署运维手册

> 智会 MeetWise — 环境配置、安装部署、使用指南、常见问题

---

## 1. 环境要求

| 项目 | 最低要求 | 推荐配置 |
| --- | --- | --- |
| 操作系统 | Windows 10 / macOS 12 / Ubuntu 20.04 | Windows 10/11 |
| Python | 3.10 | 3.11+ |
| 内存 | 8 GB | 16 GB+ |
| 硬盘空间 | 5 GB（含模型文件） | 10 GB+ |
| 麦克风 | 必备 | 指向性麦克风效果更佳 |
| 网络 | 首次运行需联网下载模型和调用 API | 稳定网络连接 |

性能参考：
- faster-whisper base 模型约 140MB，CPU 下转写延迟约 2-3 秒/片段
- pyannote.audio 依赖 PyTorch，模型约 100MB，首次加载需 10-20 秒
- 所有耗时操作在子线程执行，不会导致界面卡顿
- 有 NVIDIA GPU 时自动加速推理（需安装 CUDA 版 PyTorch）

---

## 2. 安装步骤

### 2.1 获取项目

```bash
git clone <your-repo-url>
cd MeetWise
```

### 2.2 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2.3 安装依赖

```bash
pip install -r requirements.txt
```

### 2.4 配置 HuggingFace Token

pyannote.audio 的模型托管在 HuggingFace 上，需要：

1. 注册 HuggingFace 账号（https://huggingface.co/join）
2. 访问 pyannote/embedding 页面（https://huggingface.co/pyannote/embedding），同意用户协议
3. 在 Settings → Access Tokens 中创建 Token
4. 将 Token 填入 `resources/config.json` 的 `hf_token` 字段

**国内网络加速**：项目已配置 HuggingFace 国内镜像（`https://hf-mirror.com`），下载模型时会自动走镜像站。

### 2.5 配置智谱 API Key

1. 注册智谱 AI 开放平台（https://open.bigmodel.cn/）
2. 创建 API Key
3. 将 API Key 填入 `resources/config.json` 的 `glm_api_key` 字段

---

## 3. 配置说明

`resources/config.json` 各配置项：

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| glm_api_key | 智谱 GLM API 密钥 | 必填 |
| glm_base_url | GLM API 接口地址 | https://open.bigmodel.cn/api/paas/v4/ |
| glm_model | GLM 模型名 | glm-4.5-air |
| hf_token | HuggingFace 访问令牌 | 必填 |
| whisper_model_size | Whisper 模型大小 | base |
| pyannote_model | 声纹识别模型 | pyannote/embedding |
| speaker_threshold | 说话人识别相似度阈值（0-1） | 0.7 |
| audio_sample_rate | 录音采样率 (Hz) | 16000 |
| transcribe_interval | 转写间隔 (秒) | 3 |
| voiceprint_dir | 声纹数据存储目录 | data/voiceprints |
| recording_dir | 录音文件存储目录 | data/recordings |
| db_path | SQLite 数据库文件路径 | data/meetwise.db |

Whisper 模型选择：

| 模型 | 大小 | 适用场景 |
| --- | --- | --- |
| tiny | 约 75MB | 快速测试，准确率一般 |
| base | 约 140MB | CPU 用户推荐，速度与准确率平衡 |
| small | 约 460MB | 准确率较高，需要更多内存 |
| medium | 约 1.5GB | 高准确率，建议有 GPU 时使用 |

---

## 4. 运行方式

### 4.1 开发模式

```bash
python main.py
```

**预下载模型（推荐）**：首次启动会自动下载模型，国内网络可在启动前执行：

```bash
python scripts/download_models.py
```

该脚本会下载 faster-whisper base 模型和 pyannote/embedding 声纹模型，避免 GUI 主线程下载导致界面卡死。

### 4.2 打包为 exe（Windows）

```bash
pip install pyinstaller
pyinstaller meetwise.spec
# 产物在 dist/ 目录下
```

打包注意事项：
- resources/config.json 需与 exe 放在同一目录
- 检查 meetwise.spec 中的 hidden imports 是否完整
- 建议在虚拟环境中打包，避免打包多余依赖

---

## 5. 使用指南

### 5.1 声纹注册（会前准备）

1. 点击顶部菜单栏"声纹管理"按钮
2. 输入发言人姓名
3. 点击"开始录音"，朗读至少 3 秒内容（建议 10-30 秒，质量更佳）
4. 录音完成后点击"注册"

声纹注册只需做一次，后续会议自动识别已注册的发言人。

### 5.2 开始会议

1. 在主界面点击"开始会议"
2. 转写结果以气泡形式实时显示：已注册显示姓名，未注册显示"陌生人A/B/C"
3. 可通过暂停/继续按钮控制录音
4. 点击停止结束会议

### 5.3 语音回放定位

1. 左键点击任意气泡
2. 系统从该段语音对应的时间位置开始播放录音
3. 播放时当前气泡边框紫色高亮
4. 可点击其他气泡跳转

### 5.4 重命名陌生人

1. 右键点击陌生人气泡
2. 选择"重命名"，输入真实姓名
3. 系统自动更新当前会议和所有历史会议中的显示

### 5.5 生成 AI 摘要

1. 点击右侧"生成摘要"按钮
2. 生成结构化摘要：关键点、待办事项、结论

### 5.6 AI 对话

1. 在右侧输入框输入问题，按 Enter 发送
2. 系统以会议全文为上下文回答
3. 支持多轮对话，历史自动保存

### 5.7 管理历史会议

1. 左侧面板显示所有历史会议（按时间排序）
2. 点击查看详情（转写内容、摘要、对话记录）
3. 右键删除（级联删除所有关联数据）

---

## 6. 常见问题

**Q: 启动后长时间无响应？**
首次运行自动下载模型，需联网。base 模型约 140MB，pyannote/embedding 约 100MB，后续启动使用本地缓存。

**Q: 说话人识别不准确？**
- 检查声纹注册录音质量（安静环境、正常语速 15 秒以上）
- 适当降低 speaker_threshold（如 0.6）提高召回率
- 增加注册时长可提升准确率

**Q: 转写延迟较大？**
- 将 whisper_model_size 改为 tiny（牺牲准确率）
- 安装 CUDA 版 PyTorch 可大幅加速
- 增大 transcribe_interval 降低 CPU 负载

---

>
