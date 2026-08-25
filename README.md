# CogniCare AI 🧠

**Full-Stack Multi-Agent Cognitive Wellness Platform for Elders**

CogniCare AI is an AI-driven cognitive engagement companion for elderly users, built as an MVP for the **AICTE | IBM SkillsBuild AI Automation & Intelligent Solutions Internship (BharatCares)**, addressing **UN SDG 3: Good Health & Well-being**.

Originally a local desktop application, the system has been re-architected into a scalable, secure, full-stack web application with an **async Celery pipeline**. It engages elders with daily memory-prompting questions (via **Telegram**), analyzes spoken/typed responses for emotional/cognitive signals, extracts long-term memories (RAG), and recommends personalized offline activities — while giving caregivers secure, authenticated visibility into historical trends via a Next.js dashboard.

---

## Table of Contents
- [Tech Stack](#tech-stack)
- [Architecture Overview](#architecture-overview)
- [Database Schema (V2)](#database-schema-v2)
- [Channels: Telegram (Demo) vs WhatsApp (Production)](#channels-telegram-demo-vs-whatsapp-production)
- [Installation & Setup](#installation--setup)
- [Local Development (Docker)](#local-development-docker)
- [Production Deployment (Render)](#production-deployment-render)
- [Environment Variables](#environment-variables)
- [Developer Roadmap](#developer-roadmap)
- [Phase Status](#phase-status)
- [Team](#team)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14 (App Router), React 18, Tailwind CSS, TypeScript |
| **Backend API** | FastAPI, Python 3.11, Uvicorn |
| **Async Pipeline** | Celery 5.3 + Redis (Upstash/Render), Celery Beat scheduler |
| **Database & Auth** | Supabase (PostgreSQL + `pgvector`), Row Level Security |
| **LLM (Cloud)** | Groq (`openai/gpt-oss-20b`, `whisper-large-v3-turbo`) |
| **Embeddings** | Hugging Face Inference Router (`sentence-transformers/all-MiniLM-L6-v2`, 384-dim) |
| **Messaging** | Twilio WhatsApp (elder channel), Telegram Bot API (recruiter demo) |
| **Observability** | Structured logging, Render logs |

---

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Elder      │────▶│  Telegram    │────▶│  FastAPI Webhook│
│  (Telegram) │     │  Bot API     │     │  /webhooks/     │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                            ┌──────────────────────┘
                            ▼
                     ┌──────────────┐     ┌─────────────────┐
                     │  Redis       │◀───▶│  Celery Worker  │
                     │  (Broker)    │     │  (5 queues)     │
                     └──────────────┘     └────────┬────────┘
                                                   │
         ┌─────────────────────────────────────────┼─────────────────────────────────────────┐
         ▼                                         ▼                                         ▼
┌──────────────────┐                    ┌──────────────────┐                    ┌──────────────────┐
│ scheduling queue │                    │   inbound queue  │                    │ fallback queue   │
│ dispatch_daily_  │                    │ process_inbound_ │                    │ expire_stale_    │
│ questions        │                    │ message          │                    │ recommendations  │
└──────────────────┘                    └────────┬─────────┘                    └──────────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    ▼                            ▼                            ▼
           ┌───────────────┐            ┌───────────────┐            ┌───────────────┐
           │ Interviewer   │            │  Evaluator    │            │ Coordinator   │
           │ Agent         │            │  (Phase 3A)   │            │ Agent         │
           │ generate_     │            │ evaluate_     │            │ generate_     │
           │ question()    │            │ response()    │            │ recommendation()│
           └───────┬───────┘            └───────┬───────┘            └───────┬───────┘
                   │                            │                            │
                   │              ┌─────────────┴─────────────┐              │
                   │              ▼                           ▼              │
                   │     ┌───────────────┐            ┌───────────────┐      │
                   │     │ RAG Memory    │            │ Escalation    │      │
                   │     │ Extraction &  │            │ Check         │      │
                   │     │ Storage       │            │ (safety/      │      │
                   │     │ (pgvector)    │            │ engagement)   │      │
                   │     └───────────────┘            └───────────────┘      │
                   │                            │                            │
                   └────────────────────────────┼────────────────────────────┘
                                                ▼
                                    ┌─────────────────────┐
                                    │ Supabase (Postgres) │
                                    │ + pgvector          │
                                    └─────────────────────┘
```

**Key flows:**

1. **Daily Question (scheduled):** Celery Beat → `dispatch_daily_questions` → `send_daily_question` (per elder) → Twilio template message → `daily_interactions` row opened
2. **Inbound Reply (async):** Twilio webhook → enqueue `process_inbound_message` (idempotent on `MessageSid`) → transcribe (Whisper) → translate → evaluate → store insight → extract memories → generate recommendation → escalation check → advance `cycle_day`
3. **Fallback Sweep (12h):** `expire_stale_recommendations` → pending → `timed_out`
4. **Weekly Report (Mon 07:00):** `generate_all_weekly_reports` → 7-day aggregates → `weekly_reports` table
5. **Telegram Demo (on-demand):** `/webhooks/telegram/inbound` → enqueue `process_telegram_update` → same agent pipeline → warm companion reply → next question

---

## Database Schema (V2)

Managed via SQL migrations in `backend/database/migrations/`:

| Migration | Description |
|-----------|-------------|
| `0001_initial_schema.sql` | Legacy (ignored) |
| `0002_cognicare_v2_schema.sql` | Core V2 tables + RLS policies |
| `0003_add_telegram_chat_id.sql` | Telegram demo elder support (chat_id) |
| `0004_telegram_production.sql` | Telegram production elder support (user_id + deep-link) |

**Core tables:**

| Table | Purpose |
|-------|---------|
| `elder_profiles` | Elder config: name, language, timezone, proximity, mobility, `cycle_day` (1-7), `telegram_chat_id` (nullable, unique, demo), `telegram_user_id` (nullable, unique, production), `onboarding_method` ('demo' \| 'production') |
| `daily_interactions` | One row per scheduled question: `elder_id`, `domain`, `question`, `raw_response`, `transcript_source`, `language`, `twilio_message_sid` (idempotency key, reused for `tg:<chat>:<msg>`) |
| `interaction_insights` | Evaluator output: `sentiment_label`, `sentiment_score`, `engagement_level`, `engagement_score`, `response_depth`, `topics[]`, `safety_flag` |
| `memories` | `pgvector` (384-dim) long-term memories: `elder_id`, `content`, `embedding`, `source_interaction_id`, `tags[]` |
| `recommendations` | Coordinator output for caregiver dashboard: `recommendation_text`, `reason`, `status` (pending/done/dismissed/timed_out) |
| `family_interactions` | Caregiver feedback loop: `reaction` (done/dismiss), `caregiver_suggestion` |
| `weekly_reports` | 7-day aggregates: `period_start`, `period_end`, `avg_engagement`, `dominant_sentiment`, `topic_frequency`, `total_interactions`, `markdown_summary` |

**RLS:** Enabled on all tables. Policies enforce `caregiver_user_id` = `auth.uid()` for caregiver-scoped access. Elder profiles are inserted by caregivers; interactions are inserted by the service role (webhook/worker).

---

## Channels: Telegram (Production + Demo)

| Aspect | Telegram Bot (Production Elder) | Telegram Bot (Recruiter Demo) |
|--------|--------------------------------|-------------------------------|
| **Access** | Deep-link `t.me/YourBot?start=elder_<uuid>` | Public `t.me/YourBot` |
| **Elder onboarding** | Caregiver creates elder → shares deep-link | Auto-provisioned on first `/start` |
| **Elder identity** | `telegram_user_id` (from `message.from.id`) | `telegram_chat_id` (from `message.chat.id`) |
| **`onboarding_method`** | `production` | `demo` |
| **Messaging** | Freeform, bidirectional, companion replies | Freeform, bidirectional, companion replies |
| **Cost** | **Free** (Bot API) | **Free** (Bot API) |
| **Template rules** | **None** | **None** |
| **Voice notes** | ✅ Supported (Whisper) | ✅ Supported (Whisper) |
| **Scheduled questions** | ✅ Celery Beat at `preferred_interaction_time` | ❌ Not scheduled (on-demand only) |e/YourBot` — anyone can start | Pre-registered test numbers only (Twilio trial) |
| **Auth** | Auto-provisions demo elder keyed by `chat_id` | Elder profiles created by caregiver onboarding |
| **Messaging** | Freeform, bidirectional | Template-only (Twilio trial sender `+17372212163`) |
| **Template** | N/A | `TWILIO_TEMPLATE_CONTENT_SID=HXfe5ab5f00277942d4d4200328b4d403c` (Appointment Reminders) |
| **Pipeline** | Same agents (Interviewer→Evaluator→Coordinator→Companion) | Same agents, no companion reply (elder gets no ack) |
| **Use case** | Recruiter walks up, taps "Start", holds live conversation | Elder receives daily question, replies; caregiver sees dashboard |

**Why both?** Twilio's trial sender is template-gated even in-session (error 21654). A recruiter can't use WhatsApp without pre-registration. Telegram is zero-friction for demos.

---

## Installation & Setup

### Prerequisites
- Docker Desktop (includes Docker Compose)
- Supabase project (PostgreSQL + `pgvector` extension)
- Groq API key (LLM + Whisper)
- Hugging Face API key (embeddings)
- Telegram bot token (from @BotFather) — production + demo channel

---

## Local Development (Docker)

**1. Clone & configure:**
```bash
git clone https://github.com/Atharv-Bandekar/CogniCare
cd CogniCare
cp .env.example .env
# Edit .env with your keys (see Environment Variables below)
```

**2. Run Supabase migrations:**
```bash
# In Supabase Dashboard → SQL Editor, run:
# backend/database/migrations/0002_cognicare_v2_schema.sql
# backend/database/migrations/0003_add_telegram_chat_id.sql
# backend/database/migrations/0004_telegram_production.sql
```

**3. Start local stack:**
```bash
docker compose up --build -d
```
Services:
- `api` — FastAPI on `http://localhost:8000` (Swagger at `/docs`)
- `worker` — Celery worker (all 5 queues)
- `beat` — Celery Beat scheduler
- `redis` — Redis 7 (local)

**4. Register Telegram webhook (for local tunnel testing):**
```bash
# Start cloudflared tunnel to localhost:8000
cloudflared tunnel --url http://localhost:8000
# Copy the https URL, update .env:
# TELEGRAM_WEBHOOK_URL=https://your-tunnel.trycloudflare.com/webhooks/telegram/inbound
docker compose exec api python -c "
from backend.integrations.telegram_client import set_webhook
print(set_webhook())
"
```

**5. Test:** Open `t.me/YourBotUsername` → `/start`

---

## Production Deployment (Render)

**Services created via `render.yaml` Blueprint:**

| Service | Type | Command |
|---------|------|---------|
| `cognicare` | Web Service (Docker) | `honcho start` (FastAPI + Celery worker) |
| `cognicare-redis` | Redis (Free) | Managed by Render |

**Deploy:**
1. Push `render.yaml` to `main`
2. Render Dashboard → New → Blueprint → connect repo
3. Add environment variables (see below)
4. Deploy → watch logs for `honcho` starting both processes

**Register production webhook:**
```bash
docker compose exec api python -c "
from backend.integrations.telegram_client import set_webhook
print(set_webhook())
"
# Uses TELEGRAM_WEBHOOK_URL=https://cognicare-backend.onrender.com/webhooks/telegram/inbound
```

---

## Environment Variables

Create `.env` from `.env.example`:

```env
# =============================================================================
# Supabase (REQUIRED — backend crashes at import if missing)
# =============================================================================
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# =============================================================================
# LLM (Groq)
# =============================================================================
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key
GROQ_MODEL=openai/gpt-oss-20b
GROQ_WHISPER_MODEL=whisper-large-v3-turbo

# =============================================================================
# Embeddings (Hugging Face Inference Router)
# =============================================================================
HUGGINGFACE_API_KEY=hf_your_token

# =============================================================================
# Celery / Redis
# =============================================================================
# Local: redis://redis:6379/0 (docker-compose overrides)
# Render: auto-injected from cognicare-redis service
# Upstash: rediss://default:TOKEN@host:6379?ssl_cert_reqs=CERT_REQUIRED
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TIMEZONE=Asia/Kolkata

# =============================================================================
# Telegram Bot (production + recruiter demo channel)
# =============================================================================
TELEGRAM_BOT_TOKEN=123456:ABC-DEF-your-token
TELEGRAM_WEBHOOK_URL=https://cognicare-backend.onrender.com/webhooks/telegram/inbound
TELEGRAM_WEBHOOK_SECRET=your-random-secret-string
TELEGRAM_VALIDATE_SECRET=true
TELEGRAM_DEMO_CAREGIVER_ID=uuid-from-supabase-auth-users-table
TELEGRAM_BOT_USERNAME=CogniCareBot
```T=true
TELEGRAM_DEMO_CAREGIVER_ID=uuid-from-supabase-auth-users-table
```

**Frontend** (`frontend/.env.local`):
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=https://cognicare-backend.onrender.com
```

---

## Developer Roadmap

### 🧠 AI Agents (`backend/agents/`)
| File | Responsibility |
|------|----------------|
| `interviewer.py` | Generates daily memory questions (DDA + RAG context, multilingual) |
| `evaluator.py` | **Phase 3A:** `evaluate_response(text)` → structured insight (sentiment, engagement, topics, safety) |
| `coordinator.py` | **Phase 3A:** `generate_recommendation(elder, evaluator_output, domain, memories, weather)` → caregiver recommendation |
| `companion.py` | Warm, user-facing reply for Telegram channel (acknowledges elder's actual words) |
| `escalation.py` | **Phase 3A:** `check_escalation(elder_id, evaluator_output)` → safety/engagement alerts |
| `report_generator.py` | **Phase 3A:** `generate_weekly_report(elder_id, insights_7d)` → markdown summary |
| `question_engine.py` | Domain rotation (7-day), difficulty adaptation, RAG context building |
| `embeddings.py` | HF Inference Router client (fixed endpoint) |
| `base.py` | Shared Groq client with error logging |

### ⚙️ Celery Pipeline (`backend/celery_app/`)
| File | Responsibility |
|------|----------------|
| `config.py` | Queues, routes, acks_late, time limits, beat schedule import |
| `beat_schedule.py` | Cron definitions: daily questions (15min), fallback (12h), weekly reports (Mon 07:00) |
| `tasks/scheduling.py` | `dispatch_daily_questions`, `send_daily_question` (template-aware) |
| `tasks/inbound.py` | **Core 10-step pipeline** — idempotent, graceful degradation |
| `tasks/fallback.py` | `expire_stale_recommendations` |
| `tasks/reports.py` | `generate_all_weekly_reports`, `generate_weekly_report_for_elder` |
| `tasks/telegram_bot.py` | Telegram on-demand pipeline (reuses inbound helpers) |

### 🔌 Webhooks (`backend/webhooks/`)
| File | Purpose |
|------|---------|
| `twilio_webhook.py` | `POST /webhooks/twilio/inbound` — signature validation, enqueues to `inbound` queue |
| `telegram_webhook.py` | `POST /webhooks/telegram/inbound` — secret token validation, enqueues to `inbound` queue |

### 🗄️ Database (`backend/database/`)
| File | Purpose |
|------|---------|
| `db.py` | All Supabase CRUD + helpers (`get_elder_by_whatsapp_number`, `get_elder_by_telegram_chat_id`, `get_open_interaction_for_elder`, `update_daily_interaction`, etc.) |
| `migrations/0002_cognicare_v2_schema.sql` | Core schema + RLS |
| `migrations/0003_add_telegram_chat_id.sql` | Telegram demo support |

### 🌐 API Routes (`backend/api/routes/`)
| File | Endpoints |
|------|-----------|
| `elders.py` | `POST/GET/PATCH /api/elders` — onboarding & profile management |
| `recommendations.py` | `GET /api/{elder_id}/recommendations`, `POST /recommendations/{id}/done|dismiss|suggest` — caregiver dashboard |

### 🖥️ Frontend (`frontend/src/`)
| Path | Purpose |
|------|---------|
| `components/features/CheckInTab.tsx` | Elder check-in (voice/text, TTS, replay) |
| `components/features/DashboardTab.tsx` | Caregiver dashboard (history, insights, recommendations) |
| `components/layout/SettingsSidebar.tsx` | Language, accessibility, elder profile |
| `hooks/useAudioRecorder.ts` | Browser MediaRecorder + Whisper upload |
| `utils/translations.ts` | EN/HI/MR/TA UI strings |

---

## Phase Status

| Phase | Branch | Status | Tests | Description |
|-------|--------|--------|-------|-------------|
| **Pre-3A fixes** | `main` | ✅ Merged | — | Bug fixes: `source_id`→`source_interaction_id`, engagement case, imports |
| **Phase 3A** | `feature/evaluator-escalation-reports` | ✅ Complete, **unpushed** | 28/28 | Evaluator contract, escalation, weekly report orchestrator |
| **Phase 3B** | `feature/celery-pipeline-3b` | ✅ Complete, **unpushed** | 103/103 | Async Celery pipeline, Twilio/Whisper, webhook auth, beat scheduler |
| **Telegram Demo** | `main` | ✅ Merged | — | Telegram bot, auto-provisioning, companion reply, webhook |
| **Render Deploy** | `main` | ✅ Live | — | Docker + honcho + Upstash Redis on Render Free tier |

**Next:** Phase 4A (Frontend V2 integration — connect dashboard to real V2 endpoints, WebSocket for live updates, recommendation feedback UI).

---

## Team

Developed by **Atharv Bandekar** and **Shubham Govekar** for the AICTE | IBM SkillsBuild Internship (BharatCares).

- **Atharv (Member A):** Backend architecture, AI agents (3A), Celery pipeline (3B), Telegram demo, deployment
- **Shubham (Member B):** Frontend (V1), Database schema (V2), Supabase/RLS, Twilio integration

---

## License

MIT — see `LICENSE` for details.