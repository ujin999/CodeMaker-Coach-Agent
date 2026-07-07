"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ApiError, problemsApi, submissionsApi } from "@/lib/api";
import { LANGUAGES } from "@/lib/constants";
import type { SubmissionResponse, SubmissionStatus, ProblemDetail } from "@/lib/types";
import CodeEditor from "@/components/CodeEditor";
import ConfirmModal from "@/components/ConfirmModal";
import DifficultyBadge from "@/components/DifficultyBadge";
import HintPanel from "@/components/HintPanel";

const TERMINAL_STATUSES: SubmissionStatus[] = ["AC", "WA", "TLE", "RE", "MLE"];

const STATUS_STYLE: Record<SubmissionStatus, string> = {
  PENDING: "text-muted",
  JUDGING: "text-yellow-400",
  AC: "text-green-400",
  WA: "text-red-400",
  TLE: "text-orange-400",
  RE: "text-red-400",
  MLE: "text-orange-400",
};

const STATUS_LABEL: Record<SubmissionStatus, string> = {
  PENDING: "채점 대기중",
  JUDGING: "채점중...",
  AC: "정답 (Accepted)",
  WA: "오답 (Wrong Answer)",
  TLE: "시간 초과",
  RE: "런타임 에러",
  MLE: "메모리 초과",
};

export default function SolvePage({ params }: { params: { id: string } }) {
  const problemId = params.id;
  const router = useRouter();

  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [language, setLanguage] = useState(LANGUAGES[0].value);
  const [code, setCode] = useState("");

  const [submission, setSubmission] = useState<SubmissionResponse | null>(null);
  const [history, setHistory] = useState<SubmissionResponse[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const [revealOpen, setRevealOpen] = useState(false);
  const [revealCode, setRevealCode] = useState<string | null>(null);
  const [revealing, setRevealing] = useState(false);
  const [revealError, setRevealError] = useState<string | null>(null);

  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState("");
  const [reportSent, setReportSent] = useState(false);

  useEffect(() => {
    problemsApi
      .get(problemId)
      .then(setProblem)
      .catch((err) =>
        setLoadError(err instanceof ApiError ? err.message : "문제를 불러오지 못했습니다.")
      );
    submissionsApi
      .listForProblem(problemId)
      .then(setHistory)
      .catch(() => {});
  }, [problemId]);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  async function handleSubmit() {
    if (!code.trim()) {
      setSubmitError("코드를 입력해주세요.");
      return;
    }
    setSubmitError(null);
    setSubmitting(true);
    stopPolling();
    try {
      const created = await submissionsApi.submit(problemId, { code, language });
      setSubmission(created);

      pollTimer.current = setInterval(async () => {
        try {
          const latest = await submissionsApi.get(created.id);
          setSubmission(latest);
          if (TERMINAL_STATUSES.includes(latest.status)) {
            stopPolling();
            setSubmitting(false);
            submissionsApi.listForProblem(problemId).then(setHistory).catch(() => {});
          }
        } catch {
          stopPolling();
          setSubmitting(false);
        }
      }, 1500);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "제출에 실패했습니다.");
      setSubmitting(false);
    }
  }

  async function handleReveal() {
    setRevealing(true);
    setRevealError(null);
    try {
      const res = await problemsApi.revealSolution(problemId, { confirm: true });
      setRevealCode(res.code);
      setRevealOpen(false);
    } catch (err) {
      setRevealError(
        err instanceof ApiError ? err.message : "정답을 불러오지 못했습니다."
      );
    } finally {
      setRevealing(false);
    }
  }

  async function handleReport() {
    if (!reportReason.trim()) return;
    try {
      await problemsApi.report(problemId, { reason: reportReason.trim() });
      setReportSent(true);
      setReportOpen(false);
      setReportReason("");
    } catch {
      // 신고 실패는 조용히 무시 — 학습 흐름을 막지 않는다.
    }
  }

  if (loadError) {
    return <p className="text-red-400">{loadError}</p>;
  }
  if (!problem) {
    return <p className="text-muted">문제를 불러오는 중...</p>;
  }

  const isAC = submission?.status === "AC";

  return (
    <div className="grid gap-6 lg:grid-cols-[5fr_7fr]">
      {/* 좌측 — 문제 명세 */}
      <section className="flex flex-col gap-4">
        <div className="rounded-xl border border-border bg-surface p-6">
          <div className="flex items-center justify-between gap-2">
            <h1 className="text-xl font-bold text-white">{problem.title}</h1>
            <DifficultyBadge difficulty={problem.difficulty} />
          </div>
          <p className="mt-1 text-sm text-muted">{problem.learning_goal}</p>

          <div className="prose prose-invert prose-sm mt-4 max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {problem.statement}
            </ReactMarkdown>
          </div>

          <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <p className="font-medium text-white">입력 형식</p>
              <p className="text-muted">{problem.input_format}</p>
            </div>
            <div>
              <p className="font-medium text-white">출력 형식</p>
              <p className="text-muted">{problem.output_format}</p>
            </div>
          </div>

          {problem.constraints.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-white">제약 조건</p>
              <ul className="mt-1 list-inside list-disc text-sm text-muted">
                {problem.constraints.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}

          {problem.sample_input && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-sm font-medium text-white">예제 입력</p>
                <pre className="mt-1 overflow-x-auto rounded-md bg-surface-2 p-3 text-xs text-muted">
                  {problem.sample_input}
                </pre>
              </div>
              <div>
                <p className="text-sm font-medium text-white">예제 출력</p>
                <pre className="mt-1 overflow-x-auto rounded-md bg-surface-2 p-3 text-xs text-muted">
                  {problem.sample_output}
                </pre>
              </div>
            </div>
          )}

          <p className="mt-4 text-xs text-muted">
            예상 시간복잡도: {problem.expected_time_complexity}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          <button
            onClick={() => setRevealOpen(true)}
            className="w-full rounded-md border border-border px-3 py-2 text-sm text-muted hover:border-brand hover:text-white"
          >
            정답 보기
          </button>
          {revealError && (
            <p className="mt-2 text-sm text-red-400">{revealError}</p>
          )}
          {revealCode && (
            <div className="mt-3">
              <p className="text-xs font-medium text-white">공개된 정답 코드</p>
              <pre className="mt-1 overflow-x-auto rounded-md bg-bg p-3 text-xs text-slate-300">
                {revealCode}
              </pre>
            </div>
          )}

          <div className="mt-3 flex items-center justify-between">
            {reportOpen ? (
              <div className="flex w-full flex-col gap-2">
                <textarea
                  value={reportReason}
                  onChange={(e) => setReportReason(e.target.value)}
                  placeholder="신고 사유를 입력해주세요"
                  className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-white outline-none focus:border-brand"
                  rows={2}
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleReport}
                    className="rounded-md bg-brand px-3 py-1.5 text-xs text-white hover:bg-brand-hover"
                  >
                    신고 제출
                  </button>
                  <button
                    onClick={() => setReportOpen(false)}
                    className="rounded-md border border-border px-3 py-1.5 text-xs text-muted"
                  >
                    취소
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setReportOpen(true)}
                className="text-xs text-muted hover:text-white"
              >
                {reportSent ? "신고 접수됨 ✓" : "문제 품질 신고하기"}
              </button>
            )}
          </div>
        </div>

        <ConfirmModal
          open={revealOpen}
          title="정답을 확인하시겠습니까?"
          description="정답 코드는 학습 효과를 위해 기본적으로 비공개입니다. 확인 후에는 되돌릴 수 없습니다."
          confirmLabel={revealing ? "불러오는 중..." : "정답 보기"}
          onConfirm={handleReveal}
          onCancel={() => setRevealOpen(false)}
          danger
        />
      </section>

      {/* 우측 — 에디터 + 제출 + AI 코치 힌트 */}
      <section className="flex flex-col gap-4">
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="mb-3 flex items-center justify-between">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="rounded-md border border-border bg-surface-2 px-3 py-1.5 text-sm text-white outline-none focus:border-brand"
            >
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="rounded-md bg-brand px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
            >
              {submitting ? "채점 중..." : "제출하기"}
            </button>
          </div>

          <CodeEditor
            value={code}
            onChange={setCode}
            language={LANGUAGES.find((l) => l.value === language)?.monaco ?? "python"}
          />

          {submitError && <p className="mt-2 text-sm text-red-400">{submitError}</p>}

          {submission && (
            <div className="mt-3 rounded-md border border-border bg-surface-2 p-3 text-sm">
              <span className={`font-semibold ${STATUS_STYLE[submission.status]}`}>
                {STATUS_LABEL[submission.status]}
              </span>
              {submission.runtime_ms !== null && (
                <span className="ml-3 text-muted">{submission.runtime_ms}ms</span>
              )}
              {submission.memory_kb !== null && (
                <span className="ml-2 text-muted">{submission.memory_kb}KB</span>
              )}
            </div>
          )}

          {isAC && (
            <button
              onClick={() =>
                router.push(`/community/${problemId}?submissionId=${submission!.id}`)
              }
              className="mt-3 w-full rounded-md border border-brand px-3 py-2 text-sm text-brand hover:bg-brand/10"
            >
              🎉 정답입니다! 풀이 공유하러 가기
            </button>
          )}

          {history.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-medium text-muted">제출 이력</p>
              <div className="mt-1 flex flex-col gap-1">
                {history.map((s) => (
                  <div
                    key={s.id}
                    className="flex justify-between text-xs text-muted"
                  >
                    <span className={STATUS_STYLE[s.status]}>
                      {STATUS_LABEL[s.status]}
                    </span>
                    <span>{new Date(s.created_at).toLocaleString("ko-KR")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          <HintPanel problemId={problemId} />
        </div>

        <Link
          href={`/community/${problemId}`}
          className="text-center text-sm text-muted hover:text-white"
        >
          다른 사람들의 공유 풀이 보기 →
        </Link>
      </section>
    </div>
  );
}
