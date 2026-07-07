// FastAPI 백엔드 호출용 얇은 클라이언트.
// 모든 요청에 JWT Bearer 토큰을 자동으로 첨부하고, 401은 로그인 페이지로 유도한다.

import { clearToken, getToken } from "./auth";
import type {
  ApiErrorBody,
  Comment,
  CommentRequest,
  Hint,
  HintProgress,
  HintUnlockRequest,
  LoginRequest,
  ProblemDetail,
  ProblemGenerateRequest,
  ProblemListQuery,
  ProblemReportRequest,
  ProblemReportResponse,
  ProblemSummary,
  RegisterRequest,
  RevealSolutionRequest,
  RevealSolutionResponse,
  ShareSolutionRequest,
  SharedSolution,
  SubmissionRequest,
  SubmissionResponse,
  TokenResponse,
  UserResponse,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:10000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    // Network error (connection refused, DNS failure, etc.)
    throw new ApiError(
      0,
      "백엔드 API에 연결할 수 없습니다. NEXT_PUBLIC_API_BASE_URL과 API 서버 상태를 확인하세요."
    );
  }

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "인증이 만료되었습니다. 다시 로그인해주세요.");
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    const errBody = body as ApiErrorBody | null;
    let message = `요청이 실패했습니다 (${res.status})`;
    if (errBody?.detail) {
      message =
        typeof errBody.detail === "string"
          ? errBody.detail
          : errBody.detail.map((d) => d.msg).join(", ");
    }
    throw new ApiError(res.status, message);
  }

  return body as T;
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (body: RegisterRequest) =>
    request<TokenResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  login: (body: LoginRequest) =>
    request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  me: () => request<UserResponse>("/api/auth/me"),
  deleteMe: () => request<void>("/api/auth/me", { method: "DELETE" }),
};

// ── Problems ─────────────────────────────────────────────────────────────────
export const problemsApi = {
  generate: (body: ProblemGenerateRequest) =>
    request<ProblemDetail>("/api/problems/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  list: (query: ProblemListQuery = {}) => {
    const params = new URLSearchParams();
    if (query.algorithm) params.set("algorithm", query.algorithm);
    if (query.difficulty) params.set("difficulty", query.difficulty);
    if (query.q) params.set("q", query.q);
    if (query.sort) params.set("sort", query.sort);
    params.set("skip", String(query.skip ?? 0));
    params.set("limit", String(query.limit ?? 100));
    const qs = params.toString();
    return request<ProblemSummary[]>(`/api/problems${qs ? `?${qs}` : ""}`);
  },
  get: (problemId: string) =>
    request<ProblemDetail>(`/api/problems/${problemId}`),
  revealSolution: (problemId: string, body: RevealSolutionRequest) =>
    request<RevealSolutionResponse>(
      `/api/problems/${problemId}/reveal-solution`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  report: (problemId: string, body: ProblemReportRequest) =>
    request<ProblemReportResponse>(`/api/problems/${problemId}/report`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ── Submissions ──────────────────────────────────────────────────────────────
export const submissionsApi = {
  submit: (problemId: string, body: SubmissionRequest) =>
    request<SubmissionResponse>(`/api/submissions/${problemId}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  get: (submissionId: number) =>
    request<SubmissionResponse>(`/api/submissions/${submissionId}`),
  listForProblem: (problemId: string) =>
    request<SubmissionResponse[]>(`/api/submissions/problem/${problemId}`),
};

// ── Hints ────────────────────────────────────────────────────────────────────
export const hintsApi = {
  progress: (problemId: string) =>
    request<HintProgress>(`/api/hints/${problemId}/progress`),
  list: (problemId: string) => request<Hint[]>(`/api/hints/${problemId}`),
  unlock: (problemId: string, body: HintUnlockRequest) =>
    request<HintProgress>(`/api/hints/${problemId}/unlock`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ── Community ────────────────────────────────────────────────────────────────
export const communityApi = {
  share: (body: ShareSolutionRequest) =>
    request<SharedSolution>("/api/community/share", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listForProblem: (
    problemId: string,
    orderBy: "recent" | "popular" = "recent"
  ) =>
    request<SharedSolution[]>(
      `/api/community/${problemId}?order_by=${orderBy}`
    ),
  toggleLike: (sharedSolutionId: number) =>
    request<void>(`/api/community/${sharedSolutionId}/like`, {
      method: "POST",
    }),
  listComments: (sharedSolutionId: number) =>
    request<Comment[]>(`/api/community/${sharedSolutionId}/comments`),
  addComment: (sharedSolutionId: number, body: CommentRequest) =>
    request<Comment>(`/api/community/${sharedSolutionId}/comments`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
