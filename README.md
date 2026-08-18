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

## 🗄️ Database Schema (V2)
The backend relies on Supabase PostgreSQL with the `pgvector` extension. 

* **`elder_profiles`**: Core elder configuration (language, timezone, proximity to caregiver, mobility constraints).
* **`daily_interactions`**: Records the Twilio webhook interactions and transcripts.
* **`interaction_insights`**: Stores the output of the HF DeBERTa evaluation (engagement, sentiment, topics).
* **`memories`**: `pgvector` (384-dim) table storing extracted elder memories for Context Collision (RAG).
* **`recommendations`**: AI-generated distance-appropriate actions for the caregiver.
* **`family_interactions`**: Logs dashboard feedback (done, dismiss, custom suggestions) to weave into future prompts.
* **`weekly_reports`**: Aggregated 7-day cognitive and emotional summaries.

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

# Setup

## 🗄️ Step 1: Database Setup (Supabase)

Before you write or run any code, your local environment needs a database to store the AI's memory logs, otherwise the backend will crash on the first question!

1. Log into [Supabase](https://supabase.com/) and create a new project (or open the existing development project).
2. Go to the **SQL Editor** on the left sidebar.
3. Paste and run this **exact script** to create your tables and security policies:

```sql
-- 1. Create the conversations table
CREATE TABLE public.conversations (
  id uuid NOT NULL DEFAULT extensions.uuid_generate_v4(),
  user_id uuid NOT NULL,
  question text,
  response text,
  timestamp timestamp with time zone DEFAULT now(),
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

-- Enable Row Level Security (RLS)
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;

-- Enforce User-Data Isolation Policies
CREATE POLICY "Users can view their own conversations" ON conversations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own conversations" ON conversations FOR INSERT WITH CHECK (auth.uid() = user_id);
```

---

## ⚙️ Step 2: Backend Setup (FastAPI + AI Agents)

The backend runs the AI pipeline. You will need Python 3.10+ installed.

1. Open your terminal and clone the repository:

```bash
git clone https://github.com/Atharv-Bandekar/CogniCare
cd CogniCare/backend
```

2. Create and activate a Python virtual environment to keep dependencies clean:

```bash
# Mac/Linux:
python -m venv venv
source venv/bin/activate

# Windows:
python -m venv venv
venv\Scripts\activate
```

3. Install all required Python packages:

```bash
pip install -r requirements.txt
```

4. **CRITICAL STEP:** Create a file literally named `.env` inside the `backend` folder and paste these exact keys into it. Do not use quotes around the values.

```env
# backend/.env
GROQ_API_KEY=your_groq_api_key_here
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
SUPABASE_URL=your_supabase_url_here -> (https://[your-project-id-from-supabase].supabase.co)
SUPABASE_KEY=your_supabase_anon_key_here -> -> (use anon key from the supabase dashboard)
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
LLM_PROVIDER=groq
```

5. Start the backend server:

```bash
uvicorn main:app --reload
```

*(Leave this terminal window open! The backend is now running on `http://127.0.0.1:8000`)*

---

## 🎨 Step 3: Frontend Setup (Next.js)

The frontend handles the UI, microphone recording, and user accounts. You will need Node.js installed.

1. Open a **new, second terminal window** and navigate to the frontend folder:

```bash
cd CogniCare/frontend
```

2. Install all Node dependencies:

```bash
npm install
```

3. **CRITICAL STEP:** Create a file named `.env.local` inside the `frontend` folder and paste these keys into it:

```env
# frontend/.env.local
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url_here
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

4. Start the frontend development server:

```bash
npm run dev
```

**🎉 You are done! Open `http://localhost:3000` in your browser. You can now create an account and test the app.**

---

## 🗺️ Developer Roadmap: Where is everything?

When you need to build new features or fix bugs, here is exactly where to look:

### 🧠 The AI Brains (`/backend/agents/`)

* **`interviewer.py`**: Want to change the daily questions? Add new topics? Or tweak the language strictness? Do it here.
* **`evaluator.py`**: This connects to Hugging Face to calculate if the user is Happy, Sad, or Engaged.
* **`coordinator.py`**: This takes the mood and generates the Morning/Afternoon/Evening JSON plan.

### 🔌 The APIs & Database (`/backend/`)

* **`api/routes.py`**: This is the traffic cop. When the frontend clicks "Submit", this file receives the request, calls the Agents, and sends the answer back.
* **`database/db.py`**: All Supabase saving/reading happens here.

### 🖥️ The UI (`/frontend/src/`)

* **`components/features/CheckInTab.tsx`**: The main screen where users talk to the AI. Handles the microphone, the text area, and parsing the JSON plan.
* **`components/features/DashboardTab.tsx`**: The caregiver screen showing past history and mood badges.
* **`utils/translations.ts`**: If you need to add a new language or change a button's text, edit this dictionary!

---

## 🤝 Team

Developed by **Shubham Govekar** and **Atharv Bandekar** for the AICTE | IBM SkillsBuild Internship. Deployment handled separately.
