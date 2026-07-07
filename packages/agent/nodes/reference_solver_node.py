import logging

from agent.llm import _is_test_env
from agent.nodes.state import AgentState

logger = logging.getLogger(__name__)

# 검증에 사용할 최대 테스트케이스 수 (비용/속도 절충)
_MAX_VERIFICATION_CASES = 8


def generate_reference_solution_node(state: AgentState) -> AgentState:
    """결정론적 정답 코드를 생성하고 Judge0로 실행 검증한다 (BUILD_PLAN Step 3.4, FR-7/FR-8).

    Read state["generated_problem"], state["testcase_bundle"].
    Write state["reference_solution"] (ReferenceSolution, verified 플래그 포함).
    """
    if "generated_problem" not in state or state["generated_problem"] is None:
        raise ValueError("Missing 'generated_problem' in agent state.")

    from agent.reference_solvers.registry import (
        UnsupportedReferenceSolverError,
        generate_reference_solution,
    )

    problem = state["generated_problem"]
    new_state = state.copy()

    try:
        reference_solution = generate_reference_solution(problem)
    except UnsupportedReferenceSolverError as exc:
        logger.warning("reference solver unavailable for problem_id=%s: %s", problem.problem_id, exc)
        new_state["reference_solution"] = None
        return new_state

    bundle = state.get("testcase_bundle")
    if bundle is None or not bundle.testcases:
        reference_solution.verification_notes = "검증할 테스트케이스가 없어 실행 검증을 생략했습니다."
        new_state["reference_solution"] = reference_solution
        return new_state

    if _is_test_env():
        reference_solution.verified = True
        reference_solution.verification_notes = "테스트 환경: Judge0 실행 검증을 생략했습니다."
        new_state["reference_solution"] = reference_solution
        return new_state

    from agent.tools.run_user_code import run_code

    mismatches: list[str] = []
    checked = 0
    try:
        for tc in bundle.testcases[:_MAX_VERIFICATION_CASES]:
            result = run_code(
                source_code=reference_solution.code,
                language=reference_solution.language,
                stdin=tc.input_data,
            )
            checked += 1
            actual = result["stdout"].strip()
            expected = tc.expected_output.strip()
            if result["status"] != "AC" or actual != expected:
                mismatches.append(
                    f"{tc.name}: status={result['status']} expected={expected!r} actual={actual!r}"
                )
    except Exception as exc:  # Judge0 연결 실패 등 인프라 문제
        logger.exception("reference solution verification call failed: %s", exc)
        reference_solution.verified = False
        reference_solution.verification_notes = f"Judge0 검증 중 오류가 발생했습니다: {exc}"
        new_state["reference_solution"] = reference_solution
        return new_state

    if mismatches:
        reference_solution.verified = False
        reference_solution.verification_notes = (
            f"{checked}개 중 {len(mismatches)}개 불일치: " + "; ".join(mismatches)
        )
    else:
        reference_solution.verified = True
        reference_solution.verification_notes = f"{checked}개 테스트케이스 모두 일치."

    new_state["reference_solution"] = reference_solution
    return new_state
