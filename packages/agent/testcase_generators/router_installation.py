from typing import Literal
from agent.schemas import GeneratedTestcase, TestcaseBundle


def solve_router_installation(coords: list[int], c: int) -> int:
    """
    Return the maximum minimum distance between adjacent routers when C routers are placed.
    Use binary search.
    """
    if not coords or c < 2:
        return 0

    coords = sorted(coords)
    low = 1
    high = coords[-1] - coords[0]
    ans = 0

    while low <= high:
        mid = (low + high) // 2
        count = 1
        last = coords[0]
        for i in range(1, len(coords)):
            if coords[i] - last >= mid:
                count += 1
                last = coords[i]

        if count >= c:
            ans = mid
            low = mid + 1
        else:
            high = mid - 1

    return ans


def parse_router_installation_input(input_data: str) -> tuple[list[int], int]:
    """
    Parse input format:
    N C
    coord_1 coord_2 ... coord_N
    """
    lines = [line.strip() for line in input_data.strip().splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError("Input data must contain exactly 2 non-empty lines.")

    parts = lines[0].split()
    if len(parts) != 2:
        raise ValueError("First line must contain exactly N and C.")

    try:
        n = int(parts[0])
        c = int(parts[1])
    except ValueError:
        raise ValueError("N and C must be integers.")

    try:
        coords = [int(x) for x in lines[1].split()]
    except ValueError:
        raise ValueError("Coords must be integers.")

    if len(coords) != n:
        raise ValueError(f"N ({n}) does not match the number of coordinates ({len(coords)}).")

    if c < 2:
        raise ValueError("C must be at least 2.")

    return coords, c


def verify_router_installation_output(
    input_data: str,
    expected_output: str,
) -> tuple[bool, int, int]:
    try:
        coords, c = parse_router_installation_input(input_data)
        expected_output_as_int = int(expected_output.strip())
    except Exception:
        return False, -1, -2

    computed_output_from_solver = solve_router_installation(coords, c)
    is_correct = (expected_output_as_int == computed_output_from_solver)
    return is_correct, expected_output_as_int, computed_output_from_solver


def assert_router_installation_case_is_valid(testcase: GeneratedTestcase) -> None:
    is_correct, exp_val, comp_val = verify_router_installation_output(
        testcase.input_data, testcase.expected_output
    )
    if not is_correct:
        raise AssertionError(
            f"Testcase expected_output mismatch. Expected: {exp_val}, Solver computed: {comp_val}."
        )


def assert_router_installation_bundle_is_valid(bundle: TestcaseBundle) -> None:
    for tc in bundle.testcases:
        assert_router_installation_case_is_valid(tc)

    has_sample = any(tc.visibility == "sample" for tc in bundle.testcases)
    if not has_sample:
        raise AssertionError("Bundle must contain at least one sample testcase.")

    if len(bundle.testcases) >= 2:
        has_hidden_or_edge = any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)
        if not has_hidden_or_edge:
            raise AssertionError(
                "Bundle must contain at least one hidden or edge testcase when total cases >= 2."
            )


def build_router_installation_case(
    name: str,
    coords: list[int],
    c: int,
    visibility: Literal["sample", "hidden", "edge"],
    purpose: str,
    difficulty_reason: str | None = None,
) -> GeneratedTestcase:
    input_data = f"{len(coords)} {c}\n" + " ".join(map(str, coords))
    c_val = solve_router_installation(coords, c)
    expected_output = str(c_val)

    calculation_steps = (
        f"공유기 사이의 거리를 최소 {c_val} 이상으로 배치하면 {c}개 이상의 공유기 설치가 가능하며, "
        f"이보다 큰 거리로는 {c}개를 설치할 수 없으므로 최대 최소 거리는 {c_val}입니다."
    )

    tc = GeneratedTestcase(
        name=name,
        input_data=input_data,
        calculation_steps=calculation_steps,
        expected_output=expected_output,
        visibility=visibility,
        purpose=purpose,
        difficulty_reason=difficulty_reason,
    )
    
    assert_router_installation_case_is_valid(tc)
    return tc


def generate_router_installation_testcases(problem_id: str, min_cases: int = 5) -> TestcaseBundle:
    cases_data = [
        (
            "sample_1",
            [1, 2, 8, 4, 9],
            3,
            "sample",
            "기본 공유기 설치 시나리오 검증",
            None,
        ),
        (
            "hidden_uniform",
            [1, 3, 5, 7, 9],
            3,
            "hidden",
            "일정한 간격의 집 위치에서의 설치 검증",
            None,
        ),
        (
            "edge_minimum",
            [1, 10],
            2,
            "edge",
            "집 2개와 공유기 2개의 최소 경계 상태 검증",
            None,
        ),
        (
            "hidden_large",
            [100, 200, 300, 400],
            2,
            "hidden",
            "넓은 스케일의 거리 정보 검증",
            None,
        ),
        (
            "edge_tight",
            [1, 2, 3],
            3,
            "edge",
            "간격이 매우 좁은 경우 검증",
            None,
        ),
    ]

    extra_index = 1
    while len(cases_data) < min_cases:
        points = [10 * i for i in range(extra_index + 4)]
        cases_data.append((
            f"hidden_extra_{extra_index}",
            points,
            3,
            "hidden",
            f"추가 자동 생성 케이스 {extra_index}",
            None,
        ))
        extra_index += 1

    testcases = []
    for name, points, target_c, vis, purpose, diff_reason in cases_data:
        tc = build_router_installation_case(
            name=name,
            coords=points,
            c=target_c,
            visibility=vis,
            purpose=purpose,
            difficulty_reason=diff_reason,
        )
        testcases.append(tc)

    bundle = TestcaseBundle(
        problem_id=problem_id,
        testcases=testcases,
        generation_notes="Generated deterministically for router installation.",
        generation_mode="deterministic",
        generator_name="router_installation",
        verification_status="passed",
    )
    assert_router_installation_bundle_is_valid(bundle)
    return bundle
