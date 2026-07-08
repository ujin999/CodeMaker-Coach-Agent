"use client";
 
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, communityApi, submissionsApi } from "@/lib/api";
import type { SharedSolution, SubmissionResponse } from "@/lib/types";
import SharedSolutionCard from "@/components/SharedSolutionCard";
 
type OrderBy = "recent" | "popular";
 
export default function CommunityPage({
  params,
}: {
  params: { problemId: string };
}) {
  const { problemId } = params;
  const searchParams = useSearchParams();
  const prefillSubmissionId = searchParams.get("submissionId");
 
  const [solutions, setSolutions] = useState<SharedSolution[] | null>(null);
  const [gated, setGated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [order, setOrder] = useState<OrderBy>("recent");
 
  const [showShareForm, setShowShareForm] = useState(!!prefillSubmissionId);
  const [submissionId, setSubmissionId] = useState(prefillSubmissionId ?? "");
  const [submission, setSubmission] = useState<SubmissionResponse | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sharing, setSharing] = useState(false);
  const [shareError, setShareError] = useState<string | null>(null);
 
  useEffect(() => {
    if (submissionId) {
      submissionsApi
        .get(Number(submissionId))
        .then(setSubmission)
        .catch(() => setSubmission(null));
    } else {
      setSubmission(null);
    }
  }, [submissionId]);
 
  function load(orderBy: OrderBy) {
    communityApi
      .listForProblem(problemId, orderBy)
      .then((list) => {
        setSolutions(list);
        setGated(false);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setGated(true);
        } else {
          setError(
            err instanceof ApiError ? err.message : "공유 풀이를 불러오지 못했습니다."
          );
        }
      });
  }

  useEffect(() => {
    load(order);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [problemId, order]);

  async function handleShare(e: React.FormEvent) {
    e.preventDefault();
    setShareError(null);
    setSharing(true);
    try {
      await communityApi.share({
        submission_id: Number(submissionId),
        title,
        description: description || undefined,
        is_public: true,
      });
      setShowShareForm(false);
      setTitle("");
      setDescription("");
      setSubmissionId("");
      load(order);
    } catch (err) {
      setShareError(err instanceof ApiError ? err.message : "공유에 실패했습니다.");
    } finally {
      setSharing(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">커뮤니티 풀이</h1>
        <div className="flex gap-2">
          <select
            value={order}
            onChange={(e) => setOrder(e.target.value as OrderBy)}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-white outline-none focus:border-brand"
          >
            <option value="recent">최신순</option>
            <option value="popular">인기순</option>
          </select>
          <button
            onClick={() => setShowShareForm((v) => !v)}
            className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-hover"
          >
            내 풀이 공유하기
          </button>
        </div>
      </div>

      {showShareForm && (
        <form
          onSubmit={handleShare}
          className="mt-4 flex flex-col gap-3 rounded-xl border border-border bg-surface p-5"
        >
          <p className="text-sm text-muted">
            정답(AC) 처리된 제출만 공유할 수 있습니다.
          </p>
          <input
            type="number"
            required
            value={submissionId}
            onChange={(e) => setSubmissionId(e.target.value)}
            placeholder="제출 ID (AC 받은 제출)"
            className="rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-white outline-none focus:border-brand"
          />
          <input
            type="text"
            required
            maxLength={255}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="풀이 제목"
            className="rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-white outline-none focus:border-brand"
          />
          {submission && (
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-muted">제출 코드 ({submission.language})</label>
              <pre className="max-h-[200px] overflow-auto rounded-md border border-border bg-bg p-3 text-xs font-mono text-slate-300 whitespace-pre">
                <code>{submission.code}</code>
              </pre>
            </div>
          )}
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="풀이 설명 (선택)"
            rows={3}
            className="rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-white outline-none focus:border-brand"
          />
          {shareError && <p className="text-sm text-red-400">{shareError}</p>}
          <button
            type="submit"
            disabled={sharing}
            className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
          >
            {sharing ? "공유 중..." : "공유하기"}
          </button>
        </form>
      )}

      <div className="mt-6">
        {gated && (
          <div className="rounded-xl border border-dashed border-border py-16 text-center text-muted">
            <p>이 문제를 먼저 직접 풀어(AC) 다른 사람의 풀이를 볼 수 있습니다.</p>
          </div>
        )}
        {error && <p className="text-red-400">{error}</p>}
        {!gated && !error && solutions && solutions.length === 0 && (
          <p className="text-center text-muted">아직 공유된 풀이가 없습니다.</p>
        )}
        {!gated && solutions && solutions.length > 0 && (
          <div className="flex flex-col gap-4">
            {solutions.map((s) => (
              <SharedSolutionCard key={s.id} solution={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
