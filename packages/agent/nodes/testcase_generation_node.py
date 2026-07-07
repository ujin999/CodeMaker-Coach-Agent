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

    # Call with allow_experimental_llm_fallback=False (default behavior) to ensure determinism for supported types
    bundle = generate_testcases(problem, min_cases=min_cases, allow_experimental_llm_fallback=False)

    new_state = state.copy()
    new_state["testcase_bundle"] = bundle
    return new_state
