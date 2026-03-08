"""Scheduled notification tasks."""
import logging
import asyncio
from datetime import date, timedelta
from sqlalchemy import select, and_
from db.session import AsyncSessionLocal
from db.models import User
from services.fluency import get_decay_warning

logger = logging.getLogger(__name__)


async def send_daily_reminders(bot):
    """Send decay warnings and streak reminders."""
    async with AsyncSessionLocal() as session:
        yesterday = date.today() - timedelta(days=1)
        result = await session.execute(
            select(User).where(
                and_(
                    User.is_blocked == False,
                    User.last_active < date.today(),
                    User.total_messages > 0,
                )
            )
        )
        users = result.scalars().all()
        sent = 0
        for user in users:
            warning = get_decay_warning(user)
            if warning:
                try:
                    await bot.send_message(user.id, warning, parse_mode="Markdown")
                    sent += 1
                    await asyncio.sleep(0.05)  # Rate limit
                except Exception as e:
                    logger.debug(f"Could not send reminder to {user.id}: {e}")
        logger.info(f"Sent {sent} daily reminders")


async def schedule_reminders(bot):
    """Run reminder task every hour."""
    while True:
        await asyncio.sleep(3600)
        try:
            await send_daily_reminders(bot)
        except Exception as e:
            logger.error(f"Reminder task error: {e}")
