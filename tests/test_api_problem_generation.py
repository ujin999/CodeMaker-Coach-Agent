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


def test_api_generate_problem_with_seed():
    """Verify POST /api/problems/generate accepts seed, returns metadata, and ensures diversity/stability."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)
    headers = _auth_headers(client)

    algo = _unique_algorithm("api_seed_test")
    
    # 1. First generation with seed_A
    resp1 = client.post(
        "/api/problems/generate",
        json={"algorithm": algo, "seed": "seed_A"},
        headers=headers,
    )
    assert resp1.status_code == 201
    body1 = resp1.json()
    assert body1["seed"] == "seed_A"
    assert body1["generation_mode"] == "template_fallback"
    assert body1["variant_id"] == "var_seed_A"
    assert "reference_solution" not in body1
    assert "code" not in body1

    # 2. Second generation with seed_B (should return a different problem ID and title)
    resp2 = client.post(
        "/api/problems/generate",
        json={"algorithm": algo, "seed": "seed_B"},
        headers=headers,
    )
    assert resp2.status_code == 201
    body2 = resp2.json()
    assert body2["seed"] == "seed_B"
    assert body2["id"] != body1["id"]
    assert body2["title"] != body1["title"]
    assert body2["variant_id"] == "var_seed_B"

    # 3. Third generation with seed_A (should return the same problem as body1 due to DB caching of the exact same problem_id)
    resp3 = client.post(
        "/api/problems/generate",
        json={"algorithm": algo, "seed": "seed_A"},
        headers=headers,
    )
    assert resp3.status_code == 201
    body3 = resp3.json()
    assert body3["id"] == body1["id"]
    assert body3["title"] == body1["title"]
    assert body3["variant_id"] == "var_seed_A"


def test_api_generate_problem_force_new():
    """Verify that force_new=True does not silently return an existing DB row."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)
    headers = _auth_headers(client)
    algo = _unique_algorithm("force_new_check")

    # 1. Generate once
    resp1 = client.post(
        "/api/problems/generate",
        json={"algorithm": algo, "seed": "seed_A"},
        headers=headers,
    )
    assert resp1.status_code == 201
    body1 = resp1.json()

    # 2. Try to generate again with force_new=True (should raise HTTP 409 Conflict because same content exists, preventing silent reuse)
    resp2 = client.post(
        "/api/problems/generate",
        json={"algorithm": algo, "seed": "seed_A", "force_new": True},
        headers=headers,
    )
    assert resp2.status_code == 409


def test_api_generate_problem_variants_content():
    """Verify that generated variants match variant keywords (e.g. cable_cutting)."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)
    headers = _auth_headers(client)

    # Find a seed that results in "cable_cutting" variant for "binary_search"
    # Or we can just check what variant gets selected for a few seeds and check title/statement keywords.
    for seed in ["seed_a", "seed_b", "seed_c", "seed_d", "seed_e"]:
        resp = client.post(
            "/api/problems/generate",
            json={"algorithm": "binary_search", "seed": seed},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        variant_id = body["variant_id"]
        title = body["title"]
        statement = body["statement"]

        if variant_id == "cable_cutting":
            assert any(kw in title or kw in statement for kw in ["랜선", "자르기", "케이블", "나무"])
        elif variant_id == "router_installation":
            assert any(kw in title or kw in statement for kw in ["공유기", "설치", "거리"])
        elif variant_id == "immigration_time":
            assert any(kw in title or kw in statement for kw in ["심사", "입국심사", "시간"])



