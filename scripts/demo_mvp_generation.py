import sys
import os
from pathlib import Path

# Add project root to python path to support top-level imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from agent.schemas import ProblemGenerationInput, GeneratedProblem, TestcaseBundle, HintBundle
from agent.chains.problem_generation import generate_problem
from agent.chains.testcase_generation import generate_testcases
from agent.chains.hint_generation import generate_hints


def print_section(title: str) -> None:
    """Utility to print distinct section headers."""
    print("\n" + "=" * 20 + f" {title} " + "=" * 20)


def print_generated_problem(problem: GeneratedProblem) -> None:
    """Prints all the GeneratedProblem details in full."""
    print_section("생성된 문제 전체")
    print(f"[문제 ID]\n{problem.problem_id}\n")
    print(f"[제목]\n{problem.title}\n")
    print(f"[난이도]\n{problem.difficulty}\n")
    print(f"[알고리즘]\n{', '.join(problem.algorithm)}\n")
    print(f"[학습 목표]\n{problem.learning_goal}\n")
    print(f"[문제 설명]\n{problem.statement}\n")
    print(f"[입력 형식]\n{problem.input_format}\n")
    print(f"[출력 형식]\n{problem.output_format}\n")
    print(f"[제한 조건]")
    for constraint in problem.constraints:
        print(f"- {constraint}")
    print()
    print(f"[예제 입력]\n{problem.sample_input}\n")
    print(f"[예제 출력]\n{problem.sample_output}\n")
    print(f"[예상 시간복잡도]\n{problem.expected_time_complexity}\n")


def print_testcases(bundle: TestcaseBundle) -> None:
    """Prints each testcase inside the bundle in full."""
    print_section("생성된 테스트케이스 전체")
    print(f"총 {len(bundle.testcases)}개의 테스트케이스가 생성되었습니다.\n")
    for idx, tc in enumerate(bundle.testcases, 1):
        print(f"[테스트케이스 {idx}]")
        print(f"이름: {tc.name}")
        print(f"공개 범위: {tc.visibility}")
        print(f"목적: {tc.purpose}")
        print(f"난이도 이유: {tc.difficulty_reason or 'N/A'}")
        print(f"계산 검증: {tc.calculation_steps or 'N/A'}")
        print(f"입력:\n{tc.input_data}")
        print(f"출력:\n{tc.expected_output}")
        print("-" * 40)


def print_hints(hint_bundle: HintBundle) -> None:
    """Prints each hint inside the hint bundle in full."""
    print_section("생성된 힌트 전체")
    for hint in hint_bundle.hints:
        print(f"[Level {hint.level}]")
        print(f"제목: {hint.title}")
        print(f"내용: {hint.content}")
        print(f"코드 스켈레톤:\n{hint.code_skeleton or '없음'}")
        print(f"참조 개념: {', '.join(hint.concept_refs)}")
        print(f"출처: {hint.source}")
        print("-" * 40)


def main():
    print("=== CodeMaker Coach Agent - MVP Generation Demo ===")
    
    # 1. Security & Env check
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n[ERROR] OpenAI API key is missing.")
        print("Please configure OPENAI_API_KEY in your local .env or environment variables.")
        print("Exiting gracefully.")
        sys.exit(0)
        
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"Embedding Model: {settings.embedding_model or 'text-embedding-3-small'}")
    print(f"Qdrant URL: {settings.qdrant_url}")
    print("API Key: [REDACTED]")
    print("-" * 50)
    
    # 2. Formulate input
    input_data = ProblemGenerationInput(
        algorithm="binary_search",
        difficulty="medium",
        problem_style="practical",
        language="Python",
        learning_goal="예산 배정 최적화를 위한 매개 변수 탐색과 경계 조건 처리",
        user_level="중급",
        recent_weaknesses=["인덱스 오프바이원(off-by-one) 오류", "경계 조건 반복문 조건 처리"]
    )
    
    print(f"Generating problem for algorithm: '{input_data.algorithm}' (Difficulty: {input_data.difficulty}) in Korean...")
    
    # 3. Stepwise generation
    try:
        # A. Generate problem
        print("\n[Step 1] Running generate_problem()...")
        problem = generate_problem(input_data)
        print_generated_problem(problem)
        
        # B. Generate testcases
        print("\n[Step 2] Running generate_testcases()...")
        bundle = generate_testcases(problem)
        if "solve_budget_cap" in bundle.generation_notes or "deterministic_budget_cap" in bundle.generation_notes:
            print("Testcase generation mode: deterministic_budget_cap")
        else:
            print("Testcase generation mode: LLM fallback")
        print_testcases(bundle)
            
        # C. Generate hints
        print("\n[Step 3] Running generate_hints()...")
        hint_bundle = generate_hints(problem, allowed_level=3, user_situation="Stuck on binary search index updates")
        print_hints(hint_bundle)
                
        print("\n=== Demo completed successfully ===")
        
    except Exception as e:
        print(f"\n[ERROR] Generation failed during demo run: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
