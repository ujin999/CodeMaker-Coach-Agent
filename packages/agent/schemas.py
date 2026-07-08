from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class ProblemGenerationInput(BaseModel):
    """Input parameters for the problem generator."""
    algorithm: str = Field(description="The core algorithm type, e.g. binary_search, bfs, dfs, dp_basic, greedy")
    difficulty: str = Field(description="Target difficulty level, e.g. easy, medium, hard")
    problem_style: Optional[str] = Field(default=None, description="Style of the problem description, e.g. practical, mathematical")
    language: Optional[str] = Field(default=None, description="Target programming language, e.g. Python, Java, C++")
    learning_goal: Optional[str] = Field(default=None, description="Learning objective, e.g. parametric search, boundary conditions")
    user_level: Optional[str] = Field(default=None, description="Skill level of the user")
    recent_weaknesses: List[str] = Field(default_factory=list, description="List of user's recent weak concepts")
    seed: Optional[str] = Field(default=None, description="Random seed or nonce to ensure unique variant generation")
    avoid_problem_ids: List[str] = Field(default_factory=list, description="List of problem IDs to avoid repeating")
    force_new: bool = Field(default=False, description="Force generation of a new problem even if cache exists")


class HintBlueprint(BaseModel):
    """A blueprint mapping out the logical steps and constraints for hint generation."""
    intended_algorithm: List[str] = Field(description="Algorithm types needed to solve the problem")
    core_insight: str = Field(description="The main conceptual breakthrough needed")
    common_misconceptions: List[str] = Field(description="Common pitfalls or bugs to alert the user about")
    edge_case_focus: List[str] = Field(description="Extreme inputs or boundary values to check")
    forbidden_disclosures: List[str] = Field(description="Specific elements/code snippets that must not be revealed")
    level_1_guidance: str = Field(description="Strategic advice on direction without naming algorithm")
    level_2_guidance: str = Field(description="Algorithmic approach and conceptual outline")
    level_3_guidance: str = Field(description="Implementation check or structure explanation")
    allowed_code_exposure: Literal["none", "skeleton_only"] = Field(default="none")


class GeneratedProblem(BaseModel):
    """Structured output representation of a generated coding problem."""
    problem_id: str = Field(description="A unique identifier for the generated problem")
    title: str = Field(description="Problem title")
    difficulty: str = Field(description="Difficulty level")
    algorithm: List[str] = Field(description="Underlying algorithms")
    learning_goal: str = Field(description="Selected learning goal")
    statement: str = Field(description="The problem statement / story in detail")
    input_format: str = Field(description="Specification of input data format")
    output_format: str = Field(description="Specification of output data format")
    constraints: List[str] = Field(description="Input and execution constraints")
    sample_input: Optional[str] = Field(default=None, description="Example input data")
    sample_output: Optional[str] = Field(default=None, description="Expected output for sample input")
    expected_time_complexity: str = Field(description="Big-O complexity bound")
    hint_blueprint: HintBlueprint = Field(description="Blueprint containing prompt directions for staged hints")


class GeneratedTestcase(BaseModel):
    """Schema for individual generated testcase."""
    name: str = Field(description="Testcase name / label")
    input_data: str = Field(description="String input matching the input format")
    calculation_steps: Optional[str] = Field(default=None, description="Step-by-step mathematical verification for expected_output")
    expected_output: str = Field(description="Expected output string")
    visibility: Literal["sample", "hidden", "edge"] = Field(description="Visibility category")
    purpose: str = Field(description="Explanation of what this case tests")
    difficulty_reason: Optional[str] = Field(default=None, description="Reason why this case is difficult")


class TestcaseBundle(BaseModel):
    """Schema representing the collection of testcases generated for a problem."""
    __test__ = False
    problem_id: str

    testcases: List[GeneratedTestcase]
    generation_notes: str
    generation_mode: Optional[str] = Field(default=None, description="Testcase generation mode, e.g. deterministic or llm")
    generator_name: Optional[str] = Field(default=None, description="The name of the generator used")
    verification_status: Optional[str] = Field(default=None, description="Status of the validation verification")

    @model_validator(mode="after")
    def validate_testcases(self) -> 'TestcaseBundle':
        has_sample = any(tc.visibility == "sample" for tc in self.testcases)
        if not has_sample:
            raise ValueError("TestcaseBundle must include at least one sample testcase")
        return self


class Hint(BaseModel):
    """Representing a staged hint that can be delivered to the user."""
    problem_id: str
    level: int = Field(description="Stage level of the hint: 1, 2, or 3")
    title: str = Field(description="A short title for the hint")
    content: str = Field(description="User-facing hint content")
    reveals_core_code: bool = Field(default=False)
    code_skeleton: Optional[str] = Field(default=None, description="Incomplete code template")
    concept_refs: List[str] = Field(default_factory=list, description="Related RAG concept filenames")
    source: str = Field(default="generated")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: int) -> int:
        if v not in [1, 2, 3]:
            raise ValueError("Hint level must be 1, 2, or 3")
        return v

    @field_validator("reveals_core_code")
    @classmethod
    def validate_reveals_core_code(cls, v: bool) -> bool:
        if v is not False:
            raise ValueError("reveals_core_code must always be False")
        return v

    @field_validator("content")
    @classmethod
    def validate_content_no_full_code(cls, v: str) -> str:
        # Check for full Python function implementation without placeholders
        v_lower = v.lower()
        if "def " in v and ":" in v and ("return" in v or "print" in v) and "todo" not in v_lower and "..." not in v_lower and "pass" not in v_lower:
            raise ValueError("Obvious full solution code detected in hint content.")
        
        # Check for full C++ main program
        if "#include" in v and "main(" in v and "todo" not in v_lower and "..." not in v_lower:
            raise ValueError("Obvious full solution code detected in hint content.")
            
        return v

    @field_validator("code_skeleton")
    @classmethod
    def validate_skeleton_incomplete(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Check that code skeleton contains incomplete placeholders
            placeholders = ["...", "todo", "pass", "here", "fill", "구현", "빈칸", "할 일", "작성", "코드"]
            if not any(p in v.lower() for p in placeholders):
                raise ValueError("code_skeleton must be incomplete (include '...', 'TODO', or similar placeholders)")
        return v


class HintBundle(BaseModel):
    """Bundle of all hints (Level 1, 2, and 3) generated for a coding problem."""
    problem_id: str
    blueprint: HintBlueprint
    hints: List[Hint]


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    location: Optional[str] = None


class ValidationReport(BaseModel):
    passed: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    checked_sections: List[str] = Field(default_factory=list)
    summary: str = ""

    @model_validator(mode="after")
    def enforce_passed_invariance(self) -> 'ValidationReport':
        has_error = any(issue.severity == "error" for issue in self.issues)
        if has_error:
            self.passed = False
        return self


class SubmissionResult(BaseModel):
    problem_id: str
    result_type: Literal[
        "AC",
        "WA",
        "TLE",
        "RE",
        "MLE",
        "CE",
        "PE",
        "UNKNOWN",
    ]
    user_code: Optional[str] = None
    language: Optional[str] = None
    failed_testcase_name: Optional[str] = None
    failed_input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    stderr: Optional[str] = None
    execution_time_ms: Optional[int] = None
    memory_kb: Optional[int] = None


class FeedbackReport(BaseModel):
    problem_id: str
    result_type: str
    summary: str
    likely_causes: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    allowed_hint_level: int = 1
    safe_to_show: bool = True
    generated_by: Literal["deterministic", "llm"] = "deterministic"

    @field_validator("allowed_hint_level")
    @classmethod
    def validate_allowed_hint_level(cls, v: int) -> int:
        if v not in [1, 2, 3]:
            raise ValueError("allowed_hint_level must be 1, 2, or 3")
        return v

    @model_validator(mode="after")
    def validate_safety_policy(self) -> 'FeedbackReport':
        # Simple conservative checker for full solution code in summary, likely_causes, or next_steps
        unsafe = False
        kws = [
            "def ",
            "import ",
            "#include",
            "main(",
            "public static void main",
            "class solution",
            "return "
        ]
        placeholders = ["todo", "...", "pass", "구현", "빈칸", "작성"]
        for field in [self.summary] + self.likely_causes + self.next_steps:
            if not field:
                continue
            field_lower = field.lower()
            if any(kw in field_lower for kw in kws):
                if not any(ph in field_lower for ph in placeholders):
                    unsafe = True
                    break
        if unsafe:
            self.safe_to_show = False
        return self


class RoutingDecision(BaseModel):
    action: Literal[
        "present_to_user",
        "regenerate_problem",
        "regenerate_testcases",
        "revise_hints",
        "request_human_review",
        "show_feedback",
        "block_output",
    ]
    reason: str
    confidence: Literal["low", "medium", "high"] = "medium"
    blocking_issue_codes: List[str] = Field(default_factory=list)
    safe_to_continue: bool = True

    @model_validator(mode="after")
    def validate_routing_rules(self) -> 'RoutingDecision':
        if self.action == "block_output" and self.safe_to_continue:
            raise ValueError("safe_to_continue must be False when action is block_output.")
        if self.blocking_issue_codes and self.action == "present_to_user":
            raise ValueError("Cannot present to user when blocking issue codes exist.")
        if not self.reason or not self.reason.strip():
            raise ValueError("Reason must be non-empty.")
        return self


class TestcaseRunResult(BaseModel):
    __test__ = False
    testcase_name: str
    status: Literal[
        "AC",
        "WA",
        "TLE",
        "RE",
        "MLE",
        "CE",
        "PE",
        "UNKNOWN",
    ] = "UNKNOWN"
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    stderr: Optional[str] = None
    execution_time_ms: Optional[int] = None
    memory_kb: Optional[int] = None


class SubmissionEvaluationReport(BaseModel):
    problem_id: str
    result_type: Literal[
        "AC",
        "WA",
        "TLE",
        "RE",
        "MLE",
        "CE",
        "PE",
        "UNKNOWN",
    ]
    testcase_results: List[TestcaseRunResult] = Field(default_factory=list)
    total_count: int = 0
    passed_count: int = 0
    first_failed_testcase_name: Optional[str] = None
    failed_input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    stderr: Optional[str] = None
    max_execution_time_ms: Optional[int] = None
    max_memory_kb: Optional[int] = None
    summary: str = ""

    @model_validator(mode="after")
    def validate_evaluation_invariants(self) -> 'SubmissionEvaluationReport':
        expected_total = len(self.testcase_results)
        if self.total_count != expected_total:
            self.total_count = expected_total

        if not (0 <= self.passed_count <= self.total_count):
            raise ValueError(f"passed_count must be between 0 and total_count ({self.total_count})")

        all_ac = all(res.status == "AC" for res in self.testcase_results)
        if self.result_type == "AC" and not all_ac and self.testcase_results:
            raise ValueError("result_type cannot be AC if not all testcases have status AC")

        return self


class ReferenceSolution(BaseModel):
    """내부 정답 코드 — 절대 힌트/일반 API 응답으로 노출하지 않는다 (FR-20, 정책 1).

    문제와 동일한 결정론적 solver 로직으로 생성되며, Judge0에서 testcase_bundle에
    대해 실행 검증한 뒤 verified 플래그가 채워진다.
    """
    problem_id: str
    language: str = "python"
    code: str
    generator_name: str
    verified: bool = False
    verification_notes: str = ""


class ErrorDiagnosis(BaseModel):
    problem_id: str
    result_type: Literal["AC", "WA", "TLE", "RE", "MLE", "CE", "PE", "UNKNOWN"]
    primary_cause: str
    confidence: Literal["low", "medium", "high"] = "medium"
    evidence: List[str] = Field(default_factory=list)
    related_concepts: List[str] = Field(default_factory=list)
    suggested_focus: List[str] = Field(default_factory=list)
    safe_to_show: bool = True

    @model_validator(mode="after")
    def validate_safety_policy(self) -> "ErrorDiagnosis":
        unsafe = False
        kws = [
            "def ",
            "import ",
            "#include",
            "main(",
            "public static void main",
            "class solution",
            "return ",
        ]
        placeholders = ["todo", "...", "pass", "구현", "빈칸", "작성"]
        for field in [self.primary_cause] + self.evidence + self.suggested_focus:
            if not field:
                continue
            field_lower = field.lower()
            if any(kw in field_lower for kw in kws):
                if not any(ph in field_lower for ph in placeholders):
                    unsafe = True
                    break
        if unsafe:
            self.safe_to_show = False
        return self


class FailedCaseExplanation(BaseModel):
    problem_id: str
    testcase_name: Optional[str] = None
    summary: str
    input_observation: Optional[str] = None
    expected_vs_actual: Optional[str] = None
    likely_gap: Optional[str] = None
    safe_to_show: bool = True

    @model_validator(mode="after")
    def validate_safety_policy(self) -> "FailedCaseExplanation":
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be non-empty.")
        unsafe = False
        kws = [
            "def ",
            "import ",
            "#include",
            "main(",
            "public static void main",
            "class solution",
            "return ",
        ]
        placeholders = ["todo", "...", "pass", "구현", "빈칸", "작성"]
        for field in [
            self.summary,
            self.input_observation,
            self.expected_vs_actual,
            self.likely_gap,
        ]:
            if not field:
                continue
            field_lower = field.lower()
            if any(kw in field_lower for kw in kws):
                if not any(ph in field_lower for ph in placeholders):
                    unsafe = True
                    break
        if unsafe:
            self.safe_to_show = False
        return self


class ComplexityAnalysis(BaseModel):
    problem_id: str
    result_type: Literal["AC", "WA", "TLE", "RE", "MLE", "CE", "PE", "UNKNOWN"]
    expected_time_complexity: Optional[str] = None
    observed_pattern: Optional[str] = None
    suspected_complexity: Optional[str] = None
    risk_level: Literal["low", "medium", "high"] = "medium"
    evidence: List[str] = Field(default_factory=list)
    related_concepts: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)
    safe_to_show: bool = True

    @model_validator(mode="after")
    def validate_safety_policy(self) -> "ComplexityAnalysis":
        unsafe = False
        kws = [
            "def ",
            "import ",
            "#include",
            "main(",
            "public static void main",
            "class solution",
            "return ",
        ]
        placeholders = ["todo", "...", "pass", "구현", "빈칸", "작성"]
        for field in self.evidence + self.suggested_actions:
            if not field:
                continue
            field_lower = field.lower()
            if any(kw in field_lower for kw in kws):
                if not any(ph in field_lower for ph in placeholders):
                    unsafe = True
                    break
        if unsafe:
            self.safe_to_show = False
        return self


class CounterexampleReport(BaseModel):
    problem_id: str
    result_type: Literal["AC", "WA", "TLE", "RE", "MLE", "CE", "PE", "UNKNOWN"]
    testcase_name: Optional[str] = None
    counterexample_input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    explanation: str
    lesson: Optional[str] = None
    safe_to_show: bool = True

    @model_validator(mode="after")
    def validate_safety_policy(self) -> "CounterexampleReport":
        if not self.explanation or not self.explanation.strip():
            raise ValueError("explanation must be non-empty.")

        unsafe = False
        kws = [
            "def ",
            "import ",
            "#include",
            "main(",
            "public static void main",
            "class solution",
            "return ",
        ]
        placeholders = ["todo", "...", "pass", "구현", "빈칸", "작성"]
        for field in [self.explanation, self.lesson]:
            if not field:
                continue
            field_lower = field.lower()
            if any(kw in field_lower for kw in kws):
                if not any(ph in field_lower for ph in placeholders):
                    unsafe = True
                    break
        if unsafe:
            self.safe_to_show = False
        return self


class SubmissionReviewPackage(BaseModel):
    problem_id: str
    result_type: Literal["AC", "WA", "TLE", "RE", "MLE", "CE", "PE", "UNKNOWN"]
    evaluation_report: Optional[SubmissionEvaluationReport] = None
    error_diagnosis: Optional[ErrorDiagnosis] = None
    failed_case_explanation: Optional[FailedCaseExplanation] = None
    complexity_analysis: Optional[ComplexityAnalysis] = None
    counterexample_report: Optional[CounterexampleReport] = None
    feedback_report: Optional[FeedbackReport] = None
    routing_decision: Optional[RoutingDecision] = None
    concept_context: List[str] = Field(default_factory=list)
    summary: str = ""
    safe_to_show: bool = True

    @model_validator(mode="after")
    def validate_package_safety(self) -> "SubmissionReviewPackage":
        reports = [
            self.evaluation_report,
            self.error_diagnosis,
            self.failed_case_explanation,
            self.complexity_analysis,
            self.counterexample_report,
            self.feedback_report,
            self.routing_decision,
        ]
        for r in reports:
            if r is not None and hasattr(r, "safe_to_show") and not r.safe_to_show:
                self.safe_to_show = False
                break

        unsafe = False
        kws = [
            "def ",
            "import ",
            "#include",
            "main(",
            "public static void main",
            "class solution",
            "return ",
        ]
        placeholders = ["todo", "...", "pass", "구현", "빈칸", "작성"]
        if self.summary:
            summary_lower = self.summary.lower()
            if any(kw in summary_lower for kw in kws):
                if not any(ph in summary_lower for ph in placeholders):
                    unsafe = True
        if unsafe:
            self.safe_to_show = False

        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be non-empty.")

        return self


class ProblemGenerationPackage(BaseModel):
    problem_id: str
    generated_problem: GeneratedProblem
    testcase_bundle: Optional[TestcaseBundle] = None
    reference_solution: Optional[ReferenceSolution] = None
    validation_report: Optional[ValidationReport] = None
    hint_bundle: Optional[HintBundle] = None
    concept_context: List[str] = Field(default_factory=list)
    summary: str = ""
    safe_to_show: bool = True
    generation_mode: Optional[str] = "live"
    seed: Optional[str] = None
    variant_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_package(self) -> "ProblemGenerationPackage":
        if self.validation_report and not self.validation_report.passed:
            self.safe_to_show = False

        reports = [
            self.generated_problem,
            self.testcase_bundle,
            self.hint_bundle
        ]
        for r in reports:
            if r is not None and hasattr(r, "safe_to_show") and not r.safe_to_show:
                self.safe_to_show = False
                break

        unsafe = False
        kws = [
            "def ",
            "import ",
            "#include",
            "main(",
            "public static void main",
            "class solution",
            "return ",
        ]
        placeholders = ["todo", "...", "pass", "구현", "빈칸", "작성"]
        if self.summary:
            summary_lower = self.summary.lower()
            if any(kw in summary_lower for kw in kws):
                if not any(ph in summary_lower for ph in placeholders):
                    unsafe = True
        if unsafe:
            self.safe_to_show = False

        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be non-empty.")

        return self


class ProblemGenerationPackageInput(BaseModel):
    algorithm: str
    difficulty: str
    problem_style: Optional[str] = None
    language: Optional[str] = "python"
    learning_goal: Optional[str] = None
    user_level: Optional[str] = None
    recent_weaknesses: List[str] = Field(default_factory=list)
    include_hints: bool = True
    include_concept_context: bool = True
    max_validation_attempts: int = 2
    seed: Optional[str] = None
    avoid_problem_ids: List[str] = Field(default_factory=list)
    force_new: bool = False

    @field_validator("max_validation_attempts")
    @classmethod
    def validate_max_validation_attempts(cls, v: int) -> int:
        if not (1 <= v <= 5):
            raise ValueError("max_validation_attempts must be between 1 and 5.")
        return v


class HintRequestPackageInput(BaseModel):
    problem_id: str
    query: str = "힌트를 주세요."
    allowed_level: int = 1
    requested_level: Optional[int] = None
    user_situation: Optional[str] = None
    include_sources: bool = True

    @field_validator("allowed_level")
    @classmethod
    def validate_allowed_level(cls, v: int) -> int:
        if v not in [1, 2, 3]:
            raise ValueError("allowed_level must be 1, 2, or 3.")
        return v

    @field_validator("requested_level")
    @classmethod
    def validate_requested_level(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in [1, 2, 3]:
            raise ValueError("requested_level must be 1, 2, or 3 if provided.")
        return v


class HintRequestPackage(BaseModel):
    problem_id: str
    allowed_level: int
    requested_level: Optional[int] = None
    delivered_level: int
    hints: List[Hint] = Field(default_factory=list)
    blocked: bool = False
    block_reason: Optional[str] = None
    source_refs: List[str] = Field(default_factory=list)
    summary: str = ""
    safe_to_show: bool = True

    @model_validator(mode="after")
    def validate_hint_package(self) -> "HintRequestPackage":
        if self.delivered_level > self.allowed_level:
            raise ValueError("delivered_level must not exceed allowed_level.")

        for h in self.hints:
            if h.reveals_core_code:
                self.safe_to_show = False
                break

        if self.blocked:
            for h in self.hints:
                if h.level > self.allowed_level:
                    raise ValueError("Hints must not exceed allowed_level when blocked.")

        unsafe = False
        kws = [
            "def ",
            "import ",
            "#include",
            "main(",
            "public static void main",
            "class solution",
            "return ",
        ]
        placeholders = ["todo", "...", "pass", "구현", "빈칸", "작성"]
        if self.summary:
            summary_lower = self.summary.lower()
            if any(kw in summary_lower for kw in kws):
                if not any(ph in summary_lower for ph in placeholders):
                    unsafe = True
        if unsafe:
            self.safe_to_show = False

        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be non-empty.")


class ProblemReportAssessmentInput(BaseModel):
    """신고 누적 문제 재검증 요청 입력 — HITL 이전 Agent 판정 단계."""
    problem_id: str
    title: str
    statement: str
    constraints: List[str] = Field(default_factory=list)
    sample_input: Optional[str] = None
    sample_output: Optional[str] = None
    report_reasons: List[str] = Field(default_factory=list)


class ProblemReportAssessment(BaseModel):
    """Agent의 신고 재검증 결과.

    - critical: 문제 자체에 치명적 결함이 명확함 -> human 검토 없이 즉시 삭제.
    - safe: 신고 사유가 근거 없음(오신고) -> human 검토 없이 즉시 기각.
    - minor: 애매하거나 판단 근거가 불충분함 -> 기존대로 human-in-the-loop 진행.
    """
    problem_id: str
    severity: Literal["critical", "safe", "minor"]
    reasoning: str = Field(description="판정 근거 (한국어)")
    confidence: Literal["low", "medium", "high"] = "medium"

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("reasoning must be non-empty.")
        return v

        return self
