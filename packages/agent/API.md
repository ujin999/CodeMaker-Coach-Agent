# Packages/Agent API 레퍼런스 가이드

본 문서는 **CodeMaker Coach Agent** 프로젝트의 AI 생성 코어 패키지인 `packages/agent`의 Python API 스펙을 정의합니다.

---

## 1. 개요 (Overview)

`packages/agent` 패키지는 데이터베이스, 웹 프레임워크 및 외부 인프라에 의존하지 않고 독립적으로 코딩 테스트 문제 생성, 테스트케이스 세트 생성 및 학습용 단계별 힌트 생성을 처리하는 **AI Generation Core Layer**입니다.

이 패키지는 외부 인터페이스(FastAPI 백엔드 라우터, LangGraph 워크플로우 노드, CLI 데모 스크립트 등)에서 직접 임포트하여 통합할 수 있도록 다음과 같은 3가지 핵심 퍼블릭 함수를 노출합니다:
- **`generate_problem(...)`**
- **`generate_testcases(...)`**
- **`generate_hints(...)`**

---

## 2. 퍼블릭 함수 API (Public Function API)

### 2.1 generate_problem

*   **임포트 경로**:
    ```python
    from agent.chains.problem_generation import generate_problem
    ```
*   **함수 서명**:
    ```python
    def generate_problem(input_data: ProblemGenerationInput) -> GeneratedProblem:
    ```
*   **상세 설명**:
    - 입력으로 주어진 알고리즘 유형, 난이도 및 학습자의 학습 목표/약점 조건을 분석하여 중복되지 않는 독창적인 문제를 생성합니다.
    - 내부적으로 [retriever.py](../rag/retriever.py)를 통해 RAG 개념 지식(algorithm, pattern 등)을 검색하여 문제 맥락과 제약 조건에 주입합니다.
    - 반환 객체는 Pydantic 모델인 `GeneratedProblem`이며, 문제와 1대1로 대응되는 힌트 제어 지침서인 `HintBlueprint`를 반드시 포함합니다.
    - 사용자에게 노출되는 문제 제목, 문제 설명, 입출력 포맷, 제한 사항 등의 텍스트 필드는 전부 **한국어**로 자동 렌더링됩니다.

*   **사용 예시**:
    ```python
    from agent.schemas import ProblemGenerationInput
    from agent.chains.problem_generation import generate_problem

    input_data = ProblemGenerationInput(
        algorithm="binary_search",
        difficulty="medium",
        problem_style="practical",
        language="Python",
        learning_goal="매개 변수 탐색 최적화 연습",
        user_level="중급",
        recent_weaknesses=["off_by_one"]
    )
    problem = generate_problem(input_data)
    print(f"생성된 문제 제목: {problem.title}")
    ```

---

### 2.2 generate_testcases

*   **임포트 경로**:
    ```python
    from agent.chains.testcase_generation import generate_testcases
    ```
*   **함수 서명**:
    ```python
    def generate_testcases(
        problem: GeneratedProblem,
        min_cases: int = 5,
        allow_experimental_llm_fallback: bool = False,
    ) -> TestcaseBundle:
    ```
*   **상세 설명**:
    - 생성된 문제(`GeneratedProblem`) 명세를 읽고, 이를 검증하기에 충분한 `sample`, `hidden`, `edge` 테스트케이스 모음을 생성합니다.
    - **결정론적 테스트케이스 생성 레지스트리 (Deterministic Generation Registry)**:
      내부 레지스트리를 통해 문제 타입을 분석하고 매핑되는 결정론적 테스트케이스 생성기를 호출합니다.
      - **지원되는 타입 (`budget_cap`)**: 예산 배정 / parametric search 문제의 경우, 내장된 Python 해결사(Reference Solver)와 테스트케이스 생성 템플릿([budget_cap.py](./testcase_generators/budget_cap.py))을 이용해 100% 결정론적으로 기대 출력(`expected_output`)과 풀이 단계(`calculation_steps`)를 계산하여 생성합니다.
      - **지원되는 타입 (`two_pointer_subarray`)**: 양의 정수 배열과 값 K가 주어졌을 때 합이 K 이하인 가장 긴 연속 부분 배열을 찾는 투 포인터 / sliding window 문제의 경우, 내장된 Python 해결사와 테스트케이스 생성 템플릿([two_pointer_subarray.py](./testcase_generators/two_pointer_subarray.py))을 이용해 100% 결정론적으로 기대 출력(`expected_output`)과 풀이 단계(`calculation_steps`)를 계산하여 생성합니다.
      - **지원되는 타입 (`bfs_grid_shortest_path`)**: N x M 격자 지도에서 0(이동 가능)과 1(벽)이 주어지고 (0,0)에서 (N-1,M-1)까지 상하좌우로 이동하여 도달할 수 있는 최단 거리를 구하는 BFS 격자 최단 경로 문제의 경우, 내장된 Python 해결사와 테스트케이스 생성 템플릿([bfs_grid_shortest_path.py](./testcase_generators/bfs_grid_shortest_path.py))을 이용해 100% 결정론적으로 기대 출력(`expected_output`)과 풀이 단계(`calculation_steps`)를 계산하여 생성합니다.
      - **지원되는 타입 (`dfs_grid_components`)**: N x M 격자 지도에서 1(땅)과 0(물)이 주어지고 상하좌우로 연결된 땅 영역의 개수(연결 요소/섬의 개수)를 구하는 DFS 격자 연결 요소 문제의 경우, 내장된 Python 해결사와 테스트케이스 생성 템플릿([dfs_grid_components.py](./testcase_generators/dfs_grid_components.py))을 이용해 100% 결정론적으로 기대 출력(`expected_output`)과 풀이 단계(`calculation_steps`)를 계산하여 생성합니다.
      - **지원되지 않는 타입**: 기본적으로 결정론적 생성기가 매핑되지 않는 문제인 경우 `UnsupportedTestcaseGeneratorError` 예외를 발생시킵니다.
    - **실험적 LLM 대체 경로 (Experimental LLM Fallback)**:
      `allow_experimental_llm_fallback=True`로 설정된 경우에 한하여, 결정론적 생성기가 없을 때 기존의 LLM 기반 생성 경로를 사용하여 테스트케이스를 빌드합니다. (이 경로는 수학적 정확성을 직접 보장하지 못하며 실험적 기능으로 취급됩니다.)
    - `min_cases` 인자를 통해 프롬프트/생성기 수준에서 최소 생성 케이스 개수를 강제합니다. (기본값: 5개)
    - 결과 검증을 위한 최소 조건으로 적어도 1개 이상의 sample 테스트케이스가 포함되어야 하며, `min_cases >= 2`일 경우 최소 1개 이상의 hidden 또는 edge 케이스가 동반 생성되도록 규정합니다.
    - 테스트케이스의 `input_data`와 `expected_output`은 AI가 파싱하고 백엔드가 실행하기 편리하도록 줄바꿈과 띄어쓰기로 이루어진 가공되지 않은 생 문자열(raw testcase string)로 렌더링됩니다.

*   **사용 예시**:
    ```python
    from agent.chains.testcase_generation import generate_testcases

    # problem: GeneratedProblem 인스턴스
    testcase_bundle = generate_testcases(problem, min_cases=5)
    print(f"생성된 테스트케이스 총 개수: {len(testcase_bundle.testcases)}")
    ```

---

### 2.3 generate_hints

*   **임포트 경로**:
    ```python
    from agent.chains.hint_generation import generate_hints
    ```
*   **함수 서명**:
    ```python
    def generate_hints(
        problem: GeneratedProblem,
        allowed_level: int = 3,
        user_situation: str | None = None
    ) -> HintBundle:
    ```
*   **상세 설명**:
    - `GeneratedProblem` 내부의 `HintBlueprint` 및 RAG 힌트 지침서를 연동하여 학습자의 학습 단계에 최적화된 힌트를 단계별로 빌드합니다.
    - `allowed_level` (1 ~ 3) 인자를 기반으로, 반환값 필터링 및 RAG 색인(Index)에 주입될 단계를 강제 통제합니다. (Level 1: 방향성 가이드, Level 2: 알고리즘 설계적 접근법, Level 3: 구현을 돕는 주석 포함 스켈레톤 코드)
    - 정답 소스 코드를 완전히 유출하는 것은 금지되며, Level 3에서도 빈칸(`...`, `# TODO`, `pass`)이 뚫린 불완전한 소스 스켈레톤(`code_skeleton`) 구조만 허용됩니다.
    - 에이전트는 내부적으로 `reveals_core_code == True`인 힌트를 완전 걸러내고 안전 검증을 마친 후 RAG에 색인 처리하여 저장합니다.

*   **사용 예시**:
    ```python
    from agent.chains.hint_generation import generate_hints

    # problem: GeneratedProblem 인스턴스
    # 2단계(알고리즘 설계)까지만 노출하도록 제한
    hint_bundle = generate_hints(
        problem=problem,
        allowed_level=2,
        user_situation="인덱스 조절에서 무한 루프가 발생합니다."
    )
    for hint in hint_bundle.hints:
        print(f"[Level {hint.level}] {hint.title}: {hint.content}")
    ```

---

## 3. 에이전트 노드 및 워크플로우 API (Agent Nodes & Workflow API)

`packages/agent/nodes` 패키지는 문제 생성, 테스트케이스 생성, 힌트 생성 체인 주위에 데이터 흐름을 정의하고 이를 결정론적으로 검증할 수 있는 가벼운 에이전트 노드(Agent Node) 레이어 및 오케스트레이션 러너를 제공합니다. 이 노드들은 추후 LangGraph 그래프 컴포넌트나 FastAPI 라우터 내에서 상태 관리 단위로 활용될 수 있도록 설계되었습니다.

### 3.1 AgentState (에이전트 상태 구조)
*   **임포트 경로**:
    ```python
    from agent.nodes import AgentState
    ```
*   **구조**: `TypedDict` 기반의 가벼운 상태 모델로, 노드 간 데이터 공유를 제어합니다.
*   **속성**:
    - `generation_input` (`ProblemGenerationInput`): 문제 생성용 사용자 입력 조건.
    - `generated_problem` (`GeneratedProblem`): 생성된 문제 명세.
    - `testcase_bundle` (`TestcaseBundle`): 생성된 테스트케이스 모음.
    - `hint_bundle` (`HintBundle`): 생성된 단계별 힌트 모음.
    - `validation_report` (`ValidationReport`): 검증 결과 보고서.
    - `min_cases` (`int`): 테스트케이스 최소 수 (기본값: 5).
    - `allowed_hint_level` (`int`): 최대 허용 힌트 레벨 (기본값: 3).
    - `user_situation` (`str`): 사용자 질문/상황 정보.
    - `errors` (`list[str]`): 에러 리스트.
    - `metadata` (`dict[str, Any]`): 메타데이터.

### 3.2 generate_problem_node
*   **임포트 경로**:
    ```python
    from agent.nodes import generate_problem_node
    ```
*   **상세 설명**:
    - `AgentState` 내의 `generation_input`을 기반으로 `generate_problem()`을 호출하여 문제를 생성합니다.
    - 생성 결과는 상태 내의 `generated_problem` 필드에 저장되며, 다른 필드는 보존됩니다.

### 3.3 generate_testcases_node
*   **임포트 경로**:
    ```python
    from agent.nodes import generate_testcases_node
    ```
*   **상세 설명**:
    - `AgentState` 내의 `generated_problem`을 기반으로 `generate_testcases()`를 호출하여 테스트케이스를 생성합니다.
    - `min_cases` 옵션을 반영하여 생성을 처리하며, MVP 결정론적 생성을 보장하기 위해 노드 내부적으로는 실험적 LLM 대체 경로를 명시적으로 차단합니다.
    - 생성 결과는 `testcase_bundle` 필드에 기록됩니다.

### 3.4 generate_hints_node
*   **임포트 경로**:
    ```python
    from agent.nodes import generate_hints_node
    ```
*   **상세 설명**:
    - `AgentState` 내의 `generated_problem`을 읽고 `generate_hints()`를 호출하여 단계별 힌트를 빌드합니다.
    - `allowed_hint_level` 및 `user_situation` 조건을 인수로 주입하여 힌트 생성을 조율합니다.
    - 생성 결과는 `hint_bundle` 필드에 저장됩니다.

### 3.5 validate_outputs_node
*   **임포트 경로**:
    ```python
    from agent.nodes import validate_outputs_node
    ```
*   **상세 설명**:
    - 상태 내의 `generated_problem`, `testcase_bundle`(선택), `hint_bundle`(선택) 데이터를 읽어 검증 보고서(`validation_report`)를 빌드하는 결정론적 검증 노드입니다.
    - 내부적으로 어떠한 외부 LLM 호출 없이 오직 Python 기반의 결정론적 검증 코드만 수행하므로 빠르고 독립적인 일관성 검사가 보장됩니다.
    - 검증 과정에서 문제 기본 필드 검사, 각 제약 조건에 대한 테스트케이스 매핑/해결사(Solver) 유효성 평가, 힌트 보안 정책 위반 여부 등을 일체 확인하여 결과를 `validation_report` 필드에 갱신합니다.

### 3.6 run_package_workflow
*   **임포트 경로**:
    ```python
    from agent.nodes import run_package_workflow
    ```
*   **함수 서명**:
    ```python
    def run_package_workflow(
        generation_input: ProblemGenerationInput,
        min_cases: int = 5,
        allowed_hint_level: int = 3,
        user_situation: str | None = None,
        include_hints: bool = True,
    ) -> AgentState:
    ```
*   **상세 설명**:
    - 순수 Python 코드로 문제 생성 -> 테스트케이스 생성 -> (선택적) 힌트 생성 -> 검증 노드를 일괄적으로 실행해 주는 간이 패키지 오케스트레이션 워크플로우 헬퍼 함수입니다.
    - 최종 검증 완료 상태가 포함된 `AgentState` 인스턴스를 반환합니다.

### 3.7 generate_feedback_node
*   **임포트 경로**:
    ```python
    from agent.nodes import generate_feedback_node
    ```
*   **상세 설명**:
    - `AgentState` 내의 `generated_problem`과 `submission_result`를 기반으로 `FeedbackReport`를 생성하여 상태의 `feedback_report` 필드에 저장합니다.

### 3.8 run_feedback_workflow
*   **임포트 경로**:
    ```python
    from agent.nodes import run_feedback_workflow
    ```
*   **함수 서명**:
    ```python
    def run_feedback_workflow(
        problem: GeneratedProblem,
        submission_result: SubmissionResult,
    ) -> AgentState:
    ```
*   **상세 설명**:
    - 문제 명세와 채점 제출 결과를 받아 피드백 분석 노드(`generate_feedback_node`)를 일괄 실행하고 최종 에이전트 상태를 반환하는 간이 오케스트레이션 러너입니다.

### 3.9 제출 피드백 개념 및 정책 (Submission Feedback Policy)
*   **결정론적 피드백 기본 작동 (Deterministic Feedback by Default)**:
    - 외부 LLM의 호출 없이 제출 결과 유형(`result_type` 예: `WA`, `TLE`, `RE`, `MLE`, `CE` 등)과 문제 복잡도 메타데이터를 사용하여 100% 로컬 결정론적으로 원인 분석(`likely_causes`) 및 개선 조치 단계(`next_steps`)를 한글로 구성합니다.
*   **정답 소스 코드 유출 차단 (No Full Solution Code Policy)**:
    - 피드백 내용에 학습을 저해하는 완전한 형태의 솔루션 코드가 포함되지 않도록 원천 통제합니다. 스키마 validator 레벨에서 이를 스캔하여 안전하지 않다고 판단되면 `safe_to_show` 값을 `False`로 낮춰 출력 차단을 유도합니다.
*   **LLM 피드백 연동 제한**:
    - 대형 언어 모델(LLM)을 활용한 개인화 맞춤형 피드백 생성은 기본 비활성화 상태이며, 향후 기능 확장 시 명시적인 플래그 옵트인(`prefer_llm=True`) 방식으로만 활성화될 수 있습니다.

### 3.10 route_next_action_node
*   **임포트 경로**:
    ```python
    from agent.nodes import route_next_action_node
    ```
*   **상세 설명**:
    - `AgentState` 내의 `validation_report` 및 `feedback_report` 필드를 순차적으로 확인하여 다음 워크플로우 수행 경로(`RoutingDecision`)를 판정합니다.
    - 판정된 경로는 `routing_decision` 상태 필드에 기록됩니다.

### 3.11 decide_next_action
*   **임포트 경로**:
    ```python
    from agent.nodes import decide_next_action
    ```
*   **함수 서명**:
    ```python
    def decide_next_action(
        validation_report: ValidationReport | None = None,
        feedback_report: FeedbackReport | None = None,
    ) -> RoutingDecision:
    ```
*   **상세 설명**:
    - 제공된 검증 보고서 및 피드백 보고서를 기반으로 로직 분기를 실행합니다.
    - 피드백 내용에 솔루션 유출이 발생할 경우 검증 성공 여부와 상관없이 무조건 `block_output` 결정을 내리므로, 보안 검문소(Security checkpoint) 우선순위가 보장됩니다.

### 3.12 품질 게이트 / 라우팅 정책 (Quality Gate / Routing Policy)
*   **결정론적 라우팅 제어 (Deterministic Routing)**:
    - 외부 LLM의 추론에 의존하지 않고 로컬의 명확한 정책 규칙 목록을 따릅니다. 향후 LangGraph 결합 시 조건부 엣지(Conditional Edge) 탐색을 위해 완벽한 오프라인 분기를 정의합니다.
*   **분기 액션 목록**:
    - `present_to_user`: 모든 정상 검증 통과 완료 시 사용자에게 렌더링하도록 승인.
    - `regenerate_problem`: 문제 설명(Problem description) 누락/포맷 오류 시 문제 재생성.
    - `regenerate_testcases`: 테스트케이스 정답 불일치 또는 빌더 예외 시 테스트케이스 재생성.
    - `revise_hints`: 힌트 가이드 결여 및 Level 3 코드 누출 감지 시 힌트 부분 수정 요청.
    - `request_human_review`: 지원하지 않는 유형이거나 예외 처리 불가능한 복합 에러 발생 시 인간 운영자 검토 요청.
    - `show_feedback`: 제출 분석 피드백 안전성 통과.
    - `block_output`: 제출 피드백 내부 정해 노출 등으로 인한 출력 제한.
*   **안전성 차단 우선 (Feedback Safety Priority)**:
    - 피드백 내용에서 풀이 코드가 유출되어 출력이 차단될 시 (`safe_to_show == False`), `safe_to_continue` 플래그는 항상 `False`로 강제 고정됩니다.

### 3.13 evaluate_submission_node
*   **임포트 경로**:
    ```python
    from agent.nodes import evaluate_submission_node
    ```
*   **상세 설명**:
    - `AgentState` 내의 `generated_problem`과 `testcase_run_results`를 읽어 각 테스트케이스별 결과 분석 및 제출 결과 원인 평가를 집계합니다.
    - 결과는 `submission_evaluation_report` 및 `submission_result` 필드에 나누어 기록됩니다.

### 3.14 run_submission_review_workflow
*   **임포트 경로**:
    ```python
    from agent.nodes import run_submission_review_workflow
    ```
*   **함수 서명**:
    ```python
    def run_submission_review_workflow(
        problem: GeneratedProblem,
        testcase_run_results: list[TestcaseRunResult],
        user_code: str | None = None,
        language: str | None = None,
    ) -> AgentState:
    ```
*   **상세 설명**:
    - 외부 채점 엔진(예: Judge0)이 보낸 각 테스트케이스 개별 실행 결과를 받아 `평가 집계 -> 피드백 생성 -> 라우팅 분기` 노드들을 순차 수행하는 제출 평가 전용 오케스트레이션 러너입니다.

### 3.15 채점 결과 및 제출 평가 정책 (Judge Adapter / Submission Evaluation Policy)
*   **무설치 오프라인 어댑터 (Pure Offline Adapter)**:
    - 본 컴포넌트는 사용자의 코드를 실제로 가상 머신이나 도커 내에서 빌드/실행하지 않는 안전한 순수 데이터 어댑터입니다. 외부 채점 엔진에 의해 측정 완료된 원시 실행 명세(`TestcaseRunResult`)를 전달받아 통계화하기만 합니다.
*   **출력 문자열의 일관된 비교 (Whitespace and Line-ending Normalization)**:
    - 기대 출력과 실제 출력의 개행 문자 차이(CRLF/LF) 및 끝부분 무의미한 개행을 자동 무시하는 `normalize_output()` 처리를 적용하여 `AC` 판단률의 안정성을 높입니다.
    - 또한 모든 내부 공백/개행을 단일 공백으로 치환하여 비교하는 `whitespace_normalize_output()`을 이용해 프레젠테이션 공백 에러(`PE`)를 똑똑하게 구분합니다.
*   **오답 상태 수렴 우선순위 (Priority-based Aggregation)**:
    - 전체 테스트케이스에 컴파일 에러(`CE`)가 포함될 경우 최종 상태는 컴파일 에러로 간주됩니다.
    - 기타의 경우 index 순서대로 탐색하여 `WA`, `TLE`, `RE`, `MLE` 오답이 나타나면 이를 대표 상태로 집계하며, 출력 공백 불일치(`PE`)는 가장 낮은 우선순위로 집계되어 오판을 사전에 방지합니다.

---

## 4. 스키마 참조 (Schema Reference)

퍼블릭 스키마 모델들은 [schemas.py](./schemas.py)에 정의되어 있습니다.

### 4.1 ProblemGenerationInput
*   **목적**: 문제 생성 요청을 보낼 때 주입되는 프롬프트 파라미터.
*   **핵심 필드**:
    - `algorithm` (str): 이분 탐색, BFS 등 핵심 알고리즘.
    - `difficulty` (Literal["easy", "medium", "hard"]): 난이도.
    - `problem_style` (str): 실무형, 대회형 등 스타일.
    - `language` (str): 학습자의 프로그래밍 언어 (Python, Java 등).
    - `learning_goal` (str): 이번 학습의 주요 목표 텍스트.
    - `user_level` (str): 사용자 등급 및 수준.
    - `recent_weaknesses` (List[str]): 사용자의 최근 오답 취약 지표 목록.
*   **JSON 예시**:
    ```json
    {
      "algorithm": "binary_search",
      "difficulty": "medium",
      "problem_style": "practical",
      "language": "Python",
      "learning_goal": "매개변수 탐색 구현",
      "user_level": "중급",
      "recent_weaknesses": ["경계 조건 인덱스 에러"]
    }
    ```

### 4.2 GeneratedProblem
*   **목적**: 생성 완료된 코딩테스트 문제 정보 패키지.
*   **핵심 필드**:
    - `problem_id` (str): 고유 아이디.
    - `title` (str): 한국어 문제 제목.
    - `statement` (str): 한국어 본문 설명.
    - `input_format` / `output_format` (str): 입력/출력 텍스트 설명.
    - `constraints` (List[str]): 제한 조건 배열.
    - `sample_input` / `sample_output` (str): 예제 케이스.
    - `hint_blueprint` (HintBlueprint): 문제와 1대1로 보관되는 내부 힌트 생성 설계 정보.

### 4.3 HintBlueprint
*   **목적**: 해당 문제의 힌트를 일관되게 생성하기 위한 안전 장치 메타데이터.
*   **핵심 필드**:
    - `intended_algorithm` (List[str]): 의도된 정해 알고리즘.
    - `core_insight` (str): 문제 해결의 핵심 열쇠.
    - `level_1_guidance` ~ `level_3_guidance` (str): 단계별 가이드라인.
    - `forbidden_disclosures` (List[str]): 힌트에 절대로 포함되어선 안 되는 금지 정보.
    - `allowed_code_exposure` (str): 코드 노출 허용 등급.

### 4.4 GeneratedTestcase
*   **목적**: 단일 테스트케이스 규격.
*   **핵심 필드**:
    - `name` (str): 테스트케이스 구분 명칭.
    - `input_data` (str): 채점 엔진(Judge0 등)에 주입할 표준 입력 원본.
    - `expected_output` (str): 채점 기대 출력 문자열.
    - `visibility` (Literal["sample", "hidden", "edge"]): 공개 등급.
    - `purpose` (str): 해당 테스트케이스를 기획한 설계 목적.

### 4.5 TestcaseBundle
*   **목적**: 한 문제에 종속된 테스트케이스들의 컬렉션 패키지.
*   **핵심 필드**:
    - `problem_id` (str): 관련 문제 번호.
    - `testcases` (List[GeneratedTestcase]): 테스트케이스 목록.
    - `generation_notes` (str): 생성 시 작성된 부가 설명 또는 노트.
    - `generation_mode` (Optional[str]): 테스트케이스 생성 모드 (예: `"deterministic"` 또는 `"llm"`).
    - `generator_name` (Optional[str]): 사용된 구체적인 생성기 이름 (예: `"budget_cap"`).
    - `verification_status` (Optional[str]): 테스트케이스 검증 상태 (예: `"passed"` 또는 `"experimental"`).

### 4.6 Hint
*   **목적**: 사용자에게 점진적으로 해금될 학습 보조용 힌트 카드 객체.
*   **핵심 필드**:
    - `level` (int): 1, 2, 3단계 레벨.
    - `title` / `content` (str): 한국어로 작성된 힌트 메시지.
    - `code_skeleton` (Optional[str]): Level 3에서만 허용되는 빈칸 채우기용 일부 소스 코드.
    - `reveals_core_code` (bool): 힌트가 핵심 풀이 코드를 노출하는지 여부 (항상 `False`이어야 함).

### 4.7 HintBundle
*   **목적**: 생성 및 RAG 저장용 힌트 묶음 객체.
*   **핵심 필드**:
    - `problem_id` (str): 대상 문제 번호.
    - `blueprint` (HintBlueprint): 참조된 힌트 설계서.
    - `hints` (List[Hint]): `allowed_level` 이하의 검증된 힌트 목록.

### 4.8 SubmissionResult
*   **목적**: 학습자의 코드 제출 채점 결과 세부 명세.
*   **핵심 필드**:
    - `problem_id` (str): 대상 문제 번호.
    - `result_type` (Literal["AC", "WA", "TLE", "RE", "MLE", "CE", "PE", "UNKNOWN"]): 채점 결과 유형.
    - `user_code` (Optional[str]): 학습자가 제출한 소스 코드 원본.
    - `failed_testcase_name` (Optional[str]): 실패한 테스트케이스 식별자.
    - `failed_input` (Optional[str]): 실패한 테스트케이스 입력.
    - `expected_output` (Optional[str]): 실패한 케이스의 기대 출력.
    - `actual_output` (Optional[str]): 실패한 케이스의 실제 출력.

### 4.9 FeedbackReport
*   **목적**: 제출 결과를 정밀 분석하여 피드백 노드가 빌드한 최적화 피드백 보고서.
*   **핵심 필드**:
    - `problem_id` (str): 대상 문제 번호.
    - `result_type` (str): 제출 결과 유형 복사본.
    - `summary` (str): 한국어로 작성된 분석 요약문.
    - `likely_causes` (List[str]): 오답의 예상 원인 후보 목록.
    - `next_steps` (List[str]): 오답 극복을 위해 추천되는 학습 행동 단계.
    - `allowed_hint_level` (int): 본 오답 결과를 극복하기 위해 추천되는 최대 힌트 해금 레벨.
    - `safe_to_show` (bool): 보안성 안전 여부 지표 (풀이 코드가 유출되면 `False`).
    - `generated_by` (Literal["deterministic", "llm"]): 피드백 생성 주체.

### 4.10 RoutingDecision
*   **목적**: 검증 및 제출 피드백 결과에 입각해 다음 조치 방향을 정의하는 라우팅 판단 규격.
*   **핵심 필드**:
    - `action` (Literal): 다음으로 이동할 컴포넌트 행동 명칭 (`present_to_user`, `regenerate_problem`, `regenerate_testcases`, `revise_hints`, `request_human_review`, `show_feedback`, `block_output`).
    - `reason` (str): 해당 분기를 내린 구체적인 원인 메시지.
    - `confidence` (Literal["low", "medium", "high"]): 라우팅 판정의 신뢰 확률.
    - `blocking_issue_codes` (List[str]): 조치를 지연시킨 세부 유효성 에러 코드 리스트.
    - `safe_to_continue` (bool): 워크플로우 진행 가능 여부 지표 (차단 시 `False`).

### 4.11 TestcaseRunResult
*   **목적**: 외부 채점기(Judge0 등)로부터 온 테스트케이스별 개별 실행 결과 데이터 규격.
*   **핵심 필드**:
    - `testcase_name` (str): 테스트케이스 구분 명칭.
    - `status` (Literal): 개별 채점 판정 결과 (`AC`, `WA`, `TLE`, `RE`, `MLE`, `CE`, `PE`, `UNKNOWN`).
    - `input_data` / `expected_output` (Optional[str]): 해당 케이스의 입력 정보 및 기대 정답.
    - `actual_output` (Optional[str]): 학습자의 실제 콘솔/파일 출력값.
    - `execution_time_ms` / `memory_kb` (Optional[int]): 실행 시간 및 메모리 점유율 지표.

### 4.12 SubmissionEvaluationReport
*   **목적**: 제출된 테스트케이스 실행 기록 전체를 집계한 성적 보고서 규격.
*   **핵심 필드**:
    - `problem_id` (str): 대상 문제 번호.
    - `result_type` (Literal): 최종 채점 수렴 판정.
    - `testcase_results` (List[TestcaseRunResult]): 개별 테스트케이스 결과 리스트.
    - `total_count` (int): 전체 테스트케이스 수.
    - `passed_count` (int): 정답(`AC`) 판정을 받은 테스트케이스 수.
    - `first_failed_testcase_name` (Optional[str]): 최초로 실패한 테스트케이스 이름.
    - `summary` (str): 집계 결과를 설명하는 한글 안내 메시지.

---

## 5. 종단간 사용 시나리오 (End-to-End Usage)

```python
from agent.schemas import ProblemGenerationInput
from agent.chains.problem_generation import generate_problem
from agent.chains.testcase_generation import generate_testcases
from agent.chains.hint_generation import generate_hints

# 1. 문제 생성 요청 파라미터 세팅
input_data = ProblemGenerationInput(
    algorithm="binary_search",
    difficulty="medium",
    problem_style="practical",
    language="Python",
    learning_goal="파라메트릭 서치와 단조 조건 기반 결정 문제 연습",
    user_level="중급",
    recent_weaknesses=["off_by_one", "time_complexity"],
)

# 2. 문제 생성
problem = generate_problem(input_data)

# 3. 테스트케이스 세트 생성 (최소 5개 세트 강제)
testcases = generate_testcases(problem, min_cases=5)

# 4. 힌트 세트 생성 (2단계인 알고리즘 설계 힌트까지만 노출 및 필터링)
hints = generate_hints(
    problem=problem, 
    allowed_level=2, 
    user_situation="예제는 맞지만 경계 조건에서 틀립니다."
)

# 5. 확인 출력
print(f"제목: {problem.title}")
print(f"생성된 테스트케이스 수: {len(testcases.testcases)}")
print(f"생성된 힌트 수: {len(hints.hints)}")
```

---

## 6. 다국어 지원 정책 (Output Language Policy)

*   **JSON Keys (스키마 속성)**: Pydantic 객체의 구조화와 API 명세 자동화를 위하여 영어 알파벳 카멜케이스 혹은 스네이크케이스를 일관되게 유지합니다.
*   **사용자 콘텐츠 (User-facing content)**: 문제 제목, 본문, 입출력 포맷, 제한 조건, 테스트케이스 명칭, 기획 목적, 힌트 카드 제목 및 설명문 등의 텍스트는 **기본적으로 한국어(Ko)**로 자동 출력됩니다.
*   **표준 스펙 및 메타데이터**: 단, 프로그래밍 언어명(Python, Java 등), 핵심 알고리즘 키워드(binary_search, bfs 등), 복잡도 표현(Big-O) 및 실제 테스트케이스의 입출력 데이터 스트림(`input_data`, `expected_output`)은 표준 기호 및 영어 기법을 유지합니다.

---

## 7. 에이전트 보안 및 검증 정책 (Safety & Security Policy)

1.  **정답 코드 노출 차단**: 힌트 데이터베이스나 LLM 생성문 내에 컴파일 가능한 전체 정답 정해 코드를 포함하지 못하도록 규칙을 제어합니다.
2.  **RAG 필터링 및 승급 제어**: RAG 단에서 사용자의 챗봇 쿼리 입력 시 현재 세션 등급인 `allowed_level`을 엄밀히 체크하여 상위 레벨의 힌트 색인을 물리적으로 조절합니다.
3.  **내부 설계 가이드라인 보호**: `HintBlueprint`는 힌트 생성을 조율하기 위한 내부 가이드라인이며, 일반 사용자에게 반환되는 UI에는 노출되지 않도록 상위 인터페이스 개발 시 주의해야 합니다.
4.  **불완전 스켈레톤 통제**: 코드 힌트 작성 시 반드시 `TODO`, `...`, `pass` 등의 미완성 영역 키워드를 포함해야만 스키마 검증기(Pydantic Validator)를 통과하여 서비스에 등록됩니다.

---

## 8. 환경 및 런타임 정보 (Environment / Runtime Notes)

*   **API Credentials**: 실제 LLM 생성 체인 작동을 위해서는 로컬 `.env` 혹은 환경변수에 `OPENAI_API_KEY` (그리고 필요 시 `ANTHROPIC_API_KEY`)가 안전하게 구성되어야 합니다.
*   **Embedding & Vector DB**: 임베딩 파이프라인은 OpenAI 모델을 기반으로 동작하며, 힌트 색인을 위해서는 Qdrant DB 연동이 필요합니다.
*   **로컬 및 단위 테스트 모드**:
    테스트 러너 환경(`ENV=test` 혹은 `USE_FAKE_EMBEDDINGS=true`) 내에서는 실제 API 통신 및 DB 연결 없이 메모리상의 임시 `InMemoryVectorStore`와 `FakeStructuredChatModel`을 활성화하여 **완벽한 오프라인 격리 검증**을 보장합니다.

---

## 9. 현재 설계상의 제한 사항 (Current Limitations)

*   **코드 실행 및 검증 불가**: 본 패키지는 소스 코드의 컴파일 가능 여부 및 채점을 직접 다루지 않습니다. 격리 샌드박스 컴파일러(Judge0) 연동 및 테스트 통과 판정은 향후 백엔드 파이프라인 개발 범위에 속합니다.
*   **생성 테스트케이스 무오성**: 생성된 테스트케이스 데이터셋은 AI 모델 기반의 추론 결과물입니다. 따라서, 로직 에러 방지를 위해 실제 사용 전 백엔드 채점 엔진 내부의 레퍼런스 솔루션 정답 검증(Reference solver execution validation) 코드를 통과시켜 사전 오류 필터링을 권장합니다.
