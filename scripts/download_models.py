import os
# 强制启用国内镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 下载Whisper base
from faster_whisper import download_model
download_model("base")

# 下载声纹embedding（从环境变量或配置文件读取 token）
from huggingface_hub import snapshot_download
import json

hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    try:
        with open("resources/config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            hf_token = config.get("hf_token")
    except:
        pass

snapshot_download(
    repo_id="pyannote/embedding",
    token=hf_token,
    local_dir_use_symlinks=False
)