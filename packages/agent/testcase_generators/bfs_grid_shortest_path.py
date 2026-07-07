from typing import Literal
from collections import deque
from agent.schemas import GeneratedTestcase, TestcaseBundle


def solve_bfs_grid_shortest_path(grid: list[str]) -> int:
    """
    Return shortest path distance from (0,0) to (N-1,M-1) in number of cells visited.
    0 = passable, 1 = wall.
    Move in 4 directions.
    Return -1 if unreachable.
    """
    if not grid:
        raise ValueError("grid must not be empty")
    n = len(grid)
    if not grid[0]:
        raise ValueError("grid rows must not be empty")
    m = len(grid[0])
    for row in grid:
        if len(row) != m:
            raise ValueError("every row must have the same length")
        if not all(c in ("0", "1") for c in row):
            raise ValueError("every cell must be '0' or '1'")

    if grid[0][0] == '1' or grid[n - 1][m - 1] == '1':
        return -1

    if n == 1 and m == 1:
        return 1

    visited = [[False] * m for _ in range(n)]
    queue = deque([(0, 0, 1)])  # r, c, dist
    visited[0][0] = True

    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    while queue:
        r, c, d = queue.popleft()
        if r == n - 1 and c == m - 1:
            return d

        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < m:
                if grid[nr][nc] == '0' and not visited[nr][nc]:
                    visited[nr][nc] = True
                    queue.append((nr, nc, d + 1))

    return -1


def parse_bfs_grid_input(input_data: str) -> list[str]:
    """
    Parse:
    N M
    row_1
    ...
    row_N

    Validate:
    - first line has exactly N and M
    - exactly N rows follow
    - every row length is M
    - every row contains only 0 or 1
    """
    lines = [line.strip() for line in input_data.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("input must not be empty")

    first_parts = lines[0].split()
    if len(first_parts) != 2:
        raise ValueError("first line must contain exactly N and M")

    try:
        n = int(first_parts[0])
        m = int(first_parts[1])
    except ValueError:
        raise ValueError("N and M must be integers")

    if n <= 0 or m <= 0:
        raise ValueError("N and M must be positive integers")

    rows = lines[1:]
    if len(rows) != n:
        raise ValueError(f"number of row lines ({len(rows)}) does not match N ({n})")

    for r_idx, row in enumerate(rows):
        if len(row) != m:
            raise ValueError(f"row {r_idx + 1} length ({len(row)}) does not match M ({m})")
        if not all(c in ("0", "1") for c in row):
            raise ValueError(f"row {r_idx + 1} contains invalid character(s)")

    return rows


def verify_bfs_grid_output(
    input_data: str,
    expected_output: str,
) -> tuple[bool, int, int]:
    """
    Return:
    - is_correct
    - expected_output_as_int
    - computed_output_from_solver
    """
    try:
        grid = parse_bfs_grid_input(input_data)
        expected_output_as_int = int(expected_output.strip())
    except Exception:
        return False, -1, -2

    computed = solve_bfs_grid_shortest_path(grid)
    is_correct = (expected_output_as_int == computed)
    return is_correct, expected_output_as_int, computed


def assert_bfs_grid_case_is_valid(testcase: GeneratedTestcase) -> None:
    """
    Verify one testcase using solve_bfs_grid_shortest_path().
    Raise AssertionError on mismatch.
    """
    is_correct, exp, comp = verify_bfs_grid_output(
        testcase.input_data, testcase.expected_output
    )
    if not is_correct:
        raise AssertionError(
            f"Testcase expected_output mismatch. Expected: {exp}, Solver computed: {comp}."
        )


def assert_bfs_grid_bundle_is_valid(bundle: TestcaseBundle) -> None:
    """
    Verify every testcase.
    Ensure sample exists.
    Ensure hidden or edge exists if len(testcases) >= 2.
    Ensure metadata fields are correct if present.
    """
    for tc in bundle.testcases:
        assert_bfs_grid_case_is_valid(tc)

    has_sample = any(tc.visibility == "sample" for tc in bundle.testcases)
    if not has_sample:
        raise AssertionError("Bundle must contain at least one sample testcase.")

    if len(bundle.testcases) >= 2:
        has_hidden_or_edge = any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)
        if not has_hidden_or_edge:
            raise AssertionError(
                "Bundle must contain at least one hidden or edge testcase when total cases >= 2."
            )


def build_bfs_grid_case(
    name: str,
    grid: list[str],
    visibility: Literal["sample", "hidden", "edge"],
    purpose: str,
    difficulty_reason: str | None = None,
) -> GeneratedTestcase:
    """
    Build input_data.
    Compute expected_output only with solve_bfs_grid_shortest_path().
    Fill calculation_steps deterministically.
    Validate before returning.
    """
    n = len(grid)
    m = len(grid[0]) if n > 0 else 0
    input_data = f"{n} {m}\n" + "\n".join(grid)

    ans = solve_bfs_grid_shortest_path(grid)
    expected_output = str(ans)

    if ans == -1:
        calculation_steps = "BFS 탐색 결과 도착점에 도달할 수 없으므로 정답은 -1입니다."
    else:
        calculation_steps = f"BFS로 시작점에서 도착점까지의 최단 거리를 계산하면 방문 칸 수 기준 최단 거리는 {ans}입니다."

    tc = GeneratedTestcase(
        name=name,
        input_data=input_data,
        calculation_steps=calculation_steps,
        expected_output=expected_output,
        visibility=visibility,
        purpose=purpose,
        difficulty_reason=difficulty_reason,
    )

    assert_bfs_grid_case_is_valid(tc)
    return tc


def generate_bfs_grid_shortest_path_testcases(
    problem_id: str,
    min_cases: int = 5,
) -> TestcaseBundle:
    """
    Generate deterministic sample, hidden, and edge cases.
    All expected outputs must be computed by solve_bfs_grid_shortest_path().
    """
    cases_data = [
        # (name, grid, visibility, purpose, difficulty_reason)
        (
            "sample_1",
            [
                "000",
                "110",
                "000",
            ],
            "sample",
            "기본 격자 최단 거리 BFS 탐색 검증 (벽 우회 포함)",
            None,
        ),
        (
            "hidden_simple_open",
            [
                "00",
                "00",
            ],
            "hidden",
            "가장 직관적인 장애물 없는 최단 경로 탐색 검증",
            None,
        ),
        (
            "hidden_unreachable",
            [
                "010",
                "111",
                "000",
            ],
            "hidden",
            "벽에 가로막혀 도달할 수 없는 시나리오 검증 (-1 반환)",
            "모든 경로가 벽에 의해 차단된 상태",
        ),
        (
            "edge_single_cell",
            [
                "0",
            ],
            "edge",
            "N=1, M=1 최소 격자 크기 경계 조건 검증 (거리 1)",
            "격자 크기가 최소인 조건",
        ),
        (
            "edge_start_wall",
            [
                "10",
                "00",
            ],
            "edge",
            "시작점 자체가 벽인 예외 조건 검증 (-1 반환)",
            "시작 지점에 도달 불가한 조건",
        ),
        (
            "edge_goal_wall",
            [
                "00",
                "01",
            ],
            "edge",
            "도착점 자체가 벽인 예외 조건 검증 (-1 반환)",
            "도착 지점이 벽인 조건",
        ),
        (
            "hidden_longer_path",
            [
                "0000",
                "1110",
                "0000",
                "0111",
                "0000",
            ],
            "hidden",
            "구불구불한 지그재그 경로 탐색 및 정확한 최단 거리 검증",
            "긴 경로 및 우회 조건",
        ),
    ]

    extra_index = 1
    while len(cases_data) < min_cases:
        m_sz = extra_index + 3
        grid = [
            "0" * m_sz,
            "1" * (m_sz - 1) + "0",
            "0" * m_sz
        ]
        cases_data.append((
            f"hidden_extra_{extra_index}",
            grid,
            "hidden",
            f"추가적인 자동 생성 BFS 최단 경로 검증 케이스 {extra_index}",
            None,
        ))
        extra_index += 1

    testcases = []
    for name, grid, vis, purpose, diff_reason in cases_data:
        tc = build_bfs_grid_case(
            name=name,
            grid=grid,
            visibility=vis,
            purpose=purpose,
            difficulty_reason=diff_reason,
        )
        testcases.append(tc)

    bundle = TestcaseBundle(
        problem_id=problem_id,
        testcases=testcases,
        generation_notes="Generated deterministically using solve_bfs_grid_shortest_path solver.",
        generation_mode="deterministic",
        generator_name="bfs_grid_shortest_path",
        verification_status="passed",
    )

    assert_bfs_grid_bundle_is_valid(bundle)
    return bundle
