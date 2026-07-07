from langchain_core.prompts import ChatPromptTemplate


def build_testcase_generation_prompt() -> ChatPromptTemplate:
    """Builds and returns the ChatPromptTemplate for generating testcases."""
    system_message = (
        "You are an expert software QA engineer specializing in coding test validation. "
        "Your task is to generate a comprehensive test suite (TestcaseBundle) for the given problem.\n\n"
        "Rules:\n"
        "1. Create at least one sample testcase matching the sample input/output of the problem.\n"
        "2. Create hidden and edge testcases covering minimum/maximum values, extreme inputs, empty states, or large sizes.\n"
        "3. Every testcase must include clear 'input_data', 'expected_output', and 'purpose'.\n"
        "4. Avoid copying exact testcases from known platforms.\n"
        "5. You MUST generate at least {min_cases} testcases in total.\n"
        "6. If {min_cases} >= 2, you MUST include at least one hidden or edge testcase in addition to the sample testcase.\n"
        "7. Output must conform to the requested JSON schema for TestcaseBundle."
    )
    
    user_message = (
        "Here is the problem definition:\n"
        "--- PROBLEM ---\n"
        "{problem_json}\n"
        "--- END PROBLEM ---\n\n"
        "Use the following retrieved testcase strategy context for guidance:\n"
        "--- STRATEGY ---\n"
        "{strategy_context}\n"
        "--- END STRATEGY ---\n\n"
        "Generate a TestcaseBundle containing sample, hidden, and edge test cases (minimum of {min_cases} cases)."
    )
    
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("user", user_message),
    ])
