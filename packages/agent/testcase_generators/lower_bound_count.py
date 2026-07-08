from typing import Literal
from agent.schemas import GeneratedTestcase, TestcaseBundle


def solve_lower_bound_count(array: list[int], x: int) -> int:
    """
    Return the first index (0-indexed) in the sorted array where the value is >= x.
    If all elements are smaller than x, return len(array).
    Use binary search.
    """
    if not array:
        return 0

    low = 0
    high = len(array) - 1
    ans = len(array)

    while low <= high:
        mid = (low + high) // 2
        if array[mid] >= x:
            ans = mid
            high = mid - 1
        else:
            low = mid + 1

    return ans


def parse_lower_bound_count_input(input_data: str) -> tuple[list[int], int]:
    """
    Parse input format:
    N X
    val_1 val_2 ... val_N
    """
    lines = [line.strip() for line in input_data.strip().splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError("Input data must contain exactly 2 non-empty lines.")

    parts = lines[0].split()
    if len(parts) != 2:
        raise ValueError("First line must contain exactly N and X.")

    try:
        n = int(parts[0])
        x = int(parts[1])
    except ValueError:
        raise ValueError("N and X must be integers.")

    try:
        array = [int(v) for v in lines[1].split()]
    except ValueError:
        raise ValueError("Array values must be integers.")

    if len(array) != n:
        raise ValueError(f"N ({n}) does not match the number of array values ({len(array)}).")

    # The array must be sorted for binary search lower bound to be deterministic
    if array != sorted(array):
        raise ValueError("The array must be sorted in ascending order.")

    return array, x


def verify_lower_bound_count_output(
    input_data: str,
    expected_output: str,
) -> tuple[bool, int, int]:
    try:
        array, x = parse_lower_bound_count_input(input_data)
        expected_output_as_int = int(expected_output.strip())
    except Exception:
        return False, -1, -2

    computed_output_from_solver = solve_lower_bound_count(array, x)
    is_correct = (expected_output_as_int == computed_output_from_solver)
    return is_correct, expected_output_as_int, computed_output_from_solver


def assert_lower_bound_count_case_is_valid(testcase: GeneratedTestcase) -> None:
    is_correct, exp_val, comp_val = verify_lower_bound_count_output(
        testcase.input_data, testcase.expected_output
    )
    if not is_correct:
        raise AssertionError(
            f"Testcase expected_output mismatch. Expected: {exp_val}, Solver computed: {comp_val}."
        )


def assert_lower_bound_count_bundle_is_valid(bundle: TestcaseBundle) -> None:
    for tc in bundle.testcases:
        assert_lower_bound_count_case_is_valid(tc)

    has_sample = any(tc.visibility == "sample" for tc in bundle.testcases)
    if not has_sample:
        raise AssertionError("Bundle must contain at least one sample testcase.")

    if len(bundle.testcases) >= 2:
        has_hidden_or_edge = any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)
        if not has_hidden_or_edge:
            raise AssertionError(
                "Bundle must contain at least one hidden or edge testcase when total cases >= 2."
            )


def build_lower_bound_count_case(
    name: str,
    array: list[int],
    x: int,
    visibility: Literal["sample", "hidden", "edge"],
    purpose: str,
    difficulty_reason: str | None = None,
) -> GeneratedTestcase:
    input_data = f"{len(array)} {x}\n" + " ".join(map(str, array))
    c_val = solve_lower_bound_count(array, x)
    expected_output = str(c_val)

    calculation_steps = (
        f"오름차순 정렬된 배열에서 값 {x} 이상이 처음 나타나는 위치(0-based 인덱스)는 {c_val}입니다."
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
    
    assert_lower_bound_count_case_is_valid(tc)
    return tc


def generate_lower_bound_count_testcases(problem_id: str, min_cases: int = 5) -> TestcaseBundle:
    cases_data = [
        (
            "sample_1",
            [1, 3, 3, 5, 7],
            3,
            "sample",
            "기본 정렬 배열에서의 lower bound 검색 검증",
            None,
        ),
        (
            "hidden_all_smaller",
            [1, 2, 3, 4],
            5,
            "hidden",
            "모든 원소가 X보다 작아 결과가 N이 되는 상태 검증",
            None,
        ),
        (
            "edge_minimum",
            [10],
            5,
            "edge",
            "단일 원소 배열에서 X 이상인 원소의 인덱스 검색 검증",
            None,
        ),
        (
            "hidden_all_larger",
            [10, 20, 30],
            5,
            "hidden",
            "모든 원소가 X보다 커서 결과가 0이 되는 상태 검증",
            None,
        ),
        (
            "edge_duplicate_first",
            [5, 5, 5, 5],
            5,
            "edge",
            "동일한 원소들이 반복될 때 첫 인덱스 검증",
            None,
        ),
    ]

    extra_index = 1
    while len(cases_data) < min_cases:
        arr = sorted([i for i in range(1, extra_index + 4)])
        cases_data.append((
            f"hidden_extra_{extra_index}",
            arr,
            extra_index + 1,
            "hidden",
            f"추가 자동 생성 케이스 {extra_index}",
            None,
        ))
        extra_index += 1

    testcases = []
    for name, arr, target_x, vis, purpose, diff_reason in cases_data:
        tc = build_lower_bound_count_case(
            name=name,
            array=arr,
            x=target_x,
            visibility=vis,
            purpose=purpose,
            difficulty_reason=diff_reason,
        )
        testcases.append(tc)

    bundle = TestcaseBundle(
        problem_id=problem_id,
        testcases=testcases,
        generation_notes="Generated deterministically for lower bound count.",
        generation_mode="deterministic",
        generator_name="lower_bound_count",
        verification_status="passed",
    )
    assert_lower_bound_count_bundle_is_valid(bundle)
    return bundle
