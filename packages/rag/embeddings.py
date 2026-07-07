from typing import Any
from agent.llm import get_embedding_model as agent_get_embedding_model


def get_embedding_model() -> Any:
    """Returns the configured embedding model (real or fake/local fallback)."""
    return agent_get_embedding_model()
