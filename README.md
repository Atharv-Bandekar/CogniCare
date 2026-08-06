# CogniCare AI 🧠

**Full-Stack Multi-Agent Cognitive Engagement Platform**

CogniCare AI is an AI-driven wellness companion for elderly users, built as an MVP for the **AICTE | IBM SkillsBuild AI Automation & Intelligent Solutions Internship (BharatCares)**, addressing **UN SDG 3: Good Health & Well-being**.

Originally a local desktop application, the system has been completely re-architected into a scalable, secure, full-stack web application. It engages users with daily memory-prompting questions, analyzes spoken or typed responses for emotional and cognitive signals, and recommends personalized offline activities — while giving caregivers secure, authenticated visibility into historical trends.

---

## Table of Contents
- [Tech Stack](#tech-stack)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Database Setup (Supabase)](#database-setup-supabase)
- [Installation & Setup](#installation--setup)
- [Developer Roadmap (Where to look)](#developer-roadmap)
- [Notes for Reviewers & Judges](#notes-for-reviewers--judges)
- [Team](#team)
- [License](#license)

---

## Tech Stack

* **Frontend:** Next.js (React), Tailwind CSS, TypeScript
* **Backend:** FastAPI, Python (Synchronous Event Loop for Mobile Stability)
* **Database & Auth:** Supabase (PostgreSQL) with Row Level Security (RLS)
* **AI Orchestration:** Multi-Agent Pipeline (Groq / Llama 3 / Mixtral)
* **Local NLP Inference:** Hugging Face Inference API (`DeBERTa-v3-small`)
* **Audio Processing:** Browser MediaRecorder API & Groq Whisper API

---

## Key Features

- **Component-Driven Web UI:** A highly responsive, modern interface built with Next.js and Tailwind CSS, featuring dedicated Caregiver Dashboards and Patient Check-In tabs.
- **Voice & Accessibility First:** Users can speak answers using native browser microphones, transcribed instantly via Whisper. Features include adjustable text sizes, dynamic Text-To-Speech (TTS), and an interactive **Audio Replay** button for accessibility.
- **Flawless Multilingual Support:** Full UI and AI generation in English, Hindi, Marathi, and Tamil. Strict prompt guardrails prevent LLMs from hallucinating English letters into regional scripts.
- **Enterprise-Grade Security:** User authentication and session management powered by Supabase Auth, protected at the database level using PostgreSQL Row Level Security (RLS).
- **Mobile-Optimized Backend:** FastAPI routes are strictly configured to prevent event-loop blocking, ensuring seamless connectivity on aggressive mobile browser network timeouts.

---

## Architecture Overview

CogniCare AI runs on a **FastAPI backend** connected to a **unidirectional 3-agent pipeline**, where each agent's output is the strict, structured input to the next.

| Component | Tech | Responsibility |
|---|---|---|
| **Frontend Client** | Next.js | Handles UI, JWT session tokens, and browser audio recording |
| **Agent 1: The Interviewer** | Cloud LLM (70B) | Generates a warm, culturally-aware daily memory question strictly in the user's selected language |
| **Agent 2: The Evaluator** | HF API (DeBERTa)| Analyzes the translated English response for sentiment and engagement level using hybrid heuristics |
| **Agent 3: The Coordinator** | Cloud LLM (70B) | Combines the raw response with Agent 2's analysis to recommend a concrete offline activity plan |
| **Secure Data Layer** | Supabase (Postgres)| Validates JWTs and strictly enforces user data isolation before logging histories |

---

## 🗄️ Database Setup (Supabase)

To run this project locally, your Supabase project needs two specific tables to store the AI's memory logs. Go to the **SQL Editor** in your Supabase dashboard and run this exact script:

```sql
-- 1. Create the conversations table
CREATE TABLE public.conversations (
  id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
  user_id uuid NOT NULL,
  question text,
  response text,
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (id)
);

-- 2. Create the insights table
CREATE TABLE public.insights (
  id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
  conversation_id uuid REFERENCES public.conversations(id),
  sentiment_label text,
  sentiment_score numeric,
  engagement_level text,
  engagement_score numeric,
  recommended_activity text,
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (id)
);

-- Enable RLS on all tables
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;

-- Enforce User-Data Isolation Policies
CREATE POLICY "Users can view their own conversations" ON conversations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own conversations" ON conversations FOR INSERT WITH CHECK (auth.uid() = user_id);
```

---

## Installation & Setup

You will need **Node.js**, **Python 3.10+**, and a **Supabase** account to run this project.

### 1. Backend Setup (FastAPI)

```bash
# Clone the repository
git clone https://github.com/Atharv-Bandekar/CogniCare
cd CogniCare/backend

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables (create a .env file in the backend folder)
# Add GROQ_API_KEY, HUGGINGFACE_API_KEY, SUPABASE_URL, and SUPABASE_KEY
```

Start the FastAPI server:

```bash
uvicorn main:app --reload
# Server runs on http://127.0.0.1:8000
```

### 2. Frontend Setup (Next.js)

Open a new terminal window:

```bash
cd CogniCare/frontend

# Install Node dependencies
npm install

# Configure frontend environment variables (create .env.local in the frontend folder)
# Add NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, and NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Start the Next.js development server:

```bash
npm run dev
# App runs on http://localhost:3000
```

---

## 🗺️ Developer Roadmap

If you are looking to modify specific features, here is where everything lives:

**Backend (`/backend`)**

* `/agents/interviewer.py`: Modifies the daily questions, topic randomness, and prompt guardrails.
* `/agents/evaluator.py`: Handles Hugging Face sentiment scoring and engagement logic.
* `/agents/coordinator.py`: Generates the structured JSON morning/afternoon/evening activity plans.
* `/api/routes.py`: The FastAPI endpoints (`/api/question`, `/api/analyze`, `/api/history`).
* `/database/db.py`: All Supabase read/write operations.

**Frontend (`/frontend`)**

* `/src/components/features/CheckInTab.tsx`: The main daily check-in UI (Microphone, View Rendering, JSON Parsing).
* `/src/components/features/DashboardTab.tsx`: The caregiver history view and AI insight badges.
* `/src/utils/translations.ts`: The master dictionary for English, Hindi, Marathi, and Tamil UI text.

---

## Notes for Reviewers & Judges

* **Scalable Architecture:** The project has evolved from a monolithic script into a decoupled, RESTful web application ready for cloud deployment (e.g., Vercel + Render).
* **Culturally-aware prompting:** The translation middleware avoids literal translations of Western concepts, adapting them into culturally relevant equivalents to prevent hallucination in regional languages.
* **Resilient Parsing:** The frontend utilizes advanced Regex and optional chaining to gracefully handle and render AI hallucinations or missing JSON keys without crashing the UI.
* **Zero Data Leakage:** Supabase JWT integration guarantees that caregivers and patients only ever have access to their distinct cryptographic identities.

---

## Team

Built by **Shubham Govekar** and **Atharv Bandekar** as part of the AICTE | IBM SkillsBuild AI Automation & Intelligent Solutions Internship, in partnership with BharatCares.

---

## License

MIT — see [LICENSE](LICENSE) for details.
