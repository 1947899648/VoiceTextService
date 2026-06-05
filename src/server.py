import os
import subprocess
import tempfile
import time
from contextlib import asynccontextmanager

import soundfile as sf
sf.SoundFileRuntimeError = RuntimeError

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import wenet


MODEL_NAME = os.getenv("WENET_MODEL", "paraformer")

model = None

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_ffmpeg():
    local = os.path.join(_PROJECT_ROOT, "ffmpeg", "bin", "ffmpeg.exe")
    if os.path.exists(local):
        return local
    return "ffmpeg"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    print(f"[INIT] Loading model: {MODEL_NAME} ...")
    start = time.time()
    model = wenet.load_model(MODEL_NAME)
    elapsed = time.time() - start
    print(f"[INIT] Model loaded in {elapsed:.1f}s, ready for requests")
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
    return {"status": "ok"}


@app.post("/asr")
async def asr(audio: UploadFile = File(...)):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    suffix = os.path.splitext(audio.filename)[1] or ".wav"
    data = await audio.read()

    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    fd_src, src_path = tempfile.mkstemp(suffix=suffix)
    fd_wav, wav_path = tempfile.mkstemp(suffix=".wav")
    try:
        with open(fd_src, "wb") as f:
            f.write(data)
        os.close(fd_wav)

        subprocess.run([
            _find_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
            "-i", src_path,
            "-acodec", "pcm_s16le",
            "-ac", "1",
            "-ar", "16000",
            wav_path
        ], capture_output=True, check=True)

        info = sf.info(wav_path)
        audio_duration = round(info.duration, 2)

        start = time.time()
        result = model.transcribe(wav_path)
        elapsed = time.time() - start

        return {
            "text": result.text,
            "duration": audio_duration,
            "inference_time": round(elapsed, 2),
        }
    finally:
        os.unlink(src_path)
        os.unlink(wav_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
