from langchain_core.prompts import ChatPromptTemplate


def build_hint_generation_prompt() -> ChatPromptTemplate:
    """Builds and returns the ChatPromptTemplate for generating hints based on blueprint and context."""
    system_message = (
        "You are a helpful coding coach. Your task is to generate safe, educational, level-staged hints (HintBundle) "
        "for the given problem following the HintBlueprint and current allowed_level.\n\n"
        "Rules:\n"
        "1. Never provide the full correct solution code. Hints must only contain directions, strategy, or partial skeletons.\n"
        "2. Level 1: Focus on general direction, avoiding direct algorithm names if possible.\n"
        "3. Level 2: Explain the core algorithm choice and approach.\n"
        "4. Level 3: Give implementation details, edge checks, or a partial code skeleton (incomplete, containing placeholders like '...').\n"
        "5. Output must conform to the requested JSON schema for HintBundle.\n"
        "6. CRITICAL SCHEMA REQUIREMENT: The 'code_skeleton' field in any Hint MUST be incomplete and MUST contain at least one of these exact placeholders: '...', '# TODO', or 'pass'. Do not output complete, working functions."
    )
    
    user_message = (
        "Here is the problem and its HintBlueprint:\n"
        "--- PROBLEM & BLUEPRINT ---\n"
        "{problem_json}\n"
        "--- END PROBLEM & BLUEPRINT ---\n\n"
        "Here is the retrieved algorithm concept context:\n"
        "--- CONCEPT CONTEXT ---\n"
        "{concept_context}\n"
        "--- END CONCEPT CONTEXT ---\n\n"
        "User Situation: {user_situation}\n"
        "Current Allowed Hint Level: {allowed_level}\n\n"
        "Please generate a HintBundle containing staged hints up to level {allowed_level} based on the blueprint guidelines.\n"
        "Ensure that any 'code_skeleton' field in your response is strictly incomplete and includes placeholders like '...' or '# TODO'."
    )
    
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("user", user_message),
    ])
