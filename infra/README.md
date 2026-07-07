# infra — 인프라 + 앱 전체 스택 (Docker)

`docker-compose.yml`로 의존 서비스와 앱(API/Web)을 함께 띄운다.

| 컨테이너 | 역할 | 포트 | MVP |
|---|---|---|:---:|
| postgres | 관계형 데이터 | 5432 | ✅ |
| qdrant | 벡터 스토어 (개념+힌트 색인) | 6333/6334 | ✅ |
| api | FastAPI 백엔드 (apps/api) | **10000** | ✅ |
| web | Next.js 프론트엔드 (apps/web) | **10001** | ✅ |
| judge0 (+db, +worker) | 코드 채점 샌드박스 | 2358 | ✅ |
| neo4j | Graph RAG (확장) | 7474/7687 | ⬜ |

> 채점 큐는 MVP에서 API 프로세스 내부 인메모리 큐를 사용하므로 Redis 컨테이너가 없다.

## 실행 전 준비

리포지토리 루트에 `.env`가 있어야 한다 (`.env.example` 참고). 최소한 아래 값은 채운다.

- `JWT_SECRET_KEY` — 비어있으면 API가 기동을 거부한다.
- `ANTHROPIC_API_KEY` 또는 `OPENAI_API_KEY` — 없으면 stub(가짜 응답) 모드로 동작한다.
- `NEXT_PUBLIC_API_BASE_URL` — **브라우저**가 API를 호출할 주소. `localhost`가 아니라
  실제 접속 주소(서버 IP·도메인 + 포트 **10000**)를 적어야 한다. 빌드 시점에 프론트 번들에 박힌다.
- `CORS_ORIGINS` — 위 프론트 주소(포트 **10001**)를 반드시 포함해야 브라우저 요청이 차단되지 않는다.

`DATABASE_URL`, `QDRANT_URL`, `JUDGE0_URL`은 컨테이너 간 통신용으로 compose가 자동으로
오버라이드하므로 `.env`의 값과 달라도 신경 쓰지 않아도 된다.

```bash
# 전체 스택 한 번에 (리포지토리 루트에서 실행) — 최초/코드 변경 후에는 --build 포함
docker compose --env-file .env -f infra/docker-compose.yml up -d --build

# 로그 확인
docker compose -f infra/docker-compose.yml logs -f api web

# 인프라만 (앱은 로컬에서 직접 실행하며 개발할 때)
docker compose -f infra/docker-compose.yml up -d postgres qdrant

# Graph RAG 포함 (확장)
docker compose -f infra/docker-compose.yml --profile graphrag up -d
```

기동 후 `http://<서버 주소>:10001`으로 접속하면 프론트가,
`http://<서버 주소>:10000/health`로 API 상태를 확인할 수 있다.
DB 마이그레이션(`alembic upgrade head`)은 `api` 컨테이너 entrypoint가 기동할 때마다 자동으로 실행한다.

## ⚠️ Judge0 로컬 실행 제약 (macOS / Apple Silicon)

Judge0의 채점 API 서버는 macOS에서도 뜨지만, **isolate 샌드박스 코드 실행은 실패**한다.
(`status: Internal Error`, `/box/script.py: No such file or directory`)

- 원인: Judge0 1.13.1은 **cgroup v1 + linux/amd64**를 요구한다. Docker Desktop(cgroup v2) +
  Apple Silicon(arm64 에뮬레이션) 환경에서는 isolate가 정상 동작하지 않는다. 설정 오류가 아니다.
- **개발 시 대응 방안**:
  1. 실제 채점은 **Linux 호스트 / CI**에서 검증한다. (거기서는 이 compose가 그대로 동작)
  2. 또는 원격 Judge0 인스턴스 URL을 `.env`의 `JUDGE0_URL`에 지정한다.
  3. 로컬 단위테스트에서는 `run_user_code` Tool(Judge0 클라이언트)을 **모킹**한다. (Phase 3~4)
- 앱 개발(Agent/RAG/API/Web)은 postgres + qdrant만으로 진행 가능하다.
