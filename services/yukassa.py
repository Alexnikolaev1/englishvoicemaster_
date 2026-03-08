"""YuKassa payment integration."""
import aiohttp
import uuid
import logging
from datetime import timedelta
from config import config

logger = logging.getLogger(__name__)

PLANS = {
    "month": {
        "amount": str(config.PRICE_MONTH_RUB) + ".00",
        "description": "EnglishVoiceMaster — Подписка на 1 месяц",
        "days": 30,
        "label": "1 месяц",
    },
    "year": {
        "amount": str(config.PRICE_YEAR_RUB) + ".00",
        "description": "EnglishVoiceMaster — Подписка на 1 год (скидка 30%)",
        "days": 365,
        "label": "1 год",
    },
    "family": {
        "amount": str(config.PRICE_FAMILY_RUB) + ".00",
        "description": "EnglishVoiceMaster — Семейный план (2 аккаунта)",
        "days": 30,
        "label": "Семейный (2 акк.)",
    },
}


async def create_payment(user_id: int, plan: str, return_url: str) -> dict | None:
    """Create a YuKassa payment and return payment info."""
    if not config.YUKASSA_SHOP_ID or not config.YUKASSA_SECRET_KEY:
        logger.warning("YuKassa not configured")
        return {"id": f"mock_{uuid.uuid4().hex[:8]}", "confirmation": {"confirmation_url": "https://example.com/pay"}}

    plan_data = PLANS.get(plan)
    if not plan_data:
        return None

    idempotency_key = str(uuid.uuid4())
    payload = {
        "amount": {"value": plan_data["amount"], "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": plan_data["description"],
        "metadata": {"user_id": str(user_id), "plan": plan},
    }

    auth = aiohttp.BasicAuth(config.YUKASSA_SHOP_ID, config.YUKASSA_SECRET_KEY)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.yookassa.ru/v3/payments",
                auth=auth,
                json=payload,
                headers={"Idempotence-Key": idempotency_key},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                else:
                    err = await resp.text()
                    logger.error(f"YuKassa create payment error {resp.status}: {err}")
                    return None
    except Exception as e:
        logger.error(f"YuKassa exception: {e}")
        return None


async def check_payment_status(payment_id: str) -> str:
    """Check payment status: 'pending' | 'succeeded' | 'canceled'"""
    if not config.YUKASSA_SHOP_ID:
        return "pending"
    auth = aiohttp.BasicAuth(config.YUKASSA_SHOP_ID, config.YUKASSA_SECRET_KEY)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.yookassa.ru/v3/payments/{payment_id}",
                auth=auth,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("status", "pending")
                return "error"
    except Exception as e:
        logger.error(f"YuKassa check status error: {e}")
        return "error"
