import pytest
from agent.schemas import Hint, HintBlueprint, HintBundle
from rag.hint_retriever import build_hint_index, search_hints
from rag.vectorstore import _fallback_stores


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("USE_FAKE_EMBEDDINGS", "true")
    _fallback_stores.clear()


def test_hint_retrieval_allowed_level_policy():
    """Verify that hints are correctly filtered according to allowed_level."""
    problem_id = "test_prob_123"
    
    # 1. Create a blueprint
    blueprint = HintBlueprint(
        intended_algorithm=["binary_search"],
        core_insight="Insight",
        common_misconceptions=[],
        edge_case_focus=[],
        forbidden_disclosures=[],
        level_1_guidance="L1 guide",
        level_2_guidance="L2 guide",
        level_3_guidance="L3 guide",
        allowed_code_exposure="none"
    )
    
    # 2. Create Level 1, 2, and 3 Hints
    hints = [
        Hint(
            problem_id=problem_id,
            level=1,
            title="Hint 1",
            content="Think about dividing the range.",
            reveals_core_code=False
        ),
        Hint(
            problem_id=problem_id,
            level=2,
            title="Hint 2",
            content="Use binary search approach.",
            reveals_core_code=False
        ),
        Hint(
            problem_id=problem_id,
            level=3,
            title="Hint 3",
            content="Check boundaries carefully.",
            reveals_core_code=False,
            code_skeleton="def check(mid):\n    pass # TODO"
        )
    ]
    
    hint_bundle = HintBundle(
        problem_id=problem_id,
        blueprint=blueprint,
        hints=hints
    )
    
    # 3. Index hints
    build_hint_index(hint_bundle)
    
    # 4. Search with allowed_level=1
    results_l1 = search_hints(problem_id=problem_id, query="stuck", allowed_level=1)
    # Check that only Level 1 is returned
    assert len(results_l1) == 1
    assert int(results_l1[0].metadata["hint_level"]) == 1
    
    # 5. Search with allowed_level=2
    results_l2 = search_hints(problem_id=problem_id, query="stuck", allowed_level=2)
    # Level 3 must not be returned
    assert len(results_l2) == 2
    levels_returned = [int(doc.metadata["hint_level"]) for doc in results_l2]
    assert 3 not in levels_returned
    assert 1 in levels_returned
    assert 2 in levels_returned
    
    # 6. Check that reveals_core_code is False for all
    for doc in results_l2:
        assert doc.metadata["reveals_core_code"] is False
