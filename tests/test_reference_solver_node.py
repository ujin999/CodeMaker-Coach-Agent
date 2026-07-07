from agent.nodes.state import AgentState
from agent.nodes.reference_solver_node import generate_reference_solution_node
from agent.schemas import GeneratedProblem, HintBlueprint


def create_dummy_problem(
    statement: str,
    algorithm: list[str],
    problem_id: str = "test-id",
) -> GeneratedProblem:
    return GeneratedProblem(
        problem_id=problem_id,
        title="Test",
        difficulty="medium",
        algorithm=algorithm,
        learning_goal="test goal",
        statement=statement,
        input_format="N\n...",
        output_format="C",
        constraints=["N <= 10"],
        expected_time_complexity="O(N log M)",
        hint_blueprint=HintBlueprint(
            intended_algorithm=algorithm,
            core_insight="insight",
            common_misconceptions=[],
            edge_case_focus=[],
            forbidden_disclosures=[],
            level_1_guidance="guide 1",
            level_2_guidance="guide 2",
            level_3_guidance="guide 3",
            allowed_code_exposure="none",
        ),
    )


def test_reference_solver_node_skips_judge0_in_test_env(monkeypatch):
    """ENV=test 환경에서는 Judge0 호출 없이 verified=True로 표시된다."""
    monkeypatch.setenv("ENV", "test")

    problem = create_dummy_problem(
        statement="상한액 C min(요청 예산, C)",
        algorithm=["binary_search"],
    )
    from agent.testcase_generators.registry import generate_deterministic_testcases

    bundle = generate_deterministic_testcases(problem, min_cases=5)
    state = AgentState(generated_problem=problem, testcase_bundle=bundle)

    new_state = generate_reference_solution_node(state)

    ref = new_state["reference_solution"]
    assert ref is not None
    assert ref.generator_name == "budget_cap"
    assert ref.verified is True


def test_reference_solver_node_unsupported_problem_type(monkeypatch):
    """지원하지 않는 문제 유형이면 reference_solution이 None으로 설정된다."""
    monkeypatch.setenv("ENV", "test")

    problem = create_dummy_problem(
        statement="단순 사칙연산 문제입니다.",
        algorithm=["math"],
    )
    state = AgentState(generated_problem=problem)

    new_state = generate_reference_solution_node(state)
    assert new_state["reference_solution"] is None


def test_reference_solver_node_missing_problem_raises():
    state = AgentState()
    try:
        generate_reference_solution_node(state)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "generated_problem" in str(exc)
