import re
from typing import Literal, Optional, List
from agent.schemas import (
    GeneratedProblem,
    TestcaseBundle,
    HintBundle,
    ValidationIssue,
    ValidationReport,
)
from agent.nodes.state import AgentState


def validate_problem_basic(problem: GeneratedProblem) -> list[ValidationIssue]:
    """
    Validate basic problem structure.
    """
    issues = []

    def check_non_empty(field_name: str, value: str):
        if not value or not value.strip():
            issues.append(ValidationIssue(
                severity="error",
                code="EMPTY_FIELD",
                message=f"'{field_name}' must not be empty.",
                location=f"problem.{field_name}"
            ))

    check_non_empty("problem_id", problem.problem_id)
    check_non_empty("title", problem.title)
    check_non_empty("statement", problem.statement)
    check_non_empty("input_format", problem.input_format)
    check_non_empty("output_format", problem.output_format)
    check_non_empty("expected_time_complexity", problem.expected_time_complexity)

    if not problem.constraints:
        issues.append(ValidationIssue(
            severity="error",
            code="EMPTY_FIELD",
            message="'constraints' must not be empty.",
            location="problem.constraints"
        ))

    if not problem.algorithm:
        issues.append(ValidationIssue(
            severity="error",
            code="EMPTY_FIELD",
            message="'algorithm' must not be empty.",
            location="problem.algorithm"
        ))

    if problem.hint_blueprint is None:
        issues.append(ValidationIssue(
            severity="error",
            code="MISSING_HINT_BLUEPRINT",
            message="'hint_blueprint' must be present.",
            location="problem.hint_blueprint"
        ))

    # User-facing Korean content warnings
    korean_pattern = re.compile(r'[ㄱ-ㅣ가-힣]')
    user_facing_texts = [
        problem.title,
        problem.statement,
        problem.input_format,
        problem.output_format,
    ]
    if problem.constraints:
        user_facing_texts.extend(problem.constraints)

    all_english = True
    for text in user_facing_texts:
        if text and korean_pattern.search(text):
            all_english = False
            break

    if all_english:
        issues.append(ValidationIssue(
            severity="warning",
            code="ENGLISH_ONLY_PROBLEM",
            message="User-facing problem content appears to contain only English characters. Content should default to Korean.",
            location="problem"
        ))

    return issues


def validate_testcase_bundle(
    problem: GeneratedProblem,
    bundle: TestcaseBundle,
) -> list[ValidationIssue]:
    """
    Validate testcase bundle using deterministic generator-specific validators.
    """
    issues = []

    if bundle.problem_id != problem.problem_id:
        issues.append(ValidationIssue(
            severity="error",
            code="PROBLEM_ID_MISMATCH",
            message=f"TestcaseBundle problem_id '{bundle.problem_id}' does not match problem problem_id '{problem.problem_id}'.",
            location="testcase_bundle"
        ))

    if not bundle.testcases:
        issues.append(ValidationIssue(
            severity="error",
            code="EMPTY_TESTCASE_BUNDLE",
            message="TestcaseBundle must contain at least one testcase.",
            location="testcase_bundle.testcases"
        ))

    has_sample = any(tc.visibility == "sample" for tc in bundle.testcases)
    if not has_sample:
        issues.append(ValidationIssue(
            severity="error",
            code="MISSING_SAMPLE_TESTCASE",
            message="TestcaseBundle must contain at least one sample testcase.",
            location="testcase_bundle.testcases"
        ))

    # Metadata warning checks
    gen_mode = getattr(bundle, "generation_mode", None)
    if gen_mode != "deterministic":
        issues.append(ValidationIssue(
            severity="warning",
            code="NON_DETERMINISTIC_TESTCASES",
            message="TestcaseBundle generation_mode is not 'deterministic'.",
            location="testcase_bundle.generation_mode"
        ))

    gen_name = getattr(bundle, "generator_name", None)
    if not gen_name:
        issues.append(ValidationIssue(
            severity="warning",
            code="MISSING_GENERATOR_NAME",
            message="TestcaseBundle generator_name is missing.",
            location="testcase_bundle.generator_name"
        ))

    ver_status = getattr(bundle, "verification_status", None)
    if ver_status != "passed":
        issues.append(ValidationIssue(
            severity="error",
            code="UNVERIFIED_TESTCASES",
            message="TestcaseBundle verification_status is not 'passed'.",
            location="testcase_bundle.verification_status"
        ))

    # Route and run deterministic validator
    from agent.testcase_generators.base import detect_problem_type

    prob_type = detect_problem_type(problem)
    if prob_type == "budget_cap":
        from agent.testcase_generators.budget_cap import assert_budget_cap_bundle_is_valid
        try:
            assert_budget_cap_bundle_is_valid(bundle)
        except AssertionError as e:
            issues.append(ValidationIssue(
                severity="error",
                code="TESTCASE_VALIDATION_FAILED",
                message=f"Budget cap testcase validation failed: {str(e)}",
                location="testcase_bundle"
            ))
    elif prob_type == "two_pointer_subarray":
        from agent.testcase_generators.two_pointer_subarray import assert_two_pointer_subarray_bundle_is_valid
        try:
            assert_two_pointer_subarray_bundle_is_valid(bundle)
        except AssertionError as e:
            issues.append(ValidationIssue(
                severity="error",
                code="TESTCASE_VALIDATION_FAILED",
                message=f"Two-pointer subarray testcase validation failed: {str(e)}",
                location="testcase_bundle"
            ))
    elif prob_type == "bfs_grid_shortest_path":
        from agent.testcase_generators.bfs_grid_shortest_path import assert_bfs_grid_bundle_is_valid
        try:
            assert_bfs_grid_bundle_is_valid(bundle)
        except AssertionError as e:
            issues.append(ValidationIssue(
                severity="error",
                code="TESTCASE_VALIDATION_FAILED",
                message=f"BFS grid shortest path testcase validation failed: {str(e)}",
                location="testcase_bundle"
            ))
    elif prob_type == "dfs_grid_components":
        from agent.testcase_generators.dfs_grid_components import assert_dfs_grid_bundle_is_valid
        try:
            assert_dfs_grid_bundle_is_valid(bundle)
        except AssertionError as e:
            issues.append(ValidationIssue(
                severity="error",
                code="TESTCASE_VALIDATION_FAILED",
                message=f"DFS grid components testcase validation failed: {str(e)}",
                location="testcase_bundle"
            ))
    else:
        issues.append(ValidationIssue(
            severity="error",
            code="UNSUPPORTED_DETERMINISTIC_GENERATOR",
            message=f"No deterministic testcase generator is available for problem type '{prob_type}'.",
            location="problem"
        ))

    return issues


def validate_hint_bundle(
    problem: GeneratedProblem,
    hint_bundle: HintBundle | None,
) -> list[ValidationIssue]:
    """
    Validate hint safety and consistency.
    """
    issues = []

    if hint_bundle is None:
        return issues

    if hint_bundle.problem_id != problem.problem_id:
        issues.append(ValidationIssue(
            severity="error",
            code="PROBLEM_ID_MISMATCH",
            message=f"HintBundle problem_id '{hint_bundle.problem_id}' does not match problem problem_id '{problem.problem_id}'.",
            location="hint_bundle"
        ))

    for h_idx, hint in enumerate(hint_bundle.hints):
        loc = f"hint_bundle.hints[{h_idx}]"

        # Check every hint's problem_id
        if getattr(hint, "problem_id", None) and hint.problem_id != problem.problem_id:
            issues.append(ValidationIssue(
                severity="error",
                code="PROBLEM_ID_MISMATCH",
                message=f"Hint at index {h_idx} problem_id '{hint.problem_id}' does not match problem problem_id '{problem.problem_id}'.",
                location=loc
            ))

        # Level range validation
        if hint.level not in [1, 2, 3]:
            issues.append(ValidationIssue(
                severity="error",
                code="INVALID_HINT_LEVEL",
                message=f"Hint level {hint.level} is invalid. Must be 1, 2, or 3.",
                location=loc
            ))

        # Revealing code safety checks
        if hint.reveals_core_code:
            issues.append(ValidationIssue(
                severity="error",
                code="REVEALS_CORE_CODE",
                message="Hint reveals_core_code is True, which is forbidden.",
                location=loc
            ))

        # Placeholder requirement for code skeleton
        if hint.code_skeleton:
            placeholders = ["...", "todo", "pass", "here", "fill", "구현", "빈칸", "할 일", "작성", "코드"]
            if not any(p in hint.code_skeleton.lower() for p in placeholders):
                issues.append(ValidationIssue(
                    severity="error",
                    code="INVALID_CODE_SKELETON",
                    message="code_skeleton must contain placeholder markers to be incomplete.",
                    location=loc
                ))

        # Check for full solution code reveal in content
        v = hint.content
        v_lower = v.lower()
        has_python_complete = "def " in v and ":" in v and ("return" in v or "print" in v) and "todo" not in v_lower and "..." not in v_lower and "pass" not in v_lower
        has_cpp_complete = "#include" in v and "main(" in v and "todo" not in v_lower and "..." not in v_lower

        if has_python_complete or has_cpp_complete:
            issues.append(ValidationIssue(
                severity="error",
                code="FULL_SOLUTION_REVEALED",
                message="Hint content appears to contain complete solution code without placeholders.",
                location=loc
            ))

    return issues


def validate_generation_outputs(
    problem: GeneratedProblem,
    testcase_bundle: TestcaseBundle | None = None,
    hint_bundle: HintBundle | None = None,
) -> ValidationReport:
    """
    Aggregate problem, testcase, and hint validation into ValidationReport.
    """
    issues = []
    checked_sections = []

    issues.extend(validate_problem_basic(problem))
    checked_sections.append("problem")

    if testcase_bundle is not None:
        issues.extend(validate_testcase_bundle(problem, testcase_bundle))
        checked_sections.append("testcases")

    if hint_bundle is not None:
        issues.extend(validate_hint_bundle(problem, hint_bundle))
        checked_sections.append("hints")

    error_count = sum(1 for issue in issues if issue.severity == "error")
    passed = (error_count == 0)

    if passed:
        summary = "검증을 통과했습니다."
    else:
        summary = f"검증 실패: {error_count}개의 오류가 발견되었습니다."

    return ValidationReport(
        passed=passed,
        issues=issues,
        checked_sections=checked_sections,
        summary=summary
    )


def validate_outputs_node(state: AgentState) -> AgentState:
    """
    Read generated_problem, testcase_bundle, hint_bundle from state and store validation_report.
    """
    if "generated_problem" not in state or state["generated_problem"] is None:
        raise ValueError("Missing 'generated_problem' in agent state.")

    problem = state["generated_problem"]
    testcases = state.get("testcase_bundle", None)
    hints = state.get("hint_bundle", None)

    report = validate_generation_outputs(problem, testcases, hints)

    new_state = state.copy()
    new_state["validation_report"] = report
    return new_state
