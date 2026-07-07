import pytest
from agent.schemas import (
    GeneratedProblem,
    HintBlueprint,
    TestcaseRunResult,
    SubmissionEvaluationReport,
    SubmissionResult,
    FeedbackReport,
)
from agent.nodes import (
    normalize_output,
    whitespace_normalize_output,
    compare_expected_actual,
    infer_testcase_status,
    aggregate_result_type,
    build_submission_evaluation_report,
    build_submission_result_from_evaluation,
    evaluate_submission_node,
    run_submission_review_workflow,
    AgentState,
)


def create_dummy_problem(problem_id: str = "test-eval-prob") -> GeneratedProblem:
    """Helper to build a valid GeneratedProblem."""
    return GeneratedProblem(
        problem_id=problem_id,
        title="이분 탐색연습",
        difficulty="medium",
        algorithm=["binary_search"],
        learning_goal="이분 탐색 연습",
        statement="격자 설명 또는 예산 배정 최적화",
        input_format="입력",
        output_format="출력",
        constraints=["제한"],
        expected_time_complexity="O(N log M)",
        hint_blueprint=HintBlueprint(
            intended_algorithm=["binary_search"],
            core_insight="중간값",
            common_misconceptions=["오버플로우"],
            edge_case_focus=["최대값"],
            forbidden_disclosures=["전체 정해"],
            level_1_guidance="힌트1",
            level_2_guidance="힌트2",
            level_3_guidance="힌트3",
            allowed_code_exposure="skeleton_only",
        ),
    )


def test_normalize_output():
    """Test A: Check output normalization handles newlines and Windows carriage returns."""
    assert normalize_output("1\n") == "1"
    assert normalize_output("1\r\n2\r\n") == "1\n2"
    assert normalize_output(None) == ""
    assert compare_expected_actual("1\n", "1") == "AC"
    assert compare_expected_actual("1\r\n2\r\n", "1\n2") == "AC"


def test_whitespace_normalize_and_compare():
    """Test B: Test whitespace normalize comparison for PE and WA outputs."""
    # PE case (matching contents but whitespace difference)
    expected = "1 2\n3"
    actual = "1   2   3"
    assert compare_expected_actual(expected, actual) == "PE"

    # WA case
    assert compare_expected_actual("5", "4") == "WA"


def test_infer_testcase_status():
    """Test C: Test infer_testcase_status checks matching expected/actual values."""
    # 1. Matching -> AC
    res_ac = TestcaseRunResult(
        testcase_name="tc_1",
        status="UNKNOWN",
        expected_output="10",
        actual_output="10\n"
    )
    assert infer_testcase_status(res_ac).status == "AC"

    # 2. Whitespace only difference -> PE
    res_pe = TestcaseRunResult(
        testcase_name="tc_2",
        status="UNKNOWN",
        expected_output="10 20",
        actual_output="10   20"
    )
    assert infer_testcase_status(res_pe).status == "PE"

    # 3. Mismatch -> WA
    res_wa = TestcaseRunResult(
        testcase_name="tc_3",
        status="UNKNOWN",
        expected_output="10",
        actual_output="20"
    )
    assert infer_testcase_status(res_wa).status == "WA"

    # 4. Explicit status stays explicit
    res_tle = TestcaseRunResult(
        testcase_name="tc_4",
        status="TLE",
        expected_output="10",
        actual_output="10"
    )
    assert infer_testcase_status(res_tle).status == "TLE"


def test_aggregate_result_type():
    """Test D: Test aggregate_result_type priority logic."""
    # All AC -> AC
    assert aggregate_result_type([
        TestcaseRunResult(testcase_name="t1", status="AC"),
        TestcaseRunResult(testcase_name="t2", status="AC")
    ]) == "AC"

    # [AC, WA, AC] -> WA
    assert aggregate_result_type([
        TestcaseRunResult(testcase_name="t1", status="AC"),
        TestcaseRunResult(testcase_name="t2", status="WA"),
        TestcaseRunResult(testcase_name="t3", status="AC")
    ]) == "WA"

    # [AC, TLE, WA] -> TLE (first failed in ordered traversal)
    assert aggregate_result_type([
        TestcaseRunResult(testcase_name="t1", status="AC"),
        TestcaseRunResult(testcase_name="t2", status="TLE"),
        TestcaseRunResult(testcase_name="t3", status="WA")
    ]) == "TLE"

    # any CE -> CE
    assert aggregate_result_type([
        TestcaseRunResult(testcase_name="t1", status="TLE"),
        TestcaseRunResult(testcase_name="t2", status="CE")
    ]) == "CE"

    # empty -> UNKNOWN
    assert aggregate_result_type([]) == "UNKNOWN"


def test_build_submission_evaluation_report():
    """Test E: Build aggregate SubmissionEvaluationReport from run results."""
    results = [
        TestcaseRunResult(testcase_name="tc_1", status="AC"),
        TestcaseRunResult(
            testcase_name="tc_2",
            status="UNKNOWN",
            input_data="3\n1 2 3",
            expected_output="5",
            actual_output="4",
            execution_time_ms=10,
            memory_kb=128
        ),
        TestcaseRunResult(testcase_name="tc_3", status="AC", execution_time_ms=15, memory_kb=256)
    ]

    report = build_submission_evaluation_report("test-eval-prob", results)

    assert report.problem_id == "test-eval-prob"
    assert report.result_type == "WA"
    assert report.total_count == 3
    assert report.passed_count == 2
    assert report.first_failed_testcase_name == "tc_2"
    assert report.failed_input == "3\n1 2 3"
    assert report.expected_output == "5"
    assert report.actual_output == "4"
    assert report.max_execution_time_ms == 15
    assert report.max_memory_kb == 256
    assert "다릅" in report.summary  # Korean WA summary


def test_build_submission_result_from_evaluation():
    """Test F: Convert report into Feedback-compatible SubmissionResult."""
    results = [
        TestcaseRunResult(
            testcase_name="tc_1",
            status="UNKNOWN",
            input_data="1 2",
            expected_output="3",
            actual_output="4",
            execution_time_ms=10,
            memory_kb=100
        )
    ]
    report = build_submission_evaluation_report("prob_1", results)

    sub_res = build_submission_result_from_evaluation(
        report,
        user_code="def solve(): pass",
        language="Python"
    )

    assert isinstance(sub_res, SubmissionResult)
    assert sub_res.problem_id == "prob_1"
    assert sub_res.result_type == "WA"
    assert sub_res.failed_testcase_name == "tc_1"
    assert sub_res.failed_input == "1 2"
    assert sub_res.expected_output == "3"
    assert sub_res.actual_output == "4"
    assert sub_res.execution_time_ms == 10
    assert sub_res.memory_kb == 100
    assert sub_res.user_code == "def solve(): pass"
    assert sub_res.language == "Python"


def test_evaluate_submission_node():
    """Test G: evaluate_submission_node stores report and result on state."""
    problem = create_dummy_problem()
    results = [
        TestcaseRunResult(testcase_name="tc_1", status="AC", execution_time_ms=5)
    ]
    state = AgentState(
        generated_problem=problem,
        testcase_run_results=results,
        submission_result=SubmissionResult(problem_id=problem.problem_id, result_type="UNKNOWN", user_code="print()", language="Python")
    )

    new_state = evaluate_submission_node(state)

    assert "submission_evaluation_report" in new_state
    assert "submission_result" in new_state
    report = new_state["submission_evaluation_report"]
    sub_res = new_state["submission_result"]
    assert report.result_type == "AC"
    assert sub_res.result_type == "AC"
    assert sub_res.user_code == "print()"


def test_evaluate_submission_node_missing_raises():
    """Test H/I: Missing required keys raises ValueError."""
    problem = create_dummy_problem()
    results = [TestcaseRunResult(testcase_name="tc_1", status="AC")]

    # Missing results
    with pytest.raises(ValueError, match="testcase_run_results"):
        evaluate_submission_node(AgentState(generated_problem=problem))

    # Missing problem
    with pytest.raises(ValueError, match="generated_problem"):
        evaluate_submission_node(AgentState(testcase_run_results=results))


def test_run_submission_review_workflow():
    """Test J: Run end-to-end submission review workflow."""
    problem = create_dummy_problem()
    results = [
        TestcaseRunResult(
            testcase_name="tc_1",
            status="UNKNOWN",
            input_data="3",
            expected_output="5",
            actual_output="4"
        )
    ]

    final_state = run_submission_review_workflow(
        problem=problem,
        testcase_run_results=results,
        user_code="def solve(): pass",
        language="Python"
    )

    assert "submission_evaluation_report" in final_state
    assert "submission_result" in final_state
    assert "feedback_report" in final_state
    assert "routing_decision" in final_state

    assert final_state["submission_evaluation_report"].result_type == "WA"
    assert final_state["submission_result"].result_type == "WA"
    assert final_state["feedback_report"].result_type == "WA"
    # Safe feedback maps to show_feedback routing action
    assert final_state["routing_decision"].action == "show_feedback"
