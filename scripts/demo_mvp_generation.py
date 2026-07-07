import sys
import os
from pathlib import Path

# Add project root to python path to support top-level imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from agent.schemas import ProblemGenerationInput
from agent.chains.problem_generation import generate_problem
from agent.chains.testcase_generation import generate_testcases
from agent.chains.hint_generation import generate_hints


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
        learning_goal="parametric search and boundary handling",
        user_level="intermediate",
        recent_weaknesses=["off-by-one indices", "while loop condition bounds"]
    )
    
    print(f"Generating problem for algorithm: '{input_data.algorithm}' (Difficulty: {input_data.difficulty})...")
    
    # 3. Stepwise generation
    try:
        # A. Generate problem
        print("\n[Step 1] Running generate_problem()...")
        problem = generate_problem(input_data)
        print(f"-> Success! Problem ID: {problem.problem_id}")
        print(f"-> Title: {problem.title}")
        print(f"-> Expected Time Complexity: {problem.expected_time_complexity}")
        print(f"-> Statement Summary:\n   {problem.statement[:120]}...")
        
        # B. Generate testcases
        print("\n[Step 2] Running generate_testcases()...")
        bundle = generate_testcases(problem)
        print(f"-> Success! Generated {len(bundle.testcases)} testcases.")
        for idx, tc in enumerate(bundle.testcases, 1):
            print(f"   [{idx}] Name: '{tc.name}' | Visibility: {tc.visibility} | Purpose: {tc.purpose}")
            
        # C. Generate hints
        print("\n[Step 3] Running generate_hints()...")
        hint_bundle = generate_hints(problem, allowed_level=3, user_situation="Stuck on binary search index updates")
        print(f"-> Success! Generated {len(hint_bundle.hints)} staged hints.")
        for idx, hint in enumerate(hint_bundle.hints, 1):
            print(f"   - Hint Level {hint.level} Title: '{hint.title}'")
            print(f"     Content Summary: {hint.content[:80]}...")
            if hint.code_skeleton:
                print("     [Code Skeleton Provided]")
                
        print("\n=== Demo completed successfully ===")
        
    except Exception as e:
        print(f"\n[ERROR] Generation failed during demo run: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
