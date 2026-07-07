from langchain_core.prompts import ChatPromptTemplate


def build_problem_validation_prompt() -> ChatPromptTemplate:
    """Builds and returns the ChatPromptTemplate for validating a generated problem and testcases."""
    system_message = (
        "You are an elite coding competition judge and quality assurance auditor. "
        "Your task is to thoroughly analyze the generated problem, reference solution, and testcases for consistency and correctness."
    )
    
    user_message = (
        "Please validate the following generated problem and its testcases:\n"
        "--- GENERATED PROBLEM ---\n"
        "{problem_json}\n"
        "--- TESTCASE BUNDLE ---\n"
        "{testcases_json}\n\n"
        "Verify the following checklist:\n"
        "1. Condition consistency: Are the descriptions and requirements matching throughout the text?\n"
        "2. Sample input/output consistency: Do they match the expected outputs from the reference solution?\n"
        "3. Constraints: Are the constraints realistic and mathematically precise?\n"
        "4. Difficulty: Is the problem appropriate for the requested difficulty level?\n"
        "5. Required algorithm: Is the problem actually solvable by the intended algorithm?\n"
        "6. Solution leakage: Are there any solutions, full code snippets, or unacceptable leakages in the statement/hints?\n"
        "7. Ambiguity: Is the phrasing clear and free of double interpretations?\n\n"
        "Provide a JSON response indicating whether it passes validation (pass=true/false) and list any issues found."
    )
    
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("user", user_message),
    ])
