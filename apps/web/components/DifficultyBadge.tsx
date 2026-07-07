import { difficultyColor, difficultyLabel } from "@/lib/constants";

export default function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const color = difficultyColor(difficulty);
  return (
    <span
      className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
      style={{ color, backgroundColor: `${color}22`, border: `1px solid ${color}55` }}
    >
      {difficultyLabel(difficulty)}
    </span>
  );
}
