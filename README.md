# CogniCare AI

**Full-Stack Multi-Agent Cognitive Engagement Platform**

CogniCare AI is an AI-driven wellness companion for elderly users, built as an MVP for the **AICTE | IBM SkillsBuild AI Automation & Intelligent Solutions Internship (BharatCares)**, addressing **UN SDG 3: Good Health & Well-being**.

Originally a local desktop application, the system has been completely re-architected into a scalable, secure, full-stack web application. It engages users with daily memory-prompting questions, analyzes spoken or typed responses for emotional and cognitive signals, and recommends personalized offline activities — while giving caregivers secure, authenticated visibility into historical trends.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Database Security (Supabase)](#database-security-supabase)
- [Notes for Reviewers & Judges](#notes-for-reviewers--judges)
- [Team](#team)
- [License](#license)

---

## Tech Stack

* **Frontend:** Next.js (React), Tailwind CSS, TypeScript
* **Backend:** FastAPI, Python
* **Database & Auth:** Supabase (PostgreSQL) with Row Level Security (RLS)
* **AI Orchestration:** Multi-Agent Pipeline (Groq / Gemini / Llama 3)
* **Local NLP Inference:** HuggingFace `transformers` (`DeBERTa-v3-small`)
* **Audio Processing:** Browser MediaRecorder API & Groq Whisper API

---

## Key Features

- **Component-Driven Web UI:** A highly responsive, modern interface built with Next.js and Tailwind CSS, featuring dedicated Caregiver Dashboards and Patient Check-In tabs.
- **Enterprise-Grade Security:** User authentication and session management powered by Supabase Auth. Data is protected at the database level using PostgreSQL Row Level Security (RLS) ensuring strict data privacy between users.
- **Voice Mode (Accessibility-First):** Users can speak their answers using native browser microphone APIs, transcribed instantly via Groq Whisper. AI prompts and recommendations are read aloud via text-to-speech.
- **Multilingual Support:** Full UI and conversational support for English, Hindi, Marathi, and Tamil, to maximize reach and comfort for regional users.
- **Cross-Script Intelligence:** A backend translation middleware normalizes Romanized input (e.g., Marathi typed in English letters) into English for sentiment analysis, while preserving the native script for user-facing output.

---

## Architecture Overview

CogniCare AI runs on a **FastAPI backend** connected to a **unidirectional 3-agent pipeline**, where each agent's output is the strict, structured input to the next.

| Component | Tech | Responsibility |
|---|---|---|
| **Frontend Client** | Next.js | Handles UI, JWT session tokens, and browser audio recording |
| **Agent 1: The Interviewer** | Cloud LLM (70B) | Generates a warm, culturally-aware daily memory question localized to the user's selected language |
| **Agent 2: The Evaluator** | Local NLP (DeBERTa)| Analyzes the translated English response for sentiment and engagement level |
| **Agent 3: The Coordinator** | Cloud LLM (70B) | Combines the raw response with Agent 2's analysis to recommend a concrete offline activity |
| **Secure Data Layer** | Supabase (Postgres) | Validates JWTs and strictly enforces user data isolation before logging histories |

---

## Project Structure

```text
cognicare_ai/
├── frontend/                # Next.js Web Application
│   ├── src/
│   │   ├── app/             # Next.js App Router (page.tsx, layout.tsx)
│   │   ├── components/      # React Components (AuthScreen, CheckInTab, DashboardTab)
│   │   └── utils/           # Supabase Client & UI Translations
│   ├── .env.local           # Frontend Supabase & API keys
│   └── package.json         # Node dependencies
├── src/                     # Python Backend Application
│   ├── agents/              # Multi-Agent Pipeline
│   │   ├── base.py          # LLM API communication & translation middleware
│   │   ├── interviewer.py   # Agent 1: Question generation
│   │   ├── evaluator.py     # Agent 2: Local NLP inference & heuristics
│   │   └── coordinator.py   # Agent 3: Activity recommendation
│   ├── database/
│   │   └── db.py            # Supabase Python client connection
│   └── config.py            # Global constants and environment variables
├── server.py                # FastAPI endpoints and route handlers
├── requirements.txt         # Python dependency list
└── pyproject.toml           # uv project configuration
```

---

## Installation & Setup

You will need **Node.js**, **Python 3.10+**, and a **Supabase** account to run this project.

### 1. Backend Setup (FastAPI)

```bash
# Clone the repository
git clone https://github.com/Atharv-Bandekar/CogniCare
cd CogniCare

# Create a virtual environment using uv (or standard pip)
uv venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows

# Install Python dependencies
uv pip install -r requirements.txt

# Configure environment variables (create a .env file in the root)
# Add your GROQ_API_KEY, SUPABASE_URL, and SUPABASE_SERVICE_ROLE_KEY
```

Start the FastAPI server:

```bash
fastapi dev server.py
# Server runs on http://127.0.0.1:8000
```

### 2. Frontend Setup (Next.js)

Open a new terminal window:

```bash
cd frontend

# Install Node dependencies
npm install

# Configure frontend environment variables (create .env.local)
# Add NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, and NEXT_PUBLIC_API_URL
```

Start the Next.js development server:

```bash
npm run dev
# App runs on http://localhost:3000
```

---

## Database Security (Supabase)

This application uses strictly enforced Row Level Security (RLS). To replicate the database structure, run the following SQL in your Supabase SQL Editor:

```sql
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;

-- Enforce User-Data Isolation Policies
CREATE POLICY "Users can view their own conversations" ON conversations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own conversations" ON conversations FOR INSERT WITH CHECK (auth.uid() = user_id);
-- (See full SQL security scripts in project documentation)
```

---

## Notes for Reviewers & Judges

* **Scalable Architecture:** The project has evolved from a monolithic desktop script into a decoupled, RESTful web application ready for cloud deployment (e.g., Vercel + Render).
* **Culturally-aware prompting:** The translation middleware is specifically instructed to avoid literal translations of Western concepts (e.g., "grandfather clock"), adapting them into culturally relevant equivalents to prevent hallucination in regional languages.
* **Local AI integration:** Agent 2 runs lightweight, hybrid heuristic/NLP inference using HuggingFace `transformers`. Swapping in a fine-tuned sentiment checkpoint is a one-line config change.
* **Zero Data Leakage:** Supabase JWT integration guarantees that caregivers and patients only ever have access to their distinct cryptographic identities.

---

## Team

Built by Shubham Govekar and Atharv Bandekar as part of the AICTE | IBM SkillsBuild AI Automation & Intelligent Solutions Internship, in partnership with BharatCares.

---

## License

MIT — see [LICENSE](LICENSE) for details.