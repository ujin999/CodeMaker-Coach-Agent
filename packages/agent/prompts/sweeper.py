from langchain_core.prompts import ChatPromptTemplate


def build_stub_evaluator_prompt() -> ChatPromptTemplate:
    """스텁/테스트용 더미 문제를 판별하는 프롬프트를 구성합니다."""
    return ChatPromptTemplate.from_messages([
        (
            "system",
            "당신은 코딩테스트 플랫폼의 품질 정화 에이전트입니다.\n"
            "전달되는 문제의 제목과 지문을 읽고, 이것이 실제 사용자가 학습하고 풀 수 있는 정상적인 코딩 문제인지,\n"
            "아니면 개발자가 시스템 테스트나 단순 스텁용으로 무성의하게 생성한 가짜 문제(더미 데이터)인지 분석하십시오.\n\n"
            "제대로 된 코딩테스트 문제라고 보기 어렵거나, 껍데기 뿐인 임시용 스텁 데이터라고 확신한다면 "
            "is_stub을 True로 설정하고 판정 사유를 명확한 한국어로 작성하십시오.\n"
            "정상적인 문제 지문 내에 단순 도메인 용어로 '더미', '임시' 등의 단어가 쓰였다면 is_stub은 False로 판정해야 합니다."
        ),
        (
            "human",
            "문제 ID: {problem_id}\n"
            "문제 제목: {title}\n"
            "문제 지문: {statement}\n"
            "제한 사항: {constraints}\n"
            "예시 입력: {sample_input}\n"
            "예시 출력: {sample_output}"
        )
    ])


def build_debugger_prompt() -> ChatPromptTemplate:
    """출제 오류가 의심되는 문제의 원인을 진단하는 프롬프트를 구성합니다."""
    return ChatPromptTemplate.from_messages([
        (
            "system",
            "당신은 코딩테스트 문제의 출제 결함을 규명하는 디버깅 에이전트입니다.\n"
            "현재 이 문제는 사용자들의 제출 에러율이 비정상적으로 높습니다.\n"
            "제시된 [정답 소스 코드]와 [유저들의 최근 채점 실패 에러 로그]를 비교 분석하여,\n"
            "이 문제에 '출제 자체의 오류'(예: 테스트케이스 정답 불일치, 입출력 포맷 요구사항 불일치, 잘못된 정답 코드)가 존재하는지 판별하십시오.\n\n"
            "단순히 문제 난이도가 너무 높아서 유저들이 많이 틀리는 정상 문제라면 is_faulty_problem을 False로 지정하고,\n"
            "테스트케이스 또는 정답 코드 자체의 버그로 인해 풀 수 없는 상태라면 is_faulty_problem을 True로 설정한 뒤,\n"
            "감지된 문제 결함에 대한 상세한 버그 설명(bug_description)을 적어주십시오."
        ),
        (
            "human",
            "문제 제목: {title}\n"
            "문제 지문: {statement}\n"
            "정답 소스 코드: {reference_code}\n\n"
            "[유저들의 최근 채점 에러 로그 (stderr)]:\n{error_logs}"
        )
    ])
