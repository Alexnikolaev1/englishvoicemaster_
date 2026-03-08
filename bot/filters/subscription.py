"""Subscription filter."""
from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from db.crud import get_user, has_access


class SubscriptionFilter(BaseFilter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        user = await get_user(session, message.from_user.id)
        if not user:
            return False
        return await has_access(session, user)
