# CodeMaker Coach Agent

기존 문제은행에 의존하지 않고, 사용자가 선택한 알고리즘 유형·난이도에 맞는 **코딩테스트 문제를 LLM으로
생성·검증**하고, 풀이 과정에서 **오답 분석과 단계별 힌트**를 제공하는 Agent 기반 코딩테스트 학습 플랫폼이다.

"정답을 대신 풀어주는 챗봇"이 아니라 **문제 생성 → 검증 → 풀이 → 힌트 → 복습**을 하나의 학습 루프로
연결하는 것이 핵심이다.

---

## 핵심 기능

- **문제 생성/검증** — 알고리즘·난이도·스타일·언어를 고르면 LLM이 새 문제를 생성하고, 결정론적
  Testcase Generator / Reference Solver / Validator가 예제 정확도·난이도·시간복잡도를 검증한다.
  검증 실패 시 자동 재생성한다.
- **단계별 힌트 (챗봇형)** — 힌트는 문제 생성 시 1~3단계로 미리 만들어 저장되고, 풀이 중 RAG로
  서빙된다. 현재 허용 단계를 넘어서는 힌트는 서버가 검색 자체를 차단하며, 핵심 코드는 절대 노출하지
  않고 구조(스켈레톤)까지만 제공한다.
- **비동기 채점 (Judge0)** — 제출 코드는 Judge0 샌드박스에서 hidden testcase로 채점되고,
  `AC/WA/TLE/RE/MLE/JUDGE_ERROR` 상태로 분류된다.
- **오답 분석 / 개인화** — 채점 결과에 따라 오답 원인 진단, 반례, 복잡도 분석, 피드백을 생성하고,
  Neo4j(Graph RAG)에 사용자 약점 가중치를 누적해 다음 문제 생성에 반영한다.
- **코드 공유 (커뮤니티)** — AC를 받은 사용자만 자신의 풀이를 공유할 수 있고, 해당 문제를 스스로
  AC한 사용자에게만 다른 사람의 공유 코드가 노출된다 (gating).
- **문제 신고 / Human-in-the-Loop 중재** — 품질이 낮은 생성 문제는 신고할 수 있고, 신고가 임계치를
  넘으면 Agent가 먼저 심각도(critical/safe/minor)를 재판정한다. 명백한 결함은 자동 삭제, 명백한
  오신고는 자동 기각하며, 애매한 경우에만 사람의 검토(모든 로그인 사용자가 참여 가능)로 넘어간다.

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Agent 오케스트레이션 | LangChain 체인 + 결정론적 Node 파이프라인 (`packages/agent`) |
| LLM Provider | Claude / OpenAI (`LLM_PROVIDER` env) |
| RAG | Qdrant (테스트 시 InMemory fallback) + LangChain Retriever |
| Graph RAG | Neo4j (사용자 약점 기반 개인화) |
| 채점(Judge) | Judge0 (기존 오픈소스, Docker/REST API) |
| 백엔드 API | FastAPI (Python) |
| 프론트엔드 | Next.js + React (Monaco 에디터) |
| 관계형 DB | PostgreSQL |
| 채점 작업 큐 | 인메모리 큐 (`apps/api/app/queue.py`, MVP) — 인터페이스로 추상화, 확장 시 Redis+Celery로 교체 |

자세한 아키텍처는 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), 에이전트 노드/체인/서비스 구조는
[`docs/AGENTS_AND_TOOLS.md`](docs/AGENTS_AND_TOOLS.md)와 [`packages/agent/API.md`](packages/agent/API.md),
전체 REST API는 [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)를 참조한다.

---

## 디렉터리 구조

```
CodeMaker-Coach-Agent/
├── docs/                     # 기획/요구사항/아키텍처/API 문서 + RAG 지식 문서
├── apps/
│   ├── api/                  # FastAPI 백엔드 (agent 패키지를 import해서 사용)
│   └── web/                  # Next.js 프론트엔드
├── packages/
│   ├── agent/                # LangChain 기반 Agent 코어 (웹/DB와 독립된 순수 패키지)
│   ├── rag/                  # RAG 파이프라인 (개념 문서 + 힌트 색인)
│   ├── graphrag/             # Neo4j 기반 Graph RAG (사용자 약점 개인화)
│   └── config/               # 공용 환경설정 로더 (Settings)
├── infra/
│   └── docker-compose.yml    # postgres, qdrant, judge0, neo4j, api, web
└── tests/                    # pytest 테스트 스위트
```

---

## 실행 방법

인프라(postgres/qdrant/judge0/neo4j)뿐 아니라 **백엔드(api)와 프론트엔드(web)도 모두
`infra/docker-compose.yml`이 각자의 `Dockerfile`로 빌드해서 컨테이너로 띄운다.** 로컬에서
`uvicorn`/`npm run dev`를 직접 실행하는 별도 구성이 아니다.

### 1. 환경변수

리포지토리 루트에 `.env` 파일을 만든다 (`packages/config/settings.py` 참조). 최소한 아래 값을 채운다.

```env
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=...
JWT_SECRET_KEY=...            # 반드시 설정 — 비어 있으면 API 컨테이너가 기동을 거부한다
NEXT_PUBLIC_API_BASE_URL=http://localhost:10000   # 브라우저가 접속할 API 주소, 프론트 빌드 시점에 박힘
CORS_ORIGINS=http://localhost:10001,...           # 위 프론트 주소를 반드시 포함해야 함
```

> `DATABASE_URL`/`QDRANT_URL`/`JUDGE0_URL`은 컨테이너 간 통신용으로 compose가 자동
> 오버라이드하므로 `.env`에 로컬 주소를 적어도 무방하다.

### 2. 전체 스택 기동 (postgres, qdrant, judge0, api, web)

```bash
# 리포지토리 루트에서 실행 — 최초 실행/코드 변경 후에는 --build 포함
docker compose --env-file .env -f infra/docker-compose.yml up -d --build

# 로그 확인
docker compose -f infra/docker-compose.yml logs -f api web

# Graph RAG(개인화, neo4j)까지 포함하려면
docker compose -f infra/docker-compose.yml --profile graphrag up -d
```

기동 후 프론트는 `http://localhost:10001`, API 상태는 `http://localhost:10000/health`로 확인한다.
DB 마이그레이션(`alembic upgrade head`)은 `api` 컨테이너가 기동할 때마다 자동으로 실행된다.

인프라만 띄우고 API/Web은 로컬에서 직접 돌리며 개발하고 싶다면:

```bash
docker compose -f infra/docker-compose.yml up -d postgres qdrant
PYTHONPATH=packages:apps/api uv run alembic upgrade head
PYTHONPATH=packages:apps/api uv run uvicorn app.main:app --host 0.0.0.0 --port 10000 --reload
# 별도 터미널
cd apps/web && npm install && npm run dev
```

> macOS/Apple Silicon에서는 Judge0의 isolate 샌드박스가 정상 동작하지 않는다 (cgroup v1 +
> linux/amd64 요구). 상세 원인과 대응은 `infra/README.md` 참조.

### 3. 테스트 실행

```bash
uv run python -m pytest
```

> 테스트는 `ENV=test` 기준 `FakeStructuredChatModel`(LLM 목)과 `AGENT_MODE=stub` 게이트웨이를 사용해
> 외부 API 호출 없이 동작한다. 단, DB/Judge0 등 인프라는 실제 연결을 사용하므로 위 compose 스택이
> 떠 있어야 한다.

전체 서비스 구성/포트/제약 사항은 `infra/README.md`에 더 자세히 정리되어 있다.

---

## 문서 지도

| 문서 | 내용 |
|---|---|
| [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | 기능/비기능 요구사항 명세 (FR/NFR) |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 시스템 아키텍처, 데이터 흐름, 인프라 구성 |
| [`docs/AGENTS_AND_TOOLS.md`](docs/AGENTS_AND_TOOLS.md) | Agent Node / Tool / Chain / Service 사양 |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | REST API 엔드포인트 전체 레퍼런스 + 시퀀스 다이어그램 |
| [`packages/agent/API.md`](packages/agent/API.md) | `packages/agent` 파이썬 패키지 공개 API 레퍼런스 |
| [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) | 단계별(Phase 0→10) 구현 계획 |
| [`CLAUDE.md`](CLAUDE.md) | AI 에이전트(Claude Code)용 작업 정책/절차 진입점 문서 |
