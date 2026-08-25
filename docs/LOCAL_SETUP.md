# CogniCare — Local End-to-End Setup (Telegram-Only Production)

The goal of this runbook is narrow and important: **get one real message to travel the whole pipeline once.** When it does, everything after it is ordinary feature work. Until it does, every "finished" phase is only theory.

---

## Channel: Telegram (Production + Recruiter Demo)

| Channel | Purpose | Access |
|---------|---------|--------|
| **Telegram Bot** | **Production elder channel + Recruiter demo** | **Public — anyone with `t.me` link** |

The agent pipeline is identical for both use cases. Only the elder-resolution key differs:
- **Demo elders**: auto-provisioned by `telegram_chat_id` (recruiter walk-up)
- **Production elders**: linked via deep-link `t.me/YourBot?start=elder_<uuid>` → `telegram_user_id`

---

## 0. Prerequisites

- **Docker Desktop** (gives you `docker compose`)
- A tunnel tool — **cloudflared** (no account) or **ngrok** (free account)
- Accounts (all free tier): **Supabase**, **Groq**, **Hugging Face**, **Telegram** (for demo)

---

## 1. Supabase: Database + Auth User

1. Create a project at supabase.com. Wait for provisioning.
2. **SQL Editor** → run migrations in order:
   - `backend/database/migrations/0002_cognicare_v2_schema.sql` (core V2 schema + RLS)
   - `backend/database/migrations/0003_add_telegram_chat_id.sql` (Telegram demo support)
   - `backend/database/migrations/0004_telegram_production.sql` (Telegram production support)
3. **Authentication → Users → Add user** → email + password → copy **UUID** (for `TELEGRAM_DEMO_CAREGIVER_ID` and elder seeding)
4. **Project Settings → API** → copy **Project URL** and **`service_role`** key (secret, not `anon`)

---

## 2. API Keys

| Service | Where | Key Format |
|---------|-------|------------|
| **Groq** | console.groq.com → API Keys | `gsk_...` |
| **Hugging Face** | huggingface.co → Settings → Access Tokens | `hf_...` (read) |
| **Telegram** | @BotFather → `/newbot` | `123456:ABC-DEF...` |

**Telegram Bot setup:**
1. Message `@BotFather` → `/newbot` → name it → get token
2. Note the **bot username** (without @) for `TELEGRAM_BOT_USERNAME`
3. No webhook needed yet — we'll register it after tunnel starts

---

## 3. Fill `.env`

```bash
cp .env.example .env
```

Edit `.env` with all keys from steps 1–2.

**Critical (crash on import if blank):**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

**Telegram (required for all channels):**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_URL` (will fill after tunnel)
- `TELEGRAM_WEBHOOK_SECRET` (random string)
- `TELEGRAM_DEMO_CAREGIVER_ID` (UUID from step 1.3)
- `TELEGRAM_VALIDATE_SECRET=true`
- `TELEGRAM_BOT_USERNAME` (your bot's username from @BotFather, without @)

**Celery/Redis:** Leave as-is (`redis://redis:6379/0`) — docker-compose overrides.

---

## 4. Boot the Stack

```bash
docker compose up --build -d
```

**Verify all 4 services:**

| Service | Signal |
|---------|--------|
| `redis` | `Ready to accept connections` |
| `api` | `Uvicorn running on http://0.0.0.0:8000` → open `http://localhost:8000/docs` |
| `worker` | `celery@... ready.` + queues: `scheduling, inbound, fallback, escalation, reports` |
| `beat` | `beat: Starting...` |

If `api`/`worker` exit immediately → check `.env` Supabase values.

---

## 5. Expose API + Register Telegram Webhook

**Terminal 2 — start tunnel:**
```bash
cloudflared tunnel --url http://localhost:8000
# Copy the https://... URL
```

**Update `.env`:**
```
TELEGRAM_WEBHOOK_URL=https://your-tunnel.trycloudflare.com/webhooks/telegram/inbound
```

**Restart API + worker to pick up new env:**
```bash
docker compose up -d --force-recreate api worker
```

**Register webhook:**
```bash
docker compose exec api python -c "
from backend.integrations.telegram_client import set_webhook
print(set_webhook())
"
# Expected: {'ok': True, 'result': True, 'description': 'Webhook was set'}
```

---

## 6. Test the Demo (Recruiter Walk-Up)

1. Open `https://t.me/YourBotUsername`
2. Tap **Start**
3. You receive:
   - Welcome message (demo mode)
   - First question (domain = `episodic_memory`)
4. Reply (text or voice note) → you get:
   - Warm companion acknowledgement
   - Next question (7-day rotation)
5. Dashboard shows interaction, insight, recommendation:
   ```bash
   curl http://localhost:8000/api/elders  # list demo elders
   curl http://localhost:8000/api/{elder_id}/recommendations
   ```

---

## 7. Test Production Onboarding (Caregiver → Elder)

**As caregiver (via API or dashboard):**
```bash
# Create a production elder (no WhatsApp number)
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

**Share the deep-link with the elder** (via WhatsApp/SMS/email).

**As elder:**
1. Tap the deep-link → opens Telegram bot with `/start elder_<uuid>`
2. Bot links your Telegram user_id to the elder profile
3. You receive: Production welcome + First question
4. Reply normally → full pipeline runs (companion reply + next question)

---

## 8. Scheduled Daily Questions (Beat)

The scheduler runs every 15 minutes and sends questions at each elder's `preferred_interaction_time` via Telegram.

**Trigger manually for testing:**
```bash
# Get elder ID
docker compose exec worker python -c "from backend.database.db import get_all_elders; print(get_all_elders())"

# Send question (runs in scheduling queue)
docker compose exec worker python -c "from backend.celery_app.tasks.scheduling import send_daily_question; send_daily_question.apply_async(args=['ELDER-ID'], queue='scheduling')"
```

---

## 9. Frontend (Caregiver Dashboard)

```bash
cd frontend
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
npm install && npm run dev
```

Open `http://localhost:3000` → Sign up with the same Supabase Auth email/password.

**Dashboard shows:**
- Elder list (yours only, via RLS)
- Daily interactions with insights
- Recommendations with Done/Dismiss/Suggest actions

---

## 10. Common Issues

| Symptom | Fix |
|---------|-----|
| `api`/`worker` crash on startup | `.env` missing `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` |
| Webhook registration fails | `TELEGRAM_WEBHOOK_URL` must be HTTPS and reachable; restart containers after editing `.env` |
| "Duplicate update" in logs | Normal — Telegram re-delivers if webhook >5s; idempotency handles it |
| No companion reply | Check `TELEGRAM_BOT_TOKEN` valid; worker logs show `send_telegram_message` result |
| Elder not found in pipeline | Run migration 0004; check `telegram_user_id` or `telegram_chat_id` on elder profile |

---

## 11. Architecture Notes (for Shubham)

- **No Twilio/WhatsApp code runs** — removed from `main.py`, `scheduling.py`, `telegram_bot.py`
- **Shared pipeline**: `backend/celery_app/tasks/shared_helpers.py` contains the core logic used by Telegram
- **Elder resolution**: `_resolve_elder()` in `telegram_bot.py` handles demo vs production
- **Deep-link format**: `https://t.me/<bot_username>?start=elder_<uuid>`
- **Idempotency**: `tg:<chat_id>:<message_id>` stored in `daily_interactions.twilio_message_sid`