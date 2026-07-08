"""문제 신고 / HITL 검토 테스트 — POST/DELETE/GET /api/problems/{id}/report,
GET /api/admin/problems/flagged, POST /api/admin/problems/{id}/review.
"""

from __future__ import annotations

import os
import uuid

from fastapi.testclient import TestClient

os.environ["AGENT_MODE"] = "stub"


def _get_app():
    from app.main import app
    return app


def _auth_headers(client: TestClient) -> tuple[dict, int]:
    email = f"pytest_{uuid.uuid4().hex}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpass123", "display_name": "pytest"},
    )
    assert resp.status_code == 201
    body = resp.json()
    token = body["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me.json()["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


def _make_admin(user_id: int) -> None:
    from app.db import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        user.is_admin = True
        db.commit()
    finally:
        db.close()


def _generate_problem(client: TestClient, headers: dict) -> str:
    algo = f"report_hitl_{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/problems/generate", json={"algorithm": algo}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_report_then_status_and_cancel():
    client = TestClient(_get_app())
    headers, _ = _auth_headers(client)
    problem_id = _generate_problem(client, headers)

    resp = client.post(
        f"/api/problems/{problem_id}/report",
        json={"reason": "예제 출력이 문제 설명과 맞지 않습니다."},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["report_count"] == 1
    assert body["status"] == "active"

    status_resp = client.get(f"/api/problems/{problem_id}/report", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json() == {
        "problem_id": problem_id,
        "report_count": 1,
        "reported_by_me": True,
        "status": "active",
    }

    cancel_resp = client.delete(f"/api/problems/{problem_id}/report", headers=headers)
    assert cancel_resp.status_code == 204

    status_resp2 = client.get(f"/api/problems/{problem_id}/report", headers=headers)
    assert status_resp2.json()["report_count"] == 0
    assert status_resp2.json()["reported_by_me"] is False


def test_duplicate_report_is_rejected():
    client = TestClient(_get_app())
    headers, _ = _auth_headers(client)
    problem_id = _generate_problem(client, headers)

    first = client.post(
        f"/api/problems/{problem_id}/report", json={"reason": "reason 1"}, headers=headers
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/problems/{problem_id}/report", json={"reason": "reason 2"}, headers=headers
    )
    assert second.status_code == 409


def test_cancel_without_existing_report_is_404():
    client = TestClient(_get_app())
    headers, _ = _auth_headers(client)
    problem_id = _generate_problem(client, headers)

    resp = client.delete(f"/api/problems/{problem_id}/report", headers=headers)
    assert resp.status_code == 404


def test_threshold_crossing_hides_problem_from_public_catalog():
    client = TestClient(_get_app())
    owner_headers, owner_id = _auth_headers(client)
    problem_id = _generate_problem(client, owner_headers)

    from config.settings import settings

    threshold = settings.problem_report_threshold
    reporter_headers_list = [_auth_headers(client)[0] for _ in range(threshold)]

    last_body = None
    for i, headers in enumerate(reporter_headers_list):
        resp = client.post(
            f"/api/problems/{problem_id}/report",
            json={"reason": f"reason {i}"},
            headers=headers,
        )
        assert resp.status_code == 201
        last_body = resp.json()

    assert last_body["report_count"] == threshold
    assert last_body["status"] == "under_review"

    # 공개 카탈로그(mine=false)에서는 숨겨진다.
    catalog = client.get("/api/problems?limit=500", headers=owner_headers)
    assert problem_id not in [p["id"] for p in catalog.json()]

    # 본인 문제 목록(mine=true)에서는 계속 보인다.
    mine = client.get("/api/problems?mine=true&limit=500", headers=owner_headers)
    assert problem_id in [p["id"] for p in mine.json()]

    # 직접 조회는 계속 가능하고 상태가 노출된다.
    detail = client.get(f"/api/problems/{problem_id}", headers=owner_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "under_review"


def test_admin_endpoints_require_admin():
    client = TestClient(_get_app())
    headers, _ = _auth_headers(client)
    problem_id = _generate_problem(client, headers)

    resp = client.get("/api/admin/problems/flagged", headers=headers)
    assert resp.status_code == 403

    resp2 = client.post(
        f"/api/admin/problems/{problem_id}/review",
        json={"action": "dismiss"},
        headers=headers,
    )
    assert resp2.status_code == 403


def test_admin_dismiss_clears_reports_and_restores_active():
    client = TestClient(_get_app())
    owner_headers, owner_id = _auth_headers(client)
    admin_headers, admin_id = _auth_headers(client)
    _make_admin(admin_id)

    problem_id = _generate_problem(client, owner_headers)

    from config.settings import settings

    threshold = settings.problem_report_threshold
    for i in range(threshold):
        h, _ = _auth_headers(client)
        r = client.post(
            f"/api/problems/{problem_id}/report", json={"reason": f"r{i}"}, headers=h
        )
        assert r.status_code == 201
    assert r.json()["status"] == "under_review"

    flagged = client.get("/api/admin/problems/flagged", headers=admin_headers)
    assert flagged.status_code == 200
    assert any(p["id"] == problem_id for p in flagged.json())
    flagged_entry = next(p for p in flagged.json() if p["id"] == problem_id)
    assert flagged_entry["report_count"] == threshold
    assert len(flagged_entry["reports"]) == threshold

    review = client.post(
        f"/api/admin/problems/{problem_id}/review",
        json={"action": "dismiss"},
        headers=admin_headers,
    )
    assert review.status_code == 200
    assert review.json() == {"id": problem_id, "status": "active", "report_count": 0}

    status_resp = client.get(f"/api/problems/{problem_id}/report", headers=owner_headers)
    assert status_resp.json()["report_count"] == 0

    catalog = client.get("/api/problems?limit=500", headers=owner_headers)
    assert problem_id in [p["id"] for p in catalog.json()]


def test_admin_remove_soft_deletes_and_hides_from_catalog():
    client = TestClient(_get_app())
    owner_headers, _ = _auth_headers(client)
    admin_headers, admin_id = _auth_headers(client)
    _make_admin(admin_id)

    problem_id = _generate_problem(client, owner_headers)
    client.post(f"/api/problems/{problem_id}/report", json={"reason": "bad"}, headers=owner_headers)

    review = client.post(
        f"/api/admin/problems/{problem_id}/review",
        json={"action": "remove"},
        headers=admin_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "removed"

    catalog = client.get("/api/problems?limit=500", headers=owner_headers)
    assert problem_id not in [p["id"] for p in catalog.json()]

    # 직접 조회는 여전히 가능(감사/디버깅 목적) — 404로 완전히 숨기지는 않는다.
    detail = client.get(f"/api/problems/{problem_id}", headers=owner_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "removed"


def test_admin_edit_updates_fields_and_restores_active():
    client = TestClient(_get_app())
    owner_headers, _ = _auth_headers(client)
    admin_headers, admin_id = _auth_headers(client)
    _make_admin(admin_id)

    problem_id = _generate_problem(client, owner_headers)
    client.post(f"/api/problems/{problem_id}/report", json={"reason": "typo"}, headers=owner_headers)

    review = client.post(
        f"/api/admin/problems/{problem_id}/review",
        json={"action": "edit", "title": "수정된 제목", "difficulty": "hard"},
        headers=admin_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "active"
    assert review.json()["report_count"] == 0

    detail = client.get(f"/api/problems/{problem_id}", headers=owner_headers)
    assert detail.json()["title"] == "수정된 제목"
    assert detail.json()["difficulty"] == "hard"
