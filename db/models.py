from datetime import datetime, date
from sqlalchemy import (
    BigInteger, String, Integer, SmallInteger, Boolean,
    DateTime, Date, Text, Numeric, ForeignKey, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user_id
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    fluency_score: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[date | None] = mapped_column(Date)
    selected_tutor: Mapped[str] = mapped_column(String(10), default="john")
    current_topic: Mapped[str | None] = mapped_column(String(100))
    violation_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    free_messages_used: Mapped[int] = mapped_column(Integer, default=0)
    trial_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    message_count_today: Mapped[int] = mapped_column(Integer, default=0)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    language_code: Mapped[str | None] = mapped_column(String(10))

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")
    messages: Mapped[list["Message"]] = relationship(back_populates="user")
    errors: Mapped[list["UserError"]] = relationship(back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    plan: Mapped[str] = mapped_column(String(20))  # 'month' | 'year' | 'family'
    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    payment_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="active")
    family_slot: Mapped[int] = mapped_column(SmallInteger, default=1)
    linked_user_id: Mapped[int | None] = mapped_column(BigInteger)  # for family plan

    user: Mapped["User"] = relationship(back_populates="subscriptions")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    session_date: Mapped[date] = mapped_column(Date, default=func.current_date())
    role: Mapped[str] = mapped_column(String(10))  # 'user' | 'assistant'
    text_content: Mapped[str | None] = mapped_column(Text)
    tutor: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    has_error: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="messages")


class UserError(Base):
    __tablename__ = "user_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    error_type: Mapped[str] = mapped_column(String(50))  # 'grammar' | 'phonetic' | 'vocabulary'
    error_detail: Mapped[str] = mapped_column(String(255))
    count: Mapped[int] = mapped_column(Integer, default=1)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship(back_populates="errors")


class ModerationBlock(Base):
    __tablename__ = "moderation_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True)
    blocked_until: Mapped[datetime] = mapped_column(DateTime)
    reason: Mapped[str] = mapped_column(String(64), default="policy_violation")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    yukassa_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    status: Mapped[str] = mapped_column(String(20))
    plan: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
