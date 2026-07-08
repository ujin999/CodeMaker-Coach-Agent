import pytest
from agent.testcase_generators.lower_bound_count import (
    solve_lower_bound_count,
    generate_lower_bound_count_testcases,
    parse_lower_bound_count_input,
    verify_lower_bound_count_output,
    assert_lower_bound_count_case_is_valid,
    assert_lower_bound_count_bundle_is_valid,
)
from agent.schemas import TestcaseBundle, GeneratedTestcase


def test_solve_lower_bound_count():
    assert solve_lower_bound_count([1, 3, 3, 5, 7], 3) == 1
    assert solve_lower_bound_count([1, 2, 3, 4], 5) == 4


def test_parse_lower_bound_count_input_valid():
    input_data = "5 3\n1 3 3 5 7"
    array, x = parse_lower_bound_count_input(input_data)
    assert array == [1, 3, 3, 5, 7]
    assert x == 3


def test_parse_lower_bound_count_input_invalid():
    with pytest.raises(ValueError):
        parse_lower_bound_count_input("5 3\n1 3 2 5 7")
    with pytest.raises(ValueError):
        parse_lower_bound_count_input("5 3\n1 3 3")


def test_verify_lower_bound_count_output():
    is_correct, exp, comp = verify_lower_bound_count_output("5 3\n1 3 3 5 7", "1")
    assert is_correct is True
    assert exp == 1
    assert comp == 1


def test_generate_lower_bound_count_testcases():
    problem_id = "test-lower-bound"
    bundle = generate_lower_bound_count_testcases(problem_id, min_cases=5)
    assert isinstance(bundle, TestcaseBundle)
    assert bundle.problem_id == problem_id
    assert len(bundle.testcases) >= 5
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "lower_bound_count"
    assert bundle.verification_status == "passed"
