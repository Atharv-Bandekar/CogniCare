import os
import requests
import logging

# In a fully modular setup, you'd pull these from a src/config.py file,
# but we'll fetch them straight from the environment here for simplicity.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def call_llm(system_prompt, user_prompt, max_tokens=200, temperature=0.7):
    """Unified LLM caller. Fails gracefully to offline defaults."""
    try:
        if LLM_PROVIDER == "groq":
            return _call_groq(system_prompt, user_prompt, max_tokens, temperature)
        elif LLM_PROVIDER == "gemini":
            return _call_gemini(system_prompt, user_prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
    except Exception as exc:
        logging.error(f"[LLM ERROR] Falling back to offline default. Reason: {exc}")
        return None


def _call_groq(system_prompt, user_prompt, max_tokens, temperature):
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
        "temperature": temperature,
    }
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)
    # WHY: don't use raise_for_status() alone — it discards the response body.
    # A 404 from Groq is almost always model_not_found / model_decommissioned, and
    # the body names the offending model (which the bare status code does not).
    if resp.status_code >= 400:
        raise RuntimeError(f"Groq API {resp.status_code}: {resp.text}")
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_gemini(system_prompt, user_prompt, max_tokens, temperature):
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("PASTE_"):
        raise RuntimeError("GEMINI_API_KEY is not configured")

    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {
        "contents": [
            {"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}
        ],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
    }
    resp = requests.post(GEMINI_URL, headers=headers, params=params, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

def translate_to_english(text, source_language):
    """Translates native, Romanized (e.g., Minglish/Hinglish), or mixed input to English."""
    if not text.strip():
        return text

    system_prompt = (
        f"You are an intelligent translation engine. The user's selected language context is {source_language}. "
        "CRITICAL INSTRUCTIONS:\n"
        "1. The user may have typed their answer in the native script (e.g., Devanagari), Romanized transliteration (e.g., typing Marathi/Hindi using English letters), or plain English.\n"
        "2. If the text is ALREADY entirely in English, return it exactly as is.\n"
        "3. Otherwise, detect the meaning of the regional/Romanized text and translate it into clean, standard English.\n"
        "4. DO NOT answer the user's text. Output ONLY the English translation with no quotes or conversational filler."
    )
    
    user_prompt = f"Text to translate:\n\n<<<{text}>>>"
    
    translated = call_llm(system_prompt, user_prompt, max_tokens=150)
    
    if translated:
        return translated.replace("<<<", "").replace(">>>", "").strip()
    return text

def translate_text(text, target_language):
    """Translates UI elements to the user's selected language."""
    if not text.strip() or target_language == "English" and text.isascii():
        return text

    system_prompt = (
        f"You are an expert, culturally-aware translator. Translate the following text into natural, grammatically correct {target_language}. "
        "CRITICAL INSTRUCTIONS:\n"
        "1. The text is a memory question for an elderly person. DO NOT answer it. Your only job is to translate.\n"
        "2. Do NOT translate literally if the text contains Western-specific concepts (like 'grandfather clock'). Instead, ADAPT the concept into a natural, culturally equivalent term in the target language (e.g., 'a large old wall clock') so the nostalgia and meaning remain intact.\n"
        "3. Do not hallucinate unrelated items like computers or dreams.\n"
        "4. Output ONLY the final translated text with no quotes, conversational filler, or explanations."
    )

    user_prompt = f"Text to translate:\n\n<<<{text}>>>"

    # Low temperature: cultural adaptation still needs to stay grounded in the
    # source meaning. 0.7 gave the model too much room to invent rather than adapt.
    translated = call_llm(system_prompt, user_prompt, max_tokens=300, temperature=0.2)

    if not translated:
        logging.warning(
            f"[TRANSLATE] translate_text failed for target_language={target_language}; "
            "falling back to original (untranslated) text."
        )
        return text

    return translated.replace("<<<", "").replace(">>>", "").strip()