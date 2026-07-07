import asyncio
import logging
from typing import Optional, List
from agent.schemas import (
    GeneratedProblem,
    SubmissionResult,
    TestcaseRunResult,
    SubmissionReviewPackage,
    SubmissionEvaluationReport,
    ErrorDiagnosis,
    FailedCaseExplanation,
    ComplexityAnalysis,
    CounterexampleReport,
    FeedbackReport,
    RoutingDecision,
)
from agent.nodes.workflow import run_submission_review_workflow, run_feedback_workflow

logger = logging.getLogger(__name__)


async def review_submission_package(
    problem: GeneratedProblem,
    submission_result: SubmissionResult,
    testcase_results: Optional[List[TestcaseRunResult]] = None,
    include_concept_context: bool = True,
    concept_top_k: int = 3,
) -> SubmissionReviewPackage:
    """
    Async-first package-level submission review API for FastAPI integration.
    Deterministic.
    Does not execute user code.
    Does not call LLM.
    """
    # 1. Execute workflow based on input
    if testcase_results is not None:
        state = await asyncio.to_thread(
            run_submission_review_workflow,
            problem,
            testcase_results,
            submission_result.user_code,
            submission_result.language
        )
    else:
        state = await asyncio.to_thread(
            run_feedback_workflow,
            problem,
            submission_result
        )

    # 2. Extract reports from AgentState
    evaluation_report = state.get("submission_evaluation_report")
    error_diagnosis = state.get("error_diagnosis")
    failed_case_explanation = state.get("failed_case_explanation")
    complexity_analysis = state.get("complexity_analysis")
    counterexample_report = state.get("counterexample_report")
    feedback_report = state.get("feedback_report")
    routing_decision = state.get("routing_decision")

    # 3. Retrieve RAG concepts if requested
    concept_context = []
    if include_concept_context:
        queries = []
        if problem.algorithm:
            queries.extend(problem.algorithm)
        if error_diagnosis and error_diagnosis.related_concepts:
            queries.extend(error_diagnosis.related_concepts)
        if complexity_analysis and complexity_analysis.related_concepts:
            queries.extend(complexity_analysis.related_concepts)

        # Unique query tags
        unique_tags = []
        for tag in queries:
            if tag not in unique_tags:
                unique_tags.append(tag)

        if unique_tags:
            query_str = " ".join(unique_tags)
            try:
                from rag.retriever import search_concepts
                results = await asyncio.to_thread(search_concepts, query_str, concept_top_k)
                concept_context = [f"Source: {c.source_path}\n{c.content}" for c in results]
            except Exception as e:
                logger.warning(f"RAG concept retrieval failed: {e}")
                concept_context = []

    # 4. Determine result type & build concise Korean summary
    res_type = submission_result.result_type
    if evaluation_report:
        res_type = evaluation_report.result_type
    elif feedback_report:
        # Fallback to feedback report or submission_result
        pass

    cause_desc = ""
    if error_diagnosis and error_diagnosis.primary_cause:
        cause_map = {
            "WA_OFF_BY_ONE": "경계 조건 오류",
            "WA_TOO_LOW_BOUND": "결과 범위 하한 오류",
            "WA_TOO_HIGH_BOUND": "결과 범위 상한 오류",
            "WA_WINDOW_UPDATE": "슬라이딩 윈도우 갱신 오류",
            "WA_BFS_DISTANCE_OR_VISITED": "BFS 탐색 조건 오류",
            "WA_DFS_COMPONENT_COUNT": "DFS 방문 조건 오류",
            "PE_OUTPUT_FORMAT": "출력 포맷 오류",
            "TLE_COMPLEXITY": "시간 복잡도 초과 오류",
            "RE_INDEX_ERROR": "인덱스 범위 초과 오류",
            "RE_RECURSION_DEPTH": "재귀 한도 초과 오류",
            "CE_SYNTAX_ERROR": "구문/문법 오류",
        }
        cause_desc = cause_map.get(error_diagnosis.primary_cause, "알고리즘 논리 오류")

    if res_type == "AC":
        summary = "제출 결과는 AC이며, 모든 테스트케이스를 통과했습니다."
    elif cause_desc:
        summary = f"제출 결과는 {res_type}이며, 주요 원인은 {cause_desc}로 추정됩니다. 실패 입력과 반례 설명을 함께 확인해 보세요."
    else:
        summary = f"제출 결과는 {res_type}이며, 실패 입력과 반례 설명을 확인하여 오답을 수정해 보세요."

    # 5. Check safe_to_show aggregation
    safe_to_show = True
    reports = [
        evaluation_report,
        error_diagnosis,
        failed_case_explanation,
        complexity_analysis,
        counterexample_report,
        feedback_report,
        routing_decision,
    ]
    for r in reports:
        if r is not None and hasattr(r, "safe_to_show") and not r.safe_to_show:
            safe_to_show = False
            break

    return SubmissionReviewPackage(
        problem_id=problem.problem_id,
        result_type=res_type,
        evaluation_report=evaluation_report,
        error_diagnosis=error_diagnosis,
        failed_case_explanation=failed_case_explanation,
        complexity_analysis=complexity_analysis,
        counterexample_report=counterexample_report,
        feedback_report=feedback_report,
        routing_decision=routing_decision,
        concept_context=concept_context,
        summary=summary,
        safe_to_show=safe_to_show,
    )


def review_submission_package_sync(
    *args,
    **kwargs,
) -> SubmissionReviewPackage:
    """
    Convenience sync wrapper for CLI/tests.
    Not intended for FastAPI async routes.
    """
    return asyncio.run(review_submission_package(*args, **kwargs))


def review_package_to_dict(review: SubmissionReviewPackage) -> dict:
    """
    Return Pydantic v2 model_dump(mode='json') compatible dict.
    Helps FastAPI response serialization.
    """
    return review.model_dump(mode="json")
