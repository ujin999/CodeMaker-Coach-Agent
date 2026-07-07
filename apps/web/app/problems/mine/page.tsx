"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, problemsApi } from "@/lib/api";
import type { ProblemSummary } from "@/lib/types";
import ProblemCard from "@/components/ProblemCard";

export default function MyProblemsPage() {
  const [problems, setProblems] = useState<ProblemSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    problemsApi
      .list({ limit: 100 })
      .then(setProblems)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "문제 목록을 불러오지 못했습니다.")
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-white">내 문제</h1>
      <p className="mt-1 text-sm text-muted">직접 생성한 문제 목록입니다.</p>

      <div className="mt-6">
        {loading && <p className="text-muted">불러오는 중...</p>}
        {error && <p className="text-red-400">{error}</p>}
        {!loading && !error && problems.length === 0 && (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border py-20 text-center text-muted">
            <p>아직 생성한 문제가 없습니다.</p>
            <Link href="/generate" className="text-brand hover:underline">
              새 문제 생성하러 가기
            </Link>
          </div>
        )}
        {!loading && !error && problems.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {problems.map((p) => (
              <ProblemCard key={p.id} problem={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
