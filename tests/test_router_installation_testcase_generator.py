import pytest
from agent.testcase_generators.router_installation import (
    solve_router_installation,
    generate_router_installation_testcases,
    parse_router_installation_input,
    verify_router_installation_output,
    assert_router_installation_case_is_valid,
    assert_router_installation_bundle_is_valid,
)
from agent.schemas import TestcaseBundle, GeneratedTestcase


def test_solve_router_installation():
    assert solve_router_installation([1, 2, 8, 4, 9], 3) == 3
    assert solve_router_installation([1, 10], 2) == 9


def test_parse_router_installation_input_valid():
    input_data = "5 3\n1 2 8 4 9"
    coords, c = parse_router_installation_input(input_data)
    assert coords == [1, 2, 8, 4, 9]
    assert c == 3


def test_parse_router_installation_input_invalid():
    with pytest.raises(ValueError):
        parse_router_installation_input("3 3\n1 2")
    with pytest.raises(ValueError):
        parse_router_installation_input("3 1\n1 2 3")


def test_verify_router_installation_output():
    is_correct, exp, comp = verify_router_installation_output("5 3\n1 2 8 4 9", "3")
    assert is_correct is True
    assert exp == 3
    assert comp == 3


def test_generate_router_installation_testcases():
    problem_id = "test-router"
    bundle = generate_router_installation_testcases(problem_id, min_cases=5)
    assert isinstance(bundle, TestcaseBundle)
    assert bundle.problem_id == problem_id
    assert len(bundle.testcases) >= 5
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "router_installation"
    assert bundle.verification_status == "passed"
