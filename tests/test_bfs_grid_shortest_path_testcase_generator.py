import pytest
from agent.testcase_generators.bfs_grid_shortest_path import (
    solve_bfs_grid_shortest_path,
    parse_bfs_grid_input,
    verify_bfs_grid_output,
    assert_bfs_grid_case_is_valid,
    assert_bfs_grid_bundle_is_valid,
    generate_bfs_grid_shortest_path_testcases,
)
from agent.schemas import TestcaseBundle, GeneratedTestcase


def test_solve_bfs_grid_shortest_path():
    """Test solve_bfs_grid_shortest_path with the specified test cases."""
    assert solve_bfs_grid_shortest_path(["000", "110", "000"]) == 5
    assert solve_bfs_grid_shortest_path(["00", "00"]) == 3
    assert solve_bfs_grid_shortest_path(["010", "111", "000"]) == -1
    assert solve_bfs_grid_shortest_path(["0"]) == 1
    assert solve_bfs_grid_shortest_path(["10", "00"]) == -1
    assert solve_bfs_grid_shortest_path(["00", "01"]) == -1


def test_parse_bfs_grid_input_valid():
    """Test parse_bfs_grid_input with valid inputs."""
    input_data = "3 3\n000\n110\n000"
    grid = parse_bfs_grid_input(input_data)
    assert grid == ["000", "110", "000"]


def test_parse_bfs_grid_input_invalid_n_mismatch():
    """Test parse_bfs_grid_input raises ValueError when N does not match rows count."""
    input_data = "4 3\n000\n110\n000"
    with pytest.raises(ValueError, match="does not match N"):
        parse_bfs_grid_input(input_data)


def test_parse_bfs_grid_input_invalid_m_mismatch():
    """Test parse_bfs_grid_input raises ValueError when a row length does not match M."""
    input_data = "3 3\n000\n1100\n000"
    with pytest.raises(ValueError, match="does not match M"):
        parse_bfs_grid_input(input_data)


def test_parse_bfs_grid_input_invalid_characters():
    """Test parse_bfs_grid_input raises ValueError when row contains non-0/1 characters."""
    input_data = "3 3\n000\n112\n000"
    with pytest.raises(ValueError, match="contains invalid character"):
        parse_bfs_grid_input(input_data)


def test_parse_bfs_grid_input_empty():
    """Test parse_bfs_grid_input raises ValueError for empty inputs."""
    with pytest.raises(ValueError):
        parse_bfs_grid_input("")
    with pytest.raises(ValueError):
        parse_bfs_grid_input("0 0")


def test_verify_bfs_grid_output_correct():
    """Test verify_bfs_grid_output returns True for correct outputs."""
    is_correct, exp, comp = verify_bfs_grid_output("3 3\n000\n110\n000", "5")
    assert is_correct is True
    assert exp == 5
    assert comp == 5


def test_verify_bfs_grid_output_incorrect():
    """Test verify_bfs_grid_output returns False for incorrect outputs."""
    is_correct, exp, comp = verify_bfs_grid_output("3 3\n000\n110\n000", "6")
    assert is_correct is False
    assert exp == 6
    assert comp == 5


def test_assert_bfs_grid_case_is_valid_raises():
    """Test assert_bfs_grid_case_is_valid raises AssertionError for wrong output."""
    tc = GeneratedTestcase(
        name="test_fail",
        input_data="3 3\n000\n110\n000",
        expected_output="6",
        visibility="sample",
        purpose="should fail",
    )
    with pytest.raises(AssertionError):
        assert_bfs_grid_case_is_valid(tc)


def test_generate_bfs_grid_shortest_path_testcases():
    """Verify that generate_bfs_grid_shortest_path_testcases returns valid TestcaseBundle."""
    problem_id = "test-bfs-problem-456"
    min_cases = 5
    bundle = generate_bfs_grid_shortest_path_testcases(problem_id, min_cases=min_cases)

    assert isinstance(bundle, TestcaseBundle)
    assert bundle.problem_id == problem_id
    assert len(bundle.testcases) >= min_cases

    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "bfs_grid_shortest_path"
    assert bundle.verification_status == "passed"

    # Includes at least one sample testcase
    assert any(tc.visibility == "sample" for tc in bundle.testcases)

    # Includes hidden or edge cases
    assert any(tc.visibility in ["hidden", "edge"] for tc in bundle.testcases)

    # Every testcase expected_output matches solve_bfs_grid_shortest_path()
    for tc in bundle.testcases:
        grid = parse_bfs_grid_input(tc.input_data)
        expected_ans = solve_bfs_grid_shortest_path(grid)
        assert tc.expected_output == str(expected_ans)
        assert tc.calculation_steps is not None
        assert len(tc.calculation_steps.strip()) > 0
