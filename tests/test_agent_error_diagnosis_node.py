import pytest
from agent.schemas import GeneratedProblem, HintBlueprint, SubmissionResult, ErrorDiagnosis
from agent.nodes import (
    detect_problem_family,
    diagnose_wrong_answer,
    diagnose_runtime_error,
    diagnose_compile_error,
    diagnose_timeout,
    diagnose_submission,
    diagnose_submission_node,
    AgentState
)


def create_test_problem(algo: str, statement: str) -> GeneratedProblem:
    return GeneratedProblem(
        problem_id="test_prob",
        title="테스트 문제",
        difficulty="easy",
        algorithm=[algo],
        learning_goal="학습 목표",
        statement=statement,
        input_format="입력",
        output_format="출력",
        constraints=[],
        expected_time_complexity="O(N log N)",
        hint_blueprint=HintBlueprint(
            intended_algorithm=[algo],
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


def test_budget_cap_wa_diagnoses():
    """Test A, B, C: budget_cap WA variations."""
    problem = create_test_problem("binary_search", "프로젝트 예산 상한액 min(요청 예산, C)")

    # A: expected=35 actual=34 -> WA_OFF_BY_ONE
    sub_off = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="35", actual_output="34")
    diag_off = diagnose_submission(problem, sub_off)
    assert diag_off.primary_cause == "WA_OFF_BY_ONE"
    assert "binary_search" in diag_off.related_concepts

    # B: expected=35 actual=20 -> WA_TOO_LOW_BOUND
    sub_low = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="35", actual_output="20")
    diag_low = diagnose_submission(problem, sub_low)
    assert diag_low.primary_cause == "WA_TOO_LOW_BOUND"

    # C: expected=35 actual=50 -> WA_TOO_HIGH_BOUND
    sub_high = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="35", actual_output="50")
    diag_high = diagnose_submission(problem, sub_high)
    assert diag_high.primary_cause == "WA_TOO_HIGH_BOUND"


def test_two_pointer_wa_diagnosis():
    """Test D: two_pointer WA -> WA_WINDOW_UPDATE."""
    problem = create_test_problem("two_pointer", "가장 긴 연속 구간 합이 K 이하")
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="3", actual_output="2")
    diag = diagnose_submission(problem, sub)
    assert diag.primary_cause == "WA_WINDOW_UPDATE"


def test_bfs_wa_diagnosis():
    """Test E: bfs WA -> WA_BFS_DISTANCE_OR_VISITED."""
    problem = create_test_problem("bfs", "미로 찾기 최단거리")
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="12", actual_output="-1")
    diag = diagnose_submission(problem, sub)
    assert diag.primary_cause == "WA_BFS_DISTANCE_OR_VISITED"


def test_dfs_wa_diagnosis():
    """Test F: dfs WA -> WA_DFS_COMPONENT_COUNT."""
    problem = create_test_problem("dfs", "그리드 섬의 개수 연결 요소")
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="5", actual_output="4")
    diag = diagnose_submission(problem, sub)
    assert diag.primary_cause == "WA_DFS_COMPONENT_COUNT"


def test_pe_diagnosis():
    """Test G: PE -> PE_OUTPUT_FORMAT."""
    problem = create_test_problem("binary_search", "상한액 C 구하기")
    sub = SubmissionResult(problem_id="test_prob", result_type="PE", expected_output="35\n", actual_output="35 ")
    diag = diagnose_submission(problem, sub)
    assert diag.primary_cause == "PE_OUTPUT_FORMAT"


def test_re_diagnosis():
    """Test H, I: RE stderr parsing."""
    problem = create_test_problem("dfs", "그리드 탐색")

    # H: IndexError -> RE_INDEX_ERROR
    sub_index = SubmissionResult(problem_id="test_prob", result_type="RE", stderr="IndexError: list index out of range")
    diag_index = diagnose_submission(problem, sub_index)
    assert diag_index.primary_cause == "RE_INDEX_ERROR"

    # I: RecursionError -> RE_RECURSION_DEPTH
    sub_recur = SubmissionResult(problem_id="test_prob", result_type="RE", stderr="RecursionError: maximum recursion depth exceeded")
    diag_recur = diagnose_submission(problem, sub_recur)
    assert diag_recur.primary_cause == "RE_RECURSION_DEPTH"


def test_ce_diagnosis():
    """Test J: CE stderr parsing -> CE_SYNTAX_ERROR."""
    problem = create_test_problem("dfs", "그리드 탐색")
    sub = SubmissionResult(problem_id="test_prob", result_type="CE", stderr="SyntaxError: invalid syntax")
    diag = diagnose_submission(problem, sub)
    assert diag.primary_cause == "CE_SYNTAX_ERROR"


def test_tle_diagnosis():
    """Test K: TLE -> TLE_COMPLEXITY."""
    problem = create_test_problem("binary_search", "이분 탐색")
    sub = SubmissionResult(problem_id="test_prob", result_type="TLE")
    diag = diagnose_submission(problem, sub)
    assert diag.primary_cause == "TLE_COMPLEXITY"
    assert "O(N log N)" in diag.evidence[0]


def test_diagnose_submission_node():
    """Test L: diagnose_submission_node stores error_diagnosis."""
    problem = create_test_problem("binary_search", "이분 탐색")
    sub = SubmissionResult(problem_id="test_prob", result_type="WA", expected_output="10", actual_output="10")
    state = AgentState(generated_problem=problem, submission_result=sub)

    new_state = diagnose_submission_node(state)
    assert "error_diagnosis" in new_state
    assert new_state["error_diagnosis"].result_type == "WA"
