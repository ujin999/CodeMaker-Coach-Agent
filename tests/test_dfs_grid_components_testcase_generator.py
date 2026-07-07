import pytest
from agent.testcase_generators.dfs_grid_components import (
    solve_dfs_grid_components,
    parse_dfs_grid_input,
    verify_dfs_grid_output,
    assert_dfs_grid_case_is_valid,
    assert_dfs_grid_bundle_is_valid,
    generate_dfs_grid_components_testcases,
)
from agent.schemas import TestcaseBundle, GeneratedTestcase


def test_solve_dfs_grid_components():
    """Test solve_dfs_grid_components with the specified test cases."""
    assert solve_dfs_grid_components(["11000", "11010", "00110", "00001"]) == 3
    assert solve_dfs_grid_components(["000", "000"]) == 0
    assert solve_dfs_grid_components(["111", "111"]) == 1
    assert solve_dfs_grid_components(["101", "010", "101"]) == 5
    assert solve_dfs_grid_components(["1"]) == 1
    assert solve_dfs_grid_components(["0"]) == 0


def test_parse_dfs_grid_input_valid():
    """Test parse_dfs_grid_input with valid inputs."""
    input_data = "4 5\n11000\n11010\n00110\n00001"
    grid = parse_dfs_grid_input(input_data)
    assert grid == ["11000", "11010", "00110", "00001"]


def test_parse_dfs_grid_input_invalid_n_mismatch():
    """Test parse_dfs_grid_input raises ValueError when N does not match rows count."""
    input_data = "5 5\n11000\n11010\n00110\n00001"
    with pytest.raises(ValueError, match="does not match N"):
        parse_dfs_grid_input(input_data)


def test_parse_dfs_grid_input_invalid_m_mismatch():
    """Test parse_dfs_grid_input raises ValueError when a row length does not match M."""
    input_data = "4 5\n11000\n110100\n00110\n00001"
    with pytest.raises(ValueError, match="does not match M"):
        parse_dfs_grid_input(input_data)


def test_parse_dfs_grid_input_invalid_characters():
    """Test parse_dfs_grid_input raises ValueError when row contains non-0/1 characters."""
    input_data = "4 5\n11000\n11020\n00110\n00001"
    with pytest.raises(ValueError, match="contains invalid character"):
        parse_dfs_grid_input(input_data)


def test_parse_dfs_grid_input_empty():
    """Test parse_dfs_grid_input raises ValueError for empty inputs."""
    with pytest.raises(ValueError):
        parse_dfs_grid_input("")
    with pytest.raises(ValueError):
        parse_dfs_grid_input("0 0")


def test_verify_dfs_grid_output_correct():
    """Test verify_dfs_grid_output returns True for correct outputs."""
    is_correct, exp, comp = verify_dfs_grid_output("4 5\n11000\n11010\n00110\n00001", "3")
    assert is_correct is True
    assert exp == 3
    assert comp == 3


def test_verify_dfs_grid_output_incorrect():
    """Test verify_dfs_grid_output returns False for incorrect outputs."""
    is_correct, exp, comp = verify_dfs_grid_output("4 5\n11000\n11010\n00110\n00001", "4")
    assert is_correct is False
    assert exp == 4
    assert comp == 3


def test_assert_dfs_grid_case_is_valid_raises():
    """Test assert_dfs_grid_case_is_valid raises AssertionError for wrong output."""
    tc = GeneratedTestcase(
        name="test_fail",
        input_data="4 5\n11000\n11010\n00110\n00001",
        expected_output="4",
        visibility="sample",
        purpose="should fail",
    )
    with pytest.raises(AssertionError):
        assert_dfs_grid_case_is_valid(tc)


def test_generate_dfs_grid_components_testcases():
    """Verify that generate_dfs_grid_components_testcases returns valid TestcaseBundle."""
    problem_id = "test-dfs-problem-789"
    min_cases = 5
    bundle = generate_dfs_grid_components_testcases(problem_id, min_cases=min_cases)

    assert isinstance(bundle, TestcaseBundle)
    assert bundle.problem_id == problem_id
    assert len(bundle.testcases) >= min_cases

    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "dfs_grid_components"
    assert bundle.verification_status == "passed"

    # Includes at least one sample testcase
    assert any(tc.visibility == "sample" for tc in bundle.testcases)

    # Includes hidden or edge cases
    assert any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)

    # Every testcase expected_output matches solve_dfs_grid_components()
    for tc in bundle.testcases:
        grid = parse_dfs_grid_input(tc.input_data)
        expected_ans = solve_dfs_grid_components(grid)
        assert tc.expected_output == str(expected_ans)
        assert tc.calculation_steps is not None
        assert len(tc.calculation_steps.strip()) > 0
