import pytest
from agent.schemas import (
    ProblemGenerationInput,
    GeneratedProblem,
    HintBlueprint,
    TestcaseBundle,
)
from agent.nodes import (
    AgentState,
    generate_problem_node,
    generate_testcases_node,
    generate_hints_node,
    validate_outputs_node,
    run_package_workflow,
)


def create_dummy_problem(
    problem_id: str = "budget_allocation_optimization",
    title: str = "예산 배정 최적화",
    statement: str = "격자 최단 경로를 구하는 문제 또는 상한액 C min(요청 예산, C) 계산 문제입니다.",
    algorithm: list[str] = None,
) -> GeneratedProblem:
    """Helper to construct a valid GeneratedProblem in Korean."""
    return GeneratedProblem(
        problem_id=problem_id,
        title=title,
        difficulty="medium",
        algorithm=algorithm or ["binary_search"],
        learning_goal="매개 변수 탐색 학습",
        statement=statement,
        input_format="입력 형식",
        output_format="출력 형식",
        constraints=["제한 조건 1"],
        expected_time_complexity="O(N log M)",
        hint_blueprint=HintBlueprint(
            intended_algorithm=algorithm or ["binary_search"],
            core_insight="이분 탐색 사용",
            common_misconceptions=["오버플로우 주의"],
            edge_case_focus=["최대값 입력"],
            forbidden_disclosures=["전체 정해"],
            level_1_guidance="힌트 1",
            level_2_guidance="힌트 2",
            level_3_guidance="힌트 3",
            allowed_code_exposure="none",
        ),
    )


def test_generate_testcases_node_budget_cap():
    """Test A: generate_testcases_node generates deterministic budget_cap testcases."""
    problem = create_dummy_problem()
    state = AgentState(generated_problem=problem, min_cases=5)
    
    new_state = generate_testcases_node(state)
    assert "testcase_bundle" in new_state
    bundle = new_state["testcase_bundle"]
    assert isinstance(bundle, TestcaseBundle)
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "budget_cap"
    assert len(bundle.testcases) >= 5


def test_validate_outputs_node_stores_report():
    """Test B: validate_outputs_node stores validation_report with passed=True."""
    problem = create_dummy_problem()
    from agent.testcase_generators.registry import generate_deterministic_testcases
    bundle = generate_deterministic_testcases(problem, min_cases=5)
    
    state = AgentState(generated_problem=problem, testcase_bundle=bundle)
    new_state = validate_outputs_node(state)
    
    assert "validation_report" in new_state
    report = new_state["validation_report"]
    assert report.passed is True
    assert "problem" in report.checked_sections
    assert "testcases" in report.checked_sections


def test_missing_generated_problem_raises_value_error():
    """Test C: missing generated_problem raises ValueError in downstream nodes."""
    state_empty = AgentState()
    
    with pytest.raises(ValueError, match="generated_problem"):
        generate_testcases_node(state_empty)
        
    with pytest.raises(ValueError, match="generated_problem"):
        generate_hints_node(state_empty)
        
    with pytest.raises(ValueError, match="generated_problem"):
        validate_outputs_node(state_empty)


def test_run_package_workflow_monkeypatched(monkeypatch):
    """Test D: run_package_workflow executes the full pipeline end-to-end with mock generation chains."""
    # Reference solver verification hits Judge0 over the network; skip it in this offline unit test.
    monkeypatch.setenv("ENV", "test")
    problem = create_dummy_problem()

    # Mock the LLM chains to return dummy/pre-computed structures instead of hitting external services
    def mock_generate_problem(input_data):
        return problem

    # We import and mock the actual problem generation function inside packages/agent
    monkeypatch.setattr("agent.chains.problem_generation.generate_problem", mock_generate_problem)
    
    # Mock hint generation
    from agent.schemas import HintBundle, Hint
    mock_hint_bundle = HintBundle(
        problem_id=problem.problem_id,
        blueprint=problem.hint_blueprint,
        hints=[
            Hint(
                problem_id=problem.problem_id,
                level=1,
                title="기본 방향",
                content="이분 탐색으로 접근하세요.",
                reveals_core_code=False
            )
        ]
    )
    
    def mock_generate_hints(prob, allowed_level, user_situation):
        return mock_hint_bundle
        
    monkeypatch.setattr("agent.chains.hint_generation.generate_hints", mock_generate_hints)
    
    # Run the workflow
    gen_input = ProblemGenerationInput(
        algorithm="binary_search",
        difficulty="medium",
        recent_weaknesses=[]
    )
    
    final_state = run_package_workflow(
        generation_input=gen_input,
        min_cases=5,
        allowed_hint_level=3,
        include_hints=True
    )
    
    assert final_state["generated_problem"] is problem
    assert "testcase_bundle" in final_state
    assert final_state["testcase_bundle"].generation_mode == "deterministic"
    assert "hint_bundle" in final_state
    assert final_state["hint_bundle"] is mock_hint_bundle
    assert "validation_report" in final_state
    assert final_state["validation_report"].passed is True
