# CogniCare AI 🧠

**Multi-Agent Cognitive Engagement Assistant**

CogniCare AI is an AI-driven wellness companion for elderly users, built as an MVP for the **AICTE | IBM SkillsBuild AI Automation & Intelligent Solutions Internship (BharatCares)**, addressing **UN SDG 3: Good Health & Well-being**.

The system engages users with daily memory-prompting questions, analyzes their responses for emotional and cognitive signals, and recommends personalized offline activities — while giving caregivers visibility into trends over time.

---

## Table of Contents

- [Architecture Overview](#-architecture-overview)
- [Project Structure](#-project-structure)
- [Installation & Setup](#-installation--setup)
- [Running the App](#-running-the-app)
- [Notes for Reviewers & Judges](#-notes-for-reviewers--judges)
- [Team](#-team)
- [License](#-license)

---

## 🏗️ Architecture Overview

CogniCare AI runs on a **unidirectional 3-agent pipeline**, where each agent's output is the strict, structured input to the next — proving genuine agent-to-agent hand-off rather than a single script making repeated API calls.

| Agent | Role | Responsibility |
|---|---|---|
| **1. The Interviewer** | Cloud LLM | Generates a warm, specific daily memory question designed to prompt nostalgic reflection |
| **2. The Evaluator** | Local NLP | Analyzes the user's response for sentiment and engagement level; logs results to SQLite |
| **3. The Coordinator** | Cloud LLM | Combines the raw response with Agent 2's analysis to recommend a concrete, personalized offline activity |

Each agent communicates via structured JSON, so the full chain — question → response → analysis → recommendation — is inspectable at every step.

---

## 📂 Project Structure

```
cognicare_ai/
├── src/
│   ├── agents/
│   │   ├── base.py          # Shared LLM API communication logic
│   │   ├── interviewer.py   # Agent 1: Question generation
│   │   ├── evaluator.py     # Agent 2: Local NLP inference & heuristics
│   │   └── coordinator.py   # Agent 3: Activity recommendation
│   ├── database/
│   │   └── db.py            # SQLite connection and schema definitions
│   ├── ui/
│   │   └── app.py           # Frontend and background thread management
│   └── config.py            # Global constants and environment variables
├── .env                      # API keys and configuration overrides (gitignored)
├── requirements.txt           # Dependency list
└── main.py                    # Application entry point
```

---

## ⚙️ Installation & Setup

This project uses [`uv`](https://github.com/astral-sh/uv) for fast dependency management (standard `pip` also supported).

### 1. Clone the repository and create a virtual environment

```bash
git clone <your-repo-url>
cd cognicare_ai
uv venv

# Activate the environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 2. Install dependencies

```bash
uv pip install -r requirements.txt
```

Key dependencies: `transformers`, `torch`, `protobuf`, `sentencepiece`, `tiktoken`, `python-dotenv`, `requests`

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
LLM_PROVIDER=groq          # or 'gemini'
GROQ_API_KEY=your-api-key-here
# GEMINI_API_KEY=your-api-key-here
```

---

## 🚀 Running the App

```bash
python main.py
```

---

## 💡 Notes for Reviewers & Judges

- **Graceful degradation:** if API keys are missing or connectivity drops mid-demo, Agents 1 and 3 fall back to pre-written heuristics — the app is designed to never hard-crash during a live pitch.
- **Local data privacy:** Agent 2 runs entirely on-device via `transformers`, loaded asynchronously on a background thread so the UI stays responsive on startup.
- **Model configuration:** the local model is a lightweight base encoder blended with a transparent keyword/length heuristic for this MVP. Swapping in a fine-tuned sentiment checkpoint is a one-line config change (`LOCAL_MODEL_NAME`).
- **Caregiver telemetry:** every interaction — raw text plus Agent 2's derived insights — is logged to a local SQLite database (`cognicare.db`) and viewable in real time via the Caregiver Dashboard.

---

## 👥 Team

Built by [Your Name] and [Teammate Name] as part of the AICTE | IBM SkillsBuild AI Automation & Intelligent Solutions Internship, in partnership with BharatCares.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.