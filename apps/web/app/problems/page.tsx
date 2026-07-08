"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ApiError, problemsApi, authApi } from "@/lib/api";
import { ALGORITHM_CATEGORIES, DIFFICULTY_LEVELS } from "@/lib/constants";
import type { ProblemSummary, UserWeaknessesResponse } from "@/lib/types";
import ProblemCard from "@/components/ProblemCard";

type SortKey = "recent" | "difficulty";

const DIFFICULTY_ORDER: Record<string, number> = { easy: 0, medium: 1, hard: 2 };

export default function ProblemCatalogPage() {
  const [problems, setProblems] = useState<ProblemSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [weaknessReport, setWeaknessReport] = useState<UserWeaknessesResponse | null>(null);

  const [algorithms, setAlgorithms] = useState<string[]>([]);
  const [difficulties, setDifficulties] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortKey>("recent");

  useEffect(() => {
    problemsApi
      .list({ limit: 100 })
      .then(setProblems)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "문제 목록을 불러오지 못했습니다.")
      )
      .finally(() => setLoading(false));

    authApi.weaknesses()
      .then(setWeaknessReport)
      .catch(() => {});
  }, []);

  function toggleAlgorithm(value: string) {
    setAlgorithms((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  function toggleDifficulty(value: string) {
    setDifficulties((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  function clearFilters() {
    setAlgorithms([]);
    setDifficulties([]);
    setSearch("");
  }

  // 백엔드가 아직 algorithm/difficulty/q 필터를 지원하지 않으므로(apps/web/README.md 참조),
  // 받아온 목록을 클라이언트에서 필터링·정렬한다.
  const filtered = useMemo(() => {
    let result = problems;
    if (algorithms.length > 0) {
      result = result.filter((p) => p.algorithm.some((a) => algorithms.includes(a)));
    }
    if (difficulties.length > 0) {
      result = result.filter((p) => difficulties.includes(p.difficulty));
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.learning_goal.toLowerCase().includes(q)
      );
    }
    const sorted = [...result];
    if (sort === "difficulty") {
      sorted.sort(
        (a, b) =>
          (DIFFICULTY_ORDER[a.difficulty] ?? 99) -
          (DIFFICULTY_ORDER[b.difficulty] ?? 99)
      );
    } else {
      sorted.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    }
    return sorted;
  }, [problems, algorithms, difficulties, search, sort]);

  const hasActiveFilters =
    algorithms.length > 0 || difficulties.length > 0 || search.trim().length > 0;

  return (
    <div className="grid gap-8 lg:grid-cols-[260px_1fr]">
      <aside className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold text-white">문제 둘러보기</h1>
          <p className="mt-1 text-sm text-muted">
            난이도·알고리즘 유형으로 원하는 문제를 찾아보세요.
          </p>
        </div>

        <div>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="제목 또는 학습 목표 검색"
            className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-brand"
          />
        </div>

        <div>
          <p className="text-sm font-medium text-muted">난이도</p>
          <div className="mt-2 flex flex-col gap-1.5">
            {DIFFICULTY_LEVELS.map((d) => (
              <label
                key={d.value}
                className="flex items-center gap-2 text-sm text-muted hover:text-white"
              >
                <input
                  type="checkbox"
                  checked={difficulties.includes(d.value)}
                  onChange={() => toggleDifficulty(d.value)}
                  className="accent-brand"
                />
                {d.label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <p className="text-sm font-medium text-muted">알고리즘 분류</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {ALGORITHM_CATEGORIES.map((a) => (
              <button
                key={a.value}
                onClick={() => toggleAlgorithm(a.value)}
                className={`rounded-full border px-3 py-1 text-xs ${
                  algorithms.includes(a.value)
                    ? "border-brand bg-brand/20 text-white"
                    : "border-border text-muted hover:text-white"
                }`}
              >
                {a.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="text-sm font-medium text-muted">정렬</p>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className="mt-2 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-brand"
          >
            <option value="recent">최신순</option>
            <option value="difficulty">난이도순</option>
          </select>
        </div>

        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="rounded-md border border-border px-3 py-2 text-sm text-muted hover:text-white"
          >
            필터 초기화
          </button>
        )}
      </aside>

      <section>
        {/* AI 취약점 진단 대시보드 (Phase 4) */}
        {!loading && weaknessReport && (
          <div className="mb-6 rounded-xl border border-brand/20 bg-brand/5 p-5 text-sm">
            <h2 className="text-base font-bold text-brand mb-4 flex items-center gap-2">
              🤖 AI 맞춤 취약점 분석 대시보드
            </h2>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {/* 1. 취약 개념 게이지 */}
              <div className="rounded-lg bg-surface-2 p-4">
                <p className="font-semibold text-white mb-3">⚠️ 취약 알고리즘 TOP 3</p>
                {weaknessReport.weak_concepts.length === 0 ? (
                  <p className="text-xs text-muted py-2">아직 감지된 취약 알고리즘이 없습니다.</p>
                ) : (
                  <div className="flex flex-col gap-3">
                    {weaknessReport.weak_concepts.map((wc, i) => {
                      const nameKo = {
                        binary_search: "이분 탐색",
                        bfs: "너비 우선 탐색 (BFS)",
                        dfs: "깊이 우선 탐색 (DFS)",
                        two_pointer: "투 포인터",
                        dp_basic: "동적 계획법 (DP)",
                        greedy: "그리디 알고리즘",
                        hash: "해시 (Hash Map)"
                      }[wc.concept] || wc.concept;
                      const percentage = Math.min(100, (wc.score / 10.0) * 100);
                      return (
                        <div key={i}>
                          <div className="flex justify-between text-xs text-muted mb-1">
                            <span>{nameKo}</span>
                            <span>{wc.score} / 10.0</span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-border overflow-hidden">
                            <div
                              className="h-full bg-orange-500 transition-all"
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* 2. 잦은 오답 패턴 */}
              <div className="rounded-lg bg-surface-2 p-4">
                <p className="font-semibold text-white mb-3">❌ 자주 발생한 오답</p>
                {weaknessReport.top_errors.length === 0 ? (
                  <p className="text-xs text-muted py-2">아직 오답 이력이 누적되지 않았습니다.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {weaknessReport.top_errors.map((te, i) => {
                      const errKo = {
                        WA: "틀렸습니다 (Wrong Answer)",
                        TLE: "시간 초과 (Time Limit)",
                        RE: "런타임 에러 (Runtime Error)",
                        MLE: "메모리 초과 (Memory Limit)"
                      }[te.error_type] || te.error_type;
                      return (
                        <div
                          key={i}
                          className="flex items-center gap-2 rounded-md bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-white"
                        >
                          <span className="text-red-400 font-bold">●</span>
                          <span>{errKo}</span>
                          <span className="bg-red-500/20 px-1.5 py-0.5 rounded text-red-300 font-semibold">
                            {te.count}회
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* 3. AI 맞춤 추천 및 숏컷 */}
              <div className="rounded-lg bg-surface-2 p-4 flex flex-col justify-between">
                <div>
                  <p className="font-semibold text-white mb-2">🎯 AI 학습 코치 가이드</p>
                  <p className="text-xs text-muted leading-relaxed">
                    {weaknessReport.recommendation}
                  </p>
                </div>
                {weaknessReport.weak_concepts.length > 0 && (
                  <div className="mt-3">
                    <Link
                      href={`/generate?algorithm=${weaknessReport.weak_concepts[0].concept}`}
                      className="block text-center rounded-md bg-brand py-2 text-xs font-semibold text-white hover:bg-brand-hover transition-colors"
                    >
                      취약점 저격 문제 즉시 생성 🎯
                    </Link>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {loading && <p className="text-muted">불러오는 중...</p>}
        {error && <p className="text-red-400">{error}</p>}
        {!loading && !error && filtered.length === 0 && (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border py-20 text-center text-muted">
            <p>조건에 맞는 문제가 없습니다.</p>
            <Link href="/generate" className="text-brand hover:underline">
              새 문제 생성하러 가기
            </Link>
          </div>
        )}
        {!loading && !error && filtered.length > 0 && (
          <>
            <p className="mb-4 text-sm text-muted">총 {filtered.length}개 문제</p>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {filtered.map((p) => (
                <ProblemCard key={p.id} problem={p} />
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
