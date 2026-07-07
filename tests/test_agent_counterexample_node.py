import pytest
from pydantic import ValidationError
from agent.schemas import GeneratedProblem, SubmissionResult, ErrorDiagnosis, CounterexampleReport, HintBlueprint
from agent.nodes import (
    build_counterexample_report,
    build_counterexample_node,
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


def test_wa_creates_counterexample_report():
    """Test A: WA with failed_input/expected/actual creates counterexample_report."""
    problem = create_test_problem()
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="WA",
        failed_testcase_name="tc_3",
        failed_input="100",
        expected_output="10",
        actual_output="9"
    )

    report = build_counterexample_report(problem, sub)
    assert report.problem_id == "test_prob"
    assert report.result_type == "WA"
    assert report.testcase_name == "tc_3"
    assert report.counterexample_input == "100"
    assert report.expected_output == "10"
    assert report.actual_output == "9"
    assert "테스트케이스 'tc_3'에서 오류가 발생했습니다." in report.explanation
    assert "제시된 반례 입력값은 [100] 입니다." in report.explanation
    assert "기대 출력은 '10' 이었으나" in report.explanation
    assert "실제 출력은 '9'" in report.explanation


def test_ac_says_counterexample_not_needed():
    """Test B: AC says counterexample is not needed."""
    problem = create_test_problem()
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="AC"
    )

    report = build_counterexample_report(problem, sub)
    assert report.result_type == "AC"
    assert "반례가 필요하지 않습니다" in report.explanation


def test_wa_off_by_one_maps_to_boundary():
    """Test C: WA_OFF_BY_ONE maps to boundary lesson."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", failed_input="10")
    diag = ErrorDiagnosis(
        problem_id="test_prob",
        result_type="WA",
        primary_cause="WA_OFF_BY_ONE",
        evidence=["오차 1"],
        suggested_focus=["경계값 점검"]
    )

    report = build_counterexample_report(problem, sub, diagnosis=diag)
    assert "경계 조건 오차" in report.lesson


def test_wa_window_update_maps_to_sliding_window():
    """Test D: WA_WINDOW_UPDATE maps to sliding window lesson."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", failed_input="10")
    diag = ErrorDiagnosis(
        problem_id="test_prob",
        result_type="WA",
        primary_cause="WA_WINDOW_UPDATE",
        evidence=[],
        suggested_focus=[]
    )

    report = build_counterexample_report(problem, sub, diagnosis=diag)
    assert "슬라이딩 윈도우/투포인터" in report.lesson


def test_pe_maps_to_output_format():
    """Test E: PE maps to output format lesson."""
    problem = create_test_problem()
    sub = SubmissionResult(problem_id="test_prob", result_type="PE", failed_input="10")
    diag = ErrorDiagnosis(
        problem_id="test_prob",
        result_type="PE",
        primary_cause="PE_OUTPUT_FORMAT",
        evidence=[],
        suggested_focus=[]
    )

    report = build_counterexample_report(problem, sub, diagnosis=diag)
    assert "출력 형식 오류" in report.lesson


def test_build_counterexample_node():
    """Test F: build_counterexample_node stores counterexample_report."""
    problem = create_test_problem()
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="WA",
        failed_input="10",
        expected_output="5",
        actual_output="4"
    )
    state = AgentState(generated_problem=problem, submission_result=sub)

    new_state = build_counterexample_node(state)
    assert "counterexample_report" in new_state
    assert new_state["counterexample_report"].result_type == "WA"
    assert new_state["counterexample_report"].counterexample_input == "10"


def test_safety_validation_blocks_full_code():
    """Test G: safety validation blocks obvious full code leakage."""
    problem = create_test_problem()

    # normal explanation passes
    report = CounterexampleReport(
        problem_id="test_prob",
        result_type="WA",
        explanation="정상적인 한국어 설명입니다. 특정 함수 정의 문법을 노출하지 않고, 알고리즘 개념을 짚어줍니다.",
        lesson="경계 값을 확인하세요.",
        safe_to_show=True
    )
    assert report.safe_to_show is True

    # full code leak flips safe_to_show to False
    report_leak = CounterexampleReport(
        problem_id="test_prob",
        result_type="WA",
        explanation="여기 코드 예시입니다: def solve(n): return n * 2",
        lesson="return n * 2",
        safe_to_show=True
    )
    assert report_leak.safe_to_show is False

    # empty explanation raises validation error
    with pytest.raises(ValidationError):
        CounterexampleReport(
            problem_id="test_prob",
            result_type="WA",
            explanation="",
            safe_to_show=True
        )
