from langchain_core.prompts import ChatPromptTemplate


def build_feedback_prompt() -> ChatPromptTemplate:
    """Builds and returns the ChatPromptTemplate for generating feedback after user submission."""
    system_message = (
        "You are an encouraging and patient coding coach. Your goal is to analyze the user's submission, "
        "explain the cause of their error (WA, TLE, RE, MLE, etc.) without revealing the complete solution code, "
        "and provide guidance to help them learn from their mistakes based on retrieved concept guidelines."
    )
    
    user_message = (
        "Please provide learning-oriented feedback based on the following details:\n"
        "- Submission Result Type: {result_type}\n"
        "- User Code Summary/Snippet:\n{user_code}\n"
        "- Allowed Hint Level: {allowed_level}\n\n"
        "Retrieved Concept Guidelines:\n"
        "--- CONCEPTS ---\n"
        "{concept_context}\n"
        "--- END CONCEPTS ---\n\n"
        "Generate a helpful feedback response that adheres strictly to the hint policy (no full code solutions)."
    )
    
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("user", user_message),
    ])
