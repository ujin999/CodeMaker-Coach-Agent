from agent.schemas import GeneratedProblem, TestcaseBundle
from agent.testcase_generators.base import (
    detect_problem_type,
    UnsupportedTestcaseGeneratorError,
)
from agent.testcase_generators.budget_cap import generate_budget_cap_testcases
from agent.testcase_generators.cable_cutting import generate_cable_cutting_testcases
from agent.testcase_generators.router_installation import generate_router_installation_testcases
from agent.testcase_generators.immigration_time import generate_immigration_time_testcases
from agent.testcase_generators.lower_bound_count import generate_lower_bound_count_testcases
from agent.testcase_generators.two_pointer_subarray import generate_two_pointer_subarray_testcases
from agent.testcase_generators.bfs_grid_shortest_path import generate_bfs_grid_shortest_path_testcases
from agent.testcase_generators.dfs_grid_components import generate_dfs_grid_components_testcases


def get_testcase_generator_name(problem: GeneratedProblem) -> str:
    """
    Return the deterministic generator name for a problem.
    Currently supports:
    - budget_cap
    - cable_cutting
    - router_installation
    - immigration_time
    - lower_bound_count
    - two_pointer_subarray
    - bfs_grid_shortest_path
    - dfs_grid_components
    """
    return detect_problem_type(problem)


def generate_deterministic_testcases(
    problem: GeneratedProblem,
    min_cases: int = 5,
) -> TestcaseBundle:
    """
    Detect problem type and call the correct deterministic generator.
    Raise UnsupportedTestcaseGeneratorError if the problem type is not supported.
    """
    problem_type = detect_problem_type(problem)
    if problem_type == "budget_cap":
        bundle = generate_budget_cap_testcases(problem.problem_id, min_cases=min_cases)
        
        # Populate deterministic metadata fields if they exist in the schema
        if hasattr(bundle, "generation_mode"):
            bundle.generation_mode = "deterministic"
        if hasattr(bundle, "generator_name"):
            bundle.generator_name = "budget_cap"
        if hasattr(bundle, "verification_status"):
            bundle.verification_status = "passed"
            
        return bundle
    elif problem_type == "cable_cutting":
        bundle = generate_cable_cutting_testcases(problem.problem_id, min_cases=min_cases)
        if hasattr(bundle, "generation_mode"):
            bundle.generation_mode = "deterministic"
        if hasattr(bundle, "generator_name"):
            bundle.generator_name = "cable_cutting"
        if hasattr(bundle, "verification_status"):
            bundle.verification_status = "passed"
        return bundle
    elif problem_type == "router_installation":
        bundle = generate_router_installation_testcases(problem.problem_id, min_cases=min_cases)
        if hasattr(bundle, "generation_mode"):
            bundle.generation_mode = "deterministic"
        if hasattr(bundle, "generator_name"):
            bundle.generator_name = "router_installation"
        if hasattr(bundle, "verification_status"):
            bundle.verification_status = "passed"
        return bundle
    elif problem_type == "immigration_time":
        bundle = generate_immigration_time_testcases(problem.problem_id, min_cases=min_cases)
        if hasattr(bundle, "generation_mode"):
            bundle.generation_mode = "deterministic"
        if hasattr(bundle, "generator_name"):
            bundle.generator_name = "immigration_time"
        if hasattr(bundle, "verification_status"):
            bundle.verification_status = "passed"
        return bundle
    elif problem_type == "lower_bound_count":
        bundle = generate_lower_bound_count_testcases(problem.problem_id, min_cases=min_cases)
        if hasattr(bundle, "generation_mode"):
            bundle.generation_mode = "deterministic"
        if hasattr(bundle, "generator_name"):
            bundle.generator_name = "lower_bound_count"
        if hasattr(bundle, "verification_status"):
            bundle.verification_status = "passed"
        return bundle
    elif problem_type == "two_pointer_subarray":
        bundle = generate_two_pointer_subarray_testcases(problem.problem_id, min_cases=min_cases)
        
        # Populate deterministic metadata fields if they exist in the schema
        if hasattr(bundle, "generation_mode"):
            bundle.generation_mode = "deterministic"
        if hasattr(bundle, "generator_name"):
            bundle.generator_name = "two_pointer_subarray"
        if hasattr(bundle, "verification_status"):
            bundle.verification_status = "passed"
            
        return bundle
    elif problem_type == "bfs_grid_shortest_path":
        bundle = generate_bfs_grid_shortest_path_testcases(problem.problem_id, min_cases=min_cases)
        
        # Populate deterministic metadata fields if they exist in the schema
        if hasattr(bundle, "generation_mode"):
            bundle.generation_mode = "deterministic"
        if hasattr(bundle, "generator_name"):
            bundle.generator_name = "bfs_grid_shortest_path"
        if hasattr(bundle, "verification_status"):
            bundle.verification_status = "passed"
            
        return bundle
    elif problem_type == "dfs_grid_components":
        bundle = generate_dfs_grid_components_testcases(problem.problem_id, min_cases=min_cases)
        
        # Populate deterministic metadata fields if they exist in the schema
        if hasattr(bundle, "generation_mode"):
            bundle.generation_mode = "deterministic"
        if hasattr(bundle, "generator_name"):
            bundle.generator_name = "dfs_grid_components"
        if hasattr(bundle, "verification_status"):
            bundle.verification_status = "passed"
            
        return bundle
    else:
        raise UnsupportedTestcaseGeneratorError(
            "No deterministic testcase generator is available for this problem type."
        )
