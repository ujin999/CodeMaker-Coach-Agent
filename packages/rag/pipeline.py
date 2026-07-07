import logging
from typing import Any
from rag.document_loader import load_knowledge_documents
from rag.splitter import split_documents
from rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

# Tracking index status
_concepts_indexed = False


def build_concept_index(root_path: str = "docs/knowledge", force_rebuild: bool = False) -> Any:
    """Loads knowledge documents, splits them, and stores them in the concept vector store.
    
    Supports fallback to InMemoryVectorStore.
    """
    global _concepts_indexed
    
    store = get_vectorstore("codemaker_concepts")
    is_in_memory = "InMemoryVectorStore" in str(type(store))
    
    # Avoid duplicate indexing if already done (unless force_rebuild is requested)
    if not force_rebuild and not is_in_memory and _concepts_indexed:
        return store
        
    try:
        docs = load_knowledge_documents(root_path)
        if not docs:
            logger.warning(f"No documents found at {root_path}")
            return store
            
        chunks = split_documents(docs)
        
        # If in-memory and force_rebuild, clear existing storage
        if is_in_memory and force_rebuild:
            if hasattr(store, "store"):
                store.store.clear()
                
        if chunks:
            store.add_documents(chunks)
            logger.info(f"Successfully indexed {len(chunks)} chunks into concept vectorstore.")
            
        _concepts_indexed = True
    except Exception as e:
        logger.error(f"Failed to build concept index: {e}")
        
    return store
