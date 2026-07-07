import subprocess
import sys

import pytest

from agent.schemas import GeneratedProblem, HintBlueprint, ReferenceSolution
from agent.reference_solvers.registry import (
    generate_reference_solution,
    UnsupportedReferenceSolverError,
)
from agent.reference_solvers.budget_cap import get_reference_solution_code as budget_cap_code
from agent.reference_solvers.two_pointer_subarray import (
    get_reference_solution_code as two_pointer_subarray_code,
)
from agent.reference_solvers.bfs_grid_shortest_path import (
    get_reference_solution_code as bfs_grid_shortest_path_code,
)
from agent.reference_solvers.dfs_grid_components import (
    get_reference_solution_code as dfs_grid_components_code,
)
from agent.testcase_generators.budget_cap import solve_budget_cap
from agent.testcase_generators.two_pointer_subarray import solve_two_pointer_subarray
from agent.testcase_generators.bfs_grid_shortest_path import solve_bfs_grid_shortest_path
from agent.testcase_generators.dfs_grid_components import solve_dfs_grid_components


def _run(code: str, stdin: str) -> str:
    """실제로 Python 서브프로세스에서 코드를 실행해 stdout을 반환한다 (Judge0 없이 로컬 검증)."""
    result = subprocess.run(
        [sys.executable, "-c", code],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"script failed: {result.stderr}"
    return result.stdout.strip()


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


def test_budget_cap_reference_solution_matches_solver():
    requests, budget = [30, 40, 50], 100
    stdin = f"{len(requests)}\n" + " ".join(map(str, requests)) + f"\n{budget}"
    expected = str(solve_budget_cap(requests, budget))
    assert _run(budget_cap_code(), stdin) == expected


def test_two_pointer_subarray_reference_solution_matches_solver():
    nums, k = [2, 1, 5, 1, 3, 2], 8
    stdin = f"{len(nums)} {k}\n" + " ".join(map(str, nums))
    expected = str(solve_two_pointer_subarray(nums, k))
    assert _run(two_pointer_subarray_code(), stdin) == expected


def test_bfs_grid_shortest_path_reference_solution_matches_solver():
    grid = ["000", "110", "000"]
    stdin = f"{len(grid)} {len(grid[0])}\n" + "\n".join(grid)
    expected = str(solve_bfs_grid_shortest_path(grid))
    assert _run(bfs_grid_shortest_path_code(), stdin) == expected


def test_dfs_grid_components_reference_solution_matches_solver():
    grid = ["110", "010", "001"]
    stdin = f"{len(grid)} {len(grid[0])}\n" + "\n".join(grid)
    expected = str(solve_dfs_grid_components(grid))
    assert _run(dfs_grid_components_code(), stdin) == expected


def test_generate_reference_solution_dispatches_by_problem_type():
    problem = create_dummy_problem(
        statement="상한액 C min(요청 예산, C)",
        algorithm=["binary_search"],
    )
    ref = generate_reference_solution(problem)
    assert isinstance(ref, ReferenceSolution)
    assert ref.problem_id == problem.problem_id
    assert ref.generator_name == "budget_cap"
    assert ref.language == "python"
    assert ref.verified is False
    assert "def solve_budget_cap" in ref.code


def test_generate_reference_solution_unsupported_raises():
    problem = create_dummy_problem(
        statement="단순 사칙연산 문제입니다.",
        algorithm=["math"],
    )
    with pytest.raises(UnsupportedReferenceSolverError):
        generate_reference_solution(problem)
