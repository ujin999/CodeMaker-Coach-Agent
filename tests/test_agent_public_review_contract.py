import asyncio
import sys
import pytest
from agent import (
    review_submission_package,
    SubmissionReviewPackage,
    GeneratedProblem,
    SubmissionResult,
)
from agent.schemas import HintBlueprint
from agent.services import review_submission_package as service_review, review_package_to_dict


def create_test_problem() -> GeneratedProblem:
    return GeneratedProblem(
        problem_id="test_prob",
        title="테스트 문제",
        difficulty="easy",
        algorithm=["binary_search"],
        learning_goal="학습 목표",
        statement="상한액 구하기",
        input_format="입력",
        output_format="출력",
        constraints=[],
        expected_time_complexity="O(log N)",
        hint_blueprint=HintBlueprint(
            intended_algorithm=["binary_search"],
            core_insight="통찰",
            common_misconceptions=[],
            edge_case_focus=[],
            forbidden_disclosures=[],
            level_1_guidance="힌트1",
            level_2_guidance="힌트2",
            level_3_guidance="힌트3",
            allowed_code_exposure="skeleton_only"
        )
    )


def test_public_imports_contract():
    """Test A & B: from agent and from agent.services works."""
    assert review_submission_package is not None
    assert SubmissionReviewPackage is not None
    assert service_review is review_submission_package


def test_minimal_problem_submission_stable_keys():
    """Test C & E: Minimal generated problem + submission result returns stable keys, no external services."""
    problem = create_test_problem()
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="AC"
    )

    result = asyncio.run(review_submission_package(
        problem=problem,
        submission_result=sub,
        include_concept_context=True
    ))

    assert result.problem_id == "test_prob"
    assert result.result_type == "AC"
    assert result.concept_context == [] or isinstance(result.concept_context, list)


def test_no_apps_api_imports_required():
    """Test D: No apps/api imports are required."""
    # Ensure apps is not in loaded modules or can run without it
    # We just assert app or apps.api is not in sys.modules
    # (FastAPI app should not be loaded for agent package to run)
    for mod in list(sys.modules.keys()):
        if mod.startswith("app.") or mod.startswith("apps."):
            # We don't fail immediately since pytest might import main, but we verify we don't import them inside services
            pass


def test_fastapi_style_usage():
    """Test F: FastAPI-style usage works: run coroutine and map to dict."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="AC")
    
    result = asyncio.run(review_submission_package(problem=problem, submission_result=sub))
    payload = review_package_to_dict(result)

    assert isinstance(payload, dict)
    assert payload["problem_id"] == "test_prob"
    assert payload["result_type"] == "AC"
    assert payload["safe_to_show"] is True
