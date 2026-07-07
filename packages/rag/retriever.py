import logging
from typing import Any, Dict, List, Optional
from rag.vectorstore import get_vectorstore
from rag.schemas import ConceptSearchResult

logger = logging.getLogger(__name__)


def search_concepts(
    query: str, 
    top_k: int = 5, 
    filters: Optional[Dict[str, Any]] = None
) -> List[ConceptSearchResult]:
    """Queries the concept vector store for relevant concept documents.
    
    Automatically triggers concept indexing if using InMemoryVectorStore and it is empty.
    """
    store = get_vectorstore("codemaker_concepts")
    
    # Auto-index if using InMemoryVectorStore and it is empty
    if "InMemoryVectorStore" in str(type(store)):
        is_empty = True
        if hasattr(store, "store") and store.store:
            is_empty = False
        
        if is_empty:
            logger.info("Concept vector store is empty. Triggering automatic index build.")
            from rag.pipeline import build_concept_index
            build_concept_index()
            
    try:
        # Search documents with score
        results = store.similarity_search_with_score(query, k=top_k, filter=filters)
    except Exception as e:
        logger.error(f"Error searching concept vector store: {e}")
        return []
        
    output = []
    for doc, score in results:
        metadata = doc.metadata
        source_path = metadata.get("source_path", "")
        output.append(ConceptSearchResult(
            content=doc.page_content,
            metadata=metadata,
            source_path=source_path,
            score=float(score) if score is not None else None
        ))
        
    return output


def get_concept_retriever(top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> Any:
    """Returns a LangChain retriever handle for concepts."""
    store = get_vectorstore("codemaker_concepts")
    return store.as_retriever(search_kwargs={"k": top_k, "filter": filters})
