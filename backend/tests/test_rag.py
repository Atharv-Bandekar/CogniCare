import pytest
from unittest.mock import patch, MagicMock
import json

from backend.agents.embeddings import embed_text
from backend.rag.memory_store import store_memory, search_memories
from backend.rag.memory_extraction import extract_memorable_content

# WHY: We mock os.environ globally for tests to prevent local dev setups 
# from leaking into the test assertions.
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict("os.environ", {"HUGGINGFACE_API_KEY": "fake_hf_key", "GROQ_API_KEY": "fake_groq_key"}):
        yield

# --- Test Embeddings ---

@patch("backend.agents.embeddings.requests.post")
def test_embed_text_success(mock_post):
    """Tests that a successful HF API call returns a flat list of floats."""
    # Mocking standard nested list response from Hugging Face feature extraction pipeline
    mock_post.return_value.json.return_value = [[0.1, 0.2, 0.3]]
    mock_post.return_value.raise_for_status = MagicMock()
    
    result = embed_text("I love gardening.")
    
    assert result == [0.1, 0.2, 0.3]
    mock_post.assert_called_once()

@patch("backend.agents.embeddings.requests.post")
def test_embed_text_retries(mock_post):
    """Tests that the retry mechanism correctly raises an error after 3 failures."""
    import requests
    mock_post.side_effect = requests.exceptions.RequestException("API down")
    
    with pytest.raises(RuntimeError):
        # WHY: Fast-forwarding time.sleep isn't strictly necessary here if we mock the side_effect,
        # but in a deeper suite we would patch `time.sleep` to keep tests blazing fast.
        with patch("time.sleep"): 
            embed_text("Fail me")
            
    assert mock_post.call_count == 3

# --- Test Memory Store ---

@patch("backend.rag.memory_store.embed_text")
@patch("backend.rag.memory_store.insert_memory")
def test_store_memory(mock_insert, mock_embed):
    """Tests the round trip of embedding and saving a memory record."""
    mock_embed.return_value = [0.5] * 384
    mock_insert.return_value = {"id": "123", "content": "Test"}
    
    result = store_memory("elder_1", "Loves tea", "hobbies", "interaction_99")
    
    mock_embed.assert_called_once_with("Loves tea")
    mock_insert.assert_called_once_with(
        elder_id="elder_1", 
        content="Loves tea", 
        category="hobbies", 
        source_id="interaction_99", 
        embedding=[0.5] * 384
    )
    assert result["id"] == "123"

@patch("backend.rag.memory_store.embed_text")
@patch("backend.rag.memory_store.vector_search_memories")
def test_search_memories(mock_search, mock_embed):
    """Tests that vector search correctly passes the query embedding to the DB."""
    mock_embed.return_value = [0.1] * 384
    mock_search.return_value = [{"content": "Has a dog"}]
    
    results = search_memories("elder_1", "Pets?", top_k=2)
    
    mock_embed.assert_called_once_with("Pets?")
    mock_search.assert_called_once_with("elder_1", [0.1] * 384, 2)
    assert len(results) == 1
    assert results[0]["content"] == "Has a dog"

# --- Test Memory Extraction ---

@patch("backend.rag.memory_extraction.client.chat.completions.create")
def test_extract_memorable_content(mock_groq_create):
    """Tests that the Groq LLM JSON payload is parsed into a clean memory list."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "memories": [
            {"content": "Daughter's name is Sarah.", "category": "people"}
        ]
    })
    mock_groq_create.return_value = mock_response
    
    transcript = "My daughter Sarah visited me today. My back was hurting."
    results = extract_memorable_content(transcript, ["gardening"])
    
    assert len(results) == 1
    assert results[0]["category"] == "people"
    assert "Sarah" in results[0]["content"]
    
    # Verify the medical info was not extracted (based on our prompt rules testing logic).
    # Since we are mocking the response, we just ensure the mock setup returns cleanly.
    mock_groq_create.assert_called_once()
    
    # WHY: We specifically assert the 'temperature' argument to ensure the extraction is deterministic.
    _, kwargs = mock_groq_create.call_args
    assert kwargs["temperature"] == 0.1
    assert kwargs["response_format"] == {"type": "json_object"}