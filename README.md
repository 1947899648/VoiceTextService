# VoiceTextService

Minimal offline ASR (speech-to-text) microservice. Accepts audio files via HTTP, returns transcribed text.  
轻量级离线语音转文本微服务。通过 HTTP 接收音频文件，返回识别文本。

Powered by [WeNet](https://github.com/wenet-e2e/wenet) + Paraformer model.  
基于 WeNet 框架 + Paraformer 模型。

---

## Architecture / 架构

```
Client  --POST /asr-->  FastAPI :8000  --wenet-->  paraformer  -->  {"text": "..."}
            GET /health
            multipart/form-data
```

## Directory Structure / 目录结构

```
VoiceTextService/
├── src/
│   ├── server.py              # FastAPI application / 主服务（/health）
│   ├── asr.py                 # ASR routes / 语音识别路由（POST /asr）
│   └── tts.py                 # TTS routes / 语音合成路由（骨架）
├── tests/
│   ├── test_asr.py            # CLI test tool for ASR / 命令行测试工具
│   └── test_tts.py            # CLI test tool for TTS / 命令行测试工具
├── scripts/
│   ├── apply_patches.py       # Compatibility patcher / 兼容补丁（setup.bat 调用）
│   └── download_ffmpeg.ps1    # FFmpeg auto-downloader / FFmpeg 自动下载
├── ffmpeg/
│   └── bin/                   # FFmpeg shared binaries (Windows)
├── requirements.txt           # Pip dependencies / 依赖清单
├── .gitignore
├── setup.bat                  # One-click first-time setup / 首次部署（双击）
└── start.bat                  # Launch the server / 日常启动（双击）
```

Hidden at runtime / 运行时生成：
- `.venv/` — Python virtual environment / 虚拟环境（`setup.bat` 创建，git 忽略）
- `.setup_done` — Sentinel file / 哨兵文件（防止重复部署，git 忽略）
- `~/.wenet/paraformer/` — Cached model files (~900 MB) / 模型缓存

## Prerequisites / 前置条件

- **Windows** (tested on 10/11) / Windows 10/11 已测试
- **Python 3.10+** (in PATH) / Python 3.10+ 已加入 PATH
- **Git** (in PATH) / Git 已加入 PATH（`pip install git+...` 需要）
- **NVIDIA GPU** (optional) / GPU 可选（无 GPU 自动降级 CPU）

## Quick Start / 快速开始

### First-time Setup / 首次部署

```
双击 setup.bat
```

This will / 将依次完成：  
1. Create venv `.venv/` / 创建虚拟环境  
2. Install pip dependencies / 安装 pip 依赖  
3. Install WeNet from GitHub / 从 GitHub 安装 WeNet  
4. Apply 4 compatibility patches / 应用 4 个兼容补丁  
5. Download Paraformer model (~900 MB) / 下载模型

Re-running is safe — skips everything if already complete (0 network).  
重复运行安全 — 已部署则秒退，零网络流量。

### Launch / 启动

```
双击 start.bat
```

Starts on `http://0.0.0.0:8000`.  
服务监听 `http://0.0.0.0:8000`。

### Verify / 验证

```bash
python tests/test_asr.py sample.wav
```

Or open / 或打开 `http://localhost:8000/docs` (Swagger UI).

## API

### `GET /health`

| | |
|---|---|
| Description / 说明 | Server & module health check / 服务器与模块健康检查 |
| Response / 返回 | `{"status": "ok", "asr": true, "tts": false}` |

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

### Supported Audio Formats / 支持的音频格式

WAV, MP3, M4A (AAC), FLAC, OGG — any format decodable by FFmpeg.  
所有 FFmpeg 能解码的格式均支持。

## Configuration / 配置

| Variable / 变量 | Default / 默认值 | Description / 说明 |
|---|---|---|
| `WENET_MODEL` (env) | `paraformer` | Model to load. Alternatives: `whisper-large-v3`, `firered`, `wenetspeech` |

Set via environment / 通过环境变量设置：
```bat
set WENET_MODEL=whisper-large-v3
start.bat
```

## Performance / 性能

Tested on CPU (Intel, no GPU) / CPU 实测（无 GPU）：

| Audio / 音频 | Duration / 时长 | Inference / 推理 | Factor / 倍速 |
|---|---|---|---|
| 2s silence / 静音 | 2.0s | 0.13s | 15× |
| 9.3s speech / 语音 | 9.3s | 1.58s | 5.9× |

GPU mode (10–50× speedup) / GPU 模式（10–50 倍加速）：
```bash
pip uninstall torch torchaudio -y
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```
No code changes required. / 代码无需修改。

## Compatibility Patches / 兼容补丁

This project applies 4 patches to WeNet for Python 3.14 + PyTorch 2.12:  
本项目对 WeNet 打了 4 个补丁以兼容 Python 3.14 + PyTorch 2.12：

| # | Patch / 补丁 | File / 文件 | Reason / 原因 |
|---|---|---|---|
| 1 | Split broken imports | `conv2d.py` | PyTorch 2.12 removed `Union`/`_pair` from `torch.nn.modules.conv` |
| 2 | Audio loading → soundfile | `processor.py` `decode_wav` | `torchaudio.load` removed; `soundfile` reads WAV pre-decoded by FFmpeg |
| 3 | Resample → librosa | `processor.py` `resample` | `torchaudio.transforms.Resample` → `librosa.resample` |
| 4 | SoundFileRuntimeError | `soundfile` (monkey-patch) | `soundfile` 0.12+ removed class; `librosa` fallback broke |

All patches are idempotent — `scripts/apply_patches.py` detects existing patches and skips.  
所有补丁均可重复执行 — `apply_patches.py` 自动检测已补状态并跳过。

## Deploying to Another Machine / 部署到其他电脑

1. Copy entire project folder **except `.venv/`** / 拷贝整个项目文件夹，**不含 `.venv/`**
2. Run `setup.bat` / 双击 `setup.bat`
3. Run `start.bat` / 双击 `start.bat`

Note: `ffmpeg/bin/` must be included in the copy.  
注意：`ffmpeg/bin/` 目录必须随项目拷贝。

## Roadmap / 路线图

- [ ] GPU mode with CUDA PyTorch / CUDA GPU 加速（代码零改动）
- [ ] FunASR model comparison / FunASR 模型对比切换
- [ ] Streaming ASR (WebSocket) / 流式实时识别
- [ ] Docker container / Docker 容器化

## License / 许可证

Apache 2.0 (WeNet) + MIT (this service).
