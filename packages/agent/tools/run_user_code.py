"""Judge0 클라이언트 — 코드 실행을 Judge0 샌드박스에 위임한다 (BUILD_PLAN Step 3.1).

timeout/memory/network 제한은 Judge0 인스턴스 설정(infra/judge0.conf)에서 강제되며,
이 클라이언트는 결과를 정규화해서 돌려주는 역할만 한다.
"""

from __future__ import annotations

import httpx

from config.settings import settings

_LANGUAGE_IDS = {
    "python": 71,
    "python3": 71,
    "java": 62,
    "cpp": 54,
    "c++": 54,
}

# Judge0 status id -> 내부 상태 코드 (apps/api의 submissions.py와 동일한 매핑을 사용한다)
_STATUS_MAP = {
    3: "AC",
    4: "WA",
    5: "TLE",
    6: "RE",
    14: "MLE",
}


def run_code(source_code: str, language: str, stdin: str = "", expected_output: str | None = None) -> dict:
    """Judge0에 코드를 제출하고 정규화된 실행 결과를 반환한다.

    Returns:
        {"status": "AC"|"WA"|"TLE"|"CE"|"RE"|"MLE", "stdout": str, "stderr": str,
         "time_ms": int, "memory_kb": int}
    """
    language_id = _LANGUAGE_IDS.get(language.lower(), 71)

    headers = {}
    if settings.judge0_auth_token:
        headers["X-Auth-Token"] = settings.judge0_auth_token

    payload = {
        "source_code": source_code,
        "language_id": language_id,
        "stdin": stdin,
    }
    if expected_output is not None:
        payload["expected_output"] = expected_output

    with httpx.Client(base_url=settings.judge0_url, timeout=30) as client:
        resp = client.post("/submissions?wait=true", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    status_id = data.get("status", {}).get("id", 13)
    status = _STATUS_MAP.get(status_id, "RE")

    return {
        "status": status,
        "stdout": data.get("stdout") or "",
        "stderr": data.get("stderr") or data.get("compile_output") or "",
        "time_ms": int(float(data.get("time", 0) or 0) * 1000),
        "memory_kb": int(data.get("memory", 0) or 0),
    }
