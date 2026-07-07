from typing import Any


def get_embedding_model() -> Any:
    """Returns the configured embedding model (real or fake/local fallback)."""
    from agent.llm import get_embedding_model as agent_get_embedding_model
    return agent_get_embedding_model()
