import re
from typing import Literal
from agent.schemas import GeneratedProblem

# Type alias for supported problem types
ProblemType = Literal["budget_cap", "two_pointer_subarray", "bfs_grid_shortest_path", "dfs_grid_components", "unsupported"]


class UnsupportedTestcaseGeneratorError(Exception):
    """Raised when no deterministic generator is available for the given problem type."""
    pass


def normalize_text(text: str | None) -> str:
    """Normalize text for simple Korean/English keyword detection."""
    if not text:
        return ""
    # Lowercase and replace consecutive whitespace characters with a single space
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def problem_text(problem: GeneratedProblem) -> str:
    """
    Combine title, statement, learning_goal, algorithm, and expected_time_complexity
    into one normalized searchable text.
    """
    parts = [
        problem.title or "",
        problem.statement or "",
        problem.learning_goal or "",
        " ".join(problem.algorithm) if problem.algorithm else "",
        problem.expected_time_complexity or "",
    ]
    return normalize_text(" ".join(parts))


def is_budget_cap_problem(problem: GeneratedProblem) -> bool:
    """
    Return True when the problem is clearly a budget cap / parametric search problem.

    Detection should check for:
    - "min(요청 예산, C)"
    - "상한액 C"
    - "budget cap"
    - "cap C"
    - "sum(min"
    - algorithm contains "binary_search"
    """
    normalized = problem_text(problem)

    indicators = [
        "min(요청 예산, c)",
        "min(요청 예산,c)",
        "min(요청예산, c)",
        "min(요청예산,c)",
        "상한액 c",
        "budget cap",
        "cap c",
        "sum(min",
    ]
    for indicator in indicators:
        if indicator in normalized:
            return True

    # Check if algorithm has binary_search and there is budget cap context
    if problem.algorithm and "binary_search" in problem.algorithm:
        for kw in ["예산", "상한", "배정", "budget", "cap"]:
            if kw in normalized:
                return True

    return False


def is_two_pointer_subarray_problem(problem: GeneratedProblem) -> bool:
    """
    Return True when the problem is clearly about finding the longest contiguous subarray
    whose sum is <= K using two pointers / sliding window.
    """
    statement_normalized = normalize_text(problem.statement)

    # 1. Check if algorithm contains "two_pointer" and statement includes "연속" and "합" and "K/k"
    algos = [normalize_text(a) for a in (problem.algorithm or [])]
    has_two_pointer_algo = any("two_pointer" in a or "two pointer" in a for a in algos)
    if has_two_pointer_algo:
        if "연속" in statement_normalized and "합" in statement_normalized and "k" in statement_normalized:
            return True

    # 2. Check at least 3 strong indicators
    strong_indicators = [
        "투 포인터",
        "sliding window",
        "슬라이딩 윈도우",
        "연속 부분 배열",
        "연속 구간",
        "합이 k 이하",
        "최대 길이",
        "양의 정수",
    ]
    matched_count = 0
    normalized = problem_text(problem)
    for indicator in strong_indicators:
        if indicator in normalized:
            matched_count += 1

    if matched_count >= 3:
        return True

    return False


def is_bfs_grid_shortest_path_problem(problem: GeneratedProblem) -> bool:
    """
    Return True when the problem is clearly about BFS shortest path on a 2D grid.
    """
    normalized = problem_text(problem)
    statement_normalized = normalize_text(problem.statement)

    # Negative checks to avoid confusion with dfs_grid_components
    algos = [normalize_text(a) for a in (problem.algorithm or [])]
    if "dfs" in algos and "bfs" not in algos:
        return False
    if "연결 요소" in normalized or "컴포넌트" in normalized or "섬" in normalized:
        if "최단" not in normalized and "bfs" not in normalized:
            return False

    bfs_indicators = [
        "bfs",
        "너비 우선 탐색",
        "최단 거리",
        "최단 경로",
        "격자",
        "grid",
        "상하좌우",
        "벽",
        "0과 1",
        "도달할 수 없으면 -1",
        "시작점",
        "도착점",
    ]

    # Check option 1: algorithm contains "bfs" and statement includes at least two of the specified keywords
    has_bfs_algo = any("bfs" in a for a in algos)
    if has_bfs_algo:
        kws = ["격자", "최단", "상하좌우", "벽", "-1"]
        matched_kws = sum(1 for kw in kws if kw in statement_normalized)
        if matched_kws >= 2:
            return True

    # Check option 2: text includes at least 4 strong BFS grid indicators
    matched_indicators = sum(1 for ind in bfs_indicators if ind in normalized)
    if matched_indicators >= 4:
        return True

    return False


def is_dfs_grid_components_problem(problem: GeneratedProblem) -> bool:
    """
    Return True when the problem is clearly about counting connected components
    in a 2D grid using DFS.
    """
    normalized = problem_text(problem)
    statement_normalized = normalize_text(problem.statement)

    # Negative checks to avoid confusion with bfs_grid_shortest_path
    algos = [normalize_text(a) for a in (problem.algorithm or [])]
    if "bfs" in algos and "dfs" not in algos:
        return False
    if "최단" in normalized or "최단 거리" in normalized or "최단 경로" in normalized or "-1" in normalized:
        if "dfs" not in normalized and "연결 요소" not in normalized and "섬" not in normalized:
            return False

    dfs_indicators = [
        "dfs",
        "깊이 우선 탐색",
        "연결 요소",
        "컴포넌트",
        "connected component",
        "island",
        "섬",
        "격자",
        "상하좌우",
        "0과 1",
        "1은 땅",
        "0은 물",
    ]

    # Check option 1: algorithm contains "dfs" and statement includes at least two of the specified keywords
    has_dfs_algo = any("dfs" in a for a in algos)
    if has_dfs_algo:
        kws = ["격자", "연결", "섬", "상하좌우", "컴포넌트"]
        matched_kws = sum(1 for kw in kws if kw in statement_normalized)
        if matched_kws >= 2:
            return True

    # Check option 2: text includes at least 4 strong DFS grid component indicators
    matched_indicators = sum(1 for ind in dfs_indicators if ind in normalized)
    if matched_indicators >= 4:
        return True

    return False


def detect_problem_type(problem: GeneratedProblem) -> ProblemType:
    """
    Return "budget_cap" for supported budget cap problems.
    Return "two_pointer_subarray" for supported two-pointer subarray problems.
    Return "bfs_grid_shortest_path" for supported BFS grid shortest path problems.
    Return "dfs_grid_components" for supported DFS grid components problems.
    Return "unsupported" otherwise.
    """
    if is_budget_cap_problem(problem):
        return "budget_cap"
    if is_two_pointer_subarray_problem(problem):
        return "two_pointer_subarray"
    if is_bfs_grid_shortest_path_problem(problem):
        return "bfs_grid_shortest_path"
    if is_dfs_grid_components_problem(problem):
        return "dfs_grid_components"
    return "unsupported"
