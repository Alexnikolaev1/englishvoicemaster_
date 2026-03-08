"""
Vercel Serverless Function — Telegram Webhook endpoint.

Vercel maps this file to: POST /api/webhook
Each incoming Telegram update triggers a fresh invocation of this handler.

Important constraints on Vercel:
  - Max execution time: 10s (Hobby) / 60s (Pro)
  - No persistent filesystem (use /tmp sparingly)
  - No background threads/tasks (asyncio.ensure_future won't outlive request)
  - No ffmpeg binary available → audio handled via Yandex SpeechKit directly
  - Stateless between invocations → DB connection via NullPool
"""
import json
import logging
import os
import sys
import asyncio
from http.server import BaseHTTPRequestHandler

# Make sure project root is on Python path for Vercel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aiogram.types import Update
from config import config
from core.app_factory import get_bot, get_dispatcher
from db.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# DB init flag — run once per cold start
_db_initialized = False


async def _init_db_once():
    global _db_initialized
    if not _db_initialized:
        try:
            await init_db()
            _db_initialized = True
        except Exception as e:
            logger.error(f"DB init failed: {e}")


async def process_update(body: bytes, secret_header: str | None) -> tuple[int, str]:
    """
    Core handler: parse Telegram update → feed to aiogram dispatcher.
    Returns (http_status_code, response_body).
    """
    # ── Security: verify secret token ────────────────────────────────
    if config.WEBHOOK_SECRET and secret_header != config.WEBHOOK_SECRET:
        logger.warning("Webhook: invalid secret token")
        return 403, "Forbidden"

    # ── Parse update ─────────────────────────────────────────────────
    try:
        update_data = json.loads(body)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return 400, "Bad Request"

    # ── Ensure DB tables exist ────────────────────────────────────────
    await _init_db_once()

    # ── Feed update to aiogram ────────────────────────────────────────
    bot = get_bot()
    dp = get_dispatcher()

    try:
        update = Update.model_validate(update_data)
        await dp.feed_update(bot=bot, update=update)
        return 200, "OK"
    except Exception as e:
        logger.error(f"Update processing error: {e}", exc_info=True)
        return 200, "OK"  # Always return 200 to Telegram to avoid retries


class handler(BaseHTTPRequestHandler):
    """
    Vercel expects a class named 'handler' inheriting BaseHTTPRequestHandler
    in api/*.py files.
    """

    def log_message(self, format, *args):
        """Suppress default HTTP logging — use our logger instead."""
        logger.debug(f"HTTP {format}", *args)

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "service": "EnglishVoiceMaster",
            "mode": "webhook",
        }).encode())

    def do_POST(self):
        """Main webhook handler — called by Telegram for every update."""
        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Secret token (Telegram sends it as X-Telegram-Bot-Api-Secret-Token)
        secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")

        # Run async handler in a new event loop
        # (Vercel Python runtime is sync; we bridge to async here)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            status, response = loop.run_until_complete(
                process_update(body, secret)
            )
        except Exception as e:
            logger.error(f"Handler exception: {e}", exc_info=True)
            status, response = 500, "Internal Server Error"
        finally:
            loop.close()

        # Send response
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(response.encode())
