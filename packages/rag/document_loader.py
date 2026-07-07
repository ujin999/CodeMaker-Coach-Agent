import os
from pathlib import Path
from typing import List
from langchain_core.documents import Document


def load_knowledge_documents(root_path: str = "docs/knowledge") -> List[Document]:
    """Recursively loads all markdown (.md) documents from root_path.
    
    Returns LangChain-compatible Document objects with metadata:
    - source_path
    - category (algorithm | pattern | problem_generation | hint)
    - name
    - algorithm (if inferable)
    - difficulty (if inferable)
    """
    documents = []
    base_dir = Path(root_path)
    
    if not base_dir.exists():
        return documents

    for path in base_dir.rglob("*.md"):
        if path.name == "README.md":
            continue
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Determine category based on parent folder name
        parent_name = path.parent.name
        category = parent_name if parent_name in ["algorithm", "pattern", "problem_generation", "hint"] else "unknown"
        
        name = path.stem
        
        # Infer algorithm and difficulty from metadata
        algorithm = None
        if category == "algorithm":
            algorithm = name
        elif "binary_search" in name:
            algorithm = "binary_search"
        elif "bfs" in name:
            algorithm = "bfs"
        elif "dfs" in name:
            algorithm = "dfs"
        elif "dp" in name:
            algorithm = "dp_basic"
        elif "greedy" in name:
            algorithm = "greedy"
        elif "hash" in name:
            algorithm = "hash"
        elif "two_pointer" in name:
            algorithm = "two_pointer"

        difficulty = None
        if "difficulty" in name or "easy" in content.lower() or "쉬움" in content:
            difficulty = "easy"
        if "medium" in content.lower() or "보통" in content:
            difficulty = "medium"
        if "hard" in content.lower() or "어려움" in content:
            difficulty = "hard"

        metadata = {
            "source_path": str(path.resolve()),
            "category": category,
            "name": name,
        }
        if algorithm:
            metadata["algorithm"] = algorithm
        if difficulty:
            metadata["difficulty"] = difficulty
            
        doc = Document(
            page_content=content,
            metadata=metadata
        )
        documents.append(doc)
        
    return documents
