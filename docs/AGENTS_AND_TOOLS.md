# Agent & Tool 사양

CodeMaker Coach Agent를 구성하는 **Agent(LangGraph Node)** 와 **Tool(LangChain)** 을 정의한다.
기획 문서 6·7·12·13장을 코드 구조(`packages/agent/`)에 매핑한다.

---

## 1. Agent = LangGraph Node

각 Agent는 `packages/agent/nodes/`의 하나의 Node로 구현된다.

| Agent | 역할 | 입력 | 출력 | MVP |
|---|---|---|---|:---:|
| **Problem Generator** | 알고리즘·난이도 기반 새 문제 생성 + **힌트 1~3단계 동시 생성** | 유형, 난이도, 스타일, 언어, (약점) | 문제 JSON + 힌트 | ✅ |
| **Testcase Generator** | sample / hidden / edge 테스트케이스 생성 | 문제 | 테스트케이스 목록 | ✅ |
| **Reference Solver** | 내부 검증용 정답 코드 생성 (비공개) | 문제 | reference solution | ✅ |
| **Validator** | 예제 출력·조건·난이도·복잡도 검증, 실패 시 재생성 신호 | 문제 + 정답 + 테스트케이스 | pass/fail + 사유 | ✅ |
| **Feedback / Hints** | 채점 결과 기반 오답 분석 + 챗봇형 단계 힌트 제공 | 제출 결과, 허용 힌트 단계, RAG 결과 | 분석 + 힌트 | ✅ |

> Problem Generator가 힌트를 **문제 생성 시 함께 만들어 저장**한다. Feedback/Hints Agent는 즉석 생성이 아니라
> 저장된 힌트를 **허용 단계 범위 내에서 RAG로 검색**해 응답한다. (REQUIREMENTS FR-5, FR-16)

---

## 2. Tool (LangChain, `packages/agent/tools/`)

기획 13장 Tool 목록.

| Tool | 역할 | 비고 |
|---|---|---|
| `retrieve_concepts` | RAG 알고리즘 개념 검색 | Vector DB |
| `retrieve_hints` | 문제별 힌트 검색 **(허용 단계 이하로 제한)** | 단계 필터 필수 |
| `generate_problem` | 유형·난이도 기반 문제 생성 | |
| `generate_testcases` | sample/hidden/edge 생성 | |
| `generate_reference_solution` | 내부 정답 코드 생성 | 비공개 |
| `run_reference_solution` | 정답 코드 실행·출력 검증 | **Judge0 호출** |
| `validate_problem` | 조건·난이도·예제 출력 검증 | |
| `run_user_code` | 사용자 코드 샌드박스 실행 | **Judge0 호출** |
| `analyze_complexity` | 시간복잡도 추정 | |
| `generate_counterexample` | 반례 생성 (정답 코드 미노출) | |
| `generate_hint` | 문제 생성 시 단계별 힌트 생성 | 저장용, 핵심코드 필터 |
| `save_learning_log` | 학습 이력 저장 | DB |

> `run_user_code`, `run_reference_solution`은 **Judge0 REST API를 호출하는 얇은 클라이언트**다.
> 직접 샌드박스를 구현하지 않는다.

---

## 3. 힌트 관련 Tool 정책 (요구사항 반영)

- `generate_hint`: 힌트 생성 시 **전문/핵심 코드를 포함하지 않는지 필터 검증** 후 저장한다.
  최대 노출 = 구조/뼈대(skeleton). 핵심 로직 자리는 비워 사용자가 입력하게 한다. (FR-19)
- `retrieve_hints`: 검색 범위를 항상 `[1 .. allowed_level]`로 제한한다.
  상위 단계 힌트는 **검색 결과에 포함되지 않는다.** (FR-18, NFR-4)

---

## 4. 코드 배치 요약

```
packages/agent/
├── graph.py        # 워크플로우 조립 (nodes + 조건 분기)
├── state.py        # GraphState (문제, 제출, 채점결과, allowed_level 등)
├── nodes/
│   ├── problem_generator.py
│   ├── testcase_generator.py
│   ├── reference_solver.py
│   ├── validator.py
│   └── feedback_hints.py
├── tools/
│   ├── retrieve_concepts.py
│   ├── retrieve_hints.py
│   ├── run_user_code.py          # Judge0 클라이언트
│   ├── run_reference_solution.py # Judge0 클라이언트
│   ├── ... (나머지 Tool)
└── prompts/
    ├── problem_generation.py
    ├── hint_generation.py
    └── feedback.py
```
