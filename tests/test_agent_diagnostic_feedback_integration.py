import pytest
from agent.schemas import (
    GeneratedProblem,
    HintBlueprint,
    SubmissionResult,
    TestcaseRunResult,
    ErrorDiagnosis,
    FailedCaseExplanation,
)
from agent.nodes import (
    generate_feedback_node,
    run_submission_review_workflow,
    AgentState
)


def create_test_problem() -> GeneratedProblem:
    return GeneratedProblem(
        problem_id="test_prob",
        title="테스트 문제",
        difficulty="easy",
        algorithm=["binary_search"],
        learning_goal="학습 목표",
        statement="상한액 C 구하기",
        input_format="입력",
        output_format="출력",
        constraints=[],
        expected_time_complexity="O(N)",
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


def test_generate_feedback_node_incorporates_diagnosis():
    """Test A: generate_feedback_node incorporates diagnosis/explanation in report."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="10", actual_output="9")

    diag = ErrorDiagnosis(
        problem_id="test_prob",
        result_type="WA",
        primary_cause="WA_OFF_BY_ONE",
        evidence=["Expected: 10, Actual: 9"],
        suggested_focus=["lo/hi 갱신 조건"]
    )

    expl = FailedCaseExplanation(
        problem_id="test_prob",
        summary="오답 요약",
        likely_gap="경계 조건 오류 의심"
    )

    state = AgentState(
        generated_problem=problem,
        submission_result=sub,
        error_diagnosis=diag,
        failed_case_explanation=expl
    )

    new_state = generate_feedback_node(state)
    report = new_state["feedback_report"]

    assert "WA_OFF_BY_ONE" in report.summary
    assert "Expected: 10, Actual: 9" in report.likely_causes
    assert "lo/hi 갱신 조건" in report.likely_causes
    assert "경계 조건 오류 의심" in report.next_steps


def test_safe_to_show_remains_true_for_normal():
    """Test B: safe_to_show remains True for normal diagnostic feedback."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="10", actual_output="9")

    diag = ErrorDiagnosis(problem_id="test_prob", result_type="WA", primary_cause="WA_OFF_BY_ONE")
    expl = FailedCaseExplanation(problem_id="test_prob", summary="오답 요약", likely_gap="경계 조건 오류 의심")

    state = AgentState(
        generated_problem=problem,
        submission_result=sub,
        error_diagnosis=diag,
        failed_case_explanation=expl
    )

    new_state = generate_feedback_node(state)
    assert new_state["feedback_report"].safe_to_show is True


def test_run_submission_review_workflow_returns_all():
    """Test C: run_submission_review_workflow returns evaluation, diagnosis, explanation, feedback, routing."""
    problem = create_test_problem()
    runs = [
        TestcaseRunResult(
            testcase_name="tc_1",
            status="UNKNOWN",
            input_data="10",
            expected_output="10",
            actual_output="9"
        )
    ]

    state = run_submission_review_workflow(
        problem=problem,
        testcase_run_results=runs,
        user_code="print(9)",
        language="python"
    )

    assert "submission_evaluation_report" in state
    assert "submission_result" in state
    assert "error_diagnosis" in state
    assert "failed_case_explanation" in state
    assert "feedback_report" in state
    assert "routing_decision" in state

    assert state["submission_evaluation_report"].result_type == "WA"
    assert state["error_diagnosis"].primary_cause == "WA_OFF_BY_ONE"
    assert "경계값 갱신 또는 종료 조건" in state["failed_case_explanation"].likely_gap
    assert "WA_OFF_BY_ONE" in state["feedback_report"].summary
    assert state["routing_decision"].action == "show_feedback"
