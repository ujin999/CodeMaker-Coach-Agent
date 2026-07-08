"""Problems 라우터 — 문제 생성·조회 (FR-1~FR-10)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from agent.schemas import GeneratedProblem, HintBundle, ReferenceSolution, TestcaseBundle
from app.auth import get_current_user_id
from app.db import get_db
from app.gateway import AgentGateway, get_agent_gateway
from app.models.community import ProblemReport
from app.models.problem import Problem, TestCase, Hint
from app.schemas.domain import (
    ProblemReportRequest,
    ProblemReportResponse,
    ProblemSummaryResponse,
    ProblemDetailResponse,
    RevealSolutionRequest,
    RevealSolutionResponse,
)
from app.schemas.problems import ProblemGenerateRequest

router = APIRouter(prefix="/api/problems", tags=["problems"])

# 검증 실패 시 재생성을 허용하는 라우팅 액션 (BUILD_PLAN Step 3.5)
_REGENERATE_ACTIONS = {"regenerate_problem", "regenerate_testcases", "revise_hints"}
_MAX_GENERATION_ATTEMPTS = 3


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

        problem_orm = Problem(
            id=unique_id,
            title=generated.title,
            difficulty=generated.difficulty,
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
    limit: int = 20,
    mine: bool = False,
) -> List[ProblemSummaryResponse]:
    """전체 또는 내가 만든 문제 목록 조회."""
    query = db.query(Problem)
    if mine:
        query = query.filter(Problem.created_by == user_id)
        
    problems = (
        query
        .order_by(Problem.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
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
def report_problem(
    problem_id: str,
    body: ProblemReportRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProblemReportResponse:
    """품질 낮은 생성 문제 신고 (FR-34)."""
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    report = ProblemReport(user_id=user_id, problem_id=problem_id, reason=body.reason)
    db.add(report)
    db.commit()
    db.refresh(report)
    return ProblemReportResponse.model_validate(report)
