/**
 * Typed API client for SplitSmart AI backend.
 * All requests go to /api (proxied to FastAPI via next.config.ts rewrites).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1`
  : "/api/v1";

// ── Fetch wrapper ─────────────────────────────────────────────────────────

interface RequestOptions {
  method?: string;
  body?: unknown;
  token?: string;
  signal?: AbortSignal;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token, signal } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(response.status, error.detail ?? "Request failed", error);
  }

  return response.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Health ────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: "ok" | "degraded";
  app: string;
  version: string;
  environment: string;
  timestamp: number;
  db: string;
  redis: string;
  ocr_mode: "mock" | "gemini";
}

export const api = {
  health: {
    get: () => request<HealthResponse>("/health"),
  },

  // ── Auth ────────────────────────────────────────────────────────────────
  auth: {
    register: (data: { email: string; display_name: string; password: string }) =>
      request("/auth/register", { method: "POST", body: data }),
    login: (data: { email: string; password: string }) =>
      request("/auth/login", { method: "POST", body: data }),
    guest: (data: { display_name: string }) =>
      request("/auth/guest", { method: "POST", body: data }),
  },

  // ── Groups ──────────────────────────────────────────────────────────────
  groups: {
    list: (token: string) => request("/groups", { token }),
    create: (data: { name: string; currency?: string }, token: string) =>
      request("/groups", { method: "POST", body: data, token }),
    get: (id: string, token: string) => request(`/groups/${id}`, { token }),
    balances: (id: string, token: string) => request(`/groups/${id}/balances`, { token }),
    simplified: (id: string, token: string) => request(`/groups/${id}/simplified`, { token }),
  },

  // ── Receipts ─────────────────────────────────────────────────────────────
  receipts: {
    upload: async (formData: FormData, token: string) => {
      const response = await fetch(`${API_BASE}/receipts/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) throw new ApiError(response.status, "Upload failed");
      return response.json();
    },
    get: (id: string, token: string) => request(`/receipts/${id}`, { token }),
  },

  // ── Rooms ─────────────────────────────────────────────────────────────────
  rooms: {
    guestJoin: (roomCode: string, displayName: string) =>
      request(`/rooms/${roomCode}/guest-join`, {
        method: "POST",
        body: { display_name: displayName },
      }),
  },

  // ── Sandbox ──────────────────────────────────────────────────────────────
  sandbox: {
    init: () => request("/sandbox/init", { method: "POST" }),
  },

  // ── Metrics ──────────────────────────────────────────────────────────────
  metrics: {
    get: () => request("/metrics"),
  },
};

export default api;
