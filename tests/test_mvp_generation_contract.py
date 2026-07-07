import pytest
from agent.schemas import (
    ProblemGenerationInput, 
    GeneratedProblem, 
    TestcaseBundle, 
    HintBundle,
    HintBlueprint
)
from agent.chains.problem_generation import generate_problem
from agent.chains.testcase_generation import generate_testcases
from agent.chains.hint_generation import generate_hints
from rag.vectorstore import _fallback_stores


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("USE_FAKE_EMBEDDINGS", "true")
    _fallback_stores.clear()


def test_problem_generation_contract():
    """Verify that generate_problem returns a valid GeneratedProblem with HintBlueprint."""
    input_data = ProblemGenerationInput(
        algorithm="binary_search",
        difficulty="medium",
        problem_style="practical",
        language="Python",
        learning_goal="parametric search",
        user_level="intermediate"
    )
    
    problem = generate_problem(input_data)
    
    assert isinstance(problem, GeneratedProblem)
    assert problem.title is not None
    assert isinstance(problem.hint_blueprint, HintBlueprint)
    assert problem.hint_blueprint.allowed_code_exposure in ["none", "skeleton_only"]


def test_testcase_generation_contract():
    """Verify that generate_testcases returns a valid TestcaseBundle with sample case using LLM fallback."""
    # Build a dummy GeneratedProblem for the function input
    input_data = ProblemGenerationInput(
        algorithm="bfs",
        difficulty="easy"
    )
    problem = generate_problem(input_data)
    
    bundle = generate_testcases(problem, allow_experimental_llm_fallback=True)
    
    assert isinstance(bundle, TestcaseBundle)
    assert bundle.problem_id == problem.problem_id
    assert len(bundle.testcases) >= 1
    # Check that it contains at least one sample testcase
    assert any(tc.visibility == "sample" for tc in bundle.testcases)


def test_testcase_generation_deterministic_contract():
    """Verify that generate_testcases returns a valid TestcaseBundle for budget cap via deterministic path."""
    input_data = ProblemGenerationInput(
        algorithm="binary_search",
        difficulty="easy"
    )
    problem = generate_problem(input_data)
    # Force statement/algorithm to match budget cap deterministic rules
    problem.statement = "상한액 C min(요청 예산, C)"
    problem.algorithm = ["binary_search"]
    
    bundle = generate_testcases(problem)
    assert isinstance(bundle, TestcaseBundle)
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "budget_cap"
    assert len(bundle.testcases) >= 5



def test_hint_generation_contract():
    """Verify that generate_hints returns a valid HintBundle and indexes the hints."""
    input_data = ProblemGenerationInput(
        algorithm="dfs",
        difficulty="hard"
    )
    problem = generate_problem(input_data)
    
    hint_bundle = generate_hints(problem, allowed_level=3)
    
    assert isinstance(hint_bundle, HintBundle)
    assert hint_bundle.problem_id == problem.problem_id
    assert len(hint_bundle.hints) >= 1
    
    # Check that they satisfy hint level requirements
    for hint in hint_bundle.hints:
        assert hint.level in [1, 2, 3]
        assert hint.reveals_core_code is False
        
    # Verify that the hints were indexed in RAG
    from rag.hint_retriever import search_hints
    retrieved = search_hints(problem_id=problem.problem_id, query="dfs", allowed_level=3)
    assert len(retrieved) >= 1
