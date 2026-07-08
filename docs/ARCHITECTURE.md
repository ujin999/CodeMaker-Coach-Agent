# 아키텍처 (Architecture)

CodeMaker Coach Agent의 시스템 아키텍처를 정의한다.
채점은 **Judge0(기존 오픈소스)** 를 사용하며, 직접 샌드박스를 구현하지 않는다.
채점 작업 큐는 **MVP 단계에서 인메모리 큐**를 사용한다. (아래 2.6 참조)

---

## 1. 컴포넌트 개요

```
[사용자 브라우저 / Next.js]
  │  문제 생성 요청 / 코드 제출 / 힌트 챗봇 / 커뮤니티 조회
  ▼
[API 서버 / FastAPI]──────────────┬───────────────┬────────────────┐
  │                               │               │                │
  ▼ (동기: 생성·힌트·피드백)       ▼ (비동기: 채점) ▼                ▼
[Agent 코어 / LangGraph]     [인메모리 큐]     [PostgreSQL]     [Neo4j]
  ├─ Problem Generator       (백그라운드 워커) 유저·문제·힌트    (Graph RAG:
  ├─ Testcase Generator          │            제출·공유코드      약점 개인화)
  ├─ Reference Solver            ▼            ·힌트단계상태
  ├─ Validator              [Judge0]
  └─ Feedback/Hints         Docker sandbox
  │                         (timeout·mem·net 차단)
  ▼                              │
[RAG / Vector DB]                ▼
 Qdrant/pgvector            [채점 결과 AC/WA/TLE/RE]
  ├─ 개념 문서 색인               └─> 콜백 → 상태 분기 → 학습 로그 저장
  └─ 힌트 색인(문제별)
```

---

## 2. 레이어별 책임

### 2.1 프론트엔드 (`apps/web`, Next.js)
- **문제 생성 화면** (`/generate`): 알고리즘·난이도·스타일·언어·힌트 방식 선택
- **문제 풀이 화면** (`/solve/[id]`): 문제 + Monaco/CodeMirror 에디터 + 실행/제출 + **AI Tutor 챗봇 패널**
- **커뮤니티** (`/community`): 코드 공유 피드 (gating 적용)
- 힌트 단계·정답 노출 여부는 프론트에서 임의로 못 바꾼다 → 서버가 판단 (NFR-4)

### 2.2 API 서버 (`apps/api`, FastAPI)
- 라우터: `problems`, `submissions`, `hints`, `community`, `auth`
- Agent 코어를 **import해서 호출**한다: `from agent.graph import build_graph`
- 채점은 직접 안 하고 **큐에 적재** 후 즉시 응답(202) → 결과는 폴링/WebSocket
- **힌트 단계 게이트키핑**을 여기서 강제한다 (허용 단계 이하만 Agent에 전달)

### 2.3 Agent 코어 (`packages/agent`, LangGraph)
- 웹/DB에 의존하지 않는 **독립 패키지** (NFR-10)
- 워크플로우는 아래 4장 참조
- Tool은 `packages/agent/tools/`에 정의, 외부 자원(Judge0·RAG·DB)은 주입받는다

### 2.4 RAG (`packages/rag`)
- `docs/knowledge/`의 개념 문서를 Loader→Splitter→Embed→VectorStore→Retriever로 색인
- **두 개의 검색 대상**을 가진다:
  1. **개념 문서 색인** — 문제 생성·오답 분석 근거
  2. **힌트 색인** — 문제 생성 시 저장된 힌트를 문제별로 검색 (단계 필터 적용)

### 2.5 Graph RAG (`packages/graphrag`, Neo4j)
- 사용자 약점·문제·개념·오답유형 관계를 Neo4j에 그래프 구조로 유지하고 개인화 문제 생성에 활용한다.
- **오답 발생/해결 시점**: `judge_submission` 완료 시점에 사용자-개념 간의 약점 가중치(`WEAK_IN {weight_score}`)를 증감하여 학습 상태를 누적 업데이트한다.
- **문제 생성 시점**: 생성 에이전트 구동 전 Neo4j에서 현재 사용자의 약점 개념(가중치가 높은 알고리즘 태그)과 잦은 오답 유형을 조회한 뒤, `recent_weaknesses` 프롬프트 필드에 주입하여 LLM이 개인화된 맞춤 문제를 설계하도록 유도한다.

### 2.6 채점 작업 큐 (MVP: 인메모리)
- **MVP는 인메모리 큐를 사용한다.** 사용자 규모가 작아 별도 브로커(Redis)와 Celery 워커가 불필요하다.
  - 구현: FastAPI `BackgroundTasks` 또는 `asyncio.Queue` + 인프로세스 백그라운드 워커
  - 장점: 추가 컨테이너/워커 프로세스 없음, 설정 단순, 자원 소모 미미
  - 한계(인지하고 감수): 프로세스 재시작 시 대기 작업 유실, 멀티 API 워커로 수평 확장 불가, 작업 영속성 없음
- **큐는 인터페이스로 추상화한다** (`enqueue_judge(...)` / 워커). 구현체만 인메모리 → Redis+Celery/RQ로
  교체할 수 있게 설계해, 트래픽 증가 시 **Agent·API 로직 변경 없이** 전환한다.
- 전환 트리거(참고): 다중 인스턴스 배포가 필요해지거나, 재시작 시 작업 유실이 문제가 될 때.

### 2.7 채점 (Judge0, `infra/docker-compose.yml`)
- 기존 오픈소스. REST API로 `언어 + 코드 + stdin` 전달 → `stdout/시간/메모리/상태` 반환
- `packages/agent/tools/run_user_code.py`가 얇은 클라이언트
- API·DB와 네트워크 격리, timeout·memory·network 차단

---

## 3. 데이터 흐름 (핵심 시나리오)

### 3.1 문제 생성 (동기)
```
사용자 선택 → API → Neo4j 약점 및 오답 유형 쿼리 → 약점 주입
  → RAG(개념 검색) → Problem Generator → Testcase Generator
  → Reference Solver → Validator
      ├ 실패 → 재생성 (분기)
      └ 성공 → 문제 + 힌트(1~3단계) DB 저장 + 힌트 벡터 색인 → 사용자에게 문제 제공
```

### 3.2 채점 (비동기, 인메모리 큐)
```
코드 제출 → API가 인메모리 큐에 적재 → 202 응답
  → 백그라운드 워커가 Judge0로 hidden testcase 실행 → 상태(AC/WA/TLE/RE/MLE)
  → 콜백 → LangGraph 분기(정답 로그 / 오답 분석 / 복잡도 분석 / 에러 분석)
      ├ 정답(AC) -> Neo4j 약점 가중치 감산 및 해결 이력 기록
      └ 오답(WA/TLE/RE) -> Neo4j 약점 가중치 가산 및 오답 유형 축적
  → 사용자에게 결과 전달 (폴링/WebSocket)
```

### 3.3 힌트 (챗봇, 동기) — 단계 제어 핵심
```
사용자가 챗봇에 힌트 요청
  → API가 (user, problem)의 "현재 허용 단계" 조회 (DB)
  → RAG 힌트 검색 범위를 [1 .. 허용단계]로 제한   ← 상위 단계는 물리적으로 검색 불가
  → Feedback/Hints Agent가 검색된 힌트로 응답 구성 (구조까지만, 핵심 코드 제외)
  → 다음 단계 요청 시 → 승급 확인 → 허용 단계 +1
```
> 상위 단계 힌트는 "프롬프트에 안 넣는" 수준이 아니라 **검색 대상에서 제외**되어야 안전하다. (NFR-4)

---

## 4. LangGraph 워크플로우 (기획 12.2)

```
[사용자 선택]
   ↓
[Problem Generator] → [Testcase Generator] → [Reference Solver] → [Validator]
   ↓ (조건 분기)
   ├ 검증 실패 → 문제 재생성
   └ 검증 성공 → 문제 + 힌트 저장 → 제공
        ↓
   [사용자 코드 제출] → [Code Execution (Judge0)]
        ↓ (조건 분기)
        ├ 정답      → 학습 로그 저장 & Neo4j 가중치 해결 반영
        ├ 오답      → 오답 분석 + 반례 생성 & Neo4j 취약점 추가
        ├ 시간 초과 → 시간복잡도 분석
        └ 런타임 E  → 에러 분석
        ↓
   [Feedback / Hints Generator]  (힌트 단계·노출 범위 정책 적용)
```

---

## 5. 데이터 모델 (PostgreSQL, 주요 테이블)

```
User            : id, email, password_hash, created_at
Problem         : id, title, difficulty, algorithm[], statement, input_format,
                  output_format, constraints[], sample_input, sample_output,
                  reference_solution(비공개), time_complexity, created_by, created_at
TestCase        : id, problem_id, type(sample|hidden|edge), input, expected_output
Hint            : id, problem_id, level(1|2|3), content,
                  reveals_core_code(false 강제), code_skeleton(nullable)
Submission      : id, user_id, problem_id, code, language,
                  status(AC|WA|TLE|RE|MLE), runtime, memory, created_at
HintProgress    : user_id, problem_id, allowed_level   ← 힌트 단계 게이트 상태
SolvedRecord    : user_id, problem_id, solved_at        ← 공유 gating 판단용
LearningLog     : id, user_id, problem_id, error_type, hint_level_used, resolved
SharedSolution  : id, submission_id, title, description, is_public, likes_count, created_at
Comment         : id, shared_solution_id, user_id, content, created_at
Like            : user_id, shared_solution_id
ProblemReport   : id, user_id, problem_id, reason, created_at
```

핵심 제약:
- `Hint.reveals_core_code`는 항상 false (저장 전 필터 검증) — 요구사항 FR-19
- `HintProgress.allowed_level`로 힌트 초과 요청 차단 — FR-18
- `SolvedRecord` 존재 여부로 커뮤니티 공유 코드 gating — FR-30

---

## 6. 인프라 (`infra/docker-compose.yml`)

| 컨테이너 | 역할 | MVP 필수 |
|---|---|:---:|
| `postgres` | 관계형 데이터 | ✅ |
| `qdrant` | 벡터 스토어 (개념 + 힌트 색인) | ✅ |
| `judge0` | 코드 채점 샌드박스 (+ 부속 워커/DB) | ✅ |
| `api` | FastAPI (인메모리 큐 + 백그라운드 워커 포함) | ✅ |
| `web` | Next.js | ✅ |
| `neo4j` | Graph RAG (개인화 확장) | ✅ (Phase 4 도입) |
| ~~`redis`~~ | ~~채점 큐 브로커~~ → **MVP 제외**, 인메모리 큐로 대체 (트래픽 증가 시 도입) | ⬜ |

> - 채점 큐는 MVP에서 API 프로세스 내부 인메모리 큐(`apps/api/app/queue.py`)로 처리하므로 별도 컨테이너가 없다. (2.6 참조)
> - `judge0-redis`는 Judge0 자체 구현이 쓰는 내부 컴포넌트다. "앱 큐용 Redis"와 혼동하지 않는다 — 위 표의 `~~redis~~` 행이 가리키는 것은 앱 큐용이며 MVP에서 실제로 존재하지 않는다.
> - Judge0는 API·DB 네트워크와 분리된 네트워크에 두어 격리한다. (NFR-2)

---

## 7. [TODO - 차기 과제] 신고 누적 문제 자동 중재 에이전트 (Human-in-the-Loop)

특정 문제의 신고가 일정 횟수 이상 누적되면 시스템 안정성 및 품질 유지를 위해 `Moderation Agent`가 자동으로 개입하는 기능 설계 사양이다.

### 7.1 아키텍처 모델 및 상태 정의 (DB)
- `ProblemModeration` 테이블을 신설하여 문제 아이디, 판정 상태(`PENDING` | `AUTO_DELETED` | `ADMIN_PENDING` | `ADMIN_APPROVED` | `DISMISSED`), AI 중재 의견(`reason`), 심각도(`severity`), 그리고 일시 정지된 에이전트를 재개하기 위한 LangGraph `thread_id` 정보를 추적 관리한다.

### 7.2 LangGraph 상태 기계 흐름
1.  **[assess_problem Node]**: 누적된 신고 사유와 문제 정보를 컨텍스트로 LLM에 넘겨 심각도를 `critical` (치명적), `minor` (수정 필요), `safe` (오신고)로 판정한다.
2.  **[Routing Edge]**: 심각도에 따라 분기한다:
    - `critical` -> `auto_delete Node`로 이동하여 DB에서 문제를 일괄 삭제하고 `status=AUTO_DELETED` 처리.
    - `safe` -> `dismiss_reports Node`로 이동하여 신고 내역을 기각/초기화하고 `status=DISMISSED` 처리.
    - `minor` -> **Interrupt 발생**. LangGraph 실행을 일시정지하고 `status=ADMIN_PENDING` 상태로 대기한다.
3.  **[Admin Approval Interrupt & Resume]**:
    - 관리자가 전용 어드민 API(`POST /api/admin/moderations/{id}/action`)를 통해 승인(`approve`) 또는 반려(`reject`) 응답을 송신한다.
    - 백엔드는 관리자의 결정을 그래프의 상태 값(State)에 주입하고, 체크포인터(`MemorySaver`)의 대기 스레드를 재개(`resume`)하여 이후 노드(`auto_delete` 또는 `dismiss_reports`)를 최종 실행한다.
