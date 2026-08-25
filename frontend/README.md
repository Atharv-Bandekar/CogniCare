# CogniCare Frontend

**Next.js 14 (App Router) — Caregiver Dashboard & Elder Check-In**

This is the web UI for CogniCare AI. It provides:
- **Elder Check-In Tab** — voice/text responses to daily questions, TTS playback, accessibility controls
- **Caregiver Dashboard Tab** — history, insights, recommendations with done/dismiss/suggest actions
- **Settings Sidebar** — language, text size, elder profile management
- **Auth Screen** — Supabase Auth (email/password, magic link)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Next.js 14 (App Router), React 18 |
| Styling | Tailwind CSS, shadcn/ui components |
| Language | TypeScript (strict) |
| Auth | Supabase Auth (SSR via `@supabase/ssr`) |
| API Client | Custom fetch wrapper (`src/utils/supabaseClient.ts`) |
| Audio | Browser MediaRecorder API → Whisper (Groq) |
| State | React hooks (`useAudioRecorder`, `useSettings`, `useSpeech`) |

---

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout, providers, fonts
│   │   ├── page.tsx            # Landing → redirects to /dashboard or /checkin
│   │   ├── dashboard/          # Caregiver dashboard (protected)
│   │   ├── checkin/            # Elder check-in (protected)
│   │   ├── auth/               # Auth callback route
│   │   └── globals.css         # Tailwind + custom CSS variables
│   ├── components/
│   │   ├── features/
│   │   │   ├── CheckInTab.tsx       # Main elder interaction UI
│   │   │   └── DashboardTab.tsx     # Caregiver dashboard UI
│   │   ├── layout/
│   │   │   ├── SettingsSidebar.tsx  # Language, accessibility, profile
│   │   │   └── WelcomeSplash.tsx    # Onboarding splash
│   │   ├── ui/                     # shadcn/ui primitives (Button, Card, etc.)
│   │   └── auth/
│   │       └── AuthScreen.tsx      # Login/signup UI
│   ├── hooks/
│   │   ├── useAudioRecorder.ts     # MediaRecorder + chunk upload
│   │   ├── useSettings.ts          # Language, text size, TTS prefs
│   │   └── useSpeech.ts            # Browser TTS (speechSynthesis)
│   ├── utils/
│   │   ├── supabaseClient.ts       # Server/client Supabase clients
│   │   └── translations.ts         # EN/HI/MR/TA string dictionary
│   └── types/
│       └── index.ts                # Shared TypeScript interfaces
├── public/                         # Static assets
├── .env.local                      # Local env (gitignored)
├── next.config.ts                  # Next.js config
├── tailwind.config.ts              # Tailwind config
├── tsconfig.json                   # TypeScript config
└── package.json
```

---

## Getting Started

### Prerequisites
- Node.js 20+
- Running backend API (local: `http://localhost:8000`, or Render URL)
- Supabase project (same as backend)

### Install & Run

```bash
cd frontend
npm install

# Create .env.local from template
cp .env.local.example .env.local
# Edit with your values (see below)

npm run dev
```

Open `http://localhost:3000`.

---

## Environment Variables (`.env.local`)

```env
# Supabase (must match backend project)
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Backend API (local or production)
NEXT_PUBLIC_API_URL=http://localhost:8000
# Or for production:
# NEXT_PUBLIC_API_URL=https://cognicare-backend.onrender.com
```

> The frontend uses the **anon key** (safe for browser). The backend uses the **service role key** (server-only).

---

## Key Features Implementation

### Check-In Tab (`CheckInTab.tsx`)
- Fetches today's question from `GET /api/question` (V1) — **TODO: migrate to V2 `/api/elders/{elder_id}/question`**
- Voice recording via `useAudioRecorder` → uploads to `POST /api/transcribe`
- Text submission → `POST /api/analyze`
- Displays JSON activity plan from Coordinator
- TTS playback via `useSpeech` (browser `speechSynthesis`)
- Accessibility: dynamic font size, high contrast, audio replay

### Dashboard Tab (`DashboardTab.tsx`)
- Loads history from `GET /api/history` (V1) — **TODO: migrate to V2 `/api/{elder_id}/recommendations`**
- Displays sentiment/engagement badges from `interaction_insights`
- Recommendation cards with **Done / Dismiss / Custom Suggestion** actions
- Calls `POST /api/recommendations/{id}/done|dismiss|suggest`

### Settings Sidebar (`SettingsSidebar.tsx`)
- Language selector (EN/HI/MR/TA) → persists to `localStorage` + Supabase
- Text size slider (CSS `--font-scale` variable)
- Elder profile editor (name, proximity, mobility, timezone)

### Auth Screen (`AuthScreen.tsx`)
- Supabase Auth: email/password, magic link
- On signup: creates `elder_profiles` row via `POST /api/elders`
- Session persisted via `@supabase/ssr` cookies

---

## V1 → V2 Migration Status (Frontend)

| V1 Endpoint (current) | V2 Endpoint (target) | Status |
|----------------------|---------------------|--------|
| `GET /api/question` | `GET /api/elders/{elder_id}/question` | ❌ Not implemented in backend |
| `POST /api/transcribe` | `POST /api/elders/{elder_id}/transcribe` | ❌ Not implemented |
| `POST /api/analyze` | Handled by Celery pipeline (async, Telegram) | ❌ Architecture change |
| `GET /api/history` | `GET /api/{elder_id}/recommendations` | ❌ Not implemented |
| `POST /api/refresh-question` | Handled by Celery Beat | ❌ Architecture change |

**Phase 4A scope:** Implement V2 API endpoints + WebSocket for live updates + migrate frontend calls.

**Note:** The backend is now **Telegram-only** (no WhatsApp). Elders receive questions and reply via Telegram bot. The frontend dashboard connects to the same Supabase database to show insights and recommendations.

---

## Commands

```bash
npm run dev          # Development server (localhost:3000)
npm run build        # Production build
npm run start        # Run production build
npm run lint         # ESLint
npm run type-check   # TypeScript check
```

---

## Deployment (Vercel)

1. Connect repo to Vercel
2. Set env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`
3. Deploy — Vercel auto-detects Next.js

> The frontend is static-exportable for demo purposes, but SSR is used for Supabase Auth.

---

## Notes for Shubham (Phase 4A)

Your local `main` branch is at **Phase 2** (V1 synchronous architecture). The backend has advanced to **Phase 3B + Telegram-only production** with a completely different async architecture.

**To catch up locally:**

1. **Pull latest `main`:**
   ```bash
   git fetch origin
   git checkout main
   git pull origin main
   ```

2. **Run migrations on your Supabase:**
   - `backend/database/migrations/0002_cognicare_v2_schema.sql`
   - `backend/database/migrations/0003_add_telegram_chat_id.sql`
   - `backend/database/migrations/0004_telegram_production.sql`

3. **Use Docker for local dev (recommended):**
   ```bash
   cp .env.example .env
   # Fill in your keys (see .env.example for Telegram-only vars)
   docker compose up --build -d
   ```
   This runs API + worker + beat + Redis with the exact production config.

4. **Frontend env:**
   ```bash
   cd frontend
   cp .env.local.example .env.local
   # Set NEXT_PUBLIC_API_URL=http://localhost:8000
   npm install && npm run dev
   ```

5. **Test Telegram demo:**
   ```bash
   # Start tunnel
   cloudflared tunnel --url http://localhost:8000
   # Update .env TELEGRAM_WEBHOOK_URL to your tunnel URL
   docker compose exec api python -c "
   from backend.integrations.telegram_client import set_webhook
   print(set_webhook())
   "
   # Test at t.me/YourBot
   ```

**Key architectural changes you'll see:**
- **No WhatsApp/Twilio code** — backend is Telegram-only (production + demo)
- No more synchronous `POST /api/analyze` — inbound messages go to Celery queue
- Daily questions sent by Celery Beat at `preferred_interaction_time` via Telegram
- Recommendations created async, appear in dashboard via `GET /api/{elder_id}/recommendations`
- Telegram bot for zero-friction recruiter demo + production elders
- Production elders onboarded via deep-link: `t.me/YourBot?start=elder_<uuid>`
- WebSocket for live updates (planned Phase 4A)

---

## License

MIT