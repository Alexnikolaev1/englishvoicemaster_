"""
Voice message handler — the core of EnglishVoiceMaster.

Vercel note: ffmpeg is NOT available in the serverless runtime.
We pass the raw OGG/OPUS bytes directly to Yandex SpeechKit,
which natively accepts Telegram's oggopus format.
"""
import logging
from datetime import datetime
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, BufferedInputFile
from aiogram.types.input_file import FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import (
    get_user, get_or_create_user, save_message, get_recent_messages,
    get_top_errors, update_user_activity, has_access,
    increment_violation, block_user, set_temporary_block, get_temporary_block,
)
from services.censor import check_content
from services.speechkit import recognize_audio, synthesize_speech
from services.yandex_gpt import get_gpt_response
from services.fluency import get_fluency_message, POINTS_PER_MESSAGE
from bot.keyboards.main_menu import subscribe_prompt_kb
from bot.domain.topics import TOPIC_LABEL_TO_STARTER
from bot.i18n import normalize_lang

logger = logging.getLogger(__name__)
router = Router()
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_tutor_image(tutor: str) -> Path | None:
    base = "John" if tutor == "john" else "Mary"
    candidates = (
        f"{base}.jpg",
        f"{base}.jpeg",
        f"{base}.png",
        "Jhon.jpg" if tutor == "john" else "",
        "Jhon.jpeg" if tutor == "john" else "",
        "Jhon.png" if tutor == "john" else "",
        f"{base.lower()}.jpg",
        f"{base.lower()}.jpeg",
        f"{base.lower()}.png",
        "jhon.jpg" if tutor == "john" else "",
        "jhon.jpeg" if tutor == "john" else "",
        "jhon.png" if tutor == "john" else "",
    )
    for filename in candidates:
        if not filename:
            continue
        path = PROJECT_ROOT / filename
        if path.exists():
            return path
    return None

VIOLATION_MESSAGES = {
    1: "Let's keep our conversation respectful and focused on learning English. How was your day? 😊",
    2: "I'm here to teach English, and that topic is outside my guidelines. Shall we discuss your hobbies instead? 🌟",
}

@router.message(F.voice)
async def handle_voice(message: Message, session: AsyncSession, bot: Bot):
    user_id = message.from_user.id

    # ── 1. Get or create user ─────────────────────────────────────────
    user = await get_user(session, user_id)
    if not user:
        user = await get_or_create_user(
            session, user_id,
            message.from_user.username,
            message.from_user.first_name,
        )

    # ── 2. Access check ───────────────────────────────────────────────
    if user.is_blocked:
        await message.answer("⛔ Your account has been suspended due to policy violations.")
        return

    temp_block = await get_temporary_block(session, user_id)
    if temp_block:
        hours_left = max(1, int((temp_block.blocked_until - datetime.utcnow()).total_seconds() // 3600))
        await message.answer(
            "⛔ This session is temporarily suspended due to policy violations.\n"
            f"Try again in about {hours_left} hour(s)."
        )
        return

    if not await has_access(session, user):
        lang = normalize_lang(user.language_code)
        await message.answer(
            "⏰ <b>Your free trial has ended!</b>\n\n"
            "Subscribe to continue practicing with John &amp; Mary and keep your progress!\n\n"
            f"📊 Your current score: <b>{user.fluency_score} pts</b>\n"
            "Don't lose it — subscribe now! 💎",
            reply_markup=subscribe_prompt_kb(lang),
        )
        return

    # Send tutor photo once at the very beginning of conversation.
    if user.total_messages == 0:
        tutor_key = user.selected_tutor or "john"
        image_path = _resolve_tutor_image(tutor_key)
        if image_path:
            await message.answer_photo(FSInputFile(str(image_path)))

    # ── 3. Typing indicator ───────────────────────────────────────────
    await bot.send_chat_action(message.chat.id, "record_voice")

    # ── 4. Download raw OGG bytes ─────────────────────────────────────
    # Vercel: no disk writes, keep everything in memory
    try:
        file = await bot.get_file(message.voice.file_id)
        downloaded = await bot.download_file(file.file_path)
        # downloaded is a BytesIO — read it fully into bytes
        audio_bytes = downloaded.read() if hasattr(downloaded, "read") else bytes(downloaded)
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        await message.answer("❌ Could not download your voice message. Please try again.")
        return

    # ── 5. ASR: raw OGG → text ────────────────────────────────────────
    # Yandex SpeechKit accepts oggopus natively — no conversion needed
    transcript = await recognize_audio(audio_bytes, format="oggopus")

    if not transcript or len(transcript.strip()) < 2:
        await message.answer(
            "🎙️ I couldn't catch that clearly. "
            "Please speak a bit louder and try again!"
        )
        return

    # ── 6. Content filter ─────────────────────────────────────────────
    censor = check_content(transcript)
    if censor.blocked:
        violation_count = await increment_violation(session, user_id)
        if violation_count >= 5:
            await block_user(session, user_id)
            await message.answer(
                "⛔ Your account has been permanently suspended due to repeated policy violations.\n"
                "Contact support to appeal."
            )
            return
        if violation_count >= 3:
            await set_temporary_block(session, user_id, hours=24)
            await message.answer(
                "⛔ This session has been suspended for 24 hours due to repeated policy violations.\n"
                "You can continue learning tomorrow."
            )
            return
        msg = VIOLATION_MESSAGES.get(violation_count, VIOLATION_MESSAGES[2])
        await message.answer(f"⚠️ {msg}")
        return
    if censor.soft_redirect:
        await message.answer(
            "Let's keep our conversation focused on English practice.\n"
            "Tell me about your hobbies, travel plans, or your last weekend! 😊"
        )
        return

    # ── 7. Save user message ──────────────────────────────────────────
    await save_message(session, user_id, "user", transcript, user.selected_tutor)
    await update_user_activity(session, user_id)
    await session.refresh(user)

    # ── 8. Build GPT context ──────────────────────────────────────────
    history = await get_recent_messages(session, user_id, limit=10)
    error_profile = await get_top_errors(session, user_id)

    # Topic starter for first messages on a new topic
    user_input = transcript
    if user.current_topic and user.total_messages <= 2:
        starter = TOPIC_LABEL_TO_STARTER.get(user.current_topic)
        if starter:
            user_input = starter

    # ── 9. YandexGPT response ─────────────────────────────────────────
    await bot.send_chat_action(message.chat.id, "typing")
    gpt_result = await get_gpt_response(
        user_message=user_input,
        tutor=user.selected_tutor,
        history=history,
        error_profile=error_profile,
        message_count=user.total_messages,
        current_topic=user.current_topic,
    )
    response_text = gpt_result.get("text", "")

    # Block signal from GPT
    if "##BLOCK_SESSION##" in response_text:
        await increment_violation(session, user_id)
        await message.answer(f"⚠️ {VIOLATION_MESSAGES[2]}")
        return

    # ── 10. Save bot response ─────────────────────────────────────────
    await save_message(session, user_id, "assistant", response_text, user.selected_tutor)

    # ── 11. TTS: text → OGG voice ─────────────────────────────────────
    await bot.send_chat_action(message.chat.id, "record_voice")
    audio_response = await synthesize_speech(response_text, tutor=user.selected_tutor)

    # ── 12. Send voice (or text fallback) ─────────────────────────────
    if audio_response and len(audio_response) > 100:
        voice_file = BufferedInputFile(audio_response, filename="response.ogg")
        await message.answer_voice(voice_file)
    else:
        # TTS unavailable — send text (still functional)
        await message.answer(
            f"🔊 <i>{response_text}</i>\n\n"
            "<code>ℹ️ Voice synthesis is temporarily unavailable</code>"
        )

    # ── 13. Grammar hint (if any) ──────────────────────────────────────
    hint = gpt_result.get("hint")
    if hint:
        await message.answer(f"💡 <b>Grammar tip:</b> {hint}")

    # ── 14. Fluency bar update (every 3 messages) ─────────────────────
    if user.total_messages > 0 and user.total_messages % 3 == 0:
        fluency_msg = get_fluency_message(user, POINTS_PER_MESSAGE)
        await message.answer(fluency_msg, parse_mode="Markdown")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, session: AsyncSession):
    """Redirect text messages to voice — keep UX voice-first."""
    user = await get_user(session, message.from_user.id)
    tutor_name = "John" if (not user or user.selected_tutor == "john") else "Mary"
    await message.answer(
        f"🎙️ <b>{tutor_name} prefers voice messages!</b>\n\n"
        "Send a voice message to practice your English speaking.\n"
        "That's where the real learning happens! 🎤\n\n"
        "Use /menu to see options."
    )
