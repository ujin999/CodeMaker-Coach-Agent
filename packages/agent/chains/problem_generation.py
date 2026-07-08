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


