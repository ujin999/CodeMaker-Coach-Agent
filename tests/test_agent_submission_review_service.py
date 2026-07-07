import asyncio
import inspect
import json
import pytest
from agent.schemas import (
    GeneratedProblem,
    SubmissionResult,
    TestcaseRunResult,
    SubmissionReviewPackage,
    HintBlueprint,
    CounterexampleReport
)
from agent.services import (
    review_submission_package,
    review_submission_package_sync,
    review_package_to_dict
)


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


def test_wa_submission_review_service():
    """Test A: WA submission returns package with all expected child reports."""
    problem = create_test_problem()
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="WA",
        user_code="print(9)",
        language="python"
    )
    runs = [
        TestcaseRunResult(
            testcase_name="tc_1",
            status="WA",
            input_data="100",
            expected_output="10",
            actual_output="9"
        )
    ]

    result = review_submission_package_sync(
        problem=problem,
        submission_result=sub,
        testcase_results=runs,
        include_concept_context=True
    )

    assert isinstance(result, SubmissionReviewPackage)
    assert result.result_type == "WA"
    assert result.evaluation_report is not None
    assert result.error_diagnosis is not None
    assert result.failed_case_explanation is not None
    assert result.complexity_analysis is not None
    assert result.counterexample_report is not None
    assert result.feedback_report is not None
    assert result.routing_decision is not None
    assert "제출 결과는 WA" in result.summary
    assert len(result.concept_context) > 0


def test_tle_submission_complexity_mentions():
    """Test B: TLE submission includes complexity_analysis and feedback mentions complexity."""
    problem = create_test_problem()
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="TLE",
        user_code="for i in range(10):\n  for j in range(10): pass",
        language="python"
    )
    runs = [
        TestcaseRunResult(
            testcase_name="tc_1",
            status="TLE",
            input_data="100",
            expected_output="10",
            actual_output=None
        )
    ]

    result = review_submission_package_sync(
        problem=problem,
        submission_result=sub,
        testcase_results=runs,
        include_concept_context=True
    )

    assert result.result_type == "TLE"
    assert result.complexity_analysis is not None
    assert result.complexity_analysis.risk_level == "high"
    assert "시간 복잡도" in result.summary


def test_ac_submission_review_service():
    """Test C: AC submission is safe, low-risk, and counterexample says not needed."""
    problem = create_test_problem()
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="AC",
        user_code="print(10)",
        language="python"
    )
    runs = [
        TestcaseRunResult(
            testcase_name="tc_1",
            status="AC",
            input_data="100",
            expected_output="10",
            actual_output="10"
        )
    ]

    result = review_submission_package_sync(
        problem=problem,
        submission_result=sub,
        testcase_results=runs,
        include_concept_context=True
    )

    assert result.result_type == "AC"
    assert result.safe_to_show is True
    assert result.counterexample_report.explanation == "반례가 필요하지 않습니다. 모든 테스트를 통과했습니다."


def test_concept_context_disabled():
    """Test D: include_concept_context=False returns empty concept_context."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA")
    runs = [
        TestcaseRunResult(testcase_name="tc_1", status="WA", input_data="100", expected_output="10", actual_output="9")
    ]

    result = review_submission_package_sync(
        problem=problem,
        submission_result=sub,
        testcase_results=runs,
        include_concept_context=False
    )
    assert result.concept_context == []


def test_rag_failure_graceful(monkeypatch):
    """Test E: RAG failure does not crash review_submission_package."""
    # Mock search_concepts to raise exception
    import rag.retriever
    monkeypatch.setattr(rag.retriever, "search_concepts", lambda *args, **kwargs: exec("raise(Exception('Qdrant down'))"))

    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA")
    runs = [
        TestcaseRunResult(testcase_name="tc_1", status="WA", input_data="100", expected_output="10", actual_output="9")
    ]

    result = review_submission_package_sync(
        problem=problem,
        submission_result=sub,
        testcase_results=runs,
        include_concept_context=True
    )
    # should succeed with empty concept_context
    assert result.concept_context == []


def test_review_package_to_dict():
    """Test F: review_package_to_dict returns dict and is JSON-compatible."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA")
    runs = [
        TestcaseRunResult(testcase_name="tc_1", status="WA", input_data="100", expected_output="10", actual_output="9")
    ]

    result = review_submission_package_sync(
        problem=problem,
        submission_result=sub,
        testcase_results=runs
    )

    payload = review_package_to_dict(result)
    assert isinstance(payload, dict)
    assert payload["problem_id"] == "test_prob"
    # check JSON serialization
    serialized = json.dumps(payload)
    assert "test_prob" in serialized


def test_unsafe_child_report_cascades_safety():
    """Test G: unsafe child report makes package.safe_to_show False."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA")
    runs = [
        TestcaseRunResult(testcase_name="tc_1", status="WA", input_data="100", expected_output="10", actual_output="9")
    ]

    result = review_submission_package_sync(
        problem=problem,
        submission_result=sub,
        testcase_results=runs
    )

    # Force a child report to be unsafe
    result.counterexample_report.safe_to_show = False
    # Trigger model validator again to cascade
    validated = SubmissionReviewPackage.model_validate(result.model_dump())
    assert validated.safe_to_show is False


def test_review_submission_package_is_async_coroutine():
    """Test H: review_submission_package is an async coroutine function."""
    assert inspect.iscoroutinefunction(review_submission_package)


def test_review_submission_package_sync_wrapper():
    """Test I: review_submission_package_sync works from normal sync context."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="AC")
    res = review_submission_package_sync(problem=problem, submission_result=sub)
    assert res.result_type == "AC"
