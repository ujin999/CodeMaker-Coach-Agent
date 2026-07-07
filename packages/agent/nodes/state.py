from typing import TypedDict, Optional, Any
from agent.schemas import (
    ProblemGenerationInput,
    GeneratedProblem,
    TestcaseBundle,
    HintBundle,
    ReferenceSolution,
    ValidationReport,
    SubmissionResult,
    FeedbackReport,
    RoutingDecision,
    TestcaseRunResult,
    SubmissionEvaluationReport,
    ErrorDiagnosis,
    FailedCaseExplanation,
    ComplexityAnalysis,
)


class AgentState(TypedDict, total=False):
    generation_input: ProblemGenerationInput
    generated_problem: GeneratedProblem
    testcase_bundle: TestcaseBundle
    hint_bundle: HintBundle
    reference_solution: Optional[ReferenceSolution]
    validation_report: ValidationReport
    submission_result: SubmissionResult
    feedback_report: FeedbackReport
    routing_decision: RoutingDecision
    testcase_run_results: list[TestcaseRunResult]
    submission_evaluation_report: SubmissionEvaluationReport
    error_diagnosis: ErrorDiagnosis
    failed_case_explanation: FailedCaseExplanation
    complexity_analysis: ComplexityAnalysis
    min_cases: int
    allowed_hint_level: int
    user_situation: Optional[str]
    errors: list[str]
    metadata: dict[str, Any]
