# apps/web — 프론트엔드 (Next.js 14 App Router)

## 실행

```bash
cd apps/web
npm install
# 기본값은 http://localhost:10000 (apps/api 기본 포트). 다른 주소를 쓰려면 .env.local에
# NEXT_PUBLIC_API_BASE_URL=<주소> 를 설정한다 (lib/api.ts 참조).
npm run dev
```

백엔드(`apps/api`)가 기본적으로 `http://localhost:10000`에서 떠 있어야 정상 동작한다.

## 화면 구성

- `/` — 랜딩
- `/login`, `/register` — 인증
- `/generate` — 문제 생성 (알고리즘·난이도·언어·학습목표·취약점 선택)
- `/problems` — **공개 문제 카탈로그** (`GET /api/problems`, `mine=false`): 난이도·알고리즘 분류·검색·정렬
  필터를 서버가 처리한다. 신고 누적으로 `under_review`/`removed` 상태가 된 문제는 자동으로 숨겨진다.
- `/problems/mine` — 내가 생성한 문제 (`mine=true` — 상태와 무관하게 전부 보임)
- `/problems/manage` — **문제 관리(HITL 검토)**: 신고 누적으로 검토 대기 중인 문제 목록과 신고 사유를
  보여주고, 기각(dismiss)/삭제(remove)/수정 후 복구(edit) 조치를 할 수 있다. 별도 관리자 계정이
  없으며, 로그인한 사용자라면 누구나 접근 가능하다.
- `/solve/[id]` — 문제 풀이: Monaco 에디터 + 제출/채점 폴링 + AI 코치 힌트 챗봇 패널 + 정답 보기(confirm) + 문제 신고(취소 가능한 토글)
- `/community/[problemId]` — AC gating 적용된 공유 풀이 피드 (좋아요·댓글)

힌트 단계·정답 노출 여부는 서버가 판단하며, 프론트는 표시만 한다(임의 변경 불가).

## API 클라이언트

- `lib/types.ts` — `apps/api/app/schemas/*`, `packages/agent/schemas.py`와 1:1 대응하는 TS 타입
- `lib/api.ts` — `NEXT_PUBLIC_API_BASE_URL` 기반 fetch 래퍼. JWT를 자동으로 `Authorization: Bearer`로 첨부하고, 401 응답 시 토큰을 지우고 `/login`으로 이동한다.
- `lib/auth.ts` — 토큰을 `localStorage`에 저장 (클라이언트 전용)

## 카탈로그 필터 (구현됨)

`GET /api/problems`는 아래 쿼리 파라미터를 서버에서 직접 필터링/정렬해 반환한다
(`apps/api/app/routers/problems.py`의 `list_problems`).

```
GET /api/problems?mine=<bool>&algorithm=<str>&difficulty=<str>&q=<str>&sort=recent|difficulty&skip=&limit=
```

- `mine=false`(기본값): 전체 공개 문제 목록, `Problem.status == "active"`인 것만 (신고 누적으로
  `under_review`/`removed`가 된 문제는 자동으로 빠진다)
- `mine=true`: 로그인한 사용자 본인이 생성한 문제만, 상태와 무관하게 전부 반환 — `/problems/mine`
  페이지가 사용
- `algorithm`(배열 컬럼 매칭), `difficulty`, `q`(제목/본문 `ilike` 검색), `sort`(`recent`|`difficulty`)는
  모두 서버 쿼리로 처리된다.
