import pytest
from agent.testcase_generators.two_pointer_subarray import (
    solve_two_pointer_subarray,
    parse_two_pointer_subarray_input,
    verify_two_pointer_subarray_output,
    assert_two_pointer_subarray_case_is_valid,
    assert_two_pointer_subarray_bundle_is_valid,
    generate_two_pointer_subarray_testcases,
)
from agent.schemas import TestcaseBundle, GeneratedTestcase


def test_solve_two_pointer_subarray():
    """Verify solve_two_pointer_subarray solver logic with typical cases."""
    assert solve_two_pointer_subarray([1, 2, 3, 4, 5], 7) == 3
    assert solve_two_pointer_subarray([1, 1, 1, 1], 10) == 4
    assert solve_two_pointer_subarray([5, 6, 7], 4) == 0
    assert solve_two_pointer_subarray([2, 1, 3, 2, 1, 1, 5], 5) == 3
    assert solve_two_pointer_subarray([10], 10) == 1
    assert solve_two_pointer_subarray([3, 1, 2, 1, 1, 4, 2], 6) == 4


def test_parse_two_pointer_subarray_input_valid():
    """Verify parsing valid two pointer subarray input."""
    input_data = "5 7\n1 2 3 4 5"
    nums, k = parse_two_pointer_subarray_input(input_data)
    assert nums == [1, 2, 3, 4, 5]
    assert k == 7


def test_parse_two_pointer_subarray_input_n_mismatch():
    """Verify ValueError is raised if N does not match count."""
    input_data = "6 7\n1 2 3 4 5"
    with pytest.raises(ValueError, match="does not match the number of elements"):
        parse_two_pointer_subarray_input(input_data)


def test_parse_two_pointer_subarray_input_invalid_values():
    """Verify ValueError is raised for non-positive or negative values."""
    # Zero or negative nums
    with pytest.raises(ValueError, match="positive integers"):
        parse_two_pointer_subarray_input("3 5\n1 0 3")
    with pytest.raises(ValueError, match="positive integers"):
        parse_two_pointer_subarray_input("3 5\n1 -2 3")
    # Negative K
    with pytest.raises(ValueError, match="non-negative"):
        parse_two_pointer_subarray_input("3 -5\n1 2 3")


def test_verify_two_pointer_subarray_output():
    """Verify verify_two_pointer_subarray_output returns correctness status."""
    input_data = "5 7\n1 2 3 4 5"
    # Correct case
    is_correct, exp, comp = verify_two_pointer_subarray_output(input_data, "3")
    assert is_correct is True
    assert exp == 3
    assert comp == 3

    # Incorrect case
    is_correct, exp, comp = verify_two_pointer_subarray_output(input_data, "4")
    assert is_correct is False
    assert exp == 4
    assert comp == 3


def test_assert_two_pointer_subarray_case_is_valid_raises():
    """Verify assert_two_pointer_subarray_case_is_valid raises AssertionError on mismatch."""
    tc = GeneratedTestcase(
        name="test_case",
        input_data="5 7\n1 2 3 4 5",
        expected_output="4",  # incorrect
        visibility="sample",
        purpose="assert fail",
    )
    with pytest.raises(AssertionError, match="expected_output mismatch"):
        assert_two_pointer_subarray_case_is_valid(tc)


def test_generate_two_pointer_subarray_testcases():
    """Verify generate_two_pointer_subarray_testcases returns correct TestcaseBundle."""
    problem_id = "test-two-pointer-id"
    min_cases = 5
    bundle = generate_two_pointer_subarray_testcases(problem_id, min_cases=min_cases)

    assert isinstance(bundle, TestcaseBundle)
    assert bundle.problem_id == problem_id
    assert len(bundle.testcases) >= min_cases

    # Verify metadata fields
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "two_pointer_subarray"
    assert bundle.verification_status == "passed"

    # Verify visibility constraints
    assert any(tc.visibility == "sample" for tc in bundle.testcases)
    assert any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)

    # Verify every testcase in the generated bundle
    for tc in bundle.testcases:
        lines = tc.input_data.strip().split("\n")
        assert len(lines) == 2
        n, k = map(int, lines[0].split())
        nums = list(map(int, lines[1].split()))

        # Re-solve and compare
        expected_ans = solve_two_pointer_subarray(nums, k)
        assert tc.expected_output == str(expected_ans)
        assert tc.calculation_steps is not None
        assert len(tc.calculation_steps.strip()) > 0
