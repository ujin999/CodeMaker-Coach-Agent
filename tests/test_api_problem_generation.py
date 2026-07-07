from __future__ import annotations
import os
import uuid

from fastapi.testclient import TestClient
from app.main import app


def _auth_headers(client: TestClient) -> dict:
    """테스트용 사용자를 등록하고 Authorization 헤더를 반환한다."""
    email = f"pytest_{uuid.uuid4().hex}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpass123", "display_name": "pytest"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _unique_algorithm(base: str) -> str:
    """실제 DB에 남아있는 이전 실행의 문제와 충돌하지 않도록 매 테스트마다 고유한 알고리즘 이름을 만든다."""
    return f"{base}_{uuid.uuid4().hex[:8]}"


def test_api_health_works():
    """Verify that existing health endpoint still works."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["agent_mode"] == "stub"


def test_api_generate_problem_requires_auth():
    """Verify POST /api/problems/generate rejects unauthenticated requests."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)

    payload = {"algorithm": "binary_search", "difficulty": "easy"}
    resp = client.post("/api/problems/generate", json=payload)
    assert resp.status_code == 401


def test_api_generate_problem_in_stub_mode():
    """Verify POST /api/problems/generate persists a validated problem in stub mode."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)
    headers = _auth_headers(client)

    algo = _unique_algorithm("binary_search")
    payload = {
        "algorithm": algo,
        "difficulty": "easy",
        "learning_goal": "상한액 C 이분 탐색",
    }

    resp = client.post("/api/problems/generate", json=payload, headers=headers)
    assert resp.status_code == 201
    body = resp.json()

    assert body["id"] == f"stub-{algo}-001"
    assert body["difficulty"] == "easy"
    assert body["learning_goal"] == "상한액 C 이분 탐색"
    assert "reference_solution" not in body

    # 조회도 동작해야 한다.
    get_resp = client.get(f"/api/problems/{body['id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == body["id"]


def test_api_generate_problem_omitted_defaults():
    """Verify request defaults apply cleanly."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)
    headers = _auth_headers(client)

    # Send absolute minimal payload (only required field)
    algo = _unique_algorithm("bfs")
    payload = {"algorithm": algo}

    resp = client.post("/api/problems/generate", json=payload, headers=headers)
    assert resp.status_code == 201
    body = resp.json()

    assert body["id"] == f"stub-{algo}-001"
    assert body["difficulty"] == "easy"  # Default value
    assert body["learning_goal"] == "기본 로직 이해"  # Default stub value
