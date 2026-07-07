from typing import Literal, Optional, List
from agent.schemas import GeneratedProblem, TestcaseRunResult, SubmissionEvaluationReport, SubmissionResult
from agent.nodes.state import AgentState


def normalize_output(output: str | None) -> str:
    """
    Normalize line endings and trailing newlines.
    Do not aggressively remove internal whitespace.
    """
    if output is None:
        return ""
    normalized = output.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.rstrip("\n")


def whitespace_normalize_output(output: str | None) -> str:
    """
    Normalize all whitespace for presentation-error style comparison.
    """
    if output is None:
        return ""
    return " ".join(output.split())


def compare_expected_actual(
    expected_output: str | None,
    actual_output: str | None,
) -> Literal["AC", "PE", "WA"]:
    """
    Compare expected and actual outputs.
    """
    if normalize_output(expected_output) == normalize_output(actual_output):
        return "AC"
    if whitespace_normalize_output(expected_output) == whitespace_normalize_output(actual_output):
        return "PE"
    return "WA"


def infer_testcase_status(result: TestcaseRunResult) -> TestcaseRunResult:
    """
    If result.status is UNKNOWN and expected/actual exist, infer AC/PE/WA.
    Otherwise keep explicit non-UNKNOWN status.
    """
    if result.status != "UNKNOWN":
        return result

    if result.expected_output is not None or result.actual_output is not None:
        inferred = compare_expected_actual(result.expected_output, result.actual_output)
        return result.model_copy(update={"status": inferred})

    return result


def aggregate_result_type(results: List[TestcaseRunResult]) -> str:
    """
    Aggregate testcase statuses into one submission result type based on deterministic priority.
    """
    if not results:
        return "UNKNOWN"

    # 1. CE has top priority
    if any(res.status == "CE" for res in results):
        return "CE"

    # 2. WA, TLE, RE, MLE in order of appearance
    for res in results:
        if res.status in ["WA", "TLE", "RE", "MLE"]:
            return res.status

    # 3. PE in order of appearance
    for res in results:
        if res.status == "PE":
            return "PE"

    # 4. UNKNOWN
    if any(res.status == "UNKNOWN" for res in results):
        return "UNKNOWN"

    # 5. All AC
    return "AC"


def build_submission_evaluation_report(
    problem_id: str,
    testcase_results: List[TestcaseRunResult],
) -> SubmissionEvaluationReport:
    """
    Infer statuses, aggregate result type, and build a summary.
    """
    inferred_results = [infer_testcase_status(res) for res in testcase_results]

    total_count = len(inferred_results)
    passed_count = sum(1 for res in inferred_results if res.status == "AC")
    result_type = aggregate_result_type(inferred_results)

    first_failed = None
    for res in inferred_results:
        if res.status != "AC":
            first_failed = res
            break

    failed_name = None
    failed_input = None
    expected_output = None
    actual_output = None
    stderr = None

    if first_failed is not None:
        failed_name = first_failed.testcase_name
        failed_input = first_failed.input_data
        expected_output = first_failed.expected_output
        actual_output = first_failed.actual_output
        stderr = first_failed.stderr

    execution_times = [res.execution_time_ms for res in inferred_results if res.execution_time_ms is not None]
    max_execution_time_ms = max(execution_times) if execution_times else None

    memories = [res.memory_kb for res in inferred_results if res.memory_kb is not None]
    max_memory_kb = max(memories) if memories else None

    summaries = {
        "AC": "모든 테스트케이스를 통과했습니다.",
        "WA": "일부 테스트케이스에서 기대 출력과 실제 출력이 다릅니다.",
        "PE": "출력 형식 차이가 의심됩니다.",
        "TLE": "시간 제한 초과가 발생했습니다.",
        "RE": "런타임 오류가 발생했습니다.",
        "MLE": "메모리 제한 초과가 발생했습니다.",
        "CE": "컴파일 오류가 발생했습니다.",
        "UNKNOWN": "제출 결과를 명확히 판정할 수 없습니다.",
    }
    summary = summaries.get(result_type, "제출 결과를 명확히 판정할 수 없습니다.")

    return SubmissionEvaluationReport(
        problem_id=problem_id,
        result_type=result_type,
        testcase_results=inferred_results,
        total_count=total_count,
        passed_count=passed_count,
        first_failed_testcase_name=failed_name,
        failed_input=failed_input,
        expected_output=expected_output,
        actual_output=actual_output,
        stderr=stderr,
        max_execution_time_ms=max_execution_time_ms,
        max_memory_kb=max_memory_kb,
        summary=summary,
    )


def build_submission_result_from_evaluation(
    report: SubmissionEvaluationReport,
    user_code: str | None = None,
    language: str | None = None,
) -> SubmissionResult:
    """
    Convert SubmissionEvaluationReport to Feedback-compatible SubmissionResult.
    """
    return SubmissionResult(
        problem_id=report.problem_id,
        result_type=report.result_type,
        failed_testcase_name=report.first_failed_testcase_name,
        failed_input=report.failed_input,
        expected_output=report.expected_output,
        actual_output=report.actual_output,
        stderr=report.stderr,
        execution_time_ms=report.max_execution_time_ms,
        memory_kb=report.max_memory_kb,
        user_code=user_code,
        language=language
    )


def evaluate_submission_node(state: AgentState) -> AgentState:
    """
    Read generated_problem and testcase_run_results from state.
    Produce submission_evaluation_report and submission_result.
    """
    if "generated_problem" not in state or state["generated_problem"] is None:
        raise ValueError("Missing 'generated_problem' in agent state.")
    if "testcase_run_results" not in state or state["testcase_run_results"] is None:
        raise ValueError("Missing 'testcase_run_results' in agent state.")

    problem = state["generated_problem"]
    results = state["testcase_run_results"]

    existing_sub = state.get("submission_result", None)
    user_code = existing_sub.user_code if existing_sub else None
    language = existing_sub.language if existing_sub else None

    report = build_submission_evaluation_report(problem.problem_id, results)
    sub_res = build_submission_result_from_evaluation(report, user_code=user_code, language=language)

    new_state = state.copy()
    new_state["submission_evaluation_report"] = report
    new_state["submission_result"] = sub_res
    return new_state
