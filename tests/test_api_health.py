"""feat/api-foundation DoD 테스트: /health + AgentGateway stub."""

from __future__ import annotations

import asyncio
import os

from fastapi.testclient import TestClient


def test_health_returns_ok():
    os.environ["AGENT_MODE"] = "stub"
    from app.main import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["agent_mode"] == "stub"


def test_stub_gateway_generate_problem():
    from agent.schemas import ProblemGenerationInput
    from app.gateway import StubAgentGateway

    gw = StubAgentGateway()
    spec = ProblemGenerationInput(algorithm="binary_search", difficulty="medium")
    problem = asyncio.run(gw.generate_problem(spec))

    assert problem.problem_id
    assert problem.algorithm == ["binary_search"]
    assert problem.hint_blueprint is not None


def test_stub_gateway_hint_gating():
    """allowed_level 을 넘는 힌트는 반환되면 안 된다."""
    from agent.schemas import ProblemGenerationInput
    from app.gateway import StubAgentGateway

    gw = StubAgentGateway()
    spec = ProblemGenerationInput(algorithm="hash", difficulty="medium")
    problem = asyncio.run(gw.generate_problem(spec))

    bundle = asyncio.run(gw.generate_hints(problem, allowed_level=1))
    assert all(h.level <= 1 for h in bundle.hints)
    assert len(bundle.hints) == 1


def test_stub_gateway_conforms_to_protocol():
    from app.gateway import AgentGateway, StubAgentGateway

    assert isinstance(StubAgentGateway(), AgentGateway)
