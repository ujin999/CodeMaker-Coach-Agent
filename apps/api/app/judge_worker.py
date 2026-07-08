"""채점 워커 — Judge0 REST 채점 실행 (BUILD_PLAN Step 4.2, FR-12~FR-14).

JudgeQueue(apps/api/app/queue.py)가 이 모듈의 judge_submission()을 핸들러로 사용한다.
요청 스코프 세션과 독립적으로 자체 DB 세션을 열어서, 큐 백엔드가 별도 프로세스로
바뀌어도(Redis 워커 등) 동일하게 동작하도록 한다.
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.problem import TestCase
from app.models.submission import LearningLog, SolvedRecord, Submission

logger = logging.getLogger(__name__)

# 언어 ID 매핑 (Judge0 기준)
_LANGUAGE_IDS = {"python": 71, "python3": 71, "java": 62, "cpp": 54, "c++": 54}

# Judge0 status id -> 내부 상태 코드 (packages/agent/tools/run_user_code.py와 동일한 매핑)
_STATUS_MAP = {3: "AC", 4: "WA", 5: "TLE", 6: "RE", 14: "MLE"}


async def judge_submission(submission_id: int) -> None:
    """제출을 채점하고 결과를 DB에 반영한다. JudgeQueue 핸들러로 등록되어 호출된다."""
    db = SessionLocal()
    try:
        submission = db.get(Submission, submission_id)
        if not submission:
            return

        submission.status = "JUDGING"
        db.commit()

        try:
            from config.settings import settings

            if settings.judge0_url:
                result = await _call_judge0(submission, db)
            else:
                # Judge0 미설정 시 개발용 stub: 항상 AC
                result = {"status": "AC", "runtime_ms": 100, "memory_kb": 1024}

            submission.status = result["status"]
            submission.runtime_ms = result.get("runtime_ms")
            submission.memory_kb = result.get("memory_kb")
            if result["status"] != "AC":
                submission.failed_testcase_name = result.get("failed_testcase_name")
                submission.failed_input = result.get("failed_input")
                submission.expected_output = result.get("expected_output")
                submission.actual_output = result.get("actual_output")
                submission.stderr = result.get("stderr")
            db.commit()

            # AC면 SolvedRecord 생성 (커뮤니티 gating용 — FR-30)
            if result["status"] == "AC":
                try:
                    db.add(SolvedRecord(user_id=submission.user_id, problem_id=submission.problem_id))
                    db.commit()
                except IntegrityError:
                    db.rollback()  # 이미 AC 기록 있음
            else:
                # 학습 로그 저장 (FR-24)
                db.add(LearningLog(
                    user_id=submission.user_id,
                    problem_id=submission.problem_id,
                    submission_id=submission.id,
                    error_type=result["status"],
                    resolved=False,
                ))
                db.commit()

            # Graph RAG Neo4j 실시간 연동 (Phase 4)
            try:
                from packages.graphrag import record_submission_to_graph
                user_email = submission.user.email if submission.user else f"user_{submission.user_id}@codemaker.io"
                prob_title = submission.problem.title if submission.problem else "Unknown"
                prob_diff = submission.problem.difficulty if submission.problem else "medium"
                prob_algos = submission.problem.algorithm if submission.problem else []
                
                record_submission_to_graph(
                    user_id=submission.user_id,
                    user_email=user_email,
                    problem_id=submission.problem_id,
                    problem_title=prob_title,
                    problem_difficulty=prob_diff,
                    problem_algorithms=prob_algos,
                    status=result["status"],
                )
            except Exception as graph_err:
                logger.warning(f"Failed to record submission to Neo4j graph: {graph_err}")

        except Exception:
            logger.exception("채점 워커 오류 (submission_id=%s)", submission_id)
            submission.status = "RE"
            db.commit()
    finally:
        db.close()


async def _call_judge0(submission: Submission, db: Session) -> dict:
    """Judge0 REST API 호출 — hidden testcase 기준 채점.

    timeout/memory/network 제한은 Judge0 인스턴스 설정(infra/judge0.conf)에서 강제된다 (NFR-1).
    """
    from config.settings import settings

    hidden_cases = (
        db.query(TestCase)
        .filter(TestCase.problem_id == submission.problem_id, TestCase.type == "hidden")
        .all()
    )
    if not hidden_cases:
        return {"status": "AC", "runtime_ms": 0, "memory_kb": 0}

    language_id = _LANGUAGE_IDS.get(submission.language.lower(), 71)

    headers = {}
    if settings.judge0_auth_token:
        headers["X-Auth-Token"] = settings.judge0_auth_token

    worst_status = "AC"
    worst_runtime = 0
    worst_memory = 0
    failed_details = {}

    async with httpx.AsyncClient(base_url=settings.judge0_url, timeout=30) as client:
        for tc in hidden_cases[:5]:  # 최대 5케이스
            payload = {
                "source_code": submission.code,
                "language_id": language_id,
                "stdin": tc.input,
                "expected_output": tc.expected_output,
            }
            resp = await client.post("/submissions?wait=true", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            status_id = data.get("status", {}).get("id", 3)
            tc_status = _STATUS_MAP.get(status_id, "RE")

            if tc_status != "AC":
                worst_status = tc_status
                
                import base64
                def decode_val(val):
                    if not val:
                        return val
                    try:
                        return base64.b64decode(val.encode()).decode("utf-8")
                    except Exception:
                        return val

                stdout = decode_val(data.get("stdout"))
                stderr = decode_val(data.get("stderr") or data.get("compile_output"))
                
                failed_details = {
                    "failed_testcase_name": f"hidden-{tc.id}",
                    "failed_input": tc.input,
                    "expected_output": tc.expected_output,
                    "actual_output": stdout,
                    "stderr": stderr,
                }
                break

            worst_runtime = max(worst_runtime, int(float(data.get("time", 0) or 0) * 1000))
            worst_memory = max(worst_memory, int(data.get("memory", 0) or 0))

    return {
        "status": worst_status,
        "runtime_ms": worst_runtime,
        "memory_kb": worst_memory,
        **failed_details
    }
