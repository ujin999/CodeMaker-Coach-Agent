import os
import logging
from typing import Any
from config.settings import settings
from rag.embeddings import get_embedding_model
from langchain_core.vectorstores import InMemoryVectorStore

logger = logging.getLogger(__name__)

# Singletons for fallback in-memory stores to persist documents during run lifetime
_fallback_stores = {}


def get_fallback_vectorstore(collection_name: str, embedding_model: Any) -> InMemoryVectorStore:
    """Returns a persisted InMemoryVectorStore singleton for the collection name."""
    if collection_name not in _fallback_stores:
        _fallback_stores[collection_name] = InMemoryVectorStore(embedding=embedding_model)
    return _fallback_stores[collection_name]


def get_vectorstore(collection_name: str) -> Any:
    """Returns the Qdrant vector store or falls back to InMemoryVectorStore if Qdrant is offline or in test mode.
    
    Collection names:
    - codemaker_concepts
    - codemaker_hints
    """
    embedding_model = get_embedding_model()
    
    # Check for test env or forced fake embeddings
    if (
        os.getenv("ENV") == "test" or 
        os.getenv("USE_FAKE_EMBEDDINGS") == "true" or 
        settings.qdrant_url == "mock" or 
        not settings.qdrant_url
    ):
        return get_fallback_vectorstore(collection_name, embedding_model)

    try:
        from langchain_qdrant import QdrantVectorStore
        from qdrant_client import QdrantClient
        
        # Test client connection with a 1 second timeout
        client = QdrantClient(
            url=settings.qdrant_url, 
            api_key=settings.qdrant_api_key or None,
            timeout=1.0
        )
        
        # Ping the server
        client.get_collections()
        
        # Initialize and return QdrantVectorStore
        return QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embedding_model,
        )
    except Exception as e:
        logger.warning(
            f"Qdrant connection failed ({e}). Falling back to InMemoryVectorStore."
        )
        return get_fallback_vectorstore(collection_name, embedding_model)
