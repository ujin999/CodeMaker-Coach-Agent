from agent.nodes.state import AgentState


def generate_problem_node(state: AgentState) -> AgentState:
    """
    Read state["generation_input"], call generate_problem(), and return updated state.
    """
    if "generation_input" not in state or state["generation_input"] is None:
        raise ValueError("Missing 'generation_input' in agent state.")

    # Import inside the function to allow clean monkeypatching in unit tests
    from agent.chains.problem_generation import generate_problem

    prob_in = state["generation_input"]
    problem = generate_problem(prob_in)

    new_state = state.copy()
    new_state["generated_problem"] = problem
    return new_state
