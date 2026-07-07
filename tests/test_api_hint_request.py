"""API 힌트 엔드포인트 테스트 — /api/hints/* 기본 동작."""

from __future__ import annotations

import os
import uuid

from fastapi.testclient import TestClient

os.environ["AGENT_MODE"] = "stub"


def _get_app():
    from app.main import app
    return app


def _auth_headers_and_problem(client: TestClient) -> tuple[dict, str]:
    """테스트 사용자 등록 + 문제 생성 → (headers, problem_id) 반환."""
    email = f"pytest_{uuid.uuid4().hex}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpass123", "display_name": "pytest"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    algo = f"hint_test_{uuid.uuid4().hex[:8]}"
    gen_resp = client.post(
        "/api/problems/generate",
        json={"algorithm": algo},
        headers=headers,
    )
    assert gen_resp.status_code == 201
    problem_id = gen_resp.json()["id"]
    return headers, problem_id


def test_hint_progress_initial():
    """Initial hint progress should be level 1."""
    client = TestClient(_get_app())
    headers, problem_id = _auth_headers_and_problem(client)

    resp = client.get(f"/api/hints/{problem_id}/progress", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["problem_id"] == problem_id
    assert body["allowed_level"] == 1


def test_hint_unlock_requires_confirm():
    """Unlocking next hint level requires confirm=true."""
    client = TestClient(_get_app())
    headers, problem_id = _auth_headers_and_problem(client)

    # confirm=false should be rejected
    resp = client.post(
        f"/api/hints/{problem_id}/unlock",
        json={"confirm": False},
        headers=headers,
    )
    assert resp.status_code == 400

    # confirm=true should succeed
    resp = client.post(
        f"/api/hints/{problem_id}/unlock",
        json={"confirm": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["allowed_level"] == 2


def test_hint_level_cap_at_3():
    """Hint level cannot exceed 3."""
    client = TestClient(_get_app())
    headers, problem_id = _auth_headers_and_problem(client)

    # Unlock to level 3
    for _ in range(2):
        resp = client.post(
            f"/api/hints/{problem_id}/unlock",
            json={"confirm": True},
            headers=headers,
        )
        assert resp.status_code == 200

    assert resp.json()["allowed_level"] == 3

    # Trying to unlock beyond 3 should fail
    resp = client.post(
        f"/api/hints/{problem_id}/unlock",
        json={"confirm": True},
        headers=headers,
    )
    assert resp.status_code == 400


def test_hints_list_respects_level():
    """GET /api/hints/{problem_id} returns hints only at allowed level."""
    client = TestClient(_get_app())
    headers, problem_id = _auth_headers_and_problem(client)

    # At level 1, should only get level-1 hints
    resp = client.get(f"/api/hints/{problem_id}", headers=headers)
    assert resp.status_code == 200
    hints = resp.json()
    assert all(h["level"] <= 1 for h in hints)


def test_hints_require_auth():
    """Hint endpoints require authentication."""
    client = TestClient(_get_app())

    resp = client.get("/api/hints/fake-problem-id/progress")
    assert resp.status_code == 401

    payload = {
        "problem_id": "fake-problem-id",
        "query": "힌트 주세요",
        "requested_level": 1,
    }
    resp = client.post("/api/hints/request", json=payload)
    assert resp.status_code == 401


def test_api_hint_request_success():
    """POST /api/hints/request succeeds and returns the hint when requested_level <= allowed_level."""
    client = TestClient(_get_app())
    headers, problem_id = _auth_headers_and_problem(client)

    payload = {
        "problem_id": problem_id,
        "query": "기본 힌트",
        "requested_level": 1,
    }
    resp = client.post("/api/hints/request", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["problem_id"] == problem_id
    assert body["blocked"] is False
    assert len(body["hints"]) > 0
    assert all(h["level"] == 1 for h in body["hints"])


def test_api_hint_request_blocked():
    """POST /api/hints/request is blocked when requested_level > allowed_level."""
    client = TestClient(_get_app())
    headers, problem_id = _auth_headers_and_problem(client)

    # Initial allowed_level is 1. Requesting level 2 should be blocked.
    payload = {
        "problem_id": problem_id,
        "query": "2단계 힌트",
        "requested_level": 2,
    }
    resp = client.post("/api/hints/request", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["problem_id"] == problem_id
    assert body["blocked"] is True
    assert "허용되지 않은" in body["block_reason"]
    # Should not contain any level 2 hints
    assert all(h["level"] <= 1 for h in body["hints"])

