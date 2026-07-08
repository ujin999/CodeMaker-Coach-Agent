"""JudgeQueue 추상화 테스트 (BUILD_PLAN Step 4.1).

DoD: enqueue한 작업을 백그라운드 워커가 소비한다.
"""

from __future__ import annotations

import asyncio

import pytest

from app.queue import InMemoryJudgeQueue, get_judge_queue, reset_judge_queue_for_testing


def test_enqueue_is_consumed_by_background_worker():
    """enqueue한 작업을 백그라운드 워커가 소비한다 (Step 4.1 DoD)."""
    processed: list[int] = []

    async def handler(submission_id: int) -> None:
        processed.append(submission_id)

    async def scenario() -> None:
        queue = InMemoryJudgeQueue(handler=handler)
        await queue.enqueue(1)
        await queue.enqueue(2)
        await queue._queue.join()

    asyncio.run(scenario())
    assert sorted(processed) == [1, 2]


def test_worker_survives_handler_exception():
    """핸들러가 예외를 던져도 워커가 죽지 않고 다음 작업을 계속 처리한다."""
    processed: list[int] = []

    async def handler(submission_id: int) -> None:
        if submission_id == 1:
            raise RuntimeError("boom")
        processed.append(submission_id)

    async def scenario() -> None:
        queue = InMemoryJudgeQueue(handler=handler)
        await queue.enqueue(1)
        await queue.enqueue(2)
        await queue._queue.join()

    asyncio.run(scenario())
    assert processed == [2]


def test_get_judge_queue_is_a_process_singleton(monkeypatch):
    """get_judge_queue()는 동일 인스턴스를 반환한다 (FastAPI Depends용)."""
    from config.settings import settings

    reset_judge_queue_for_testing()
    monkeypatch.setattr(settings, "queue_backend", "memory")
    try:
        q1 = get_judge_queue()
        q2 = get_judge_queue()
        assert q1 is q2
        assert isinstance(q1, InMemoryJudgeQueue)
    finally:
        reset_judge_queue_for_testing()


def test_get_judge_queue_does_not_require_running_event_loop(monkeypatch):
    """get_judge_queue()는 동기 FastAPI 의존성으로 스레드풀에서 실행되므로,
    실행 중인 이벤트 루프가 없어도 (asyncio.create_task 없이) 안전하게 호출되어야 한다.
    """
    from config.settings import settings

    reset_judge_queue_for_testing()
    monkeypatch.setattr(settings, "queue_backend", "memory")
    try:
        # 이 시점에는 실행 중인 이벤트 루프가 없다. asyncio.create_task를
        # 즉시 호출했다면 여기서 RuntimeError가 발생했을 것이다.
        queue = get_judge_queue()
        assert queue is not None
    finally:
        reset_judge_queue_for_testing()


def test_get_judge_queue_rejects_unsupported_backend(monkeypatch):
    from config.settings import settings

    reset_judge_queue_for_testing()
    monkeypatch.setattr(settings, "queue_backend", "redis")
    try:
        with pytest.raises(NotImplementedError):
            get_judge_queue()
    finally:
        reset_judge_queue_for_testing()
