from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ConceptSearchResult(BaseModel):
    """Schema for returned Concept RAG results."""
    content: str
    metadata: Dict[str, Any]
    source_path: str
    score: Optional[float] = None
