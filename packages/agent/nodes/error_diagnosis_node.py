from typing import Literal
from agent.schemas import GeneratedProblem, SubmissionResult, ErrorDiagnosis
from agent.nodes.state import AgentState


def detect_problem_family(problem: GeneratedProblem) -> str:
    """
    Return one of:
    - budget_cap
    - two_pointer_subarray
    - bfs_grid_shortest_path
    - dfs_grid_components
    - unknown
    """
    try:
        from agent.testcase_generators.base import detect_problem_type
        ptype = detect_problem_type(problem)
        if ptype in ["budget_cap", "two_pointer_subarray", "bfs_grid_shortest_path", "dfs_grid_components"]:
            return ptype
    except Exception:
        pass

    # Keyword fallbacks
    stmt = (problem.statement or "").lower()
    title = (problem.title or "").lower()
    goal = (problem.learning_goal or "").lower()
    algos = [a.lower() for a in (problem.algorithm or [])]

    # BFS Grid shortest path
    if "bfs" in algos or "bfs_grid_shortest_path" in algos or "최단거리" in stmt or "최단 거리" in stmt:
        return "bfs_grid_shortest_path"

    # DFS Grid connected components
    if "dfs" in algos or "dfs_grid_components" in algos or "연결 요소" in stmt or "연결요소" in stmt or "단지" in stmt:
        return "dfs_grid_components"

    # Two pointer subarray
    if "two_pointer" in algos or "two_pointer_subarray" in algos or "투 포인터" in stmt or "투포인터" in stmt:
        return "two_pointer_subarray"

    # Budget cap
    if "binary_search" in algos or "budget_cap" in algos or "상한액" in stmt or "상한" in stmt or "예산" in stmt:
        return "budget_cap"

    return "unknown"


def diagnose_wrong_answer(problem: GeneratedProblem, submission: SubmissionResult) -> ErrorDiagnosis:
    """
    Diagnose WA/PE based on problem family and expected vs actual.
    """
    res_type = submission.result_type
    family = detect_problem_family(problem)

    if res_type == "PE":
        return ErrorDiagnosis(
            problem_id=problem.problem_id,
            result_type="PE",
            primary_cause="PE_OUTPUT_FORMAT",
            evidence=["출력 문자열의 공백/개행 형식이 일치하지 않습니다."],
            related_concepts=["output_format"],
            suggested_focus=["공백 및 개행 처리", "출력 데이터 타입"]
        )

    # WA cases
    evidence = []
    if submission.expected_output is not None and submission.actual_output is not None:
        evidence.append(f"Expected: {submission.expected_output}, Actual: {submission.actual_output}")

    if family == "budget_cap":
        # Check boundary deviations if integers
        expected_val = None
        actual_val = None
        try:
            expected_val = int(submission.expected_output.strip())
            actual_val = int(submission.actual_output.strip())
        except (ValueError, TypeError, AttributeError):
            pass

        if expected_val is not None and actual_val is not None:
            if actual_val == expected_val - 1 or actual_val == expected_val + 1:
                cause = "WA_OFF_BY_ONE"
            elif actual_val < expected_val:
                cause = "WA_TOO_LOW_BOUND"
            else:
                cause = "WA_TOO_HIGH_BOUND"
        else:
            cause = "WA_LOGIC_MISMATCH"

        return ErrorDiagnosis(
            problem_id=problem.problem_id,
            result_type="WA",
            primary_cause=cause,
            evidence=evidence,
            related_concepts=["binary_search", "parametric_search", "boundary_condition"],
            suggested_focus=[
                "가능한 C일 때 answer를 갱신하는 위치",
                "lo/hi 갱신 방향",
                "종료 조건"
            ]
        )

    elif family in ["two_pointer_subarray", "two_pointer"]:
        return ErrorDiagnosis(
            problem_id=problem.problem_id,
            result_type="WA",
            primary_cause="WA_WINDOW_UPDATE",
            evidence=evidence,
            related_concepts=["two_pointer", "sliding_window", "boundary_condition"],
            suggested_focus=[
                "윈도우 갱신 조건",
                "포인터 이동 방향",
                "경계값 처리"
            ]
        )

    elif family in ["bfs_grid_shortest_path", "bfs"]:
        return ErrorDiagnosis(
            problem_id=problem.problem_id,
            result_type="WA",
            primary_cause="WA_BFS_DISTANCE_OR_VISITED",
            evidence=evidence,
            related_concepts=["bfs", "shortest_path", "visited"],
            suggested_focus=[
                "시작 위치 방문 및 거리 초기화",
                "방문 처리 시점 (큐 삽입 시점)",
                "이동 방향 탐색 조건"
            ]
        )

    elif family in ["dfs_grid_components", "dfs"]:
        return ErrorDiagnosis(
            problem_id=problem.problem_id,
            result_type="WA",
            primary_cause="WA_DFS_COMPONENT_COUNT",
            evidence=evidence,
            related_concepts=["dfs", "connected_components", "visited"],
            suggested_focus=[
                "방문 배열 체크 및 초기화",
                "재귀 호출의 기저 조건 (범위 체크)",
                "상하좌우 연결 탐색 방향"
            ]
        )

    else:
        return ErrorDiagnosis(
            problem_id=problem.problem_id,
            result_type="WA",
            primary_cause="WA_LOGIC_MISMATCH",
            evidence=evidence,
            related_concepts=["logic_error"],
            suggested_focus=[
                "알고리즘 구현 상태 점검",
                "경계 조건 체크"
            ]
        )


def diagnose_runtime_error(problem: GeneratedProblem, submission: SubmissionResult) -> ErrorDiagnosis:
    """
    Use stderr/user_code keywords.
    """
    stderr_str = submission.stderr or ""
    evidence = [stderr_str] if stderr_str else []

    if "indexerror" in stderr_str.lower():
        cause = "RE_INDEX_ERROR"
        suggested = ["인덱스가 배열/리스트 범위를 벗어나는지 확인", "루프 경계조건 확인"]
    elif "recursionerror" in stderr_str.lower():
        cause = "RE_RECURSION_DEPTH"
        suggested = ["재귀 기저조건 확인", "방문 배열의 visited 누락에 의한 무한 재귀 확인"]
    elif "valueerror" in stderr_str.lower():
        cause = "RE_VALUE_ERROR"
        suggested = ["타입 캐스팅 과정 또는 함수 입력 인자 무결성 확인"]
    elif "keyerror" in stderr_str.lower():
        cause = "RE_KEY_ERROR"
        suggested = ["딕셔너리에 존재하지 않는 키 참조 확인"]
    else:
        cause = "RE_RUNTIME_EXCEPTION"
        suggested = ["런타임 오류가 발생한 라인을 확인하고 예외 유형 디버깅"]

    return ErrorDiagnosis(
        problem_id=problem.problem_id,
        result_type="RE",
        primary_cause=cause,
        evidence=evidence,
        related_concepts=["runtime_error"],
        suggested_focus=suggested
    )


def diagnose_compile_error(problem: GeneratedProblem, submission: SubmissionResult) -> ErrorDiagnosis:
    stderr_str = submission.stderr or ""
    evidence = [stderr_str] if stderr_str else []

    if "syntaxerror" in stderr_str.lower():
        cause = "CE_SYNTAX_ERROR"
        suggested = ["괄호 짝 맞춤, 들여쓰기(Indentation), 콜론(:) 누락 여부 확인"]
    elif "nameerror" in stderr_str.lower():
        cause = "CE_NAME_ERROR"
        suggested = ["정의하지 않았거나 철자가 틀린 변수/함수명 확인"]
    elif "importerror" in stderr_str.lower() or "modulenotfounderror" in stderr_str.lower():
        cause = "CE_IMPORT_ERROR"
        suggested = ["임포트하려는 모듈명이 정확한지 확인"]
    else:
        cause = "CE_COMPILE_ERROR"
        suggested = ["컴파일러 및 구문 번역기 지시 사항 확인"]

    return ErrorDiagnosis(
        problem_id=problem.problem_id,
        result_type="CE",
        primary_cause=cause,
        evidence=evidence,
        related_concepts=["compile_error"],
        suggested_focus=suggested
    )


def diagnose_timeout(problem: GeneratedProblem, submission: SubmissionResult) -> ErrorDiagnosis:
    evidence = []
    if problem.expected_time_complexity:
        evidence.append(f"기대 시간 복잡도: {problem.expected_time_complexity}")

    return ErrorDiagnosis(
        problem_id=problem.problem_id,
        result_type="TLE",
        primary_cause="TLE_COMPLEXITY",
        evidence=evidence,
        related_concepts=problem.algorithm or ["time_complexity"],
        suggested_focus=[
            "이중 반복문을 선형 시간 복잡도로 줄일 수 있는지 검토",
            "불필요한 반복 계산 제거 및 메모이제이션 적용 고려"
        ]
    )


def diagnose_submission(problem: GeneratedProblem, submission: SubmissionResult) -> ErrorDiagnosis:
    res_type = submission.result_type

    if res_type == "AC":
        return ErrorDiagnosis(
            problem_id=problem.problem_id,
            result_type="AC",
            primary_cause="AC_ACCEPTED",
            evidence=["모든 테스트케이스 통과"],
            related_concepts=problem.algorithm or [],
            suggested_focus=["추가적인 성능 최적화 방안 고민"]
        )
    elif res_type == "MLE":
        return ErrorDiagnosis(
            problem_id=problem.problem_id,
            result_type="MLE",
            primary_cause="MLE_SPACE_COMPLEXITY",
            evidence=["메모리 사용량 제한 초과"],
            related_concepts=["space_complexity"],
            suggested_focus=["방문 배열 크기 또는 저장 데이터 구조의 공간복잡도 최적화"]
        )
    elif res_type in ["WA", "PE"]:
        return diagnose_wrong_answer(problem, submission)
    elif res_type == "TLE":
        return diagnose_timeout(problem, submission)
    elif res_type == "RE":
        return diagnose_runtime_error(problem, submission)
    elif res_type == "CE":
        return diagnose_compile_error(problem, submission)
    else:
        return ErrorDiagnosis(
            problem_id=problem.problem_id,
            result_type="UNKNOWN",
            primary_cause="UNKNOWN_RESULT",
            evidence=["알 수 없는 오류 상태"],
            related_concepts=[],
            suggested_focus=["디버깅 정보 확인 및 코드 실행 환경 확인"]
        )


def diagnose_submission_node(state: AgentState) -> AgentState:
    if "generated_problem" not in state or state["generated_problem"] is None:
        raise ValueError("Missing 'generated_problem' in AgentState.")
    if "submission_result" not in state or state["submission_result"] is None:
        raise ValueError("Missing 'submission_result' in AgentState.")

    problem = state["generated_problem"]
    submission = state["submission_result"]

    diagnosis = diagnose_submission(problem, submission)

    new_state = state.copy()
    new_state["error_diagnosis"] = diagnosis
    return new_state
