// 알고리즘 분류·난이도 체계 (docs/INTERFACE_DESIGN.md 2.1 + Judge0 언어 매핑 기준).
// 백엔드는 algorithm을 자유 문자열로 받으므로, 여기 value는 Agent/RAG 쪽 키와 맞춘다.

export interface AlgorithmCategory {
  value: string;
  label: string;
}

export const ALGORITHM_CATEGORIES: AlgorithmCategory[] = [
  { value: "binary_search", label: "이분 탐색" },
  { value: "bfs", label: "BFS" },
  { value: "dfs", label: "DFS" },
  { value: "greedy", label: "그리디" },
  { value: "hash", label: "해시" },
  { value: "two_pointer", label: "투 포인터" },
  { value: "dp_basic", label: "동적 계획법" },
  { value: "sorting", label: "정렬" },
  { value: "graph", label: "그래프" },
  { value: "string", label: "문자열" },
];

export interface DifficultyLevel {
  value: string;
  label: string;
  color: string;
}

export const DIFFICULTY_LEVELS: DifficultyLevel[] = [
  { value: "easy", label: "쉬움", color: "#22c55e" },
  { value: "medium", label: "보통", color: "#eab308" },
  { value: "hard", label: "어려움", color: "#ef4444" },
];

export const LANGUAGES = [
  { value: "python", label: "Python", monaco: "python" },
  { value: "java", label: "Java", monaco: "java" },
  { value: "cpp", label: "C++", monaco: "cpp" },
];

export function algorithmLabel(value: string): string {
  return ALGORITHM_CATEGORIES.find((a) => a.value === value)?.label ?? value;
}

export function difficultyLabel(value: string): string {
  return DIFFICULTY_LEVELS.find((d) => d.value === value)?.label ?? value;
}

export function difficultyColor(value: string): string {
  return DIFFICULTY_LEVELS.find((d) => d.value === value)?.color ?? "#94a3b8";
}
