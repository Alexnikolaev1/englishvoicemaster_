"""Start handler — onboarding flow."""
import logging
from pathlib import Path
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.types.input_file import FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import (
    get_or_create_user,
    get_user,
    set_tutor,
    has_access,
    is_on_trial,
    set_current_topic,
    set_user_language,
)
from bot.keyboards.main_menu import main_menu_kb, start_talking_kb, back_kb, language_kb
from bot.domain.topics import TOPIC_BY_KEY
from bot.i18n import normalize_lang, tr, language_label
from services.fluency import get_level_info, get_decay_warning
from config import config

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

WELCOME_TEXT_RU = """
🎤 *Добро пожаловать в EnglishVoiceMaster!*

Твой AI-коуч по разговорному английскому уже здесь — 24/7, терпеливый и реально интересный в общении.

━━━━━━━━━━━━━━━━━━━━━━
👨‍💼 *Джон* — британский наставник
Структурно, тепло, с аккуратным исправлением ошибок

👩‍💼 *Мэри* — американская собеседница
Энергично, живо, с современным разговорным английским
━━━━━━━━━━━━━━━━━━━━━━

🎁 *Бесплатный доступ:*
✅ {days} дня премиум-функций
✅ {messages} голосовых сообщений

*Как это работает:*
1️⃣ Отправляешь голосовое 🎙️
2️⃣ Наставник отвечает голосом 🔊
3️⃣ Ошибки корректируются естественно ✏️
4️⃣ Fluency Bar растет 📊

С кем начнем?
"""

WELCOME_TEXT_EN = """
🎤 *Welcome to EnglishVoiceMaster!*

Your AI-powered English speaking coach is here — available 24/7, patient, and genuinely fun to talk to.

━━━━━━━━━━━━━━━━━━━━━━
👨‍💼 *John* — Your British mentor
Structured, warm, BBC-style English

👩‍💼 *Mary* — Your American friend
Energetic, fun, modern American slang
━━━━━━━━━━━━━━━━━━━━━━

🎁 *You get FREE access:*
✅ {days} days of full premium
✅ {messages} voice messages

*How it works:*
1️⃣ Send a voice message 🎙️
2️⃣ Your tutor responds with voice 🔊
3️⃣ Your grammar gets corrected naturally ✏️
4️⃣ Your Fluency Bar grows 📊

Who would you like to start with?
"""

TUTOR_SELECTED_JOHN = """
👨‍💼 *John is ready for you!*

_"Hello! I'm John, your personal English tutor. I'm here to help you speak with confidence and clarity. What would you like to talk about today? Tell me a bit about yourself — where are you from, and why are you learning English?"_

🎙️ *Send me a voice message to begin!*

Current topic: 🤝 Small Talk _(change in menu)_
"""

TUTOR_SELECTED_MARY = """
👩‍💼 *Mary is SO excited to meet you!*

_"Oh my gosh, HI! I'm Mary, your new English bestie! I am literally so excited to help you improve your English — it's going to be SO much fun! Okay, so tell me everything — where are you from and what do you do? Let's talk!"_

🎙️ *Send me a voice message to begin!*

Current topic: 🤝 Small Talk _(change in menu)_
"""


def _tutor_label(selected_tutor: str) -> str:
    return "👨‍💼 John" if selected_tutor == "john" else "👩‍💼 Mary"


def _user_lang(user) -> str:
    return normalize_lang(user.language_code if user else None)


def _menu_text(
    lang: str,
    score: int,
    selected_tutor: str | None = None,
    streak_days: int | None = None,
    current_topic: str | None = None,
) -> str:
    info = get_level_info(score)
    text = (
        f"{tr(lang, 'menu_title')}\n\n"
        f"{tr(lang, 'menu_level', label=info['label'], cefr=info['cefr'])}\n"
        f"`{info['bar']}` {info['progress_pct']}%\n\n"
    )
    if selected_tutor is not None and streak_days is not None:
        text += (
            f"{tr(lang, 'menu_tutor', tutor=_tutor_label(selected_tutor))}\n"
            f"{tr(lang, 'menu_topic', topic=current_topic or '🤝 Small Talk')}\n"
            f"{tr(lang, 'menu_streak', days=streak_days)}"
        )
    else:
        text += tr(lang, "menu_choose")
    return text


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    user = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        language_code="ru",
    )
    lang = _user_lang(user)

    # Check for decay warning on return visits
    warning = get_decay_warning(user)
    if warning and user.total_messages > 0:
        await message.answer(warning, parse_mode="Markdown")

    welcome_tpl = WELCOME_TEXT_RU if lang == "ru" else WELCOME_TEXT_EN
    welcome = welcome_tpl.format(
        days=config.FREE_TRIAL_DAYS,
        messages=config.FREE_TRIAL_MESSAGES,
    )
    await message.answer(welcome, parse_mode="Markdown", reply_markup=start_talking_kb(lang))


@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession):
    user = await get_user(session, message.from_user.id)
    if not user:
        await message.answer("Please use /start first.")
        return
    lang = _user_lang(user)
    text = _menu_text(
        lang=lang,
        score=user.fluency_score,
        selected_tutor=user.selected_tutor,
        streak_days=user.streak_days,
        current_topic=user.current_topic,
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_kb(lang))


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery, session: AsyncSession):
    user = await get_user(session, callback.from_user.id)
    lang = _user_lang(user)
    text = _menu_text(lang=lang, score=user.fluency_score if user else 0)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_kb(lang))
    await callback.answer()


@router.callback_query(F.data == "menu:language")
async def menu_language(callback: CallbackQuery, session: AsyncSession):
    user = await get_user(session, callback.from_user.id)
    lang = _user_lang(user)
    await callback.message.edit_text(
        tr(lang, "language_select_title"),
        parse_mode="Markdown",
        reply_markup=language_kb(lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lang:set:"))
async def set_language(callback: CallbackQuery, session: AsyncSession):
    lang = normalize_lang(callback.data.split(":")[-1])
    await set_user_language(session, callback.from_user.id, lang)
    await callback.answer(tr(lang, "language_saved", label=language_label(lang)))
    user = await get_user(session, callback.from_user.id)
    text = _menu_text(lang=lang, score=user.fluency_score if user else 0)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_kb(lang))


@router.callback_query(F.data.startswith("tutor:"))
async def select_tutor(callback: CallbackQuery, session: AsyncSession):
    tutor = callback.data.split(":")[1]
    user = await get_user(session, callback.from_user.id)
    if not user:
        user = await get_or_create_user(session, callback.from_user.id)
    await set_tutor(session, callback.from_user.id, tutor)

    if tutor == "john":
        await callback.message.edit_text(TUTOR_SELECTED_JOHN, parse_mode="Markdown")
    else:
        await callback.message.edit_text(TUTOR_SELECTED_MARY, parse_mode="Markdown")

    image_path = _resolve_tutor_image(tutor)
    if image_path:
        await callback.message.answer_photo(FSInputFile(str(image_path)))

    await callback.answer(f"{'👨‍💼 John' if tutor == 'john' else '👩‍💼 Mary'} selected!")


@router.callback_query(F.data == "menu:progress")
async def show_progress(callback: CallbackQuery, session: AsyncSession):
    user = await get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Please start the bot first.")
        return
    info = get_level_info(user.fluency_score)
    lang = _user_lang(user)
    on_trial = await is_on_trial(session, user)
    has_sub = await has_access(session, user)

    status = "🎁 Free Trial" if on_trial else ("💎 Premium" if has_sub else "❌ No Access")
    msgs_left = config.FREE_TRIAL_MESSAGES - user.free_messages_used if on_trial else "∞"

    text = (
        f"📊 *Your Progress*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎓 Level: *{info['label']}* ({info['cefr']})\n"
        f"📈 Score: *{info['score']}/1000*\n"
        f"`{info['bar']}` {info['progress_pct']}%\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 Streak: *{user.streak_days} days*\n"
        f"💬 Total messages: *{user.total_messages}*\n"
        f"🎙️ Tutor: *{'👨‍💼 John' if user.selected_tutor == 'john' else '👩‍💼 Mary'}*\n"
        f"📋 Status: *{status}*\n"
        f"✉️ Messages left: *{msgs_left}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 Keep practicing daily to maintain your streak!"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_kb(lang))
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def show_help(callback: CallbackQuery, session: AsyncSession):
    user = await get_user(session, callback.from_user.id)
    lang = _user_lang(user)
    if lang == "ru":
        text = (
            "ℹ️ *Как работает EnglishVoiceMaster*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "*🎙️ Разговорная практика*\n"
            "Отправляй голосовые — наставник отвечает голосом.\n\n"
            "*✏️ Умные исправления*\n"
            "Ошибки корректируются естественно прямо в диалоге.\n\n"
            "*📊 Fluency Bar*\n"
            "Каждое сообщение дает очки. Серия дней дает бонус.\n"
            "Пропуски снижают прогресс — регулярность повышает уровень.\n\n"
            "*📚 Темы*\n"
            "Выбирай тему и тренируй словарь в нужном контексте.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔊 *Отправь голосовое и начнем!*"
        )
    else:
        text = (
            "ℹ️ *How EnglishVoiceMaster Works*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "*🎙️ Speaking Practice*\n"
            "Send a voice message — your tutor responds with voice.\n\n"
            "*✏️ Smart Corrections*\n"
            "Grammar mistakes are corrected naturally in conversation.\n\n"
            "*📊 Fluency Bar*\n"
            "Each message gives points. Daily streaks give bonuses.\n\n"
            "*📚 Topics*\n"
            "Choose a topic and focus your conversation practice.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔊 *Send a voice message now to begin!*"
        )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_kb(lang))
    await callback.answer()


@router.callback_query(F.data == "menu:topics")
async def show_topics(callback: CallbackQuery, session: AsyncSession):
    from bot.keyboards.main_menu import topics_kb
    user = await get_user(session, callback.from_user.id)
    lang = _user_lang(user)
    text = (
        "📚 *Выбери тему разговора*\n\n"
        "Наставник будет вести диалог в выбранном контексте.\n"
        "Выбери тему для сегодняшней практики!"
        if lang == "ru"
        else
        "📚 *Choose a Conversation Topic*\n\n"
        "Your tutor will guide the conversation around this theme.\n"
        "Pick one to focus your practice today!"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=topics_kb(lang))
    await callback.answer()


@router.callback_query(F.data.startswith("topic:"))
async def select_topic(callback: CallbackQuery, session: AsyncSession):
    topic_key = callback.data.split(":")[1]
    topic = TOPIC_BY_KEY.get(topic_key)
    if not topic:
        await callback.answer("Unknown topic.", show_alert=True)
        return

    await set_current_topic(session, callback.from_user.id, topic.label)

    user = await get_user(session, callback.from_user.id)
    lang = _user_lang(user)
    await callback.message.edit_text(
        f"✅ *Topic set: {topic.label}*\n\n"
        f"Your tutor will focus the conversation on this theme.\n"
        f"🎙️ Send a voice message to begin!",
        parse_mode="Markdown",
        reply_markup=back_kb(lang)
    )
    await callback.answer(f"Topic: {topic.label}")
