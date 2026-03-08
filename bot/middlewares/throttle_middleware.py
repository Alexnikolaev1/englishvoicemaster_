"""Rate limiting middleware."""
import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message

_user_timestamps: Dict[int, float] = {}
RATE_LIMIT_SECONDS = 2.0  # min seconds between messages


class ThrottleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not hasattr(event, "from_user") or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.monotonic()
        last = _user_timestamps.get(user_id, 0)

        if now - last < RATE_LIMIT_SECONDS:
            return  # silently drop

        _user_timestamps[user_id] = now
        return await handler(event, data)
