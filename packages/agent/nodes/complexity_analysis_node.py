import re
from typing import Optional
from agent.schemas import GeneratedProblem, SubmissionResult, ComplexityAnalysis
from agent.nodes.state import AgentState


def count_indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def infer_code_pattern(user_code: str | None) -> tuple[str | None, list[str]]:
    """
    Deterministically inspect code text only.
    Do not execute code.
    Detect simple patterns:
    - nested_for_loop
    - nested_while_loop
    - recursion
    - repeated_sort_inside_loop
    - bfs_queue_pattern
    - dfs_stack_or_recursion_pattern
    - unknown
    Return observed_pattern and evidence.
    """
    if not user_code:
        return "unknown", []

    lines = user_code.splitlines()
    evidence = []

    loop_stack = []
    has_nested = False
    for line in lines:
        strip_line = line.strip()
        if not strip_line or strip_line.startswith("#") or strip_line.startswith("//"):
            continue

        indent = count_indent(line)

        # pop stack while top indent is >= current line indent
        while loop_stack and loop_stack[-1] >= indent:
            loop_stack.pop()

        is_loop = False
        if re.search(r"\bfor\b", strip_line) or re.search(r"\bwhile\b", strip_line):
            if ":" in strip_line or "(" in strip_line or "{" in strip_line or "in" in strip_line:
                is_loop = True

        if is_loop:
            if loop_stack:
                has_nested = True
                evidence.append(f"중첩 반복문 감지: '{strip_line}'이 이전 반복문 내부에 중첩되어 있습니다.")
            loop_stack.append(indent)

    has_sort_in_loop = False
    for i, line in enumerate(lines):
        strip_line = line.strip()
        if "sort" in strip_line:
            outer_loop = False
            indent_i = count_indent(line)
            for prev_line in lines[:i]:
                prev_strip = prev_line.strip()
                if not prev_strip:
                    continue
                if re.search(r"\b(for|while)\b", prev_strip):
                    prev_indent = count_indent(prev_line)
                    if indent_i > prev_indent:
                        outer_loop = True
                        break
            if outer_loop:
                has_sort_in_loop = True
                evidence.append(f"반복문 내부 정렬 감지: '{strip_line}'")

    has_recursion = False
    func_names = re.findall(r"def\s+(\w+)\s*\(", user_code)
    func_names += re.findall(r"\b\w+\s+(\w+)\s*\([^)]*\)\s*\{", user_code)
    func_names = [f for f in func_names if f not in ["if", "for", "while", "switch", "main"]]
    for fn in func_names:
        pattern = rf"\b{fn}\s*\("
        calls = re.findall(pattern, user_code)
        if len(calls) >= 2:
            has_recursion = True
            evidence.append(f"재귀 호출 패턴 감지: 함수 '{fn}'가 자기 자신을 호출합니다.")
            break

    has_bfs = False
    has_dfs = False
    code_lower = user_code.lower()

    if "deque" in code_lower or "popleft" in code_lower or "queue" in code_lower:
        has_bfs = True
        evidence.append("BFS 큐/deque 패턴 감지")

    if "stack" in code_lower or "dfs" in code_lower or has_recursion:
        has_dfs = True
        evidence.append("DFS 스택/재귀 패턴 감지")

    observed_pattern = "unknown"
    if has_nested:
        observed_pattern = "nested_for_loop"
    elif has_sort_in_loop:
        observed_pattern = "repeated_sort_inside_loop"
    elif has_recursion:
        observed_pattern = "recursion"
    elif has_bfs:
        observed_pattern = "bfs_queue_pattern"
    elif has_dfs:
        observed_pattern = "dfs_stack_or_recursion_pattern"

    return observed_pattern, evidence


def analyze_complexity(problem: GeneratedProblem, submission: SubmissionResult) -> ComplexityAnalysis:
    """
    Use problem.expected_time_complexity, problem.algorithm, result_type, user_code, stderr.
    """
    problem_id = problem.problem_id
    result_type = submission.result_type
    expected = problem.expected_time_complexity

    pattern, evidence = infer_code_pattern(submission.user_code)

    if submission.stderr and "RecursionError" in submission.stderr:
        pattern = "recursion"
        evidence.append("런타임 에러(RecursionError)가 발생하여 무한 재귀가 의심됩니다.")

    suspected_complexity = None
    risk_level = "medium"
    suggested_actions = []

    related = list(problem.algorithm or [])
    related.append("time_complexity")
    related.append("input_optimization")

    if result_type == "TLE":
        risk_level = "high"
        primary_evidence = "시간 제한 초과(TLE)가 발생했습니다. 효율적인 알고리즘 설계가 필요합니다."
        evidence = [primary_evidence] + evidence

        is_expected_linear_or_log = False
        if expected:
            expected_lower = expected.lower()
            if "o(n log n)" in expected_lower or "o(log n)" in expected_lower or "o(n)" in expected_lower:
                is_expected_linear_or_log = True

        is_bfs_dfs_expected = any(
            algo in ["bfs", "dfs", "bfs_grid_shortest_path", "dfs_grid_components"]
            for algo in (problem.algorithm or [])
        )

        if pattern == "nested_for_loop" and (is_expected_linear_or_log or is_bfs_dfs_expected):
            suspected_complexity = "O(N^2) 또는 그 이상"

        suggested_actions.append("중첩 반복문이 필요한지 확인하세요.")
        suggested_actions.append("문제의 의도 알고리즘에 맞게 탐색 범위를 줄이세요.")

        if "binary_search" in (problem.algorithm or []):
            suggested_actions.append("가능 여부 판단 함수와 이분 탐색 경계를 분리해 보세요.")
            related.append("parametric_search")
        if "two_pointer" in (problem.algorithm or []) or "two_pointer_subarray" in (problem.algorithm or []):
            suggested_actions.append("모든 구간을 다시 계산하지 말고 포인터 이동으로 합을 갱신하세요.")
            related.append("sliding_window")
        if any(
            algo in ["bfs", "dfs", "bfs_grid_shortest_path", "dfs_grid_components"]
            for algo in (problem.algorithm or [])
        ):
            suggested_actions.append("같은 정점을 여러 번 방문하지 않도록 visited 처리를 확인하세요.")
            related.append("visited")
    else:
        if result_type == "AC":
            risk_level = "low"
        else:
            risk_level = "medium"

        if pattern == "nested_for_loop":
            suggested_actions.append("중첩 반복문 사용으로 인한 성능 저하 위험이 있습니다.")
        elif pattern == "repeated_sort_inside_loop":
            suggested_actions.append(
                "반복문 내부에서 매번 정렬(sort)을 수행하여 비효율적일 수 있습니다. 정렬을 한 번만 하거나 우선순위 큐(heapq)를 사용하세요."
            )
        elif pattern == "recursion":
            suggested_actions.append(
                "재귀 호출 깊이(Recursion Depth) 제한을 초과하지 않는지 확인하고, 필요시 반복문으로 변경하세요."
            )

    return ComplexityAnalysis(
        problem_id=problem_id,
        result_type=result_type,
        expected_time_complexity=expected,
        observed_pattern=pattern,
        suspected_complexity=suspected_complexity,
        risk_level=risk_level,
        evidence=evidence,
        related_concepts=related,
        suggested_actions=suggested_actions,
    )


def analyze_complexity_node(state: AgentState) -> AgentState:
    if "generated_problem" not in state or state["generated_problem"] is None:
        raise ValueError("Missing 'generated_problem' in AgentState.")
    if "submission_result" not in state or state["submission_result"] is None:
        raise ValueError("Missing 'submission_result' in AgentState.")

    problem = state["generated_problem"]
    submission = state["submission_result"]

    complexity = analyze_complexity(problem, submission)

    new_state = state.copy()
    new_state["complexity_analysis"] = complexity
    return new_state
