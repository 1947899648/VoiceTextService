from fastapi import APIRouter

router = APIRouter(prefix="/tts")


@router.post("")
async def tts():
    return {"message": "TTS not implemented yet"}
