# packages/agent — Agent 코어 패키지

웹/DB 및 기타 인프라에 직접 의존하지 않는 **독립 Python 패키지**. 문제 생성·검증,
채점 결과 오답 분석, 챗봇형 힌트 요청을 처리한다.

## API 문서 링크
자세한 Python API 명세 및 Pydantic 스키마 가이드는 [API.md](./API.md) 참고.

## 현재 구현 상태

- 오케스트레이션은 **결정론적 노드 순차 호출**(`nodes/workflow.py`)이다. 문서 전반에서
  "LangGraph"를 언급하지만, 실제 LangGraph `StateGraph` 조립은 아직 목표/확장 단계이며
  현재 코드는 아니다. `AgentState`(TypedDict, `nodes/state.py`)를 공유 상태로 쓰는
  일반 함수 파이프라인이다.
- 문제 유형은 결정론적으로 지원되는 8개 archetype 중심으로 테스트케이스/정답 코드가
  생성된다 (`testcase_generators/`, `reference_solvers/`): 비-이분탐색 3종
  (`two_pointer_subarray`, `bfs_grid_shortest_path`, `dfs_grid_components`) + `binary_search`
  알고리즘 요청 시 `variants.py`가 seed 해시로 고르는 5종(`budget_cap`, `cable_cutting`,
  `router_installation`, `immigration_time`, `lower_bound_count`). 지원하지 않는 유형은
  `UnsupportedTestcaseGeneratorError`/`UnsupportedReferenceSolverError`가 발생하고, 라우팅
  결정에 따라 재생성되거나 인간 검토 대상이 된다.
- 문제 생성/채점 파이프라인과 별개로, 문제 신고가 임계치 이상 누적되면
  `chains/problem_report_assessment.py` + `services/problem_report_assessment_service.py`가
  문제 본문과 신고 사유를 LLM으로 재판정해 `critical`/`safe`/`minor` 심각도를 매긴다
  (실패 시 항상 `minor`로 안전 폴백). 상세: `docs/ARCHITECTURE.md` 7장, API.md 3.23장.

## Public Service API (API 서버가 호출해야 하는 진입점)

`app.gateway.AgentGateway`는 아래 4개의 async 함수만 호출한다. API/Web 개발자는
`chains`/`nodes`를 직접 부르지 말고 이 레벨을 사용한다.

### `generate_problem_package(input: ProblemGenerationPackageInput) -> ProblemGenerationPackage`
RAG 검색 → 문제 생성 → 테스트케이스 생성 → reference solver(Judge0 검증) → 힌트 생성 →
검증 → 라우팅 결정까지 한 번에 수행한다. `problem_package_to_public_dict()`로 직렬화하면
`reference_solution`이 제거된 안전한 dict를 얻는다(`problem_package_to_internal_dict()`는
영속화용으로만 쓰고 API 응답에 그대로 노출하지 않는다).

### `request_hint_package(input: HintRequestPackageInput, generated_hints=...) -> HintRequestPackage`
챗봇형 힌트 요청. `allowed_level`을 반드시 호출자(API)가 DB의 `HintProgress`로 강제
설정해서 넘겨야 한다 — 이 함수는 요청측이 준 `allowed_level`을 신뢰한다. `requested_level >
allowed_level`이면 `blocked=True`와 함께 허용 단계 이하 힌트만 돌려준다. 호출자는
`generated_hints`로 넘기는 힌트 자체도 이미 `level <= allowed_level`로 필터링해서 넘기는
것이 안전하다(방어 깊이 — DB/RAG 조회 단계에서 상위 힌트를 아예 배제).

### `review_submission_package(problem, submission_result, include_concept_context=True) -> SubmissionReviewPackage`
채점 결과(AC/WA/TLE/RE/MLE)에 대해 오답 진단 → 실패 케이스 설명 → 복잡도 분석 →
반례 생성 → 피드백 요약까지 결정론적 규칙 기반으로 수행한다. `reference_solution`이나
정답 코드는 어떤 필드에도 포함되지 않는다.

### `assess_problem_report_package(input: ProblemReportAssessmentInput) -> ProblemReportAssessment`
문제 신고 누적 시(HITL 이전 사전 심사)에만 호출된다. LLM 호출/파싱이 실패해도 예외를
전파하지 않고 항상 `severity="minor"`로 안전 폴백한다. 상세: `docs/ARCHITECTURE.md` 7장.

## Lower-level Chains (직접 호출 지양)

`chains/problem_generation.py`, `chains/testcase_generation.py`, `chains/hint_generation.py`,
`chains/feedback_generation.py`는 서비스 API가 내부적으로 사용하는 단일 단계 함수다.
테스트/스크립트에서 개별 동작을 검증할 때만 직접 호출한다.

## Nodes Workflow

`nodes/workflow.py`의 `run_package_workflow`가 실제 오케스트레이션이다:

```
generate_problem_node → generate_testcases_node → generate_reference_solution_node
  → generate_hints_node → validate_outputs_node → route_next_action_node
```

`run_feedback_workflow`/`run_submission_review_workflow`도 유사하게 진단/설명/복잡도/반례
노드를 순차 호출한다. LangGraph 조건 분기 대신, `RoutingDecision.action`을 보고 **호출자
(API 라우터)가** 재시도 여부를 결정한다 (`apps/api/app/routers/problems.py`의
`_MAX_GENERATION_ATTEMPTS` 참조) — 즉 재생성 루프는 Agent 내부가 아니라 API 레이어에 있다.

## Schemas

`schemas.py`가 사실상 GraphState 겸 public 계약 역할을 한다. 핵심 타입:
`ProblemGenerationInput`, `GeneratedProblem`(+ `HintBlueprint`), `TestcaseBundle`,
`HintBundle`, `ReferenceSolution`, `ValidationReport`, `RoutingDecision`,
`SubmissionResult`/`SubmissionEvaluationReport`, `ErrorDiagnosis`,
`FailedCaseExplanation`, `ComplexityAnalysis`, `CounterexampleReport`, `FeedbackReport`.

## Safety Policies (Pydantic validator 수준에서 강제)

- `Hint.reveals_core_code`는 `False`가 아니면 즉시 `ValidationError`.
- `Hint.code_skeleton`은 placeholder(`...`, `TODO`, `구현` 등)가 없으면 거부되어
  "완성된 코드가 스켈레톤으로 위장"하는 것을 막는다.
- `FeedbackReport`는 `summary`/`likely_causes`/`next_steps`에 완성된 코드로 보이는
  패턴이 감지되면 `safe_to_show=False`로 강제 전환된다.
- `RoutingDecision`은 `action="block_output"`이면 반드시 `safe_to_continue=False`여야
  하고, `blocking_issue_codes`가 있으면 `action="present_to_user"`가 될 수 없다.

## Testcase / Reference Solver Registry

`testcase_generators/base.py`의 `detect_problem_type()`이 문제 유형을 감지하고,
`testcase_generators/registry.py` / `reference_solvers/registry.py`가 해당 유형의
결정론적 생성기를 찾는다. 정답 코드는 테스트케이스를 만들 때 쓴 것과 **동일한 solve_*()
로직**을 독립 실행 스크립트로 옮긴 것이며, `nodes/reference_solver_node.py`가 Judge0로
실제 실행 검증까지 한다(`ENV=test`/`AGENT_MODE=stub`에서는 네트워크 호출을 생략하고
`verified=True`로 표시). 검증 실패는 `ValidationReport`의
`REFERENCE_SOLUTION_UNVERIFIED` 이슈로 이어져 재생성 라우팅을 유발한다.

## Stub/Test Mode

- `agent.llm.get_chat_model()`/`get_embedding_model()`은 `ENV=test` 또는
  `USE_FAKE_EMBEDDINGS=true`일 때 실제 LLM 호출 없이 fake 모델을 반환한다.
- `nodes/reference_solver_node.py`는 같은 조건에서 Judge0 실행을 생략한다.
- `rag/vectorstore.py`는 Qdrant 연결 실패 시 in-memory fallback으로 조용히 전환한다.
- `packages/graphrag`는 Neo4j 미설정/연결 실패 시 mock/no-op으로 동작해 오프라인
  환경에서도 예외를 던지지 않는다.

이 fallback들은 로컬 개발에는 유용하지만, 운영 환경에서 필수 설정이 누락됐을 때도
조용히 fallback으로 넘어가면 장애를 늦게 발견하게 된다. 현재는 `apps/api/app/auth.py`의
`JWT_SECRET_KEY`만 누락 시 기동을 거부(fail-fast)하고, 나머지(LLM 키, Judge0, Qdrant,
Neo4j)는 로그만 남기고 fallback으로 넘어간다.

## Known Gaps

- **`AgentGateway.analyze_feedback`(`apps/api/app/gateway.py`)는 `LiveAgentGateway`에서도
  stub을 반환한다** — `generate_feedback` chain이 없기 때문. 실제 오답 리뷰는
  `review_submission_package`(`/api/submissions/review`)가 담당하며 이건 결정론적으로
  완전히 구현되어 있다. "오답 분석이 미구현"이 아니라 "gateway의 이 메서드 하나가
  미연결"이라는 뜻이다.
- LangGraph `StateGraph`는 아직 조립되지 않았다(위 참조).
- 결정론적 문제 유형이 아닌 경우(`detect_problem_type` → `unsupported`) 테스트케이스/
  정답 생성이 모두 실패하며, 현재는 `request_human_review` 라우팅으로만 이어진다 — LLM
  기반 일반 문제 생성으로의 완전한 확장은 아직 없다.
