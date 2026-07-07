import pytest
from agent.schemas import GeneratedProblem, HintBlueprint
from agent.testcase_generators.base import (
    detect_problem_type,
    UnsupportedTestcaseGeneratorError,
)
from agent.testcase_generators.registry import (
    generate_deterministic_testcases,
    get_testcase_generator_name,
)
from agent.schemas import TestcaseBundle


def create_dummy_problem(
    title: str = "Test Title",
    statement: str = "Test Statement",
    algorithm: list[str] = None,
) -> GeneratedProblem:
    """Helper to create a valid GeneratedProblem for tests."""
    return GeneratedProblem(
        problem_id="test-id",
        title=title,
        difficulty="medium",
        algorithm=algorithm or ["binary_search"],
        learning_goal="test goal",
        statement=statement,
        input_format="N\n...",
        output_format="C",
        constraints=["N <= 10"],
        expected_time_complexity="O(N log M)",
        hint_blueprint=HintBlueprint(
            intended_algorithm=algorithm or ["binary_search"],
            core_insight="insight",
            common_misconceptions=[],
            edge_case_focus=[],
            forbidden_disclosures=[],
            level_1_guidance="guide 1",
            level_2_guidance="guide 2",
            level_3_guidance="guide 3",
            allowed_code_exposure="none",
        ),
    )


def test_detect_problem_type_budget_cap():
    """Verify detect_problem_type detects budget_cap problem correctly."""
    # Test by specific statement text
    problem1 = create_dummy_problem(
        statement="이 문제는 상한액 C를 구하는 문제입니다. min(요청 예산, C)를 계산합니다."
    )
    assert detect_problem_type(problem1) == "budget_cap"

    # Test by binary_search algorithm with budget keywords
    problem2 = create_dummy_problem(
        title="예산 분배",
        statement="이분 탐색으로 최적의 분배금을 찾습니다.",
        algorithm=["binary_search"],
    )
    assert detect_problem_type(problem2) == "budget_cap"


def test_detect_problem_type_unsupported():
    """Verify detect_problem_type returns unsupported for other types."""
    problem = create_dummy_problem(
        title="BFS 최단경로",
        statement="그래프 탐색을 수행합니다.",
        algorithm=["bfs"],
    )
    assert detect_problem_type(problem) == "unsupported"


def test_get_testcase_generator_name():
    """Verify get_testcase_generator_name returns the correct name."""
    problem = create_dummy_problem(
        statement="상한액 C min(요청 예산, C)"
    )
    assert get_testcase_generator_name(problem) == "budget_cap"


def test_generate_deterministic_testcases_success():
    """Verify generate_deterministic_testcases returns bundle for budget_cap."""
    problem = create_dummy_problem(
        statement="상한액 C min(요청 예산, C)"
    )
    bundle = generate_deterministic_testcases(problem, min_cases=5)
    assert isinstance(bundle, TestcaseBundle)
    assert len(bundle.testcases) >= 5
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "budget_cap"


def test_generate_deterministic_testcases_unsupported():
    """Verify generate_deterministic_testcases raises UnsupportedTestcaseGeneratorError."""
    problem = create_dummy_problem(
        title="DFS 탐색",
        statement="이 문제는 DFS를 사용하는 경로 탐색 문제입니다.",
        algorithm=["dfs"],
    )
    with pytest.raises(UnsupportedTestcaseGeneratorError, match="No deterministic testcase generator"):
        generate_deterministic_testcases(problem)


def test_detect_problem_type_two_pointer_subarray():
    """Verify detect_problem_type detects two_pointer_subarray problem correctly."""
    problem1 = create_dummy_problem(
        statement="연속 부분 배열의 합이 K 이하인 최대 길이를 구하는 문제입니다. 투 포인터와 sliding window를 사용하세요.",
        algorithm=["two_pointer"],
    )
    assert detect_problem_type(problem1) == "two_pointer_subarray"

    problem2 = create_dummy_problem(
        statement="양의 정수로 구성된 연속 구간의 합과 최대 길이를 구합니다.",
        algorithm=["two_pointer"],
    )
    assert detect_problem_type(problem2) == "two_pointer_subarray"


def test_get_testcase_generator_name_two_pointer():
    """Verify get_testcase_generator_name returns the correct name for two pointer subarray."""
    problem = create_dummy_problem(
        statement="연속 부분 배열 합이 K 이하 최대 길이 투 포인터",
        algorithm=["two_pointer"],
    )
    assert get_testcase_generator_name(problem) == "two_pointer_subarray"


def test_generate_deterministic_testcases_two_pointer_success():
    """Verify generate_deterministic_testcases returns bundle for two_pointer_subarray."""
    problem = create_dummy_problem(
        statement="연속 부분 배열 합이 K 이하 최대 길이 투 포인터",
        algorithm=["two_pointer"],
    )
    bundle = generate_deterministic_testcases(problem, min_cases=5)
    assert isinstance(bundle, TestcaseBundle)
    assert len(bundle.testcases) >= 5
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "two_pointer_subarray"
    assert bundle.verification_status == "passed"


def test_two_pointer_subarray_not_detected_on_single_keyword():
    """Verify two_pointer_subarray does not trigger on a single broad keyword."""
    # Only "최대 길이"
    problem1 = create_dummy_problem(
        statement="이 문제는 최대 길이를 구하는 단순 정렬 문제입니다.",
        algorithm=["two_pointer"],
    )
    assert detect_problem_type(problem1) == "unsupported"

    # Only "양의 정수"
    problem2 = create_dummy_problem(
        statement="모든 정수는 양의 정수입니다.",
        algorithm=["two_pointer"],
    )
    assert detect_problem_type(problem2) == "unsupported"


def test_detect_problem_type_bfs_grid_shortest_path():
    """Verify detect_problem_type detects bfs_grid_shortest_path correctly."""
    # Option 1: algorithm contains bfs and statement includes at least two specified keywords
    problem1 = create_dummy_problem(
        statement="N x M 격자 지도에서 벽을 우회하여 최단 거리를 구하세요.",
        algorithm=["bfs"],
    )
    assert detect_problem_type(problem1) == "bfs_grid_shortest_path"

    # Option 2: statement includes at least 4 strong indicators
    problem2 = create_dummy_problem(
        statement="상하좌우로 이동하며 0과 1로 주어지는 지도에서 벽을 우회합니다. 도달할 수 없으면 -1을 출력하세요. BFS를 사용합니다.",
        algorithm=["graph_traversal"],
    )
    assert detect_problem_type(problem2) == "bfs_grid_shortest_path"


def test_get_testcase_generator_name_bfs_grid():
    """Verify get_testcase_generator_name returns the correct name for bfs grid shortest path."""
    problem = create_dummy_problem(
        statement="격자 최단 거리 상하좌우 벽 0과 1 도달할 수 없으면 -1 BFS 너비 우선 탐색",
        algorithm=["bfs"],
    )
    assert get_testcase_generator_name(problem) == "bfs_grid_shortest_path"


def test_generate_deterministic_testcases_bfs_grid_success():
    """Verify generate_deterministic_testcases returns bundle for bfs_grid_shortest_path."""
    problem = create_dummy_problem(
        statement="격자 최단 거리 상하좌우 벽 0과 1 도달할 수 없으면 -1 BFS 너비 우선 탐색",
        algorithm=["bfs"],
    )
    bundle = generate_deterministic_testcases(problem, min_cases=5)
    assert isinstance(bundle, TestcaseBundle)
    assert len(bundle.testcases) >= 5
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "bfs_grid_shortest_path"
    assert bundle.verification_status == "passed"


def test_detect_problem_type_dfs_grid_components():
    """Verify detect_problem_type detects dfs_grid_components correctly."""
    # Option 1: algorithm contains dfs and statement includes at least two specified keywords
    problem1 = create_dummy_problem(
        statement="격자 형태의 지도가 0과 1로 주어질 때 상하좌우 연결 요소를 구하세요.",
        algorithm=["dfs"],
    )
    assert detect_problem_type(problem1) == "dfs_grid_components"

    # Option 2: statement includes at least 4 strong indicators
    problem2 = create_dummy_problem(
        statement="1은 땅, 0은 물을 뜻하는 격자에서 섬의 개수(연결 요소)를 깊이 우선 탐색을 통해 찾아냅니다.",
        algorithm=["graph_traversal"],
    )
    assert detect_problem_type(problem2) == "dfs_grid_components"


def test_get_testcase_generator_name_dfs_grid_components():
    """Verify get_testcase_generator_name returns the correct name for dfs grid components."""
    problem = create_dummy_problem(
        statement="격자 연결 요소 상하좌우 0과 1 1은 땅 0은 물 DFS 깊이 우선 탐색",
        algorithm=["dfs"],
    )
    assert get_testcase_generator_name(problem) == "dfs_grid_components"


def test_generate_deterministic_testcases_dfs_grid_components_success():
    """Verify generate_deterministic_testcases returns bundle for dfs_grid_components."""
    problem = create_dummy_problem(
        statement="격자 연결 요소 상하좌우 0과 1 1은 땅 0은 물 DFS 깊이 우선 탐색",
        algorithm=["dfs"],
    )
    bundle = generate_deterministic_testcases(problem, min_cases=5)
    assert isinstance(bundle, TestcaseBundle)
    assert len(bundle.testcases) >= 5
    assert bundle.generation_mode == "deterministic"
    assert bundle.generator_name == "dfs_grid_components"
    assert bundle.verification_status == "passed"


def test_cross_detection_negative_cases():
    """Verify that BFS shortest path and DFS components do not mis-detect each other."""
    # A BFS shortest path problem should not be detected as dfs_grid_components
    bfs_prob = create_dummy_problem(
        statement="N x M 격자 지도에서 벽을 우회하여 최단 거리를 구하세요. 도달할 수 없으면 -1을 출력합니다.",
        algorithm=["bfs"],
    )
    assert detect_problem_type(bfs_prob) == "bfs_grid_shortest_path"
    assert detect_problem_type(bfs_prob) != "dfs_grid_components"

    # A DFS components problem should not be detected as bfs_grid_shortest_path
    dfs_prob = create_dummy_problem(
        statement="1은 땅, 0은 물을 뜻하는 격자에서 연결 요소(섬)의 개수를 구하는 프로그램. 대각선은 인접하지 않습니다.",
        algorithm=["dfs"],
    )
    assert detect_problem_type(dfs_prob) == "dfs_grid_components"
    assert detect_problem_type(dfs_prob) != "bfs_grid_shortest_path"

