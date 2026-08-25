# Telegram Bot Setup — Recruiter-Facing Demo Channel

## Why Telegram?
Twilio's WhatsApp *trial* sender is template-only and requires pre-registered test
numbers, so a stranger who finds the GitHub repo or the live deployment can't
actually use the app. A Telegram bot is public by default — anyone with the
`t.me/YourBotName` link taps **Start** and holds a live conversation, for free,
with no verification. That makes it the channel a recruiter can genuinely try.

---

## 1) Create the bot
1. Open Telegram and message **@BotFather**
2. `/newbot` → give it a name (`CogniCare Demo`) and a username ending in
   `bot` (e.g. `CogniCareDemoBot`)
3. BotFather replies with a token like `123456:ABC-DEF-your-token-here`
4. Copy it.

---

## 2) Run the database migration
In the **Supabase SQL editor** (or `psql`):

```sql
-- Migration 0003: Telegram demo channel
ALTER TABLE public.elder_profiles
  ADD COLUMN IF NOT EXISTS telegram_chat_id text;

CREATE UNIQUE INDEX IF NOT EXISTS elder_profiles_telegram_chat_id_key
  ON public.elder_profiles (telegram_chat_id)
  WHERE telegram_chat_id IS NOT NULL;
```

This adds `telegram_chat_id` (nullable) and a partial unique index so each
Telegram chat maps to exactly one elder. WhatsApp elders keep `telegram_chat_id`
`NULL`; Telegram demo elders keep a synthetic `whatsapp_number` of
`tg:<chat_id>` because the column is `NOT NULL UNIQUE`.

---

## 3) Create the demo caregiver user
The `elder_profiles.caregiver_user_id` column is a `NOT NULL` FK to
`auth.users`. Every auto-provisioned Telegram demo elder needs a valid caregiver
UUID.

Easiest path:
1. In Supabase Dashboard → **Authentication** → **Users** → **Invite User**
2. Email: `demo-caregiver@cognicare.local` (or any dummy email)
3. After creation, copy the **User UUID** from the user row.
4. Paste it into `.env` as `TELEGRAM_DEMO_CAREGIVER_ID`.

---

## 4) Fill `.env`
Copy `.env.example` to `.env` and edit the new Telegram section:

```bash
# Paste your BotFather token
TELEGRAM_BOT_TOKEN=123456:ABC-DEF-your-token-here

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

If the tunnel URL ever changes (cloudflared gives a new one on each restart),
repeat step 6.3 — the same command updates the webhook.

---

## 7) Test it live
1. Open `https://t.me/YourBotUsername` (or the short link BotFather gave you)
2. Tap **Start**
3. You should receive:
   - The welcome message
   - The first daily-style question (domain = `episodic_memory`)
4. Reply with text or a voice note — you'll get:
   - A warm, personalised acknowledgement (from `agents.companion`)
   - A new question (next domain in the 7-day rotation)
5. The caregiver dashboard (`/api/elders/...`) now shows the interaction,
   insight, and a pending recommendation.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `{"ok": false, "description": "Bad Request: chat not found"}` | Bot token wrong, or you're calling `sendMessage` to a chat the bot hasn't seen yet. The webhook must receive an update from the chat first. |
| `TELEGRAM_BOT_TOKEN is not set` in worker logs | `.env` not picked up → `docker compose down && docker compose up --build -d` |
| `No open interaction for elder` but you replied | The `/start` message already opened the first question; a *second* reply before the first question arrives won't match. Just send another message. |
| `Warming up` reply | `TELEGRAM_DEMO_CAREGIVER_ID` missing or migration 0003 not run. |
| Voice note → no reply | Whisper may have failed silently. Check `docker compose logs worker`. |

---

## Architecture recap (for the demo pitch)

| Component | WhatsApp (production) | Telegram (recruiter demo) |
|-----------|-----------------------|---------------------------|
| Entry point | Scheduled question (template) | `/start` or user message |
| Elder resolution | `whatsapp_number` (pre-registered) | `telegram_chat_id` (auto-provisioned) |
| Reply to elder | ❌ None (by design) | ✅ Warm companion agent |
| Conversation | 1 question/day | Unlimited turns |
| Voice notes | ✅ Whisper | ✅ Whisper (same `stt.transcribe_audio`) |
| Caregiver dashboard | ✅ Full | ✅ Identical data |
| Access | Pre-registered testers only | **Anyone with the t.me link** |

The **agent pipeline is exactly the same code** — only the transport adapter and
the elder-resolution key differ. This proves the architecture is
channel-agnostic.