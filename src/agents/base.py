import os
import requests
import logging

# In a fully modular setup, you'd pull these from a src/config.py file,
# but we'll fetch them straight from the environment here for simplicity.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def call_llm(system_prompt, user_prompt, max_tokens=200):
    """Unified LLM caller. Fails gracefully to offline defaults."""
    try:
        if LLM_PROVIDER == "groq":
            return _call_groq(system_prompt, user_prompt, max_tokens)
        elif LLM_PROVIDER == "gemini":
            return _call_gemini(system_prompt, user_prompt, max_tokens)
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
    except Exception as exc:
        logging.error(f"[LLM ERROR] Falling back to offline default. Reason: {exc}")
        return None


def _call_groq(system_prompt, user_prompt, max_tokens):
    if not GROQ_API_KEY or GROQ_API_KEY.startswith("PASTE_"):
        raise RuntimeError("GROQ_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_gemini(system_prompt, user_prompt, max_tokens):
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("PASTE_"):
        raise RuntimeError("GEMINI_API_KEY is not configured")

    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {
        "contents": [
            {"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}
        ],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
    }
    resp = requests.post(GEMINI_URL, headers=headers, params=params, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()