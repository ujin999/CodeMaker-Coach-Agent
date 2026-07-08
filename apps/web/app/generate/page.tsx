"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ApiError, problemsApi } from "@/lib/api";
import { ALGORITHM_CATEGORIES, DIFFICULTY_LEVELS, LANGUAGES } from "@/lib/constants";
import type { ProblemDetail } from "@/lib/types";
import DifficultyBadge from "@/components/DifficultyBadge";

function GenerateForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [algorithm, setAlgorithm] = useState(ALGORITHM_CATEGORIES[0].value);

  useEffect(() => {
    const algoParam = searchParams.get("algorithm");
    if (algoParam && ALGORITHM_CATEGORIES.some((a) => a.value === algoParam)) {
      setAlgorithm(algoParam);
    }
  }, [searchParams]);

  const [difficulty, setDifficulty] = useState("easy");
  const [language, setLanguage] = useState(LANGUAGES[0].value);
  const [learningGoal, setLearningGoal] = useState("");
  const [problemStyle, setProblemStyle] = useState("");
  const [weaknesses, setWeaknesses] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<ProblemDetail | null>(null);
  const [avoidProblemIds, setAvoidProblemIds] = useState<string[]>([]);
  const [focusWeaknesses, setFocusWeaknesses] = useState(true);

    function createClientSeed(): string {
    if (
      typeof globalThis !== "undefined" &&
      globalThis.crypto &&
      typeof globalThis.crypto.randomUUID === "function"
    ) {
      return globalThis.crypto.randomUUID();
    }

    return `seed_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  }

  function toggleWeakness(value: string) {
    setWeaknesses((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setPreview(null);
    try {
      const problem = await problemsApi.generate({
        algorithm,
        difficulty,
        language,
        learning_goal: learningGoal || undefined,
        problem_style: problemStyle || undefined,
        recent_weaknesses: weaknesses,
        seed: createClientSeed(),
        force_new: true,
        avoid_problem_ids: avoidProblemIds,
        focus_weaknesses: focusWeaknesses,
      });
      setPreview(problem);
      if (problem?.id) {
        setAvoidProblemIds((prev) => [...prev, problem.id]);
      }
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "문제 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[380px_1fr]">
      <div>
        <h1 className="text-2xl font-bold text-white">문제 생성</h1>
        <p className="mt-1 text-sm text-muted">
          알고리즘 유형과 난이도를 선택하면 AI가 새 문제를 생성합니다.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-5">
          <div>
            <label className="text-sm font-medium text-muted">알고리즘 유형</label>
            <select
              value={algorithm}
              onChange={(e) => setAlgorithm(e.target.value)}
              className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-white outline-none focus:border-brand"
            >
              {ALGORITHM_CATEGORIES.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-muted">난이도</label>
            <div className="mt-1.5 flex gap-2">
              {DIFFICULTY_LEVELS.map((d) => (
                <button
                  type="button"
                  key={d.value}
                  onClick={() => setDifficulty(d.value)}
                  className={`flex-1 rounded-md border px-3 py-2 text-sm ${
                    difficulty === d.value
                      ? "border-brand bg-surface-2 text-white"
                      : "border-border text-muted hover:text-white"
                  }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-md border border-brand/20 bg-brand/5 p-3">
            <input
              type="checkbox"
              id="focusWeaknesses"
              checked={focusWeaknesses}
              onChange={(e) => setFocusWeaknesses(e.target.checked)}
              className="h-4 w-4 rounded border-border bg-surface text-brand outline-none focus:ring-0 accent-brand cursor-pointer"
            />
            <label htmlFor="focusWeaknesses" className="text-sm font-medium text-white cursor-pointer select-none">
              AI 취약점 극복 옵션 적용 (추천)
            </label>
          </div>

          <div>
            <label className="text-sm font-medium text-muted">프로그래밍 언어</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-white outline-none focus:border-brand"
            >
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-muted">
              학습 목표 (선택)
            </label>
            <input
              type="text"
              value={learningGoal}
              onChange={(e) => setLearningGoal(e.target.value)}
              placeholder="예) 매개 변수 탐색과 경계값 처리"
              className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-white outline-none focus:border-brand"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-muted">
              문제 스타일 (선택)
            </label>
            <input
              type="text"
              value={problemStyle}
              onChange={(e) => setProblemStyle(e.target.value)}
              placeholder="예) practical, mathematical"
              className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-white outline-none focus:border-brand"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-muted">
              최근 취약점 (선택)
            </label>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {ALGORITHM_CATEGORIES.map((a) => (
                <button
                  type="button"
                  key={a.value}
                  onClick={() => toggleWeakness(a.value)}
                  className={`rounded-full border px-3 py-1 text-xs ${
                    weaknesses.includes(a.value)
                      ? "border-brand bg-brand/20 text-white"
                      : "border-border text-muted hover:text-white"
                  }`}
                >
                  {a.label}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-brand px-4 py-2.5 font-medium text-white hover:bg-brand-hover disabled:opacity-50"
          >
            {loading ? "생성 중... (검증 포함, 최대 1분)" : "문제 생성하기"}
          </button>
        </form>
      </div>

      <div>
        {!preview && !loading && (
          <div className="flex h-full min-h-[300px] items-center justify-center rounded-xl border border-dashed border-border text-muted">
            생성된 문제 미리보기가 여기에 표시됩니다.
          </div>
        )}
        {loading && (
          <div className="flex h-full min-h-[300px] items-center justify-center rounded-xl border border-border bg-surface text-muted">
            AI가 문제를 생성하고 검증하는 중입니다...
          </div>
        )}
        {preview && (
          <div className="rounded-xl border border-border bg-surface p-6">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-xl font-bold text-white">{preview.title}</h2>
              <DifficultyBadge difficulty={preview.difficulty} />
            </div>
            <div className="flex items-center gap-2 mt-2 flex-wrap text-xs text-muted">
              <span>ID: {preview.id}</span>
              {preview.generation_mode && (
                <span className="rounded-full bg-surface-2 border border-border px-2.5 py-0.5">
                  Mode: {preview.generation_mode}
                </span>
              )}
              {preview.variant_id && (
                <span className="rounded-full bg-surface-2 border border-border px-2.5 py-0.5">
                  Variant: {preview.variant_id}
                </span>
              )}
            </div>
            <p className="mt-3 text-sm text-muted">{preview.learning_goal}</p>
            <div className="prose prose-invert prose-sm mt-4 max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {preview.statement}
              </ReactMarkdown>
            </div>
            <div className="mt-4 grid gap-3 text-sm text-muted sm:grid-cols-2">
              <div>
                <p className="font-medium text-white">입력 형식</p>
                <p>{preview.input_format}</p>
              </div>
              <div>
                <p className="font-medium text-white">출력 형식</p>
                <p>{preview.output_format}</p>
              </div>
            </div>
            {preview.sample_input && (
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-white">예제 입력</p>
                  <pre className="mt-1 overflow-x-auto rounded-md bg-surface-2 p-3 text-xs text-muted">
                    {preview.sample_input}
                  </pre>
                </div>
                <div>
                  <p className="text-sm font-medium text-white">예제 출력</p>
                  <pre className="mt-1 overflow-x-auto rounded-md bg-surface-2 p-3 text-xs text-muted">
                    {preview.sample_output}
                  </pre>
                </div>
              </div>
            )}
            <button
              onClick={() => router.push(`/solve/${preview.id}`)}
              className="mt-6 w-full rounded-md bg-brand px-4 py-2.5 font-medium text-white hover:bg-brand-hover"
            >
              풀이 시작하기
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function GeneratePage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-[400px] items-center justify-center text-muted">
        폼을 로드하는 중...
      </div>
    }>
      <GenerateForm />
    </Suspense>
  );
}
