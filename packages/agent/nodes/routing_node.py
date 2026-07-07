from typing import Optional
from agent.schemas import ValidationReport, FeedbackReport, RoutingDecision
from agent.nodes.state import AgentState


def decide_from_validation_report(report: ValidationReport) -> RoutingDecision:
    """
    Decide what to do based on validation report.
    """
    error_codes = [issue.code for issue in report.issues if issue.severity == "error"]

    if report.passed:
        return RoutingDecision(
            action="present_to_user",
            reason="모든 검증을 통과했습니다.",
            confidence="high",
            blocking_issue_codes=[],
            safe_to_continue=True
        )

    if any(code.startswith("TESTCASE") or code == "TESTCASE_VALIDATION_FAILED" for code in error_codes):
        return RoutingDecision(
            action="regenerate_testcases",
            reason="테스트케이스 검증 실패가 감지되었습니다. 테스트케이스 재생성이 필요합니다.",
            confidence="medium",
            blocking_issue_codes=error_codes,
            safe_to_continue=True
        )

    if "REFERENCE_SOLUTION_UNVERIFIED" in error_codes:
        return RoutingDecision(
            action="regenerate_testcases",
            reason="정답 코드가 Judge0 검증을 통과하지 못했습니다. 테스트케이스/문제 재생성이 필요합니다.",
            confidence="medium",
            blocking_issue_codes=error_codes,
            safe_to_continue=True
        )

    if "UNSUPPORTED_DETERMINISTIC_GENERATOR" in error_codes:
        return RoutingDecision(
            action="request_human_review",
            reason="결정론적 테스트케이스 생성기가 지원되지 않는 문제 유형입니다. 인간 검토가 필요합니다.",
            confidence="medium",
            blocking_issue_codes=error_codes,
            safe_to_continue=True
        )

    if any("HINT" in code or "SOLUTION_LEAK" in code for code in error_codes):
        return RoutingDecision(
            action="revise_hints",
            reason="힌트 유효성 검증 오류 또는 솔루션 유출이 감지되었습니다. 힌트 수정이 필요합니다.",
            confidence="medium",
            blocking_issue_codes=error_codes,
            safe_to_continue=True
        )

    if any("PROBLEM" in code for code in error_codes):
        return RoutingDecision(
            action="regenerate_problem",
            reason="문제의 필수 필드 누락 또는 형식 오류가 감지되었습니다. 문제 재생성이 필요합니다.",
            confidence="medium",
            blocking_issue_codes=error_codes,
            safe_to_continue=True
        )

    return RoutingDecision(
        action="request_human_review",
        reason="기타 심각한 오류가 감지되어 인간 검토를 요청합니다.",
        confidence="medium",
        blocking_issue_codes=error_codes,
        safe_to_continue=True
    )


def decide_from_feedback_report(report: FeedbackReport) -> RoutingDecision:
    """
    Decide whether feedback can be shown safely.
    """
    if not report.safe_to_show:
        return RoutingDecision(
            action="block_output",
            reason="피드백 내용에 정답 코드 유출 가능성이 감지되어 출력을 차단합니다.",
            confidence="high",
            blocking_issue_codes=["FEEDBACK_SOLUTION_LEAK"],
            safe_to_continue=False
        )
    return RoutingDecision(
        action="show_feedback",
        reason="안전한 피드백 출력이 확인되었습니다.",
        confidence="high",
        blocking_issue_codes=[],
        safe_to_continue=True
    )


def decide_next_action(
    validation_report: Optional[ValidationReport] = None,
    feedback_report: Optional[FeedbackReport] = None,
) -> RoutingDecision:
    """
    Decide next action from available reports.
    Feedback safety has priority over validation.
    """
    if feedback_report is not None:
        fb_decision = decide_from_feedback_report(feedback_report)
        if fb_decision.action == "block_output":
            return fb_decision

    if validation_report is not None:
        return decide_from_validation_report(validation_report)

    if feedback_report is not None:
        # feedback_report exists and is safe
        return decide_from_feedback_report(feedback_report)

    return RoutingDecision(
        action="request_human_review",
        reason="검증 보고서 및 피드백 보고서가 존재하지 않습니다.",
        confidence="low",
        blocking_issue_codes=[],
        safe_to_continue=True
    )


def route_next_action_node(state: AgentState) -> AgentState:
    """
    Read validation_report and/or feedback_report from state.
    Store routing_decision.
    """
    validation_report = state.get("validation_report", None)
    feedback_report = state.get("feedback_report", None)

    decision = decide_next_action(validation_report, feedback_report)

    new_state = state.copy()
    new_state["routing_decision"] = decision
    return new_state
