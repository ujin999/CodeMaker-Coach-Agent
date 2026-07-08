from agent.llm import get_chat_model
from agent.schemas import ProblemReportAssessment, ProblemReportAssessmentInput
from agent.prompts.problem_report_assessment import build_problem_report_assessment_prompt


def assess_problem_reports(input_data: ProblemReportAssessmentInput) -> ProblemReportAssessment:
    """신고 누적 문제를 LLM으로 재검증해 심각도(critical/safe/minor)를 판정한다.

    human-in-the-loop 이전 단계 — critical/safe는 사람 검토 없이 자동 처리되므로
    호출자는 반드시 minor를 안전한 기본값으로 취급해야 한다 (BUILD_PLAN FR-34 확장).
    """
    prompt_template = build_problem_report_assessment_prompt()
    model = get_chat_model(temperature=0.0)
    structured_model = model.with_structured_output(ProblemReportAssessment)

    reasons = input_data.report_reasons
    reasons_text = "\n".join(f"- {r}" for r in reasons) if reasons else "(신고 사유 없음)"

    prompt_messages = prompt_template.format_messages(
        problem_id=input_data.problem_id,
        title=input_data.title,
        statement=input_data.statement,
        constraints=", ".join(input_data.constraints) if input_data.constraints else "없음",
        sample_input=input_data.sample_input or "없음",
        sample_output=input_data.sample_output or "없음",
        report_reasons=reasons_text,
    )

    result = structured_model.invoke(prompt_messages)
    result.problem_id = input_data.problem_id
    return result
