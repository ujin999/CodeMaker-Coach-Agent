# apps/api — 백엔드 API (FastAPI)

Agent 코어(`packages/agent`)를 import해서 사용한다. 채점은 인메모리 큐로 비동기 처리한다.

- `app/routers/` — problems, submissions, hints, community, auth
- `app/schemas/` — Pydantic (기획 9장 입출력 스키마)
- `app/models/` — SQLAlchemy ORM (ARCHITECTURE 5장)
- `app/queue.py` — JudgeQueue 인터페이스 + InMemoryJudgeQueue (Phase 4)
- `app/judge_worker.py` — 큐 핸들러: Judge0 REST 채점 실행, 자체 DB 세션 사용 (Phase 4)

핵심: 힌트 단계 게이트키핑을 서버에서 강제한다. 상세: `docs/ARCHITECTURE.md`

## 문제 신고 / HITL (FR-34)

`POST/DELETE/GET /api/problems/{id}/report`로 신고·취소·상태 조회를 한다. 누적
신고 수(`settings.problem_report_threshold`, 기본 5)를 넘으면, 사람이 보기 전에
`packages/agent`의 `assess_problem_report_package()`가 먼저 문제와 신고 사유를
재검증해 `critical`(즉시 삭제)/`safe`(즉시 기각)/`minor`(사람 검토 대기, 판정 실패
시에도 안전하게 이쪽으로 폴백)로 분기한다. `minor`인 경우에만 문제가 `under_review`
상태가 되어 공개 카탈로그에서 숨겨진다. 별도 관리자 계정 없이, 로그인한 모든
사용자가 `GET /api/problems/flagged`로 검토 대기 목록을 보고 `POST
/api/problems/{id}/review`(`dismiss`/`remove`/`edit`)로 조치를 취할 수 있다.
상세 시퀀스: `docs/API_REFERENCE.md` 6.4장.
