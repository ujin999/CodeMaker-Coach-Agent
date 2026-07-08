from agent.llm import get_chat_model
from agent.schemas import ProblemGenerationInput, GeneratedProblem
from rag.retriever import search_concepts
from agent.prompts.problem_generation import build_problem_generation_prompt
from agent.variants import select_variant


def generate_problem(input_data: ProblemGenerationInput) -> GeneratedProblem:
    """Generates a coding problem using LLM based on user constraints and retrieved RAG concepts."""
    # 1. Retrieve RAG concepts
    query = f"{input_data.algorithm} {input_data.difficulty}"
    if input_data.learning_goal:
        query += f" {input_data.learning_goal}"
    if input_data.recent_weaknesses:
        query += " " + " ".join(input_data.recent_weaknesses)
        
    concepts = search_concepts(query, top_k=3)
    concept_context = "\n\n".join([f"Source: {c.source_path}\n{c.content}" for c in concepts])
    
    # 2. Build prompt
    prompt_template = build_problem_generation_prompt()
    
    # 3. Request ChatModel with structured output schema
    temp = 0.7 if input_data.seed else 0.0
    model = get_chat_model(temperature=temp)
    structured_model = model.with_structured_output(GeneratedProblem)
    
    context_str = concept_context
    if input_data.seed:
        context_str += f"\n\nGeneration Seed/Nonce: {input_data.seed}\n"

    # ── Graph RAG 기반 적응형 에러 방어 제약조건 동적 주입 ──
    if hasattr(input_data, "recent_errors") and input_data.recent_errors:
        context_str += "\n\n[USER ERROR CONTEXT & CONSTRAINTS]"
        context_str += "\nThe user has frequently encountered the following errors recently. You MUST adjust the problem statement, constraints, or hint instructions to help them learn to avoid these issues:\n"
        for err in input_data.recent_errors:
            if err == "TLE":
                context_str += (
                    "- USER WEAKNESS: Time Limit Exceeded (TLE).\n"
                    "  INSTRUCTION: Formulate a tight constraints section (e.g., N up to 10^5) that forces an optimized O(N) or O(N log N) approach, making O(N^2) brute force impossible. "
                    "In the HintBlueprint, ensure the level_2/level_3 guidelines contain clear guidance on how to avoid unnecessary nested loops and optimize time complexity.\n"
                )
            elif err in ["RE", "WA"]:
                context_str += (
                    "- USER WEAKNESS: Runtime Error (RE) / Wrong Answer (WA) on edge/boundary cases.\n"
                    "  INSTRUCTION: The problem description or constraints must naturally force the user to handle extreme inputs (such as N=0, empty arrays, or maximum integer limits). "
                    "In the HintBlueprint's edge_case_focus, explicitly specify at least two edge/boundary values the user must handle carefully.\n"
                )
            elif err == "MLE":
                context_str += (
                    "- USER WEAKNESS: Memory Limit Exceeded (MLE).\n"
                    "  INSTRUCTION: Design the problem constraints and time/memory limits to discourage large spatial allocations (like massive multidimensional tables or adjacency matrices). "
                    "Ensure the hint blueprint guides them toward space-efficient representations.\n"
                )

    variant = select_variant(input_data.algorithm, input_data.seed)
    if variant:
        context_str += f"\n\nSelected Variant ID: {variant['variant_id']}\n"
        context_str += f"Target Variant Instruction:\n{variant['prompt_instruction']}\n"
        for kw in variant["forbidden_keywords"]:
            context_str += f"Do NOT mention or formulate the problem as a '{kw}' problem.\n"
    elif input_data.seed:
        context_str += "Please generate a unique variant scenario/description corresponding to this seed."

    prompt_messages = prompt_template.format_messages(
        algorithm=input_data.algorithm,
        difficulty=input_data.difficulty,
        problem_style=input_data.problem_style or "standard",
        language=input_data.language or "Python",
        learning_goal=input_data.learning_goal or "understanding basic logic",
        user_level=input_data.user_level or "intermediate",
        recent_weaknesses=input_data.recent_weaknesses or ["none"],
        concept_context=context_str
    )
    
    result = structured_model.invoke(prompt_messages)
    
    # Post-process problem_id if seed is present to ensure uniqueness in DB cache
    if input_data.seed and result and result.problem_id:
        clean_seed = "".join(c for c in input_data.seed if c.isalnum() or c == "_")[:8]
        if clean_seed and clean_seed not in result.problem_id:
            result.problem_id = f"{result.problem_id}_{clean_seed}"
            
    return result


