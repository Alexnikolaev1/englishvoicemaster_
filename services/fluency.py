"""Fluency bar and gamification logic."""
from datetime import date, timedelta
from db.models import User

FLUENCY_LEVELS = [
    (0,   100,  "🌱 Beginner",       "A1"),
    (100, 250,  "📚 Elementary",     "A2"),
    (250, 450,  "💬 Pre-Intermediate","B1"),
    (450, 650,  "🗣️ Intermediate",   "B1+"),
    (650, 800,  "🎯 Upper-Intermediate","B2"),
    (800, 950,  "⭐ Advanced",        "C1"),
    (950, 1000, "🏆 Mastery",         "C2"),
]

POINTS_PER_MESSAGE = 5
POINTS_STREAK_BONUS = 20
POINTS_DECAY_PER_DAY = 15


def get_level_info(score: int) -> dict:
    for low, high, label, cefr in FLUENCY_LEVELS:
        if low <= score < high:
            progress = (score - low) / (high - low) * 100
            return {
                "label": label,
                "cefr": cefr,
                "score": score,
                "next_level": high,
                "progress_pct": int(progress),
                "bar": _make_bar(progress),
            }
    return {"label": "🏆 Mastery", "cefr": "C2", "score": score,
            "next_level": 1000, "progress_pct": 100, "bar": "██████████"}


def _make_bar(pct: float, length: int = 10) -> str:
    filled = int(pct / 100 * length)
    return "█" * filled + "░" * (length - filled)


def get_fluency_message(user: User, points_gained: int) -> str:
    info = get_level_info(user.fluency_score)
    streak_text = f"🔥 Streak: {user.streak_days} days" if user.streak_days > 0 else ""
    return (
        f"📊 *Fluency Bar*\n"
        f"`{info['bar']}` {info['progress_pct']}%\n"
        f"Level: {info['label']} ({info['cefr']})\n"
        f"Score: {info['score']}/1000\n"
        f"+{points_gained} pts this message\n"
        f"{streak_text}"
    )


def get_decay_warning(user: User) -> str | None:
    if user.last_active is None:
        return None
    days_missed = (date.today() - user.last_active).days
    if days_missed == 1:
        loss = POINTS_DECAY_PER_DAY
        return (
            f"⚠️ *Your Fluency Bar is at risk!*\n"
            f"You haven't practiced today. "
            f"You'll lose {loss} points by tomorrow!\n"
            f"Current score: {user.fluency_score} pts"
        )
    elif days_missed >= 2:
        # TZ rule: after 2+ skipped days decay is doubled per day.
        loss = POINTS_DECAY_PER_DAY * 2 * days_missed
        return (
            f"🚨 *Fluency Alert!*\n"
            f"You've been away for {days_missed} days.\n"
            f"Lost: -{loss} pts 😔\n"
            f"Current score: {user.fluency_score} pts\n\n"
            f"Subscribe to *freeze your progress* and stop the decay! ❄️"
        )
    return None
