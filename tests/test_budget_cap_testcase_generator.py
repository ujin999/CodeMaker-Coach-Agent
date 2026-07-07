import pytest
from agent.testcase_generators.budget_cap import (
    solve_budget_cap,
    generate_budget_cap_testcases,
    parse_budget_cap_input,
    verify_budget_cap_output,
    assert_budget_cap_case_is_valid,
    assert_budget_cap_bundle_is_valid,
)
from agent.schemas import TestcaseBundle, GeneratedTestcase


def test_solve_budget_cap():
    """Test solve_budget_cap with the specified test cases."""
    assert solve_budget_cap([30, 40, 50], 100) == 35
    assert solve_budget_cap([100, 200, 300, 400, 500], 1500) == 500
    assert solve_budget_cap([1000, 2000, 3000, 4000], 5000) == 1333
    assert solve_budget_cap([1], 1) == 1
    assert solve_budget_cap([1000000, 1000000], 1000000) == 500000
    assert solve_budget_cap([100, 200, 300], 50) == 16


def test_parse_budget_cap_input_valid():
    """Test parse_budget_cap_input with valid inputs."""
    input_data = "3\n30 40 50\n100"
    reqs, budget = parse_budget_cap_input(input_data)
    assert reqs == [30, 40, 50]
    assert budget == 100


def test_parse_budget_cap_input_invalid_n_mismatch():
    """Test parse_budget_cap_input raises error when N does not match count."""
    input_data = "4\n30 40 50\n100"
    with pytest.raises(ValueError, match="does not match the number of requests"):
        parse_budget_cap_input(input_data)


def test_parse_budget_cap_input_invalid_format():
    """Test parse_budget_cap_input raises error for bad inputs."""
    with pytest.raises(ValueError):
        parse_budget_cap_input("not_number\n30 40 50\n100")
    with pytest.raises(ValueError):
        parse_budget_cap_input("3\n30 40 50\n-5")
    with pytest.raises(ValueError):
        parse_budget_cap_input("3\n30 -40 50\n100")


def test_verify_budget_cap_output_correct():
    """Test verify_budget_cap_output returns True for correct outputs."""
    is_correct, exp, comp = verify_budget_cap_output("3\n30 40 50\n100", "35")
    assert is_correct is True
    assert exp == 35
    assert comp == 35


def test_verify_budget_cap_output_incorrect():
    """Test verify_budget_cap_output returns False for incorrect outputs."""
    is_correct, exp, comp = verify_budget_cap_output("3\n30 40 50\n100", "36")
    assert is_correct is False
    assert exp == 36
    assert comp == 35


def test_assert_budget_cap_case_is_valid_raises():
    """Test assert_budget_cap_case_is_valid raises AssertionError for wrong output."""
    tc = GeneratedTestcase(
        name="test_fail",
        input_data="3\n30 40 50\n100",
        expected_output="36",
        visibility="sample",
        purpose="should fail",
    )
    with pytest.raises(AssertionError):
        assert_budget_cap_case_is_valid(tc)


def test_generate_budget_cap_testcases():
    """Verify that generate_budget_cap_testcases returns valid TestcaseBundle."""
    problem_id = "test-problem-123"
    min_cases = 5
    bundle = generate_budget_cap_testcases(problem_id, min_cases=min_cases)

    assert isinstance(bundle, TestcaseBundle)
    assert bundle.problem_id == problem_id
    assert len(bundle.testcases) >= min_cases

    # Check optional fields if schema supports them
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "budget_cap"
    assert bundle.verification_status == "passed"

    # Includes at least one sample testcase
    assert any(tc.visibility == "sample" for tc in bundle.testcases)

    # Includes hidden or edge cases
    assert any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)

    # Every testcase expected_output matches solve_budget_cap()
    for tc in bundle.testcases:
        lines = tc.input_data.strip().split("\n")
        assert len(lines) == 3
        requests = list(map(int, lines[1].split()))
        budget = int(lines[2])

        expected_c = solve_budget_cap(requests, budget)
        assert tc.expected_output == str(expected_c)
        assert tc.calculation_steps is not None
        assert len(tc.calculation_steps.strip()) > 0
