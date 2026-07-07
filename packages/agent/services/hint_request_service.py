import asyncio
import logging
from typing import Optional, List, Union
from agent.schemas import HintRequestPackageInput, HintRequestPackage, Hint, HintBundle

logger = logging.getLogger(__name__)


async def request_hint_package(
    input_data: HintRequestPackageInput,
    generated_hints: Optional[Union[HintBundle, List[Hint]]] = None,
) -> HintRequestPackage:
    """
    Async-first package-level hint request API.
    Enforces allowed_level at package level.
    Uses existing hint retriever when generated_hints is not provided.
    """
    problem_id = input_data.problem_id
    allowed_level = input_data.allowed_level
    requested_level = input_data.requested_level if input_data.requested_level is not None else allowed_level

    blocked = False
    block_reason = None
    
    # 1. Enforce allowed_level check
    if requested_level > allowed_level:
        blocked = True
        block_reason = "아직 허용되지 않은 힌트 단계입니다. 먼저 현재 단계 힌트를 확인하거나 승급을 요청하세요."
        delivered_level = allowed_level
    else:
        delivered_level = requested_level

    raw_hints = []
    source_refs = []

    # 2. Retrieve hints
    if generated_hints is not None:
        if hasattr(generated_hints, "hints"):
            raw_hints = generated_hints.hints
        else:
            raw_hints = generated_hints
    else:
        # Retrieve hints from vector store
        try:
            from rag import search_hints
            # search_hints is sync, run in thread pool
            results = await asyncio.to_thread(
                search_hints,
                problem_id,
                input_data.query,
                allowed_level
            )
            for doc in results:
                meta = doc.metadata
                content = doc.page_content
                
                title = f"Level {meta.get('hint_level', 1)} Hint"
                content_text = content
                code_skeleton = None
                
                if "Title: " in content:
                    parts = content.split("Content: ", 1)
                    title_part = parts[0].replace("Title: ", "").strip()
                    if title_part:
                        title = title_part
                    if len(parts) > 1:
                        content_text = parts[1]
                        
                if "Code Skeleton:" in content_text:
                    c_parts = content_text.split("Code Skeleton:", 1)
                    content_text = c_parts[0].strip()
                    code_skeleton = c_parts[1].strip()

                raw_hints.append(Hint(
                    problem_id=problem_id,
                    level=int(meta.get("hint_level", 1)),
                    title=title,
                    content=content_text.strip(),
                    reveals_core_code=bool(meta.get("reveals_core_code", False)),
                    code_skeleton=code_skeleton,
                    concept_refs=meta.get("concept_refs", []),
                    source=meta.get("source", "retrieved")
                ))
                source_refs.append(f"Level {meta.get('hint_level')}")
        except Exception as e:
            logger.warning(f"RAG search_hints failed in hint request service: {e}")
            raw_hints = []

    # 3. Filter hints strictly by rules
    eligible_hints = []
    for h in raw_hints:
        if h.level > allowed_level:
            continue
        if h.reveals_core_code:
            continue
        eligible_hints.append(h)

    delivered_hints = []
    if blocked:
        # Retrieve/deliver only hints <= allowed_level if available
        delivered_hints = eligible_hints
    else:
        # Prefer exact requested level
        exact_hints = [h for h in eligible_hints if h.level == requested_level]
        if exact_hints:
            delivered_hints = exact_hints
        else:
            delivered_hints = eligible_hints

    # 4. delivered_level recalculation
    if delivered_hints:
        max_lvl = max(h.level for h in delivered_hints)
        delivered_level = min(max_lvl, allowed_level)
    else:
        delivered_level = min(delivered_level, allowed_level)

    # 5. Korean Summary
    if blocked:
        summary = f"허용되지 않은 단계({requested_level}단계) 힌트를 요청하여 요청이 거부되었습니다."
    else:
        levels = sorted(list(set(h.level for h in delivered_hints)))
        levels_str = ", ".join(f"{lvl}단계" for lvl in levels)
        if levels:
            summary = f"{levels_str} 힌트가 정상적으로 제공되었습니다."
        else:
            summary = "요청에 부합하는 적절한 힌트를 찾지 못했습니다."

    # 6. Safety policy checks
    safe_to_show = True
    for h in delivered_hints:
        if h.reveals_core_code:
            safe_to_show = False
            break

    # Build source references if they were not populated from metadata
    if not source_refs and delivered_hints:
        source_refs = [f"Level {h.level}" for h in delivered_hints]

    return HintRequestPackage(
        problem_id=problem_id,
        allowed_level=allowed_level,
        requested_level=input_data.requested_level,
        delivered_level=delivered_level,
        hints=delivered_hints,
        blocked=blocked,
        block_reason=block_reason,
        source_refs=source_refs,
        summary=summary,
        safe_to_show=safe_to_show
    )


def request_hint_package_sync(*args, **kwargs) -> HintRequestPackage:
    """Convenience sync wrapper for CLI/tests."""
    return asyncio.run(request_hint_package(*args, **kwargs))


def hint_package_to_dict(package: HintRequestPackage) -> dict:
    """Return JSON-safe dict representation."""
    return package.model_dump(mode="json")


def can_promote_hint_level(current_level: int, user_confirmed: bool) -> tuple[bool, int, str]:
    """
    Package-only helper.
    If user_confirmed=True and current_level < 3, return next level.
    No DB state mutation.
    """
    if user_confirmed and current_level < 3:
        next_level = current_level + 1
        return True, next_level, f"힌트 단계가 {next_level}단계로 승급되었습니다."
    else:
        return False, current_level, "승급 조건을 충족하지 못했거나 이미 최고 단계(3단계)입니다."
