# 실행 계획 (Build Plan)

AI 에이전트가 CodeMaker Coach Agent를 **순서대로 구현**하기 위한 단계별 플레이북이다.

## 사용 규칙 (AI 필독)
- 위에서 아래로 **순차 진행**한다. 각 Step은 이전 Step의 산출물에 의존한다.
- 각 Step은 `목표 → 작업 → 산출 → 검증(DoD) → 근거`로 구성된다. **검증(DoD)을 통과해야 다음 Step으로 간다.**
- 코드 작성 전 항상 `CLAUDE.md`의 **정책 6개**를 위반하지 않는지 확인한다.
- 상세 사양은 `REQUIREMENTS.md`(요구사항), `ARCHITECTURE.md`(구조), `AGENTS_AND_TOOLS.md`(Agent/Tool) 참조.
- `[MVP]` 표시는 최소 기능 완성에 필수인 Step이다. `[확장]`은 이후로 미뤄도 된다.

## 작업 절차 규칙 (모든 Step 공통 — CLAUDE.md 5장)
각 Step(또는 묶인 기능 단위)마다 아래 루프를 지킨다.
1. **작업 전**: 이번 작업 계획(대상 Step·파일·브랜치명·DoD)을 사용자에게 **먼저 표시**한다.
2. **브랜치 생성**: `main`에서 기능 브랜치를 딴다. 아래 Phase별 권장 브랜치명 참고.
3. **구현 + DoD 검증**: 작업 후 해당 Step의 검증(DoD)을 통과시킨다.
4. **커밋 & 푸시**: `git commit` 후 **`git push -u origin <branch>`** (push는 `origin`만, `upstream` 금지).

### Phase별 권장 브랜치
| Phase | 브랜치 | Phase | 브랜치 |
|---|---|---|---|
| 0 | `chore/scaffold` | 5 | `feat/hint-system` |
| 1 | `feat/agent-core` | 6 | `feat/feedback-analysis` |
| 2 | `feat/rag-pipeline` | 7 | `feat/api-and-auth` |
| 3 | `feat/problem-generation` | 8 | `feat/web-frontend` |
| 4 | `feat/judging` | 9 | `feat/community-sharing` |
|  |  | 10 | `feat/graphrag-personalization` |
> Phase가 크면 Step 단위로 더 잘게 나눠도 된다. (예: `feat/hint-gating`, `feat/hint-chatbot`)

## 진행 체크리스트

> 표기: `[x]` 완료 / `[~]` 부분 구현(확장 여지 있음) / `[ ]` 미착수.
> 이 체크리스트는 "구현 완료 이력"을 반영한다. 세부 미해결 항목은 `error-fix/`를 참조한다.

- [x] Phase 0 — 프로젝트 초기화
- [x] Phase 1 — Agent 코어 뼈대 + LLM 연결
- [x] Phase 2 — RAG 파이프라인
- [x] Phase 3 — 문제 생성·검증 워크플로우 (결정론적 노드 순차 오케스트레이션, LangGraph `StateGraph` 조립은 아님)
- [x] Phase 4 — 채점 (제출 → 인메모리 큐 → Judge0, `apps/api/app/queue.py` + `judge_worker.py`)
- [x] Phase 5 — 힌트 시스템 (핵심)
- [x] Phase 6 — 풀이 지원 (오답 분석)
- [x] Phase 7 — API 서버 + 인증
- [x] Phase 8 — 프론트엔드
- [x] Phase 9 — 코드 공유 (커뮤니티)
- [x] Phase 10 — 개인화 / Graph RAG [확장] — LangGraph StateGraph 연동 및 Self-Correction 루프백 배선 완료

---

## Phase 0 — 프로젝트 초기화 `[MVP]`

### Step 0.1 — 저장소 골격 생성
- **목표**: `ARCHITECTURE.md` 3장 디렉터리 구조를 실제 폴더/스텁으로 만든다.
- **작업**:
  - `apps/api`, `apps/web`, `packages/agent`, `packages/rag`, `packages/graphrag`, `infra`, `tests` 생성
  - `docs/knowledge/{algorithm,pattern,problem_generation}` 폴더 생성
  - 각 폴더에 목적을 적은 `README.md` 배치
- **산출**: 위 디렉터리 + 빈 `__init__.py`
- **검증(DoD)**: 트리가 `ARCHITECTURE.md` 3장과 일치한다.
- **근거**: ARCHITECTURE 3장

### Step 0.2 — Python 프로젝트 설정
- **목표**: 의존성·가상환경·패키지 설치.
- **작업**:
  - 루트 `pyproject.toml` 생성 (`packages/*`를 로컬 패키지로 인식하도록 워크스페이스/경로 설정)
  - 의존성: `langchain`, `langgraph`, `langchain-anthropic`(또는 `-openai`), `pydantic`, `fastapi`,
    `uvicorn`, `httpx`, `sqlalchemy`, `alembic`, `qdrant-client`, `pytest`
  - 가상환경 생성 + 설치
- **산출**: `pyproject.toml`, 잠금 파일, `.venv`
- **검증(DoD)**: `python -c "import langchain, langgraph, fastapi"` 성공.
- **근거**: CLAUDE 2장

### Step 0.3 — 환경변수 & 설정 로더
- **목표**: `.env` 기반 설정을 코드에서 읽는다.
- **작업**: `.env.example`를 `.env`로 복사, `packages/*` 공용 `settings.py`(pydantic-settings) 작성
- **산출**: `settings.py`, `.env`(로컬, 미커밋)
- **검증(DoD)**: 설정 객체가 `LLM_PROVIDER`, `JUDGE0_URL`, `DATABASE_URL`을 읽어온다.
- **근거**: `.env.example`, NFR-3

### Step 0.4 — 인프라 컨테이너
- **목표**: 로컬 의존 서비스를 띄운다.
- **작업**: `infra/docker-compose.yml`에 `postgres`, `qdrant`, `judge0`(+부속) 정의. Redis는 넣지 않음(인메모리 큐).
- **산출**: `docker-compose.yml`
- **검증(DoD)**: `docker compose up -d` 후 postgres/qdrant/judge0 헬스체크 통과.
- **근거**: ARCHITECTURE 6장

---

## Phase 1 — Agent 코어 뼈대 + LLM 연결 `[MVP]`

### Step 1.1 — GraphState 정의
- **목표**: 워크플로우가 공유할 상태 스키마.
- **작업**: `packages/agent/state.py`에 `GraphState`(문제, 테스트케이스, 정답, 제출, 채점결과, allowed_level 등)
- **산출**: `state.py`
- **검증(DoD)**: 타입체크/임포트 성공.
- **근거**: ARCHITECTURE 5장, AGENTS_AND_TOOLS 4장

### Step 1.2 — LLM Provider 추상화 + 스모크
- **목표**: `LLM_PROVIDER`로 ChatModel을 선택하고 1회 호출한다.
- **작업**: `packages/agent/llm.py`에 provider 팩토리(claude/openai), 간단 호출 스크립트
- **산출**: `llm.py`, `scripts/smoke_llm.py`
- **검증(DoD)**: 스모크 스크립트가 LLM 응답 1건을 출력한다.
- **근거**: CLAUDE 2장, NFR-11

### Step 1.3 — 빈 LangGraph 조립
- **목표**: Node를 붙일 수 있는 그래프 뼈대.
- **작업**: `packages/agent/graph.py`에 `build_graph()` (지금은 pass-through Node 1개)
- **산출**: `graph.py`
- **검증(DoD)**: `build_graph().invoke(초기상태)`가 상태를 반환한다.
- **근거**: ARCHITECTURE 4장

---

## Phase 2 — RAG 파이프라인 `[MVP]`

### Step 2.1 — 지식 문서 시드
- **목표**: RAG가 검색할 초기 개념 문서.
- **작업**: `docs/knowledge/algorithm/`에 `binary_search.md`, `bfs.md`, `dfs.md`, `dp_basic.md`,
  `greedy.md` 등, `pattern/`에 `time_complexity.md`, `off_by_one.md` 등 최소 세트 작성 (기획 10.1)
- **산출**: 마크다운 지식 문서
- **검증(DoD)**: 문서 5개 이상 존재.
- **근거**: 기획 10.1, FR-4

### Step 2.2 — RAG 파이프라인 구현
- **목표**: Loader→Splitter→Embed→VectorStore→Retriever.
- **작업**: `packages/rag/pipeline.py`(색인 빌드), `retriever.py`(개념 검색). Qdrant 사용.
- **산출**: `packages/rag/*`, 색인 빌드 스크립트
- **검증(DoD)**: "이분 탐색" 질의 시 `binary_search.md` 청크가 상위로 검색된다.
- **근거**: ARCHITECTURE 2.4, FR-4

---

## Phase 3 — 문제 생성·검증 워크플로우 `[MVP]`

### Step 3.1 — Judge0 클라이언트 Tool
- **목표**: 코드 실행을 Judge0에 위임.
- **작업**: `packages/agent/tools/run_user_code.py`, `run_reference_solution.py` (httpx로 Judge0 REST 호출,
  `언어+코드+stdin` → `stdout/시간/메모리/상태`)
- **산출**: Judge0 클라이언트 Tool 2종
- **검증(DoD)**: 파이썬 "hello world" 채점이 `AC` 유사 결과를 반환한다.
- **근거**: AGENTS_AND_TOOLS 2장, FR-12

### Step 3.2 — Problem Generator Node
- **목표**: 유형·난이도 → 문제 JSON 생성 (+ 힌트는 Phase 5에서 연결).
- **작업**: `nodes/problem_generator.py`. 출력은 기획 9.2 스키마를 Pydantic/Structured Output으로 강제.
  생성 전 `retrieve_concepts` 호출.
- **산출**: `problem_generator.py`, 문제 Pydantic 스키마
- **검증(DoD)**: 유효한 문제 JSON(제목·설명·입출력·제한·예제)이 생성된다.
- **근거**: FR-2, FR-3, FR-4, NFR-6

### Step 3.3 — Testcase Generator Node
- **목표**: sample/hidden/edge 케이스 생성.
- **작업**: `nodes/testcase_generator.py`
- **산출**: 테스트케이스 목록
- **검증(DoD)**: 각 타입별로 1개 이상 생성.
- **근거**: FR-6

### Step 3.4 — Reference Solver Node
- **목표**: 내부 정답 코드 생성(비공개).
- **작업**: `nodes/reference_solver.py`
- **산출**: reference solution
- **검증(DoD)**: 생성 코드가 Judge0에서 실행된다.
- **근거**: FR-7

### Step 3.5 — Validator Node + 재생성 분기
- **목표**: 예제 출력 == reference 실행 결과 + 조건/난이도/복잡도 검증, 실패 시 재생성.
- **작업**: `nodes/validator.py` + `graph.py`에 조건 분기(실패→Problem Generator로 루프)
- **산출**: `validator.py`, 분기 배선
- **검증(DoD)**: 의도적으로 틀린 예제를 주면 fail → 재생성 경로를 탄다.
- **근거**: FR-8, FR-9, NFR-5

---

## Phase 4 — 채점 파이프라인 `[MVP]`

### Step 4.1 — 큐 추상화 (인메모리)
- **목표**: 제출을 비동기 처리하되 Redis 없이.
- **작업**: `apps/api/queue.py`에 `JudgeQueue` 인터페이스 + `InMemoryJudgeQueue`(asyncio.Queue/BackgroundTasks).
  나중에 Redis로 교체 가능하게 인터페이스 고정.
- **산출**: 큐 인터페이스 + 인메모리 구현
- **검증(DoD)**: enqueue한 작업을 백그라운드 워커가 소비한다.
- **근거**: ARCHITECTURE 2.6

### Step 4.2 — 채점 워커 + 상태 분기
- **목표**: 제출 코드 → Judge0(hidden testcase) → `AC/WA/TLE/RE/MLE` → LangGraph 분기.
- **작업**: 워커가 `run_user_code`로 채점 후 결과를 상태에 반영, 그래프의 제출 후 분기 배선
- **산출**: 채점 워커, 제출 후 분기
- **검증(DoD)**: 정답/오답/시간초과 코드가 각각 올바른 상태로 분류된다.
- **근거**: FR-13, FR-14, FR-21

---

## Phase 5 — 힌트 시스템 `[MVP]` (핵심)

> `CLAUDE.md` 정책 6 + `REQUIREMENTS.md` 2.4장의 규칙을 이 Phase에서 구현한다.

### Step 5.1 — 힌트 생성 + 핵심코드 필터
- **목표**: 문제 생성 시 힌트 1~3단계를 만들고, 핵심 코드가 없는지 검증 후 저장.
- **작업**: `tools/generate_hint.py`. Problem Generator에서 호출.
  필터: 힌트에 정답/핵심 로직 코드가 포함되면 재생성 또는 skeleton으로 축소. `reveals_core_code`는 항상 false.
- **산출**: `generate_hint.py`, `Hint` 저장 로직
- **검증(DoD)**: 생성된 힌트에 핵심 코드가 없고, 3단계 힌트도 구조/뼈대까지만 담긴다.
- **근거**: FR-5, FR-19, NFR-4

### Step 5.2 — 힌트 색인 (RAG 서빙)
- **목표**: 저장된 힌트를 문제별로 검색 가능하게 색인.
- **작업**: `tools/retrieve_hints.py`. 검색 범위를 항상 `[1..allowed_level]`로 제한하는 필터 내장.
- **산출**: 힌트 retriever
- **검증(DoD)**: `allowed_level=1`일 때 2·3단계 힌트가 **검색 결과에 포함되지 않는다.**
- **근거**: FR-16, FR-18, NFR-4

### Step 5.3 — 힌트 단계 게이트 상태
- **목표**: (user, problem)별 허용 단계 관리.
- **작업**: `HintProgress` 모델 + 승급 API(현재 단계 +1은 명시적 승급 확인 후에만)
- **산출**: `HintProgress` CRUD, 승급 로직
- **검증(DoD)**: 상위 단계 직접 요청은 거부되고, 승급 확인을 거쳐야만 단계가 오른다.
- **근거**: FR-17, FR-18

### Step 5.4 — 챗봇형 힌트 Node
- **목표**: 사용자가 요청할 때만 허용 단계 힌트로 응답.
- **작업**: `nodes/feedback_hints.py`에서 `retrieve_hints` 호출 → 응답 구성(구조까지만). 자동 푸시 금지.
- **산출**: 힌트 챗봇 Node
- **검증(DoD)**: "3단계 힌트 바로 줘"라고 해도 허용 단계까지만 응답한다(초과 차단).
- **근거**: FR-15, FR-16, FR-18, FR-19

---

## Phase 6 — 풀이 지원 (오답 분석) `[MVP]`

### Step 6.1 — 오답/복잡도/에러 분석
- **목표**: 채점 상태별 분석 + RAG 근거.
- **작업**: `feedback_hints.py`에 오답 분석·`analyze_complexity`·에러 분석 연결, `retrieve_concepts`로 근거 검색
- **산출**: 분석 로직
- **검증(DoD)**: O(N²) 제출에 TLE 시 "복잡도 초과" 분석 + 관련 개념이 근거로 붙는다.
- **근거**: FR-21, FR-22

### Step 6.2 — 반례 생성
- **목표**: 실패 케이스를 드러내는 반례 제공(정답 코드 미노출).
- **작업**: `tools/generate_counterexample.py`
- **산출**: 반례 Tool
- **검증(DoD)**: 반례가 실제로 오답을 유발하고, 정답 코드는 노출되지 않는다.
- **근거**: FR-23

---

## Phase 7 — API 서버 + 인증 `[MVP]`

### Step 7.1 — DB 모델 & 마이그레이션
- **목표**: `ARCHITECTURE.md` 5장 테이블 생성.
- **작업**: SQLAlchemy 모델 + Alembic 마이그레이션
- **산출**: 모델, 마이그레이션
- **검증(DoD)**: `alembic upgrade head` 성공, 테이블 생성 확인.
- **근거**: ARCHITECTURE 5장

### Step 7.2 — 인증
- **목표**: 회원가입/로그인 + 소유권.
- **작업**: `routers/auth.py` (JWT/세션), 비밀번호 해시
- **산출**: 인증 라우터
- **검증(DoD)**: 가입→로그인→보호 엔드포인트 접근이 동작한다.
- **근거**: FR-27

### Step 7.3 — 핵심 API 라우터
- **목표**: 문제·제출·힌트·학습로그 엔드포인트.
- **작업**: `routers/problems.py`(생성/조회), `submissions.py`(제출→큐, 결과 폴링),
  `hints.py`(요청/승급, **서버에서 단계 강제**), 학습로그 저장
- **산출**: 라우터 일체
- **검증(DoD)**: 문제 생성→제출→채점결과→힌트요청 전체 흐름이 API로 동작한다.
- **근거**: FR-11~FR-18, FR-24, NFR-4

---

## Phase 8 — 프론트엔드 `[MVP]`

### Step 8.1 — 프로젝트 셋업 + 인증 UI
- **작업**: `apps/web` Next.js 초기화, 로그인/회원가입 화면, API 클라이언트
- **검증(DoD)**: 로그인 후 토큰으로 API 호출 가능.
- **근거**: FR-27

### Step 8.2 — 문제 생성 화면 (`/generate`)
- **작업**: 알고리즘·난이도·스타일·언어·힌트 방식 선택 → 생성 요청 → 로딩
- **검증(DoD)**: 선택 후 문제가 생성되어 풀이 화면으로 이동.
- **근거**: FR-1, 기획 17.1

### Step 8.3 — 풀이 화면 + AI Tutor 챗봇 (`/solve/[id]`)
- **작업**: 문제 표시 + Monaco/CodeMirror 에디터 + 실행/제출 + **힌트 챗봇 패널**(요청 시에만 응답, 단계 승급 UI)
- **검증(DoD)**: 코드 제출→채점 결과 표시, 힌트 요청→허용 단계 응답, 초과 요청 차단 확인.
- **근거**: FR-10~FR-19, 기획 17.1

---

## Phase 9 — 코드 공유 (커뮤니티) `[MVP]`

### Step 9.1 — 공유 도메인 + gating
- **목표**: AC한 사용자만 공유 코드 열람.
- **작업**: `SharedSolution`/`Comment`/`Like` 모델, `routers/community.py`.
  **gating**: 특정 문제 공유 코드는 그 문제 `SolvedRecord`가 있는 사용자에게만 노출.
- **산출**: 커뮤니티 API + gating
- **검증(DoD)**: 미해결 사용자는 해당 문제의 공유 코드를 볼 수 없다.
- **근거**: FR-29, FR-30

### Step 9.2 — 커뮤니티 UI (`/community`)
- **작업**: 피드(필터: 문제/알고리즘/난이도/인기), 좋아요·댓글, 풀이 비교
- **검증(DoD)**: AC 후 공유 게시→다른 사용자(AC자)가 열람·좋아요·댓글.
- **근거**: FR-31, FR-32, FR-33

---

## Phase 10 — 개인화 / Graph RAG `[확장]`

### Step 10.1 — Neo4j 스키마 + 적재
- **작업**: 기획 11장 Node/Edge(User, Problem, Concept, ErrorType, USER_FAILED_ON 등) `packages/graphrag`에 구현
- **검증(DoD)**: 사용자 오답이 그래프에 기록된다.
- **근거**: FR-25

### Step 10.2 — 약점 기반 개인화 생성
- **작업**: Problem Generator가 사용자 약점 개념을 반영해 문제 생성
- **검증(DoD)**: 약점(예: off-by-one) 사용자에게 해당 요소가 포함된 문제가 나온다.
- **근거**: FR-25, FR-26

---

## 완료 기준 (MVP Done)
Phase 0~9 완료 시 다음 end-to-end 시나리오가 동작해야 한다 (기획 17.2):
1. 로그인 → `/generate`에서 "이분 탐색·중" 선택
2. 문제 생성(RAG→생성→테스트케이스→정답→검증 통과) + 힌트 1~3단계 저장
3. 풀이 화면에서 O(N²) 코드 제출 → **TLE** 판정
4. 챗봇에 힌트 요청 → **1단계**만 응답(초과 차단), 승급 후 2단계
5. 수정 후 **AC** → 학습 로그 저장
6. 풀이 코드 공유 → 같은 문제 AC자만 열람
