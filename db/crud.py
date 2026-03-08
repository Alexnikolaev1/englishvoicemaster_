from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, desc
from .models import User, Subscription, Message, UserError, Payment, ModerationBlock
from config import config
from services.fluency import POINTS_PER_MESSAGE, POINTS_STREAK_BONUS, POINTS_DECAY_PER_DAY


# ─── USERS ───────────────────────────────────────────────────────────────────

async def get_or_create_user(session: AsyncSession, telegram_id: int,
                              username: str = None, first_name: str = None,
                              language_code: str = None) -> User:
    result = await session.execute(select(User).where(User.id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        trial_expires = datetime.utcnow() + timedelta(days=config.FREE_TRIAL_DAYS)
        user = User(
            id=telegram_id,
            username=username,
            first_name=first_name,
            language_code=language_code,
            trial_expires_at=trial_expires,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == telegram_id))
    return result.scalar_one_or_none()


async def update_user_activity(session: AsyncSession, user_id: int):
    today = date.today()
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return
    yesterday = today - timedelta(days=1)
    if user.last_active == yesterday:
        user.streak_days += 1
        user.fluency_score = min(user.fluency_score + POINTS_STREAK_BONUS, 1000)
    elif user.last_active != today and user.last_active is not None:
        days_missed = (today - user.last_active).days
        user.streak_days = 0

        # TZ rule:
        # - miss 1 day: -15
        # - miss 2+ days: -30/day
        active_sub = await get_active_subscription(session, user_id)
        if not active_sub:
            decay = (
                POINTS_DECAY_PER_DAY
                if days_missed == 1
                else POINTS_DECAY_PER_DAY * 2 * days_missed
            )
            user.fluency_score = max(0, user.fluency_score - decay)

    # Base progress for each valid practice message.
    user.fluency_score = min(user.fluency_score + POINTS_PER_MESSAGE, 1000)

    # Consume free trial message only while trial is still active.
    trial_active = (
        user.trial_expires_at is not None
        and user.trial_expires_at > datetime.utcnow()
        and user.free_messages_used < config.FREE_TRIAL_MESSAGES
    )
    if trial_active:
        user.free_messages_used += 1

    user.last_active = today
    user.message_count_today += 1
    user.total_messages += 1
    await session.commit()


async def update_fluency(session: AsyncSession, user_id: int, points: int):
    await session.execute(
        update(User).where(User.id == user_id)
        .values(fluency_score=User.fluency_score + points)
    )
    await session.commit()


async def set_tutor(session: AsyncSession, user_id: int, tutor: str):
    await session.execute(update(User).where(User.id == user_id).values(selected_tutor=tutor))
    await session.commit()


async def set_user_language(session: AsyncSession, user_id: int, language_code: str):
    await session.execute(update(User).where(User.id == user_id).values(language_code=language_code))
    await session.commit()


async def set_current_topic(session: AsyncSession, user_id: int, topic_label: str):
    await session.execute(update(User).where(User.id == user_id).values(current_topic=topic_label))
    await session.commit()


async def increment_violation(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.violation_count += 1
        if user.violation_count >= 5:
            user.is_blocked = True
        await session.commit()
        return user.violation_count
    return 0


async def set_temporary_block(session: AsyncSession, user_id: int, hours: int = 24):
    blocked_until = datetime.utcnow() + timedelta(hours=hours)
    result = await session.execute(select(ModerationBlock).where(ModerationBlock.user_id == user_id))
    block = result.scalar_one_or_none()
    if block:
        block.blocked_until = blocked_until
    else:
        session.add(
            ModerationBlock(
                user_id=user_id,
                blocked_until=blocked_until,
                reason="policy_violation",
            )
        )
    await session.commit()


async def get_temporary_block(session: AsyncSession, user_id: int) -> ModerationBlock | None:
    result = await session.execute(select(ModerationBlock).where(ModerationBlock.user_id == user_id))
    block = result.scalar_one_or_none()
    if not block:
        return None
    if block.blocked_until <= datetime.utcnow():
        await session.delete(block)
        await session.commit()
        return None
    return block


async def clear_temporary_block(session: AsyncSession, user_id: int):
    result = await session.execute(select(ModerationBlock).where(ModerationBlock.user_id == user_id))
    block = result.scalar_one_or_none()
    if block:
        await session.delete(block)
        await session.commit()


async def reset_user_moderation(session: AsyncSession, user_id: int):
    await clear_temporary_block(session, user_id)
    await session.execute(
        update(User).where(User.id == user_id).values(is_blocked=False, violation_count=0)
    )
    await session.commit()


async def block_user(session: AsyncSession, user_id: int):
    await session.execute(update(User).where(User.id == user_id).values(is_blocked=True))
    await session.commit()


# ─── SUBSCRIPTIONS ────────────────────────────────────────────────────────────

async def get_active_subscription(session: AsyncSession, user_id: int) -> Subscription | None:
    result = await session.execute(
        select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.status == "active",
                Subscription.expires_at > datetime.utcnow()
            )
        ).order_by(desc(Subscription.expires_at))
    )
    return result.scalar_one_or_none()


async def create_subscription(session: AsyncSession, user_id: int, plan: str,
                               payment_id: str, days: int) -> Subscription:
    sub = Subscription(
        user_id=user_id,
        plan=plan,
        payment_id=payment_id,
        expires_at=datetime.utcnow() + timedelta(days=days),
        status="active"
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


async def is_on_trial(session: AsyncSession, user: User) -> bool:
    """Check if user is still within free trial."""
    if user.trial_expires_at and user.trial_expires_at > datetime.utcnow():
        if user.free_messages_used < config.FREE_TRIAL_MESSAGES:
            return True
    return False


async def has_access(session: AsyncSession, user: User) -> bool:
    """Check if user has full access (trial or subscription)."""
    if user.is_blocked:
        return False
    if await is_on_trial(session, user):
        return True
    sub = await get_active_subscription(session, user.id)
    return sub is not None


# ─── MESSAGES ─────────────────────────────────────────────────────────────────

async def save_message(session: AsyncSession, user_id: int, role: str,
                        text: str, tutor: str = None, has_error: bool = False):
    msg = Message(
        user_id=user_id,
        role=role,
        text_content=text[:4000] if text else "",
        tutor=tutor,
        has_error=has_error
    )
    session.add(msg)
    await session.commit()


async def get_recent_messages(session: AsyncSession, user_id: int, limit: int = 10) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    msgs = result.scalars().all()
    return list(reversed(msgs))


# ─── ERRORS ───────────────────────────────────────────────────────────────────

async def record_error(session: AsyncSession, user_id: int,
                        error_type: str, error_detail: str):
    result = await session.execute(
        select(UserError).where(
            and_(UserError.user_id == user_id, UserError.error_detail == error_detail)
        )
    )
    err = result.scalar_one_or_none()
    if err:
        err.count += 1
        err.last_seen = datetime.utcnow()
    else:
        err = UserError(user_id=user_id, error_type=error_type, error_detail=error_detail)
        session.add(err)
    await session.commit()


async def get_top_errors(session: AsyncSession, user_id: int, limit: int = 3) -> list[UserError]:
    result = await session.execute(
        select(UserError)
        .where(UserError.user_id == user_id)
        .order_by(desc(UserError.count))
        .limit(limit)
    )
    return list(result.scalars().all())


# ─── PAYMENTS ─────────────────────────────────────────────────────────────────

async def create_payment(session: AsyncSession, user_id: int, yukassa_id: str,
                          amount: float, plan: str) -> Payment:
    payment = Payment(
        user_id=user_id,
        yukassa_id=yukassa_id,
        amount=amount,
        plan=plan,
        status="pending"
    )
    session.add(payment)
    await session.commit()
    return payment


async def update_payment_status(session: AsyncSession, yukassa_id: str, status: str):
    await session.execute(
        update(Payment).where(Payment.yukassa_id == yukassa_id).values(status=status)
    )
    await session.commit()
