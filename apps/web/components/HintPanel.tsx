"use client";

import { useEffect, useState } from "react";
import { ApiError, hintsApi } from "@/lib/api";
import type { Hint, HintProgress } from "@/lib/types";
import ConfirmModal from "./ConfirmModal";

// 힌트는 챗봇 방식 — 사용자가 명시적으로 요청할 때만 응답한다.
// 허용 단계를 넘어서는 힌트는 서버가 물리적으로 차단하므로, 프론트는 서버가 준 것만 그대로 보여준다.
export default function HintPanel({ problemId }: { problemId: string }) {
  const [progress, setProgress] = useState<HintProgress | null>(null);
  const [hints, setHints] = useState<Hint[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [unlocking, setUnlocking] = useState(false);

  useEffect(() => {
    hintsApi
      .progress(problemId)
      .then(setProgress)
      .catch(() => setProgress(null));
  }, [problemId]);

  async function requestHints() {
    setLoading(true);
    setError(null);
    try {
      const list = await hintsApi.list(problemId);
      setHints(list);
      const p = await hintsApi.progress(problemId);
      setProgress(p);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "힌트를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function handleUnlock() {
    setUnlocking(true);
    setError(null);
    try {
      const p = await hintsApi.unlock(problemId, { confirm: true });
      setProgress(p);
      setConfirmOpen(false);
      const list = await hintsApi.list(problemId);
      setHints(list);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "단계 승급에 실패했습니다.");
    } finally {
      setUnlocking(false);
    }
  }

  const allowedLevel = progress?.allowed_level ?? 1;
  const maxedOut = allowedLevel >= 3;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white">AI 코치 힌트</h3>
        <span className="text-xs text-muted">
          현재 허용 단계: {allowedLevel} / 3
        </span>
      </div>

      <div className="flex flex-col gap-3">
        {!hints && (
          <p className="text-sm text-muted">
            막히는 부분이 있으면 힌트를 요청해보세요. 정답 코드는 절대 제공되지 않으며,
            구조(스켈레톤)까지만 안내합니다.
          </p>
        )}
        {hints?.map((h) => (
          <div
            key={h.level}
            className="rounded-lg border border-border bg-surface-2 p-3 text-sm"
          >
            <p className="font-medium text-white">
              {h.level}단계 · {h.title}
            </p>
            <p className="mt-1 whitespace-pre-wrap text-muted">{h.content}</p>
            {h.code_skeleton && (
              <div className="mt-2">
                <p className="text-xs font-medium text-muted">
                  구조 스켈레톤 (핵심 로직은 직접 작성)
                </p>
                <pre className="mt-1 overflow-x-auto rounded-md bg-bg p-2 text-xs text-slate-300">
                  {h.code_skeleton}
                </pre>
              </div>
            )}
            {h.concept_refs.length > 0 && (
              <p className="mt-2 text-xs text-muted">
                관련 개념: {h.concept_refs.join(", ")}
              </p>
            )}
          </div>
        ))}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="flex flex-col gap-2">
        <button
          onClick={requestHints}
          disabled={loading}
          className="rounded-md border border-border px-3 py-2 text-sm text-white hover:border-brand disabled:opacity-50"
        >
          {loading ? "불러오는 중..." : hints ? "힌트 새로고침" : "힌트 요청하기"}
        </button>
        {!maxedOut ? (
          <button
            onClick={() => setConfirmOpen(true)}
            className="rounded-md bg-surface-2 px-3 py-2 text-sm text-muted hover:text-white"
          >
            다음 단계 힌트 열기 ({allowedLevel + 1}단계)
          </button>
        ) : (
          <p className="text-center text-xs text-muted">
            이미 최고 단계(3단계) 힌트까지 허용되었습니다.
          </p>
        )}
      </div>

      <ConfirmModal
        open={confirmOpen}
        title="다음 단계 힌트를 여시겠습니까?"
        description="힌트 단계가 올라가면 더 구체적인 접근 방법이 공개됩니다. 스스로 풀이를 시도해본 후 여는 것을 권장합니다."
        confirmLabel={unlocking ? "처리 중..." : "다음 단계 열기"}
        onConfirm={handleUnlock}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
