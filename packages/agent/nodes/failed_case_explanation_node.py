from agent.schemas import GeneratedProblem, SubmissionResult, ErrorDiagnosis, FailedCaseExplanation
from agent.nodes.state import AgentState


def summarize_failed_case(
    problem: GeneratedProblem,
    submission: SubmissionResult,
    diagnosis: ErrorDiagnosis | None = None,
) -> FailedCaseExplanation:
    """
    Explain the failed testcase in Korean without revealing solution code.
    """
    res_type = submission.result_type

    if res_type == "AC":
        return FailedCaseExplanation(
            problem_id=problem.problem_id,
            testcase_name=submission.failed_testcase_name,
            summary="실패한 테스트케이스가 없습니다.",
            input_observation=None,
            expected_vs_actual=None,
            likely_gap=None
        )

    # Build summary
    if res_type == "WA":
        summary = f"테스트케이스 {submission.failed_testcase_name or '오답'}에서 기대값과 다른 결과가 나왔습니다."
    elif res_type == "PE":
        summary = "출력 형식 오류(PE)가 발생했습니다."
    elif res_type == "TLE":
        summary = "시간 제한을 초과했습니다."
    elif res_type == "RE":
        summary = "프로그램 실행 중 런타임 오류가 발생했습니다."
    elif res_type == "CE":
        summary = "컴파일 또는 문법 오류가 발생했습니다."
    elif res_type == "MLE":
        summary = "메모리 사용 제한을 초과했습니다."
    else:
        summary = "제출 분석 중 오류가 발견되었습니다."

    input_obs = None
    if submission.failed_input is not None:
        input_obs = f"입력 프리뷰: {str(submission.failed_input)[:80]}"

    exp_vs_act = None
    if submission.expected_output is not None and submission.actual_output is not None:
        exp_trunc = str(submission.expected_output)[:80]
        act_trunc = str(submission.actual_output)[:80]
        exp_vs_act = f"기대 출력은 '{exp_trunc}'이지만 실제 출력은 '{act_trunc}'입니다."

    likely_gap = None
    if diagnosis and diagnosis.primary_cause:
        gaps = {
            "WA_OFF_BY_ONE": "정답보다 1 차이가 나므로 경계값 갱신 또는 종료 조건을 의심할 수 있습니다.",
            "WA_TOO_LOW_BOUND": "가능한 답을 너무 작게 잡고 있을 가능성이 있습니다.",
            "WA_TOO_HIGH_BOUND": "가능한 답을 너무 크게 잡고 있을 가능성이 있습니다.",
            "WA_WINDOW_UPDATE": "구간 합을 갱신하는 순서나 왼쪽 포인터 이동 조건을 점검해야 합니다.",
            "WA_BFS_DISTANCE_OR_VISITED": "거리 시작값 또는 방문 처리 시점을 점검해야 합니다.",
            "WA_DFS_COMPONENT_COUNT": "방문 처리 또는 연결 방향 조건을 점검해야 합니다.",
            "PE_OUTPUT_FORMAT": "출력 값은 유사하지만 공백/개행 형식이 다를 가능성이 있습니다."
        }
        likely_gap = gaps.get(diagnosis.primary_cause, "알고리즘 구현의 논리적 결함 또는 탈출 조건을 점검해야 합니다.")

    return FailedCaseExplanation(
        problem_id=problem.problem_id,
        testcase_name=submission.failed_testcase_name,
        summary=summary,
        input_observation=input_obs,
        expected_vs_actual=exp_vs_act,
        likely_gap=likely_gap
    )


def explain_failed_case_node(state: AgentState) -> AgentState:
    if "generated_problem" not in state or state["generated_problem"] is None:
        raise ValueError("Missing 'generated_problem' in AgentState.")
    if "submission_result" not in state or state["submission_result"] is None:
        raise ValueError("Missing 'submission_result' in AgentState.")

    problem = state["generated_problem"]
    submission = state["submission_result"]
    diagnosis = state.get("error_diagnosis", None)

    explanation = summarize_failed_case(problem, submission, diagnosis)

    new_state = state.copy()
    new_state["failed_case_explanation"] = explanation
    return new_state
