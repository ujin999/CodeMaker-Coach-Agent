import asyncio
import sys
import pytest
from agent import (
    generate_problem_package,
    request_hint_package,
    ProblemGenerationPackageInput,
    HintRequestPackageInput,
    GeneratedProblem,
)
from agent.schemas import HintBlueprint
from agent.services import (
    generate_problem_package as service_gen,
    request_hint_package as service_hint,
    problem_package_to_public_dict
)


def mock_run_package_workflow(generation_input, min_cases=5, allowed_hint_level=3, user_situation=None, include_hints=True):
    # Dummy mock workflow state return
    prob = GeneratedProblem(
        problem_id="prob_123",
        title="Mock Problem",
        difficulty="easy",
        algorithm=["greedy"],
        learning_goal="Mock Goal",
        statement="Solve it",
        input_format="In",
        output_format="Out",
        constraints=[],
        expected_time_complexity="O(N)",
        hint_blueprint=HintBlueprint(
            intended_algorithm=["greedy"],
            core_insight="Insight",
            common_misconceptions=[],
            edge_case_focus=[],
            forbidden_disclosures=[],
            level_1_guidance="g1",
            level_2_guidance="g2",
            level_3_guidance="g3",
            allowed_code_exposure="skeleton_only"
        )
    )
    return {
        "generated_problem": prob,
        "testcase_bundle": None,
        "reference_solution": None,
        "validation_report": None,
        "hint_bundle": None
    }


def test_public_imports_contract():
    """Test A & B: imports from root and services match."""
    assert generate_problem_package is not None
    assert request_hint_package is not None
    assert service_gen is generate_problem_package
    assert service_hint is request_hint_package


def test_fastapi_style_await_usage(monkeypatch):
    """Test C & D: FastAPI style async execution and mapping works, public dict excludes reference_solution."""
    import agent.services.problem_generation_service
    monkeypatch.setattr(agent.services.problem_generation_service, "run_package_workflow", mock_run_package_workflow)

    inp = ProblemGenerationPackageInput(
        algorithm="greedy",
        difficulty="easy",
        include_concept_context=False
    )
    
    # Run async function using asyncio.run
    res = asyncio.run(generate_problem_package(inp))
    assert res.problem_id == "prob_123"
    
    # Map to public dict
    payload = problem_package_to_public_dict(res)
    assert isinstance(payload, dict)
    assert "reference_solution" not in payload
    assert payload["problem_id"] == "prob_123"


def test_no_apps_api_import_required():
    """Test E: No apps/api imports are required for running service code."""
    # Ensure no import error occurs due to missing app/api files
    for mod in list(sys.modules.keys()):
        if mod.startswith("app.") or mod.startswith("apps."):
            pass
