"use client";

import { useEffect, useState } from "react";
import { ApiError, problemsApi } from "@/lib/api";
import type { FlaggedProblem } from "@/lib/types";
import DifficultyBadge from "@/components/DifficultyBadge";

// 별도 관리자 계정 없이, 로그인한 모든 사용자가 신고 누적 문제를 검토/조치할 수 있다 (FR-34, HITL).
export default function ManageProblemsPage() {
  const [problems, setProblems] = useState<FlaggedProblem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDifficulty, setEditDifficulty] = useState("");
  const [editStatement, setEditStatement] = useState("");

  function load() {
    problemsApi
      .listFlagged()
      .then(setProblems)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "목록을 불러오지 못했습니다.")
      );
  }

  useEffect(() => {
    load();
  }, []);

  function startEdit(p: FlaggedProblem) {
    setEditingId(p.id);
    setEditTitle(p.title);
    setEditDifficulty(p.difficulty);
    setEditStatement(p.statement);
  }

  async function act(problemId: string, action: "dismiss" | "remove" | "edit") {
    setBusyId(problemId);
    try {
      if (action === "edit") {
        await problemsApi.review(problemId, {
          action: "edit",
          title: editTitle,
          difficulty: editDifficulty,
          statement: editStatement,
        });
        setEditingId(null);
      } else {
        await problemsApi.review(problemId, { action });
      }
      setProblems((prev) => (prev ? prev.filter((p) => p.id !== problemId) : prev));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "조치를 처리하지 못했습니다.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white">문제 관리</h1>
      <p className="mt-1 text-sm text-muted">
        신고가 누적되어 검토가 필요한 문제 목록입니다. 로그인한 누구나 신고 내용을
        확인하고 기각, 삭제, 수정 조치를 취할 수 있습니다.
      </p>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-6 flex flex-col gap-4">
        {problems === null && !error && <p className="text-muted">불러오는 중...</p>}
        {problems && problems.length === 0 && (
          <p className="text-center text-muted">검토 대기 중인 문제가 없습니다.</p>
        )}
        {problems?.map((p) => (
          <div key={p.id} className="rounded-xl border border-border bg-surface p-5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-white">{p.title}</h2>
                <DifficultyBadge difficulty={p.difficulty} />
              </div>
              <span className="text-xs text-red-400">신고 {p.report_count}건</span>
            </div>

            {editingId === p.id ? (
              <div className="mt-3 flex flex-col gap-2">
                <input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-white outline-none focus:border-brand"
                  placeholder="제목"
                />
                <select
                  value={editDifficulty}
                  onChange={(e) => setEditDifficulty(e.target.value)}
                  className="rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-white outline-none focus:border-brand"
                >
                  <option value="easy">easy</option>
                  <option value="medium">medium</option>
                  <option value="hard">hard</option>
                </select>
                <textarea
                  value={editStatement}
                  onChange={(e) => setEditStatement(e.target.value)}
                  rows={4}
                  className="rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-white outline-none focus:border-brand"
                  placeholder="문제 본문"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => act(p.id, "edit")}
                    disabled={busyId === p.id}
                    className="rounded-md bg-brand px-3 py-1.5 text-xs text-white hover:bg-brand-hover disabled:opacity-50"
                  >
                    수정 후 복구
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="rounded-md border border-border px-3 py-1.5 text-xs text-muted"
                  >
                    취소
                  </button>
                </div>
              </div>
            ) : (
              <>
                <p className="mt-2 whitespace-pre-wrap text-sm text-muted">
                  {p.statement.length > 300 ? `${p.statement.slice(0, 300)}...` : p.statement}
                </p>

                <div className="mt-3 flex flex-col gap-1.5 rounded-md bg-surface-2 p-3">
                  <p className="text-xs font-medium text-white">신고 사유</p>
                  {p.reports.map((r, i) => (
                    <p key={i} className="text-xs text-muted">
                      · {r.reason}
                    </p>
                  ))}
                </div>

                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => act(p.id, "dismiss")}
                    disabled={busyId === p.id}
                    className="rounded-md border border-border px-3 py-1.5 text-xs text-white hover:border-brand disabled:opacity-50"
                  >
                    기각(신고 초기화)
                  </button>
                  <button
                    onClick={() => startEdit(p)}
                    disabled={busyId === p.id}
                    className="rounded-md border border-border px-3 py-1.5 text-xs text-white hover:border-brand disabled:opacity-50"
                  >
                    수정
                  </button>
                  <button
                    onClick={() => act(p.id, "remove")}
                    disabled={busyId === p.id}
                    className="rounded-md border border-red-500/50 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                  >
                    삭제
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
