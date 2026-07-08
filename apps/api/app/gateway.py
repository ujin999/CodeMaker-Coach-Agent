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
from app.schemas.problems import ProblemGenerateRequest, ProblemGenerateResponse

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

    async def generate_problem_package(
        self,
        request: ProblemGenerateRequest,
    ) -> ProblemGenerateResponse: ...

    async def assess_problem_report(
        self,
        *,
        problem_id: str,
        title: str,
        statement: str,
        constraints: list[str],
        sample_input: Optional[str],
        sample_output: Optional[str],
        report_reasons: list[str],
    ) -> dict: ...


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

    async def generate_problem_package(
        self,
        request: ProblemGenerateRequest,
    ) -> ProblemGenerateResponse:
        from agent import generate_problem_package, ProblemGenerationPackageInput

        pkg_input = ProblemGenerationPackageInput(
            algorithm=request.algorithm,
            difficulty=request.difficulty,
            problem_style=request.problem_style,
            language=request.language,
            learning_goal=request.learning_goal,
            user_level=request.user_level,
            recent_weaknesses=request.recent_weaknesses,
            min_cases=request.min_cases,
            allowed_hint_level=request.allowed_hint_level,
            include_hints=request.include_hints,
            seed=request.seed,
            avoid_problem_ids=request.avoid_problem_ids,
            force_new=request.force_new
        )

        package = await generate_problem_package(pkg_input)

        prob_dict = package.generated_problem.model_dump() if package.generated_problem else {}
        tc_dict = package.testcase_bundle.model_dump() if package.testcase_bundle else None
        hint_dict = package.hint_bundle.model_dump() if package.hint_bundle else None
        ref_dict = package.reference_solution.model_dump() if package.reference_solution else None
        rep_dict = package.validation_report.model_dump() if package.validation_report else None

        routing_decision = {
            "action": "present_to_user" if package.safe_to_show else "regenerate_problem",
            "reason": package.summary,
            "confidence": "high",
            "blocking_issue_codes": [],
            "safe_to_continue": package.safe_to_show
        }

        return ProblemGenerateResponse(
            generated_problem=prob_dict,
            testcase_bundle=tc_dict,
            hint_bundle=hint_dict,
            reference_solution=ref_dict,
            validation_report=rep_dict,
            routing_decision=routing_decision,
            gateway_mode="live",
            generation_mode=package.generation_mode,
            seed=package.seed,
            variant_id=package.variant_id
        )

    async def assess_problem_report(
        self,
        *,
        problem_id: str,
        title: str,
        statement: str,
        constraints: list[str],
        sample_input: Optional[str],
        sample_output: Optional[str],
        report_reasons: list[str],
    ) -> dict:
        """신고 누적 문제 재검증 — human-in-the-loop 이전 Agent 판정 단계.

        LLM 실패는 assess_problem_report_package 내부에서 이미 'minor'로
        폴백되므로 여기서는 추가 예외 처리를 하지 않는다.
        """
        from agent import assess_problem_report_package, assessment_to_dict
        from agent.schemas import ProblemReportAssessmentInput

        assessment = await assess_problem_report_package(
            ProblemReportAssessmentInput(
                problem_id=problem_id,
                title=title,
                statement=statement,
                constraints=constraints,
                sample_input=sample_input,
                sample_output=sample_output,
                report_reasons=report_reasons,
            )
        )
        return assessment_to_dict(assessment)


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

    async def generate_problem_package(
        self,
        request: ProblemGenerateRequest,
    ) -> ProblemGenerateResponse:
        algo = request.algorithm
        p_id = f"stub-{algo}-001"
        if request.seed:
            clean_seed = "".join(c for c in request.seed if c.isalnum() or c == "_")[:8]
            p_id = f"stub-{algo}_{clean_seed}-001"

        from agent.variants import select_variant
        variant = select_variant(algo, request.seed)

        title = f"[STUB] {algo} 연습 문제"
        if request.seed:
            title += f" (Seed: {request.seed})"
        statement = f"정수 배열에서 두 수의 합이 target이 되는 두 인덱스를 찾으시오. (STUB) Seed: {request.seed or 'none'}"
        input_format = "첫 줄에 N과 target, 둘째 줄에 N개의 정수"
        output_format = "두 인덱스(오름차순), 없으면 -1"
        constraints = ["1 <= N <= 100000", "|a_i| <= 10^9"]
        sample_input = "4 9\n2 7 11 15"
        sample_output = "0 1"

        if variant:
            tmpl = variant["stub_template"]
            title = tmpl["title"]
            if request.seed:
                title += f" (Seed: {request.seed})"
            statement = tmpl["statement"]
            input_format = tmpl["input_format"]
            output_format = tmpl["output_format"]
            constraints = tmpl["constraints"]
            sample_input = tmpl.get("sample_input")
            sample_output = tmpl.get("sample_output")

        generated_problem = {
            "problem_id": p_id,
            "title": title,
            "difficulty": request.difficulty,
            "algorithm": [algo],
            "learning_goal": request.learning_goal or "기본 로직 이해",
            "statement": statement,
            "input_format": input_format,
            "output_format": output_format,
            "constraints": constraints,
            "sample_input": sample_input,
            "sample_output": sample_output,
            "expected_time_complexity": "O(N)",
            "hint_blueprint": {
                "intended_algorithm": [algo],
                "core_insight": "필요한 값을 자료구조로 빠르게 조회한다.",
                "common_misconceptions": ["이중 for문으로 O(N^2) 작성"],
                "edge_case_focus": ["중복 원소", "정답 없음"],
                "forbidden_disclosures": ["완성된 정답 코드"],
                "level_1_guidance": "완전 탐색 말고 더 빠른 방법을 떠올려보세요.",
                "level_2_guidance": "해시맵에 본 값을 저장하는 접근을 생각해보세요.",
                "level_3_guidance": "반복문 안에서 보수(target-x) 존재 여부를 확인하세요.",
                "allowed_code_exposure": "skeleton_only"
            }
        }
        testcase_bundle = {
            "problem_id": p_id,
            "testcases": [
                {
                    "name": "sample-1",
                    "input_data": sample_input or "4 9\n2 7 11 15",
                    "expected_output": sample_output or "0 1",
                    "visibility": "sample",
                    "purpose": "기본 동작 확인 (STUB)",
                    "calculation_steps": "기본 케이스 검증 단계"
                }
            ],
            "generation_notes": "STUB testcases",
            "generation_mode": "deterministic",
            "generator_name": "stub_generator",
            "verification_status": "passed"
        }
        reference_solution = {
            "problem_id": p_id,
            "language": "python",
            "code": "# STUB reference solution\nprint(0, 1)",
            "generator_name": "stub_generator",
            "verified": True,
            "verification_notes": "STUB: 검증 생략",
        }
        validation_report = {
            "passed": True,
            "issues": [],
            "checked_sections": ["problem", "testcases"],
            "summary": "검증을 통과했습니다."
        }
        routing_decision = {
            "action": "present_to_user",
            "reason": "모든 검증을 통과했습니다.",
            "confidence": "high",
            "blocking_issue_codes": [],
            "safe_to_continue": True
        }
        return ProblemGenerateResponse(
            generated_problem=generated_problem,
            testcase_bundle=testcase_bundle,
            hint_bundle=None,
            reference_solution=reference_solution,
            validation_report=validation_report,
            routing_decision=routing_decision,
            gateway_mode="stub",
            generation_mode="template_fallback",
            seed=request.seed,
            variant_id=variant["variant_id"] if variant else (f"var_{request.seed}" if request.seed else None)
        )

    async def assess_problem_report(
        self,
        *,
        problem_id: str,
        title: str,
        statement: str,
        constraints: list[str],
        sample_input: Optional[str],
        sample_output: Optional[str],
        report_reasons: list[str],
    ) -> dict:
        # 항상 human-in-the-loop로 라우팅한다 — 실제 LLM 판정을 흉내내지 않는다.
        return {
            "problem_id": problem_id,
            "severity": "minor",
            "reasoning": "STUB: 항상 human-in-the-loop로 라우팅합니다.",
            "confidence": "low",
        }


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
