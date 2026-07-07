from langchain_core.prompts import ChatPromptTemplate


def build_problem_generation_prompt() -> ChatPromptTemplate:
    """Builds and returns the ChatPromptTemplate for generating coding problems."""
    system_message = (
        "You are an expert coding test problem author. Your task is to generate a new, original coding test problem "
        "matching the requested requirements, and a corresponding HintBlueprint to guide future hint generation.\n\n"
        "Rules:\n"
        "1. Never copy existing online judge problems (Baekjoon, LeetCode, Programmers, etc.) directly. Write original problem descriptions.\n"
        "2. Do not expose the full solution code anywhere in the user-facing problem statements or output fields.\n"
        "3. Provide clear sample inputs and outputs.\n"
        "4. Output must conform to the requested JSON schema for GeneratedProblem, which includes the HintBlueprint."
    )
    
    user_message = (
        "Please generate a coding problem under the following conditions:\n"
        "- Core Algorithm: {algorithm}\n"
        "- Difficulty: {difficulty}\n"
        "- Style: {problem_style}\n"
        "- Language: {language}\n"
        "- Learning Goal: {learning_goal}\n"
        "- User Skill Level: {user_level}\n"
        "- User's Recent Weaknesses: {recent_weaknesses}\n\n"
        "Use the following retrieved algorithm concept and pattern guidelines for grounding:\n"
        "--- START CONTEXT ---\n"
        "{concept_context}\n"
        "--- END CONTEXT ---\n\n"
        "Generate the problem statement, constraints, expected time complexity, and a HintBlueprint outlining staged hints (Level 1, 2, and 3)."
    )
    
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("user", user_message),
    ])
