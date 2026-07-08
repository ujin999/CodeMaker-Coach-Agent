import pytest
from agent.testcase_generators.immigration_time import (
    solve_immigration_time,
    generate_immigration_time_testcases,
    parse_immigration_time_input,
    verify_immigration_time_output,
    assert_immigration_time_case_is_valid,
    assert_immigration_time_bundle_is_valid,
)
from agent.schemas import TestcaseBundle, GeneratedTestcase


def test_solve_immigration_time():
    assert solve_immigration_time([7, 10], 6) == 28
    assert solve_immigration_time([1, 2, 3], 10) == 6


def test_parse_immigration_time_input_valid():
    input_data = "2 6\n7 10"
    times, m = parse_immigration_time_input(input_data)
    assert times == [7, 10]
    assert m == 6


def test_parse_immigration_time_input_invalid():
    with pytest.raises(ValueError):
        parse_immigration_time_input("2 6\n7")
    with pytest.raises(ValueError):
        parse_immigration_time_input("2 0\n7 10")


def test_verify_immigration_time_output():
    is_correct, exp, comp = verify_immigration_time_output("2 6\n7 10", "28")
    assert is_correct is True
    assert exp == 28
    assert comp == 28


def test_generate_immigration_time_testcases():
    problem_id = "test-immigration"
    bundle = generate_immigration_time_testcases(problem_id, min_cases=5)
    assert isinstance(bundle, TestcaseBundle)
    assert bundle.problem_id == problem_id
    assert len(bundle.testcases) >= 5
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "immigration_time"
    assert bundle.verification_status == "passed"
