from langchain_core.prompts import ChatPromptTemplate


def build_testcase_generation_prompt() -> ChatPromptTemplate:
    """Builds and returns the ChatPromptTemplate for generating testcases."""
    system_message = (
        "WARNING: This prompt is for unsupported experimental cases only. "
        "For supported MVP problem types (such as budget cap / parametric search, two-pointer subarray with sum <= K, BFS grid shortest path, or DFS grid components), expected_output must be computed by deterministic generator code, not by LLM arithmetic. "
        "The LLM must not be trusted as the source of truth for expected_output.\n\n"
        "You are an expert software QA engineer specializing in coding test validation. "
        "Your task is to generate a comprehensive test suite (TestcaseBundle) for the given problem.\n\n"
        "Rules:\n"
        "1. Create at least one sample testcase matching the sample input/output of the problem.\n"
        "2. Create hidden and edge testcases covering minimum/maximum values, extreme inputs, empty states, or large sizes.\n"
        "3. Every testcase must include clear 'input_data', 'expected_output', and 'purpose'.\n"
        "4. Avoid copying exact testcases from known platforms.\n"
        "5. You MUST generate at least {min_cases} testcases in total.\n"
        "6. If {min_cases} >= 2, you MUST include at least one hidden or edge testcase in addition to the sample testcase.\n"
        "7. Output must conform to the requested JSON schema for TestcaseBundle.\n"
        "8. CRITICAL: All user-facing description values must be written in Korean. JSON keys must remain in English. Testcase name, purpose, difficulty_reason, and generation_notes must be written in Korean. Do not translate input_data or expected_output values; they must remain raw testcase data strings.\n"
        "9. CRITICAL SIZE LIMIT: To avoid LLM token limits, the raw input_data and expected_output size for any single testcase must NOT exceed 10 items (e.g. N <= 10). Do not output more than 10 numbers in input_data under any circumstances. Keep N small (between 1 and 10) for all testcases (including sample, hidden, and edge cases) to ensure token-friendliness and easy mathematical verification.\n"
        "10. MATHEMATICAL CORRECTNESS & CONSISTENCY: Calculate the expected_output step by step before finalizing each testcase. All outputs must be 100% mathematically correct and consistent with the logic in the problem statement. Prefer small but representative testcases where correctness can easily be manually verified. Do not generate contradictory outputs.\n"
        "11. BUDGET CAP VERIFICATION PROCEDURES: If the problem uses the budget cap rule (allocation = min(request_i, C) under budget B):\n"
        "    - If sum(request_i) <= B, expected_output must be max(request_i). Cap values above max(request_i) are not meaningful because all requests are already fully granted. The explanation should clearly state that cap values above max(request_i) are not meaningful since all requests are already fully granted.\n"
        "    - If B is smaller than the minimum request, the answer is NOT 0. It must be floor(B / N) (e.g. N=3, costs=[100, 200, 300], B=50 -> cap C=16 since 16+16+16=48 <= 50, whereas 17+17+17=51 > 50. So expected_output is 16).\n"
        "    - For EVERY generated testcase, you MUST mentally verify: C must be in [0, max(request_i)] where C = expected_output. Verify sum(min(request_i, C)) <= B. If C < max(request_i), also verify sum(min(request_i, C+1)) > B. If C == max(request_i), verify sum(request_i) <= B.\n"
        "12. CALCULATION STEPS FIELD: In the 'calculation_steps' field, you MUST write down the step-by-step arithmetic verification showing that the boundary condition checks pass. If C < max(request_i), write: 'C=X 일 때 sum(min(요청, X)) = ... <= B 이고, C=X+1 일 때 sum = ... > B 이므로 상한액은 X'. If C == max(request_i), write: 'C=X 일 때 sum(min(요청, X)) = ... <= B 이고 모든 요청의 합이 예산 이하이므로 정답은 X'."
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
        "Generate a TestcaseBundle containing sample, hidden, and edge test cases (minimum of {min_cases} cases) in Korean. Verify each expected output mathematically and keep data size under the token limits."
    )
    
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("user", user_message),
    ])
