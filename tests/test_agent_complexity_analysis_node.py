import pytest
from agent.schemas import GeneratedProblem, SubmissionResult, ComplexityAnalysis, HintBlueprint
from agent.nodes import (
    infer_code_pattern,
    analyze_complexity,
    analyze_complexity_node,
    AgentState
)


def create_test_problem(algo: str, expected_complexity: str) -> GeneratedProblem:
    return GeneratedProblem(
        problem_id="test_prob",
        title="테스트 문제",
        difficulty="easy",
        algorithm=[algo],
        learning_goal="학습 목표",
        statement="문제 본문",
        input_format="입력",
        output_format="출력",
        constraints=[],
        expected_time_complexity=expected_complexity,
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


def test_tle_nested_loops_binary_search():
    """Test A: TLE + nested loops on binary_search expected O(log N) -> high risk, suspected O(N^2)"""
    problem = create_test_problem("binary_search", "O(log N)")
    code = (
        "for i in range(n):\n"
        "    for j in range(n):\n"
        "        print(i, j)\n"
    )
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="TLE",
        user_code=code
    )

    analysis = analyze_complexity(problem, sub)
    assert analysis.risk_level == "high"
    assert analysis.observed_pattern == "nested_for_loop"
    assert analysis.suspected_complexity == "O(N^2) 또는 그 이상"
    assert "중첩 반복문" in analysis.evidence[1]


def test_tle_two_pointer_nested_loops():
    """Test B: TLE + two_pointer with nested loops -> suggested action mentions pointer/sum update"""
    problem = create_test_problem("two_pointer", "O(N)")
    code = (
        "for i in range(n):\n"
        "    for j in range(i, n):\n"
        "        sum_val = sum(arr[i:j])\n"
    )
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="TLE",
        user_code=code
    )

    analysis = analyze_complexity(problem, sub)
    assert any("포인터 이동으로 합을 갱신" in act for act in analysis.suggested_actions)


def test_tle_bfs_weak_visited():
    """Test C: TLE + bfs -> suggested action mentions visited"""
    problem = create_test_problem("bfs", "O(V+E)")
    code = (
        "from collections import deque\n"
        "q = deque()\n"
        "q.append(start)\n"
        "while q:\n"
        "    curr = q.popleft()\n"
        "    for nxt in adj[curr]:\n"
        "        q.append(nxt)\n"
    )
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="TLE",
        user_code=code
    )

    analysis = analyze_complexity(problem, sub)
    assert any("visited 처리를 확인" in act for act in analysis.suggested_actions)
    assert "visited" in analysis.related_concepts


def test_ac_simple_code():
    """Test D: AC with simple code -> low risk"""
    problem = create_test_problem("binary_search", "O(log N)")
    code = "print('hello')"
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="AC",
        user_code=code
    )

    analysis = analyze_complexity(problem, sub)
    assert analysis.risk_level == "low"
    assert analysis.observed_pattern == "unknown"


def test_recursion_pattern():
    """Test E: recursion pattern detected"""
    problem = create_test_problem("dfs", "O(V+E)")
    code = (
        "def solve(n):\n"
        "    if n <= 1: return 1\n"
        "    return solve(n - 1) + solve(n - 2)\n"
    )
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="WA",
        user_code=code
    )

    analysis = analyze_complexity(problem, sub)
    assert analysis.observed_pattern == "recursion"
    assert any("자기 자신을 호출" in ev for ev in analysis.evidence)


def test_repeated_sort_in_loop():
    """Test F: repeated sort inside loop detected"""
    problem = create_test_problem("two_pointer", "O(N)")
    code = (
        "for x in range(n):\n"
        "    arr.sort()\n"
    )
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="WA",
        user_code=code
    )

    analysis = analyze_complexity(problem, sub)
    assert analysis.observed_pattern == "repeated_sort_inside_loop"
    assert any("반복문 내부 정렬 감지" in ev for ev in analysis.evidence)


def test_analyze_complexity_node():
    """Test G: analyze_complexity_node stores complexity_analysis"""
    problem = create_test_problem("binary_search", "O(log N)")
    sub = SubmissionResult(
        problem_id="test_prob",
        result_type="TLE",
        user_code="for i in arr:\n  for j in arr:\n    pass"
    )
    state = AgentState(generated_problem=problem, submission_result=sub)

    new_state = analyze_complexity_node(state)
    assert "complexity_analysis" in new_state
    assert new_state["complexity_analysis"].risk_level == "high"
