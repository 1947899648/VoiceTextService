import os
import subprocess
import tempfile
import time

import soundfile as sf
from fastapi import APIRouter, Request, UploadFile, File, HTTPException

router = APIRouter(prefix="/asr")


def _find_ffmpeg():
    project_root = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))
    local = os.path.join(project_root, "ffmpeg", "bin", "ffmpeg.exe")
    if os.path.exists(local):
        return local
    return "ffmpeg"


@router.post("")
async def asr(request: Request, audio: UploadFile = File(...)):
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
        result = request.app.state.model.transcribe(wav_path)
        elapsed = time.time() - start

        return {
            "text": result.text,
            "duration": audio_duration,
            "inference_time": round(elapsed, 2),
        }
    finally:
        os.unlink(src_path)
        os.unlink(wav_path)
