from typing import Literal
from agent.schemas import GeneratedTestcase, TestcaseBundle


def solve_two_pointer_subarray(nums: list[int], k: int) -> int:
    """
    Return the maximum length of a contiguous subarray whose sum <= k.
    All nums must be positive integers.
    Use deterministic two-pointer / sliding-window logic.
    """
    if not nums:
        raise ValueError("nums must not be empty")
    if any(x <= 0 for x in nums):
        raise ValueError("all nums must be positive integers")
    if k < 0:
        raise ValueError("k must be non-negative")

    left = 0
    current_sum = 0
    max_len = 0
    for right in range(len(nums)):
        current_sum += nums[right]
        while current_sum > k and left <= right:
            current_sum -= nums[left]
            left += 1
        if current_sum <= k:
            max_len = max(max_len, right - left + 1)
    return max_len


def parse_two_pointer_subarray_input(input_data: str) -> tuple[list[int], int]:
    """
    Parse:
    N K
    a1 a2 ... aN

    Validate:
    - exactly 2 non-empty lines
    - first line has exactly N and K
    - N matches len(nums)
    - all nums are positive integers
    - K is non-negative
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
        nums = [int(x) for x in lines[1].split()]
    except ValueError:
        raise ValueError("Numbers must be integers.")

    if len(nums) != n:
        raise ValueError(f"N ({n}) does not match the number of elements ({len(nums)}).")

    if any(x <= 0 for x in nums):
        raise ValueError("All numbers must be positive integers.")

    if k < 0:
        raise ValueError("K must be non-negative.")

    return nums, k


def verify_two_pointer_subarray_output(
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
        nums, k = parse_two_pointer_subarray_input(input_data)
        expected_output_as_int = int(expected_output.strip())
    except Exception:
        return False, -1, -2

    computed_output_from_solver = solve_two_pointer_subarray(nums, k)
    is_correct = (expected_output_as_int == computed_output_from_solver)
    return is_correct, expected_output_as_int, computed_output_from_solver


def assert_two_pointer_subarray_case_is_valid(testcase: GeneratedTestcase) -> None:
    """
    Verify one testcase using solve_two_pointer_subarray().
    Raise AssertionError on mismatch.
    """
    is_correct, exp_val, comp_val = verify_two_pointer_subarray_output(
        testcase.input_data, testcase.expected_output
    )
    if not is_correct:
        raise AssertionError(
            f"Testcase expected_output mismatch. Expected: {exp_val}, Solver computed: {comp_val}."
        )


def assert_two_pointer_subarray_bundle_is_valid(bundle: TestcaseBundle) -> None:
    """
    Verify every testcase.
    Ensure at least one sample testcase.
    Ensure hidden or edge exists if len(testcases) >= 2.
    Ensure metadata fields are correct if present.
    """
    for tc in bundle.testcases:
        assert_two_pointer_subarray_case_is_valid(tc)

    has_sample = any(tc.visibility == "sample" for tc in bundle.testcases)
    if not has_sample:
        raise AssertionError("Bundle must contain at least one sample testcase.")

    if len(bundle.testcases) >= 2:
        has_hidden_or_edge = any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)
        if not has_hidden_or_edge:
            raise AssertionError(
                "Bundle must contain at least one hidden or edge testcase when total cases >= 2."
            )

    if getattr(bundle, "generation_mode", None) != "deterministic":
        raise AssertionError("bundle.generation_mode must be 'deterministic'")
    if getattr(bundle, "generator_name", None) != "two_pointer_subarray":
        raise AssertionError("bundle.generator_name must be 'two_pointer_subarray'")
    if getattr(bundle, "verification_status", None) != "passed":
        raise AssertionError("bundle.verification_status must be 'passed'")


def build_two_pointer_subarray_case(
    name: str,
    nums: list[int],
    k: int,
    visibility: Literal["sample", "hidden", "edge"],
    purpose: str,
    difficulty_reason: str | None = None,
) -> GeneratedTestcase:
    """
    Build input_data.
    Compute expected_output only with solve_two_pointer_subarray().
    Fill calculation_steps deterministically.
    Validate before returning.
    """
    input_data = f"{len(nums)} {k}\n" + " ".join(map(str, nums))
    ans = solve_two_pointer_subarray(nums, k)
    expected_output = str(ans)

    example_subarray = []
    if ans > 0:
        for i in range(len(nums) - ans + 1):
            sub = nums[i : i + ans]
            if sum(sub) <= k:
                example_subarray = sub
                break

    if ans > 0:
        sub_str = ", ".join(map(str, example_subarray))
        calculation_steps = (
            f"투 포인터로 윈도우 합이 K 이하인 가장 긴 연속 구간을 확인하면 최대 길이는 {ans}입니다. "
            f"예: [{sub_str}]의 합은 {sum(example_subarray)} <= {k}입니다."
        )
    else:
        calculation_steps = (
            f"모든 단일 원소의 값조차 K={k}를 초과하므로 만족하는 연속 부분 배열이 존재하지 않아 최대 길이는 0입니다."
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
    assert_two_pointer_subarray_case_is_valid(tc)
    return tc


def generate_two_pointer_subarray_testcases(
    problem_id: str,
    min_cases: int = 5,
) -> TestcaseBundle:
    """
    Generate deterministic sample, hidden, and edge cases.
    All expected outputs must be computed by solve_two_pointer_subarray().
    """
    cases_data = [
        # (name, nums, k, visibility, purpose, difficulty_reason)
        (
            "sample_1",
            [1, 2, 3, 4, 5],
            7,
            "sample",
            "기본적인 양의 정수 배열에 대한 연속 구간 최대 길이 검증",
            None,
        ),
        (
            "hidden_all_possible",
            [1, 1, 1, 1],
            10,
            "hidden",
            "모든 원소의 합이 K보다 작거나 같아 전체 배열이 선택되는 경계 상태 검증",
            "배열 전체가 윈도우에 들어오는 상태",
        ),
        (
            "edge_none_possible",
            [5, 6, 7],
            4,
            "edge",
            "모든 개별 원소가 K보다 커서 만족하는 부분 배열이 없는 예외 상황 검증",
            "길이가 0이 되는 극단적인 조건",
        ),
        (
            "hidden_tight_window",
            [2, 1, 3, 2, 1, 1, 5],
            5,
            "hidden",
            "복잡한 구간 합 조건에서 최대 길이를 정확히 포착하는지 검증",
            "윈도우 크기가 동적으로 조절되는 복잡한 시나리오",
        ),
        (
            "edge_single_item",
            [10],
            10,
            "edge",
            "단일 원소가 입력으로 주어졌을 때의 처리 여부 검증",
            "최소 배열 길이 조건",
        ),
        (
            "hidden_varied_elements",
            [3, 1, 2, 1, 1, 4, 2],
            6,
            "hidden",
            "원소 값이 다양하게 구성된 상황에서 최대 길이 탐색 검증",
            None,
        ),
    ]

    # Generate deterministic extra cases if min_cases is larger
    extra_index = 1
    while len(cases_data) < min_cases:
        extra_nums = [2] + [1] * (extra_index + 1)
        extra_k = extra_index + 1
        cases_data.append((
            f"hidden_extra_{extra_index}",
            extra_nums,
            extra_k,
            "hidden",
            f"추가적인 자동 생성 투 포인터 검증 케이스 {extra_index}",
            None,
        ))
        extra_index += 1

    testcases = []
    for name, nums, k, vis, purpose, diff_reason in cases_data:
        tc = build_two_pointer_subarray_case(
            name=name,
            nums=nums,
            k=k,
            visibility=vis,
            purpose=purpose,
            difficulty_reason=diff_reason,
        )
        testcases.append(tc)

    bundle = TestcaseBundle(
        problem_id=problem_id,
        testcases=testcases,
        generation_notes="Generated deterministically using solve_two_pointer_subarray solver.",
        generation_mode="deterministic",
        generator_name="two_pointer_subarray",
        verification_status="passed",
    )

    assert_two_pointer_subarray_bundle_is_valid(bundle)
    return bundle
