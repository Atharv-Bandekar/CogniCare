import re
import logging

LOCAL_MODEL_NAME = "microsoft/deberta-v3-small"

class EvaluatorAgent:
    def __init__(self):
        self.pipeline = None
        self.model_ready = False
        self._load_error = None

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
        try:
            from transformers import pipeline
            self.pipeline = pipeline(
                "text-classification",
                model=LOCAL_MODEL_NAME,
                tokenizer=LOCAL_MODEL_NAME,
                top_k=None,
            )
            self.model_ready = True
            logging.info(f"[Agent 2] Loaded local model: {LOCAL_MODEL_NAME}")
        except Exception as exc:
            self._load_error = str(exc)
            self.model_ready = False
            logging.warning(f"[Agent 2] Could not load local model, using heuristic fallback. Reason: {exc}")

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
            engagement_level, engagement_score = "High", 0.9
        elif word_count >= 10:
            engagement_level, engagement_score = "Medium", 0.6
        elif word_count >= 1:
            engagement_level, engagement_score = "Low", 0.3
        else:
            engagement_level, engagement_score = "None", 0.0

        return heuristic_sentiment, engagement_level, engagement_score

    def analyze(self, text):
        heuristic_sentiment, engagement_level, engagement_score = self._heuristic_scores(text)
        model_sentiment_score = None
        model_label = None

        if self.model_ready and self.pipeline is not None:
            try:
                raw = self.pipeline(text[:512])
                scores = raw[0] if isinstance(raw[0], list) else raw
                best = max(scores, key=lambda d: d["score"])
                model_label = best["label"]
                model_sentiment_score = (best["score"] * 2) - 1
            except Exception as exc:
                logging.error(f"[Agent 2] Inference error, using heuristic only: {exc}")

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