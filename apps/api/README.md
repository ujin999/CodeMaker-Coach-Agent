# apps/api — 백엔드 API (FastAPI)

Agent 코어(`packages/agent`)를 import해서 사용한다. 채점은 인메모리 큐로 비동기 처리한다.

- `app/routers/` — problems, submissions, hints, community, auth
- `app/schemas/` — Pydantic (기획 9장 입출력 스키마)
- `app/models/` — SQLAlchemy ORM (ARCHITECTURE 5장)
- `app/queue.py` — JudgeQueue 인터페이스 + InMemoryJudgeQueue (Phase 4)
- `app/judge_worker.py` — 큐 핸들러: Judge0 REST 채점 실행, 자체 DB 세션 사용 (Phase 4)

핵심: 힌트 단계 게이트키핑을 서버에서 강제한다. 상세: `docs/ARCHITECTURE.md`
