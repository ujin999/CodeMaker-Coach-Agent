import os
import logging
from typing import Optional, List
from config.settings import settings
from rag.vectorstore import get_vectorstore
from rag.pipeline import build_concept_index

logger = logging.getLogger(__name__)


def get_vectorstore_status(collection_names: Optional[List[str]] = None) -> dict:
    """
    Return a safe status dictionary for configured vector stores.
    Do not raise if Qdrant is unavailable.
    Do not expose qdrant_api_key or secrets.

    Return shape:
    {
        "qdrant_url": "...",
        "using_fallback": bool,
        "collections": {
            "codemaker_concepts": {
                "status": "available" | "fallback" | "error",
                "vectorstore_type": "...",
                "error": None | "..."
            },
            ...
        }
    }
    """
    if collection_names is None:
        collection_names = ["codemaker_concepts", "codemaker_hints"]

    qdrant_url = settings.qdrant_url
    collections_info = {}
    using_fallback = False

    for name in collection_names:
        status = "available"
        vectorstore_type = "unknown"
        error_msg = None

        try:
            store = get_vectorstore(name)
            vectorstore_type = type(store).__name__
            if "InMemoryVectorStore" in vectorstore_type:
                # Determine if it's fallback or intended mock/local memory store
                is_intended_mock = (
                    not settings.qdrant_url or
                    settings.qdrant_url == "mock" or
                    os.getenv("ENV") == "test" or
                    os.getenv("USE_FAKE_EMBEDDINGS") == "true"
                )
                if not is_intended_mock:
                    status = "fallback"
                    using_fallback = True
                else:
                    status = "fallback"
            else:
                status = "available"
        except Exception as e:
            status = "error"
            error_msg = str(e)

        collections_info[name] = {
            "status": status,
            "vectorstore_type": vectorstore_type,
            "error": error_msg
        }

    # If any is fallback, set using_fallback to True
    if any(info["status"] == "fallback" for info in collections_info.values()):
        using_fallback = True

    return {
        "qdrant_url": qdrant_url,
        "using_fallback": using_fallback,
        "collections": collections_info
    }


def bootstrap_rag_indexes(
    knowledge_root: str = "docs/knowledge",
    force_rebuild: bool = False,
) -> dict:
    """
    Build concept index using existing build_concept_index().
    Do not directly modify infra.
    Do not require Qdrant to be running.
    If Qdrant is unavailable, fallback should still work.

    Return:
    {
        "concept_index_built": bool,
        "collection_name": "codemaker_concepts",
        "vectorstore_type": "...",
        "fallback_used": bool,
        "error": None | "..."
    }
    """
    concept_index_built = False
    vectorstore_type = "unknown"
    fallback_used = False
    error_msg = None

    try:
        store = build_concept_index(root_path=knowledge_root, force_rebuild=force_rebuild)
        vectorstore_type = type(store).__name__
        if "InMemoryVectorStore" in vectorstore_type:
            fallback_used = True
        concept_index_built = True
    except Exception as e:
        error_msg = str(e)

    return {
        "concept_index_built": concept_index_built,
        "collection_name": "codemaker_concepts",
        "vectorstore_type": vectorstore_type,
        "fallback_used": fallback_used,
        "error": error_msg
    }
