from agent.nodes.state import AgentState


def generate_hints_node(state: AgentState) -> AgentState:
    """
    Read state["generated_problem"], call generate_hints(), and return updated state.
    """
    if "generated_problem" not in state or state["generated_problem"] is None:
        raise ValueError("Missing 'generated_problem' in agent state.")

    # Import inside the function to allow clean monkeypatching in unit tests
    from agent.chains.hint_generation import generate_hints

    problem = state["generated_problem"]
    allowed_level = state.get("allowed_hint_level", 3)
    user_situation = state.get("user_situation", None)

    bundle = generate_hints(problem, allowed_level=allowed_level, user_situation=user_situation)

    new_state = state.copy()
    new_state["hint_bundle"] = bundle
    return new_state
