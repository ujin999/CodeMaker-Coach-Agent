"""CORS 설정 테스트 — 로컬 개발 환경 origin 허용 확인."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

os.environ["AGENT_MODE"] = "stub"


def _get_app():
    from app.main import app
    return app


_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:10001",
    "http://127.0.0.1:10001",
]


def test_cors_allows_local_origins():
    """CORS middleware should allow all standard local dev origins."""
    client = TestClient(_get_app())

    for origin in _ALLOWED_ORIGINS:
        resp = client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        # Preflight should return 200 with the origin in the header
        assert resp.status_code == 200, f"CORS preflight failed for {origin}"
        assert resp.headers.get("access-control-allow-origin") == origin, (
            f"Origin {origin} not reflected in access-control-allow-origin header"
        )


def test_cors_allows_credentials():
    """CORS should allow credentials (cookies, auth headers)."""
    client = TestClient(_get_app())

    resp = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_cors_rejects_unknown_origin():
    """CORS should not reflect an unknown origin."""
    client = TestClient(_get_app())

    resp = client.options(
        "/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # The origin should NOT be reflected
    allow_origin = resp.headers.get("access-control-allow-origin", "")
    assert allow_origin != "http://evil.example.com"
