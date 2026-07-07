from __future__ import annotations
import os
from fastapi.testclient import TestClient
from app.main import app


def test_api_health_works():
    """Verify that existing health endpoint still works."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["agent_mode"] == "stub"


def test_api_generate_problem_in_stub_mode():
    """Verify POST /api/problems/generate works with stub mode and defaults."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)

    payload = {
        "algorithm": "binary_search",
        "difficulty": "easy",
        "learning_goal": "상한액 C 이분 탐색"
    }

    resp = client.post("/api/problems/generate", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    assert "generated_problem" in body
    assert "testcase_bundle" in body
    assert "validation_report" in body
    assert "routing_decision" in body
    assert "gateway_mode" in body

    # Check stub response fields
    assert body["gateway_mode"] == "stub"
    assert body["generated_problem"]["problem_id"] == "stub-binary_search-001"
    assert body["generated_problem"]["difficulty"] == "easy"
    assert body["generated_problem"]["learning_goal"] == "상한액 C 이분 탐색"
    assert body["routing_decision"]["action"] == "present_to_user"


def test_api_generate_problem_omitted_defaults():
    """Verify request defaults apply cleanly."""
    os.environ["AGENT_MODE"] = "stub"
    client = TestClient(app)

    # Send absolute minimal payload
    payload = {
        "algorithm": "bfs"
    }

    resp = client.post("/api/problems/generate", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    assert body["gateway_mode"] == "stub"
    assert body["generated_problem"]["problem_id"] == "stub-bfs-001"
    assert body["generated_problem"]["difficulty"] == "easy"  # Default value
    assert body["generated_problem"]["learning_goal"] == "기본 로직 이해"  # Default stub value
