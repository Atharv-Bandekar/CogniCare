Here is the markdown code for your README. You can easily copy this and paste it directly into your `README.md` file, or use the copy button on the top right of the code block to grab it all at once.

```markdown
# CogniCare AI 🧠
**Multi-Agent Cognitive Engagement Assistant**

An AI-driven wellness companion designed for elderly users, developed as an MVP for an IBM internship pitch addressing **UN SDG 3: Good Health & Well-being**. 

CogniCare AI uses a localized multi-agent pipeline to engage users with daily memory questions, analyze their cognitive and emotional responses in real-time, and recommend personalized offline activities to promote mental wellness.

## 🏗️ Architecture Overview

The application is powered by a unidirectional **3-Agent Pipeline**, where each agent's output serves as the strict input for the next:

1. **Agent 1 — The Interviewer (Cloud LLM):** Generates a warm, specific, and unique daily memory question tailored to prompt nostalgic reflection.
2. **Agent 2 — The Evaluator (Local NLP):** Runs a local `microsoft/deberta-v3-small` transformer model to analyze the user's typed response. It scores sentiment and extracts engagement levels, logging the telemetry to a local SQLite database.
3. **Agent 3 — The Coordinator (Cloud LLM):** Ingests the user's raw text alongside Agent 2's structured sentiment/engagement analysis to generate a highly personalized, concrete offline activity recommendation.

## 📂 Project Structure

The project follows an industry-standard modular design for scalable agentic applications:

```text
cognicare_ai/
├── src/                    
│   ├── agents/
│   │   ├── base.py         # Shared LLM API communication logic
│   │   ├── interviewer.py  # Agent 1: Question generation
│   │   ├── evaluator.py    # Agent 2: Local DeBERTa inference & heuristics
│   │   └── coordinator.py  # Agent 3: Activity recommendation
│   ├── database/
│   │   └── db.py           # SQLite connection and schema definitions
│   ├── ui/
│   │   └── app.py          # Tkinter frontend and background thread management
│   └── config.py           # Global constants and environment variables
├── .env                    # API keys and configuration overrides (gitignored)
├── requirements.txt        # Dependency list
└── main.py                 # Application entry point

```

## ⚙️ Installation & Setup

This project uses `uv` for lightning-fast dependency management (standard `pip` also supported).

**1. Clone and activate your virtual environment:**

```bash
uv venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

```

**2. Install dependencies:**

```bash
uv pip install -r requirements.txt
# Requires: transformers, torch, protobuf, sentencepiece, tiktoken, python-dotenv, requests

```

**3. Configure Environment Variables:**
Create a `.env` file in the root directory and add your preferred Cloud LLM API key.

```env
# Required: Choose your provider and add the key
LLM_PROVIDER=groq  # or 'gemini'
GROQ_API_KEY=your-groq-api-key-here
# GEMINI_API_KEY=your-gemini-key-here

```

**4. Run the Application:**

```bash
python main.py

```

## 💡 Notes for Reviewers & Judges

* **Graceful Degradation (Offline Mode):** If API keys are missing or network connectivity drops during a live pitch, Agents 1 and 3 will seamlessly fall back to pre-written behavioral heuristics. The app will never hard-crash during a demo.
* **Local Data Privacy:** Agent 2 (The Evaluator) runs entirely locally using `transformers`. It is loaded asynchronously on a background thread during application startup to ensure the UI remains instantly responsive.
* **Model Configuration:** Because `microsoft/deberta-v3-small` is a base encoder, this MVP blends its zero-shot classification output with a transparent keyword/length heuristic. For a production deployment, swapping `LOCAL_MODEL_NAME` to a fine-tuned sentiment checkpoint is a one-line configuration change.
* **Caregiver Telemetry:** All interactions, including the raw text and Agent 2's calculated emotional insights, are logged directly to a local SQLite database (`cognicare.db`), viewable in real-time via the Caregiver Dashboard tab.

```

```