"""
Bot + Dispatcher factory.
Single source of truth — used by both:
  - api/webhook.py  (Vercel serverless)
  - local_run.py    (polling dev server)
"""
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from bot.handlers import start, voice, payment, admin
from bot.middlewares.db_middleware import DbSessionMiddleware
from bot.middlewares.throttle_middleware import ThrottleMiddleware

logger = logging.getLogger(__name__)

# Module-level singletons — safe because Vercel re-imports on cold start,
# and local run keeps them alive for the process lifetime.
_bot: Bot | None = None
_dp: Dispatcher | None = None


def get_bot() -> Bot:
    global _bot
    # In serverless mode each request can run in a fresh event loop.
    # Reusing one Bot instance across closed loops causes "Event loop is closed".
    if config.is_vercel:
        return Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    if _bot is None:
        _bot = Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        logger.info("Bot instance created")
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        dp = Dispatcher(storage=MemoryStorage())

        # ── Middlewares ──────────────────────────────────────────────
        dp.message.middleware(DbSessionMiddleware())
        dp.callback_query.middleware(DbSessionMiddleware())
        dp.message.middleware(ThrottleMiddleware())

        # ── Routers (order matters) ──────────────────────────────────
        dp.include_router(admin.router)    # admin commands first
        dp.include_router(start.router)    # /start, menu, topics
        dp.include_router(payment.router)  # payment callbacks
        dp.include_router(voice.router)    # voice + text catch-all

        _dp = dp
        logger.info("Dispatcher configured with all routers")
    return _dp
