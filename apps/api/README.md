# apps/api — 백엔드 API (FastAPI)

Agent 코어(`packages/agent`)를 import해서 사용한다. 채점은 인메모리 큐로 비동기 처리한다.

- `app/routers/` — problems, submissions, hints, community, auth, admin
- `app/schemas/` — Pydantic (기획 9장 입출력 스키마)
- `app/models/` — SQLAlchemy ORM (ARCHITECTURE 5장)
- `app/queue.py` — JudgeQueue 인터페이스 + InMemoryJudgeQueue (Phase 4)
- `app/judge_worker.py` — 큐 핸들러: Judge0 REST 채점 실행, 자체 DB 세션 사용 (Phase 4)

핵심: 힌트 단계 게이트키핑을 서버에서 강제한다. 상세: `docs/ARCHITECTURE.md`

## 문제 신고 / HITL (FR-34)

`POST/DELETE/GET /api/problems/{id}/report`로 신고·취소·상태 조회를 한다. 누적
신고 수(`settings.problem_report_threshold`, 기본 5)를 넘으면 문제가 `under_review`
상태가 되어 공개 카탈로그에서 숨겨진다. `is_admin` 사용자는 `GET
/api/admin/problems/flagged`로 검토 대기 목록을, `POST
/api/admin/problems/{id}/review`(`dismiss`/`remove`/`edit`)로 조치를 취할 수 있다.
최초 관리자 계정은 API로 만들 수 없으므로 DB에서 직접
`UPDATE users SET is_admin = true WHERE email = '...'`로 설정해야 한다.
