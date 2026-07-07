import pytest
from agent.schemas import (
    GeneratedProblem,
    SubmissionResult,
    TestcaseRunResult,
    ErrorDiagnosis,
    FailedCaseExplanation,
    ComplexityAnalysis,
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
        statement="상한액 C 구하기",
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


def test_feedback_node_incorporates_complexity():
    """Test A: generate_feedback_node includes complexity_analysis evidence/actions for TLE"""
    problem = create_test_problem()
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="TLE",
        user_code="for i in range(10):\n  for j in range(10): pass"
    )

    comp = ComplexityAnalysis(
        problem_id="test_prob",
        result_type="TLE",
        expected_time_complexity="O(log N)",
        observed_pattern="nested_for_loop",
        suspected_complexity="O(N^2)",
        risk_level="high",
        evidence=["중첩 반복문 감지됨"],
        suggested_actions=["중첩 루프 최적화"]
    )

    state = AgentState(
        generated_problem=problem,
        submission_result=sub,
        complexity_analysis=comp
    )

    new_state = generate_feedback_node(state)
    report = new_state["feedback_report"]

    assert "시간 복잡도 분석 결과 위험도가 high 수준으로 감지되었습니다." in report.summary
    assert "중첩 반복문 감지됨" in report.likely_causes
    assert "중첩 루프 최적화" in report.next_steps


def test_run_submission_review_workflow_returns_complexity():
    """Test B: run_submission_review_workflow returns complexity_analysis"""
    problem = create_test_problem()
    runs = [
        TestcaseRunResult(
            testcase_name="tc_1",
            status="TLE",
            input_data="10",
            expected_output="10",
            actual_output=None
        )
    ]

    state = run_submission_review_workflow(
        problem=problem,
        testcase_run_results=runs,
        user_code="for i in range(10):\n  for j in range(10): pass",
        language="python"
    )

    assert "complexity_analysis" in state
    assert state["complexity_analysis"].observed_pattern == "nested_for_loop"
    assert "시간 복잡도 분석 결과" in state["feedback_report"].summary


def test_existing_diagnosis_and_explanation_remain():
    """Test C: existing diagnosis and failed_case_explanation still remain in final state"""
    problem = create_test_problem()
    runs = [
        TestcaseRunResult(
            testcase_name="tc_1",
            status="WA",
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

    assert "error_diagnosis" in state
    assert "failed_case_explanation" in state
    assert "complexity_analysis" in state
    assert "feedback_report" in state

    assert state["error_diagnosis"].primary_cause == "WA_OFF_BY_ONE"
    assert "경계값 갱신 또는 종료 조건" in state["failed_case_explanation"].likely_gap


def test_safe_to_show_remains_true_for_normal():
    """Test D: safe_to_show remains True for normal complexity feedback"""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="TLE", user_code="print(10)")
    comp = ComplexityAnalysis(
        problem_id="test_prob",
        result_type="TLE",
        evidence=["안전한 분석 증거"],
        suggested_actions=["안전한 액션"],
        safe_to_show=True
    )
    state = AgentState(
        generated_problem=problem,
        submission_result=sub,
        complexity_analysis=comp
    )

    new_state = generate_feedback_node(state)
    assert new_state["feedback_report"].safe_to_show is True
