import pytest
from agent.schemas import (
    GeneratedProblem,
    SubmissionResult,
    TestcaseRunResult,
    ErrorDiagnosis,
    FailedCaseExplanation,
    ComplexityAnalysis,
    CounterexampleReport,
    HintBlueprint,
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


def test_feedback_node_incorporates_counterexample():
    """Test A: generate_feedback_node includes counterexample report information."""
    problem = create_test_problem()
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="WA",
        user_code="print(9)"
    )

    report = CounterexampleReport(
        problem_id="test_prob",
        result_type="WA",
        testcase_name="tc_3",
        counterexample_input="100",
        expected_output="10",
        actual_output="9",
        explanation="테스트케이스 'tc_3' 반례 설명",
        lesson="경계조건 학습 팁"
    )

    state = AgentState(
        generated_problem=problem,
        submission_result=sub,
        counterexample_report=report
    )

    new_state = generate_feedback_node(state)
    feedback = new_state["feedback_report"]

    assert "테스트케이스 'tc_3' 반례 설명" in feedback.likely_causes
    assert "경계조건 학습 팁" in feedback.next_steps


def test_run_submission_review_workflow_returns_all_reports():
    """Test B & C: run_submission_review_workflow returns counterexample_report and all existing reports."""
    problem = create_test_problem()
    runs = [
        TestcaseRunResult(
            testcase_name="tc_1",
            status="WA",
            input_data="100",
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

    # Confirm counterexample_report exists
    assert "counterexample_report" in state
    assert state["counterexample_report"].result_type == "WA"
    assert state["counterexample_report"].counterexample_input == "100"
    assert "테스트케이스 'tc_1' 반례 설명" in state["counterexample_report"].explanation or "오류가 발생했습니다" in state["counterexample_report"].explanation

    # Confirm existing fields remain
    assert "error_diagnosis" in state
    assert "failed_case_explanation" in state
    assert "complexity_analysis" in state
    assert "feedback_report" in state
    assert "routing_decision" in state

    assert state["error_diagnosis"].primary_cause == "WA_OFF_BY_ONE"
    assert "경계값 갱신 또는 종료 조건" in state["failed_case_explanation"].likely_gap
    assert state["complexity_analysis"].risk_level == "medium"
    assert state["routing_decision"].action == "show_feedback"


def test_safe_to_show_remains_true_for_normal_integration():
    """Test D: safe_to_show remains True for normal report."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA")
    report = CounterexampleReport(
        problem_id="test_prob",
        result_type="WA",
        explanation="정상적인 반례 설명",
        lesson="정상적인 학습 가이드",
        safe_to_show=True
    )

    state = AgentState(
        generated_problem=problem,
        submission_result=sub,
        counterexample_report=report
    )

    new_state = generate_feedback_node(state)
    assert new_state["feedback_report"].safe_to_show is True
