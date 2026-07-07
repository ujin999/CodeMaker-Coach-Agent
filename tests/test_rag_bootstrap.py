import os
import pytest
from rag.bootstrap import get_vectorstore_status, bootstrap_rag_indexes
from rag import get_vectorstore_status as root_get_status, bootstrap_rag_indexes as root_bootstrap


def test_imports_from_rag_root():
    """Test E: functions import from rag package root."""
    assert root_get_status is get_vectorstore_status
    assert root_bootstrap is bootstrap_rag_indexes


def test_vectorstore_status_reports_fallback(monkeypatch):
    """Test A: With USE_FAKE_EMBEDDINGS=true and QDRANT_URL=mock, get_vectorstore_status reports fallback."""
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("USE_FAKE_EMBEDDINGS", "true")
    from config.settings import settings
    monkeypatch.setattr(settings, "qdrant_url", "mock")

    status = get_vectorstore_status()
    assert status["using_fallback"] is True
    assert status["qdrant_url"] == "mock"
    assert status["collections"]["codemaker_concepts"]["status"] == "fallback"
    assert "InMemoryVectorStore" in status["collections"]["codemaker_concepts"]["vectorstore_type"]


def test_bootstrap_rag_indexes_returns_summary(monkeypatch):
    """Test B: bootstrap_rag_indexes returns concept_index_built true or non-error fallback summary when docs exist."""
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("USE_FAKE_EMBEDDINGS", "true")

    summary = bootstrap_rag_indexes(knowledge_root="docs/knowledge", force_rebuild=True)
    assert summary["concept_index_built"] is True
    assert summary["collection_name"] == "codemaker_concepts"
    assert summary["fallback_used"] is True
    assert summary["error"] is None


def test_bootstrap_does_not_raise_when_qdrant_unavailable(monkeypatch):
    """Test C: bootstrap does not raise when Qdrant is unavailable."""
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("USE_FAKE_EMBEDDINGS", "false")
    from config.settings import settings
    monkeypatch.setattr(settings, "qdrant_url", "http://localhost:9999")

    try:
        summary = bootstrap_rag_indexes(knowledge_root="docs/knowledge", force_rebuild=True)
        assert summary["fallback_used"] is True
        assert summary["error"] is None
    except Exception as e:
        pytest.fail(f"bootstrap_rag_indexes raised an exception: {e}")


def test_qdrant_api_key_not_exposed(monkeypatch):
    """Test D: qdrant_api_key is not included in returned status."""
    from config.settings import settings
    monkeypatch.setattr(settings, "qdrant_api_key", "secret-key-12345")

    status = get_vectorstore_status()
    status_str = str(status)
    assert "secret-key-12345" not in status_str
