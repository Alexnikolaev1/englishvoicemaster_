"""
EnglishVoiceMaster — unified configuration.
Works for both Vercel (webhook) and local (polling) modes.
"""
import logging
import os
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class Config:
    # ── Telegram ────────────────────────────────────────────────────────
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # ── Yandex Cloud ────────────────────────────────────────────────────
    YANDEX_API_KEY: str = os.getenv("YANDEX_API_KEY", "")
    YANDEX_FOLDER_ID: str = os.getenv("YANDEX_FOLDER_ID", "")
    SPEECHKIT_API_KEY: str = os.getenv("SPEECHKIT_API_KEY", "")

    # ── Database ─────────────────────────────────────────────────────────
    # For Vercel: use Neon (postgresql+asyncpg://...) or Supabase
    # For local: postgresql+asyncpg://postgres:postgres@localhost:5432/evm
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/englishvoicemaster"
    )

    # ── YuKassa ──────────────────────────────────────────────────────────
    YUKASSA_SHOP_ID: str = os.getenv("YUKASSA_SHOP_ID", "")
    YUKASSA_SECRET_KEY: str = os.getenv("YUKASSA_SECRET_KEY", "")

    # ── Bot settings ─────────────────────────────────────────────────────
    FREE_TRIAL_DAYS: int = int(os.getenv("FREE_TRIAL_DAYS", "3"))
    FREE_TRIAL_MESSAGES: int = int(os.getenv("FREE_TRIAL_MESSAGES", "20"))
    PRICE_MONTH_RUB: int = 599
    PRICE_YEAR_RUB: int = 4990
    PRICE_FAMILY_RUB: int = 899

    # ── Deployment ───────────────────────────────────────────────────────
    # VERCEL_URL is auto-set by Vercel on deploy (e.g. "your-app.vercel.app")
    # WEBHOOK_URL overrides it if set manually
    VERCEL_URL: str = os.getenv("VERCEL_URL", "")        # auto-injected by Vercel
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")       # manual override
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "evm_secret_token_change_me")

    # ── Admin ─────────────────────────────────────────────────────────────
    ADMIN_IDS: list = field(default_factory=list)

    # ── Runtime mode ─────────────────────────────────────────────────────
    # Detected automatically: "vercel" | "local"
    MODE: str = os.getenv("DEPLOY_MODE", "local")

    def __post_init__(self):
        raw = os.getenv("ADMIN_IDS", "")
        parsed_admin_ids: list[int] = []
        if raw:
            for value in raw.split(","):
                candidate = value.strip()
                if not candidate:
                    continue
                try:
                    parsed_admin_ids.append(int(candidate))
                except ValueError:
                    logger.warning("Ignoring invalid ADMIN_IDS value: %s", candidate)
        self.ADMIN_IDS = parsed_admin_ids
        # Accept both "b1g..." and "ID=b1g..." formats from UI copy/paste.
        if self.YANDEX_FOLDER_ID.startswith("ID="):
            self.YANDEX_FOLDER_ID = self.YANDEX_FOLDER_ID.split("=", 1)[1].strip()
        # Vercel Storage often provides sync URL (postgresql://...).
        # We use async SQLAlchemy engine, so normalize to asyncpg DSN.
        if self.DATABASE_URL.startswith("postgresql://"):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        elif self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgres://", "postgresql+asyncpg://", 1
            )
        self.DATABASE_URL = self._normalize_asyncpg_ssl_query(self.DATABASE_URL)

    @staticmethod
    def _normalize_asyncpg_ssl_query(database_url: str) -> str:
        """
        asyncpg does not accept 'sslmode' kwarg, only 'ssl'.
        Convert common Postgres DSN query param sslmode=require -> ssl=true.
        """
        if "postgresql+asyncpg://" not in database_url or "sslmode=" not in database_url:
            return database_url

        parts = urlsplit(database_url)
        query_items = parse_qsl(parts.query, keep_blank_values=True)
        normalized_query: list[tuple[str, str]] = []
        ssl_already_set = any(k == "ssl" for k, _ in query_items)

        for key, value in query_items:
            if key != "sslmode":
                normalized_query.append((key, value))
                continue

            if ssl_already_set:
                continue

            # asyncpg expects ssl as mode-like value
            # (disable|allow|prefer|require|verify-ca|verify-full).
            if value in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
                normalized_query.append(("ssl", value))
            else:
                normalized_query.append(("ssl", "require"))

        rebuilt_query = urlencode(normalized_query)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, rebuilt_query, parts.fragment))

    @property
    def effective_webhook_base(self) -> str:
        """Return the best available base URL for webhook."""
        if self.WEBHOOK_URL:
            return self.WEBHOOK_URL.rstrip("/")
        if self.VERCEL_URL:
            return f"https://{self.VERCEL_URL}"
        return ""

    @property
    def is_vercel(self) -> bool:
        return self.MODE == "vercel" or bool(self.VERCEL_URL)

    @property
    def webhook_path(self) -> str:
        return f"/api/webhook"

    @property
    def full_webhook_url(self) -> str:
        base = self.effective_webhook_base
        return f"{base}{self.webhook_path}" if base else ""


config = Config()
