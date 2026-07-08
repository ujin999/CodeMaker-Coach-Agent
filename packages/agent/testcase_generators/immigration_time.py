from typing import Literal
from agent.schemas import GeneratedTestcase, TestcaseBundle


def solve_immigration_time(times: list[int], m: int) -> int:
    """
    Return the minimum time required to process M people with N immigration counters.
    Use binary search.
    """
    if not times or m <= 0:
        return 0

    low = 1
    high = min(times) * m
    ans = high

    while low <= high:
        mid = (low + high) // 2
        people = sum(mid // t for t in times)
        if people >= m:
            ans = mid
            high = mid - 1
        else:
            low = mid + 1

    return ans


def parse_immigration_time_input(input_data: str) -> tuple[list[int], int]:
    """
    Parse input format:
    N M
    time_1 time_2 ... time_N
    """
    lines = [line.strip() for line in input_data.strip().splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError("Input data must contain exactly 2 non-empty lines.")

    parts = lines[0].split()
    if len(parts) != 2:
        raise ValueError("First line must contain exactly N and M.")

    try:
        n = int(parts[0])
        m = int(parts[1])
    except ValueError:
        raise ValueError("N and M must be integers.")

    try:
        times = [int(x) for x in lines[1].split()]
    except ValueError:
        raise ValueError("Times must be integers.")

    if len(times) != n:
        raise ValueError(f"N ({n}) does not match the number of times ({len(times)}).")

    if any(t <= 0 for t in times):
        raise ValueError("All times must be positive integers.")

    if m <= 0:
        raise ValueError("M must be a positive integer.")

    return times, m


def verify_immigration_time_output(
    input_data: str,
    expected_output: str,
) -> tuple[bool, int, int]:
    try:
        times, m = parse_immigration_time_input(input_data)
        expected_output_as_int = int(expected_output.strip())
    except Exception:
        return False, -1, -2

    computed_output_from_solver = solve_immigration_time(times, m)
    is_correct = (expected_output_as_int == computed_output_from_solver)
    return is_correct, expected_output_as_int, computed_output_from_solver


def assert_immigration_time_case_is_valid(testcase: GeneratedTestcase) -> None:
    is_correct, exp_val, comp_val = verify_immigration_time_output(
        testcase.input_data, testcase.expected_output
    )
    if not is_correct:
        raise AssertionError(
            f"Testcase expected_output mismatch. Expected: {exp_val}, Solver computed: {comp_val}."
        )


def assert_immigration_time_bundle_is_valid(bundle: TestcaseBundle) -> None:
    for tc in bundle.testcases:
        assert_immigration_time_case_is_valid(tc)

    has_sample = any(tc.visibility == "sample" for tc in bundle.testcases)
    if not has_sample:
        raise AssertionError("Bundle must contain at least one sample testcase.")

    if len(bundle.testcases) >= 2:
        has_hidden_or_edge = any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)
        if not has_hidden_or_edge:
            raise AssertionError(
                "Bundle must contain at least one hidden or edge testcase when total cases >= 2."
            )


def build_immigration_time_case(
    name: str,
    times: list[int],
    m: int,
    visibility: Literal["sample", "hidden", "edge"],
    purpose: str,
    difficulty_reason: str | None = None,
) -> GeneratedTestcase:
    input_data = f"{len(times)} {m}\n" + " ".join(map(str, times))
    c_val = solve_immigration_time(times, m)
    expected_output = str(c_val)

    calculation_steps = (
        f"소요 시간 {c_val} 동안 처리할 수 있는 대기자 수가 {sum(c_val // t for t in times)}명으로 "
        f"M={m}명 이상을 심사할 수 있고, 이보다 적은 시간에는 M명을 심사하지 못하므로 최소 시간은 {c_val}입니다."
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
    
    assert_immigration_time_case_is_valid(tc)
    return tc


def generate_immigration_time_testcases(problem_id: str, min_cases: int = 5) -> TestcaseBundle:
    cases_data = [
        (
            "sample_1",
            [7, 10],
            6,
            "sample",
            "기본 입국심사 처리 시나리오 검증",
            None,
        ),
        (
            "hidden_all_same",
            [5, 5, 5],
            10,
            "hidden",
            "모든 심사대의 속도가 같을 때의 시간 계산 검증",
            None,
        ),
        (
            "edge_minimum",
            [1],
            1,
            "edge",
            "심사관 1명 및 대기자 1명의 최소 경계 상태 검증",
            None,
        ),
        (
            "hidden_large",
            [100, 200],
            1000,
            "hidden",
            "대기자 수가 많을 때의 효율성 검증",
            None,
        ),
        (
            "edge_fast_slow",
            [1, 1000000],
            10,
            "edge",
            "심사대 간 소요 시간 편차가 매우 클 때 검증",
            None,
        ),
    ]

    extra_index = 1
    while len(cases_data) < min_cases:
        tms = [2 * i for i in range(1, extra_index + 3)]
        target_m = 10 * extra_index
        cases_data.append((
            f"hidden_extra_{extra_index}",
            tms,
            target_m,
            "hidden",
            f"추가 자동 생성 케이스 {extra_index}",
            None,
        ))
        extra_index += 1

    testcases = []
    for name, tms, target_m, vis, purpose, diff_reason in cases_data:
        tc = build_immigration_time_case(
            name=name,
            times=tms,
            m=target_m,
            visibility=vis,
            purpose=purpose,
            difficulty_reason=diff_reason,
        )
        testcases.append(tc)

    bundle = TestcaseBundle(
        problem_id=problem_id,
        testcases=testcases,
        generation_notes="Generated deterministically for immigration time.",
        generation_mode="deterministic",
        generator_name="immigration_time",
        verification_status="passed",
    )
    assert_immigration_time_bundle_is_valid(bundle)
    return bundle
