from agent.llm import get_chat_model
from agent.schemas import GeneratedProblem, SubmissionResult, FeedbackReport
from agent.prompts.feedback_generation import build_feedback_generation_prompt

def generate_feedback(problem: GeneratedProblem, submission: SubmissionResult) -> FeedbackReport:
    """Generates feedback report utilizing LLM structured output based on problem and submission details."""
    prompt_template = build_feedback_generation_prompt()
    model = get_chat_model(temperature=0.0)
    structured_model = model.with_structured_output(FeedbackReport)

    prompt_messages = prompt_template.format_messages(
        problem_title=problem.title or "Unknown",
        problem_algorithm=str(problem.algorithm or []),
        problem_statement=problem.statement or "",
        expected_time_complexity=problem.expected_time_complexity or "O(N)",
        result_type=submission.result_type or "WA",
        language=submission.language or "python",
        user_code=submission.user_code or "",
        failed_testcase_name=submission.failed_testcase_name or "None",
        failed_input=submission.failed_input or "None",
        expected_output=submission.expected_output or "None",
        actual_output=submission.actual_output or "None",
        stderr=submission.stderr or "None",
    )

    result = structured_model.invoke(prompt_messages)
    if result:
        result.generated_by = "llm"
        # 프로그램 조건에 맞게 허용 단계 레벨 강제 적용
        from agent.nodes.feedback_node import infer_allowed_hint_level
        result.allowed_hint_level = infer_allowed_hint_level(submission.result_type)
    return result
