from langchain_core.prompts import ChatPromptTemplate


def build_problem_validation_prompt() -> ChatPromptTemplate:
    """Builds and returns the ChatPromptTemplate for validating a generated problem and testcases."""
    system_message = (
        "You are an elite coding competition judge and quality assurance auditor. "
        "Your task is to thoroughly analyze the generated problem, reference solution, and testcases for consistency and correctness.\n\n"
        "Rules:\n"
        "1. All audit results, explanations, and issue descriptions must be written in Korean.\n"
        "2. You MUST verify that the user-facing problem statements, input/output formats, constraints, and hint blueprints are written in Korean. Report a validation failure if any user-facing text is written in English.\n"
        "3. You MUST verify that the problem genuinely requires the requested Core Algorithm and cannot be bypassed by a simpler direct method (e.g. greedy/sorting). If it can be bypassed, fail validation.\n"
        "4. You MUST check that all testcase expected outputs are mathematically consistent with the problem logic. If any sample, hidden, or edge case has an incorrect output, fail validation.\n"
        "5. BUDGET CAP VALIDATION: For budget cap problems where allocation is min(request_i, C):\n"
        "    - C must be in [0, max(request_i)] where C = expected_output.\n"
        "    - Verify sum(min(request_i, C)) <= B.\n"
        "    - If C < max(request_i), also verify sum(min(request_i, C+1)) > B.\n"
        "    - If C == max(request_i), verify sum(request_i) <= B.\n"
        "    - If C == 0, verify sum(min(request_i, 1)) > B unless max(request_i) == 0.\n"
        "    - If expected_output > max(request_i), fail validation unless the statement explicitly allows over-allocation.\n"
        "6. TWO POINTER SUBARRAY VALIDATION: For positive integer array + longest contiguous subarray with sum <= K:\n"
        "    - Check that all elements of the input array (nums) are positive integers.\n"
        "    - Check expected_output is an integer in [0, N] (where N is the length of the array).\n"
        "    - Verify there exists a contiguous subarray of length expected_output with sum <= K unless expected_output is 0.\n"
        "    - Verify no contiguous subarray of length expected_output + 1 has sum <= K.\n"
        "    - If expected_output == N, verify the total sum of the array is <= K.\n"
        "7. BFS GRID SHORTEST PATH VALIDATION: For BFS grid shortest path:\n"
        "    - Check grid rows match N and M.\n"
        "    - Check cells are only 0 or 1.\n"
        "    - Check start and goal rules.\n"
        "    - If start or goal is wall, expected_output must be -1.\n"
        "    - If expected_output == -1, verify no path exists.\n"
        "    - If expected_output > 0, verify it is the shortest path distance counted by visited cells, with start distance 1.\n"
        "    - Moves must be limited to 4 directions.\n"
        "8. DFS GRID COMPONENT VALIDATION: For DFS grid component counting:\n"
        "    - Check grid rows match N and M.\n"
        "    - Check cells are only 0 or 1.\n"
        "    - Check connectivity is 4-directional only.\n"
        "    - Diagonal adjacency must not merge components.\n"
        "    - Verify expected_output equals the number of connected components made of 1 cells.\n"
        "    - If all cells are 0, expected_output must be 0.\n"
        "    - If all cells are 1, expected_output must be 1."
    )
    
    user_message = (
        "Please validate the following generated problem and its testcases:\n"
        "--- GENERATED PROBLEM ---\n"
        "{problem_json}\n"
        "--- TESTCASE BUNDLE ---\n"
        "{testcases_json}\n\n"
        "Verify the following checklist:\n"
        "1. Condition consistency: Are the descriptions and requirements matching throughout the text?\n"
        "2. Sample/Hidden/Edge input-output consistency: Are all testcase expected outputs mathematically correct according to the problem logic? Calculate them manually step-by-step to verify. If any output is mathematically incorrect (e.g. sum of selected costs exceeds budget), you MUST fail validation (pass=false).\n"
        "3. Constraints: Are the constraints realistic and mathematically precise?\n"
        "4. Difficulty: Is the problem appropriate for the requested difficulty level?\n"
        "5. Required algorithm: Does the problem genuinely require the requested Core Algorithm? Is there a simpler direct solution (e.g. sorting + greedy prefix sum) that makes the requested algorithm unnecessary? If a simpler direct solution exists, you MUST fail validation (pass=false).\n"
        "6. Expected Time Complexity: Does the expected_time_complexity match the intended algorithm?\n"
        "7. Solution leakage: Are there any solutions, full code snippets, or unacceptable leakages in the statement/hints?\n"
        "8. Ambiguity: Is the phrasing clear and free of double interpretations?\n"
        "9. Language Check: Is all user-facing content written in Korean?\n\n"
        "Provide a JSON response in Korean indicating whether it passes validation (pass=true/false) and list any issues found in Korean."
    )
    
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("user", user_message),
    ])
