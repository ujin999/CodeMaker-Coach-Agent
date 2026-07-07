from typing import Literal
from agent.schemas import GeneratedProblem, SubmissionResult, FeedbackReport
from agent.nodes.state import AgentState


def infer_allowed_hint_level(result_type: str) -> int:
    """
    Return allowed hint level based on result type.
    """
    if result_type in ["WA", "TLE", "RE", "MLE"]:
        return 2
    return 1


def analyze_submission_deterministic(
    problem: GeneratedProblem,
    submission: SubmissionResult,
) -> FeedbackReport:
    """
    Produce safe deterministic feedback without calling LLM.
    All feedback is returned in Korean, with safety checks against complete solution code.
    """
    problem_id = problem.problem_id
    result_type = submission.result_type
    allowed_hint_level = infer_allowed_hint_level(result_type)

    summary = ""
    likely_causes = []
    next_steps = []

    if result_type == "AC":
        summary = "정답입니다. 이제 같은 풀이를 더 간결하게 정리하거나 시간 복잡도를 설명해보세요."
        likely_causes = []
        next_steps = ["풀이 아이디어를 말로 설명해보기", "시간 복잡도와 공간 복잡도 정리하기"]
    elif result_type == "WA":
        summary = "틀렸습니다. 예제와 경계값 입력에 대한 로직을 검토해야 합니다."
        if submission.expected_output is not None and submission.actual_output is not None:
            exp_val = submission.expected_output.strip()
            act_val = submission.actual_output.strip()
            if len(exp_val) > 50:
                exp_val = exp_val[:47] + "..."
            if len(act_val) > 50:
                act_val = act_val[:47] + "..."
            summary = f"틀렸습니다. 기대 출력값('{exp_val}')과 실제 출력값('{act_val}')이 일치하지 않습니다."

        likely_causes = [
            "경계 조건(Boundary condition) 처리 오류",
            "입력 데이터 파싱(Parsing) 관련 실수",
            "Off-by-one 에러 (1 차이로 인한 루프/인덱스 에러)",
            "문제 조건 및 제약사항에 대한 오해"
        ]
        next_steps = [
            "문제에 명시된 극단적인 제한 조건(최소/최대 입력값)을 손으로 직접 따라가며 검증하기",
            "실패한 테스트케이스를 바탕으로 로컬에서 디버거를 붙여 메모리 상태 추적하기"
        ]
        if submission.failed_input:
            input_preview = submission.failed_input.strip()
            if len(input_preview) > 50:
                input_preview = input_preview[:47] + "..."
            next_steps.append(f"실패한 입력값('{input_preview}')을 디버깅 데이터로 사용하기")
    elif result_type == "TLE":
        summary = "시간 초과입니다. 알고리즘의 시간 복잡도를 줄여야 합니다."
        likely_causes = [
            "문제에서 의도한 알고리즘을 사용하지 않고 비효율적인 완전 탐색 등을 사용함",
            "반복문(Loop) 내부의 시간 복잡도가 너무 큼",
            "불필요하게 중복된 연산이 매번 호출됨"
        ]
        next_steps = [
            f"문제에 명시된 예상 시간 복잡도 '{problem.expected_time_complexity}'와 현재 구현의 시간 복잡도를 비교해 보세요.",
            "중첩 루프의 범위를 좁히거나 비효율적인 데이터 구조(예: list 대신 set/dict)를 사용했는지 확인하기",
            "동적 계획법(DP)이나 메모이제이션을 통해 중복 연산을 회피할 수 있는지 검토하기"
        ]
    elif result_type == "RE":
        summary = "런타임 에러입니다. 예외 처리가 누락되었거나 비정상적인 메모리/인덱스 참조가 발생했습니다."
        likely_causes = [
            "배열 또는 리스트 인덱스 범위를 초과함 (IndexError)",
            "빈 입력값 또는 비정상적인 경계 조건에 대한 예외 처리 누락",
            "재귀 호출 깊이(Recursion limit) 초과",
            "잘못된 자료형 변환 (Type conversion error)"
        ]
        next_steps = [
            "실패한 테스트케이스 입력값을 확인하여 로컬에서 예외 재현하기",
            "배열/리스트 인덱스 접근 전 범위 검증 코드 추가하기",
            "재귀 대신 반복문으로 변경하거나 sys.setrecursionlimit() 설정 검토하기"
        ]
    elif result_type == "MLE":
        summary = "메모리 초과입니다. 불필요하게 많은 공간을 사용 중인지 확인해야 합니다."
        likely_causes = [
            "지나치게 거대한 크기의 배열이나 테이블(DP 테이블 등)을 할당함",
            "불필요한 중복 상태를 메모리에 보관 중임",
            "인접 행렬 등으로 너무 크게 그래프를 표현함"
        ]
        next_steps = [
            "공간 복잡도를 최소화하도록 고정 크기 변수나 누적 값만 저장하도록 변경하기",
            "대용량 배열을 사용하는 대신 이터레이터나 제너레이터 등을 활용해 메모리 절약하기",
            "그래프 표현 시 인접 행렬 대신 인접 리스트(Adjacency List) 사용하기"
        ]
    elif result_type == "CE":
        summary = "컴파일 에러입니다. 코드의 문법이나 환경 설정을 확인해 보세요."
        likely_causes = [
            "언어의 문법 오류 (Syntax Error)",
            "필수 라이브러리/모듈 임포트 누락",
            "함수 및 클래스 이름 오타 혹은 잘못된 인덴트(Indentation)"
        ]
        next_steps = [
            "로컬 컴파일러 또는 인터프리터에서 실행하여 에러 메시지 확인하기",
            "사용 중인 언어(예: Python, C++, Java)에 맞는 표준 구문을 정확히 준수했는지 검토하기"
        ]
    elif result_type == "PE":
        summary = "출력 형식 오류입니다. 문제에서 요구하는 띄어쓰기, 줄바꿈 등을 확인하세요."
        likely_causes = [
            "출력값 끝에 불필요한 공백 문자나 빈 줄이 추가됨",
            "줄바꿈 포맷이 정답 기준과 불일치함"
        ]
        next_steps = [
            "기대 출력 형식 문자열과 본인의 출력 포맷을 글자 단위로 대조하기",
            "rstrip() 등을 사용하여 개행 문자 및 뒤쪽 공백을 제거하고 출력해보기"
        ]
    else:  # UNKNOWN
        summary = "알 수 없는 에러가 발생했습니다. 코드 구조를 다시 한 번 검증해 보세요."
        likely_causes = [
            "실행 런타임 오류 혹은 원인 미상의 실패 상태"
        ]
        next_steps = [
            "기본적인 예제 테스트케이스를 통해 로직이 정상 작동하는지 처음부터 검증하기"
        ]

    return FeedbackReport(
        problem_id=problem_id,
        result_type=result_type,
        summary=summary,
        likely_causes=likely_causes,
        next_steps=next_steps,
        allowed_hint_level=allowed_hint_level,
        safe_to_show=True,
        generated_by="deterministic"
    )


def build_feedback_from_submission(
    problem: GeneratedProblem,
    submission: SubmissionResult,
    prefer_llm: bool = False,
) -> FeedbackReport:
    """
    Default to deterministic feedback.
    If prefer_llm=True, keep the deterministic result for now.
    Do not call LLM yet in this function.
    """
    # LLM-based personalized feedback can be added later as an explicit opt-in path.
    return analyze_submission_deterministic(problem, submission)


def generate_feedback_node(state: AgentState) -> AgentState:
    """
    Read generated_problem and submission_result from state.
    Store feedback_report.
    """
    if "generated_problem" not in state or state["generated_problem"] is None:
        raise ValueError("Missing 'generated_problem' in agent state.")
    if "submission_result" not in state or state["submission_result"] is None:
        raise ValueError("Missing 'submission_result' in agent state.")

    problem = state["generated_problem"]
    submission = state["submission_result"]

    report = build_feedback_from_submission(problem, submission)

    diagnosis = state.get("error_diagnosis")
    explanation = state.get("failed_case_explanation")

    if diagnosis and explanation:
        cause_map = {
            "WA_OFF_BY_ONE": "경계 조건 오차(WA_OFF_BY_ONE)",
            "WA_TOO_LOW_BOUND": "결과 범위 상한 도달 미흡(WA_TOO_LOW_BOUND)",
            "WA_TOO_HIGH_BOUND": "결과 범위 상한 초과(WA_TOO_HIGH_BOUND)",
            "WA_WINDOW_UPDATE": "슬라이딩 윈도우 포인터 이동 오류(WA_WINDOW_UPDATE)",
            "WA_BFS_DISTANCE_OR_VISITED": "BFS 최단거리/방문처리 조건 오류(WA_BFS_DISTANCE_OR_VISITED)",
            "WA_DFS_COMPONENT_COUNT": "DFS 연결요소 방문 조건 오류(WA_DFS_COMPONENT_COUNT)",
            "PE_OUTPUT_FORMAT": "출력 포맷 불일치(PE_OUTPUT_FORMAT)",
            "WA_LOGIC_MISMATCH": "일반 논리 오류(WA_LOGIC_MISMATCH)",
            "RE_INDEX_ERROR": "인덱스 범위 초과(RE_INDEX_ERROR)",
            "RE_RECURSION_DEPTH": "재귀 한도 초과(RE_RECURSION_DEPTH)",
            "RE_VALUE_ERROR": "잘못된 형 변환/값 참조(RE_VALUE_ERROR)",
            "RE_KEY_ERROR": "잘못된 키 참조(RE_KEY_ERROR)",
            "RE_RUNTIME_EXCEPTION": "기타 런타임 오류(RE_RUNTIME_EXCEPTION)",
            "CE_SYNTAX_ERROR": "구문/문법 오류(CE_SYNTAX_ERROR)",
            "CE_NAME_ERROR": "변수/함수명 오타(CE_NAME_ERROR)",
            "CE_IMPORT_ERROR": "임포트 오류(CE_IMPORT_ERROR)",
            "CE_COMPILE_ERROR": "기타 컴파일 오류(CE_COMPILE_ERROR)",
            "TLE_COMPLEXITY": "시간 복잡도 초과(TLE_COMPLEXITY)",
            "MLE_SPACE_COMPLEXITY": "공간 복잡도 초과(MLE_SPACE_COMPLEXITY)",
            "AC_ACCEPTED": "모든 조건 통과(AC_ACCEPTED)",
            "UNKNOWN_RESULT": "미정의 에러(UNKNOWN_RESULT)",
        }
        friendly_cause = cause_map.get(diagnosis.primary_cause, diagnosis.primary_cause)
        report.summary = f"진단 결과: [{friendly_cause}]. {report.summary}"

        if diagnosis.evidence:
            report.likely_causes = list(diagnosis.evidence) + list(report.likely_causes)
        if diagnosis.suggested_focus:
            report.likely_causes = list(report.likely_causes) + list(diagnosis.suggested_focus)

        if explanation.likely_gap:
            report.next_steps = [explanation.likely_gap] + list(report.next_steps)

        if not explanation.safe_to_show or not diagnosis.safe_to_show:
            report.safe_to_show = False
        else:
            report = report.validate_safety_policy()

    complexity = state.get("complexity_analysis")
    if complexity:
        if complexity.evidence:
            report.likely_causes = list(complexity.evidence) + list(report.likely_causes)
        if complexity.suggested_actions:
            report.next_steps = list(report.next_steps) + list(complexity.suggested_actions)
        if submission.result_type == "TLE":
            risk_msg = f"시간 복잡도 분석 결과 위험도가 {complexity.risk_level} 수준으로 감지되었습니다."
            if complexity.suspected_complexity:
                risk_msg += f" (의심 복잡도: {complexity.suspected_complexity})"
            report.summary = f"{risk_msg} {report.summary}"
        if not complexity.safe_to_show:
            report.safe_to_show = False
        else:
            report = report.validate_safety_policy()

    counterexample = state.get("counterexample_report")
    if counterexample:
        if counterexample.explanation:
            report.likely_causes = list(report.likely_causes) + [counterexample.explanation]
        if counterexample.lesson:
            report.next_steps = list(report.next_steps) + [counterexample.lesson]
        if not counterexample.safe_to_show:
            report.safe_to_show = False
        else:
            report = report.validate_safety_policy()

    new_state = state.copy()
    new_state["feedback_report"] = report
    return new_state
