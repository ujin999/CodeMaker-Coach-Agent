import pytest
from agent.schemas import (
    ValidationReport,
    ValidationIssue,
    FeedbackReport,
    RoutingDecision,
)
from agent.nodes import (
    decide_from_validation_report,
    decide_from_feedback_report,
    decide_next_action,
    route_next_action_node,
    AgentState,
)


def test_passed_validation_report():
    """Test A: Passed validation report translates to present_to_user decision."""
    report = ValidationReport(passed=True, issues=[], summary="통과")
    decision = decide_from_validation_report(report)
    assert decision.action == "present_to_user"
    assert decision.safe_to_continue is True
    assert decision.confidence == "high"
    assert len(decision.blocking_issue_codes) == 0


def test_testcase_validation_failure():
    """Test B: Testcase validation error triggers regenerate_testcases action."""
    report = ValidationReport(
        passed=False,
        issues=[
            ValidationIssue(
                severity="error",
                code="TESTCASE_VALIDATION_FAILED",
                message="테스트케이스 검증 실패"
            )
        ]
    )
    decision = decide_from_validation_report(report)
    assert decision.action == "regenerate_testcases"
    assert decision.safe_to_continue is True
    assert "TESTCASE_VALIDATION_FAILED" in decision.blocking_issue_codes


def test_unsupported_generator():
    """Test C: Unsupported generator code triggers request_human_review."""
    report = ValidationReport(
        passed=False,
        issues=[
            ValidationIssue(
                severity="error",
                code="UNSUPPORTED_DETERMINISTIC_GENERATOR",
                message="지원 안함"
            )
        ]
    )
    decision = decide_from_validation_report(report)
    assert decision.action == "request_human_review"
    assert "UNSUPPORTED_DETERMINISTIC_GENERATOR" in decision.blocking_issue_codes


def test_hint_leak():
    """Test D: Hint leak issue triggers revise_hints action."""
    report = ValidationReport(
        passed=False,
        issues=[
            ValidationIssue(
                severity="error",
                code="HINT_SOLUTION_LEAK",
                message="힌트 정답 유출"
            )
        ]
    )
    decision = decide_from_validation_report(report)
    assert decision.action == "revise_hints"
    assert "HINT_SOLUTION_LEAK" in decision.blocking_issue_codes


def test_problem_error():
    """Test E: Problem statement missing triggers regenerate_problem action."""
    report = ValidationReport(
        passed=False,
        issues=[
            ValidationIssue(
                severity="error",
                code="PROBLEM_EMPTY_STATEMENT",
                message="설명 빈칸"
            )
        ]
    )
    decision = decide_from_validation_report(report)
    assert decision.action == "regenerate_problem"
    assert "PROBLEM_EMPTY_STATEMENT" in decision.blocking_issue_codes


def test_unsafe_feedback():
    """Test F: Unsafe feedback report maps to block_output action and sets safe_to_continue=False."""
    report = FeedbackReport(
        problem_id="test",
        result_type="WA",
        summary="피드백",
        safe_to_show=False
    )
    decision = decide_from_feedback_report(report)
    assert decision.action == "block_output"
    assert decision.safe_to_continue is False
    assert decision.confidence == "high"


def test_safe_feedback():
    """Test G: Safe feedback report maps to show_feedback action."""
    report = FeedbackReport(
        problem_id="test",
        result_type="WA",
        summary="피드백",
        safe_to_show=True
    )
    decision = decide_from_feedback_report(report)
    assert decision.action == "show_feedback"
    assert decision.safe_to_continue is True
    assert decision.confidence == "high"


def test_decide_next_action_priority():
    """Test H: Priority logic of decide_next_action (unsafe feedback overrides validation)."""
    val_passed = ValidationReport(passed=True, issues=[], summary="통과")
    val_failed = ValidationReport(
        passed=False,
        issues=[
            ValidationIssue(
                severity="error",
                code="TESTCASE_VALIDATION_FAILED",
                message="실패"
            )
        ]
    )

    fb_safe = FeedbackReport(
        problem_id="test",
        result_type="WA",
        summary="피드백",
        safe_to_show=True
    )
    fb_unsafe = FeedbackReport(
        problem_id="test",
        result_type="WA",
        summary="피드백",
        safe_to_show=False
    )

    # 1. Validation passed, feedback unsafe -> block_output
    d1 = decide_next_action(val_passed, fb_unsafe)
    assert d1.action == "block_output"

    # 2. Validation failed, feedback safe -> validation action applies (regenerate_testcases)
    d2 = decide_next_action(val_failed, fb_safe)
    assert d2.action == "regenerate_testcases"

    # 3. No reports -> request_human_review with low confidence
    d3 = decide_next_action(None, None)
    assert d3.action == "request_human_review"
    assert d3.confidence == "low"


def test_route_next_action_node():
    """Test I: route_next_action_node reads state reports and stores decision."""
    val_passed = ValidationReport(passed=True, issues=[], summary="통과")
    state = AgentState(validation_report=val_passed)

    new_state = route_next_action_node(state)
    assert "routing_decision" in new_state
    assert new_state["routing_decision"].action == "present_to_user"


def test_routing_decision_schema_validation():
    """Test J: RoutingDecision validation rules."""
    # 1. action="block_output" with safe_to_continue=True raises ValueError
    with pytest.raises(ValueError, match="safe_to_continue"):
        RoutingDecision(
            action="block_output",
            reason="차단",
            safe_to_continue=True
        )

    # 2. action="present_to_user" with blocking_issue_codes raises ValueError
    with pytest.raises(ValueError, match="Cannot present to user"):
        RoutingDecision(
            action="present_to_user",
            reason="오류있음",
            blocking_issue_codes=["SOME_ERROR"],
            safe_to_continue=True
        )

    # 3. empty reason raises ValueError
    with pytest.raises(ValueError, match="Reason must be non-empty"):
        RoutingDecision(
            action="present_to_user",
            reason="   ",
            safe_to_continue=True
        )
