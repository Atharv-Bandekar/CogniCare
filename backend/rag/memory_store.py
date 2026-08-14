import logging
from typing import List, Dict, Any
from backend.agents.embeddings import embed_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TODO(Phase 0): remove stub once db.py lands
# These stubs strictly match the Phase 0 contract to allow for local testing 
# without breaking the app before Member B's migration is merged.
# ---------------------------------------------------------------------------
def insert_memory(elder_id: str, content: str, category: str, embedding: list[float], source_interaction_id: str | None = None) -> dict:
    logger.warning("Using STUBBED insert_memory. Database not updated.")
    return {"id": "stub_id", "content": content}

def vector_search_memories(elder_id: str, query_embedding: list[float], top_k: int = 3) -> list[dict]:
    logger.warning("Using STUBBED vector_search_memories. Database not updated.")
    return []

def get_memories_by_elder(elder_id: str, limit: int = 50) -> list[dict]:
    logger.warning("Using STUBBED get_memories_by_elder. Database not updated.")
    return []
# ---------------------------------------------------------------------------
# End of Phase 0 Stubs
# Once Member B's code is merged, delete the stubs above and uncomment this:
# from backend.database.db import insert_memory, vector_search_memories, get_memories_by_elder
# ---------------------------------------------------------------------------

def store_memory(elder_id: str, content: str, category: str, source_interaction_id: str) -> Dict[str, Any]:
    """
    Embeds memory content and stores it persistently in the pgvector database.
    
    Args:
        elder_id (str): Unique identifier for the elderly user.
        content (str): The actual memory text.
        category (str): Memory classification.
        source_interaction_id (str): The ID of the conversation where this memory was extracted.
        
    Returns:
        Dict[str, Any]: The inserted database record.
    """
    logger.info(f"Generating embedding for new memory for elder {elder_id}.")
    embedding = embed_text(content)
    
    logger.info(f"Storing memory for elder {elder_id} in vector store.")
    
    # Note: Signature updated to match Phase 0 exact contract
    record = insert_memory(
        elder_id=elder_id,
        content=content,
        category=category,
        embedding=embedding,
        source_interaction_id=source_interaction_id
    )
    return record

def search_memories(elder_id: str, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Performs a semantic similarity search against an elder's stored memories.
    """
    logger.info(f"Embedding search query for elder {elder_id}.")
    query_embedding = embed_text(query_text)
    
    logger.info(f"Executing vector search for elder {elder_id}, requesting top {top_k} results.")
    results = vector_search_memories(elder_id, query_embedding, top_k)
    
    return results