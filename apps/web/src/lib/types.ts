/**
 * TypeScript types matching the FastAPI/Pydantic schemas.
 * Keep in sync with apps/api/app/schemas/
 */

// ── Enums ─────────────────────────────────────────────────────────────────

export type ReceiptStatus =
  | "QUEUED"
  | "PROCESSING"
  | "READY_FOR_CLAIMS"
  | "LOCKED"
  | "SETTLED"
  | "FAILED";

export type EntryType = "EXPENSE_SHARE" | "SETTLEMENT";

// ── Users ─────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string | null;
  display_name: string;
  upi_id: string | null;
  avatar_color: string;
  is_guest: boolean;
  created_at: string;
}

export interface UserPublic {
  id: string;
  display_name: string;
  avatar_color: string;
  is_guest: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

// ── Groups ────────────────────────────────────────────────────────────────

export interface Group {
  id: string;
  name: string;
  currency: string;
  invite_code: string;
  is_sandbox: boolean;
  created_by: string | null;
  created_at: string;
  member_count: number;
}

export interface GroupMember {
  id: string;
  user: UserPublic;
  joined_at: string;
}

export interface GroupDetail extends Group {
  members: GroupMember[];
}

// ── Receipts ──────────────────────────────────────────────────────────────

export interface ItemClaim {
  id: string;
  user: UserPublic;
  share_fraction_numerator: number;
  share_fraction_denominator: number;
  calculated_item_paise: number;
  calculated_tax_and_fees_paise: number;
  calculated_final_paise: number;
}

export interface LineItem {
  id: string;
  item_name: string;
  quantity: number;
  unit_price_paise: number;
  total_price_paise: number;
  category: string | null;
  claims: ItemClaim[];
}

export interface Receipt {
  id: string;
  group_id: string;
  room_code: string;
  merchant_name: string | null;
  receipt_date: string | null;
  image_url: string | null;
  status: ReceiptStatus;
  subtotal_paise: number;
  tax_paise: number;
  service_charge_paise: number;
  delivery_fee_paise: number;
  discount_paise: number;
  total_paise: number;
  created_at: string;
  line_items: LineItem[];
}

export interface ReceiptUploadResponse {
  receipt_id: string;
  room_code: string;
  job_id: string;
  status: ReceiptStatus;
  sse_url: string;
}

// ── Debt Simplifier ───────────────────────────────────────────────────────

export interface DebtEdge {
  from_user: UserPublic;
  to_user: UserPublic;
  amount_paise: number;
}

export interface SimplifiedDebtResult {
  raw_edges: DebtEdge[];
  simplified_edges: DebtEdge[];
  transactions_saved: number;
  net_balances: Record<string, number>; // user_id -> paise (+credit, -debt)
}

// ── UPI ───────────────────────────────────────────────────────────────────

export interface UPIPayment {
  uri: string;
  qr_base64: string;
  amount_rupees: string;
  note: string;
}

// ── WebSocket Events ──────────────────────────────────────────────────────

export type WSEventType =
  | "PARTICIPANT_JOINED"
  | "ITEM_CLAIM_TOGGLED"
  | "TAX_RECALCULATED"
  | "RECEIPT_LOCKED"
  | "SIMULATE_FRIENDS"
  | "ERROR";

export interface WSEvent {
  type: WSEventType;
  payload: unknown;
  timestamp: string;
}

export interface ParticipantJoinedPayload {
  user_id: string;
  display_name: string;
  avatar_color: string;
}

export interface ItemClaimToggledPayload {
  item_id: string;
  user_id: string;
  action: "claim" | "unclaim";
  fraction: { numerator: number; denominator: number };
}

export interface TaxRecalculatedPayload {
  per_user_totals: Record<string, number>; // user_id -> paise
}

// ── Metrics ───────────────────────────────────────────────────────────────

export interface SystemMetrics {
  redis_cache_hit_ratio: number;
  avg_ocr_latency_ms: number;
  p95_ocr_latency_ms: number;
  total_paise_balanced: number;
  active_ws_rooms: number;
  total_users: number;
  total_groups: number;
  total_receipts: number;
  ai_token_cost_usd: number;
}
