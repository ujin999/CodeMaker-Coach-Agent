# packages/agent — Agent 코어 패키지

웹/DB 및 기타 인프라에 직접 의존하지 않고, 코딩 테스트 문제 생성을 처리하는 **독립 Python 패키지**입니다.

## API 문서 링크
*   자세한 Python API 명세 및 Pydantic 스키마 가이드는 [API.md](./API.md) 문서를 참고하시기 바랍니다.

## MVP 주요 공개 API (Chains)

이 패키지는 다음과 같은 MVP 기능을 제공하며, 미래에 LangGraph 노드나 FastAPI 백엔드 라우터에서 임포트하여 직접 호출할 수 있도록 설계되었습니다.

1. **`generate_problem(input: ProblemGenerationInput) -> GeneratedProblem`**:
   - 사용자가 제공한 알고리즘 유형, 난이도, 학습 목표 등을 입력받아 RAG 개념 문서를 참조해 고유한 코딩 문제를 생성합니다.
   - 출력에 문제의 학습을 보조하기 위한 힌트 설계 정보인 `HintBlueprint`를 반드시 포함합니다.
   
2. **`generate_testcases(problem: GeneratedProblem, min_cases: int = 5) -> TestcaseBundle`**:
   - 생성된 문제의 스펙에 맞춰 `sample`, `hidden`, `edge` 케이스로 구분된 테스트케이스 모음을 생성합니다.
   - 적어도 하나 이상의 `sample` 케이스가 포함되어 있어야 하며, Big-O 검증을 위한 에지 케이스 등이 설계됩니다.
   
3. **`generate_hints(problem: GeneratedProblem, allowed_level: int = 3, user_situation: str | None = None) -> HintBundle`**:
   - `HintBlueprint` 및 RAG 정보와 연동하여 1단계(방향), 2단계(알고리즘), 3단계(구현/스켈레톤)의 상세한 힌트 세트를 생성합니다.
   - 생성된 힌트는 자동으로 Hint RAG 저장소(Qdrant)에 인덱싱됩니다.

## 주요 설계 모델 (Schemas & HintBlueprint)

- **`HintBlueprint`**:
  문제 생성 당시에 동반 설계되는 "힌트를 위한 힌트(Blueprint)" 정보입니다. 핵심 아이디어, 흔한 오해, 에지 조건 초점, 금지된 노출 요소를 저장하여 향후 힌트 생성기가 일관적이고 안전한 힌트를 제공할 수 있게 조율합니다.
- **안전 정책 (Hint Policy)**:
  모든 힌트는 정답 코드를 완전 노출하지 않아야 하며, 3단계 힌트에서도 미완성의 `code_skeleton`만 허용됩니다. Pydantic 스키마 검증기 수준에서 이를 강하게 통제합니다.

## 미래 LangGraph 노드와의 통합

향후 LangGraph를 구현할 때 아래와 같이 개별 노드에서 MVP 기능들을 호출해 복합 에이전트 워크플로우를 완성할 수 있습니다:

```python
from agent.chains.problem_generation import generate_problem
from agent.chains.testcase_generation import generate_testcases

# LangGraph Node 예시
def problem_generator_node(state: GraphState):
    input_params = state["generation_input"]
    problem = generate_problem(input_params)
    return {"generated_problem": problem}
```
