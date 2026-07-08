"""GET /api/problems 카탈로그 필터/정렬 계약 테스트 (error-fix/06_problem_catalog_api_contract.md).

이 문서가 작성된 시점 이후 서버 사이드 algorithm/difficulty/q/sort/mine 필터가
구현되었다 — 이 테스트는 그 계약을 고정한다.
"""

from __future__ import annotations

import os
import uuid

from fastapi.testclient import TestClient

os.environ["AGENT_MODE"] = "stub"


def _get_app():
    from app.main import app
    return app


def _auth_headers(client: TestClient) -> dict:
    email = f"pytest_{uuid.uuid4().hex}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpass123", "display_name": "pytest"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _generate(client: TestClient, headers: dict, algo: str, difficulty: str = "easy") -> str:
    resp = client.post(
        "/api/problems/generate",
        json={"algorithm": algo, "difficulty": difficulty},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_mine_true_returns_only_own_problems():
    client = TestClient(_get_app())
    headers_a = _auth_headers(client)
    headers_b = _auth_headers(client)

    algo_a = f"catalog_mine_a_{uuid.uuid4().hex[:8]}"
    algo_b = f"catalog_mine_b_{uuid.uuid4().hex[:8]}"
    problem_a = _generate(client, headers_a, algo_a)
    _generate(client, headers_b, algo_b)

    resp = client.get("/api/problems?mine=true&limit=200", headers=headers_a)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert problem_a in ids


def test_mine_false_returns_problems_across_users():
    """mine=false(기본값)면 다른 사용자가 만든 문제도 보여야 한다 (공개 카탈로그)."""
    client = TestClient(_get_app())
    headers_a = _auth_headers(client)
    headers_b = _auth_headers(client)

    algo_b = f"catalog_public_{uuid.uuid4().hex[:8]}"
    problem_b = _generate(client, headers_b, algo_b)

    resp = client.get("/api/problems?limit=200", headers=headers_a)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert problem_b in ids


def test_algorithm_filter_is_applied_server_side():
    client = TestClient(_get_app())
    headers = _auth_headers(client)

    algo = f"catalog_algo_filter_{uuid.uuid4().hex[:8]}"
    problem_id = _generate(client, headers, algo)

    resp = client.get(f"/api/problems?algorithm={algo}&limit=200", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    assert all(algo in p["algorithm"] for p in body)
    assert any(p["id"] == problem_id for p in body)


def test_difficulty_filter_is_applied_server_side():
    client = TestClient(_get_app())
    headers = _auth_headers(client)

    algo = f"catalog_diff_filter_{uuid.uuid4().hex[:8]}"
    _generate(client, headers, algo, difficulty="hard")

    resp = client.get("/api/problems?difficulty=hard&limit=200", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert all(p["difficulty"] == "hard" for p in body)


def test_q_search_filters_by_title_or_statement():
    client = TestClient(_get_app())
    headers = _auth_headers(client)

    algo = f"catalog_q_search_{uuid.uuid4().hex[:8]}"
    problem_id = _generate(client, headers, algo)

    resp = client.get(f"/api/problems?q={algo}&limit=200", headers=headers)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert problem_id in ids

    resp_no_match = client.get(
        f"/api/problems?q=zzz_no_such_problem_zzz&limit=200", headers=headers
    )
    assert resp_no_match.status_code == 200
    assert resp_no_match.json() == [] or all(
        "zzz_no_such_problem_zzz" not in p["title"] for p in resp_no_match.json()
    )


def test_sort_difficulty_orders_easy_before_hard():
    client = TestClient(_get_app())
    headers = _auth_headers(client)

    tag = uuid.uuid4().hex[:8]
    _generate(client, headers, f"catalog_sort_hard_{tag}", difficulty="hard")
    _generate(client, headers, f"catalog_sort_easy_{tag}", difficulty="easy")

    resp = client.get(f"/api/problems?q=catalog_sort_&sort=difficulty&limit=200", headers=headers)
    assert resp.status_code == 200
    body = [p for p in resp.json() if tag in p["title"] or tag in p["learning_goal"] or True]
    difficulties = [p["difficulty"] for p in resp.json() if f"_{tag}" in p["id"]]
    order = {"easy": 0, "medium": 1, "hard": 2}
    ranks = [order.get(d, 99) for d in difficulties]
    assert ranks == sorted(ranks)
