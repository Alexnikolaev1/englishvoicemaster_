"""
Yandex SpeechKit — ASR (speech-to-text) and TTS (text-to-speech).

Vercel note: we pass raw OGG bytes directly without ffmpeg conversion.
Yandex SpeechKit accepts Telegram's oggopus format natively.
"""
import aiohttp
import asyncio
import logging
from config import config

logger = logging.getLogger(__name__)

# Voice settings per tutor
TUTOR_VOICES = {
    "john":   {"voice": "john",   "speed": "0.9", "emotion": "neutral"},
    "mary":   {"voice": "alyss",  "speed": "1.1", "emotion": "good"},
    "system": {"voice": "john",   "speed": "1.0", "emotion": "neutral"},
}


async def recognize_audio(audio_bytes: bytes, format: str = "oggopus") -> str | None:
    """
    Convert audio bytes to text using Yandex SpeechKit STT v1.

    Args:
        audio_bytes: Raw audio data (OGG/OPUS from Telegram, or WAV)
        format: 'oggopus' (Telegram default) or 'lpcm' (WAV)
    """
    if not config.SPEECHKIT_API_KEY:
        logger.warning("SpeechKit API key not configured — STT skipped")
        return "[SpeechKit not configured. Set SPEECHKIT_API_KEY to enable voice recognition.]"

    if not audio_bytes or len(audio_bytes) < 100:
        logger.warning(f"Audio too short: {len(audio_bytes)} bytes")
        return None

    params: dict = {
        "lang": "en-US",
        "folderId": config.YANDEX_FOLDER_ID,
        "format": format,
    }
    if format == "lpcm":
        params["sampleRateHertz"] = "16000"
    elif format == "oggopus":
        params["sampleRateHertz"] = "48000"

    headers = {"Authorization": f"Api-Key {config.SPEECHKIT_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize",
                params=params,
                headers=headers,
                data=audio_bytes,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data.get("result", "").strip()
                    logger.info(f"STT result ({len(result)} chars): {result[:80]}...")
                    return result or None
                else:
                    err = await resp.text()
                    logger.error(f"SpeechKit STT error {resp.status}: {err[:200]}")
                    return None
    except asyncio.TimeoutError:
        logger.error("SpeechKit STT: request timed out")
        return None
    except Exception as e:
        logger.error(f"SpeechKit STT exception: {e}")
        return None


async def synthesize_speech(text: str, tutor: str = "john") -> bytes | None:
    """
    Convert text to speech using Yandex SpeechKit TTS v1.
    Returns raw OGG bytes ready to send as Telegram voice message.
    """
    if not config.SPEECHKIT_API_KEY:
        logger.warning("SpeechKit API key not configured — TTS skipped")
        return None

    if not text or not text.strip():
        return None

    voice_params = TUTOR_VOICES.get(tutor, TUTOR_VOICES["system"])

    # Truncate to SpeechKit limit and clean text
    clean_text = text[:5000].replace("<", "").replace(">", "")

    form_data = {
        "text": clean_text,
        "lang": "en-US",
        "voice": voice_params["voice"],
        "emotion": voice_params["emotion"],
        "speed": voice_params["speed"],
        "folderId": config.YANDEX_FOLDER_ID,
        "format": "oggopus",
        "sampleRateHertz": "48000",
    }
    headers = {"Authorization": f"Api-Key {config.SPEECHKIT_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
                headers=headers,
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=25),
            ) as resp:
                if resp.status == 200:
                    audio = await resp.read()
                    logger.info(f"TTS: generated {len(audio)} bytes for tutor '{tutor}'")
                    return audio
                else:
                    err = await resp.text()
                    logger.error(f"SpeechKit TTS error {resp.status}: {err[:200]}")
                    return None
    except asyncio.TimeoutError:
        logger.error("SpeechKit TTS: request timed out")
        return None
    except Exception as e:
        logger.error(f"SpeechKit TTS exception: {e}")
        return None
