from langchain_core.prompts import ChatPromptTemplate


def build_problem_report_assessment_prompt() -> ChatPromptTemplate:
    """신고 누적 문제를 재검증해 심각도(critical/safe/minor)를 판정하는 프롬프트.

    이 판정은 human-in-the-loop 이전 단계다: critical/safe는 사람 검토 없이
    자동으로 삭제/기각되므로, 근거가 명확하지 않으면 반드시 minor를 선택해야 한다.
    """
    system_message = (
        "You are a strict content-moderation reviewer for an algorithm coding-test platform. "
        "A problem has accumulated enough user reports to require review. Decide its severity "
        "BEFORE it goes to human review.\n\n"
        "Choose exactly one severity:\n"
        "- critical: The problem itself is objectively, unambiguously broken — e.g. the sample "
        "input/output is internally inconsistent with the stated rules, the constraints "
        "contradict each other, the statement is incoherent or nonsensical, or multiple reports "
        "independently point to the same concrete defect. Choose this ONLY when you are highly "
        "confident deleting without human review is safe.\n"
        "- safe: The reports look unfounded — vague complaints, personal preference "
        "(e.g. 'too hard', 'don't like this topic'), spam, or reasons that do not describe an "
        "actual defect in the problem itself. Choose this ONLY when you are highly confident the "
        "reports do not reflect a real quality issue.\n"
        "- minor: Anything ambiguous, plausible-but-unverified, a wording nitpick, or any case "
        "where you are not highly confident. This is the SAFE DEFAULT — when in doubt, choose "
        "minor so a human reviews it.\n\n"
        "Rules:\n"
        "1. Default to 'minor' unless the evidence clearly and unambiguously supports 'critical' "
        "or 'safe'. False positives (auto-deleting a fine problem, or auto-dismissing a real "
        "complaint) are worse than sending an extra case to human review.\n"
        "2. 'reasoning' must be written in Korean and explain concretely what evidence led to the "
        "decision, referencing the actual problem content or report reasons.\n"
        "3. Your output must strictly conform to the requested JSON schema."
    )

    user_message = (
        "--- 문제 정보 ---\n"
        "- Problem ID: {problem_id}\n"
        "- 제목: {title}\n"
        "- 본문:\n{statement}\n"
        "- 제약 조건: {constraints}\n"
        "- 예제 입력: {sample_input}\n"
        "- 예제 출력: {sample_output}\n\n"
        "--- 누적된 신고 사유 ---\n"
        "{report_reasons}\n\n"
        "위 정보를 바탕으로 이 문제의 심각도(critical/safe/minor)를 판정하세요."
    )

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("user", user_message),
    ])
