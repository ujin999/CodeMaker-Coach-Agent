import logging
from typing import Any, List, Union
from langchain_core.documents import Document
from rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)


def build_hint_index(hint_bundle_or_hints: Any) -> Any:
    """Indexes generated hints into the hint vector store.
    
    Accepts HintBundle or a list of Hint objects.
    """
    store = get_vectorstore("codemaker_hints")
    
    # Check if input is HintBundle
    if hasattr(hint_bundle_or_hints, "hints"):
        hints = hint_bundle_or_hints.hints
    else:
        hints = hint_bundle_or_hints
        
    documents = []
    for hint in hints:
        # Determine values
        problem_id = getattr(hint, "problem_id", "")
        level = getattr(hint, "level", 1)
        reveals_core_code = getattr(hint, "reveals_core_code", False)
        source = getattr(hint, "source", "generated")
        concept_refs = getattr(hint, "concept_refs", [])
        title = getattr(hint, "title", f"Level {level} Hint")
        content = getattr(hint, "content", "")
        code_skeleton = getattr(hint, "code_skeleton", None)
        
        # Build page content containing title, content and skeleton if available
        page_content = f"Title: {title}\nContent: {content}"
        if code_skeleton:
            page_content += f"\nCode Skeleton:\n{code_skeleton}"
            
        metadata = {
            "problem_id": problem_id,
            "hint_level": int(level),
            "reveals_core_code": bool(reveals_core_code),
            "source": source,
            "concept_refs": concept_refs,
        }
        
        doc = Document(page_content=page_content, metadata=metadata)
        documents.append(doc)
        
    if documents:
        store.add_documents(documents)
        logger.info(f"Indexed {len(documents)} hints into hint vector store.")
        
    return store


def search_hints(
    problem_id: str, 
    query: str, 
    allowed_level: int, 
    top_k: int = 3
) -> List[Document]:
    """Searches and filters hints for a specific problem and allowed level.
    
    Enforces strict allowed_level and reveals_core_code == False filtering.
    """
    store = get_vectorstore("codemaker_hints")
    
    # Search all candidates for this problem_id.
    # We query for top_k * 3 to retrieve enough candidates, then filter by problem_id.
    # In langchain vector stores, we can pass metadata filters.
    # To be extremely platform-agnostic, we can query with filter of problem_id == problem_id.
    filters = {"problem_id": problem_id}
    
    try:
        results = store.similarity_search(query, k=top_k * 3, filter=filters)
    except Exception as e:
        logger.error(f"Error querying hints vector store: {e}")
        # Try without metadata filter and manually filter problem_id in Python as absolute fallback
        try:
            results = store.similarity_search(query, k=top_k * 10)
        except Exception:
            return []

    # Perform strict Python-side filtering before returning to the LLM (retrieval-level filtering)
    filtered_results = []
    for doc in results:
        meta = doc.metadata
        
        # Check problem_id match
        if meta.get("problem_id") != problem_id:
            continue
            
        # Check hint_level <= allowed_level
        hint_level = meta.get("hint_level")
        if hint_level is None or int(hint_level) > allowed_level:
            continue
            
        # Check reveals_core_code == False
        if meta.get("reveals_core_code", False):
            continue
            
        filtered_results.append(doc)
        
    # Cap to requested top_k
    filtered_results = filtered_results[:top_k]
    
    # Defensive assertions to prevent any leakage
    for doc in filtered_results:
        meta = doc.metadata
        assert int(meta["hint_level"]) <= allowed_level, (
            f"Leakage: Hint level {meta['hint_level']} exceeds allowed_level {allowed_level}"
        )
        assert meta["reveals_core_code"] is False, (
            "Leakage: Hint contains reveals_core_code == True"
        )
        
    return filtered_results
