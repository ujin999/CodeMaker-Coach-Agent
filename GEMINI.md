# GEMINI.md

이 파일은 Gemini Code 메이트 및 AI 에이전트(Antigravity)가 이 저장소에서 작업할 때 읽는 **진입점 문서**입니다.
프로젝트의 정체성, 구조, 핵심 정책 및 작업 절차를 정의합니다.

---

## 1. 프로젝트 한 줄 정의

**CodeMaker Coach Agent** — 기존 문제은행에 의존하지 않고, 사용자가 선택한 알고리즘 유형·난이도에 맞는
**코딩테스트 문제를 LLM으로 생성·검증**하고, 풀이 과정에서 **오답 분석과 단계별 힌트**를 제공하는
**Agent 기반 코딩테스트 학습 플랫폼**입니다.

---

## 2. 기술 스택

| 레이어 | 기술 |
|---|---|
| Agent 오케스트레이션 | 결정론적 Node 파이프라인 (`packages/agent/nodes/workflow.py`) — LangGraph `StateGraph`가 아님 |
| LLM 연결·Tool·프롬프트 | **LangChain** (`packages/agent/chains/`) |
| LLM Provider | Claude (기본값) / OpenAI (`LLM_PROVIDER` env로 결정) |
| RAG | Vector DB (Qdrant/pgvector) + LangChain Retriever |
| Graph RAG | **Neo4j** (사용자 약점 기반 개인화) |
| 채점(Judge) | **Judge0** (기존 오픈소스, Docker/REST API) |
| 백엔드 API | FastAPI (Python) |
| 프론트엔드 | Next.js + React (코드 에디터: Monaco/CodeMirror) |
| 관계형 DB | PostgreSQL (유저·문제·제출·공유 코드) |
| 채점 작업 큐 | **인메모리 큐** (MVP) — 확장 시 Redis+Celery로 교체 |

---

## 3. 디렉터리 구조

```
CodeMaker-Coach-Agent/
├── docs/                     # 기획 문서 + RAG 지식 문서 + 설계 문서
│   ├── REQUIREMENTS.md       # 요구사항 명세
│   ├── ARCHITECTURE.md       # 아키텍처 상세
│   └── knowledge/            # RAG 원본 문서 (algorithm/ pattern/ problem_generation/)
├── apps/
│   ├── api/                  # FastAPI 백엔드
│   └── web/                  # Next.js 프론트엔드
├── packages/
│   ├── agent/                # ★ Agent 코어 (웹/DB와 독립된 순수 패키지)
│   │   ├── chains/           #   LLM 호출 체인 (문제/힌트/피드백/신고판정 생성)
│   │   ├── nodes/            #   결정론적 파이프라인 Node + workflow.py 러너
│   │   ├── reference_solvers/ #  8종 archetype 결정론적 정답 코드 생성기
│   │   ├── testcase_generators/ # 8종 archetype 결정론적 테스트케이스 생성기
│   │   ├── tools/            #   Judge0/RAG 클라이언트
│   │   ├── services/         #   FastAPI가 실제로 호출하는 비동기 서비스 진입점
│   │   ├── prompts/          #   PromptTemplate
│   │   └── schemas.py        #   Pydantic 스키마 전체
│   ├── rag/                  # RAG 파이프라인
│   ├── graphrag/             # Neo4j Node/Edge 스키마 + Cypher (사용자 약점 개인화, 구현됨)
│   └── config/                # 공용 Settings 로더
├── infra/
│   └── docker-compose.yml    # postgres, qdrant, judge0, neo4j, api, web
└── tests/                    # pytest 테스트 스위트
```

상세 구조/사양: `docs/AGENTS_AND_TOOLS.md`, `packages/agent/API.md`, `docs/API_REFERENCE.md`.

---

## 4. 핵심 정책 (반드시 지켜야 할 규칙)

1. **정답 즉시 제공 금지 (HITL)** — 정답 코드는 기본 비공개. 사용자가 명시적으로 동의하고 확인 절차를 거친 경우에만 공개합니다.
2. **문제 원문 복제 금지 (저작권)** — 기존 온라인 저지 문제를 수집/변형하지 않고, 알고리즘 개념 문서 + 자체 템플릿 기반으로 새 문제를 생성합니다.
3. **점진적 힌트 제공** — 힌트는 1→2→3단계로 점진적으로만 상승합니다. 핵심 코드는 절대 제공하지 않고 구조(스켈레톤)까지만 노출합니다.
4. **코드 실행 격리** — 사용자 코드는 반드시 Judge0 샌드박스에서만 실행하여 보안을 강화합니다.
5. **코드 공유 gating** — 커뮤니티 공유 코드는 **해당 문제를 스스로 AC(정답 통과)한 사용자에게만** 열람을 허용합니다.
6. **문제 신고 / HITL 중재** — 신고가 누적되면 Agent가 먼저 심각도(critical/safe/minor)를 판정합니다. 애매한 경우에만 사람 검토로 넘어가며, **별도의 관리자 계정 없이 로그인한 모든 사용자**가 검토(`/problems/manage`)에 참여할 수 있습니다. 상세: `docs/ARCHITECTURE.md` 7장.

---

## 5. Gemini 에이전트 작업 절차

### 5.1 기능별 Git 브랜치 분리
* 작업을 진행하기 전 반드시 새로운 피처 브랜치(`feat/` 또는 `fix/`)를 생성하여 작업합니다.
* `develop` 브랜치에 직접 작업을 하거나 커밋을 쌓지 않습니다.

### 5.2 작업 완료 후 한글 커밋 메시지 작성 규격
* 커밋 메시지는 **반드시 한글**로 작성하며, 무엇을 변경했고 왜 변경했는지 아래 형식을 따릅니다.
  ```text
  feat: <한글 요약 설명>
  
  - 상세 설명 내용 1
  - 상세 설명 내용 2
  ```

### 5.3 origin push 대상 리모트
* 리모트 푸시 대상은 항상 `origin` (`https://github.com/ujin999/CodeMaker-Coach-Agent.git`) 입니다.
* `upstream`으로는 절대 직접 push하지 않습니다.

---

## 6. 개발 및 실행 명령어 가이드

### 백엔드 로컬 실행
```bash
PYTHONPATH=packages:apps/api uv run uvicorn app.main:app --host 0.0.0.0 --port 10000 --reload
```

### 프론트엔드 로컬 실행
```bash
cd apps/web
npm install
npm run dev
```

### 전체 테스트코드 실행
```bash
uv run python -m pytest
```
