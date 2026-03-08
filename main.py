"""EnglishVoiceMaster — Main entry point."""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from db.session import init_db
from bot.handlers import start, voice, payment, admin
from bot.middlewares.db_middleware import DbSessionMiddleware
from bot.middlewares.throttle_middleware import ThrottleMiddleware
from utils.notifications import schedule_reminders

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    logger.info("🚀 EnglishVoiceMaster is starting up...")
    await init_db()
    logger.info("✅ Database initialized")
    me = await bot.get_me()
    logger.info(f"✅ Bot: @{me.username} ({me.id})")

    if config.WEBHOOK_URL:
        webhook_url = f"{config.WEBHOOK_URL}{config.WEBHOOK_PATH if hasattr(config, 'WEBHOOK_PATH') else '/webhook'}"
        await bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook set to {webhook_url}")
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Polling mode — webhook cleared")

    logger.info("🎤 EnglishVoiceMaster is READY!")


async def on_shutdown(bot: Bot):
    logger.info("👋 EnglishVoiceMaster shutting down...")
    await bot.session.close()


async def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN is not set! Please configure .env file.")
        sys.exit(1)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # ── Middlewares ──────────────────────────────────────────────────────
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(ThrottleMiddleware())

    # ── Routers ──────────────────────────────────────────────────────────
    dp.include_router(admin.router)    # admin first (priority)
    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(voice.router)    # voice last (catch-all)

    # ── Startup / Shutdown ───────────────────────────────────────────────
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # ── Background tasks ─────────────────────────────────────────────────
    asyncio.ensure_future(schedule_reminders(bot))

    # ── Start ────────────────────────────────────────────────────────────
    logger.info("▶️  Starting polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
