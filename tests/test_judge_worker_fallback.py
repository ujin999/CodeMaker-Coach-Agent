"""judge_worker의 Judge0 폴백 정책 테스트 (error-fix/05_judge0_fallback_risk.md).

핵심 정책: Judge0가 설정되지 않았거나 hidden testcase가 없을 때 "항상 AC" 처리는
ENV=test 또는 AGENT_MODE=stub 환경에서만 허용되고, 그 외에는 JUDGE_ERROR가 되어야
한다. 채점 없이 AC가 만들어지면 SolvedRecord/커뮤니티 gating이 무력화되기 때문이다.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from app.judge_worker import _call_judge0, _is_dev_convenience_mode, judge_submission


def test_dev_convenience_mode_true_when_env_test(monkeypatch):
    monkeypatch.setenv("ENV", "test")
    monkeypatch.delenv("AGENT_MODE", raising=False)
    assert _is_dev_convenience_mode() is True


def test_dev_convenience_mode_true_when_agent_mode_stub(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("AGENT_MODE", "stub")
    assert _is_dev_convenience_mode() is True


def test_dev_convenience_mode_false_by_default(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("AGENT_MODE", raising=False)
    assert _is_dev_convenience_mode() is False


def test_call_judge0_missing_hidden_cases_is_judge_error_outside_dev_mode(monkeypatch):
    """운영/개발 모드에서 hidden testcase가 없으면 AC가 아니라 JUDGE_ERROR여야 한다."""
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("AGENT_MODE", raising=False)

    submission = MagicMock(problem_id="p1", language="python")
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []  # hidden testcase 없음

    result = asyncio.run(_call_judge0(submission, db))
    assert result["status"] == "JUDGE_ERROR"


def test_call_judge0_missing_hidden_cases_falls_back_to_ac_in_stub_mode(monkeypatch):
    """ENV=test/AGENT_MODE=stub에서는 기존처럼 개발 편의 AC 폴백이 유지된다."""
    monkeypatch.setenv("AGENT_MODE", "stub")
    monkeypatch.delenv("ENV", raising=False)

    submission = MagicMock(problem_id="p1", language="python")
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    result = asyncio.run(_call_judge0(submission, db))
    assert result["status"] == "AC"


def test_judge_submission_sets_judge_error_when_judge0_url_missing(monkeypatch):
    """JUDGE0_URL이 비어 있고 dev 편의 모드가 아니면 제출은 JUDGE_ERROR가 되어야 한다
    (채점 없이 조용히 AC가 되면 안 된다)."""
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("AGENT_MODE", raising=False)

    fake_submission = MagicMock(id=1, user_id=1, problem_id="p1", status="PENDING")
    fake_db = MagicMock()
    fake_db.get.return_value = fake_submission

    import app.judge_worker as jw
    from config.settings import settings

    monkeypatch.setattr(jw, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(settings, "judge0_url", "")

    asyncio.run(judge_submission(1))

    assert fake_submission.status == "JUDGE_ERROR"
    fake_db.close.assert_called_once()


def test_judge_submission_stub_ac_fallback_still_works_in_stub_mode(monkeypatch):
    """회귀 방지: ENV=test/AGENT_MODE=stub에서는 기존 개발 편의 동작(항상 AC)이 유지된다."""
    monkeypatch.setenv("AGENT_MODE", "stub")
    monkeypatch.delenv("ENV", raising=False)

    fake_submission = MagicMock(id=1, user_id=1, problem_id="p1", status="PENDING")
    fake_db = MagicMock()
    fake_db.get.return_value = fake_submission

    import app.judge_worker as jw
    from config.settings import settings

    monkeypatch.setattr(jw, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(settings, "judge0_url", "")

    asyncio.run(judge_submission(1))

    assert fake_submission.status == "AC"
