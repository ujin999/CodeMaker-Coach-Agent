"""문제 신고 / HITL 검토 테스트 — POST/DELETE/GET /api/problems/{id}/report,
GET /api/problems/flagged, POST /api/problems/{id}/review.

별도 관리자 계정 없이 로그인한 모든 사용자가 문제 관리(HITL 검토)에 참여할 수 있다.
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


def test_flagged_and_review_endpoints_require_only_login():
    """관리자 계정 없이 로그인한 아무 사용자나 문제 관리 기능을 쓸 수 있다."""
    client = TestClient(_get_app())
    headers, _ = _auth_headers(client)
    problem_id = _generate_problem(client, headers)

    resp = client.get("/api/problems/flagged", headers=headers)
    assert resp.status_code == 200

    resp2 = client.post(
        f"/api/problems/{problem_id}/review",
        json={"action": "dismiss"},
        headers=headers,
    )
    assert resp2.status_code == 200


def test_flagged_and_review_require_auth():
    client = TestClient(_get_app())

    resp = client.get("/api/problems/flagged")
    assert resp.status_code == 401

    resp2 = client.post("/api/problems/some-id/review", json={"action": "dismiss"})
    assert resp2.status_code == 401


def test_dismiss_clears_reports_and_restores_active():
    client = TestClient(_get_app())
    owner_headers, _ = _auth_headers(client)
    reviewer_headers, _ = _auth_headers(client)

    problem_id = _generate_problem(client, owner_headers)

    from config.settings import settings

    threshold = settings.problem_report_threshold
    r = None
    for i in range(threshold):
        h, _ = _auth_headers(client)
        r = client.post(
            f"/api/problems/{problem_id}/report", json={"reason": f"r{i}"}, headers=h
        )
        assert r.status_code == 201
    assert r.json()["status"] == "under_review"

    flagged = client.get("/api/problems/flagged", headers=reviewer_headers)
    assert flagged.status_code == 200
    assert any(p["id"] == problem_id for p in flagged.json())
    flagged_entry = next(p for p in flagged.json() if p["id"] == problem_id)
    assert flagged_entry["report_count"] == threshold
    assert len(flagged_entry["reports"]) == threshold

    review = client.post(
        f"/api/problems/{problem_id}/review",
        json={"action": "dismiss"},
        headers=reviewer_headers,
    )
    assert review.status_code == 200
    assert review.json() == {"id": problem_id, "status": "active", "report_count": 0}

    status_resp = client.get(f"/api/problems/{problem_id}/report", headers=owner_headers)
    assert status_resp.json()["report_count"] == 0

    catalog = client.get("/api/problems?limit=500", headers=owner_headers)
    assert problem_id in [p["id"] for p in catalog.json()]


def test_remove_soft_deletes_and_hides_from_catalog():
    client = TestClient(_get_app())
    owner_headers, _ = _auth_headers(client)
    reviewer_headers, _ = _auth_headers(client)

    problem_id = _generate_problem(client, owner_headers)
    client.post(f"/api/problems/{problem_id}/report", json={"reason": "bad"}, headers=owner_headers)

    review = client.post(
        f"/api/problems/{problem_id}/review",
        json={"action": "remove"},
        headers=reviewer_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "removed"

    catalog = client.get("/api/problems?limit=500", headers=owner_headers)
    assert problem_id not in [p["id"] for p in catalog.json()]

    # 직접 조회는 여전히 가능(감사/디버깅 목적) — 404로 완전히 숨기지는 않는다.
    detail = client.get(f"/api/problems/{problem_id}", headers=owner_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "removed"


def test_edit_updates_fields_and_restores_active():
    client = TestClient(_get_app())
    owner_headers, _ = _auth_headers(client)
    reviewer_headers, _ = _auth_headers(client)

    problem_id = _generate_problem(client, owner_headers)
    client.post(f"/api/problems/{problem_id}/report", json={"reason": "typo"}, headers=owner_headers)

    review = client.post(
        f"/api/problems/{problem_id}/review",
        json={"action": "edit", "title": "수정된 제목", "difficulty": "hard"},
        headers=reviewer_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "active"
    assert review.json()["report_count"] == 0

    detail = client.get(f"/api/problems/{problem_id}", headers=owner_headers)
    assert detail.json()["title"] == "수정된 제목"
    assert detail.json()["difficulty"] == "hard"


# ── Agent 사전 판정 (신고누적흐름.txt) — HITL 이전 critical/safe 자동 처리 ──────────

class _FakeAssessmentGateway:
    """threshold 도달 시 assess_problem_report()가 고정된 판정을 반환하는 가짜 게이트웨이.

    generate_problem_package는 실제 StubAgentGateway로 위임해 문제 생성은 정상 동작시킨다.
    """

    def __init__(self, severity: str):
        self._severity = severity
        self._delegate = None

    def _get_delegate(self):
        if self._delegate is None:
            from app.gateway import StubAgentGateway
            self._delegate = StubAgentGateway()
        return self._delegate

    async def generate_problem_package(self, request):
        return await self._get_delegate().generate_problem_package(request)

    async def assess_problem_report(self, **kwargs):
        return {
            "problem_id": kwargs["problem_id"],
            "severity": self._severity,
            "reasoning": f"TEST FAKE: forced {self._severity}",
            "confidence": "high",
        }

    # 아래는 이 테스트 경로에서 쓰이지 않지만 AgentGateway 프로토콜을 만족시키기 위해 위임한다.
    async def generate_problem(self, *a, **kw):
        return await self._get_delegate().generate_problem(*a, **kw)

    async def generate_testcases(self, *a, **kw):
        return await self._get_delegate().generate_testcases(*a, **kw)

    async def generate_hints(self, *a, **kw):
        return await self._get_delegate().generate_hints(*a, **kw)

    async def search_hints(self, *a, **kw):
        return await self._get_delegate().search_hints(*a, **kw)

    async def analyze_feedback(self, *a, **kw):
        return await self._get_delegate().analyze_feedback(*a, **kw)


def _override_gateway(app, severity: str):
    from app.routers.problems import _dep_gateway

    fake = _FakeAssessmentGateway(severity)
    app.dependency_overrides[_dep_gateway] = lambda: fake


def test_agent_critical_assessment_auto_deletes_without_human_review():
    app = _get_app()
    client = TestClient(app)
    try:
        owner_headers, _ = _auth_headers(client)
        problem_id = _generate_problem(client, owner_headers)

        _override_gateway(app, "critical")

        from config.settings import settings

        threshold = settings.problem_report_threshold
        last = None
        for i in range(threshold):
            h, _ = _auth_headers(client)
            last = client.post(
                f"/api/problems/{problem_id}/report", json={"reason": f"r{i}"}, headers=h
            )
            assert last.status_code == 201

        assert last.json()["status"] == "removed"

        # 삭제됐으므로 검토 대기 목록(flagged)에는 없어야 한다 — HITL을 거치지 않았다.
        flagged = client.get("/api/problems/flagged", headers=owner_headers)
        assert problem_id not in [p["id"] for p in flagged.json()]

        catalog = client.get("/api/problems?limit=500", headers=owner_headers)
        assert problem_id not in [p["id"] for p in catalog.json()]
    finally:
        app.dependency_overrides.clear()


def test_agent_safe_assessment_auto_dismisses_without_human_review():
    app = _get_app()
    client = TestClient(app)
    try:
        owner_headers, _ = _auth_headers(client)
        problem_id = _generate_problem(client, owner_headers)

        _override_gateway(app, "safe")

        from config.settings import settings

        threshold = settings.problem_report_threshold
        last = None
        for i in range(threshold):
            h, _ = _auth_headers(client)
            last = client.post(
                f"/api/problems/{problem_id}/report", json={"reason": f"r{i}"}, headers=h
            )
            assert last.status_code == 201

        assert last.json()["status"] == "active"
        assert last.json()["report_count"] == 0  # 오신고 판단 -> 신고 초기화

        # active 상태이므로 검토 대기 목록에 없고, 공개 카탈로그에는 그대로 남아있다.
        flagged = client.get("/api/problems/flagged", headers=owner_headers)
        assert problem_id not in [p["id"] for p in flagged.json()]

        catalog = client.get("/api/problems?limit=500", headers=owner_headers)
        assert problem_id in [p["id"] for p in catalog.json()]
    finally:
        app.dependency_overrides.clear()


def test_agent_minor_assessment_falls_back_to_human_review():
    app = _get_app()
    client = TestClient(app)
    try:
        owner_headers, _ = _auth_headers(client)
        problem_id = _generate_problem(client, owner_headers)

        _override_gateway(app, "minor")

        from config.settings import settings

        threshold = settings.problem_report_threshold
        last = None
        for i in range(threshold):
            h, _ = _auth_headers(client)
            last = client.post(
                f"/api/problems/{problem_id}/report", json={"reason": f"r{i}"}, headers=h
            )
            assert last.status_code == 201

        assert last.json()["status"] == "under_review"

        flagged = client.get("/api/problems/flagged", headers=owner_headers)
        assert problem_id in [p["id"] for p in flagged.json()]
    finally:
        app.dependency_overrides.clear()
