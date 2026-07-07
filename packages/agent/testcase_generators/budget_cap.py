from typing import Literal
from agent.schemas import GeneratedTestcase, TestcaseBundle


def solve_budget_cap(requests: list[int], budget: int) -> int:
    """
    Return the maximum integer cap C in [0, max(requests)]
    such that sum(min(request, C) for request in requests) <= budget.
    Use binary search.
    """
    if not requests:
        return 0

    low = 0
    high = max(requests)
    ans = 0

    while low <= high:
        mid = (low + high) // 2
        current_sum = sum(min(req, mid) for req in requests)
        if current_sum <= budget:
            ans = mid
            low = mid + 1
        else:
            high = mid - 1

    return ans


def parse_budget_cap_input(input_data: str) -> tuple[list[int], int]:
    """
    Parse input format:
    N
    request_1 request_2 ... request_N
    B

    Validate:
    - exactly 3 non-empty lines
    - N matches the number of requests
    - all requests are positive integers
    - budget is non-negative integer
    """
    lines = [line.strip() for line in input_data.strip().splitlines() if line.strip()]
    if len(lines) != 3:
        raise ValueError("Input data must contain exactly 3 non-empty lines.")

    try:
        n = int(lines[0])
    except ValueError:
        raise ValueError("N must be an integer.")

    try:
        requests = [int(x) for x in lines[1].split()]
    except ValueError:
        raise ValueError("Requests must be integers.")

    try:
        budget = int(lines[2])
    except ValueError:
        raise ValueError("Budget must be an integer.")

    if len(requests) != n:
        raise ValueError(f"N ({n}) does not match the number of requests ({len(requests)}).")

    if any(req <= 0 for req in requests):
        raise ValueError("All requests must be positive integers.")

    if budget < 0:
        raise ValueError("Budget must be a non-negative integer.")

    return requests, budget


def verify_budget_cap_output(
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
        requests, budget = parse_budget_cap_input(input_data)
        expected_output_as_int = int(expected_output.strip())
    except Exception:
        return False, -1, -2

    computed_output_from_solver = solve_budget_cap(requests, budget)
    is_correct = (expected_output_as_int == computed_output_from_solver)
    return is_correct, expected_output_as_int, computed_output_from_solver


def assert_budget_cap_case_is_valid(testcase: GeneratedTestcase) -> None:
    """
    Parse testcase.input_data and verify testcase.expected_output
    using solve_budget_cap().
    Raise AssertionError if mismatched.
    """
    is_correct, exp_val, comp_val = verify_budget_cap_output(
        testcase.input_data, testcase.expected_output
    )
    if not is_correct:
        raise AssertionError(
            f"Testcase expected_output mismatch. Expected: {exp_val}, Solver computed: {comp_val}."
        )


def assert_budget_cap_bundle_is_valid(bundle: TestcaseBundle) -> None:
    """
    Verify every testcase in a bundle.
    Ensure at least one sample testcase exists.
    Ensure at least one hidden or edge testcase exists if len(testcases) >= 2.
    """
    for tc in bundle.testcases:
        assert_budget_cap_case_is_valid(tc)

    has_sample = any(tc.visibility == "sample" for tc in bundle.testcases)
    if not has_sample:
        raise AssertionError("Bundle must contain at least one sample testcase.")

    if len(bundle.testcases) >= 2:
        has_hidden_or_edge = any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)
        if not has_hidden_or_edge:
            raise AssertionError(
                "Bundle must contain at least one hidden or edge testcase when total cases >= 2."
            )


def build_budget_cap_case(
    name: str,
    requests: list[int],
    budget: int,
    visibility: Literal["sample", "hidden", "edge"],
    purpose: str,
    difficulty_reason: str | None = None,
) -> GeneratedTestcase:
    """
    Build input_data from requests and budget.
    Compute expected_output using solve_budget_cap().
    Fill calculation_steps deterministically.
    """
    input_data = f"{len(requests)}\n" + " ".join(map(str, requests)) + f"\n{budget}"
    c_val = solve_budget_cap(requests, budget)
    expected_output = str(c_val)

    sum_c = sum(min(req, c_val) for req in requests)
    sum_c_plus_1 = sum(min(req, c_val + 1) for req in requests)

    if c_val == max(requests):
        calculation_steps = (
            f"C={c_val}일 때 sum(min(request_i, C)) = {sum_c} <= {budget}이고, "
            f"모든 요청의 합이 예산 이하이므로 정답은 {c_val}입니다."
        )
    else:
        calculation_steps = (
            f"C={c_val}일 때 sum(min(request_i, C)) = {sum_c} <= {budget}이고, "
            f"C={c_val + 1}일 때 sum(min(request_i, C)) = {sum_c_plus_1} > {budget}이므로 정답은 {c_val}입니다."
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
    
    # Call validation check before returning
    assert_budget_cap_case_is_valid(tc)
    return tc


def generate_budget_cap_testcases(problem_id: str, min_cases: int = 5) -> TestcaseBundle:
    """
    Generate deterministic sample, hidden, and edge cases for budget cap / parametric search problems.
    All expected_output values must be computed by solve_budget_cap().
    """
    cases_data = [
        # (name, requests, budget, visibility, purpose, difficulty_reason)
        (
            "sample_1",
            [30, 40, 50],
            100,
            "sample",
            "기본적인 예산 배정 시나리오 및 예산 캡 탐색 검증",
            None,
        ),
        (
            "hidden_all_granted",
            [100, 200, 300, 400, 500],
            1500,
            "hidden",
            "모든 요청을 전액 배정할 수 있는 최대 상한선 설정 여부 검증",
            "모든 요청의 합이 예산 이하인 경계 상태",
        ),
        (
            "edge_minimum",
            [1],
            1,
            "edge",
            "단일 요청 및 최소 예산 배정 조건 검증",
            "최소 크기의 N 및 예산 조건",
        ),
        (
            "hidden_general_parametric",
            [1000, 2000, 3000, 4000],
            5000,
            "hidden",
            "N개 요청에 대해 예산 총액 한도 내에서 최적의 정수 상한 계산 검증",
            "일반적인 값 범위에서의 최적 캡 탐색",
        ),
        (
            "edge_large_values",
            [1000000, 1000000],
            1000000,
            "edge",
            "큰 스케일의 요청 값에 대한 정확성 및 효율성 검증",
            "큰 정수 값 범위 처리 및 오버플로우 방지",
        ),
        (
            "hidden_tight_budget",
            [100, 200, 300],
            50,
            "hidden",
            "매우 타이트한 예산 분배 시 최적의 상한선 결정 검증",
            "전체 예산에 비해 개별 요청들이 매우 클 때의 분배",
        ),
    ]

    # If more cases are needed, generate them deterministically
    extra_index = 1
    while len(cases_data) < min_cases:
        reqs = [10 * i for i in range(1, extra_index + 4)]
        bg = sum(reqs) // 2
        cases_data.append((
            f"hidden_extra_{extra_index}",
            reqs,
            bg,
            "hidden",
            f"추가적인 자동 생성 예산 배정 검증 케이스 {extra_index}",
            None,
        ))
        extra_index += 1

    testcases = []
    for name, reqs, bg, vis, purpose, diff_reason in cases_data:
        tc = build_budget_cap_case(
            name=name,
            requests=reqs,
            budget=bg,
            visibility=vis,
            purpose=purpose,
            difficulty_reason=diff_reason,
        )
        testcases.append(tc)

    bundle = TestcaseBundle(
        problem_id=problem_id,
        testcases=testcases,
        generation_notes="Generated deterministically using solve_budget_cap solver.",
        generation_mode="deterministic",
        generator_name="budget_cap",
        verification_status="passed",
    )
    
    # Call validation check before returning
    assert_budget_cap_bundle_is_valid(bundle)
    return bundle

