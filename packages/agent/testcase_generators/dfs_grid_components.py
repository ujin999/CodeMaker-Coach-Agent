from typing import Literal
from agent.schemas import GeneratedTestcase, TestcaseBundle


def solve_dfs_grid_components(grid: list[str]) -> int:
    """
    Return the number of 4-directionally connected components made of '1' cells.
    1 = land, 0 = water.
    Use deterministic DFS.
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

    visited = [[False] * m for _ in range(n)]
    count = 0
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for r in range(n):
        for c in range(m):
            if grid[r][c] == '1' and not visited[r][c]:
                count += 1
                # Iterative stack DFS to prevent recursion depth error
                stack = [(r, c)]
                visited[r][c] = True
                while stack:
                    curr_r, curr_c = stack.pop()
                    for dr, dc in dirs:
                        nr, nc = curr_r + dr, curr_c + dc
                        if 0 <= nr < n and 0 <= nc < m:
                            if grid[nr][nc] == '1' and not visited[nr][nc]:
                                visited[nr][nc] = True
                                stack.append((nr, nc))
    return count


def parse_dfs_grid_input(input_data: str) -> list[str]:
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


def verify_dfs_grid_output(
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
        grid = parse_dfs_grid_input(input_data)
        expected_output_as_int = int(expected_output.strip())
    except Exception:
        return False, -1, -2

    computed = solve_dfs_grid_components(grid)
    is_correct = (expected_output_as_int == computed)
    return is_correct, expected_output_as_int, computed


def assert_dfs_grid_case_is_valid(testcase: GeneratedTestcase) -> None:
    """
    Verify one testcase using solve_dfs_grid_components().
    Raise AssertionError on mismatch.
    """
    is_correct, exp, comp = verify_dfs_grid_output(
        testcase.input_data, testcase.expected_output
    )
    if not is_correct:
        raise AssertionError(
            f"Testcase expected_output mismatch. Expected: {exp}, Solver computed: {comp}."
        )


def assert_dfs_grid_bundle_is_valid(bundle: TestcaseBundle) -> None:
    """
    Verify every testcase.
    Ensure sample exists.
    Ensure hidden or edge exists if len(testcases) >= 2.
    Ensure metadata fields are correct if present.
    """
    for tc in bundle.testcases:
        assert_dfs_grid_case_is_valid(tc)

    has_sample = any(tc.visibility == "sample" for tc in bundle.testcases)
    if not has_sample:
        raise AssertionError("Bundle must contain at least one sample testcase.")

    if len(bundle.testcases) >= 2:
        has_hidden_or_edge = any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)
        if not has_hidden_or_edge:
            raise AssertionError(
                "Bundle must contain at least one hidden or edge testcase when total cases >= 2."
            )


def build_dfs_grid_case(
    name: str,
    grid: list[str],
    visibility: Literal["sample", "hidden", "edge"],
    purpose: str,
    difficulty_reason: str | None = None,
) -> GeneratedTestcase:
    """
    Build input_data.
    Compute expected_output only with solve_dfs_grid_components().
    Fill calculation_steps deterministically.
    Validate before returning.
    """
    n = len(grid)
    m = len(grid[0]) if n > 0 else 0
    input_data = f"{n} {m}\n" + "\n".join(grid)

    ans = solve_dfs_grid_components(grid)
    expected_output = str(ans)

    if ans == 0:
        calculation_steps = "모든 칸이 0이므로 연결된 땅 컴포넌트가 없어 정답은 0입니다."
    else:
        calculation_steps = f"DFS로 1로 이루어진 상하좌우 연결 요소를 탐색하면 총 {ans}개의 컴포넌트가 있으므로 정답은 {ans}입니다."

    tc = GeneratedTestcase(
        name=name,
        input_data=input_data,
        calculation_steps=calculation_steps,
        expected_output=expected_output,
        visibility=visibility,
        purpose=purpose,
        difficulty_reason=difficulty_reason,
    )

    assert_dfs_grid_case_is_valid(tc)
    return tc


def generate_dfs_grid_components_testcases(
    problem_id: str,
    min_cases: int = 5,
) -> TestcaseBundle:
    """
    Generate deterministic sample, hidden, and edge cases.
    All expected outputs must be computed by solve_dfs_grid_components().
    """
    cases_data = [
        # (name, grid, visibility, purpose, difficulty_reason)
        (
            "sample_1",
            [
                "11000",
                "11010",
                "00110",
                "00001",
            ],
            "sample",
            "기본 격자 연결 요소 DFS 탐색 검증 (벽/물로 분할된 3개 땅 컴포넌트)",
            None,
        ),
        (
            "hidden_all_water",
            [
                "000",
                "000",
            ],
            "hidden",
            "모든 격자가 물인 경우 땅 컴포넌트가 0개임을 검증",
            "땅이 전혀 없는 빈 조건",
        ),
        (
            "hidden_all_land",
            [
                "111",
                "111",
            ],
            "hidden",
            "모든 격자가 땅인 경우 하나의 거대한 연결 요소로 묶이는지 검증",
            "전체 격자가 하나로 연결된 최장 탐색 조건",
        ),
        (
            "edge_diagonal_separated",
            [
                "101",
                "010",
                "101",
            ],
            "edge",
            "대각선 인접은 연결로 치지 않고 각기 독립된 컴포넌트로 개별 카운트하는지 검증 (5개 땅)",
            "대각선 격자 연결성 예외 조건",
        ),
        (
            "edge_single_land",
            [
                "1",
            ],
            "edge",
            "1x1 최소 크기 땅 격자 조건 검증 (1개 땅)",
            "최소 격자 크기 조건",
        ),
        (
            "edge_single_water",
            [
                "0",
            ],
            "edge",
            "1x1 최소 크기 물 격자 조건 검증 (0개 땅)",
            "최소 격자 크기 조건",
        ),
        (
            "hidden_multiple_irregular",
            [
                "10010",
                "11010",
                "00000",
                "01101",
                "00101",
            ],
            "hidden",
            "복잡하고 비정형적인 복수 연결 요소 시나리오에서의 카운트 검증",
            "불규칙한 복수 컴포넌트 분할 조건",
        ),
    ]

    extra_index = 1
    while len(cases_data) < min_cases:
        m_sz = extra_index + 3
        grid = []
        for r_idx in range(3):
            row = "".join("1" if (c_idx % 2 == 0) else "0" for c_idx in range(m_sz))
            grid.append(row)

        cases_data.append((
            f"hidden_extra_{extra_index}",
            grid,
            "hidden",
            f"추가적인 자동 생성 DFS 연결 요소 검증 케이스 {extra_index}",
            None,
        ))
        extra_index += 1

    testcases = []
    for name, grid, vis, purpose, diff_reason in cases_data:
        tc = build_dfs_grid_case(
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
        generation_notes="Generated deterministically using solve_dfs_grid_components solver.",
        generation_mode="deterministic",
        generator_name="dfs_grid_components",
        verification_status="passed",
    )

    assert_dfs_grid_bundle_is_valid(bundle)
    return bundle
