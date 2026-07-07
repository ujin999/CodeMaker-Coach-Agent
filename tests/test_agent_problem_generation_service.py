import asyncio
import inspect
import pytest
from agent.schemas import (
    GeneratedProblem,
    TestcaseBundle,
    ReferenceSolution,
    ValidationReport,
    HintBundle,
    ProblemGenerationPackageInput,
    ProblemGenerationPackage,
    HintBlueprint
)
from agent.services import (
    generate_problem_package,
    generate_problem_package_sync,
    problem_package_to_public_dict,
    problem_package_to_internal_dict
)


def mock_run_package_workflow(generation_input, min_cases=5, allowed_hint_level=3, user_situation=None, include_hints=True):
    # Dummy mock workflow state return
    prob = GeneratedProblem(
        problem_id="prob_123",
        title="Mock Problem",
        difficulty="easy",
        algorithm=["greedy"],
        learning_goal="Mock Goal",
        statement="Solve it",
        input_format="In",
        output_format="Out",
        constraints=[],
        expected_time_complexity="O(N)",
        hint_blueprint=HintBlueprint(
            intended_algorithm=["greedy"],
            core_insight="Insight",
            common_misconceptions=[],
            edge_case_focus=[],
            forbidden_disclosures=[],
            level_1_guidance="g1",
            level_2_guidance="g2",
            level_3_guidance="g3",
            allowed_code_exposure="skeleton_only"
        )
    )
    from agent.schemas import GeneratedTestcase
    tc = GeneratedTestcase(
        name="tc_1",
        input_data="1",
        expected_output="1",
        visibility="sample",
        purpose="sample"
    )
    testcases = TestcaseBundle(problem_id="prob_123", testcases=[tc], generation_notes="Mock Notes")
    ref = ReferenceSolution(problem_id="prob_123", code="def solve(): pass", language="python", generator_name="Mock Generator")
    val = ValidationReport(passed=True, issues=[], summary="Checked")
    
    hints = None
    if include_hints:
        hints = HintBundle(problem_id="prob_123", hints=[], blueprint=prob.hint_blueprint)
        
    return {
        "generated_problem": prob,
        "testcase_bundle": testcases,
        "reference_solution": ref,
        "validation_report": val,
        "hint_bundle": hints
    }


def test_generate_problem_package_is_coroutine_function():
    """Test A: generate_problem_package is an async coroutine function."""
    assert inspect.iscoroutinefunction(generate_problem_package)


def test_generate_problem_package_minimal(monkeypatch):
    """Test B & H: Minimal input returns ProblemGenerationPackage, and sync wrapper works."""
    import agent.services.problem_generation_service
    monkeypatch.setattr(agent.services.problem_generation_service, "run_package_workflow", mock_run_package_workflow)

    inp = ProblemGenerationPackageInput(
        algorithm="greedy",
        difficulty="easy",
        include_hints=False,
        include_concept_context=False
    )
    
    res = generate_problem_package_sync(inp)
    
    assert isinstance(res, ProblemGenerationPackage)
    assert res.problem_id == "prob_123"
    assert res.generated_problem.title == "Mock Problem"
    assert res.testcase_bundle is not None
    assert res.validation_report.passed is True
    assert res.hint_bundle is None
    assert res.concept_context == []


def test_generate_problem_package_include_hints(monkeypatch):
    """Test C: include_hints=True returns hint_bundle."""
    import agent.services.problem_generation_service
    monkeypatch.setattr(agent.services.problem_generation_service, "run_package_workflow", mock_run_package_workflow)

    inp = ProblemGenerationPackageInput(
        algorithm="greedy",
        difficulty="easy",
        include_hints=True,
        include_concept_context=False
    )
    
    res = generate_problem_package_sync(inp)
    assert res.hint_bundle is not None


def test_generate_problem_package_concept_context(monkeypatch):
    """Test D: include_concept_context=False returns empty concept_context."""
    import agent.services.problem_generation_service
    monkeypatch.setattr(agent.services.problem_generation_service, "run_package_workflow", mock_run_package_workflow)

    inp = ProblemGenerationPackageInput(
        algorithm="greedy",
        difficulty="easy",
        include_concept_context=False
    )
    res = generate_problem_package_sync(inp)
    assert res.concept_context == []


def test_problem_package_serialization_helpers(monkeypatch):
    """Test E & F: public dict excludes reference_solution, internal dict includes it."""
    import agent.services.problem_generation_service
    monkeypatch.setattr(agent.services.problem_generation_service, "run_package_workflow", mock_run_package_workflow)

    inp = ProblemGenerationPackageInput(algorithm="greedy", difficulty="easy")
    res = generate_problem_package_sync(inp)
    
    # Public dict
    pub_dict = problem_package_to_public_dict(res)
    assert "reference_solution" not in pub_dict
    assert pub_dict["problem_id"] == "prob_123"
    
    # Internal dict
    int_dict = problem_package_to_internal_dict(res)
    assert "reference_solution" in int_dict
    assert int_dict["reference_solution"]["code"] == "def solve(): pass"


def test_validation_retry_loop(monkeypatch):
    """Test G: validation retry attempt count is respected."""
    import agent.services.problem_generation_service
    
    call_count = 0
    def mock_run_failing_workflow(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        res = mock_run_package_workflow(*args, **kwargs)
        from agent.schemas import ValidationIssue
        res["validation_report"] = ValidationReport(
            passed=False,
            issues=[ValidationIssue(severity="error", code="ERR_FORMAT", message="Bad format")],
            summary="Failed"
        )
        return res
        
    monkeypatch.setattr(agent.services.problem_generation_service, "run_package_workflow", mock_run_failing_workflow)
    
    inp = ProblemGenerationPackageInput(
        algorithm="greedy",
        difficulty="easy",
        max_validation_attempts=3
    )
    
    res = generate_problem_package_sync(inp)
    assert call_count == 3
    assert res.validation_report.passed is False
    assert res.safe_to_show is False
