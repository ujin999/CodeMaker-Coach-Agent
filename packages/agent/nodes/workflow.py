from agent.schemas import ProblemGenerationInput, GeneratedProblem, SubmissionResult, TestcaseRunResult
from agent.nodes.state import AgentState
from agent.nodes.problem_generation_node import generate_problem_node
from agent.nodes.testcase_generation_node import generate_testcases_node
from agent.nodes.reference_solver_node import generate_reference_solution_node
from agent.nodes.hint_generation_node import generate_hints_node
from agent.nodes.validation_node import validate_outputs_node
from agent.nodes.feedback_node import generate_feedback_node
from agent.nodes.routing_node import route_next_action_node
from agent.nodes.submission_evaluation_node import evaluate_submission_node
from agent.nodes.error_diagnosis_node import diagnose_submission_node
from agent.nodes.failed_case_explanation_node import explain_failed_case_node


def run_package_workflow(
    generation_input: ProblemGenerationInput,
    min_cases: int = 5,
    allowed_hint_level: int = 3,
    user_situation: str | None = None,
    include_hints: bool = True,
) -> AgentState:
    """
    Run a simple package-level workflow:
    problem -> testcases -> optional hints -> validation -> routing.
    """
    # Initialize the workflow state
    state = AgentState(
        generation_input=generation_input,
        min_cases=min_cases,
        allowed_hint_level=allowed_hint_level,
        user_situation=user_situation,
        errors=[],
        metadata={}
    )

    # 1. Problem generation
    state = generate_problem_node(state)

    # 2. Testcase generation
    state = generate_testcases_node(state)

    # 3. Reference solution generation + Judge0 verification
    state = generate_reference_solution_node(state)

    # 4. Optional Hint generation
    if include_hints:
        state = generate_hints_node(state)

    # 5. Validation
    state = validate_outputs_node(state)

    # 6. Routing
    state = route_next_action_node(state)

    return state


def run_feedback_workflow(
    problem: GeneratedProblem,
    submission_result: SubmissionResult,
) -> AgentState:
    """
    Run deterministic feedback workflow:
    problem + submission_result -> diagnosis -> failed case explanation -> feedback -> routing.
    """
    state = AgentState(
        generated_problem=problem,
        submission_result=submission_result,
        errors=[],
        metadata={}
    )

    state = diagnose_submission_node(state)
    state = explain_failed_case_node(state)
    state = generate_feedback_node(state)
    state = route_next_action_node(state)
    return state


def run_submission_review_workflow(
    problem: GeneratedProblem,
    testcase_run_results: list[TestcaseRunResult],
    user_code: str | None = None,
    language: str | None = None,
) -> AgentState:
    """
    Run:
    testcase run results -> submission evaluation -> diagnosis -> failed case explanation -> feedback -> routing
    """
    state = AgentState(
        generated_problem=problem,
        testcase_run_results=testcase_run_results,
        errors=[],
        metadata={}
    )

    if user_code is not None or language is not None:
        state["submission_result"] = SubmissionResult(
            problem_id=problem.problem_id,
            result_type="UNKNOWN",
            user_code=user_code,
            language=language
        )

    # 1. Evaluate submission results
    state = evaluate_submission_node(state)

    # 2. Run error diagnosis
    state = diagnose_submission_node(state)

    # 3. Run failed case explanation
    state = explain_failed_case_node(state)

    # 4. Generate feedback report
    state = generate_feedback_node(state)

    # 5. Routing decision
    state = route_next_action_node(state)

    return state
