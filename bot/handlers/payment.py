"""Payment handler for YuKassa subscriptions."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from db.crud import create_subscription, create_payment, update_payment_status, get_user
from services.yukassa import create_payment as yk_create, check_payment_status, PLANS
from bot.keyboards.main_menu import subscribe_kb, confirm_pay_kb, back_kb
from bot.i18n import normalize_lang

logger = logging.getLogger(__name__)
router = Router()

# Store pending payments in memory (in prod: use Redis)
_pending_payments: dict[str, dict] = {}  # yukassa_id -> {user_id, plan}


async def _user_lang(session: AsyncSession, user_id: int) -> str:
    user = await get_user(session, user_id)
    return normalize_lang(user.language_code if user else None)


@router.callback_query(F.data == "menu:subscribe")
async def show_subscribe(callback: CallbackQuery, session: AsyncSession):
    lang = await _user_lang(session, callback.from_user.id)
    text = (
        "💎 *Choose Your Plan*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📅 *1 Month — 599 ₽*\n"
        "Full access to John & Mary + all topics\n\n"
        "📆 *1 Year — 4990 ₽* _(save 30%!)_\n"
        "Best value + progress freeze (7 days/month)\n\n"
        "👨‍👩‍👧 *Family — 899 ₽/month*\n"
        "2 accounts + shared progress tracking\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔒 Secure payment via YuKassa\n"
        "❄️ Active subscription *freezes your Fluency Bar*"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=subscribe_kb(lang))
    await callback.answer()


@router.callback_query(F.data.startswith("pay:"))
async def initiate_payment(callback: CallbackQuery, session: AsyncSession):
    lang = await _user_lang(session, callback.from_user.id)
    plan = callback.data.split(":")[1]
    user_id = callback.from_user.id
    plan_data = PLANS.get(plan)
    if not plan_data:
        await callback.answer("Unknown plan.", show_alert=True)
        return

    await callback.answer("Creating payment link... ⏳")

    return_url = f"https://t.me/{(await callback.bot.get_me()).username}"
    payment_data = await yk_create(user_id, plan, return_url)

    if not payment_data:
        await callback.message.edit_text(
            "❌ Payment service is temporarily unavailable. Please try again later.",
            reply_markup=back_kb(lang, "menu:subscribe")
        )
        return

    yukassa_id = payment_data.get("id", "")
    payment_url = payment_data.get("confirmation", {}).get("confirmation_url", "")

    # Store pending
    _pending_payments[yukassa_id] = {"user_id": user_id, "plan": plan}

    # Save to DB
    await create_payment(
        session, user_id, yukassa_id,
        float(plan_data["amount"].replace(",", ".")),
        plan
    )

    text = (
        f"💳 *Payment Details*\n\n"
        f"Plan: *{plan_data['label']}*\n"
        f"Amount: *{plan_data['amount']} ₽*\n"
        f"Duration: *{plan_data['days']} days*\n\n"
        f"Click the button below to pay securely.\n"
        f"After payment, press ✅ to activate your subscription!"
    )
    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=confirm_pay_kb(payment_url, f"{plan}:{yukassa_id}", lang)
    )


@router.callback_query(F.data.startswith("checkpay:"))
async def check_payment(callback: CallbackQuery, session: AsyncSession):
    lang = await _user_lang(session, callback.from_user.id)
    parts = callback.data.split(":")
    plan = parts[1]
    yukassa_id = parts[2] if len(parts) > 2 else ""

    await callback.answer("Checking payment... ⏳")

    if not yukassa_id:
        await callback.message.edit_text(
            "❌ Payment ID not found. Please try creating a new payment.",
            reply_markup=back_kb(lang, "menu:subscribe")
        )
        return

    status = await check_payment_status(yukassa_id)
    await update_payment_status(session, yukassa_id, status)

    if status == "succeeded":
        plan_data = PLANS.get(plan, {})
        days = plan_data.get("days", 30)
        await create_subscription(session, callback.from_user.id, plan, yukassa_id, days)
        _pending_payments.pop(yukassa_id, None)

        await callback.message.edit_text(
            f"🎉 *Payment Successful!*\n\n"
            f"✅ Your *{plan_data.get('label', plan)}* subscription is now active!\n"
            f"📅 Valid for: *{days} days*\n"
            f"❄️ Your Fluency Bar is now *frozen* — practice without fear!\n\n"
            f"🎙️ Send a voice message to continue learning!",
            parse_mode="Markdown",
            reply_markup=back_kb(lang)
        )
    elif status == "pending":
        await callback.message.edit_text(
            "⏳ *Payment not confirmed yet.*\n\n"
            "If you've already paid, please wait a few seconds and check again.\n"
            "Payments usually process within 1-2 minutes.",
            parse_mode="Markdown",
            reply_markup=confirm_pay_kb("", f"{plan}:{yukassa_id}", lang)
        )
    else:
        await callback.message.edit_text(
            "❌ *Payment was not completed.*\n\n"
            "The payment was canceled or failed. Please try again.",
            parse_mode="Markdown",
            reply_markup=back_kb(lang, "menu:subscribe")
        )
