from agent.llm import get_chat_model
from agent.schemas import GeneratedProblem, StubCheckReport, BuggyProblemReport
from agent.prompts.sweeper import build_stub_evaluator_prompt, build_debugger_prompt


def evaluate_stub_problem(problem: GeneratedProblem) -> StubCheckReport:
    """문제의 지문과 제목을 LLM으로 분석하여 스텁/더미 임시 데이터 여부를 판정한다."""
    prompt_template = build_stub_evaluator_prompt()
    model = get_chat_model(temperature=0.0)
    structured_model = model.with_structured_output(StubCheckReport)

    prompt_messages = prompt_template.format_messages(
        problem_id=problem.problem_id,
        title=problem.title,
        statement=problem.statement,
        constraints=", ".join(problem.constraints) if problem.constraints else "없음",
        sample_input=problem.sample_input or "없음",
        sample_output=problem.sample_output or "없음"
    )

    result = structured_model.invoke(prompt_messages)
    result.problem_id = problem.problem_id
    return result


def diagnose_buggy_problem(
    problem: GeneratedProblem,
    reference_code: str,
    error_logs: str,
) -> BuggyProblemReport:
    """에러 로그와 정답 코드를 비교 분석하여 문제 자체의 출제 결함(Buggy) 여부를 판정한다."""
    prompt_template = build_debugger_prompt()
    model = get_chat_model(temperature=0.0)
    structured_model = model.with_structured_output(BuggyProblemReport)

    prompt_messages = prompt_template.format_messages(
        title=problem.title,
        statement=problem.statement,
        reference_code=reference_code or "(정답 코드 없음)",
        error_logs=error_logs or "(실행 에러 로그 없음)"
    )

    result = structured_model.invoke(prompt_messages)
    result.problem_id = problem.problem_id
    return result
