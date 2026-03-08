"""
EnglishVoiceMaster — LOCAL DEVELOPMENT runner.

Uses long-polling (no webhook needed).
Perfect for local testing with a real bot token.

Usage:
    1. Copy .env.example → .env and fill in BOT_TOKEN + other keys
    2. Start PostgreSQL (or use Docker: docker-compose up -d postgres)
    3. python local_run.py

What this mode provides vs Vercel:
    ✅ Hot-reload friendly (Ctrl+C → re-run)
    ✅ Full logging to console + bot.log
    ✅ Background notification scheduler runs
    ✅ No webhook setup required
    ✅ Works without WEBHOOK_URL
    ⚠️  ffmpeg optional (for local audio conversion)
"""
import asyncio
import logging
import sys
import os

# Force local mode
os.environ.setdefault("DEPLOY_MODE", "local")

from aiogram import Bot
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from core.app_factory import get_bot, get_dispatcher
from db.session import init_db, close_db
from utils.notifications import schedule_reminders

# ── Logging setup ──────────────────────────────────────────────────────────
log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    log_handlers.append(logging.FileHandler("bot.log", encoding="utf-8"))
except Exception:
    pass  # /tmp may not be writable in some envs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=log_handlers,
)
logger = logging.getLogger(__name__)


def _check_env():
    """Validate required environment variables before starting."""
    errors = []
    if not config.BOT_TOKEN:
        errors.append("ERROR: BOT_TOKEN is not set")
    if not config.YANDEX_API_KEY:
        errors.append("WARN: YANDEX_API_KEY not set — GPT responses will use fallbacks")
    if not config.SPEECHKIT_API_KEY:
        errors.append("WARN: SPEECHKIT_API_KEY not set — voice will fall back to text")
    if not config.YUKASSA_SHOP_ID:
        errors.append("WARN: YUKASSA_SHOP_ID not set — payments will show mock links")

    for msg in errors:
        logger.warning(msg)

    if not config.BOT_TOKEN:
        logger.error("Cannot start without BOT_TOKEN. Edit your .env file.")
        sys.exit(1)


async def on_startup(bot: Bot):
    logger.info("=" * 60)
    logger.info("EnglishVoiceMaster - LOCAL MODE")
    logger.info("=" * 60)

    await init_db()
    logger.info("Database ready")

    # Remove any existing webhook so polling works
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook cleared (polling mode)")

    me = await bot.get_me()
    logger.info(f"Bot: @{me.username} (id={me.id})")
    logger.info(f"Trial: {config.FREE_TRIAL_DAYS} days / {config.FREE_TRIAL_MESSAGES} messages")
    logger.info("Ready! Open Telegram and send /start")
    logger.info("=" * 60)


async def on_shutdown(bot: Bot):
    logger.info("Shutting down EnglishVoiceMaster...")
    await close_db()
    await bot.session.close()
    logger.info("Shutdown complete")


async def main():
    _check_env()

    bot = get_bot()
    dp = get_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Background notifications (runs every hour)
    asyncio.ensure_future(schedule_reminders(bot))

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query"],
            polling_timeout=30,
        )
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    asyncio.run(main())
