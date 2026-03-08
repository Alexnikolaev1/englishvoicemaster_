"""Admin commands handler."""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, Subscription, Payment
from db.crud import reset_user_moderation
from config import config

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    total_users = await session.scalar(select(func.count(User.id)))
    active_subs = await session.scalar(
        select(func.count(Subscription.id)).where(Subscription.status == "active")
    )
    blocked = await session.scalar(select(func.count(User.id)).where(User.is_blocked == True))

    await message.answer(
        f"🛠️ *Admin Dashboard*\n\n"
        f"👥 Total users: *{total_users}*\n"
        f"💎 Active subscriptions: *{active_subs}*\n"
        f"⛔ Blocked users: *{blocked}*\n",
        parse_mode="Markdown"
    )


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("Usage: /broadcast Your message here")
        return

    result = await session.execute(select(User.id).where(User.is_blocked == False))
    user_ids = [row[0] for row in result.fetchall()]

    sent = 0
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, f"📢 {text}")
            sent += 1
        except Exception:
            pass

    await message.answer(f"✅ Broadcast sent to {sent}/{len(user_ids)} users.")


@router.message(Command("unblock"))
async def cmd_unblock(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /unblock <user_id>")
        return
    try:
        target_id = int(parts[1])
        await reset_user_moderation(session, target_id)
        await message.answer(f"✅ User {target_id} unblocked.")
    except ValueError:
        await message.answer("❌ Invalid user ID.")
