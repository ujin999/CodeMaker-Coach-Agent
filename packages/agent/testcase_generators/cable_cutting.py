from typing import Literal
from agent.schemas import GeneratedTestcase, TestcaseBundle


def solve_cable_cutting(lengths: list[int], k: int) -> int:
    """
    Return the maximum integer length L in [0, max(lengths)]
    such that we can produce at least K pieces of length L from the N cables.
    Use binary search.
    """
    if not lengths or k <= 0:
        return 0

    low = 1
    high = max(lengths)
    ans = 0

    while low <= high:
        mid = (low + high) // 2
        pieces = sum(l // mid for l in lengths)
        if pieces >= k:
            ans = mid
            low = mid + 1
        else:
            high = mid - 1

    return ans


def parse_cable_cutting_input(input_data: str) -> tuple[list[int], int]:
    """
    Parse input format:
    N K
    length_1 length_2 ... length_N
    """
    lines = [line.strip() for line in input_data.strip().splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError("Input data must contain exactly 2 non-empty lines.")

    parts = lines[0].split()
    if len(parts) != 2:
        raise ValueError("First line must contain exactly N and K.")

    try:
        n = int(parts[0])
        k = int(parts[1])
    except ValueError:
        raise ValueError("N and K must be integers.")

    try:
        lengths = [int(x) for x in lines[1].split()]
    except ValueError:
        raise ValueError("Lengths must be integers.")

    if len(lengths) != n:
        raise ValueError(f"N ({n}) does not match the number of lengths ({len(lengths)}).")

    if any(l <= 0 for l in lengths):
        raise ValueError("All lengths must be positive integers.")

    if k <= 0:
        raise ValueError("K must be a positive integer.")

    return lengths, k


def verify_cable_cutting_output(
    input_data: str,
    expected_output: str,
) -> tuple[bool, int, int]:
    try:
        lengths, k = parse_cable_cutting_input(input_data)
        expected_output_as_int = int(expected_output.strip())
    except Exception:
        return False, -1, -2

    computed_output_from_solver = solve_cable_cutting(lengths, k)
    is_correct = (expected_output_as_int == computed_output_from_solver)
    return is_correct, expected_output_as_int, computed_output_from_solver


def assert_cable_cutting_case_is_valid(testcase: GeneratedTestcase) -> None:
    is_correct, exp_val, comp_val = verify_cable_cutting_output(
        testcase.input_data, testcase.expected_output
    )
    if not is_correct:
        raise AssertionError(
            f"Testcase expected_output mismatch. Expected: {exp_val}, Solver computed: {comp_val}."
        )


def assert_cable_cutting_bundle_is_valid(bundle: TestcaseBundle) -> None:
    for tc in bundle.testcases:
        assert_cable_cutting_case_is_valid(tc)

    has_sample = any(tc.visibility == "sample" for tc in bundle.testcases)
    if not has_sample:
        raise AssertionError("Bundle must contain at least one sample testcase.")

    if len(bundle.testcases) >= 2:
        has_hidden_or_edge = any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)
        if not has_hidden_or_edge:
            raise AssertionError(
                "Bundle must contain at least one hidden or edge testcase when total cases >= 2."
            )


def build_cable_cutting_case(
    name: str,
    lengths: list[int],
    k: int,
    visibility: Literal["sample", "hidden", "edge"],
    purpose: str,
    difficulty_reason: str | None = None,
) -> GeneratedTestcase:
    input_data = f"{len(lengths)} {k}\n" + " ".join(map(str, lengths))
    c_val = solve_cable_cutting(lengths, k)
    expected_output = str(c_val)

    calculation_steps = (
        f"길이 {c_val}로 자르면 총 {sum(l // c_val for l in lengths) if c_val > 0 else 0}개의 조각을 얻을 수 있어 "
        f"K={k}개 이상을 만족하며, 이보다 긴 길이로는 K개 이상을 만들 수 없으므로 최댓값은 {c_val}입니다."
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
    
    assert_cable_cutting_case_is_valid(tc)
    return tc


def generate_cable_cutting_testcases(problem_id: str, min_cases: int = 5) -> TestcaseBundle:
    cases_data = [
        (
            "sample_1",
            [802, 743, 457, 539],
            11,
            "sample",
            "기본적인 랜선 자르기 시나리오 검증",
            None,
        ),
        (
            "hidden_all_same",
            [100, 100, 100, 100],
            4,
            "hidden",
            "모든 랜선의 길이가 같고 조각 수가 N과 일치하는 경계 검증",
            None,
        ),
        (
            "edge_minimum",
            [1],
            1,
            "edge",
            "단일 랜선 및 최소 개수 조건 검증",
            None,
        ),
        (
            "hidden_large",
            [1000000, 1000000],
            3,
            "hidden",
            "큰 값에 대한 효율성 검증",
            None,
        ),
        (
            "edge_large_k",
            [10, 20, 30],
            100,
            "edge",
            "K가 매우 커서 잘라낼 수 없는 경우 검증",
            None,
        ),
    ]

    extra_index = 1
    while len(cases_data) < min_cases:
        lens = [100 * i for i in range(1, extra_index + 3)]
        target_k = len(lens) * 2
        cases_data.append((
            f"hidden_extra_{extra_index}",
            lens,
            target_k,
            "hidden",
            f"추가 자동 생성 케이스 {extra_index}",
            None,
        ))
        extra_index += 1

    testcases = []
    for name, lens, target_k, vis, purpose, diff_reason in cases_data:
        tc = build_cable_cutting_case(
            name=name,
            lengths=lens,
            k=target_k,
            visibility=vis,
            purpose=purpose,
            difficulty_reason=diff_reason,
        )
        testcases.append(tc)

    bundle = TestcaseBundle(
        problem_id=problem_id,
        testcases=testcases,
        generation_notes="Generated deterministically for cable cutting.",
        generation_mode="deterministic",
        generator_name="cable_cutting",
        verification_status="passed",
    )
    assert_cable_cutting_bundle_is_valid(bundle)
    return bundle
