from typing import Optional
from agent.schemas import GeneratedProblem, SubmissionResult, ErrorDiagnosis, FailedCaseExplanation, CounterexampleReport
from agent.nodes.state import AgentState


def build_counterexample_report(
    problem: GeneratedProblem,
    submission: SubmissionResult,
    diagnosis: ErrorDiagnosis | None = None,
    failed_case: FailedCaseExplanation | None = None,
) -> CounterexampleReport:
    """
    Build a deterministic counterexample-style explanation from the failed testcase.
    Do not execute user code.
    Do not generate new random inputs.
    Use existing failed_input / expected_output / actual_output as the counterexample.
    """
    problem_id = problem.problem_id
    result_type = submission.result_type

    if result_type == "AC":
        return CounterexampleReport(
            problem_id=problem_id,
            result_type="AC",
            explanation="반례가 필요하지 않습니다. 모든 테스트를 통과했습니다."
        )

    # Use values from submission if present, fallback to failed_case
    testcase_name = submission.failed_testcase_name or (failed_case.testcase_name if failed_case else None)
    counterexample_input = submission.failed_input
    expected_output = submission.expected_output
    actual_output = submission.actual_output

    explanation_parts = []
    if testcase_name:
        explanation_parts.append(f"테스트케이스 '{testcase_name}'에서 오류가 발생했습니다.")
    else:
        explanation_parts.append("제출한 코드가 특정 입력 케이스에서 다른 실행 결과를 보였습니다.")

    if counterexample_input is not None:
        inp_trunc = str(counterexample_input)[:200]
        explanation_parts.append(f"제시된 반례 입력값은 [{inp_trunc}] 입니다.")

    if expected_output is not None and actual_output is not None:
        explanation_parts.append(
            f"이 입력에 대해 문제에서 요구하는 기대 출력은 '{expected_output}' 이었으나, "
            f"사용자 코드의 실제 출력은 '{actual_output}' 으로 기록되어 정답과 분기되었습니다."
        )
    elif result_type == "TLE":
        explanation_parts.append("해당 입력값을 처리하는 과정에서 제한 시간을 초과(TLE)하였습니다.")
    elif result_type == "RE":
        explanation_parts.append("해당 입력값을 실행하는 과정에서 런타임 에러(RE)가 발생했습니다.")
    else:
        explanation_parts.append("기대 출력과 실제 출력이 일치하지 않습니다.")

    explanation = " ".join(explanation_parts)

    lesson = None
    if diagnosis and diagnosis.primary_cause:
        cause = diagnosis.primary_cause
        if cause == "WA_OFF_BY_ONE":
            lesson = "경계 조건 오차: 반복문 탈출 조건(예: 초과/이상) 또는 인덱스 범위 경계를 다시 점검해 보세요."
        elif cause == "WA_TOO_LOW_BOUND":
            lesson = "결과 범위 하한 오류: 탐색 범위를 너무 좁게 설정했거나 하한 설정에 논리적 공백이 없는지 점검하세요."
        elif cause == "WA_TOO_HIGH_BOUND":
            lesson = "결과 범위 상한 오류: 가능한 정답 범위 상한을 너무 낮게 두었거나 정답 갱신 경계가 잘못되었는지 점검하세요."
        elif cause == "WA_WINDOW_UPDATE":
            lesson = "슬라이딩 윈도우/투포인터 갱신 오류: 포인터를 이동하면서 합이나 조건을 갱신하는 연산 순서에 주의하세요."
        elif cause == "WA_BFS_DISTANCE_OR_VISITED":
            lesson = "BFS 탐색 오류: 정점을 큐에 넣기 직전에 방문 표시(visited)를 하는지 확인하고, 시작 지점의 거리를 올바르게 초기화하세요."
        elif cause == "WA_DFS_COMPONENT_COUNT":
            lesson = "DFS 탐색 오류: 모든 연결 요소를 빠짐없이 방문하는지, 그리고 이미 방문한 정점을 스택에 중복으로 넣고 있지 않은지 점검하세요."
        elif cause == "PE_OUTPUT_FORMAT":
            lesson = "출력 형식 오류: 공백, 개행 문자, 또는 출력 형식 요구사항을 문제 지문과 완전히 맞추었는지 확인하세요."
        elif cause == "TLE_COMPLEXITY":
            lesson = "시간 복잡도 초과: 불필요한 반복 탐색을 제거하고, 메모이제이션이나 선형 탐색을 이용해 연산 횟수를 최적화하세요."
        else:
            lesson = "일반 알고리즘 논리 오류: 구현하려는 연산 흐름이 예외 케이스에서 올바르게 분기되는지 점검하세요."
    else:
        lesson = "일반 알고리즘 논리 오류: 구현하려는 연산 흐름이 예외 케이스에서 올바르게 분기되는지 점검하세요."

    return CounterexampleReport(
        problem_id=problem_id,
        result_type=result_type,
        testcase_name=testcase_name,
        counterexample_input=counterexample_input,
        expected_output=expected_output,
        actual_output=actual_output,
        explanation=explanation,
        lesson=lesson,
        safe_to_show=True
    )


def build_counterexample_node(state: AgentState) -> AgentState:
    if "generated_problem" not in state or state["generated_problem"] is None:
        raise ValueError("Missing 'generated_problem' in AgentState.")
    if "submission_result" not in state or state["submission_result"] is None:
        raise ValueError("Missing 'submission_result' in AgentState.")

    problem = state["generated_problem"]
    submission = state["submission_result"]
    diagnosis = state.get("error_diagnosis")
    failed_case = state.get("failed_case_explanation")

    report = build_counterexample_report(
        problem=problem,
        submission=submission,
        diagnosis=diagnosis,
        failed_case=failed_case
    )

    new_state = state.copy()
    new_state["counterexample_report"] = report
    return new_state
