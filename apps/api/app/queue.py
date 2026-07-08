"""채점 작업 큐 추상화 (BUILD_PLAN Step 4.1, ARCHITECTURE 2.6).

MVP는 인메모리(asyncio.Queue) 구현을 쓴다. 라우터는 `JudgeQueue` 인터페이스에만
의존하므로, 트래픽이 늘어 Redis+Celery 등으로 백엔드를 교체해도 라우터 코드는
바뀌지 않는다 (settings.queue_backend로 구현체를 선택).

핸들러는 submission_id(int)만 받는다 — 큐 반대편이 별도 프로세스(Redis 워커 등)일
수도 있으므로 요청 스코프의 SQLAlchemy Session을 넘기지 않는다. 핸들러는 자체
DB 세션을 연다.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

JudgeJobHandler = Callable[[int], Awaitable[None]]


class JudgeQueue(ABC):
    """채점 작업 큐 인터페이스. 라우터는 구현체가 아니라 이 인터페이스에만 의존한다."""

    @abstractmethod
    async def enqueue(self, submission_id: int) -> None:
        """제출 ID를 채점 큐에 등록한다. 즉시 반환하며 채점은 백그라운드에서 처리된다."""
        raise NotImplementedError


class InMemoryJudgeQueue(JudgeQueue):
    """asyncio.Queue 기반 인메모리 구현 — 워커 태스크가 순차적으로 소비한다.

    프로세스가 재시작되면 큐에 남아 있던 작업은 유실된다 (MVP 한계, ARCHITECTURE 2.6).
    """

    def __init__(self, handler: JudgeJobHandler, *, worker_count: int = 1) -> None:
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._handler = handler
        self._worker_count = worker_count
        self._workers: list[asyncio.Task] = []

    def start(self) -> None:
        """워커 태스크를 시작한다. 이미 시작된 경우 아무 일도 하지 않는다."""
        if self._workers:
            return
        for _ in range(self._worker_count):
            self._workers.append(asyncio.create_task(self._run_worker()))

    async def _run_worker(self) -> None:
        while True:
            submission_id = await self._queue.get()
            try:
                await self._handler(submission_id)
            except Exception:
                logger.exception("채점 워커 처리 중 오류 (submission_id=%s)", submission_id)
            finally:
                self._queue.task_done()

    async def enqueue(self, submission_id: int) -> None:
        self.start()
        await self._queue.put(submission_id)


_queue_instance: JudgeQueue | None = None


def get_judge_queue() -> JudgeQueue:
    """FastAPI 의존성 — 프로세스 싱글턴 큐 인스턴스를 반환한다.

    settings.queue_backend로 구현체를 선택한다. 현재 MVP는 "memory"만 지원한다.

    주의: 이 함수는 동기(def) 의존성이라 FastAPI가 스레드풀에서 실행하므로,
    여기서 `asyncio.create_task`(워커 시작)를 호출하면 "no running event loop"
    오류가 난다. 워커 시작은 이벤트 루프 위에서 실행되는 `enqueue()`가 지연 수행한다.
    """
    global _queue_instance
    if _queue_instance is None:
        from config.settings import settings

        if settings.queue_backend != "memory":
            raise NotImplementedError(
                f"queue_backend={settings.queue_backend!r}는 아직 지원하지 않습니다 "
                "(MVP는 memory만 지원, Redis 전환은 이후 단계)."
            )

        from app.judge_worker import judge_submission

        _queue_instance = InMemoryJudgeQueue(handler=judge_submission)
    return _queue_instance


def reset_judge_queue_for_testing() -> None:
    """테스트에서 싱글턴을 초기화하기 위한 헬퍼. 프로덕션 코드에서는 호출하지 않는다."""
    global _queue_instance
    _queue_instance = None
