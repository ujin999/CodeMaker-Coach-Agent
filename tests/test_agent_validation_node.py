import pytest
from agent.schemas import (
    GeneratedProblem,
    HintBlueprint,
    TestcaseBundle,
    GeneratedTestcase,
    HintBundle,
    Hint,
)
from agent.nodes.validation_node import (
    validate_generation_outputs,
    validate_problem_basic,
    validate_testcase_bundle,
    validate_hint_bundle,
)


def create_dummy_problem(
    problem_id: str = "budget_allocation_optimization",
    title: str = "예산 배정 최적화",
    statement: str = "격자 최단 경로를 구하는 문제 또는 상한액 C min(요청 예산, C) 계산 문제입니다.",
    algorithm: list[str] = None,
) -> GeneratedProblem:
    """Helper to construct a valid GeneratedProblem in Korean."""
    return GeneratedProblem(
        problem_id=problem_id,
        title=title,
        difficulty="medium",
        algorithm=algorithm or ["binary_search"],
        learning_goal="매개 변수 탐색 학습",
        statement=statement,
        input_format="입력 형식",
        output_format="출력 형식",
        constraints=["제한 조건 1"],
        expected_time_complexity="O(N log M)",
        hint_blueprint=HintBlueprint(
            intended_algorithm=algorithm or ["binary_search"],
            core_insight="이분 탐색 사용",
            common_misconceptions=["오버플로우 주의"],
            edge_case_focus=["최대값 입력"],
            forbidden_disclosures=["전체 정해"],
            level_1_guidance="힌트 1",
            level_2_guidance="힌트 2",
            level_3_guidance="힌트 3",
            allowed_code_exposure="none",
        ),
    )


def test_valid_budget_cap_validation():
    """Test A: Valid budget_cap problem and its deterministic testcases pass validation."""
    problem = create_dummy_problem()
    
    # Generate deterministic testcases using the registry function
    from agent.testcase_generators.registry import generate_deterministic_testcases
    bundle = generate_deterministic_testcases(problem, min_cases=5)
    
    report = validate_generation_outputs(problem, testcase_bundle=bundle)
    assert report.passed is True
    assert "problem" in report.checked_sections
    assert "testcases" in report.checked_sections
    assert len(report.issues) == 0


def test_wrong_testcase_output_fails_validation():
    """Test B: Testcase output mutation causes validation to fail."""
    problem = create_dummy_problem()
    
    from agent.testcase_generators.registry import generate_deterministic_testcases
    bundle = generate_deterministic_testcases(problem, min_cases=5)
    
    # Mutate the first testcase to have an incorrect output
    bundle.testcases[0].expected_output = "99999"
    
    report = validate_generation_outputs(problem, testcase_bundle=bundle)
    assert report.passed is False
    assert any(issue.severity == "error" for issue in report.issues)
    assert any("TESTCASE_VALIDATION_FAILED" in issue.code for issue in report.issues)


def test_unsupported_problem_fails_testcase_validation():
    """Test C: Unsupported problem type fails testcase validation."""
    # Create a problem with unsupported algorithm and statement keywords
    problem = create_dummy_problem(
        problem_id="unsupported_prob",
        title="단순 사칙연산",
        statement="두 정수 A와 B를 입력받아 더하는 프로그램을 작성하시오.",
        algorithm=["math"],
    )
    
    # Create a minimal testcase bundle
    bundle = TestcaseBundle(
        problem_id="unsupported_prob",
        testcases=[
            GeneratedTestcase(
                name="sample_1",
                input_data="1 2",
                expected_output="3",
                visibility="sample",
                purpose="간단한 더하기 테스트",
                calculation_steps="1 + 2 = 3"
            )
        ],
        generation_mode="deterministic",
        generator_name="unsupported_generator",
        verification_status="passed",
        generation_notes="unsupported test"
    )
    
    report = validate_generation_outputs(problem, testcase_bundle=bundle)
    assert report.passed is False
    assert any(issue.severity == "error" for issue in report.issues)
    assert any(issue.code == "UNSUPPORTED_DETERMINISTIC_GENERATOR" for issue in report.issues)


def test_hint_bundle_safety_validation():
    """Test D: Hint bundle safety validation (detecting full code leak or reveals_core_code)."""
    problem = create_dummy_problem()
    
    # 1. Valid HintBundle
    hint1 = Hint(
        problem_id=problem.problem_id,
        level=1,
        title="힌트 제목",
        content="이분 탐색의 원리를 생각해 보세요.",
        reveals_core_code=False,
    )
    hint_bundle = HintBundle(
        problem_id=problem.problem_id,
        blueprint=problem.hint_blueprint,
        hints=[hint1],
    )
    
    report = validate_generation_outputs(problem, hint_bundle=hint_bundle)
    assert report.passed is True
    
    # 2. Unsafe hint using reveals_core_code=True (bypass model validation using model_construct)
    unsafe_hint = Hint.model_construct(
        problem_id=problem.problem_id,
        level=2,
        title="정해 힌트",
        content="핵심 풀이 소스 코드입니다.",
        reveals_core_code=True,
    )
    unsafe_bundle = HintBundle(
        problem_id=problem.problem_id,
        blueprint=problem.hint_blueprint,
        hints=[unsafe_hint],
    )
    
    report2 = validate_generation_outputs(problem, hint_bundle=unsafe_bundle)
    assert report2.passed is False
    assert any(issue.code == "REVEALS_CORE_CODE" for issue in report2.issues)
    
    # 3. Unsafe hint that reveals complete Python solution code
    code_leak_hint = Hint.model_construct(
        problem_id=problem.problem_id,
        level=3,
        title="코드 설명",
        content="def solve(n, requests, b):\n    return 42",
        reveals_core_code=False,
    )
    code_leak_bundle = HintBundle(
        problem_id=problem.problem_id,
        blueprint=problem.hint_blueprint,
        hints=[code_leak_hint],
    )
    
    report3 = validate_generation_outputs(problem, hint_bundle=code_leak_bundle)
    assert report3.passed is False
    assert any(issue.code == "FULL_SOLUTION_REVEALED" for issue in report3.issues)
