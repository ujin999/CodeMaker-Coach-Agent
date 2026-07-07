import asyncio
import inspect
import pytest
from agent.schemas import HintRequestPackageInput, HintRequestPackage, Hint, HintBundle
from agent.services import (
    request_hint_package,
    request_hint_package_sync,
    hint_package_to_dict,
    can_promote_hint_level
)


def test_request_hint_package_is_coroutine_function():
    """Test A: request_hint_package is an async coroutine function."""
    assert inspect.iscoroutinefunction(request_hint_package)


def test_hint_request_blocked_when_requested_level_exceeds_allowed():
    """Test B & D: requested_level > allowed_level is blocked and returned hints are limited."""
    inp = HintRequestPackageInput(
        problem_id="prob_1",
        allowed_level=1,
        requested_level=2
    )
    
    generated = [
        Hint(problem_id="prob_1", level=1, title="L1 Title", content="L1 Content"),
        Hint(problem_id="prob_1", level=2, title="L2 Title", content="L2 Content"),
    ]
    
    res = request_hint_package_sync(inp, generated_hints=generated)
    
    assert res.blocked is True
    assert res.delivered_level == 1
    assert "아직 허용되지 않은 힌트 단계" in res.block_reason
    assert len(res.hints) == 1
    assert res.hints[0].level == 1


def test_hint_filtering_by_allowed_level():
    """Test C: hints are filtered correctly by allowed_level."""
    inp = HintRequestPackageInput(
        problem_id="prob_1",
        allowed_level=2,
        requested_level=2
    )
    
    generated = [
        Hint(problem_id="prob_1", level=1, title="L1 Title", content="L1 Content"),
        Hint(problem_id="prob_1", level=2, title="L2 Title", content="L2 Content"),
        Hint(problem_id="prob_1", level=3, title="L3 Title", content="L3 Content"),
    ]
    
    res = request_hint_package_sync(inp, generated_hints=generated)
    
    assert res.blocked is False
    assert len(res.hints) == 1
    assert res.hints[0].level == 2  # prefers requested level


def test_hint_reveals_core_code_policy():
    """Test E: reveals_core_code=True makes safe_to_show False."""
    inp = HintRequestPackageInput(
        problem_id="prob_1",
        allowed_level=2,
        requested_level=2
    )
    
    h = Hint(problem_id="prob_1", level=2, title="L2 Title", content="Code: ...")
    object.__setattr__(h, "reveals_core_code", True)
    generated = [h]
    
    res = request_hint_package_sync(inp, generated_hints=generated)
    assert len(res.hints) == 0 or res.safe_to_show is False

    # Verify directly that HintRequestPackage validator flags safe_to_show as False if a leaking hint is inside it
    pkg = HintRequestPackage(
        problem_id="prob_1",
        allowed_level=2,
        requested_level=2,
        delivered_level=2,
        hints=generated,
        summary="Test"
    )
    assert pkg.safe_to_show is False


def test_search_hints_failure_fallback(monkeypatch):
    """Test F: search_hints failure does not crash service."""
    # Mock search_hints to raise exception
    import rag
    monkeypatch.setattr(rag, "search_hints", lambda *args, **kwargs: exec("raise(Exception('Qdrant error'))"))
    
    inp = HintRequestPackageInput(
        problem_id="prob_1",
        allowed_level=1,
        requested_level=1
    )
    
    res = request_hint_package_sync(inp, generated_hints=None)
    assert res.hints == []
    assert res.safe_to_show is True


def test_can_promote_hint_level():
    """Test G: can_promote_hint_level works correctly."""
    # Promoted case
    promoted, next_lvl, msg = can_promote_hint_level(1, user_confirmed=True)
    assert promoted is True
    assert next_lvl == 2
    assert "2단계" in msg
    
    # Non-confirmed case
    promoted, next_lvl, msg = can_promote_hint_level(1, user_confirmed=False)
    assert promoted is False
    assert next_lvl == 1
    
    # Max level case
    promoted, next_lvl, msg = can_promote_hint_level(3, user_confirmed=True)
    assert promoted is False
    assert next_lvl == 3


def test_hint_package_to_dict():
    """Test I: hint_package_to_dict returns JSON-safe dict."""
    inp = HintRequestPackageInput(problem_id="prob_1", allowed_level=1)
    res = request_hint_package_sync(inp, generated_hints=[])
    
    payload = hint_package_to_dict(res)
    assert isinstance(payload, dict)
    assert payload["problem_id"] == "prob_1"
    assert payload["allowed_level"] == 1
