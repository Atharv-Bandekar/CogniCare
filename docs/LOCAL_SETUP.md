# CogniCare — Local End-to-End Setup (Updated for V2 + Telegram Demo)

The goal of this runbook is narrow and important: **get one real message to travel the whole pipeline once.** When it does, everything after it is ordinary feature work. Until it does, every "finished" phase is only theory.

---

## Two Channels, One Pipeline

| Channel | Purpose | Access |
|---------|---------|--------|
| **WhatsApp (Twilio)** | Production elder channel | Pre-registered test numbers only, template-gated |
| **Telegram Bot** | **Recruiter demo channel** | **Public — anyone with `t.me` link** |

**The agent pipeline is identical.** Only the transport adapter and elder-resolution key differ.

---

## 0. Prerequisites

- **Docker Desktop** (gives you `docker compose`)
- A tunnel tool — **cloudflared** (no account) or **ngrok** (free account)
- Accounts (all free tier): **Supabase**, **Groq**, **Hugging Face**, **Twilio** (optional for local), **Telegram** (for demo)

---

## 1. Supabase: Database + Auth User

1. Create a project at supabase.com. Wait for provisioning.
2. **SQL Editor** → run both migrations in order:
   - `backend/database/migrations/0002_cognicare_v2_schema.sql` (core V2 schema + RLS)
   - `backend/database/migrations/0003_add_telegram_chat_id.sql` (Telegram demo support)
3. **Authentication → Users → Add user** → email + password → copy **UUID** (for `TELEGRAM_DEMO_CAREGIVER_ID` and elder seeding)
4. **Project Settings → API** → copy **Project URL** and **`service_role`** key (secret, not `anon`)

---

## 2. API Keys

| Service | Where | Key Format |
|---------|-------|------------|
| **Groq** | console.groq.com → API Keys | `gsk_...` |
| **Hugging Face** | huggingface.co → Settings → Access Tokens | `hf_...` (read) |
| **Twilio** | Console → Dashboard (optional for WhatsApp) | `AC...`, auth token |
| **Telegram** | @BotFather → `/newbot` | `123456:ABC-DEF...` |

**Twilio WhatsApp sandbox (optional):** Console → Messaging → Try it out → Send WhatsApp message → join code → send from your phone.

---

## 3. Fill `.env`

```bash
cp .env.example .env
```

Edit `.env` with all keys from steps 1–2.

**Critical (crash on import if blank):**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

**Telegram demo (required for recruiter-facing demo):**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_URL` (will fill after tunnel)
- `TELEGRAM_WEBHOOK_SECRET` (random string)
- `TELEGRAM_DEMO_CAREGIVER_ID` (UUID from step 1.3)
- `TELEGRAM_VALIDATE_SECRET=true`

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

## 6. Test the Demo (Telegram)

1. Open `https://t.me/YourBotUsername`
2. Tap **Start**
3. You receive:
   - Welcome message
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

## 7. (Optional) Test WhatsApp Production Path

**Seed an elder with your WhatsApp number:**
```sql
insert into public.elder_profiles
  (caregiver_user_id, name, whatsapp_number, preferred_language,
   preferred_interaction_time, proximity, cycle_day)
values
  ('YOUR-CAREGIVER-UUID', 'Test Elder', '+9198XXXXXXXX', 'en', '09:00', 'remote', 1);
```

**Trigger today's question:**
```bash
# Get elder ID
docker compose exec worker python -c "from backend.database.db import get_all_elders; print(get_all_elders())"

# Send question (runs in scheduling queue)
docker compose exec worker python -c "from backend.celery_app.tasks.scheduling import send_daily_question; send_daily_question.apply_async(args=['ELDER-ID'], queue='scheduling')"
```

**Reply on WhatsApp** → check `docker compose logs -f worker` for pipeline execution.

---

## Key Architectural Notes (for Shubham)

### What's Different from Phase 2 (V1)

| V1 (Phase 2) | V2 (Current) |
|--------------|--------------|
| Synchronous `POST /api/analyze` | Async Celery pipeline (`inbound` queue) |
| Frontend polls for questions | Celery Beat sends daily questions |
| `conversations`/`insights` tables | `daily_interactions`/`interaction_insights`/`memories`/`recommendations` |
| No scheduler | Celery Beat (daily, 12h fallback, weekly) |
| No Telegram | Telegram bot for zero-friction demo |
| No companion reply | `agents.companion` warm reply for Telegram |
| WhatsApp only | Dual channel (WhatsApp + Telegram) |

### Frontend Migration Needed (Phase 4A)

| Current Frontend Call | Target V2 Endpoint |
|----------------------|-------------------|
| `GET /api/question` | `GET /api/elders/{elder_id}/question` |
| `POST /api/transcribe` | Handled by webhook → Celery |
| `POST /api/analyze` | Handled by webhook → Celery |
| `GET /api/history` | `GET /api/{elder_id}/recommendations` |
| `POST /api/refresh-question` | Handled by Beat |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `api`/`worker` exit on boot | Fix `SUPABASE_URL`/`SERVICE_ROLE_KEY` in `.env`, `docker compose up -d --force-recreate api worker` |
| `TELEGRAM_BOT_TOKEN is not set` | `docker compose down && docker compose up --build -d` |
| `Warming up` reply | Run migration 0003 + set `TELEGRAM_DEMO_CAREGIVER_ID` |
| Webhook 400 "Failed to resolve host" | Tunnel URL expired → restart tunnel, update `.env`, re-register webhook |
| Worker `unknown_sender` (WhatsApp) | Store bare E.164 (`+9198...`), no `whatsapp:` prefix |
| Voice note → no reply | Check `docker compose logs worker` for Whisper errors |

---

## Production Deployment (Render)

See main `README.md` → [Production Deployment (Render)](#production-deployment-render).

Services: Web (Docker + honcho) + Free Redis via `render.yaml` Blueprint.

---

## What This Proves

When the Telegram demo works end-to-end, the **entire async pipeline** is verified:
- Webhook auth → queue → idempotency → transcript → evaluate → memory → recommendation → escalation → companion reply → next question

Phase 4 becomes normal feature building on a solid foundation.