"""Simple i18n utilities for bot UI."""

from dataclasses import dataclass


DEFAULT_LANG = "ru"
SUPPORTED_LANGS = ("ru", "en", "es", "zh", "fr", "de", "pt", "ar", "hi", "tr")


@dataclass(frozen=True)
class LanguageOption:
    code: str
    label: str


LANGUAGE_OPTIONS: tuple[LanguageOption, ...] = (
    LanguageOption("ru", "Русский"),
    LanguageOption("en", "English"),
    LanguageOption("es", "Espanol"),
    LanguageOption("zh", "中文"),
    LanguageOption("fr", "Francais"),
    LanguageOption("de", "Deutsch"),
    LanguageOption("pt", "Portugues"),
    LanguageOption("ar", "العربية"),
    LanguageOption("hi", "Hindi"),
    LanguageOption("tr", "Turkce"),
)


STRINGS = {
    "ru": {
        "btn_john": "👨‍💼 Джон",
        "btn_mary": "👩‍💼 Мэри",
        "btn_progress": "📊 Мой прогресс",
        "btn_topic": "📚 Выбрать тему",
        "btn_subscribe": "💎 Подписка",
        "btn_help": "ℹ️ Как это работает",
        "btn_language": "🌐 Язык",
        "btn_back": "🔙 Назад в меню",
        "btn_start_john": "🎙️ Начать с Джоном",
        "btn_start_mary": "🎙️ Начать с Мэри",
        "btn_choose_topic_first": "📚 Сначала выбрать тему",
        "btn_get_access": "💎 Получить полный доступ",
        "btn_see_progress": "📊 Смотреть прогресс",
        "btn_pay_now": "💳 Оплатить",
        "btn_paid_check": "✅ Я оплатил — проверить",
        "btn_cancel": "❌ Отмена",
        "btn_month": "📅 1 месяц — 599 ₽",
        "btn_year": "📆 1 год — 4990 ₽ (-30%)",
        "btn_family": "👨‍👩‍👧 Семейный — 899 ₽/мес",
        "language_select_title": "🌐 *Выберите язык интерфейса*",
        "language_saved": "Язык сохранен: {label}",
        "unknown_language": "Неизвестный язык.",
        "menu_title": "📋 *Главное меню*",
        "menu_level": "📊 Ваш уровень: {label} ({cefr})",
        "menu_tutor": "🎙️ Текущий наставник: {tutor}",
        "menu_topic": "📚 Тема: {topic}",
        "menu_streak": "🔥 Серия: {days} дней",
        "menu_choose": "Выберите действие ниже 👇",
    },
    "en": {
        "btn_john": "👨‍💼 John",
        "btn_mary": "👩‍💼 Mary",
        "btn_progress": "📊 My Progress",
        "btn_topic": "📚 Choose Topic",
        "btn_subscribe": "💎 Subscribe",
        "btn_help": "ℹ️ How It Works",
        "btn_language": "🌐 Language",
        "btn_back": "🔙 Back to Menu",
        "btn_start_john": "🎙️ Start with John",
        "btn_start_mary": "🎙️ Start with Mary",
        "btn_choose_topic_first": "📚 Choose a Topic First",
        "btn_get_access": "💎 Get Full Access",
        "btn_see_progress": "📊 See My Progress",
        "btn_pay_now": "💳 Pay Now",
        "btn_paid_check": "✅ I've Paid - Check",
        "btn_cancel": "❌ Cancel",
        "btn_month": "📅 1 Month — 599 ₽",
        "btn_year": "📆 1 Year — 4990 ₽ (-30%)",
        "btn_family": "👨‍👩‍👧 Family — 899 ₽/month",
        "language_select_title": "🌐 *Choose your interface language*",
        "language_saved": "Language saved: {label}",
        "unknown_language": "Unknown language.",
        "menu_title": "📋 *Main Menu*",
        "menu_level": "📊 Your level: {label} ({cefr})",
        "menu_tutor": "🎙️ Current tutor: {tutor}",
        "menu_topic": "📚 Topic: {topic}",
        "menu_streak": "🔥 Streak: {days} days",
        "menu_choose": "Choose an option below 👇",
    },
}


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LANG
    short = lang.lower().split("-")[0]
    return short if short in SUPPORTED_LANGS else DEFAULT_LANG


def tr(lang: str | None, key: str, **kwargs) -> str:
    code = normalize_lang(lang)
    template = STRINGS.get(code, {}).get(key) or STRINGS["en"].get(key) or key
    return template.format(**kwargs) if kwargs else template


def language_label(code: str) -> str:
    normalized = normalize_lang(code)
    for option in LANGUAGE_OPTIONS:
        if option.code == normalized:
            return option.label
    return normalized

