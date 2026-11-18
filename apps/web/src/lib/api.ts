import type {
  FinalizeResponse,
  Group,
  GroupBalancesResponse,
  GroupDetail,
  GroupMember,
  GuestJoinResponse,
  HealthResponse,
  ManualExpense,
  Receipt,
  ReceiptUploadResponse,
  SimplifiedDebtResult,
  SystemMetrics,
  UPIPayment,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "")}/api/v1`
  : "/api/v1";

interface RequestOptions {
  method?: string;
  body?: unknown;
  token?: string;
  signal?: AbortSignal;
}

async function request<T>(
  path: string,
  { method = "GET", body, token, signal }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const error = (await response.json()) as { detail?: unknown };
      if (typeof error.detail === "string") detail = error.detail;
    } catch {
      // Keep the HTTP status message when the server does not return JSON.
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function roomWebSocketUrl(roomCode: string, token: string): string {
  const path = `/api/v1/rooms/${encodeURIComponent(roomCode)}/ws`;
  const base = process.env.NEXT_PUBLIC_API_URL;
  const isLocalHost = ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const url = base
    ? new URL(path, base)
    : new URL(
        path,
        isLocalHost
          ? `${window.location.protocol}//${window.location.hostname}:8000`
          : window.location.origin,
      );
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("token", token);
  return url.toString();
}

export const api = {
  health: {
    get: (signal?: AbortSignal) => request<HealthResponse>("/health", { signal }),
  },
  groups: {
    list: (signal?: AbortSignal) => request<Group[]>("/groups", { signal }),
    create: (data: { name: string; currency?: string }) =>
      request<Group>("/groups", { method: "POST", body: data }),
    get: (id: string, signal?: AbortSignal) =>
      request<GroupDetail>(`/groups/${encodeURIComponent(id)}`, { signal }),
    addMember: (
      id: string,
      data: { display_name: string; upi_id?: string },
    ) =>
      request<GroupMember>(`/groups/${encodeURIComponent(id)}/members`, {
        method: "POST",
        body: data,
      }),
    expenses: (id: string, signal?: AbortSignal) =>
      request<ManualExpense[]>(
        `/groups/${encodeURIComponent(id)}/expenses`,
        { signal },
      ),
    addExpense: (
      id: string,
      data: {
        description: string;
        amount_paise: number;
        paid_by_user_id: string;
        participant_user_ids: string[];
      },
    ) =>
      request<ManualExpense>(`/groups/${encodeURIComponent(id)}/expenses`, {
        method: "POST",
        body: data,
      }),
    balances: (id: string, signal?: AbortSignal) =>
      request<GroupBalancesResponse>(
        `/groups/${encodeURIComponent(id)}/balances`,
        { signal },
      ),
    simplified: (id: string, signal?: AbortSignal) =>
      request<SimplifiedDebtResult>(
        `/groups/${encodeURIComponent(id)}/simplified`,
        { signal },
      ),
  },
  receipts: {
    upload: async (formData: FormData, signal?: AbortSignal) => {
      const response = await fetch(`${API_BASE}/receipts/upload`, {
        method: "POST",
        body: formData,
        signal,
        cache: "no-store",
      });
      if (!response.ok) {
        let detail = `Upload failed (${response.status})`;
        try {
          const error = (await response.json()) as { detail?: unknown };
          if (typeof error.detail === "string") detail = error.detail;
        } catch {
          // Retain the HTTP status when the server response is not JSON.
        }
        throw new ApiError(response.status, detail);
      }
      return response.json() as Promise<ReceiptUploadResponse>;
    },
    get: (id: string, signal?: AbortSignal) =>
      request<Receipt>(`/receipts/${encodeURIComponent(id)}`, { signal }),
    forGroup: (groupId: string, signal?: AbortSignal) =>
      request<Receipt[]>(
        `/groups/${encodeURIComponent(groupId)}/receipts`,
        { signal },
      ),
    byRoomCode: (roomCode: string, signal?: AbortSignal) =>
      request<Receipt>(
        `/receipts/room/${encodeURIComponent(roomCode)}`,
        { signal },
      ),
  },
  rooms: {
    guestJoin: (roomCode: string, displayName: string) =>
      request<GuestJoinResponse>(
        `/rooms/${encodeURIComponent(roomCode)}/guest-join`,
        { method: "POST", body: { display_name: displayName } },
      ),
    webSocketUrl: roomWebSocketUrl,
    finalize: (
      roomCode: string,
      payload: { payer_user_id: string; idempotency_key: string },
      token: string,
    ) =>
      request<FinalizeResponse>(
        `/rooms/${encodeURIComponent(roomCode)}/finalize`,
        { method: "POST", body: payload, token },
      ),
  },
  metrics: {
    get: (signal?: AbortSignal) => request<SystemMetrics>("/metrics", { signal }),
  },
  ledger: {
    upiPayment: (
      payload: {
        group_id: string;
        creditor_user_id: string;
        amount_paise: number;
      },
      signal?: AbortSignal,
    ) =>
      request<UPIPayment>("/ledger/upi-intent", {
        method: "POST",
        body: payload,
        signal,
      }),
    settle: (
      payload: {
        group_id: string;
        from_user_id: string;
        to_user_id: string;
        amount_paise: number;
        idempotency_key: string;
      },
    ) => request("/ledger/settle", { method: "POST", body: payload }),
  },
  copilot: {
    chat: (message: string, groupId: string) =>
      request<{ reply: string }>("/copilot/chat", {
        method: "POST",
        body: { message, group_id: groupId },
      }),
  },
};

export default api;
