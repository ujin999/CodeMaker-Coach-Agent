"""Hints 라우터 — 챗봇형 힌트 요청 / 단계 승급 (FR-15~FR-19, NFR-4).

핵심 보안 규칙:
1. 허용 단계 초과 힌트는 서버에서 물리적으로 차단 (검색 자체를 막음).
2. 단계 승급은 명시적 confirm=true 요청을 거쳐야만 한다.
3. 클라이언트가 allowed_level을 임의로 올릴 수 없다.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.db import get_db
from app.gateway import AgentGateway, get_agent_gateway
from app.models.problem import Hint, Problem
from app.models.submission import HintProgress
from app.schemas.domain import HintProgressResponse, HintResponse, HintUnlockRequest

from agent import (
    request_hint_package,
    hint_package_to_dict,
    HintRequestPackageInput,
)

router = APIRouter(prefix="/api/hints", tags=["hints"])


def _dep_gateway() -> AgentGateway:
    return get_agent_gateway()


def _get_or_create_progress(user_id: int, problem_id: str, db: Session) -> HintProgress:
    """힌트 진행 상태를 가져오거나 level=1로 초기화한다."""
    progress = (
        db.query(HintProgress)
        .filter(HintProgress.user_id == user_id, HintProgress.problem_id == problem_id)
        .first()
    )
    if not progress:
        progress = HintProgress(user_id=user_id, problem_id=problem_id, allowed_level=1)
        db.add(progress)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            progress = (
                db.query(HintProgress)
                .filter(HintProgress.user_id == user_id, HintProgress.problem_id == problem_id)
                .first()
            )
    return progress


@router.post("/request", status_code=status.HTTP_200_OK)
async def request_hint(
    body: HintRequestPackageInput,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    gateway: AgentGateway = Depends(_dep_gateway),
) -> dict:
    """챗봇형 힌트 요청 — Agent 패키지의 비동기 request_hint_package() 호출.

    서버 측에서 DB의 allowed_level을 강제 조회하여 body의 allowed_level을 덮어씌운다.
    requested_level이 allowed_level보다 큰 경우 차단(blocked) 응답을 반환한다.
    """
    problem = db.get(Problem, body.problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    progress = _get_or_create_progress(user_id, body.problem_id, db)

    # Enforce allowed_level server-side!
    body.allowed_level = progress.allowed_level

    # 힌트가 이 문제에 하나도 저장되어 있지 않은지 확인 (레벨 무관, 존재 여부만).
    # 실제로 서비스에 넘길 힌트는 아래에서 allowed_level 이하로만 다시 조회한다.
    has_any_hint = db.query(Hint.id).filter(Hint.problem_id == body.problem_id).first() is not None

    if not has_any_hint:
        # 힌트가 없으면 Agent로 생성 후 저장
        from agent.schemas import GeneratedProblem, HintBlueprint
        generated = GeneratedProblem(
            problem_id=problem.id,
            title=problem.title,
            difficulty=problem.difficulty,
            algorithm=problem.algorithm,
            learning_goal=problem.learning_goal,
            statement=problem.statement,
            input_format=problem.input_format,
            output_format=problem.output_format,
            constraints=problem.constraints,
            sample_input=problem.sample_input,
            sample_output=problem.sample_output,
            expected_time_complexity=problem.expected_time_complexity,
            hint_blueprint=HintBlueprint(
                intended_algorithm=problem.algorithm,
                core_insight="",
                common_misconceptions=[],
                edge_case_focus=[],
                forbidden_disclosures=[],
                level_1_guidance="",
                level_2_guidance="",
                level_3_guidance="",
            ),
        )
        hint_bundle = await gateway.generate_hints(generated, allowed_level=3)
        for h in hint_bundle.hints:
            db.add(Hint(
                problem_id=body.problem_id,
                level=h.level,
                title=h.title,
                content=h.content,
                reveals_core_code=False,
                code_skeleton=h.code_skeleton,
                concept_refs=h.concept_refs,
                source=h.source,
            ))
        db.commit()

    # 허용 단계 이하 힌트만 조회한다 — 상위 단계 힌트는 애초에 조회 대상에서
    # 물리적으로 제외하여, 이후 서비스 계층 필터링에만 의존하지 않는다 (FR-18, NFR-4).
    hints = (
        db.query(Hint)
        .filter(Hint.problem_id == body.problem_id, Hint.level <= progress.allowed_level)
        .order_by(Hint.level)
        .all()
    )

    # Convert DB Hint models to agent.schemas.Hint objects
    from agent.schemas import Hint as AgentHint
    agent_hints = [
        AgentHint(
            problem_id=h.problem_id,
            level=h.level,
            title=h.title,
            content=h.content,
            reveals_core_code=h.reveals_core_code,
            code_skeleton=h.code_skeleton,
            concept_refs=h.concept_refs or [],
            source=h.source or "db"
        )
        for h in hints
    ]

    package = await request_hint_package(body, generated_hints=agent_hints)
    return hint_package_to_dict(package)


@router.get("/{problem_id}/progress", response_model=HintProgressResponse)
def get_hint_progress(
    problem_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> HintProgressResponse:
    """현재 사용자의 힌트 허용 단계 조회."""
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")
    progress = _get_or_create_progress(user_id, problem_id, db)
    return HintProgressResponse(problem_id=problem_id, allowed_level=progress.allowed_level)


@router.get("/{problem_id}", response_model=List[HintResponse])
async def get_hints(
    problem_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    gateway: AgentGateway = Depends(_dep_gateway),
) -> List[HintResponse]:
    """허용 단계 이하의 힌트 목록 반환.

    DB에 저장된 힌트를 우선 사용하고, 없으면 Agent로 생성 후 저장한다.
    어떤 경우에도 allowed_level 초과 힌트는 반환하지 않는다 (NFR-4).
    """
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    progress = _get_or_create_progress(user_id, problem_id, db)
    allowed = progress.allowed_level

    # DB에서 허용 단계 이하 힌트만 조회 (물리적 필터 — FR-18)
    hints = (
        db.query(Hint)
        .filter(Hint.problem_id == problem_id, Hint.level <= allowed)
        .order_by(Hint.level)
        .all()
    )

    if not hints:
        # 힌트가 없으면 Agent로 생성 후 저장
        from app.models.problem import Problem as ProblemModel
        from agent.schemas import GeneratedProblem, HintBlueprint, ProblemGenerationInput
        # 최소한의 GeneratedProblem 재구성
        generated = GeneratedProblem(
            problem_id=problem.id,
            title=problem.title,
            difficulty=problem.difficulty,
            algorithm=problem.algorithm,
            learning_goal=problem.learning_goal,
            statement=problem.statement,
            input_format=problem.input_format,
            output_format=problem.output_format,
            constraints=problem.constraints,
            sample_input=problem.sample_input,
            sample_output=problem.sample_output,
            expected_time_complexity=problem.expected_time_complexity,
            hint_blueprint=HintBlueprint(
                intended_algorithm=problem.algorithm,
                core_insight="",
                common_misconceptions=[],
                edge_case_focus=[],
                forbidden_disclosures=[],
                level_1_guidance="",
                level_2_guidance="",
                level_3_guidance="",
            ),
        )
        hint_bundle = await gateway.generate_hints(generated, allowed_level=3)
        for h in hint_bundle.hints:
            db.add(Hint(
                problem_id=problem_id,
                level=h.level,
                title=h.title,
                content=h.content,
                reveals_core_code=False,
                code_skeleton=h.code_skeleton,
                concept_refs=h.concept_refs,
                source=h.source,
            ))
        db.commit()

        hints = (
            db.query(Hint)
            .filter(Hint.problem_id == problem_id, Hint.level <= allowed)
            .order_by(Hint.level)
            .all()
        )

    return [HintResponse.model_validate(h) for h in hints]


@router.post("/{problem_id}/unlock", response_model=HintProgressResponse)
def unlock_next_level(
    problem_id: str,
    body: HintUnlockRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> HintProgressResponse:
    """다음 단계 힌트 승급 — confirm=true 명시 필수 (FR-17, FR-18).

    프론트는 '다음 단계 힌트를 여시겠습니까?' 확인 모달 후 이 API를 호출한다.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="명시적 확인(confirm=true)이 필요합니다.",
        )

    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    progress = _get_or_create_progress(user_id, problem_id, db)
    if progress.allowed_level >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 최고 단계(3단계) 힌트까지 허용되었습니다.",
        )

    progress.allowed_level += 1
    db.commit()
    return HintProgressResponse(problem_id=problem_id, allowed_level=progress.allowed_level)
