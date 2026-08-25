import os
import time
import logging
import requests
from typing import List

logger = logging.getLogger(__name__)

# WHY: We use a specific sentence-transformer model that outputs 384 dimensions,
# perfectly matching our pgvector column configuration for efficient memory retrieval.
HF_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

# WHY: Hugging Face retired the legacy `api-inference.huggingface.co` host and
# moved serverless inference behind the provider router at `router.huggingface.co`.
# The old subdomain no longer resolves in DNS, so the legacy URL fails with a
# name-resolution error before any request is even sent. The current path is
# /hf-inference/models/{model}/pipeline/{task}.
HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL_ID}/pipeline/feature-extraction"

def embed_text(text: str) -> List[float]:
    """
    Generates a 384-dimensional text embedding using the Hugging Face Inference API.
    
    Args:
        text (str): The raw text to embed (e.g., a memory or search query).
        
    Returns:
        List[float]: A list of floats representing the text embedding.
        
    Raises:
        RuntimeError: If the API fails after all retry attempts.
    """
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        # WHY: Fail fast if the environment isn't properly configured to avoid silent data drops.
        raise ValueError("HUGGINGFACE_API_KEY environment variable is missing.")

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"inputs": text, "options": {"wait_for_model": True}}

    max_retries = 3
    base_delay = 2.0

    # WHY: The HF free inference API can aggressively rate-limit or experience cold starts.
    # Exponential backoff ensures we give the model time to load into memory without crashing the worker.
    for attempt in range(max_retries):
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            # The pipeline/feature-extraction endpoint returns a 1D or 2D list depending on input shape.
            # We enforce returning a flat 1D list of floats.
            embeddings = response.json()
            if isinstance(embeddings, list) and isinstance(embeddings[0], list):
                return embeddings[0]
            return embeddings
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"HF API attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
            else:
                logger.error("All retries exhausted for HF Inference API.")
                raise RuntimeError(f"Failed to generate embedding: {e}") from e