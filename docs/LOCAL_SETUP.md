# CogniCare — Local End-to-End Setup

The goal of this runbook is narrow and important: **get one real WhatsApp message
to travel the whole pipeline once.** When it does, everything after it is ordinary
feature work. Until it does, every "finished" phase is only theory.

The path a message travels:

```
You (WhatsApp)
   → Twilio  → [public tunnel] → FastAPI  /webhooks/twilio/inbound
   → Redis (queue)  → Celery worker
        → Groq (understand + reply)   → Supabase (store)   → Hugging Face (embed)
   → Twilio  → You (WhatsApp reply)
```

Four processes run together: **Redis**, the **API**, the **Celery worker**, and
**Celery beat**. `docker compose` starts all four. Twilio lives on the public
internet, so a **tunnel** bridges it to your laptop.

---

## 0. Prerequisites

- **Docker Desktop** (gives you `docker compose`).
- A tunnel tool — **cloudflared** (no account needed) or **ngrok** (free account).
- Accounts, all free tier: **Supabase**, **Groq**, **Hugging Face**, **Twilio**.

---

## 1. Supabase: database + one auth user

1. Create a project at supabase.com. Wait for it to finish provisioning.
2. Open **SQL Editor**, paste the entire contents of
   `backend/database/migrations/0002_cognicare_v2_schema.sql`, and run it. This
   creates all seven tables, enables `pgvector`, and defines the `match_memories`
   similarity function in one shot.
   - If it complains about `uuid_generate_v4()`, run `create extension if not
     exists "uuid-ossp";` first, then re-run the migration. (Most Supabase
     projects have it pre-enabled.)
3. Create one caregiver login so you have a real user id to attach an elder to:
   **Authentication → Users → Add user** (email + password). Click the new user
   and copy its **UUID** — you'll need it in step 6.
4. **Project Settings → API** — copy the **Project URL** and the
   **`service_role`** key (the secret one, *not* `anon`). The backend uses the
   service role key, which bypasses RLS, so row-level policies won't block it.

---

## 2. API keys

- **Groq:** console.groq.com → API Keys → create one (`gsk_...`).
- **Hugging Face:** huggingface.co → Settings → Access Tokens → create a `read`
  token (`hf_...`).
- **Twilio WhatsApp sandbox:** Console → Messaging → **Try it out → Send a
  WhatsApp message**. You'll see a sandbox number (e.g. `+1 415 523 8886`) and a
  join code like `join <two-words>`. **From your own phone, send that join
  message to the sandbox number.** You must do this or Twilio will refuse to
  deliver messages to you. Note your Account SID and Auth Token from the console
  dashboard.

---

## 3. Fill in `.env`

```bash
cp .env.example .env
```

Open `.env` and set every value from steps 1–2. Leave `CELERY_BROKER_URL` /
`CELERY_RESULT_BACKEND` as-is — compose overrides them to the `redis` service.
Leave `TWILIO_WEBHOOK_URL` for now; you'll fill it in step 5 once the tunnel is up.

> **Why this matters:** the backend builds its Supabase client *at import time*.
> A blank `SUPABASE_URL` or key doesn't fail later — it crashes the API and the
> worker the instant they start. Fill those two in before booting.

---

## 4. Boot the stack

```bash
docker compose up --build
```

Watch for these four "it's alive" signals, one per service:

| Service | You should see |
|---------|----------------|
| `redis` | `Ready to accept connections` |
| `api`   | `Uvicorn running on http://0.0.0.0:8000` — then open http://localhost:8000/docs and confirm the routes load |
| `worker`| `celery@... ready.` and a queue list showing `scheduling, inbound, fallback, escalation, reports` |
| `beat`  | `beat: Starting...` |

If the `api` or `worker` container exits immediately, it's almost always a blank
or wrong Supabase value (see the import-time note above). Read the last ~20 log
lines: `docker compose logs api`.

---

## 5. Expose the API to Twilio

In a **second terminal**, start a tunnel to port 8000:

```bash
# cloudflared (no account):
cloudflared tunnel --url http://localhost:8000

# — or — ngrok:
ngrok http 8000
```

Copy the public `https://...` URL it prints. Then:

1. Put the full inbound URL in `.env`:
   `TWILIO_WEBHOOK_URL=https://<your-tunnel>/webhooks/twilio/inbound`
   and restart just the API and worker so they pick it up:
   `docker compose up -d --force-recreate api worker`
2. In the **Twilio sandbox settings** ("Sandbox Configuration"), set
   **"When a message comes in"** to the same URL:
   `https://<your-tunnel>/webhooks/twilio/inbound` (method **POST**).

> **Why the URL must match exactly:** Twilio signs each request using the URL it
> posted to. The webhook recomputes that signature against `TWILIO_WEBHOOK_URL`.
> If the two differ by even a trailing slash, every request is rejected with 403.
> (For a quick smoke test without a tunnel you can set
> `TWILIO_VALIDATE_SIGNATURE=false`, but turn it back on — it's your only defense
> against forged elder messages.)

---

## 6. Seed one elder

In the Supabase SQL Editor, insert an elder whose `whatsapp_number` is **your own
phone in bare E.164** — the number you joined the sandbox with, **without** the
`whatsapp:` prefix and with no spaces:

```sql
insert into public.elder_profiles
  (caregiver_user_id, name, whatsapp_number, preferred_language,
   preferred_interaction_time, proximity, cycle_day)
values
  ('PASTE-THE-AUTH-USER-UUID-FROM-STEP-1',  -- caregiver_user_id
   'Test Elder',
   '+9198XXXXXXXX',                          -- YOUR phone, E.164, no 'whatsapp:' prefix
   'en',
   '09:00',
   'remote',
   1);
```

> **Why bare E.164:** Twilio sends `From` as `whatsapp:+9198...`; the worker strips
> the `whatsapp:` prefix and matches the remainder against `whatsapp_number`. If you
> store the number *with* the prefix or with spaces, the lookup misses and the worker
> logs `unknown_sender` — no reply, no error.

---

## 7. The end-to-end test

The inbound pipeline only answers a reply that belongs to a question it asked. So
first **make the app ask you a question**, then reply to it.

**7a — Trigger today's question** (enqueues the real send task the beat would
normally fire on a timer). Grab your elder's id first, then send it:

```bash
# get the elder id
docker compose exec worker python -c "from backend.database.db import get_all_elders; print(get_all_elders())"

# send today's question to that elder
docker compose exec worker python -c "from backend.celery_app.tasks.scheduling import send_daily_question; send_daily_question.apply_async(args=['PASTE-ELDER-ID'], queue='scheduling')"
```

✅ **Checkpoint 1 — outbound works:** within a second or two you receive a
question on WhatsApp. This alone proves Groq (question generation), Supabase (an
`daily_interactions` row was opened), and Twilio outbound. Watch it happen live:
`docker compose logs -f worker`.

> Debugging tip: swap `.apply_async(args=[id], queue='scheduling')` for
> `.apply(args=[id]).get()` to run it synchronously and see the return value or
> the full traceback right in your terminal.

**7b — Reply on WhatsApp.** Just answer the question naturally.

✅ **Checkpoint 2 — inbound auth works:** `docker compose logs -f api` shows a
`POST /webhooks/twilio/inbound` returning **200** (not 403). A 403 means the
signature URL doesn't match step 5.

✅ **Checkpoint 3 — the pipeline runs:** `docker compose logs -f worker` shows the
`process_inbound_message` task running through its steps without an exception.

✅ **Checkpoint 4 — the loop closes:** you receive an AI-generated reply on
WhatsApp. **This is the finish line.** It proves the entire chain: signature
validation → queue → transcript → attach-to-interaction → evaluate → generate
reply → store insight → embed to memory → outbound.

When checkpoint 4 lands once, the system genuinely works, and Phase 4 becomes
normal feature building.

---

## Troubleshooting — the failure modes worth knowing

| Symptom | Cause | Fix |
|---|---|---|
| `api`/`worker` container exits on boot | blank/typo'd `SUPABASE_URL` or service key — client is built at import | fix `.env`, `docker compose up -d --force-recreate api worker` |
| Question never arrives (7a) | wrong Twilio creds, or you never sent the `join` code from your phone | re-join the sandbox; verify SID/token; run 7a with `.apply().get()` to see the error |
| Worker logs `unknown_sender` | `whatsapp_number` stored with `whatsapp:` prefix or spaces | store bare E.164, e.g. `+9198XXXXXXXX` |
| Worker logs `no_open_interaction` | you replied before the app asked a question | run 7a first, then reply |
| Inbound webhook returns 403 | `TWILIO_WEBHOOK_URL` ≠ the URL set in the Twilio console | make them byte-identical; recreate api/worker |
| Scheduled tasks never fire | worker not listening on all queues | it must run with `-Q scheduling,inbound,fallback,escalation,reports` (compose already does this) |
| Voice note gets "couldn't understand" reply | Groq Whisper couldn't transcribe | fine for a first test — send text instead |

---

## What this setup does *not* prove

This gets one message through the happy path. It does **not** exercise: the
weekly report job end to end, the 12-hour stale-recommendation sweep, caregiver
escalation delivery (needs `personal_context.caregiver_whatsapp` — there's no
caregiver phone column in the schema yet), multi-language replies, or load. Those
are worth their own passes, but none of them block the core loop.
