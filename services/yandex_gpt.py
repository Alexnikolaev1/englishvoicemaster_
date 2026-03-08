"""YandexGPT integration for generating tutor responses."""
import aiohttp
import logging
import json
from pathlib import Path
from config import config

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent

def _load_prompt(tutor: str) -> str:
    path = BASE_DIR / "prompts" / f"{tutor}_system.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"You are {tutor.title()}, an English language tutor. Speak only in English."


SYSTEM_PROMPTS = {
    "john": _load_prompt("john"),
    "mary": _load_prompt("mary"),
}

FALLBACK_RESPONSES = {
    "john": [
        "That's a wonderful topic to discuss! Tell me more about it — I'd love to hear your thoughts in detail.",
        "Fascinating! Now, let me challenge you a bit. Can you expand on that idea using some new vocabulary?",
        "Brilliant! I noticed something interesting in what you said. Let's explore that further, shall we?",
    ],
    "mary": [
        "Oh wow, that is SO interesting! Tell me everything — I want all the details!",
        "No way! That is amazing! Okay, okay — now say it again but try to use a different word for that!",
        "I love that! You are doing SO well today, seriously! Now, what happened next?",
    ],
}

_fallback_index = {"john": 0, "mary": 0}


def _get_fallback(tutor: str) -> dict:
    idx = _fallback_index[tutor] % len(FALLBACK_RESPONSES[tutor])
    _fallback_index[tutor] += 1
    return {"text": FALLBACK_RESPONSES[tutor][idx], "hint": None, "error_types": []}


async def get_gpt_response(
    user_message: str,
    tutor: str,
    history: list,
    error_profile: list,
    message_count: int = 0,
    current_topic: str = None,
) -> dict:
    """Get response from YandexGPT."""
    if not config.YANDEX_API_KEY or not config.YANDEX_FOLDER_ID:
        logger.warning("YandexGPT not configured — using fallback response")
        return _get_fallback(tutor)

    # Build error context injection
    error_ctx = ""
    if error_profile:
        error_ctx = "\n\n[USER ERROR PROFILE — adapt your responses to reinforce correct usage]\n"
        for err in error_profile[:3]:
            error_ctx += f"- Frequent mistake: {err.error_detail} ({err.count} times)\n"

    # Rephrasing challenge trigger
    rephrase_ctx = ""
    if message_count > 0 and message_count % 5 == 0:
        rephrase_ctx = "\n\n[SYSTEM NOTE: This is message #" + str(message_count) + " — trigger the rephrasing challenge now.]"

    topic_ctx = f"\n\n[Current conversation topic: {current_topic}]" if current_topic else ""

    system_text = SYSTEM_PROMPTS.get(tutor, SYSTEM_PROMPTS["john"]) + error_ctx + rephrase_ctx + topic_ctx

    # Build message history
    messages = [{"role": "system", "text": system_text}]
    for msg in history[-8:]:
        role = "user" if msg.role == "user" else "assistant"
        messages.append({"role": role, "text": msg.text_content or ""})
    messages.append({"role": "user", "text": user_message})

    payload = {
        "modelUri": f"gpt://{config.YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.75,
            "maxTokens": "600",
        },
        "messages": messages,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers={
                    "Authorization": f"Api-Key {config.YANDEX_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    text = data["result"]["alternatives"][0]["message"]["text"]
                    hint = _extract_hint(text)
                    return {"text": text, "hint": hint, "error_types": []}
                else:
                    err_text = await resp.text()
                    logger.error(f"YandexGPT error {resp.status}: {err_text}")
                    return _get_fallback(tutor)
    except Exception as e:
        logger.error(f"YandexGPT exception: {e}")
        return _get_fallback(tutor)


def _extract_hint(text: str) -> str | None:
    """Extract any correction hint from GPT response."""
    hint_markers = ["💡", "Note:", "Tip:", "Correction:", "Actually,"]
    lines = text.split("\n")
    for line in lines:
        for marker in hint_markers:
            if marker in line:
                return line.strip()
    return None
