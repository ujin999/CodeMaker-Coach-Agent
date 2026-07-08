"use client";

import { useState } from "react";
import { ApiError, communityApi } from "@/lib/api";
import type { Comment, SharedSolution } from "@/lib/types";

export default function SharedSolutionCard({
  solution,
}: {
  solution: SharedSolution;
}) {
  const [likes, setLikes] = useState(solution.likes_count);
  const [liked, setLiked] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState<Comment[] | null>(null);
  const [newComment, setNewComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleLike() {
    try {
      await communityApi.toggleLike(solution.id);
      setLiked((prev) => !prev);
      setLikes((prev) => (liked ? prev - 1 : prev + 1));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "좋아요 처리에 실패했습니다.");
    }
  }

  async function toggleComments() {
    const next = !showComments;
    setShowComments(next);
    if (next && !comments) {
      try {
        const list = await communityApi.listComments(solution.id);
        setComments(list);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "댓글을 불러오지 못했습니다.");
      }
    }
  }

  async function handleAddComment() {
    if (!newComment.trim()) return;
    try {
      const c = await communityApi.addComment(solution.id, {
        content: newComment.trim(),
      });
      setComments((prev) => [...(prev ?? []), c]);
      setNewComment("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "댓글 등록에 실패했습니다.");
    }
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-white">{solution.title}</h3>
          <p className="text-xs text-muted">
            사용자 #{solution.user_id} ·{" "}
            {new Date(solution.created_at).toLocaleDateString("ko-KR")}
          </p>
        </div>
      </div>
      {solution.description && (
        <p className="mt-2 whitespace-pre-wrap text-sm text-muted">
          {solution.description}
        </p>
      )}

      {solution.code && (
        <div className="mt-3">
          <div className="flex items-center justify-between rounded-t-lg bg-surface-2 px-3 py-1.5 text-xs text-muted border border-border">
            <span>공유된 코드 ({solution.language || "python"})</span>
          </div>
          <pre className="max-h-[300px] overflow-auto rounded-b-lg border border-t-0 border-border bg-bg p-3.5 text-xs font-mono text-slate-300 whitespace-pre">
            <code>{solution.code}</code>
          </pre>
        </div>
      )}

      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}

      <div className="mt-3 flex items-center gap-4 text-sm">
        <button
          onClick={handleLike}
          className={`rounded-md border px-2.5 py-1 ${
            liked ? "border-brand text-brand" : "border-border text-muted hover:text-white"
          }`}
        >
          ♥ {likes}
        </button>
        <button onClick={toggleComments} className="text-muted hover:text-white">
          댓글 {showComments ? "숨기기" : "보기"}
        </button>
      </div>

      {showComments && (
        <div className="mt-3 flex flex-col gap-2 border-t border-border pt-3">
          {comments?.map((c) => (
            <div key={c.id} className="text-sm">
              <span className="font-medium text-white">#{c.user_id}</span>{" "}
              <span className="text-muted">{c.content}</span>
            </div>
          ))}
          {comments?.length === 0 && (
            <p className="text-xs text-muted">아직 댓글이 없습니다.</p>
          )}
          <div className="mt-1 flex gap-2">
            <input
              type="text"
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="댓글을 입력하세요"
              className="flex-1 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-sm text-white outline-none focus:border-brand"
            />
            <button
              onClick={handleAddComment}
              className="rounded-md bg-brand px-3 py-1.5 text-sm text-white hover:bg-brand-hover"
            >
              등록
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
