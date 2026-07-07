import asyncio
import logging
from typing import Optional
from agent.schemas import (
    ProblemGenerationInput,
    ProblemGenerationPackageInput,
    ProblemGenerationPackage,
    GeneratedProblem,
    TestcaseBundle,
    ReferenceSolution,
    ValidationReport,
    HintBundle,
)
from agent.nodes.workflow import run_package_workflow

logger = logging.getLogger(__name__)


async def generate_problem_package(
    input_data: ProblemGenerationPackageInput,
) -> ProblemGenerationPackage:
    """
    Async-first package-level problem generation API for FastAPI.
    It orchestrates problem generation, testcase generation, reference solution generation/verification,
    validation, optional hint generation, and optional concept context.
    """
    # 1. Convert to existing ProblemGenerationInput
    generation_input = ProblemGenerationInput(
        algorithm=input_data.algorithm,
        difficulty=input_data.difficulty,
        problem_style=input_data.problem_style,
        language=input_data.language,
        learning_goal=input_data.learning_goal,
        user_level=input_data.user_level,
        recent_weaknesses=input_data.recent_weaknesses
    )

    state = {}
    attempts = input_data.max_validation_attempts
    
    # 2. Retry loop for validation
    for attempt in range(1, attempts + 1):
        state = await asyncio.to_thread(
            run_package_workflow,
            generation_input,
            include_hints=input_data.include_hints
        )
        
        val_report = state.get("validation_report")
        if val_report and val_report.passed:
            logger.info(f"Problem generation validation passed on attempt {attempt}.")
            break
        else:
            logger.warning(f"Problem validation failed on attempt {attempt}/{attempts}.")

    # 3. Extract components
    generated_problem = state.get("generated_problem")
    testcase_bundle = state.get("testcase_bundle")
    reference_solution = state.get("reference_solution")
    validation_report = state.get("validation_report")
    hint_bundle = state.get("hint_bundle")

    # 4. Optional Hint Bundle check
    if hint_bundle:
        # Ensure hints are safe and reveals_core_code is False
        for hint in hint_bundle.hints:
            if hint.reveals_core_code:
                hint_bundle.safe_to_show = False
                break

    # 5. Concept Context retrieval
    concept_context = []
    if input_data.include_concept_context and generated_problem:
        query_parts = []
        if generated_problem.algorithm:
            query_parts.extend(generated_problem.algorithm)
        if generated_problem.learning_goal:
            query_parts.append(generated_problem.learning_goal)
        
        if query_parts:
            query_str = " ".join(query_parts)
            try:
                from rag import search_concepts
                results = await asyncio.to_thread(search_concepts, query_str, 3)
                concept_context = [f"Source: {c.source_path}\n{c.content}" for c in results]
            except Exception as e:
                logger.warning(f"RAG search failed in problem generation service: {e}")
                concept_context = []

    # 6. Build Summary
    if validation_report:
        if validation_report.passed:
            summary = "요청하신 문제와 테스트케이스가 성공적으로 생성 및 검증되었습니다."
        else:
            summary = "생성 과정에서 일부 검증 검사를 통과하지 못했습니다. 피드백을 확인해 보세요."
    else:
        summary = "문제와 테스트케이스가 생성되었으나 검증 보고서가 누락되었습니다."

    # 7. Determine safety
    safe_to_show = True
    if validation_report and not validation_report.passed:
        safe_to_show = False

    reports = [generated_problem, testcase_bundle, hint_bundle]
    for r in reports:
        if r is not None and hasattr(r, "safe_to_show") and not r.safe_to_show:
            safe_to_show = False
            break

    return ProblemGenerationPackage(
        problem_id=generated_problem.problem_id if generated_problem else "unknown",
        generated_problem=generated_problem,
        testcase_bundle=testcase_bundle,
        reference_solution=reference_solution,
        validation_report=validation_report,
        hint_bundle=hint_bundle,
        concept_context=concept_context,
        summary=summary,
        safe_to_show=safe_to_show
    )


def generate_problem_package_sync(*args, **kwargs) -> ProblemGenerationPackage:
    """Convenience sync wrapper for CLI/tests."""
    return asyncio.run(generate_problem_package(*args, **kwargs))


def problem_package_to_public_dict(package: ProblemGenerationPackage) -> dict:
    """
    Return JSON-safe dict for API response.
    Must exclude reference_solution.
    """
    data = package.model_dump(mode="json")
    data.pop("reference_solution", None)
    return data


def problem_package_to_internal_dict(package: ProblemGenerationPackage) -> dict:
    """
    Return JSON-safe dict including internal fields.
    Internal only.
    """
    return package.model_dump(mode="json")
