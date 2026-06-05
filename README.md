# VoiceTextService

Offline ASR + TTS microservice. Voice-to-text and text-to-voice via HTTP.  
离线语音转文字 + 文字转语音微服务。通过 HTTP 接口双向转换。

ASR powered by [WeNet](https://github.com/wenet-e2e/wenet) + Paraformer.  
TTS powered by [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) (Alibaba FunAudioLLM).  
ASR 基于 WeNet + Paraformer；TTS 基于阿里达摩院 CosyVoice。

---

## Architecture / 架构

```
                     ┌──────────────────────────┐
  audio/wav ──POST /asr──→  FastAPI :8000       │
                     │     │  ┌─ wenet/paraformer
                     │     │  └─ cosyvoice
  text   ──POST /tts──→     │                    │
  audio/wav ←───────────────┘                    │
                     └──────────────────────────┘
         GET /health  →  {"asr": true, "tts": true}
```

## Directory Structure / 目录结构

```
VoiceTextService/
├── install/
│   ├── setup_win.bat            # Windows setup entry / Windows 安装入口
│   ├── setup_linux.sh           # Linux setup entry / Linux 安装入口
│   └── scripts/
│       ├── setup.py             # Cross-platform setup orchestrator / 跨平台安装调度器
│       ├── apply_patches.py     # Compatibility patcher / 兼容补丁
│       ├── install_cosyvoice.py # CosyVoice installer / CosyVoice 安装脚本
│       └── download_ffmpeg.ps1  # FFmpeg auto-downloader (Win) / FFmpeg 自动下载
├── run/
│   ├── start_win.bat            # Windows launch / Windows 启动
│   └── start_linux.sh           # Linux launch / Linux 启动
├── src/
│   └── core/
│       ├── server.py            # FastAPI application / 主服务
│       ├── asr.py               # ASR routes / 语音识别路由
│       └── tts.py               # TTS routes / 语音合成路由
├── tests/
│   ├── test_asr.py              # CLI test tool for ASR / 命令行测试工具
│   └── test_tts.py              # CLI test tool for TTS / 命令行测试工具
├── ffmpeg/
│   └── bin/                     # FFmpeg shared binaries (Windows)
├── requirements.txt             # Pip dependencies / 依赖清单
├── .gitignore
└── README.md
```

Hidden at runtime / 运行时生成：
- `.venv/` — Python virtual environment / 虚拟环境（`setup` 创建，git 忽略）
- `.setup_done` — Sentinel file / 哨兵文件（防止重复部署，git 忽略）
- `pretrained_models/` — Model cache / 模型缓存（git 忽略）
  - `pretrained_models/paraformer/` — Paraformer model (~900 MB) / ASR 模型
  - `pretrained_models/CosyVoice-300M-SFT/` — CosyVoice model (~1.6 GB) / TTS 模型

## Prerequisites / 前置条件

- **Windows 10/11** or **Linux** / Windows 10/11 或 Linux
- **Python 3.10+** (in PATH) / Python 3.10+ 已加入 PATH
- **Git** (in PATH) / Git 已加入 PATH
- Linux only / 仅 Linux: **FFmpeg** (`sudo apt install ffmpeg`) recommended for broad audio format support
- **NVIDIA GPU** (optional) / GPU 可选（无 GPU 自动降级 CPU）

## Quick Start / 快速开始

### First-time Setup / 首次部署

**Windows:**
```
双击 install\setup_win.bat
```

**Linux:**
```bash
chmod +x install/setup_linux.sh
./install/setup_linux.sh
```

This will / 将依次完成：  
1. Create venv `.venv/` / 创建虚拟环境  
2. Install pip dependencies / 安装 pip 依赖  
3. Install WeNet (ASR) from GitHub / 从 GitHub 安装 WeNet  
4. Install CosyVoice (TTS) to site-packages / 安装 CosyVoice 到 site-packages  
5. Apply compatibility patches / 应用兼容补丁  
6. Download Paraformer model (~900 MB) / 下载 ASR 模型  
7. Download CosyVoice-300M-SFT model (~1.6 GB) / 下载 TTS 模型  
8. Download/verify FFmpeg / 下载/验证 FFmpeg

Re-running is safe — skips everything if already complete (0 network).  
重复运行安全 — 已部署则秒退，零网络流量。

### Launch / 启动

**Windows:**
```
双击 run\start_win.bat
```

**Linux:**
```bash
chmod +x run/start_linux.sh
./run/start_linux.sh
```

Starts on `http://0.0.0.0:8000`.  
服务监听 `http://0.0.0.0:8000`。

### Verify / 验证

```bash
# Activate venv first / 先激活虚拟环境
# Windows: .venv\Scripts\activate
# Linux:   source .venv/bin/activate

# ASR test
python tests/test_asr.py sample.wav

# TTS test — list voices
python tests/test_tts.py --voices

# TTS test — synthesize
python tests/test_tts.py "你好世界" --spk "中文女" --out output.wav
```

Or open / 或打开 `http://localhost:8000/docs` (Swagger UI).

## API

### `GET /health`

| | |
|---|---|
| Description / 说明 | Server & module health check / 服务器与模块健康检查 |
| Response / 返回 | `{"status": "ok", "asr": true, "tts": true}` |

### `POST /asr`

| | |
|---|---|
| Description / 说明 | Transcribe an audio file / 语音转文本 |
| Body | `multipart/form-data` |
| Field / 字段 | `audio` — audio file / 音频文件 |

**Response / 返回：**

```json
{
  "text": "你好我是王胖子",
  "duration": 9.3,
  "inference_time": 1.58
}
```

| Field / 字段 | Type / 类型 | Description / 说明 |
|---|---|---|
| `text` | string | Recognized text / 识别文本 |
| `duration` | float | Audio duration in seconds / 音频时长（秒） |
| `inference_time` | float | Inference time in seconds / 推理耗时（秒） |

### `GET /tts/voices`

| | |
|---|---|
| Description / 说明 | List available speaker voices / 列出可用音色 |
| Response / 返回 | `{"voices": ["中文女", "中文男", ...]}` |

### `POST /tts`

| | |
|---|---|
| Description / 说明 | Synthesize speech from text / 文本转语音 |
| Body | `application/json` |
| Field / 字段 | `text` (string, required) — text to speak / 要合成的文本 |
| | `spk_id` (string, optional, default `"中文女"`) — speaker voice / 音色 ID |

**Response / 返回：**

- Content-Type: `audio/wav` (16kHz mono PCM)
- Headers:
  - `X-Duration` — audio duration in seconds / 音频时长
  - `X-Inference-Time` — inference time in seconds / 推理耗时
  - `X-Spk-Id` — speaker used / 使用的音色

### Supported Audio Formats / 支持的音频格式 (ASR)

WAV, MP3, M4A (AAC), FLAC, OGG — any format decodable by FFmpeg.  
所有 FFmpeg 能解码的格式均支持。

## Configuration / 配置

| Variable / 变量 | Default / 默认值 | Description / 说明 |
|---|---|---|
| `WENET_MODEL` (env) | `paraformer` | ASR model. Alternatives: `whisper-large-v3`, `firered`, `wenetspeech` |
| `COSYVOICE_MODEL_DIR` (env) | `pretrained_models/CosyVoice-300M-SFT` | Path to TTS model directory / TTS 模型目录 |

Set via environment / 通过环境变量设置：

**Windows:**
```bat
set WENET_MODEL=whisper-large-v3
run\start_win.bat
```

**Linux:**
```bash
WENET_MODEL=whisper-large-v3 ./run/start_linux.sh
```

## Performance / 性能

Tested on CPU (Intel, no GPU) / CPU 实测（无 GPU）：

### ASR

| Audio / 音频 | Duration / 时长 | Inference / 推理 | Factor / 倍速 |
|---|---|---|---|
| 2s silence / 静音 | 2.0s | 0.13s | 15× |
| 9.3s speech / 语音 | 9.3s | 1.58s | 5.9× |

### TTS

CosyVoice-300M-SFT on CPU generates ~3-5 seconds of speech per second of inference time.  
CosyVoice-300M-SFT 在 CPU 上约每秒推理生成 3-5 秒语音。

GPU mode (10–50× speedup) / GPU 模式（10–50 倍加速）：
```bash
# Run inside venv / 在虚拟环境内执行
pip uninstall torch torchaudio -y
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```
No code changes required. / 代码无需修改。

## Compatibility Patches / 兼容补丁

This project applies patches for Python 3.14 + PyTorch 2.12:  
本项目打了补丁以兼容 Python 3.14 + PyTorch 2.12：

| # | Patch / 补丁 | Target / 目标 | Reason / 原因 |
|---|---|---|---|
| 1 | Split broken imports | WeNet `conv2d.py` | PyTorch 2.12 removed `Union`/`_pair` from `torch.nn.modules.conv` |
| 2 | Audio loading → soundfile | WeNet `processor.py` `decode_wav` | `torchaudio.load` removed |
| 3 | Resample → librosa | WeNet `processor.py` `resample` | `torchaudio.transforms.Resample` removed |
| 4 | SoundFileRuntimeError | `soundfile` (monkey-patch) | `soundfile` 0.12+ removed class |
| 5 | torch.load weights_only | CosyVoice + Matcha | PyTorch 2.6+ defaults `weights_only=True`, breaks model checkpoints |
| 6 | pyworld graceful fallback | CosyVoice `processor.py` | pyworld has no cp314 wheel on Windows |

All patches are idempotent — `apply_patches.py` detects existing patches and skips.  
所有补丁均可重复执行 — `apply_patches.py` 自动检测已补状态并跳过。

## Deploying to Another Machine / 部署到其他电脑

1. Copy entire project folder **except `.venv/`** / 拷贝整个项目文件夹，**不含 `.venv/`**  
   Include `pretrained_models/` and `ffmpeg/bin/` (Windows) to skip model downloads.  
   建议带上 `pretrained_models/` 和 `ffmpeg/bin/`（Windows），避免重新下载模型。
2. **Windows:** 双击 `install\setup_win.bat`  
   **Linux:** `./install/setup_linux.sh`  
   (Setup detects existing models in `pretrained_models/` and skips download.)  
   （setup 自动检测 `pretrained_models/` 中已有模型并跳过下载。）
3. **Windows:** 双击 `run\start_win.bat`  
   **Linux:** `./run/start_linux.sh`

Note: On Windows, `ffmpeg/bin/` must be included in the copy. On Linux, install via `apt install ffmpeg`.  
注意：Windows 下 `ffmpeg/bin/` 必须随项目拷贝。Linux 下通过 `apt install ffmpeg` 安装。

## Roadmap / 路线图

- [x] Offline ASR (WeNet + Paraformer) / 离线语音识别
- [x] Offline TTS (CosyVoice SFT) / 离线语音合成
- [x] Cross-platform support (Windows + Linux) / 跨平台支持
- [ ] GPU mode with CUDA PyTorch / CUDA GPU 加速（代码零改动）
- [ ] Streaming ASR (WebSocket) / 流式实时识别
- [ ] Streaming TTS (WebSocket) / 流式实时合成
- [ ] FunASR model comparison / FunASR 模型对比切换
- [ ] Docker container / Docker 容器化

## License / 许可证

Apache 2.0 (WeNet + CosyVoice) + MIT (this service).
