# apps/web — 프론트엔드 (Next.js 14 App Router)

## 실행

```bash
cd apps/web
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_BASE_URL 확인 (기본 http://localhost:8000)
npm run dev
```

백엔드(`apps/api`)가 `http://localhost:8000`에서 떠 있어야 정상 동작한다.

## 화면 구성

- `/` — 랜딩
- `/login`, `/register` — 인증
- `/generate` — 문제 생성 (알고리즘·난이도·언어·학습목표·취약점 선택)
- `/problems` — **공개 문제 카탈로그**: 난이도·알고리즘 분류·검색·정렬 필터
- `/problems/mine` — 내가 생성한 문제
- `/solve/[id]` — 문제 풀이: Monaco 에디터 + 제출/채점 폴링 + AI 코치 힌트 챗봇 패널 + 정답 보기(confirm) + 문제 신고
- `/community/[problemId]` — AC gating 적용된 공유 풀이 피드 (좋아요·댓글)

힌트 단계·정답 노출 여부는 서버가 판단하며, 프론트는 표시만 한다(임의 변경 불가).

## API 클라이언트

- `lib/types.ts` — `apps/api/app/schemas/*`, `packages/agent/schemas.py`와 1:1 대응하는 TS 타입
- `lib/api.ts` — `NEXT_PUBLIC_API_BASE_URL` 기반 fetch 래퍼. JWT를 자동으로 `Authorization: Bearer`로 첨부하고, 401 응답 시 토큰을 지우고 `/login`으로 이동한다.
- `lib/auth.ts` — 토큰을 `localStorage`에 저장 (클라이언트 전용)

## ⚠️ 백엔드에 필요한 확장 (아직 미구현)

`/problems` 카탈로그 페이지는 "이미 생성되어 공개된 모든 문제"를 분류해서 보여주기 위한 화면이다.
그런데 현재 `GET /api/problems` (`apps/api/app/routers/problems.py`)는 **로그인한 사용자가 직접 생성한
문제만** 반환한다 (`.filter(Problem.created_by == user_id)`). 즉 전체 공개 카탈로그용 엔드포인트가 아직 없다.

임시 조치: 프론트는 받아온 목록을 클라이언트에서 `algorithm` / `difficulty` / `q`(검색어)로 필터링하고
있지만, 애초에 서버가 본인 문제만 주기 때문에 다른 사용자가 만든 문제는 카탈로그에 보이지 않는다.

**백엔드 담당에게 요청**: `GET /api/problems`가 아래 쿼리 파라미터를 지원하도록 확장해달라.

```
GET /api/problems?scope=public|mine&algorithm=<str>&difficulty=<str>&q=<str>&sort=recent|difficulty&skip=&limit=
```

- `scope=public`(기본값): 전체 사용자의 공개 문제 목록 (created_by 필터 제거)
- `scope=mine`: 기존 동작 (본인 문제만) — `/problems/mine` 페이지가 사용
- `algorithm`, `difficulty`, `q`, `sort`는 서버에서 필터링/정렬 후 반환하면 프론트의 클라이언트 사이드
  폴백 필터는 자연히 no-op이 되므로 별도 프론트 변경 없이 그대로 맞물린다.

이 엔드포인트가 준비되기 전까지는 `/problems` 카탈로그가 "내 문제 목록"과 동일하게 보인다는 점을
알아두면 된다.
