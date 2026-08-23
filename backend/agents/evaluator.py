import os
import re
import logging
import requests

# Pointing exactly to the DeBERTa-v3-small model on the Hugging Face Inference API
HF_MODEL_NAME = "microsoft/deberta-v3-small"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL_NAME}"

class EvaluatorAgent:
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
        """
        This no longer loads a 2.5GB model into RAM! 
        Instead, it just prepares the lightweight API connection headers.
        """
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        if self.api_key:
            self.headers = {"Authorization": f"Bearer {self.api_key}"}
            self.model_ready = True
            logging.info(f"[Agent 2] Connected to Hugging Face Inference API for {HF_MODEL_NAME}")
        else:
            self.model_ready = False
            logging.warning("[Agent 2] Missing HUGGINGFACE_API_KEY. Falling back to heuristic scoring.")

    def _heuristic_scores(self, text):
        words = re.findall(r"[a-zA-Z']+", text.lower())
        word_count = len(words)
        pos_hits = sum(1 for w in words if w in self.POSITIVE_WORDS)
        neg_hits = sum(1 for w in words if w in self.NEGATIVE_WORDS)

        if pos_hits + neg_hits > 0:
            heuristic_sentiment = (pos_hits - neg_hits) / (pos_hits + neg_hits)
        else:
            heuristic_sentiment = 0.0

        if word_count >= 25:
            engagement_level, engagement_score = "high", 0.9
        elif word_count >= 10:
            engagement_level, engagement_score = "medium", 0.6
        elif word_count >= 1:
            engagement_level, engagement_score = "low", 0.3
        else:
            engagement_level, engagement_score = "none", 0.0

        return heuristic_sentiment, engagement_level, engagement_score

    def analyze(self, text):
        heuristic_sentiment, engagement_level, engagement_score = self._heuristic_scores(text)
        model_sentiment_score = None
        model_label = None

        if self.model_ready:
            try:
                # Make a lightning-fast HTTP request instead of local inference
                response = requests.post(
                    HF_API_URL, 
                    headers=self.headers, 
                    json={"inputs": text[:512]},
                    timeout=10
                )
                
                if response.status_code == 200:
                    raw = response.json()
                    # HF API usually returns lists of lists: [[{'label': 'LABEL', 'score': 0.9}]]
                    scores = raw[0] if isinstance(raw, list) and isinstance(raw[0], list) else raw
                    
                    if isinstance(scores, list):
                        best = max(scores, key=lambda d: d.get("score", 0))
                        model_label = best.get("label")
                        # Normalize the score to a -1.0 to 1.0 range for your hybrid calculation
                        model_sentiment_score = (best.get("score", 0.5) * 2) - 1
                elif response.status_code == 503:
                    # 503 means the free tier model is currently waking up, gracefully fall back
                    logging.warning("[Agent 2] HF Model is waking up. Using heuristic for now.")
                else:
                    logging.warning(f"[Agent 2] HF API returned {response.status_code}: {response.text}")
            
            except Exception as exc:
                logging.error(f"[Agent 2] API Inference error, using heuristic only: {exc}")

        # Your exact 70/30 weight integration
        if model_sentiment_score is not None:
            final_sentiment_score = round(0.3 * model_sentiment_score + 0.7 * heuristic_sentiment, 3)
        else:
            final_sentiment_score = round(heuristic_sentiment, 3)

        if final_sentiment_score > 0.15:
            sentiment_label = "Positive"
        elif final_sentiment_score < -0.15:
            sentiment_label = "Negative"
        else:
            sentiment_label = "Neutral"

        return {
            "sentiment_label": sentiment_label,
            "sentiment_score": final_sentiment_score,
            "engagement_level": engagement_level,
            "engagement_score": engagement_score,
            "raw_model_label": model_label,
        }