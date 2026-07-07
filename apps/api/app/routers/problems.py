"""Problems 라우터 — 문제 생성·조회 (FR-1~FR-10)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from agent.schemas import GeneratedProblem, HintBundle, TestcaseBundle
from app.auth import get_current_user_id
from app.db import get_db
from app.gateway import AgentGateway, get_agent_gateway
from app.models.problem import Problem, TestCase, Hint
from app.schemas.domain import ProblemSummaryResponse, ProblemDetailResponse
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

    # DB 저장
    if db.get(Problem, generated.problem_id):
        # 동일 ID가 이미 있으면 재생성된 결과를 덮어쓰지 않고 그냥 반환
        problem_orm = db.get(Problem, generated.problem_id)
    else:
        problem_orm = Problem(
            id=generated.problem_id,
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
            created_by=user_id,
        )
        db.add(problem_orm)
        db.flush()  # problem_id FK 확보

        # TestCase 저장
        for tc in tc_bundle.testcases:
            db.add(TestCase(
                problem_id=generated.problem_id,
                type=tc.visibility,
                input=tc.input_data,
                expected_output=tc.expected_output,
                purpose=tc.purpose,
            ))

        # Hint 저장 (reveals_core_code 항상 False 강제 — FR-19)
        for h in (hint_bundle.hints if hint_bundle else []):
            db.add(Hint(
                problem_id=generated.problem_id,
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

    return ProblemDetailResponse.model_validate(problem_orm)


@router.get("", response_model=List[ProblemSummaryResponse])
def list_problems(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
) -> List[ProblemSummaryResponse]:
    """내가 만든 문제 목록 조회."""
    problems = (
        db.query(Problem)
        .filter(Problem.created_by == user_id)
        .order_by(Problem.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [ProblemSummaryResponse.model_validate(p) for p in problems]


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
    return ProblemDetailResponse.model_validate(problem)
