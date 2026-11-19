export type ReceiptStatus =
  | "QUEUED"
  | "PROCESSING"
  | "READY_FOR_CLAIMS"
  | "LOCKED"
  | "SETTLED"
  | "FAILED";

export type EntryType = "EXPENSE_SHARE" | "SETTLEMENT";

export interface UserPublic {
  id: string;
  display_name: string;
  avatar_color: string;
  is_guest: boolean;
}

export interface Group {
  id: string;
  name: string;
  currency: string;
  invite_code: string;
  created_by: string | null;
  created_at: string;
  member_count: number;
}

export interface GroupMember {
  id: string;
  user: UserPublic;
  joined_at: string;
}

export interface ManualExpenseParticipant {
  user_id: string;
  share_paise: number;
}

export interface ManualExpense {
  id: string;
  group_id: string;
  description: string;
  amount_paise: number;
  paid_by_user_id: string;
  participants: ManualExpenseParticipant[];
  created_at: string;
}

export interface GroupDetail extends Group {
  members: GroupMember[];
}

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
  paid_by: string | null;
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

export interface ReceiptProgressEvent {
  event: string;
  receipt_id?: string;
  stage?: string;
  message?: string;
  progress?: number;
  [key: string]: unknown;
}

export interface GroupBalance {
  user_id: string;
  display_name: string;
  avatar_color: string;
  net_balance_paise: number;
  status: "creditor" | "debtor" | "settled";
}

export interface GroupBalancesResponse {
  group_id: string;
  group_name: string;
  currency: string;
  balances: GroupBalance[];
  total_entries: number;
}

export interface Settlement {
  from_user_id: string;
  from_display_name: string;
  from_avatar_color: string;
  to_user_id: string;
  to_display_name: string;
  to_avatar_color: string;
  to_upi_id: string | null;
  amount_paise: number;
  amount_display: string;
}

export interface SimplifiedDebtResult {
  group_id: string;
  group_name: string;
  currency: string;
  original_transactions: number;
  simplified_transactions: number;
  transactions_saved: number;
  zero_sum_verified?: boolean;
  settlements: Settlement[];
}

export interface GuestJoinResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: UserPublic;
}

export type RoomEvent =
  | {
      event: "PARTICIPANT_JOINED";
      user_id: string;
      display_name: string;
      avatar_color: string;
      simulated?: boolean;
    }
  | {
      event: "ITEM_CLAIM_TOGGLED";
      item_id: string;
      user_id: string;
      action: "claimed" | "unclaimed";
      fraction: { numerator: number; denominator: number };
    }
  | {
      event: "TAX_RECALCULATED";
      per_user_totals: Record<string, number>;
      invariant_holds: boolean;
    }
  | {
      event: "RECEIPT_LOCKED";
      receipt_id: string;
      final_splits: Record<string, number>;
    }
  | { event: "ERROR"; detail: string; status_code?: number };

export interface FinalizeResponse {
  receipt_id: string;
  status: ReceiptStatus;
  created: boolean;
  payer_user_id: string;
  final_splits: Record<string, number>;
  settlements: Array<{
    from_user_id: string;
    to_user_id: string;
    amount_paise: number;
  }>;
}

export interface SystemMetrics {
  status: "ok";
  total_users: number;
  total_groups: number;
  total_receipts: number;
  active_rooms: number;
  ledger_entries: number;
  total_paise_tracked: number;
}

export interface UPIPayment {
  uri: string;
  qr_base64: string;
  amount_rupees: string;
  payee_name: string;
  payee_upi_id: string;
  note: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  app: string;
  version: string;
  environment: string;
  timestamp: number;
  db: string;
  redis: string;
  ocr_mode: "mock" | "groq";
}
