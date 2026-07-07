import pytest
from pydantic import ValidationError
from agent.schemas import Hint, HintBlueprint, GeneratedTestcase, TestcaseBundle


def test_hint_validation_level_fails():
    """Verify Hint level must be 1, 2, or 3."""
    with pytest.raises(ValidationError) as excinfo:
        Hint(
            problem_id="prob_1",
            level=4, # invalid level
            title="Invalid Hint",
            content="Try dividing the array.",
            reveals_core_code=False
        )
    assert "level" in str(excinfo.value)


def test_hint_validation_reveals_code_fails():
    """Verify Hint reveals_core_code must always be False."""
    with pytest.raises(ValidationError) as excinfo:
        Hint(
            problem_id="prob_1",
            level=2,
            title="Invalid Hint",
            content="Check target values.",
            reveals_core_code=True # invalid value
        )
    assert "reveals_core_code" in str(excinfo.value)


def test_hint_validation_full_solution_rejected():
    """Verify obvious full solution code in hint content is rejected."""
    # Obvious Python solution code without placeholders
    full_python_code = (
        "def solve(arr, target):\n"
        "    for val in arr:\n"
        "        if val == target:\n"
        "            return True\n"
        "    return False"
    )
    
    with pytest.raises(ValidationError) as excinfo:
        Hint(
            problem_id="prob_1",
            level=3,
            title="Avoid this",
            content=f"Here is the complete solution:\n{full_python_code}",
            reveals_core_code=False
        )
    assert "Obvious full solution code detected" in str(excinfo.value)


def test_hint_validation_skeleton_incomplete_succeeds():
    """Verify code skeleton with incomplete placeholders is allowed."""
    skeleton_code = (
        "def solve(arr, target):\n"
        "    # TODO: fill logic here\n"
        "    for val in arr:\n"
        "        if val == target:\n"
        "            pass # ...\n"
        "    return False"
    )
    
    hint = Hint(
        problem_id="prob_1",
        level=3,
        title="Skeleton",
        content="Here is a helper structure.",
        reveals_core_code=False,
        code_skeleton=skeleton_code
    )
    assert hint.code_skeleton == skeleton_code


def test_hint_validation_skeleton_complete_rejected():
    """Verify code skeleton that is actually complete gets rejected."""
    complete_skeleton = (
        "def solve(arr, target):\n"
        "    return sorted(arr)"
    )
    
    with pytest.raises(ValidationError) as excinfo:
        Hint(
            problem_id="prob_1",
            level=3,
            title="Completed Skeleton",
            content="Here is complete code.",
            reveals_core_code=False,
            code_skeleton=complete_skeleton
        )
    assert "code_skeleton must be incomplete" in str(excinfo.value)


def test_testcase_bundle_validation_fails_without_sample():
    """Verify TestcaseBundle must include at least one sample testcase."""
    tc_hidden = GeneratedTestcase(
        name="tc_1",
        input_data="1 2 3",
        expected_output="6",
        visibility="hidden",
        purpose="general hidden test"
    )
    
    with pytest.raises(ValidationError) as excinfo:
        TestcaseBundle(
            problem_id="prob_1",
            testcases=[tc_hidden], # only hidden case, missing sample
            generation_notes="Notes"
        )
    assert "must include at least one sample testcase" in str(excinfo.value)


def test_testcase_bundle_validation_succeeds_with_sample():
    """Verify TestcaseBundle succeeds with a sample testcase."""
    tc_sample = GeneratedTestcase(
        name="tc_1",
        input_data="1 2 3",
        expected_output="6",
        visibility="sample",
        purpose="sample case"
    )
    tc_edge = GeneratedTestcase(
        name="tc_2",
        input_data="0",
        expected_output="0",
        visibility="edge",
        purpose="edge case"
    )
    
    bundle = TestcaseBundle(
        problem_id="prob_1",
        testcases=[tc_sample, tc_edge],
        generation_notes="Notes"
    )
    assert len(bundle.testcases) == 2
