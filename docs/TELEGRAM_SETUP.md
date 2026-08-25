# Telegram Bot Setup — Production + Recruiter Demo Channel

## Why Telegram?
Twilio's WhatsApp *trial* sender is template-only and requires pre-registered test numbers, so a stranger who finds the GitHub repo or the live deployment can't actually use the app. A Telegram bot is public by default — anyone with the `t.me/YourBotName` link taps **Start** and holds a live conversation, for free, with no verification. That makes it the channel a recruiter can genuinely try.

**Now also the production elder channel** — free, no template rules, voice notes supported.

---

## Two Modes, One Bot

| Mode | Trigger | Elder Resolution | Onboarding |
|------|---------|------------------|------------|
| **Demo (Recruiter)** | `/start` (no args) | Auto-provision by `telegram_chat_id` | None — walk-up |
| **Production (Elder)** | `/start elder_<uuid>` | Link by `telegram_user_id` | Caregiver shares deep-link |

---

## 1) Create the bot

1. Open Telegram and message **@BotFather**
2. `/newbot` → give it a name (`CogniCare`) and a username ending in `bot` (e.g. `CogniCareBot`)
3. BotFather replies with a token like `123456:ABC-DEF-your-token-here`
4. Copy the token **and the bot username** (without `@`)

---

## 2) Run the database migrations

In the **Supabase SQL editor** (or `psql`), run **all three** in order:

```sql
-- Migration 0002: Core V2 schema + RLS
\i backend/database/migrations/0002_cognicare_v2_schema.sql

-- Migration 0003: Telegram demo channel (chat_id)
\i backend/database/migrations/0003_add_telegram_chat_id.sql

-- Migration 0004: Telegram production (user_id + deep-link)
\i backend/database/migrations/0004_telegram_production.sql
```

---

## 3) Create the demo caregiver user

The `elder_profiles.caregiver_user_id` column is a `NOT NULL` FK to `auth.users`. Every auto-provisioned Telegram demo elder needs a valid caregiver UUID.

Easiest path:
1. In Supabase Dashboard → **Authentication** → **Users** → **Invite User**
2. Email: `demo-caregiver@cognicare.local` (or any dummy email)
3. After creation, copy the **User UUID** from the user row.
4. Paste it into `.env` as `TELEGRAM_DEMO_CAREGIVER_ID`.

---

## 4) Fill `.env`

Copy `.env.example` to `.env` and edit the Telegram section:

```bash
# Paste your BotFather token
TELEGRAM_BOT_TOKEN=123456:ABC-DEF-your-token-here

# Bot username (without @) for generating deep-links
TELEGRAM_BOT_USERNAME=CogniCareBot

# Your public HTTPS tunnel URL + the webhook route
TELEGRAM_WEBHOOK_URL=https://your-subdomain.trycloudflare.com/webhooks/telegram/inbound

# A random secret (Telegram echoes it back for validation)
TELEGRAM_WEBHOOK_SECRET=super-secret-random-string-here

# Keep true in production
TELEGRAM_VALIDATE_SECRET=true

# The caregiver UUID from step 3
TELEGRAM_DEMO_CAREGIVER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

## 5) Rebuild the Docker image

```bash
docker compose build
```

---

## 6) Start the stack + register the webhook

```bash
# 1) Bring everything up
docker compose up -d

# 2) Wait for the API healthcheck to pass (check `docker compose logs api`)

# 3) Register the webhook with Telegram (one-liner):
docker compose exec api python -c "
from backend.integrations.telegram_client import set_webhook
print(set_webhook())
"
# Expected: {'ok': True, 'result': True, 'description': 'Webhook was set'}
```

If the tunnel URL ever changes (cloudflared gives a new one on each restart), repeat step 6.3 — the same command updates the webhook.

---

## 7) Test it live

### Demo Mode (Recruiter Walk-Up)
1. Open `https://t.me/YourBotUsername`
2. Tap **Start**
3. You should receive:
   - The demo welcome message
   - The first daily-style question (domain = `episodic_memory`)
4. Reply with text or a voice note — you'll get:
   - A warm, personalised acknowledgement (from `agents.companion`)
   - A new question (next domain in the 7-day rotation)
5. The caregiver dashboard (`/api/elders/...`) now shows the interaction, insight, and a pending recommendation.

### Production Mode (Caregiver → Elder)

**As caregiver (via API):**
```bash
# Create a production elder
curl -X POST http://localhost:8000/api/elders/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "caregiver_user_id": "YOUR-CAREGIVER-UUID",
    "name": "Test Elder",
    "preferred_language": "en",
    "preferred_interaction_time": "09:00",
    "timezone": "Asia/Kolkata",
    "proximity": "remote"
  }'
# Returns: {"elder_id": "...", "deep_link": "https://t.me/YourBot?start=elder_<uuid>", "bot_username": "YourBot"}
```

**Share the `deep_link` with the elder** (via WhatsApp/SMS/email).

**As elder:**
1. Tap the deep-link → opens Telegram bot with `/start elder_<uuid>`
2. Bot links your Telegram `user_id` to the elder profile
3. You receive: Production welcome + First question
4. Reply normally → full pipeline runs (companion reply + next question)
5. Scheduled daily questions arrive at `preferred_interaction_time` via Celery Beat

---

## 8) Verify pipeline internals (optional)

```bash
# List all elders (demo + production)
curl http://localhost:8000/api/elders

# Get recommendations for a specific elder
curl http://localhost:8000/api/{elder_id}/recommendations

# Check worker logs for pipeline traces
docker compose logs -f worker
```

---

## 9) Common Issues

| Symptom | Fix |
|---------|-----|
| `api`/`worker` crash on startup | `.env` missing `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` |
| Webhook registration fails | `TELEGRAM_WEBHOOK_URL` must be HTTPS and reachable; restart containers after editing `.env` |
| "Duplicate update" in logs | Normal — Telegram re-delivers if webhook >5s; idempotency handles it |
| No companion reply | Check `TELEGRAM_BOT_TOKEN` valid; worker logs show `send_telegram_message` result |
| Elder not found in pipeline | Run migration 0004; check `telegram_user_id` (production) or `telegram_chat_id` (demo) on elder profile |
| Deep-link doesn't work | Verify `TELEGRAM_BOT_USERNAME` matches BotFather username exactly (no `@`) |

---

## Architecture Notes

- **No Twilio/WhatsApp code runs** — removed from `main.py`, `scheduling.py`, `telegram_bot.py`
- **Shared pipeline**: `backend/celery_app/tasks/shared_helpers.py` contains the core logic used by Telegram
- **Elder resolution**: `_resolve_elder()` in `telegram_bot.py` handles demo vs production
- **Deep-link format**: `https://t.me/<bot_username>?start=elder_<uuid>`
- **Idempotency**: `tg:<chat_id>:<message_id>` stored in `daily_interactions.twilio_message_sid`