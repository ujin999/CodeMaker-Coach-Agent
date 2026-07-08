// 백엔드 Pydantic 스키마(apps/api/app/schemas, packages/agent/schemas.py)와
// 1:1로 대응하는 타입 정의. 백엔드 스키마가 바뀌면 이 파일도 함께 갱신한다.

// ── Auth ─────────────────────────────────────────────────────────────────────
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
  display_name: string | null;
  created_at: string;
}

export interface RegisterRequest {
  email: string;
  password: string; // 최소 8자
  display_name?: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// ── Problem ────────────────────────────────────────────────────────────────
// POST /api/problems/generate 요청 바디 (app.schemas.problems.ProblemGenerateRequest)
export interface ProblemGenerateRequest {
  algorithm: string;
  difficulty: string; // easy | medium | hard
  problem_style?: string | null;
  language?: string | null;
  learning_goal?: string | null;
  user_level?: string | null;
  recent_weaknesses?: string[];
  min_cases?: number;
  allowed_hint_level?: number;
  include_hints?: boolean;
  seed?: string | null;
  avoid_problem_ids?: string[];
  force_new?: boolean;
  focus_weaknesses?: boolean;
}

export interface UserWeaknessesResponse {
  weak_concepts: { concept: string; score: number }[];
  top_errors: { error_type: string; count: number }[];
  recommendation: string;
}

export interface ProblemSummary {
  id: string;
  title: string;
  difficulty: string;
  algorithm: string[];
  learning_goal: string;
  expected_time_complexity: string;
  created_at: string;
  created_by_name?: string;
}

export interface ProblemDetail {
  id: string;
  title: string;
  difficulty: string;
  algorithm: string[];
  learning_goal: string;
  statement: string;
  input_format: string;
  output_format: string;
  constraints: string[];
  sample_input: string | null;
  sample_output: string | null;
  expected_time_complexity: string;
  created_at: string;
  created_by_name?: string;
  seed?: string | null;
  generation_mode?: string | null;
  variant_id?: string | null;
}

// GET /api/problems 목록 조회 쿼리.
// 참고: 현재 백엔드는 "내가 만든 문제"만 반환하며 algorithm/difficulty/q 필터는
// 아직 서버에 구현되어 있지 않다 (apps/web/README.md 확장 계약 섹션 참조).
// 프론트는 이 파라미터들을 함께 보내되, 서버가 무시하는 경우 클라이언트 사이드로 필터링한다.
export interface ProblemListQuery {
  algorithm?: string;
  difficulty?: string;
  q?: string;
  sort?: "recent" | "difficulty";
  skip?: number;
  limit?: number;
  mine?: boolean;
}

export interface RevealSolutionRequest {
  confirm: boolean;
}

export interface RevealSolutionResponse {
  problem_id: string;
  language: string;
  code: string;
}

export interface ProblemReportRequest {
  reason: string;
}

export interface ProblemReportResponse {
  id: number;
  problem_id: string;
  reason: string;
  created_at: string;
}

// ── Submission ────────────────────────────────────────────────────────────
export type SubmissionStatus =
  | "PENDING"
  | "JUDGING"
  | "AC"
  | "WA"
  | "TLE"
  | "RE"
  | "MLE"
  | "JUDGE_ERROR";

export interface SubmissionRequest {
  code: string;
  language: string;
}

export interface SubmissionResponse {
  id: number;
  problem_id: string;
  code?: string;
  language: string;
  status: SubmissionStatus;
  runtime_ms: number | null;
  memory_kb: number | null;
  failed_testcase_name?: string | null;
  failed_input?: string | null;
  expected_output?: string | null;
  actual_output?: string | null;
  stderr?: string | null;
  created_at: string;
}

export interface SubmissionReviewRequest {
  problem_id: string;
  problem_title?: string;
  problem_difficulty?: string;
  problem_algorithm?: string[];
  problem_statement?: string;
  user_code: string;
  language?: string;
  result_type: string;
  failed_testcase_name?: string | null;
  failed_input?: string | null;
  expected_output?: string | null;
  actual_output?: string | null;
  stderr?: string | null;
  include_concept_context?: boolean;
}

export interface SubmissionReviewReport {
  problem_id: string;
  result_type: string;
  summary: string;
  safe_to_show: boolean;
  error_diagnosis?: {
    primary_cause?: string;
    evidence?: string[];
    suggested_focus?: string[];
  } | null;
  complexity_analysis?: {
    risk_level?: string;
    suspected_complexity?: string | null;
    observed_pattern?: string;
    suggested_actions?: string[];
  } | null;
  failed_case_explanation?: {
    summary?: string;
    input_observation?: string | null;
    expected_vs_actual?: string | null;
    likely_gap?: string | null;
  } | null;
  feedback_report?: {
    summary?: string;
    likely_causes?: string[];
    next_steps?: string[];
  } | null;
}

// ── Hint ──────────────────────────────────────────────────────────────────
export interface HintProgress {
  problem_id: string;
  allowed_level: number; // 1~3
}

export interface Hint {
  level: number;
  title: string;
  content: string;
  code_skeleton: string | null;
  concept_refs: string[];
}

export interface HintUnlockRequest {
  confirm: boolean;
}

// ── Community ───────────────────────────────────────────────────────────────
export interface ShareSolutionRequest {
  submission_id: number;
  title: string;
  description?: string | null;
  is_public?: boolean;
}

export interface SharedSolution {
  id: number;
  problem_id: string;
  user_id: number;
  title: string;
  description: string | null;
  is_public: boolean;
  likes_count: number;
  code?: string;
  language?: string;
  created_at: string;
}

export interface CommentRequest {
  content: string;
}

export interface Comment {
  id: number;
  user_id: number;
  content: string;
  created_at: string;
}

export interface ApiErrorBody {
  detail?: string | { msg: string }[];
}
