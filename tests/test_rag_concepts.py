import pytest
from rag.retriever import search_concepts
from rag.vectorstore import _fallback_stores


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Enforce test environment settings."""
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("USE_FAKE_EMBEDDINGS", "true")
    # Reset fallback in-memory stores to ensure fresh indexing
    _fallback_stores.clear()


def test_rag_concepts_binary_search():
    """Query '이분 탐색' and verify binary_search.md is returned."""
    results = search_concepts("이분 탐색", top_k=5)
    assert len(results) > 0
    
    # Check if binary_search.md is in results
    found = False
    for r in results:
        if "binary_search" in r.metadata.get("name", ""):
            found = True
            break
    assert found, "binary_search.md was not retrieved for query '이분 탐색'"


def test_rag_concepts_time_complexity():
    """Query '시간 초과 O(N^2)' and verify time_complexity.md is returned."""
    results = search_concepts("시간 초과 O(N^2)", top_k=5)
    assert len(results) > 0
    
    # Check if time_complexity.md is in results
    found = False
    for r in results:
        if "time_complexity" in r.metadata.get("name", ""):
            found = True
            break
    assert found, "time_complexity.md was not retrieved for query '시간 초과 O(N^2)'"
