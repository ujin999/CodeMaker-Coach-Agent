import Link from "next/link";
import { algorithmLabel } from "@/lib/constants";
import type { ProblemSummary } from "@/lib/types";
import DifficultyBadge from "./DifficultyBadge";

export default function ProblemCard({ problem }: { problem: ProblemSummary }) {
  return (
    <Link
      href={`/solve/${problem.id}`}
      className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-5 transition-colors hover:border-brand"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-base font-semibold text-white">{problem.title}</h3>
        <DifficultyBadge difficulty={problem.difficulty} />
      </div>
      <p className="line-clamp-2 text-sm text-muted">{problem.learning_goal}</p>
      <div className="flex flex-wrap gap-1.5">
        {problem.algorithm.map((a) => (
          <span
            key={a}
            className="rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted"
          >
            {algorithmLabel(a)}
          </span>
        ))}
      </div>
      <div className="mt-auto flex flex-col gap-1 text-xs text-muted">
        <div className="flex items-center justify-between">
          <span>생성자: <span className="text-white font-medium">{problem.created_by_name || "알 수 없음"}</span></span>
          <span>{new Date(problem.created_at).toLocaleDateString("ko-KR")}</span>
        </div>
        <div>시간복잡도 {problem.expected_time_complexity}</div>
      </div>
    </Link>
  );
}
