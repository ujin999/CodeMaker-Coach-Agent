from agent.llm import get_chat_model
from agent.schemas import ProblemGenerationInput, GeneratedProblem
from rag.retriever import search_concepts
from agent.prompts.problem_generation import build_problem_generation_prompt


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
    model = get_chat_model()
    structured_model = model.with_structured_output(GeneratedProblem)
    
    prompt_messages = prompt_template.format_messages(
        algorithm=input_data.algorithm,
        difficulty=input_data.difficulty,
        problem_style=input_data.problem_style or "standard",
        language=input_data.language or "Python",
        learning_goal=input_data.learning_goal or "understanding basic logic",
        user_level=input_data.user_level or "intermediate",
        recent_weaknesses=input_data.recent_weaknesses or ["none"],
        concept_context=concept_context
    )
    
    result = structured_model.invoke(prompt_messages)
    return result
