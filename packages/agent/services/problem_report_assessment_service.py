import asyncio
import logging

from agent.schemas import ProblemReportAssessment, ProblemReportAssessmentInput

logger = logging.getLogger(__name__)


async def assess_problem_report_package(
    input_data: ProblemReportAssessmentInput,
) -> ProblemReportAssessment:
    """Async-first package-level API — 신고 누적 문제를 Agent가 재검증한다.

    LLM 호출/파싱이 실패해도 절대 예외를 전파하지 않는다 — 실패 시 항상
    'minor'(=human-in-the-loop로 폴백)로 처리해 오탐으로 인한 자동 삭제/자동
    기각을 막는다.
    """
    from agent.chains.problem_report_assessment import assess_problem_reports

    try:
        return await asyncio.to_thread(assess_problem_reports, input_data)
    except Exception:
        logger.exception(
            "problem report assessment failed for problem_id=%s; falling back to minor",
            input_data.problem_id,
        )
        return ProblemReportAssessment(
            problem_id=input_data.problem_id,
            severity="minor",
            reasoning="Agent 판정 중 오류가 발생해 안전하게 사람 검토로 넘깁니다.",
            confidence="low",
        )


def assessment_to_dict(assessment: ProblemReportAssessment) -> dict:
    return assessment.model_dump(mode="json")
