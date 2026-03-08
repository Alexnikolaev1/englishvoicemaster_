"""
Vercel Serverless Function — one-time webhook setup utility.
Call GET /api/setup_webhook?token=<your_secret> to register the webhook with Telegram.

Usage after deploy:
  curl "https://your-app.vercel.app/api/setup_webhook?token=your_secret"
"""
import json
import logging
import os
import sys
import asyncio
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import config
from core.app_factory import get_bot

logger = logging.getLogger(__name__)


async def _setup() -> dict:
    bot = get_bot()
    me = await bot.get_me()

    webhook_url = config.full_webhook_url
    if not webhook_url:
        return {"ok": False, "error": "WEBHOOK_URL or VERCEL_URL not configured"}

    await bot.set_webhook(
        url=webhook_url,
        secret_token=config.WEBHOOK_SECRET,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )
    info = await bot.get_webhook_info()
    return {
        "ok": True,
        "bot": f"@{me.username}",
        "webhook_url": webhook_url,
        "pending_updates": info.pending_update_count,
    }


async def _delete() -> dict:
    bot = get_bot()
    await bot.delete_webhook(drop_pending_updates=True)
    return {"ok": True, "action": "webhook deleted"}


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        token = qs.get("token", [""])[0]
        action = qs.get("action", ["setup"])[0]  # setup | delete

        # Simple auth: require matching WEBHOOK_SECRET
        if token != config.WEBHOOK_SECRET:
            self._respond(403, {"ok": False, "error": "Unauthorized"})
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            if action == "delete":
                result = loop.run_until_complete(_delete())
            else:
                result = loop.run_until_complete(_setup())
        except Exception as e:
            result = {"ok": False, "error": str(e)}
        finally:
            loop.close()

        self._respond(200 if result.get("ok") else 500, result)

    def _respond(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
