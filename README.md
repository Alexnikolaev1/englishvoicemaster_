# 🎤 EnglishVoiceMaster

> AI-powered English speaking coach for Telegram  
> **Yandex API · Python · aiogram 3.x · Vercel Serverless + Local Polling**

---

## 📁 Project Structure

```
englishvoicemaster/
│
├── api/                         ← Vercel serverless functions
│   ├── webhook.py               ← POST /api/webhook  (Telegram updates)
│   └── setup_webhook.py         ← GET  /api/setup_webhook  (register webhook)
│
├── core/
│   └── app_factory.py           ← Shared Bot + Dispatcher factory
│
├── bot/
│   ├── handlers/
│   │   ├── start.py             ← /start, menu, topics, progress
│   │   ├── voice.py             ← Voice pipeline (no ffmpeg needed)
│   │   ├── payment.py           ← YuKassa subscription flow
│   │   └── admin.py             ← Admin commands
│   ├── keyboards/main_menu.py   ← All inline keyboards
│   ├── middlewares/
│   │   ├── db_middleware.py     ← Auto DB session per request
│   │   └── throttle_middleware.py
│   └── filters/subscription.py
│
├── services/
│   ├── yandex_gpt.py            ← YandexGPT API (John & Mary prompts)
│   ├── speechkit.py             ← ASR + TTS (no ffmpeg — raw OGG)
│   ├── yukassa.py               ← YuKassa payment API
│   ├── censor.py                ← Content moderation
│   └── fluency.py               ← Gamification / Fluency Bar
│
├── db/
│   ├── models.py                ← SQLAlchemy ORM (5 tables)
│   ├── session.py               ← NullPool for serverless / pool for local
│   └── crud.py                  ← All DB operations
│
├── prompts/
│   ├── john_system.txt          ← John's full system prompt
│   └── mary_system.txt          ← Mary's full system prompt
│
├── utils/notifications.py       ← Scheduled decay reminders (local only)
├── config.py                    ← Unified config (Vercel-aware)
│
├── local_run.py                 ← ▶ LOCAL development runner (polling)
├── vercel.json                  ← ▶ Vercel deployment config
├── requirements.txt
├── docker-compose.yml           ← Local PostgreSQL + Redis
└── .env.example                 ← Environment variable template
```

---

## 🚀 Deployment: Vercel (Production)

### Prerequisites
- Vercel account at [vercel.com](https://vercel.com)
- Neon PostgreSQL at [neon.tech](https://neon.tech) (free tier works)
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Yandex Cloud account for GPT + SpeechKit

### Step 1 — Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy (from project root)
vercel --prod
```

### Step 2 — Set Environment Variables

In Vercel Dashboard → Project → Settings → Environment Variables, add:

| Variable | Value | Required |
|----------|-------|----------|
| `BOT_TOKEN` | `123456:ABC...` | ✅ |
| `YANDEX_API_KEY` | `AQVN...` | ✅ |
| `YANDEX_FOLDER_ID` | `b1g...` | ✅ |
| `SPEECHKIT_API_KEY` | same as `YANDEX_API_KEY` | ✅ |
| `DATABASE_URL` | `postgresql+asyncpg://...neon.tech/evm?sslmode=require` | ✅ |
| `WEBHOOK_SECRET` | any random 32-char string | ✅ |
| `DEPLOY_MODE` | `vercel` | ✅ |
| `YUKASSA_SHOP_ID` | your shop id | optional |
| `YUKASSA_SECRET_KEY` | your secret | optional |
| `ADMIN_IDS` | `123456789` | optional |

> ⚠️ **Vercel auto-sets `VERCEL_URL`** — no need to set `WEBHOOK_URL` manually.

### Step 3 — Register Webhook

After deploy, call the setup endpoint **once**:

```bash
curl "https://your-app.vercel.app/api/setup_webhook?token=YOUR_WEBHOOK_SECRET"
```

Expected response:
```json
{
  "ok": true,
  "bot": "@YourBotUsername",
  "webhook_url": "https://your-app.vercel.app/api/webhook",
  "pending_updates": 0
}
```

### Step 4 — Verify

Open Telegram, find your bot, send `/start`. Done! 🎉

---

## 💻 Local Development (Polling)

No webhook, no HTTPS needed. Perfect for testing and development.

### Step 1 — Setup

```bash
# Clone / navigate to project
cd englishvoicemaster

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment
cp .env.example .env
# → Fill in at minimum: BOT_TOKEN, DATABASE_URL
#   (for docker-compose in this repo use port 55432)
```

### Step 2 — Start PostgreSQL

```bash
# Option A: Docker (recommended)
docker compose up -d postgres

# Option B: Local PostgreSQL
createdb englishvoicemaster
```

### Step 3 — Run

```bash
python local_run.py
```

Output:
```
============================================================
🚀  EnglishVoiceMaster — LOCAL MODE
============================================================
✅  Database ready
✅  Webhook cleared (polling mode)
✅  Bot: @YourBot (id=123456789)
✅  Trial: 3 days / 20 messages
🎤  Ready! Open Telegram and send /start
============================================================
```

### Step 4 — Test

Send `/start` to your bot in Telegram. All features work locally:
- 🎙️ Voice messages (requires `SPEECHKIT_API_KEY`)
- 🤖 GPT responses (requires `YANDEX_API_KEY`)
- 💳 Payments (mock mode without `YUKASSA_SHOP_ID`)
- 📊 Fluency Bar — works fully offline

---

## 🗄️ Database: Neon (Vercel) vs Local

| | Vercel (Neon) | Local |
|--|---------------|-------|
| Provider | [neon.tech](https://neon.tech) (free) | Docker / local PG |
| Connection | `NullPool` (serverless-safe) | Connection pool |
| SSL | Required (`?sslmode=require`) | Not required |
| Auto-scale | Yes | No |
| Cost | Free tier: 0.5GB | Free |

**Neon connection string format:**
```
postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require
```

---

## 🔑 Getting API Keys

### Telegram Bot Token
1. Open [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow instructions → copy the token

### Yandex Cloud (GPT + SpeechKit)
1. Register at [console.cloud.yandex.ru](https://console.cloud.yandex.ru)
2. Create a folder → note the **Folder ID**
3. IAM → Service Accounts → Create account → assign roles:
   - `ai.languageModels.user` (for YandexGPT)
   - `ai.speechkit.stt` (for speech recognition)  
   - `ai.speechkit.tts` (for speech synthesis)
4. Create API Key for the service account → copy the key

### Neon PostgreSQL (for Vercel)
1. Register at [neon.tech](https://neon.tech)
2. Create project → create database `englishvoicemaster`
3. Connection → copy the **asyncpg** connection string
4. Add `?sslmode=require` at the end

### YuKassa (Payments)
1. Register at [yookassa.ru](https://yookassa.ru)
2. Settings → API Keys → create secret key
3. Note your **Shop ID**

---

## ⚡ Voice Pipeline

```
User sends voice (OGG/OPUS)
        ↓
   Download bytes (no disk write)
        ↓
   Yandex SpeechKit STT
   (accepts OGG natively — no ffmpeg!)
        ↓
   Content filter (regex censor)
        ↓
   YandexGPT → John or Mary responds
   (with error profile adaptation)
        ↓
   Yandex SpeechKit TTS → OGG bytes
        ↓
   Send voice message back
        ↓
   Update Fluency Bar + save to DB
```

---

## 🎮 Bot Commands

| Command | Who | Description |
|---------|-----|-------------|
| `/start` | Everyone | Onboarding & welcome |
| `/menu` | Everyone | Main menu |
| `/admin` | Admins | Stats dashboard |
| `/broadcast <text>` | Admins | Message all users |
| `/unblock <user_id>` | Admins | Unblock user |

---

## 📊 Fluency Bar Scoring

| Event | Points |
|-------|--------|
| Voice message sent | +5 |
| Daily streak bonus | +20 |
| Miss 1 day | −15 |
| Miss 2+ days | −15/day |
| Active subscription | ❄️ Freeze |

Levels: 🌱 A1 → 📚 A2 → 💬 B1 → 🗣️ B1+ → 🎯 B2 → ⭐ C1 → 🏆 C2

---

## 🔒 Content Safety

3-strike system:
1. Warning + redirect to neutral topic
2. Final warning + topic suggestion  
3. Session blocked (24h) → 5+ violations: permanent block

Admin can unblock: `/unblock <user_id>`

---

## ⚠️ Vercel Limitations

| Limitation | Impact | Solution |
|------------|--------|----------|
| No ffmpeg binary | Can't convert audio | Pass OGG directly to SpeechKit ✅ |
| Max 60s execution | Long GPT calls may timeout | YandexGPT timeout set to 30s |
| No background tasks | Notification scheduler won't run | Use Vercel Cron Jobs (see below) |
| No persistent filesystem | Can't write logs to disk | Use Vercel logging dashboard |
| Stateless between calls | Memory FSM resets | Acceptable for this use case |

### Vercel Cron Jobs (for notifications)
Add to `vercel.json`:
```json
{
  "crons": [{
    "path": "/api/send_reminders",
    "schedule": "0 9 * * *"
  }]
}
```
Then create `api/send_reminders.py` to trigger the notification logic.
