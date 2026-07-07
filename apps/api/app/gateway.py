"""AgentGateway — AI 경계 어댑터.

서버(API)는 AI(`agent.chains`)를 직접 호출하지 않고 이 게이트웨이에만 의존한다.
- LiveAgentGateway: 실제 AI 함수를 async로 감싸 호출 (동기 chain → 스레드풀)
- StubAgentGateway: AI/인프라 없이 가짜 응답 (로컬 개발·테스트·미구현 대체)

AGENT_MODE 환경변수: "stub" | "live" | "auto"(기본). auto는 LLM 키 유무로 자동 판단.

⚠️ 미연결 지점(연결되면 알림 대상):
  - analyze_feedback: AI 측에 generate_feedback chain이 아직 없어 stub 반환.
    (agent/prompts/feedback.py 프롬프트만 존재) → AI 팀에 chain 추가 요청 필요.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from agent.schemas import (
    GeneratedProblem,
    GeneratedTestcase,
    Hint,
    HintBlueprint,
    HintBundle,
    ProblemGenerationInput,
    TestcaseBundle,
)

logger = logging.getLogger(__name__)


class Feedback(BaseModel):
    """오답 분석 결과 DTO.

    AI 측에 아직 함수/스키마가 없어 앱에서 임시 정의한다. (stub)
    AI 팀이 generate_feedback 을 추가하면 그 스키마로 대체 예정.
    """

    status_analysis: str
    error_type: str
    related_concepts: list[str] = Field(default_factory=list)
    next_action: str
    show_solution: bool = False


@runtime_checkable
class AgentGateway(Protocol):
    """서버가 의존하는 유일한 AI 인터페이스."""

    async def generate_problem(self, spec: ProblemGenerationInput) -> GeneratedProblem: ...

    async def generate_testcases(
        self, problem: GeneratedProblem, min_cases: int = 5
    ) -> TestcaseBundle: ...

    async def generate_hints(
        self,
        problem: GeneratedProblem,
        allowed_level: int = 3,
        user_situation: Optional[str] = None,
    ) -> HintBundle: ...

    async def search_hints(
        self, problem_id: str, query: str, allowed_level: int, top_k: int = 3
    ) -> list[dict]: ...

    async def analyze_feedback(
        self, *, problem_id: str, result_type: str, user_code: str, allowed_level: int
    ) -> Feedback: ...


class LiveAgentGateway:
    """실제 AI(`agent.chains`, `rag`)를 호출하는 어댑터.

    chain 함수들이 동기(blocking)라서 asyncio.to_thread 로 스레드풀에서 실행,
    FastAPI 이벤트 루프를 막지 않는다.
    """

    async def generate_problem(self, spec: ProblemGenerationInput) -> GeneratedProblem:
        from agent.chains import generate_problem

        return await asyncio.to_thread(generate_problem, spec)

    async def generate_testcases(
        self, problem: GeneratedProblem, min_cases: int = 5
    ) -> TestcaseBundle:
        from agent.chains import generate_testcases

        return await asyncio.to_thread(generate_testcases, problem, min_cases)

    async def generate_hints(
        self,
        problem: GeneratedProblem,
        allowed_level: int = 3,
        user_situation: Optional[str] = None,
    ) -> HintBundle:
        from agent.chains import generate_hints

        return await asyncio.to_thread(
            generate_hints, problem, allowed_level, user_situation
        )

    async def search_hints(
        self, problem_id: str, query: str, allowed_level: int, top_k: int = 3
    ) -> list[dict]:
        from rag.hint_retriever import search_hints

        docs = await asyncio.to_thread(
            search_hints, problem_id, query, allowed_level, top_k
        )
        return [
            {"level": d.metadata.get("hint_level"), "content": d.page_content}
            for d in docs
        ]

    async def analyze_feedback(
        self, *, problem_id: str, result_type: str, user_code: str, allowed_level: int
    ) -> Feedback:
        # ⚠️ AI 측에 generate_feedback chain 미구현 → stub 반환.
        logger.warning(
            "analyze_feedback: AI generate_feedback 미구현 → stub 반환 "
            "(problem_id=%s, result_type=%s)",
            problem_id,
            result_type,
        )
        return _stub_feedback(result_type)


class StubAgentGateway:
    """AI/인프라 없이 동작하는 가짜 게이트웨이. 로컬 개발·테스트·CI용."""

    async def generate_problem(self, spec: ProblemGenerationInput) -> GeneratedProblem:
        algo = spec.algorithm
        return GeneratedProblem(
            problem_id=f"stub-{algo}-001",
            title=f"[STUB] {algo} 연습 문제",
            difficulty=spec.difficulty,
            algorithm=[algo],
            learning_goal=spec.learning_goal or "기본 로직 이해",
            statement="정수 배열에서 두 수의 합이 target이 되는 두 인덱스를 찾으시오. (STUB)",
            input_format="첫 줄에 N과 target, 둘째 줄에 N개의 정수",
            output_format="두 인덱스(오름차순), 없으면 -1",
            constraints=["1 <= N <= 100000", "|a_i| <= 10^9"],
            sample_input="4 9\n2 7 11 15",
            sample_output="0 1",
            expected_time_complexity="O(N)",
            hint_blueprint=_stub_blueprint([algo]),
        )

    async def generate_testcases(
        self, problem: GeneratedProblem, min_cases: int = 5
    ) -> TestcaseBundle:
        cases = [
            GeneratedTestcase(
                name="sample-1",
                input_data="4 9\n2 7 11 15",
                expected_output="0 1",
                visibility="sample",
                purpose="기본 동작 확인 (STUB)",
            ),
            GeneratedTestcase(
                name="hidden-1",
                input_data="3 6\n3 2 4",
                expected_output="1 2",
                visibility="hidden",
                purpose="중복 없는 일반 케이스 (STUB)",
            ),
            GeneratedTestcase(
                name="edge-1",
                input_data="2 3\n1 2",
                expected_output="0 1",
                visibility="edge",
                purpose="최소 입력 경계 (STUB)",
            ),
        ]
        return TestcaseBundle(
            problem_id=problem.problem_id,
            testcases=cases,
            generation_notes="STUB testcases",
        )

    async def generate_hints(
        self,
        problem: GeneratedProblem,
        allowed_level: int = 3,
        user_situation: Optional[str] = None,
    ) -> HintBundle:
        all_hints = [
            Hint(
                problem_id=problem.problem_id,
                level=1,
                title="방향 힌트",
                content="모든 쌍을 비교하지 않고 필요한 값을 빠르게 찾는 방법을 생각해보세요. (STUB)",
            ),
            Hint(
                problem_id=problem.problem_id,
                level=2,
                title="알고리즘 힌트",
                content="지금까지 본 값을 해시맵에 저장하면 target - x 를 빠르게 찾을 수 있습니다. (STUB)",
            ),
            Hint(
                problem_id=problem.problem_id,
                level=3,
                title="구현 힌트",
                content="아래 뼈대의 빈칸을 채워 완성하세요. (STUB)",
                code_skeleton=(
                    "seen = {}\n"
                    "for i, x in enumerate(nums):\n"
                    "    # 구현: target - x 를 seen 에서 찾고, 있으면 인덱스 출력 (...)\n"
                    "    seen[x] = i"
                ),
            ),
        ]
        hints = [h for h in all_hints if h.level <= allowed_level]
        return HintBundle(
            problem_id=problem.problem_id,
            blueprint=_stub_blueprint(problem.algorithm),
            hints=hints,
        )

    async def search_hints(
        self, problem_id: str, query: str, allowed_level: int, top_k: int = 3
    ) -> list[dict]:
        canned = {
            1: "모든 쌍을 비교하지 않는 방법을 생각해보세요. (STUB)",
            2: "해시맵으로 target - x 를 O(1)에 찾으세요. (STUB)",
            3: "seen 딕셔너리를 채워 완성하세요. (STUB)",
        }
        return [
            {"level": lvl, "content": content}
            for lvl, content in canned.items()
            if lvl <= allowed_level
        ][:top_k]

    async def analyze_feedback(
        self, *, problem_id: str, result_type: str, user_code: str, allowed_level: int
    ) -> Feedback:
        return _stub_feedback(result_type)


def _stub_blueprint(algorithms: list[str]) -> HintBlueprint:
    return HintBlueprint(
        intended_algorithm=algorithms or ["hash"],
        core_insight="필요한 값을 자료구조로 빠르게 조회한다. (STUB)",
        common_misconceptions=["이중 for문으로 O(N^2) 작성"],
        edge_case_focus=["중복 원소", "정답 없음"],
        forbidden_disclosures=["완성된 정답 코드"],
        level_1_guidance="완전 탐색 말고 더 빠른 방법을 떠올려보세요.",
        level_2_guidance="해시맵에 본 값을 저장하는 접근을 생각해보세요.",
        level_3_guidance="반복문 안에서 보수(target-x) 존재 여부를 확인하세요.",
        allowed_code_exposure="skeleton_only",
    )


def _stub_feedback(result_type: str) -> Feedback:
    table = {
        "TLE": ("시간 초과 가능성이 높습니다. 복잡도를 줄여보세요. (STUB)", "time_complexity", ["hash", "two_pointer"]),
        "WA": ("일부 케이스에서 틀립니다. 경계값을 확인하세요. (STUB)", "wrong_answer", ["off_by_one"]),
        "RE": ("런타임 에러입니다. 인덱스 범위를 확인하세요. (STUB)", "runtime_error", ["index_error"]),
    }
    analysis, err, concepts = table.get(
        result_type, ("제출을 분석했습니다. (STUB)", "unknown", [])
    )
    return Feedback(
        status_analysis=analysis,
        error_type=err,
        related_concepts=concepts,
        next_action="입력 크기 기준으로 가능한 시간복잡도를 먼저 계산해보세요. (STUB)",
    )


def get_agent_gateway() -> AgentGateway:
    """AGENT_MODE 에 따라 게이트웨이 구현을 선택한다."""
    mode = os.getenv("AGENT_MODE", "auto").lower()
    if mode == "stub":
        return StubAgentGateway()
    if mode == "live":
        return LiveAgentGateway()
    # auto: LLM 키가 있으면 live, 없으면 stub
    try:
        from config.settings import settings

        has_key = bool(settings.openai_api_key or settings.anthropic_api_key)
    except Exception:
        has_key = False
    return LiveAgentGateway() if has_key else StubAgentGateway()
