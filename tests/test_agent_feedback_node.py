import pytest
from agent.schemas import (
    GeneratedProblem,
    HintBlueprint,
    SubmissionResult,
    FeedbackReport,
)
from agent.nodes import (
    infer_allowed_hint_level,
    analyze_submission_deterministic,
    build_feedback_from_submission,
    generate_feedback_node,
    run_feedback_workflow,
    AgentState,
)


def create_dummy_problem(problem_id: str = "test-problem-123") -> GeneratedProblem:
    """Helper to construct a valid GeneratedProblem in Korean."""
    return GeneratedProblem(
        problem_id=problem_id,
        title="이분 탐색 연습",
        difficulty="medium",
        algorithm=["binary_search"],
        learning_goal="매개 변수 탐색 학습",
        statement="격자 형태 또는 예산 배정 최적화 문제입니다.",
        input_format="입력 형식",
        output_format="출력 형식",
        constraints=["제한 조건"],
        expected_time_complexity="O(N log M)",
        hint_blueprint=HintBlueprint(
            intended_algorithm=["binary_search"],
            core_insight="상한액 C 정하고 탐색",
            common_misconceptions=["오버플로우"],
            edge_case_focus=["최대 예산"],
            forbidden_disclosures=["답안 코드"],
            level_1_guidance="방향",
            level_2_guidance="원리",
            level_3_guidance="스켈레톤",
            allowed_code_exposure="skeleton_only",
        ),
    )


def test_infer_allowed_hint_level():
    """Test A: Check infer_allowed_hint_level mapping for each result type."""
    assert infer_allowed_hint_level("AC") == 1
    assert infer_allowed_hint_level("WA") == 2
    assert infer_allowed_hint_level("TLE") == 2
    assert infer_allowed_hint_level("RE") == 2
    assert infer_allowed_hint_level("MLE") == 2
    assert infer_allowed_hint_level("CE") == 1
    assert infer_allowed_hint_level("PE") == 1
    assert infer_allowed_hint_level("UNKNOWN") == 1


def test_wa_feedback_with_expected_actual_output():
    """Test B: Test WA feedback generation with outputs mismatch."""
    problem = create_dummy_problem()
    submission = SubmissionResult(
        problem_id=problem.problem_id,
        result_type="WA",
        expected_output="5",
        actual_output="4",
        failed_input="3 10\n1 2 3"
    )

    report = analyze_submission_deterministic(problem, submission)

    assert report.problem_id == problem.problem_id
    assert report.result_type == "WA"
    assert report.generated_by == "deterministic"
    assert report.safe_to_show is True
    assert "5" in report.summary
    assert "4" in report.summary
    assert len(report.likely_causes) > 0
    assert len(report.next_steps) > 0
    assert report.allowed_hint_level == 2


def test_ac_feedback():
    """Test C: Test AC feedback generation."""
    problem = create_dummy_problem()
    submission = SubmissionResult(
        problem_id=problem.problem_id,
        result_type="AC"
    )

    report = analyze_submission_deterministic(problem, submission)

    assert report.result_type == "AC"
    assert len(report.likely_causes) == 0
    assert len(report.next_steps) > 0
    assert any("시간" in step or "설명" in step for step in report.next_steps)
    assert report.allowed_hint_level == 1


def test_tle_feedback():
    """Test D: Test TLE feedback generation."""
    problem = create_dummy_problem()
    submission = SubmissionResult(
        problem_id=problem.problem_id,
        result_type="TLE"
    )

    report = analyze_submission_deterministic(problem, submission)

    assert report.result_type == "TLE"
    assert any("복잡도" in cause or "알고리즘" in cause or "연산" in cause for cause in report.likely_causes)
    assert report.allowed_hint_level == 2


def test_generate_feedback_node():
    """Test E: Verify generate_feedback_node updates AgentState correctly."""
    problem = create_dummy_problem()
    submission = SubmissionResult(
        problem_id=problem.problem_id,
        result_type="RE"
    )
    state = AgentState(generated_problem=problem, submission_result=submission)

    new_state = generate_feedback_node(state)

    assert "feedback_report" in new_state
    report = new_state["feedback_report"]
    assert isinstance(report, FeedbackReport)
    assert report.result_type == "RE"
    assert report.allowed_hint_level == 2


def test_generate_feedback_node_missing_fields_raises():
    """Test F: generate_feedback_node raises ValueError when required state is missing."""
    problem = create_dummy_problem()
    submission = SubmissionResult(problem_id="test", result_type="AC")

    # Missing submission_result
    state_no_sub = AgentState(generated_problem=problem)
    with pytest.raises(ValueError, match="submission_result"):
        generate_feedback_node(state_no_sub)

    # Missing generated_problem
    state_no_prob = AgentState(submission_result=submission)
    with pytest.raises(ValueError, match="generated_problem"):
        generate_feedback_node(state_no_prob)


def test_run_feedback_workflow():
    """Test G: run_feedback_workflow runs the node sequence successfully."""
    problem = create_dummy_problem()
    submission = SubmissionResult(
        problem_id=problem.problem_id,
        result_type="MLE"
    )

    state = run_feedback_workflow(problem, submission)

    assert "feedback_report" in state
    report = state["feedback_report"]
    assert report.result_type == "MLE"
    assert report.allowed_hint_level == 2


def test_feedback_report_safety_policy():
    """Test H: Verify FeedbackReport safety policy flags leaks (safe_to_show = False)."""
    # 1. Safe report
    safe_report = FeedbackReport(
        problem_id="test",
        result_type="WA",
        summary="이 코드의 오류를 수정해 보세요.",
        likely_causes=["인덱스 범위 초과"],
        next_steps=["조건문 검사"],
        allowed_hint_level=1,
        safe_to_show=True
    )
    assert safe_report.safe_to_show is True

    # 2. Unsafe report (full Python code in next_steps)
    unsafe_report = FeedbackReport(
        problem_id="test",
        result_type="WA",
        summary="오류 발견",
        likely_causes=["인덱스 범위 초과"],
        next_steps=["여기에 정답이 있습니다: def solve(n):\n    return n + 1"],
        allowed_hint_level=1,
        safe_to_show=True
    )
    # The validator model checker must set safe_to_show to False
    assert unsafe_report.safe_to_show is False

    # 3. Unsafe report with mixed/uppercase code leak
    mixed_unsafe = FeedbackReport(
        problem_id="test",
        result_type="WA",
        summary="Here is code: DEF solve(): return 1",
        likely_causes=[],
        next_steps=[],
        allowed_hint_level=1,
        safe_to_show=True
    )
    assert mixed_unsafe.safe_to_show is False

