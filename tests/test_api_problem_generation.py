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


def test_reveal_solution_requires_confirm_and_is_gated():
    """Verify reveal-solution requires confirm=true and returns the stub reference code once confirmed."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)
    headers = _auth_headers(client)

    algo = _unique_algorithm("reveal_check")
    gen_resp = client.post(
        "/api/problems/generate", json={"algorithm": algo}, headers=headers
    )
    assert gen_resp.status_code == 201
    problem_id = gen_resp.json()["id"]

    # confirm=false must be rejected
    rejected = client.post(
        f"/api/problems/{problem_id}/reveal-solution",
        json={"confirm": False},
        headers=headers,
    )
    assert rejected.status_code == 400

    # confirm=true reveals the code
    revealed = client.post(
        f"/api/problems/{problem_id}/reveal-solution",
        json={"confirm": True},
        headers=headers,
    )
    assert revealed.status_code == 200
    body = revealed.json()
    assert body["problem_id"] == problem_id
    assert body["language"] == "python"
    assert len(body["code"]) > 0

    # the general problem detail endpoint must never include the solution
    detail = client.get(f"/api/problems/{problem_id}", headers=headers)
    assert "reference_solution" not in detail.json()
    assert "code" not in detail.json()


def test_reveal_solution_unknown_problem_returns_404():
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)
    headers = _auth_headers(client)

    resp = client.post(
        "/api/problems/does-not-exist/reveal-solution",
        json={"confirm": True},
        headers=headers,
    )
    assert resp.status_code == 404


def test_report_problem():
    """Verify a problem can be reported and unknown problems 404."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)
    headers = _auth_headers(client)

    algo = _unique_algorithm("report_check")
    gen_resp = client.post(
        "/api/problems/generate", json={"algorithm": algo}, headers=headers
    )
    assert gen_resp.status_code == 201
    problem_id = gen_resp.json()["id"]

    resp = client.post(
        f"/api/problems/{problem_id}/report",
        json={"reason": "예제 출력이 설명과 맞지 않습니다."},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["problem_id"] == problem_id
    assert body["reason"] == "예제 출력이 설명과 맞지 않습니다."

    missing = client.post(
        "/api/problems/does-not-exist/report",
        json={"reason": "test"},
        headers=headers,
    )
    assert missing.status_code == 404
