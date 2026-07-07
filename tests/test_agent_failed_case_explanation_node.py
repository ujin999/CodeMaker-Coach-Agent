import pytest
from agent.schemas import GeneratedProblem, HintBlueprint, SubmissionResult, ErrorDiagnosis, FailedCaseExplanation
from agent.nodes import (
    summarize_failed_case,
    explain_failed_case_node,
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


def test_expected_actual_truncation():
    """Test A: expected/actual are included and truncated safely."""
    problem = create_test_problem()
    long_exp = "1" * 100
    long_act = "2" * 100
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="WA",
        expected_output=long_exp,
        actual_output=long_act,
        failed_input="10\n"
    )

    exp = summarize_failed_case(problem, sub)
    assert len(exp.expected_vs_actual) < 200
    assert "기대 출력은 '" + ("1" * 80) + "'이지만" in exp.expected_vs_actual
    assert "실제 출력은 '" + ("2" * 80) + "'입니다." in exp.expected_vs_actual


def test_wa_off_by_one_mapping():
    """Test B: WA_OFF_BY_ONE maps to Korean likely_gap."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="10", actual_output="9")
    diag = ErrorDiagnosis(problem_id="test_prob", result_type="WA", primary_cause="WA_OFF_BY_ONE")

    exp = summarize_failed_case(problem, sub, diag)
    assert "경계값 갱신 또는 종료 조건" in exp.likely_gap


def test_wa_window_update_mapping():
    """Test C: WA_WINDOW_UPDATE maps to two-pointer guidance."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="10", actual_output="5")
    diag = ErrorDiagnosis(problem_id="test_prob", result_type="WA", primary_cause="WA_WINDOW_UPDATE")

    exp = summarize_failed_case(problem, sub, diag)
    assert "왼쪽 포인터 이동 조건" in exp.likely_gap


def test_bfs_gap_mapping():
    """Test D: BFS cause maps to visited/distance guidance."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="10", actual_output="5")
    diag = ErrorDiagnosis(problem_id="test_prob", result_type="WA", primary_cause="WA_BFS_DISTANCE_OR_VISITED")

    exp = summarize_failed_case(problem, sub, diag)
    assert "방문 처리 시점" in exp.likely_gap


def test_ac_returns_no_failed_testcase():
    """Test E: AC says no failed testcase."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="AC")
    exp = summarize_failed_case(problem, sub)
    assert exp.summary == "실패한 테스트케이스가 없습니다."


def test_explain_failed_case_node():
    """Test F: explain_failed_case_node stores failed_case_explanation."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="10", actual_output="5")
    state = AgentState(generated_problem=problem, submission_result=sub)

    new_state = explain_failed_case_node(state)
    assert "failed_case_explanation" in new_state
    assert new_state["failed_case_explanation"].problem_id == "test_prob"


def test_safety_check_blocks_code_leakage():
    """Test G: safety check blocks code-like leakage."""
    problem = create_test_problem()
    sub_unsafe = SubmissionResult(
        problem_id="test_prob",
        result_type="WA",
        expected_output="10",
        actual_output="5"
    )
    # Inject solution code into summary
    exp = FailedCaseExplanation(
        problem_id=problem.problem_id,
        summary="여기에 정답 코드: def solve(n): return n + 1",
        safe_to_show=True
    )
    assert exp.safe_to_show is False
