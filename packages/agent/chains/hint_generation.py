import json
from typing import Optional
from agent.llm import get_chat_model
from agent.schemas import GeneratedProblem, HintBundle
from rag.retriever import search_concepts
from rag.hint_retriever import build_hint_index
from agent.prompts.hint_generation import build_hint_generation_prompt



def generate_hints(
    problem: GeneratedProblem, 
    allowed_level: int = 3, 
    user_situation: Optional[str] = None
) -> HintBundle:
    """Generates stages of hints (1, 2, and 3) and indexes them into Hint RAG vector store."""
    # 1. Search RAG concepts using problem algorithm and learning goal
    query = " ".join(problem.algorithm) + " " + problem.learning_goal
    concepts = search_concepts(query, top_k=3)
    concept_context = "\n\n".join([f"Source: {c.source_path}\n{c.content}" for c in concepts])
    
    # 2. Build prompt
    prompt_template = build_hint_generation_prompt()
    
    # 3. Call ChatModel with structured output
    model = get_chat_model()
    structured_model = model.with_structured_output(HintBundle)
    
    problem_json = problem.model_dump_json(indent=2)
    
    prompt_messages = prompt_template.format_messages(
        problem_json=problem_json,
        concept_context=concept_context,
        user_situation=user_situation or "Not specified",
        allowed_level=allowed_level
    )
    
    result = structured_model.invoke(prompt_messages)
    result.problem_id = problem.problem_id
    
    # Enforce validation rules and allowed_level constraints on the output bundle
    filtered_hints = []
    for hint in result.hints:
        hint.problem_id = problem.problem_id
        if hint.reveals_core_code:
            continue
        if hint.level > allowed_level:
            continue
        filtered_hints.append(hint)
        
    result.hints = filtered_hints
    
    # Defensive assertions
    for hint in result.hints:
        assert hint.level <= allowed_level
        assert hint.reveals_core_code is False
                
    # 4. Index generated hints into Hint RAG vector store
    build_hint_index(result)
    
    return result
