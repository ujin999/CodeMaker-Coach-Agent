"""API 제출 리뷰 엔드포인트 테스트 — POST /api/submissions/review."""

from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
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


def test_review_requires_auth():
    """POST /api/submissions/review rejects unauthenticated requests."""
    client = TestClient(_get_app())
    payload = {
        "problem_id": "test-001",
        "user_code": "print(1)",
        "result_type": "WA",
    }
    resp = client.post("/api/submissions/review", json=payload)
    assert resp.status_code == 401


def test_review_returns_review_package():
    """POST /api/submissions/review returns a review package with expected fields."""
    client = TestClient(_get_app())
    headers = _auth_headers(client)

    from agent.schemas import SubmissionReviewPackage

    mock_package = SubmissionReviewPackage(
        problem_id="test-001",
        result_type="WA",
        summary="테스트 리뷰 요약",
        safe_to_show=True,
    )

    # Patch at the module level where the import lives
    with patch(
        "app.routers.submissions.review_submission_package",
        new_callable=AsyncMock,
        return_value=mock_package,
    ):
        payload = {
            "problem_id": "test-001",
            "problem_title": "Test Problem",
            "problem_difficulty": "easy",
            "problem_algorithm": ["greedy"],
            "problem_statement": "Solve it",
            "user_code": "print(1)",
            "language": "python",
            "result_type": "WA",
            "include_concept_context": False,
        }
        resp = client.post("/api/submissions/review", json=payload, headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["problem_id"] == "test-001"
    assert body["result_type"] == "WA"
    assert body["summary"] == "테스트 리뷰 요약"
    assert body["safe_to_show"] is True
    assert "reference_solution" not in body


def test_review_no_reference_solution_leak():
    """Verify review response never contains reference_solution."""
    client = TestClient(_get_app())
    headers = _auth_headers(client)

    from agent.schemas import SubmissionReviewPackage

    mock_package = SubmissionReviewPackage(
        problem_id="test-002",
        result_type="AC",
        summary="AC",
        safe_to_show=True,
    )

    with patch(
        "app.routers.submissions.review_submission_package",
        new_callable=AsyncMock,
        return_value=mock_package,
    ):
        payload = {
            "problem_id": "test-002",
            "user_code": "x=1",
            "result_type": "AC",
        }
        resp = client.post("/api/submissions/review", json=payload, headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert "reference_solution" not in body
    assert "code" not in body
