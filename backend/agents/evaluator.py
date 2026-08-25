"""
Agent 2 — Evaluator.

Analyzes an elder's response transcript and produces a structured insight that maps
1:1 onto the `interaction_insights` table (sentiment, engagement, response depth,
conversation topics, and a non-clinical safety flag).

Phase 3A public contract:
    evaluate_response(transcript: str) -> dict

The returned dict is a strict superset of the keys consumed downstream by the
Coordinator agent (`engagement_level`, `sentiment_label`, `topics`, `safety_flag`)
and the weekly report generator.

HARD RULE (non-clinical): this agent NEVER diagnoses. `safety_flag` means only
"a caregiver may want to check in" — it is not a medical assessment.
"""
import os
import re
import logging
import requests

logger = logging.getLogger(__name__)

# Pointing exactly to the DeBERTa-v3-small model on the Hugging Face Inference API
HF_MODEL_NAME = "microsoft/deberta-v3-small"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL_NAME}"

# Acute distress / wellbeing signals that warrant a gentle caregiver check-in.
# WHY: These are intentionally NON-CLINICAL. A hit sets safety_flag=True, which the
# Coordinator turns into a soft "consider checking in" nudge — never a diagnosis.
SAFETY_KEYWORDS = {
    "fell", "fall", "fallen", "help", "emergency", "ambulance", "hospital",
    "dizzy", "faint", "fainted", "bleeding", "blood", "collapse", "collapsed",
}
SAFETY_PHRASES = (
    "chest pain", "can't breathe", "cannot breathe", "can't get up",
    "cannot get up", "can't move", "cannot move", "hurts a lot",
)

# High-frequency words excluded from topic extraction so `topics` surfaces
# the actual subjects the elder talked about (people, places, activities).
STOPWORDS = {
    "the", "and", "was", "were", "have", "has", "had", "that", "this", "with",
    "they", "them", "then", "than", "there", "here", "what", "when", "which",
    "your", "yours", "you", "our", "ours", "for", "from", "not", "but", "are",
    "were", "been", "being", "about", "just", "very", "really", "some", "any",
    "all", "one", "two", "into", "over", "back", "much", "more", "most", "will",
    "would", "could", "should", "did", "does", "done", "get", "got", "still",
    "today", "yesterday", "day", "days", "time", "like", "well", "good", "yeah",
    "okay", "know", "think", "feel", "felt", "went", "come", "came", "said",
    "her", "his", "she", "him", "who", "how", "why", "its", "his", "out",
}


class EvaluatorAgent:
    """Hybrid evaluator: fast heuristics always run; HF Inference API refines sentiment
    when a key is present. Falls back gracefully to heuristics on any API issue."""

    def __init__(self):
        self.model_ready = False
        self.api_key = None
        self.headers = {}

        self.POSITIVE_WORDS = {
            "happy", "love", "loved", "wonderful", "great", "joy", "fun",
            "beautiful", "warm", "laugh", "laughed", "smile", "smiled", "proud",
            "excited", "peaceful", "grateful", "good", "best", "favorite",
        }
        self.NEGATIVE_WORDS = {
            "sad", "lonely", "hard", "difficult", "cry", "cried", "miss", "missed",
            "afraid", "scared", "tired", "angry", "hurt", "bad", "worried",
            "lost", "pain", "sick",
        }

    def load_model(self):
        """Prepares the lightweight HF Inference API connection headers.
        Does NOT load a local model — sentiment refinement is a remote HTTP call."""
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        if self.api_key:
            self.headers = {"Authorization": f"Bearer {self.api_key}"}
            self.model_ready = True
            logger.info(f"[Agent 2] Connected to Hugging Face Inference API for {HF_MODEL_NAME}")
        else:
            self.model_ready = False
            logger.warning("[Agent 2] Missing HUGGINGFACE_API_KEY. Falling back to heuristic scoring.")

    # ------------------------------------------------------------------
    # Heuristic building blocks
    # ------------------------------------------------------------------
    def _heuristic_scores(self, text):
        """Returns (sentiment[-1..1], engagement_level, engagement_score, response_depth).

        Engagement labels are lowercase to match the DB schema comment
        (`engagement_level -- low/medium/high`) and the escalation contract."""
        words = re.findall(r"[a-zA-Z']+", text.lower())
        word_count = len(words)
        pos_hits = sum(1 for w in words if w in self.POSITIVE_WORDS)
        neg_hits = sum(1 for w in words if w in self.NEGATIVE_WORDS)

        if pos_hits + neg_hits > 0:
            heuristic_sentiment = (pos_hits - neg_hits) / (pos_hits + neg_hits)
        else:
            heuristic_sentiment = 0.0

        if word_count >= 25:
            engagement_level, engagement_score, response_depth = "high", 0.9, "deep"
        elif word_count >= 10:
            engagement_level, engagement_score, response_depth = "medium", 0.6, "moderate"
        elif word_count >= 1:
            engagement_level, engagement_score, response_depth = "low", 0.3, "brief"
        else:
            engagement_level, engagement_score, response_depth = "none", 0.0, "none"

        return heuristic_sentiment, engagement_level, engagement_score, response_depth

    def _extract_topics(self, text, max_topics=5):
        """Lightweight keyword extraction: content words by frequency, stopwords removed.
        Deterministic (freq desc, then first-appearance) so tests are stable."""
        words = re.findall(r"[a-zA-Z']+", text.lower())
        freq = {}
        order = {}
        for idx, w in enumerate(words):
            if len(w) >= 4 and w not in STOPWORDS:
                freq[w] = freq.get(w, 0) + 1
                order.setdefault(w, idx)
        ranked = sorted(freq.keys(), key=lambda w: (-freq[w], order[w]))
        return ranked[:max_topics]

    def _detect_safety(self, text):
        """Non-clinical acute-distress detector. Returns bool for safety_flag."""
        low = text.lower()
        for phrase in SAFETY_PHRASES:
            if phrase in low:
                return True
        tokens = set(re.findall(r"[a-zA-Z']+", low))
        return bool(tokens & SAFETY_KEYWORDS)

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------
    def analyze(self, text):
        """Produce the full insight dict for a transcript (maps to interaction_insights)."""
        text = text or ""
        heuristic_sentiment, engagement_level, engagement_score, response_depth = self._heuristic_scores(text)
        topics = self._extract_topics(text)
        safety_flag = self._detect_safety(text)

        model_sentiment_score = None
        model_label = None

        if self.model_ready and text.strip():
            try:
                response = requests.post(
                    HF_API_URL,
                    headers=self.headers,
                    json={"inputs": text[:512]},
                    timeout=10,
                )

                if response.status_code == 200:
                    raw = response.json()
                    # HF API usually returns lists of lists: [[{'label': 'LABEL', 'score': 0.9}]]
                    scores = raw[0] if isinstance(raw, list) and raw and isinstance(raw[0], list) else raw
                    if isinstance(scores, list) and scores:
                        best = max(scores, key=lambda d: d.get("score", 0))
                        model_label = best.get("label")
                        # Normalize the score to a -1.0 .. 1.0 range for the hybrid blend
                        model_sentiment_score = (best.get("score", 0.5) * 2) - 1
                elif response.status_code == 503:
                    logger.warning("[Agent 2] HF Model is waking up. Using heuristic for now.")
                else:
                    logger.warning(f"[Agent 2] HF API returned {response.status_code}: {response.text}")

            except Exception as exc:
                logger.error(f"[Agent 2] API Inference error, using heuristic only: {exc}")

        # 70/30 blend: heuristic dominates, model refines when available
        if model_sentiment_score is not None:
            final_sentiment_score = round(0.3 * model_sentiment_score + 0.7 * heuristic_sentiment, 3)
        else:
            final_sentiment_score = round(heuristic_sentiment, 3)

        if final_sentiment_score > 0.15:
            sentiment_label = "positive"
        elif final_sentiment_score < -0.15:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        return {
            "sentiment_label": sentiment_label,
            "sentiment_score": final_sentiment_score,
            "engagement_level": engagement_level,
            "engagement_score": engagement_score,
            "response_depth": response_depth,
            "topics": topics,
            "safety_flag": safety_flag,
            "raw_model_label": model_label,
        }


# ----------------------------------------------------------------------
# Module-level singleton + public Phase 3A contract
# ----------------------------------------------------------------------
_agent = None


def _get_agent():
    """Lazily builds a single EvaluatorAgent so the HF headers are prepared once
    and reused across Celery task invocations."""
    global _agent
    if _agent is None:
        _agent = EvaluatorAgent()
        _agent.load_model()
    return _agent


def evaluate_response(transcript: str) -> dict:
    """
    Evaluate an elder's response and return a structured insight.

    Args:
        transcript (str): The elder's (transcribed) reply for today's interaction.

    Returns:
        dict: {
            sentiment_label:  "positive" | "neutral" | "negative",
            sentiment_score:  float  (-1.0 .. 1.0),
            engagement_level: "high" | "medium" | "low" | "none",
            engagement_score: float  (0.0 .. 1.0),
            response_depth:   "deep" | "moderate" | "brief" | "none",
            topics:           list[str]  (conversation keywords),
            safety_flag:      bool  (non-clinical "consider a check-in" signal),
            raw_model_label:  str | None  (HF label, for traceability),
        }
    """
    return _get_agent().analyze(transcript or "")
