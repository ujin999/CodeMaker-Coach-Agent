from agent.schemas import GeneratedProblem, ReferenceSolution
from agent.testcase_generators.base import detect_problem_type
from agent.reference_solvers.budget_cap import get_reference_solution_code as _budget_cap_code
from agent.reference_solvers.cable_cutting import get_reference_solution_code as _cable_cutting_code
from agent.reference_solvers.router_installation import get_reference_solution_code as _router_installation_code
from agent.reference_solvers.immigration_time import get_reference_solution_code as _immigration_time_code
from agent.reference_solvers.lower_bound_count import get_reference_solution_code as _lower_bound_count_code
from agent.reference_solvers.two_pointer_subarray import (
    get_reference_solution_code as _two_pointer_subarray_code,
)
from agent.reference_solvers.bfs_grid_shortest_path import (
    get_reference_solution_code as _bfs_grid_shortest_path_code,
)
from agent.reference_solvers.dfs_grid_components import (
    get_reference_solution_code as _dfs_grid_components_code,
)


class UnsupportedReferenceSolverError(Exception):
    """해당 문제 유형에 대한 결정론적 정답 코드 템플릿이 없을 때 발생."""


_CODE_BUILDERS = {
    "budget_cap": _budget_cap_code,
    "cable_cutting": _cable_cutting_code,
    "router_installation": _router_installation_code,
    "immigration_time": _immigration_time_code,
    "lower_bound_count": _lower_bound_count_code,
    "two_pointer_subarray": _two_pointer_subarray_code,
    "bfs_grid_shortest_path": _bfs_grid_shortest_path_code,
    "dfs_grid_components": _dfs_grid_components_code,
}


def generate_reference_solution(problem: GeneratedProblem) -> ReferenceSolution:
    """문제 유형을 감지해 결정론적 정답 코드(Python)를 생성한다.

    테스트케이스 생성에 쓰인 solve_*() 함수와 동일한 로직이므로 정답 자체는 항상
    옳지만, 실제 실행 결과 일치 여부는 Judge0 검증(reference_solver_node)에서 확인한다.
    """
    problem_type = detect_problem_type(problem)
    builder = _CODE_BUILDERS.get(problem_type)
    if builder is None:
        raise UnsupportedReferenceSolverError(
            f"No deterministic reference solution template is available for problem type '{problem_type}'."
        )

    return ReferenceSolution(
        problem_id=problem.problem_id,
        language="python",
        code=builder(),
        generator_name=problem_type,
        verified=False,
        verification_notes="",
    )
