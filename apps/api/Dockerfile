# apps/api — FastAPI 백엔드
# 빌드 컨텍스트는 리포지토리 루트여야 한다 (packages/* 를 함께 복사해야 하므로).
#   docker build -f apps/api/Dockerfile -t codemaker-api .
# infra/docker-compose.yml에서는 build.context: .. 로 이미 지정되어 있다.

FROM python:3.12-slim

WORKDIR /app

# psycopg2 / bcrypt / cryptography 빌드용 최소 도구
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# 의존성 정의 먼저 복사해 레이어 캐시를 최대한 활용한다.
COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY apps/api ./apps/api
COPY alembic.ini ./
COPY alembic ./alembic
COPY docs ./docs

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONPATH="/app/packages:/app/apps/api"

COPY apps/api/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 10000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
