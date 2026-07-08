"""API 요청/응답 Pydantic 스키마 — Problem / Submission / Hint / Community 도메인."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# ── Problem ──────────────────────────────────────────────────────────────────

class ProblemSummaryResponse(BaseModel):
    """목록용 요약 (reference_solution 절대 포함 안 함)."""
    id: str
    title: str
    difficulty: str
    algorithm: List[str]
    learning_goal: str
    expected_time_complexity: str
    created_at: datetime
    created_by_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ProblemDetailResponse(BaseModel):
    """풀이 화면용 상세 (reference_solution 제외)."""
    id: str
    title: str
    difficulty: str
    algorithm: List[str]
    learning_goal: str
    statement: str
    input_format: str
    output_format: str
    constraints: List[str]
    sample_input: Optional[str]
    sample_output: Optional[str]
    expected_time_complexity: str
    created_at: datetime
    created_by_name: Optional[str] = None
    generation_mode: Optional[str] = None
    seed: Optional[str] = None
    variant_id: Optional[str] = None

    model_config = {"from_attributes": True}


class RevealSolutionRequest(BaseModel):
    """정답 코드 열람 요청 — 명시적 확인 필수 (FR-20)."""
    confirm: bool = Field(description="'정말 정답을 확인하시겠습니까?'에 대한 명시적 동의")


class RevealSolutionResponse(BaseModel):
    problem_id: str
    language: str
    code: str

    model_config = {"from_attributes": True}


# ── Submission ───────────────────────────────────────────────────────────────

class SubmissionRequest(BaseModel):
    code: str = Field(description="사용자 제출 코드")
    language: str = Field(description="언어 식별자 (python, java, cpp 등)")


class SubmissionResponse(BaseModel):
    id: int
    problem_id: str
    language: str
    status: str  # PENDING | JUDGING | AC | WA | TLE | RE | MLE
    runtime_ms: Optional[int]
    memory_kb: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Hint ─────────────────────────────────────────────────────────────────────

class HintProgressResponse(BaseModel):
    """현재 사용자의 힌트 허용 단계."""
    problem_id: str
    allowed_level: int  # 1~3

    model_config = {"from_attributes": True}


class HintUnlockRequest(BaseModel):
    """다음 단계 힌트 승급 요청 — 명시적 확인 필요 (FR-18)."""
    confirm: bool = Field(description="'다음 단계 힌트를 여시겠습니까?' 에 대한 명시적 동의")


class HintResponse(BaseModel):
    level: int
    title: str
    content: str
    code_skeleton: Optional[str]
    concept_refs: List[str]

    model_config = {"from_attributes": True}


# ── Community ────────────────────────────────────────────────────────────────

class ShareSolutionRequest(BaseModel):
    submission_id: int = Field(description="공유할 AC 제출 ID")
    title: str = Field(max_length=255)
    description: Optional[str] = None
    is_public: bool = True


class SharedSolutionResponse(BaseModel):
    id: int
    problem_id: str
    user_id: int
    title: str
    description: Optional[str]
    is_public: bool
    likes_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentRequest(BaseModel):
    content: str = Field(min_length=1)


class CommentResponse(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Problem Report (FR-34) ────────────────────────────────────────────────────

class ProblemReportRequest(BaseModel):
    reason: str = Field(min_length=1, description="문제 품질 신고 사유")


class ProblemReportResponse(BaseModel):
    id: int
    problem_id: str
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Submission Review (제출 리뷰) ─────────────────────────────────────────────

class SubmissionReviewRequest(BaseModel):
    """제출 리뷰 요청 — Agent 패키지의 review_submission_package() 호출용."""
    problem_id: str = Field(description="문제 ID")
    problem_title: str = Field(default="", description="문제 제목")
    problem_difficulty: str = Field(default="easy", description="난이도")
    problem_algorithm: List[str] = Field(default_factory=list, description="알고리즘 태그")
    problem_statement: str = Field(default="", description="문제 본문")
    user_code: str = Field(description="사용자 제출 코드")
    language: str = Field(default="python", description="제출 언어")
    result_type: str = Field(default="WA", description="채점 결과 (AC/WA/TLE/RE/MLE/CE)")
    include_concept_context: bool = Field(default=True, description="RAG 개념 컨텍스트 포함 여부")


class SubmissionReviewResponse(BaseModel):
    """제출 리뷰 응답 — review_package_to_dict() 결과를 그대로 반환."""
    problem_id: str
    result_type: str
    summary: str
    safe_to_show: bool
    evaluation_report: Optional[dict] = None
    error_diagnosis: Optional[dict] = None
    failed_case_explanation: Optional[dict] = None
    complexity_analysis: Optional[dict] = None
    counterexample_report: Optional[dict] = None
    feedback_report: Optional[dict] = None
    routing_decision: Optional[dict] = None
    concept_context: List[str] = Field(default_factory=list)
