from langchain_core.tools import tool
from rag.hint_retriever import search_hints


@tool
def retrieve_hints_tool(problem_id: str, query: str, allowed_level: int, top_k: int = 3) -> str:
    """Searches generated hints for a specific problem, matching the allowed level.
    
    Args:
        problem_id: Unique identifier of the problem.
        query: Specific context or question about the user's issue.
        allowed_level: Maximum level of hint allowed to be returned (1, 2, or 3).
        top_k: Number of hints to return.
        
    Returns:
        Formatted string containing safe, allowed-level hints.
    """
    results = search_hints(problem_id=problem_id, query=query, allowed_level=allowed_level, top_k=top_k)
    if not results:
        return "No relevant hints found within the allowed level."
        
    formatted = []
    for doc in results:
        meta = doc.metadata
        formatted.append(
            f"Hint Level: {meta.get('hint_level')}\n"
            f"Content: {doc.page_content}"
        )
    return "\n\n---\n\n".join(formatted)
