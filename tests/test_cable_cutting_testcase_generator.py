import pytest
from agent.testcase_generators.cable_cutting import (
    solve_cable_cutting,
    generate_cable_cutting_testcases,
    parse_cable_cutting_input,
    verify_cable_cutting_output,
    assert_cable_cutting_case_is_valid,
    assert_cable_cutting_bundle_is_valid,
)
from agent.schemas import TestcaseBundle, GeneratedTestcase


def test_solve_cable_cutting():
    assert solve_cable_cutting([802, 743, 457, 539], 11) == 200
    assert solve_cable_cutting([10, 20, 30], 100) == 0


def test_parse_cable_cutting_input_valid():
    input_data = "4 11\n802 743 457 539"
    lengths, k = parse_cable_cutting_input(input_data)
    assert lengths == [802, 743, 457, 539]
    assert k == 11


def test_parse_cable_cutting_input_invalid():
    with pytest.raises(ValueError):
        parse_cable_cutting_input("3 11\n802 743")
    with pytest.raises(ValueError):
        parse_cable_cutting_input("4 11\n802 743 457 -5")


def test_verify_cable_cutting_output():
    is_correct, exp, comp = verify_cable_cutting_output("4 11\n802 743 457 539", "200")
    assert is_correct is True
    assert exp == 200
    assert comp == 200


def test_generate_cable_cutting_testcases():
    problem_id = "test-cable-cutting"
    bundle = generate_cable_cutting_testcases(problem_id, min_cases=5)
    assert isinstance(bundle, TestcaseBundle)
    assert bundle.problem_id == problem_id
    assert len(bundle.testcases) >= 5
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "cable_cutting"
    assert bundle.verification_status == "passed"
