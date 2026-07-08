# CLAUDE.md

이 파일은 Claude Code 및 AI 에이전트가 이 저장소에서 작업할 때 읽는 **진입점 문서**다.
프로젝트의 정체성, 구조, 핵심 정책을 요약한다. 상세 내용은 `docs/`의 개별 문서를 참조한다.

---

## 1. 프로젝트 한 줄 정의

**CodeMaker Coach Agent** — 기존 문제은행에 의존하지 않고, 사용자가 선택한 알고리즘 유형·난이도에 맞는
**코딩테스트 문제를 LLM으로 생성·검증**하고, 풀이 과정에서 **오답 분석과 단계별 힌트**를 제공하는
**Agent 기반 코딩테스트 학습 플랫폼**이다.

> 이것은 "정답을 대신 풀어주는 챗봇"이 아니다.
> "문제 생성 → 검증 → 풀이 → 힌트 → 복습"을 하나의 학습 루프로 연결하는 것이 핵심이다.

기획 원문: `docs/주제 선정.pdf`

---

## 2. 기술 스택

| 레이어 | 기술 |
|---|---|
| Agent 오케스트레이션 | 결정론적 노드 순차 오케스트레이션(`packages/agent/nodes/workflow.py`). LangGraph `StateGraph` 조립은 아직 목표/확장 단계이며 현재 구현은 아니다 |
| LLM 연결·Tool·프롬프트 | **LangChain** |
| LLM Provider | Claude / GPT (env로 설정, `LLM_PROVIDER`) |
| RAG | Vector DB (Qdrant/pgvector) + LangChain Retriever |
| Graph RAG | **Neo4j** (사용자 약점 기반 개인화) |
| 채점(Judge) | **Judge0** (기존 오픈소스, Docker/REST API) — 직접 구현하지 않음 |
| 백엔드 API | FastAPI (Python) |
| 프론트엔드 | Next.js + React (코드 에디터: Monaco/CodeMirror) |
| 관계형 DB | PostgreSQL (유저·문제·제출·공유 코드) |
| 채점 작업 큐 | **인메모리 큐** (MVP) — 인터페이스로 추상화, 트래픽 증가 시 Redis+Celery로 교체 |

---

## 3. 디렉터리 구조

```
CodeMaker-Coach-Agent/
├── docs/                     # 기획 문서 + RAG 지식 문서 + 설계 문서
│   ├── 주제 선정.pdf          # 기획 원문 (.gitignore 처리됨)
│   ├── REQUIREMENTS.md       # 요구사항 명세
│   ├── ARCHITECTURE.md       # 아키텍처 상세
│   ├── AGENTS_AND_TOOLS.md   # Agent/Tool 사양
│   └── knowledge/            # RAG 원본 문서 (algorithm/ pattern/ problem_generation/)
│
├── apps/
│   ├── api/                  # FastAPI 백엔드 (Agent를 import해서 사용)
│   └── web/                  # Next.js 프론트엔드
│
├── packages/
│   ├── agent/                # ★ Agent 코어 (앱과 독립된 순수 패키지)
│   │   ├── nodes/            #   워크플로우 노드 + nodes/workflow.py(오케스트레이션), nodes/state.py(AgentState)
│   │   ├── services/         #   Public Service API (generate_problem_package 등, API가 호출하는 진입점)
│   │   ├── chains/           #   LLM 체인 (problem/testcase/hint/feedback 생성)
│   │   ├── reference_solvers/#   결정론적 정답 코드 템플릿 + registry
│   │   ├── testcase_generators/ # 결정론적 테스트케이스 생성기 + registry
│   │   ├── tools/             #   run_user_code.py = Judge0 클라이언트
│   │   ├── prompts/          #   PromptTemplate
│   │   └── schemas.py        #   Pydantic 스키마 (GraphState 역할 겸 public 계약)
│   ├── rag/                  # RAG 파이프라인 (Loader→Splitter→Embed→VectorStore→Retriever)
│   └── graphrag/             # Neo4j 연동 (driver/sync/query) — 오답 이력 적재 + 약점 개인화
│
├── infra/
│   └── docker-compose.yml    # postgres, neo4j, qdrant, judge0(+judge0 전용 judge0-redis), api, web
│
└── tests/
```

> **핵심 설계 원칙**: `packages/agent`는 웹·API·채점과 **독립된 순수 Python 패키지**다.
> API는 `app.gateway.AgentGateway`를 경계로 두고 내부에서 `agent`의 public service API
> (`generate_problem_package`, `request_hint_package`, `review_submission_package` 등)를 호출한다.
> 실제 흐름: `FastAPI router → app.gateway → agent services/chains/nodes`.
> Agent는 CLI/테스트/노트북에서 단독 실행 가능해야 한다.
> 채점(`apps/judge`)은 **직접 만들지 않는다** — Judge0 컨테이너를 띄우고 Tool에서 REST 호출한다.
>
> **Redis 관련 주의**: 앱 채점 큐는 인메모리(`apps/api/app/queue.py`)이며 Redis를 쓰지 않는다.
> compose의 `judge0-redis`는 Judge0 스택 내부 전용이며 앱 큐와 무관하다.

---

## 4. 반드시 지켜야 할 정책 (기획 문서 2.4 / 14 / 15장)

이 정책들은 협상 불가다. 코드/기능 변경 시 위반하지 않는지 확인한다.

1. **정답 즉시 제공 금지 (HITL)** — 정답 코드는 기본 비공개. 사용자가 명시적으로 "정답 보기"를 선택하고
   확인 절차를 거친 경우에만 제공한다. 힌트는 1→2→3단계로 점진적으로만 상승한다.
6. **힌트 정책** — 힌트는 **문제 생성 시 미리 만들어 DB에 저장**하고 RAG로 서빙한다(즉석 생성 아님).
   챗봇 방식으로 사용자가 요청할 때만 응답하며, **현재 허용 단계를 넘어가는 힌트는 검색·전달 자체를 서버에서 차단**한다.
   힌트는 **전문/핵심 코드를 절대 제공하지 않고 구조(스켈레톤)까지만** 노출하며, 핵심 로직은 사용자가 직접 입력한다.
   상세: `docs/REQUIREMENTS.md` 2.4장.
2. **문제 원문 복제 금지 (저작권)** — 기존 온라인 저지의 문제를 수집/변형하지 않는다.
   알고리즘 개념 문서 + 자체 템플릿 기반으로 **새 문제를 생성**한다.
3. **코드 실행 격리 (보안)** — 사용자 코드는 반드시 Judge0 샌드박스에서만 실행한다.
   timeout / memory limit / network 차단이 적용되어야 한다. API·DB와 네트워크 격리한다.
4. **개인정보 보호** — 사용자 코드·학습 이력은 사용자별 접근 제어 + 삭제 기능 대상이다. 최소 저장 원칙.
5. **코드 공유 gating** — 커뮤니티 공유 코드는 **해당 문제를 스스로 AC한 사용자에게만** 열람 허용한다.
   (정책 1과 코드 공유 기능을 동시에 만족시키기 위한 규칙)

---

## 5. 작업 절차 (필수 — 모든 기능 작업에 적용)

기능을 만들기 전/도중/후에 아래 절차를 **반드시** 따른다.

### 5.1 작업 전 — 작업 계획 표시
- 코드를 건드리기 **전에**, 이번에 무엇을 할지 사용자에게 **항상 먼저 표시**한다.
  - 대상 Step(BUILD_PLAN 기준), 변경/생성할 파일, 만들 브랜치 이름, 검증(DoD)을 요약한다.
- 계획 없이 곧바로 구현에 들어가지 않는다.

### 5.2 작업 중 — 기능별 Git 브랜치 분리
- 작업은 **최대한 기능 단위로 브랜치를 나눠서** 진행한다. `main`에 직접 커밋하지 않는다.
- 브랜치 네이밍: `feat/<범위>` (기능) · `fix/<범위>` · `chore/<범위>` · `docs/<범위>`
  - 예: `chore/scaffold`, `feat/rag-pipeline`, `feat/problem-generator`, `feat/hint-system`, `feat/community-sharing`
- 하나의 브랜치는 하나의 기능/Phase Step에 대응하도록 작게 유지한다.

### 5.3 작업 후 — 커밋 & 리모트 푸시
- 해당 브랜치 작업이 끝나면(= DoD 통과) **커밋 후 리모트로 push** 한다.
  - `git add` → `git commit` → `git push -u origin <branch>`
  - **push 대상 리모트는 `origin`** (`https://github.com/ujin999/CodeMaker-Coach-Agent.git`)
  - `upstream`은 원본(fork source)이므로 **push하지 않는다.**
- 커밋 메시지는 무엇을/왜를 명확히 한다. 기능 완료 후에는 PR 생성을 고려한다.

> 요약 루프: **[작업 계획 표시] → [feat 브랜치 생성] → [구현 + DoD 검증] → [commit] → [origin push]**

---

## 6. 작업 시 유의사항

- 새 기능/변경은 위 **정책 5개**와 충돌하지 않는지 먼저 확인한다.
- Agent 관련 코드는 `packages/agent`에 두고, 웹/DB 의존성을 이 패키지에 끌어들이지 않는다.
- 문제 생성/피드백의 입출력은 기획 문서 9장의 JSON 스키마를 따른다 → Pydantic + Structured Output으로 강제.
- 새 알고리즘 개념 지식은 `docs/knowledge/`에 md로 추가하면 RAG에 반영된다.
- 상세 요구사항은 `docs/REQUIREMENTS.md`, 아키텍처는 `docs/ARCHITECTURE.md`, Agent/Tool은 `docs/AGENTS_AND_TOOLS.md` 참조.
- **구현은 `docs/BUILD_PLAN.md`의 단계(Phase 0→10)를 순서대로 따른다.** 각 Step의 검증(DoD)을 통과해야 다음으로 넘어간다.
