from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.domain.topics import TOPICS
from bot.i18n import tr, LANGUAGE_OPTIONS, normalize_lang


def main_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    lang = normalize_lang(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=tr(lang, "btn_john"), callback_data="tutor:john"),
            InlineKeyboardButton(text=tr(lang, "btn_mary"), callback_data="tutor:mary"),
        ],
        [InlineKeyboardButton(text=tr(lang, "btn_progress"), callback_data="menu:progress")],
        [InlineKeyboardButton(text=tr(lang, "btn_topic"), callback_data="menu:topics")],
        [InlineKeyboardButton(text=tr(lang, "btn_subscribe"), callback_data="menu:subscribe")],
        [InlineKeyboardButton(text=tr(lang, "btn_help"), callback_data="menu:help")],
        [InlineKeyboardButton(text=tr(lang, "btn_language"), callback_data="menu:language")],
    ])


def topics_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=topic.label, callback_data=f"topic:{topic.key}")]
        for topic in TOPICS
    ]
    buttons.append([InlineKeyboardButton(text=tr(lang, "btn_back"), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscribe_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(lang, "btn_month"), callback_data="pay:month")],
        [InlineKeyboardButton(text=tr(lang, "btn_year"), callback_data="pay:year")],
        [InlineKeyboardButton(text=tr(lang, "btn_family"), callback_data="pay:family")],
        [InlineKeyboardButton(text=tr(lang, "btn_back"), callback_data="menu:main")],
    ])


def tutor_choice_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{tr(lang, 'btn_john')} (British 🇬🇧)", callback_data="tutor:john"),
            InlineKeyboardButton(text=f"{tr(lang, 'btn_mary')} (American 🇺🇸)", callback_data="tutor:mary"),
        ],
        [InlineKeyboardButton(text=tr(lang, "btn_back"), callback_data="menu:main")],
    ])


def confirm_pay_kb(payment_url: str, plan: str, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    if payment_url:
        rows.append([InlineKeyboardButton(text=tr(lang, "btn_pay_now"), url=payment_url)])
    rows.append([InlineKeyboardButton(text=tr(lang, "btn_paid_check"), callback_data=f"checkpay:{plan}")])
    rows.append([InlineKeyboardButton(text=tr(lang, "btn_cancel"), callback_data="menu:subscribe")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_kb(lang: str = "ru", callback: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(lang, "btn_back"), callback_data=callback)]
    ])


def start_talking_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(lang, "btn_start_john"), callback_data="tutor:john")],
        [InlineKeyboardButton(text=tr(lang, "btn_start_mary"), callback_data="tutor:mary")],
        [InlineKeyboardButton(text=tr(lang, "btn_choose_topic_first"), callback_data="menu:topics")],
        [InlineKeyboardButton(text=tr(lang, "btn_language"), callback_data="menu:language")],
    ])


def subscribe_prompt_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(lang, "btn_get_access"), callback_data="menu:subscribe")],
        [InlineKeyboardButton(text=tr(lang, "btn_see_progress"), callback_data="menu:progress")],
    ])


def language_kb(selected_lang: str = "ru") -> InlineKeyboardMarkup:
    selected_lang = normalize_lang(selected_lang)
    rows = []
    row = []
    for item in LANGUAGE_OPTIONS:
        prefix = "✅ " if item.code == selected_lang else ""
        row.append(InlineKeyboardButton(text=f"{prefix}{item.label}", callback_data=f"lang:set:{item.code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=tr(selected_lang, "btn_back"), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
