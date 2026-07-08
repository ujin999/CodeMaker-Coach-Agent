"""Problems 라우터 — 문제 생성·조회 (FR-1~FR-10)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agent.schemas import GeneratedProblem, HintBundle, ReferenceSolution, TestcaseBundle
from app.auth import get_current_user_id
from app.db import get_db
from app.gateway import AgentGateway, get_agent_gateway
from app.models.community import ProblemReport
from app.models.problem import Problem, TestCase, Hint
from app.schemas.domain import (
    FlaggedProblemResponse,
    FlaggedReportSummary,
    ProblemReportRequest,
    ProblemReportResponse,
    ProblemReportStatusResponse,
    ProblemReviewRequest,
    ProblemReviewResponse,
    ProblemSummaryResponse,
    ProblemDetailResponse,
    RevealSolutionRequest,
    RevealSolutionResponse,
)
from app.schemas.problems import ProblemGenerateRequest
from config.settings import settings

router = APIRouter(prefix="/api/problems", tags=["problems"])

# 검증 실패 시 재생성을 허용하는 라우팅 액션 (BUILD_PLAN Step 3.5)
_REGENERATE_ACTIONS = {"regenerate_problem", "regenerate_testcases", "revise_hints"}
_MAX_GENERATION_ATTEMPTS = 3


def _report_count(db: Session, problem_id: str) -> int:
    return db.query(ProblemReport).filter(ProblemReport.problem_id == problem_id).count()


def _dep_gateway() -> AgentGateway:
    return get_agent_gateway()


@router.post("/generate", response_model=ProblemDetailResponse, status_code=status.HTTP_201_CREATED)
async def generate_problem(
    spec: ProblemGenerateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    gateway: AgentGateway = Depends(_dep_gateway),
) -> ProblemDetailResponse:
    """문제 생성 → 테스트케이스 생성 → 힌트 생성 → 검증 → DB 저장.

    Agent의 패키지 워크플로우(RAG 검색 → 생성 → 검증 → 라우팅 결정)를 거치며,
    검증 실패 시 라우팅 결정에 따라 제한된 횟수 내에서 재생성한다 (FR-8, FR-9).
    안전하게 사용자에게 노출할 수 없는 결과는 DB에 저장하지 않는다.
    생성된 힌트는 DB에 저장되며 RAG로 서빙된다 (FR-5).
    """
    import os
    import uuid
    # If seed is not sent by frontend, generate one to ensure diversity (only in non-stub/non-test mode)
    if not spec.seed and os.getenv("AGENT_MODE") != "stub" and os.getenv("ENV") != "test":
        spec.seed = uuid.uuid4().hex

    # ── Neo4j 기반 개인화 약점 주입 (Phase 4) ──
    if spec.focus_weaknesses:
        try:
            from packages.graphrag import get_user_weaknesses
            weak_data = get_user_weaknesses(user_id)
            if weak_data and weak_data.get("weak_concepts"):
                for wc in weak_data["weak_concepts"]:
                    concept = wc["concept"]
                    score = wc["score"]
                    error_info = ""
                    if weak_data.get("top_errors"):
                        error_info = f", main_error: {weak_data['top_errors'][0]['error_type']}"
                    spec.recent_weaknesses.append(f"{concept} (weight: {score}{error_info})")
        except Exception as graph_err:
            import logging
            logging.getLogger(__name__).warning(f"Failed to fetch user weaknesses for problem generation: {graph_err}")

    package = None
    for _ in range(_MAX_GENERATION_ATTEMPTS):
        package = await gateway.generate_problem_package(spec)
        decision = package.routing_decision or {}
        if decision.get("action") == "present_to_user" and decision.get("safe_to_continue", True):
            break
        if decision.get("action") not in _REGENERATE_ACTIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"문제 생성 검증에 실패했습니다: {decision.get('reason', '알 수 없는 이유')}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="검증을 통과하는 문제를 생성하지 못했습니다. 잠시 후 다시 시도해주세요.",
        )

    generated = GeneratedProblem(**package.generated_problem)
    if not package.testcase_bundle:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="테스트케이스 생성에 실패했습니다.",
        )
    tc_bundle = TestcaseBundle(**package.testcase_bundle)
    hint_bundle = HintBundle(**package.hint_bundle) if package.hint_bundle else None
    reference_solution = (
        ReferenceSolution(**package.reference_solution) if package.reference_solution else None
    )

    # DB 저장
    base_id = generated.problem_id
    suffix_counter = 1
    unique_id = base_id
    problem_orm = None
    while db.get(Problem, unique_id):
        existing_prob = db.get(Problem, unique_id)
        if existing_prob.title == generated.title and existing_prob.statement == generated.statement:
            if spec.force_new:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A problem with the same content already exists.",
                )
            else:
                problem_orm = existing_prob
                break
        else:
            unique_id = f"{base_id}_{suffix_counter}"
            suffix_counter += 1

    if problem_orm is None:
        generated.problem_id = unique_id
        if hint_bundle:
            hint_bundle.problem_id = unique_id
            for h in hint_bundle.hints:
                h.problem_id = unique_id
        if tc_bundle:
            tc_bundle.problem_id = unique_id
        if reference_solution:
            reference_solution.problem_id = unique_id

        # difficulty 값 정규화 — LLM이 한국어나 비표준 값을 출력하는 경우 방어
        _DIFFICULTY_MAP = {
            "쉬움": "easy", "쉬운": "easy", "낮음": "easy",
            "중간": "medium", "보통": "medium", "중급": "medium", "중간 정도": "medium",
            "어려움": "hard", "어려운": "hard", "높음": "hard",
        }
        normalized_difficulty = _DIFFICULTY_MAP.get(
            generated.difficulty,
            generated.difficulty if generated.difficulty in {"easy", "medium", "hard"} else "medium"
        )

        problem_orm = Problem(
            id=unique_id,
            title=generated.title,
            difficulty=normalized_difficulty,
            algorithm=generated.algorithm,
            learning_goal=generated.learning_goal,
            statement=generated.statement,
            input_format=generated.input_format,
            output_format=generated.output_format,
            constraints=generated.constraints,
            sample_input=generated.sample_input,
            sample_output=generated.sample_output,
            expected_time_complexity=generated.expected_time_complexity,
            reference_solution=reference_solution.code if reference_solution else None,
            created_by=user_id,
        )
        db.add(problem_orm)
        db.flush()  # problem_id FK 확보

        # TestCase 저장
        for tc in tc_bundle.testcases:
            db.add(TestCase(
                problem_id=unique_id,
                type=tc.visibility,
                input=tc.input_data,
                expected_output=tc.expected_output,
                purpose=tc.purpose,
            ))

        # Hint 저장 (reveals_core_code 항상 False 강제 — FR-19)
        for h in (hint_bundle.hints if hint_bundle else []):
            db.add(Hint(
                problem_id=unique_id,
                level=h.level,
                title=h.title,
                content=h.content,
                reveals_core_code=False,  # DB 레벨 강제
                code_skeleton=h.code_skeleton,
                concept_refs=h.concept_refs,
                source=h.source,
            ))

        db.commit()
        db.refresh(problem_orm)

    # Convert problem_orm to dict and add extra fields, then validate:
    prob_dict = {c.name: getattr(problem_orm, c.name) for c in problem_orm.__table__.columns}
    prob_dict["seed"] = package.seed if hasattr(package, "seed") else None
    prob_dict["generation_mode"] = package.generation_mode if hasattr(package, "generation_mode") else None
    prob_dict["variant_id"] = package.variant_id if hasattr(package, "variant_id") else None

    # Fetch creator display name or email
    from app.models.user import User
    creator = db.get(User, user_id)
    prob_dict["created_by_name"] = (creator.display_name or creator.email) if creator else "알 수 없음"

    return ProblemDetailResponse.model_validate(prob_dict)


@router.get("", response_model=List[ProblemSummaryResponse])
def list_problems(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    mine: bool = False,
    algorithm: Optional[str] = Query(default=None, description="알고리즘 분류 필터 (예: bfs, binary_search)"),
    difficulty: Optional[str] = Query(default=None, description="난이도 필터 (easy, medium, hard)"),
    q: Optional[str] = Query(default=None, description="제목 및 문제 본문 검색어"),
    sort: Optional[str] = Query(default="recent", pattern="^(recent|difficulty)$"),
) -> List[ProblemSummaryResponse]:
    """전체 또는 내가 만든 문제 목록 조회 — 알고리즘/난이도/검색어 필터 및 정렬 지원."""
    from sqlalchemy import any_

    query = db.query(Problem)

    # mine 필터 — 본인 문제는 신고/검토 상태와 무관하게 전부 보여준다.
    # 공개 카탈로그(mine=false)는 active 상태만 노출한다 (신고 누적으로 under_review/removed된 문제는 숨김).
    if mine:
        query = query.filter(Problem.created_by == user_id)
    else:
        query = query.filter(Problem.status == "active")

    # 알고리즘 필터 — algorithm 컬럼은 ARRAY(String)
    if algorithm:
        query = query.filter(algorithm == any_(Problem.algorithm))

    # 난이도 필터
    if difficulty:
        query = query.filter(Problem.difficulty == difficulty)

    # 검색어 필터 — 제목 또는 본문(ilike: case-insensitive)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            Problem.title.ilike(pattern) | Problem.statement.ilike(pattern)
        )

    # 정렬
    if sort == "difficulty":
        from sqlalchemy import case
        difficulty_order = case(
            (Problem.difficulty == "easy", 1),
            (Problem.difficulty == "medium", 2),
            (Problem.difficulty == "hard", 3),
            else_=4,
        )
        query = query.order_by(difficulty_order, Problem.created_at.desc())
    else:
        query = query.order_by(Problem.created_at.desc())

    problems = query.offset(skip).limit(limit).all()

    # Bulk query user names to avoid N+1 query problem
    creator_ids = {p.created_by for p in problems if p.created_by is not None}
    user_names = {}
    if creator_ids:
        from app.models.user import User
        users = db.query(User).filter(User.id.in_(creator_ids)).all()
        user_names = {u.id: u.display_name or u.email for u in users}

    res = []
    for p in problems:
        summary = ProblemSummaryResponse.model_validate(p)
        summary.created_by_name = user_names.get(p.created_by, "알 수 없음")
        res.append(summary)
    return res


@router.get("/flagged", response_model=List[FlaggedProblemResponse])
def list_flagged_problems(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> List[FlaggedProblemResponse]:
    """검토 대기(under_review) 문제 목록 — 신고 사유 포함 (FR-34).

    별도 관리자 계정 없이 로그인한 모든 사용자가 문제 관리(HITL 검토)에
    참여할 수 있다.
    """
    problems = (
        db.query(Problem)
        .filter(Problem.status == "under_review")
        .order_by(Problem.created_at.desc())
        .all()
    )

    result: List[FlaggedProblemResponse] = []
    for p in problems:
        reports = (
            db.query(ProblemReport)
            .filter(ProblemReport.problem_id == p.id)
            .order_by(ProblemReport.created_at.desc())
            .all()
        )
        result.append(
            FlaggedProblemResponse(
                id=p.id,
                title=p.title,
                difficulty=p.difficulty,
                algorithm=p.algorithm,
                statement=p.statement,
                status=p.status,
                report_count=len(reports),
                reports=[FlaggedReportSummary.model_validate(r) for r in reports],
                created_at=p.created_at,
            )
        )
    return result


@router.get("/{problem_id}", response_model=ProblemDetailResponse)
def get_problem(
    problem_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProblemDetailResponse:
    """문제 상세 조회 (reference_solution 미포함)."""
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")
    
    detail = ProblemDetailResponse.model_validate(problem)
    if problem.created_by is not None:
        from app.models.user import User
        creator = db.get(User, problem.created_by)
        if creator:
            detail.created_by_name = creator.display_name or creator.email
        else:
            detail.created_by_name = "알 수 없음"
    else:
        detail.created_by_name = "알 수 없음"
    return detail


@router.post("/{problem_id}/reveal-solution", response_model=RevealSolutionResponse)
def reveal_solution(
    problem_id: str,
    body: RevealSolutionRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> RevealSolutionResponse:
    """정답 코드 열람 — 명시적 확인(confirm=true) 후에만 공개한다 (FR-20, 정책 1).

    힌트 채널과 완전히 분리된 별도 엔드포인트이며, 힌트 응답에는 절대 포함되지 않는다.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="명시적 확인(confirm=true)이 필요합니다.",
        )

    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    if not problem.reference_solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="이 문제는 아직 정답 코드가 준비되지 않았습니다.",
        )

    return RevealSolutionResponse(
        problem_id=problem.id,
        language="python",
        code=problem.reference_solution,
    )


@router.post(
    "/{problem_id}/report",
    response_model=ProblemReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def report_problem(
    problem_id: str,
    body: ProblemReportRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    gateway: AgentGateway = Depends(_dep_gateway),
) -> ProblemReportResponse:
    """품질 낮은 생성 문제 신고 (FR-34).

    한 사용자는 같은 문제를 한 번만 신고할 수 있다 (중복 신고는 409). 누적 신고 수가
    settings.problem_report_threshold 이상이 되면, human-in-the-loop로 가기 전에
    Agent가 먼저 문제와 신고 사유를 재검증한다 (신고누적흐름.txt 참조):

    - severity=critical (치명적 결함 명확) -> 사람 검토 없이 즉시 삭제(removed)
    - severity=safe (오신고로 판단)        -> 사람 검토 없이 신고 초기화 후 active 유지
    - severity=minor (애매함/판단 근거 불충분) -> 기존대로 under_review로 전환해 사람 검토 대기

    Agent 판정이 실패하면 항상 minor로 폴백한다 (안전한 기본값).
    """
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    report = ProblemReport(user_id=user_id, problem_id=problem_id, reason=body.reason)
    db.add(report)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 이 문제를 신고했습니다. 신고를 취소하려면 DELETE로 요청하세요.",
        )
    db.refresh(report)

    count = _report_count(db, problem_id)
    if count >= settings.problem_report_threshold and problem.status == "active":
        reasons = [
            r.reason
            for r in db.query(ProblemReport).filter(ProblemReport.problem_id == problem_id).all()
        ]
        assessment = await gateway.assess_problem_report(
            problem_id=problem_id,
            title=problem.title,
            statement=problem.statement,
            constraints=problem.constraints,
            sample_input=problem.sample_input,
            sample_output=problem.sample_output,
            report_reasons=reasons,
        )
        severity = assessment.get("severity", "minor")

        if severity == "critical":
            # Agent가 치명적 결함을 명확히 판단 — human-in-the-loop 없이 즉시 삭제.
            problem.status = "removed"
        elif severity == "safe":
            # Agent가 오신고로 판단 — human-in-the-loop 없이 즉시 기각(신고 초기화).
            db.query(ProblemReport).filter(ProblemReport.problem_id == problem_id).delete()
            problem.status = "active"
        else:
            # minor 또는 알 수 없는 값 — 기존대로 사람 검토 대기.
            problem.status = "under_review"
        db.commit()
        count = _report_count(db, problem_id)  # safe 분기에서 초기화됐을 수 있으므로 재계산

    return ProblemReportResponse(
        id=report.id,
        problem_id=report.problem_id,
        reason=report.reason,
        created_at=report.created_at,
        report_count=count,
        status=problem.status,
    )


@router.delete("/{problem_id}/report", status_code=status.HTTP_204_NO_CONTENT)
def cancel_report(
    problem_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    """내 신고 취소 (FR-34). 이미 under_review로 넘어간 검토 대기열에서는 자동으로
    빠지지 않는다 — 관리자가 검토를 시작한 뒤에는 사람이 명시적으로 처리해야 한다."""
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    report = (
        db.query(ProblemReport)
        .filter(ProblemReport.problem_id == problem_id, ProblemReport.user_id == user_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="신고 내역을 찾을 수 없습니다.")

    db.delete(report)
    db.commit()


@router.get("/{problem_id}/report", response_model=ProblemReportStatusResponse)
def get_report_status(
    problem_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProblemReportStatusResponse:
    """신고/취소 토글 UI용 — 누적 신고 수와 내 신고 여부를 조회한다."""
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    reported_by_me = (
        db.query(ProblemReport)
        .filter(ProblemReport.problem_id == problem_id, ProblemReport.user_id == user_id)
        .first()
        is not None
    )
    return ProblemReportStatusResponse(
        problem_id=problem_id,
        report_count=_report_count(db, problem_id),
        reported_by_me=reported_by_me,
        status=problem.status,
    )


@router.post("/{problem_id}/review", response_model=ProblemReviewResponse)
def review_flagged_problem(
    problem_id: str,
    body: ProblemReviewRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProblemReviewResponse:
    """문제 관리(HITL) 조치 — 로그인한 모든 사용자가 이용할 수 있다 (별도 관리자 계정 없음).

    - dismiss: 신고가 근거 없다고 판단 — 기존 신고 기록을 지우고 active로 복구한다.
    - remove: 문제를 소프트 삭제한다(상태만 변경). 신고 기록은 감사 목적으로 남긴다.
      실제 DELETE를 하지 않는 이유: Submission/SharedSolution 등 관련 레코드가
      ondelete=CASCADE라서, 하드 삭제하면 사용자들의 기존 제출/학습 이력까지
      같이 사라진다.
    - edit: 지적된 필드를 수정한 뒤 신고 기록을 지우고 active로 복구한다(내용이
      바뀌었으므로 기존 신고는 더 이상 유효하지 않다고 본다).
    """
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    if body.action == "remove":
        problem.status = "removed"
    else:
        if body.action == "edit":
            if body.title is not None:
                problem.title = body.title
            if body.statement is not None:
                problem.statement = body.statement
            if body.difficulty is not None:
                problem.difficulty = body.difficulty
            if body.constraints is not None:
                problem.constraints = body.constraints
            if body.sample_input is not None:
                problem.sample_input = body.sample_input
            if body.sample_output is not None:
                problem.sample_output = body.sample_output

        # dismiss/edit 모두 조치가 끝났으므로 기존 신고를 지우고 복구한다.
        db.query(ProblemReport).filter(ProblemReport.problem_id == problem_id).delete()
        problem.status = "active"

    db.commit()

    return ProblemReviewResponse(
        id=problem.id,
        status=problem.status,
        report_count=_report_count(db, problem_id),
    )
