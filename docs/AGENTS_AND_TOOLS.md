# Agent & Tool 사양

CodeMaker Coach Agent를 구성하는 `packages/agent`의 실제 코드 구조를 정의한다.
기획 문서 6·7·12·13장의 개념(Agent="한 단계의 처리 노드", Tool="외부 자원 클라이언트")을
아래 실제 파일 구조에 매핑한다.

> **중요**: `packages/agent`는 LangGraph `StateGraph`가 아니다. `packages/agent/nodes/workflow.py`의
> 러너 함수가 아래 Node들을 정해진 순서로 호출하는 **결정론적 파이프라인**이며, 조건 분기는
> Python 조건문(라우팅 노드)으로 구현된다. 자세한 공개 API는 `packages/agent/API.md` 참조.

---

## 1. Agent = Node (`packages/agent/nodes/`)

각 Agent는 `AgentState`(TypedDict)를 입력받아 특정 필드를 채워 반환하는 순수 함수다.

| 파일 | Node | 역할 |
|---|---|---|
| `problem_generation_node.py` | `generate_problem_node` | `generate_problem()` 체인 호출 → `generated_problem` 채움 |
| `testcase_generation_node.py` | `generate_testcases_node` | `generate_testcases()` 호출 → `testcase_bundle` 채움 (실험적 LLM 폴백 차단) |
| `reference_solver_node.py` | (내부 헬퍼) | 결정론적 레퍼런스 솔버(`reference_solvers/registry.py`) 실행 + Judge0로 실제 실행 검증 |
| `hint_generation_node.py` | `generate_hints_node` | `generate_hints()` 호출 → `hint_bundle` 채움 |
| `validation_node.py` | `validate_outputs_node` | LLM 호출 없이 문제/테스트케이스/힌트 정합성을 순수 Python으로 검증 → `validation_report` |
| `routing_node.py` | `route_next_action_node`, `decide_next_action` | 검증·피드백 보고서를 보고 다음 액션(`present_to_user`/`regenerate_*`/`block_output`/`request_human_review` 등) 결정 |
| `submission_evaluation_node.py` | `evaluate_submission_node` | Judge0 testcase 실행 결과 집계 → `submission_evaluation_report`, `submission_result` |
| `error_diagnosis_node.py` | `diagnose_submission_node` | 오답 원인 패턴 감지(`WA_OFF_BY_ONE` 등) → `ErrorDiagnosis` |
| `failed_case_explanation_node.py` | `explain_failed_case_node` | 실패 케이스 한국어 설명 → `FailedCaseExplanation` |
| `complexity_analysis_node.py` | `analyze_complexity_node` | 소스 텍스트 패턴 분석으로 시간복잡도 추정 → `ComplexityAnalysis` |
| `counterexample_node.py` | `build_counterexample_node` | 반례 리포트 생성(정답 코드 비노출) → `CounterexampleReport` |
| `feedback_node.py` | `generate_feedback_node` | 위 리포트들을 종합해 `FeedbackReport` 생성 |
| `workflow.py` | `run_package_workflow`, `run_feedback_workflow`, `run_submission_review_workflow` | 위 Node들을 순서대로 실행하는 오케스트레이션 러너 |
| `state.py` | `AgentState` | 모든 Node가 공유하는 TypedDict 상태 |

> Problem Generator/Testcase Generator/Hint Generator는 문제 생성 시 **힌트까지 함께** 만들어
> 저장한다. 챗봇형 힌트 요청(풀이 중)은 즉석 생성이 아니라 **저장된 힌트를 허용 단계 이하로
> RAG 검색해 서빙**한다 — `services/hint_request_service.py` 참조 (REQUIREMENTS FR-5, FR-16).

### 1.1 신고 판정 Agent (HITL 사전 심사, ARCHITECTURE 7장)
문제 생성/채점 파이프라인과 별개로, 신고 누적 시에만 호출되는 독립적인 체인이다.

| 파일 | 역할 |
|---|---|
| `chains/problem_report_assessment.py` | `assess_problem_reports()` — 문제 본문 + 신고 사유들을 LLM에 넘겨 `severity`(critical/safe/minor) 구조화 출력 판정 |
| `services/problem_report_assessment_service.py` | `assess_problem_report_package()` — 위 체인을 비동기로 감싸고, LLM 호출/파싱이 실패하면 예외를 삼키고 항상 `severity="minor"`로 안전 폴백 |

---

## 2. Chain (LangChain, `packages/agent/chains/`)

LLM을 실제로 호출하는 계층. 모두 `with_structured_output()`으로 Pydantic 스키마를 강제한다.

| 파일 | 함수 | 역할 |
|---|---|---|
| `problem_generation.py` | `generate_problem` | 알고리즘·난이도 기반 신규 문제 생성 (`GeneratedProblem`, `HintBlueprint` 포함) |
| `testcase_generation.py` | `generate_testcases` | 결정론적 생성기가 없는 문제 타입에 한해 쓰이는 실험적 LLM 테스트케이스 생성 경로 |
| `hint_generation.py` | `generate_hints` | 문제 생성 시 1~3단계 힌트 생성 (핵심 코드 노출 필터 적용) |
| `feedback_generation.py` | (내부용) | LLM 기반 피드백 생성 경로 (기본은 결정론적 피드백, opt-in 시에만 사용) |
| `problem_report_assessment.py` | `assess_problem_reports` | 신고 누적 문제의 심각도 판정 (1.1 참조) |

---

## 3. 결정론적 생성기 레지스트리 (`reference_solvers/`, `testcase_generators/`)

문제 생성 시 LLM이 만든 문제 설명을 8종의 알려진 "문제 유형(archetype)"으로 인식하면, 테스트케이스와
정답 코드를 **LLM이 아닌 결정론적 Python 코드**로 만들어 100% 수학적 정확성을 보장한다
(`testcase_generators/base.py`의 `detect_problem_type()`으로 유형을 감지).

| 유형 (problem_type) | 설명 |
|---|---|
| `budget_cap` | 예산 상한액 파라메트릭 서치 |
| `two_pointer_subarray` | 합이 K 이하인 최장 연속 부분 배열 (투 포인터) |
| `bfs_grid_shortest_path` | N×M 격자 BFS 최단 경로 |
| `dfs_grid_components` | N×M 격자 DFS 연결 요소(섬) 개수 |
| `cable_cutting` | 랜선 자르기 (이분 탐색) |
| `router_installation` | 공유기 설치 최대-최소 거리 (이분 탐색) |
| `immigration_time` | 입국심사 최소 소요 시간 (이분 탐색) |
| `lower_bound_count` | 정렬 배열 lower bound 인덱스 탐색 |

- `reference_solvers/registry.py` — `generate_reference_solution(problem)`. 매핑된 유형이 없으면
  `UnsupportedReferenceSolverError`를 던진다.
- `testcase_generators/registry.py` — 위와 동일한 8종에 대해 `sample`/`hidden`/`edge` 테스트케이스를
  생성. 매핑이 없으면 `UnsupportedTestcaseGeneratorError` (단, `allow_experimental_llm_fallback=True`
  옵션 시 LLM 경로로 폴백 가능 — 실험적 기능).
- `variants.py` — `binary_search` 알고리즘 요청 시, `seed` 값을 해시해 위 5개 이분 탐색 계열
  variant(`budget_cap`/`cable_cutting`/`router_installation`/`immigration_time`/`lower_bound_count`)
  중 하나를 결정론적으로 선택한다 (`select_variant`). 같은 `seed`는 항상 같은 variant를 고르므로
  재현 가능하고, `seed`가 없으면 매번 새 UUID를 써서 다양성을 확보한다.

---

## 4. Tool (`packages/agent/tools/`)

| Tool | 역할 | 비고 |
|---|---|---|
| `retrieve_concepts.py` | RAG 알고리즘 개념 검색 (`packages/rag`) | Qdrant / InMemory fallback |
| `retrieve_hints.py` | 문제별 힌트 검색 **(허용 단계 이하로 제한)** | 단계 필터 필수 (FR-18) |
| `run_user_code.py` | `run_code(source_code, language, stdin, expected_output)` — Judge0 REST API 호출 후 결과 정규화 | `apps/api/app/judge_worker.py`와 `reference_solver_node.py` 양쪽에서 재사용하는 얇은 클라이언트 |

> `run_user_code.py`는 사용자 제출 채점과 레퍼런스 솔루션 검증에 **공용으로** 쓰인다. 별도의
> `run_reference_solution` 파일은 존재하지 않는다 — 3장의 결정론적 레지스트리가 코드를 생성하고,
> 이 Tool이 Judge0에서 실제로 실행해 결과 일치 여부를 검증한다.

---

## 5. Service (`packages/agent/services/`) — 백엔드가 실제로 호출하는 진입점

FastAPI(`app/gateway.py`의 `LiveAgentGateway`)는 개별 Node/Chain을 직접 조립하지 않고, 아래 4개
비동기 서비스 함수만 호출한다. 각 서비스는 여러 Node/Chain을 내부적으로 순서대로 실행하고, 실패
시 안전한 기본값으로 폴백한다.

| 파일 | 함수 | FastAPI 호출 지점 |
|---|---|---|
| `problem_generation_service.py` | `generate_problem_package` | `POST /api/problems/generate` |
| `hint_request_service.py` | `request_hint_package` | `POST /api/hints/request` |
| `submission_review_service.py` | `review_submission_package` | `POST /api/submissions/review` |
| `problem_report_assessment_service.py` | `assess_problem_report_package` | `POST /api/problems/{id}/report` (임계치 초과 시에만) |

---

## 6. 힌트 관련 정책 (요구사항 반영)

- 힌트 생성(`chains/hint_generation.py`): 힌트 생성 시 **전문/핵심 코드를 포함하지 않는지 필터
  검증** 후 저장한다. 최대 노출 = 구조/뼈대(skeleton). 핵심 로직 자리는 비워 사용자가 입력하게
  한다 (FR-19).
- 힌트 검색(`tools/retrieve_hints.py`, `services/hint_request_service.py`): 검색 범위를 항상
  `[1 .. allowed_level]`로 제한한다. 상위 단계 힌트는 **검색 결과에 포함되지 않는다** (FR-18, NFR-4).

---

## 7. 실제 코드 배치

```
packages/agent/
├── schemas.py              # 모든 Pydantic 모델 (GeneratedProblem, HintBundle, ProblemReportAssessment 등)
├── variants.py             # binary_search 계열 문제 variant 선택 (3장)
├── llm.py                  # get_chat_model() — LLM_PROVIDER(claude/openai) 스위칭 + FakeStructuredChatModel(테스트)
├── chains/                 # LLM 호출 체인 (2장)
│   ├── problem_generation.py
│   ├── testcase_generation.py
│   ├── hint_generation.py
│   ├── feedback_generation.py
│   └── problem_report_assessment.py
├── prompts/                # 각 chain의 PromptTemplate
├── nodes/                  # 결정론적 파이프라인 Node + 오케스트레이션 (1장)
│   ├── state.py
│   ├── workflow.py
│   ├── problem_generation_node.py
│   ├── testcase_generation_node.py
│   ├── reference_solver_node.py
│   ├── hint_generation_node.py
│   ├── validation_node.py
│   ├── routing_node.py
│   ├── submission_evaluation_node.py
│   ├── error_diagnosis_node.py
│   ├── failed_case_explanation_node.py
│   ├── complexity_analysis_node.py
│   ├── counterexample_node.py
│   └── feedback_node.py
├── reference_solvers/      # 결정론적 정답 코드 생성기 8종 + registry.py (3장)
├── testcase_generators/    # 결정론적 테스트케이스 생성기 8종 + base.py + registry.py (3장)
├── tools/                  # 외부 자원 클라이언트 (4장)
│   ├── retrieve_concepts.py
│   ├── retrieve_hints.py
│   └── run_user_code.py
└── services/                # 백엔드 진입점 (5장)
    ├── problem_generation_service.py
    ├── hint_request_service.py
    ├── submission_review_service.py
    └── problem_report_assessment_service.py
```
