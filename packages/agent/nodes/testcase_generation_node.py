from agent.nodes.state import AgentState


def generate_testcases_node(state: AgentState) -> AgentState:
    """
    Read state["generated_problem"], call generate_testcases(), and return updated state.
    """
    if "generated_problem" not in state or state["generated_problem"] is None:
        raise ValueError("Missing 'generated_problem' in agent state.")

    # Import inside the function to allow clean monkeypatching in unit tests
    from agent.chains.testcase_generation import generate_testcases

    problem = state["generated_problem"]
    min_cases = state.get("min_cases", 5)

    # Call with allow_experimental_llm_fallback depending on the environment to ensure robustness
    import os
    from agent.testcase_generators import UnsupportedTestcaseGeneratorError

    allow_fallback = os.getenv("ENV") != "test" and os.getenv("RELAX_VALIDATION", "true").lower() != "false"

    new_state = state.copy()
    try:
        bundle = generate_testcases(problem, min_cases=min_cases, allow_experimental_llm_fallback=allow_fallback)
        new_state["testcase_bundle"] = bundle
    except UnsupportedTestcaseGeneratorError as e:
        if "errors" not in new_state or new_state["errors"] is None:
            new_state["errors"] = []
        new_state["errors"].append(str(e))
        new_state["testcase_bundle"] = None

    return new_state
