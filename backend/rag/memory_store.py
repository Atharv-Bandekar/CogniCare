import logging
from typing import List, Dict, Any
from backend.agents.embeddings import embed_text

# TODO: @schema-migration-dev Ensure these dependencies exist in `backend/database/db.py`.
# Expected Interfaces:
# def insert_memory(elder_id: str, content: str, category: str, source_interaction_id: str, embedding: List[float]) -> Dict[str, Any]:
#     """Inserts a memory into the vector store."""
# def vector_search_memories(elder_id: str, query_embedding: List[float], top_k: int) -> List[Dict[str, Any]]:
#     """Returns top_k nearest memories using cosine similarity over pgvector."""
from backend.database.db import insert_memory, vector_search_memories

logger = logging.getLogger(__name__)

def store_memory(elder_id: str, content: str, category: str, source_interaction_id: str) -> Dict[str, Any]:
    """
    Embeds memory content and stores it persistently in the pgvector database.
    
    Args:
        elder_id (str): Unique identifier for the elderly user.
        content (str): The actual memory text (e.g., "Grandson's name is Tim").
        category (str): Memory classification (people, places, events, hobbies, family_stories).
        source_interaction_id (str): The ID of the conversation where this memory was extracted.
        
    Returns:
        Dict[str, Any]: The inserted database record.
    """
    # WHY: We embed before interacting with the DB so that if the inference API fails,
    # we don't open a database transaction unnecessarily.
    logger.info(f"Generating embedding for new memory for elder {elder_id}.")
    embedding = embed_text(content)
    
    logger.info(f"Storing memory for elder {elder_id} in vector store.")
    record = insert_memory(
        elder_id=elder_id,
        content=content,
        category=category,
        source_interaction_id=source_interaction_id,
        embedding=embedding
    )
    return record

def search_memories(elder_id: str, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Performs a semantic similarity search against an elder's stored memories.
    
    Args:
        elder_id (str): Unique identifier for the elderly user.
        query_text (str): The context to search for (e.g., "Does the user have pets?").
        top_k (int): Number of most relevant memories to retrieve. Defaults to 3.
        
    Returns:
        List[Dict[str, Any]]: A list of memory records matching the semantic query.
    """
    # WHY: pgvector cosine similarity requires the search query to be embedded in the 
    # exact same vector space (same model/dimensions) as the stored records.
    logger.info(f"Embedding search query for elder {elder_id}.")
    query_embedding = embed_text(query_text)
    
    logger.info(f"Executing vector search for elder {elder_id}, requesting top {top_k} results.")
    results = vector_search_memories(elder_id, query_embedding, top_k)
    
    return results