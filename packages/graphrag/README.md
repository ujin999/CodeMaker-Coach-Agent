# packages/graphrag — Graph RAG (Neo4j)

사용자 약점·문제·개념·오답유형 관계를 Neo4j에 저장해 맞춤형 문제 생성에 활용한다. **구현되어
`develop`에 병합되었으며**, `apps/api`가 아래 두 시점에 실제로 호출한다 (MVP 이후 확장이 아니다).

## 공개 API (`packages/graphrag/__init__.py`)

| 함수 | 호출 지점 | 역할 |
|---|---|---|
| `record_submission_to_graph(...)` (`sync.py`) | `apps/api/app/judge_worker.py` — 채점 완료 시 | 정답(AC)이면 `WEAK_IN.weight_score`를 감산, 오답(WA/TLE/RE/MLE)이면 가산하고 `FAILED`/`POTENTIAL_ERROR` 관계로 오답 유형을 누적한다. |
| `get_user_weaknesses(user_id)` (`query.py`) | `apps/api/app/routers/problems.py` — `POST /api/problems/generate` (`focus_weaknesses=true`인 경우) | 가중치가 높은 약점 개념 top 3, 빈발 오답 유형 top 2, 한국어 추천 코멘트를 조회해 `recent_weaknesses` 프롬프트 필드에 주입한다. |
| `get_driver()` / `close_driver()` (`driver.py`) | 내부용 | `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` 기반 드라이버 싱글턴. |

- Node: `User`, `Problem`, `Concept`, `ErrorType` 등
- 핵심 관계: `WEAK_IN {weight_score, last_updated}`(User→Concept), `FAILED {count}`(User→Problem),
  `POTENTIAL_ERROR`(Problem→ErrorType)
- **Neo4j 연결 실패에도 안전**: 두 함수 모두 드라이버/쿼리 예외를 잡아 각각 no-op(기록 실패) 또는
  빈 기본값(`weak_concepts: []`)으로 폴백한다. Neo4j가 꺼져 있어도 문제 생성/채점 자체는 막히지 않는다.

상세: 기획 11장, `docs/ARCHITECTURE.md` 2.5.
