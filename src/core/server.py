import os
import time
import warnings
from contextlib import asynccontextmanager

# CosyVoice uses LoRACompatibleLinear from diffusers which triggers a
# FutureWarning unconditionally — suppress it.
warnings.filterwarnings("ignore", message=".*LoRACompatibleLinear.*")
# PyTorch 2.12 deprecated torch.cuda.amp.autocast (CosyVoice still uses it)
warnings.filterwarnings("ignore", message=".*torch.cuda.amp.autocast.*")

import soundfile as sf
sf.SoundFileRuntimeError = RuntimeError

import torch as _torch
_vtstorch_orig_load = _torch.load
_torch.load = lambda *a, **kw: _vtstorch_orig_load(
    *a, **({**kw, 'weights_only': False} if 'weights_only' not in kw else {}))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import wenet

ASR_MODEL_NAME = os.getenv("WENET_MODEL", "paraformer")
TTS_MODEL_DIR = os.getenv("COSYVOICE_MODEL_DIR", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "pretrained_models", "CosyVoice-300M-SFT",
))


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[INIT] Loading ASR model: {ASR_MODEL_NAME} ...")
    start = time.time()
    app.state.asr_model = wenet.load_model(ASR_MODEL_NAME)
    elapsed = time.time() - start
    print(f"[INIT] ASR model loaded in {elapsed:.1f}s")

    print(f"[INIT] Loading TTS model from: {TTS_MODEL_DIR} ...")
    start = time.time()
    try:
        from cosyvoice.cli.cosyvoice import CosyVoice
        app.state.tts_model = CosyVoice(
            TTS_MODEL_DIR, load_jit=False, load_trt=False, fp16=False)
        elapsed = time.time() - start
        print(f"[INIT] TTS model loaded in {elapsed:.1f}s")
    except Exception as e:
        print(f"[INIT] TTS model failed to load: {e}")
        app.state.tts_model = None

    print("[INIT] Ready for requests")
    yield
    print("[SHUTDOWN] Server stopped")


app = FastAPI(title="VoiceTextService", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "asr": getattr(app.state, "asr_model", None) is not None,
        "tts": getattr(app.state, "tts_model", None) is not None,
    }


from asr import router as asr_router
app.include_router(asr_router)

from tts import router as tts_router
app.include_router(tts_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
