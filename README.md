# CogniCare AI

**Multi-Agent Cognitive Engagement Assistant**

CogniCare AI is an AI-driven wellness companion for elderly users, built as an MVP for the **AICTE | IBM SkillsBuild AI Automation & Intelligent Solutions Internship (BharatCares)**, addressing **UN SDG 3: Good Health & Well-being**.

The system engages users with daily memory-prompting questions, analyzes their responses for emotional and cognitive signals, and recommends personalized offline activities — while giving caregivers visibility into trends over time.

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Running the App](#running-the-app)
- [Notes for Reviewers & Judges](#notes-for-reviewers--judges)
- [Team](#team)
- [License](#license)

---

## Key Features

- **Voice Mode (Accessibility-First):** Users can speak their answers using `SpeechRecognition` and hear the AI's prompts and recommendations read aloud via Google TTS (`gTTS`).
- **Multilingual Support:** Full UI and conversational support for English, Hindi, Marathi, and Tamil, to maximize reach and comfort for regional users.
- **Cross-Script Intelligence:** A backend translation middleware normalizes Romanized input (e.g., Marathi typed in English letters) into English for sentiment analysis, while preserving the native script (Devanagari/Tamil) for user-facing TTS output.
- **Modern Interface:** Built with `customtkinter` for a responsive, dark-mode compatible dashboard.

---

## Architecture Overview

CogniCare AI runs on a **unidirectional 3-agent pipeline**, where each agent's output is the strict, structured input to the next — demonstrating genuine agent-to-agent hand-off rather than a single script making repeated API calls.

| Component | Tech | Responsibility |
|---|---|---|
| **Agent 1: The Interviewer** | Cloud LLM (70B) | Generates a warm, culturally-aware daily memory question localized to the user's selected language |
| **Translation Middleware** | Cloud LLM (70B) | Normalizes native or Romanized (Hinglish/Minglish/Tanglish) input into clean English |
| **Agent 2: The Evaluator** | Local NLP (DeBERTa) | Analyzes the translated English response for sentiment and engagement level; logs results to SQLite |
| **Agent 3: The Coordinator** | Cloud LLM (70B) | Combines the raw response with Agent 2's analysis to recommend a concrete offline activity, in the user's native script |

Each agent communicates via structured JSON and parsed text, so the full chain is inspectable at every step.

---

## Project Structure

```text
cognicare_ai/
├── src/
│   ├── agents/
│   │   ├── base.py          # Shared LLM API communication & translation middleware
│   │   ├── interviewer.py   # Agent 1: Question generation
│   │   ├── evaluator.py     # Agent 2: Local NLP inference & heuristics
│   │   └── coordinator.py   # Agent 3: Activity recommendation
│   ├── database/
│   │   └── db.py            # SQLite connection and schema definitions
│   ├── ui/
│   │   └── app.py           # CustomTkinter frontend and background thread management
│   ├── utils/
│   │   └── audio.py         # gTTS and SpeechRecognition microphone handlers
│   └── config.py            # Global constants and environment variables
├── .env                     # API keys and configuration overrides (gitignored)
├── requirements.txt         # Dependency list
└── main.py                  # Application entry point
```

---

## Installation & Setup

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

Key dependencies: `transformers`, `torch`, `protobuf`, `sentencepiece`, `tiktoken`, `python-dotenv`, `requests`, `customtkinter`, `SpeechRecognition`, `pyaudio`, `gTTS`, `pygame`

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
LLM_PROVIDER=groq          # or 'gemini'
GROQ_API_KEY=your-api-key-here
# GEMINI_API_KEY=your-api-key-here
```

---

## Running the App

```bash
python main.py
```

---

## Notes for Reviewers & Judges

- **Culturally-aware prompting:** the translation middleware is specifically instructed to avoid literal translations of Western concepts (e.g., "grandfather clock"), adapting them into culturally relevant equivalents to prevent hallucination in regional languages.
- **Graceful degradation:** if API keys are missing or connectivity drops mid-demo, Agents 1 and 3 fall back to pre-written heuristics — the app is designed to never hard-crash during a live pitch.
- **Local data privacy:** Agent 2 runs entirely on-device via `transformers`, loaded asynchronously on a background thread so the UI stays responsive on startup.
- **Model configuration:** the local model is a lightweight base encoder blended with a transparent keyword/length heuristic for this MVP. Swapping in a fine-tuned sentiment checkpoint is a one-line config change (`LOCAL_MODEL_NAME`).
- **Caregiver telemetry:** every interaction — raw text plus Agent 2's derived insights — is logged to a local SQLite database (`cognicare.db`) and viewable in real time via the Caregiver Dashboard.

---

## Team

Built by [Your Name] and [Teammate Name] as part of the AICTE | IBM SkillsBuild AI Automation & Intelligent Solutions Internship, in partnership with BharatCares.

---

## License

MIT — see [LICENSE](LICENSE) for details.