from langchain_core.tools import tool
from rag.retriever import search_concepts


@tool
def retrieve_concepts_tool(query: str, top_k: int = 5) -> str:
    """Searches algorithm concepts and solving pattern documents for relevant guidelines.
    
    Args:
        query: Search term or question about algorithms/patterns.
        top_k: Number of relevant snippets to return.
        
    Returns:
        Formatted string containing retrieved snippets and source paths.
    """
    results = search_concepts(query, top_k=top_k)
    if not results:
        return "No relevant concepts found."
        
    formatted = []
    for r in results:
        formatted.append(
            f"Source: {r.source_path}\n"
            f"Content: {r.content}"
        )
    return "\n\n---\n\n".join(formatted)
