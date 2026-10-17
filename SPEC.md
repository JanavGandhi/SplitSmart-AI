# SplitSmart AI — Complete Architecture Specification

> **Version:** 1.0 | **Last Updated:** 2026-10-17 | **Status:** In Progress (Stage 1)

---

## 1. Product Overview

SplitSmart AI is a production-grade, scalable, real-time multiplayer receipt-splitting, expense ledger, and AI financial copilot web application designed to outperform Splitwise through 4 core engineering differentiators.

### 1.1 Core Differentiators

| # | Feature | Technology |
|---|---------|------------|
| 1 | **Zero-Typing Vision AI Receipt Parser** | Gemini 2.5 Flash + Celery async workers + SSE streaming |
| 2 | **No-Login Multiplayer Claim Room** | WebSockets + Redis Pub/Sub + scoped guest JWT |
| 3 | **Exact Paise/Cent Ledger + Min-Cash-Flow Debt Graph** | Integer arithmetic + graph theory O(N log N) |
| 4 | **1-Click Recruiter Guest Sandbox + Public Telemetry** | Pre-seeded demo data + /metrics observability |

---

## 2. Tech Stack

### Backend
- **Runtime:** Python 3.12
- **Framework:** FastAPI (async)
- **ORM:** SQLAlchemy 2.0 (Async) + asyncpg driver
- **Migrations:** Alembic
- **Validation:** Pydantic v2
- **Task Queue:** Celery + Redis broker
- **AI:** Google Gemini API (gemini-2.5-flash)
- **Testing:** pytest + pytest-asyncio

### Frontend
- **Framework:** Next.js 15 (App Router, TypeScript)
- **Styling:** Tailwind CSS + Shadcn UI
- **Icons:** Lucide React
- **Real-time:** WebSocket hooks
- **Charts:** Recharts / D3 (debt graph SVG)

### Infrastructure
- **Database:** PostgreSQL 16 + pgvector extension
- **Cache / Broker:** Redis 7
- **Containerization:** Docker + Docker Compose
- **CI/CD:** GitHub Actions

---

## 3. Repository Structure

```
splitsmart-ai/
├── SPEC.md
├── TASKS.md
├── docker-compose.yml
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── apps/
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── alembic/
│   │   │   ├── alembic.ini
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   └── app/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── database.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── user.py
│   │       │   ├── group.py
│   │       │   ├── group_member.py
│   │       │   ├── receipt.py
│   │       │   ├── receipt_line_item.py
│   │       │   ├── item_claim.py
│   │       │   └── ledger_entry.py
│   │       ├── schemas/
│   │       │   ├── __init__.py
│   │       │   ├── common.py
│   │       │   ├── user.py
│   │       │   ├── group.py
│   │       │   └── receipt.py
│   │       ├── api/
│   │       │   └── v1/
│   │       │       ├── __init__.py
│   │       │       ├── health.py
│   │       │       ├── auth.py
│   │       │       ├── groups.py
│   │       │       ├── receipts.py
│   │       │       ├── rooms_ws.py
│   │       │       ├── copilot.py
│   │       │       └── metrics.py
│   │       ├── services/
│   │       │   ├── math_engine.py
│   │       │   ├── debt_simplifier.py
│   │       │   ├── vision_ocr.py
│   │       │   ├── ai_copilot.py
│   │       │   ├── semantic_cache.py
│   │       │   └── upi_generator.py
│   │       └── worker/
│   │           └── celery_app.py
│   └── web/
│       ├── Dockerfile
│       ├── package.json
│       ├── next.config.ts
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       └── src/
│           ├── app/
│           │   ├── layout.tsx
│           │   ├── page.tsx
│           │   ├── dashboard/page.tsx
│           │   ├── groups/[id]/page.tsx
│           │   ├── room/[code]/page.tsx
│           │   └── metrics/page.tsx
│           ├── components/
│           ├── hooks/
│           │   ├── useRoomWebSocket.ts
│           │   ├── useReceiptSSE.ts
│           │   └── useSandbox.ts
│           └── lib/
│               ├── api.ts
│               ├── types.ts
│               └── currency.ts
```

---

## 4. Database Schema

> **Critical Rule:** All monetary values stored as `BIGINT` in minor units (paise/cents).
> Example: Rs 450.50 = `45050`

### 4.1 users
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| email | VARCHAR(255) | UNIQUE, NULLABLE |
| display_name | VARCHAR(100) | NOT NULL |
| upi_id | VARCHAR(100) | NULLABLE |
| avatar_color | VARCHAR(7) | NOT NULL (hex color) |
| is_guest | BOOLEAN | DEFAULT TRUE |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |

### 4.2 groups
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | VARCHAR(200) | NOT NULL |
| currency | VARCHAR(3) | DEFAULT 'INR' |
| invite_code | VARCHAR(12) | UNIQUE, NOT NULL |
| is_sandbox | BOOLEAN | DEFAULT FALSE |
| created_by | UUID | FK to users.id |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |

### 4.3 group_members
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| group_id | UUID | FK to groups.id |
| user_id | UUID | FK to users.id |
| joined_at | TIMESTAMPTZ | DEFAULT NOW() |
| | | UNIQUE(group_id, user_id) |

### 4.4 receipts
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| group_id | UUID | FK to groups.id |
| uploaded_by | UUID | FK to users.id |
| paid_by | UUID | FK to users.id |
| room_code | VARCHAR(12) | UNIQUE, INDEX |
| merchant_name | VARCHAR(200) | NULLABLE |
| receipt_date | DATE | NULLABLE |
| image_url | TEXT | NULLABLE |
| status | ENUM | 'QUEUED','PROCESSING','READY_FOR_CLAIMS','LOCKED','SETTLED','FAILED' |
| subtotal_paise | BIGINT | DEFAULT 0 |
| tax_paise | BIGINT | DEFAULT 0 |
| service_charge_paise | BIGINT | DEFAULT 0 |
| delivery_fee_paise | BIGINT | DEFAULT 0 |
| discount_paise | BIGINT | DEFAULT 0 |
| total_paise | BIGINT | DEFAULT 0 |
| raw_ocr_json | JSONB | NULLABLE |
| embedding | VECTOR(768) | NULLABLE |
| idempotency_key | VARCHAR(64) | UNIQUE |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |

### 4.5 receipt_line_items
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| receipt_id | UUID | FK to receipts.id ON DELETE CASCADE |
| item_name | VARCHAR(200) | NOT NULL |
| quantity | INTEGER | DEFAULT 1 |
| unit_price_paise | BIGINT | NOT NULL |
| total_price_paise | BIGINT | NOT NULL |
| category | VARCHAR(50) | NULLABLE |

### 4.6 item_claims
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| line_item_id | UUID | FK to receipt_line_items.id ON DELETE CASCADE |
| user_id | UUID | FK to users.id |
| share_fraction_numerator | INTEGER | DEFAULT 1 |
| share_fraction_denominator | INTEGER | DEFAULT 1 |
| calculated_item_paise | BIGINT | DEFAULT 0 |
| calculated_tax_and_fees_paise | BIGINT | DEFAULT 0 |
| calculated_final_paise | BIGINT | DEFAULT 0 |
| | | UNIQUE(line_item_id, user_id) |

### 4.7 ledger_entries
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| group_id | UUID | FK to groups.id |
| receipt_id | UUID | FK to receipts.id NULLABLE |
| from_user_id | UUID | FK to users.id (debtor) |
| to_user_id | UUID | FK to users.id (creditor) |
| amount_paise | BIGINT | CHECK (amount_paise > 0) |
| entry_type | ENUM | 'EXPENSE_SHARE','SETTLEMENT' |
| idempotency_key | VARCHAR(64) | UNIQUE |
| created_at | TIMESTAMPTZ | DEFAULT NOW() |

---

## 5. Core Algorithms

### 5.1 Proportional Tax/Fee/Discount Distribution (math_engine.py)

**Inputs:**
- `subtotal_paise` S — sum of all line item prices
- `tax_paise` + `service_charge_paise` + `delivery_fee_paise` = extra charges E
- `discount_paise` D
- `total_paise` T = S + E - D
- Per-user raw subtotals {S_u}

**Steps:**
1. Each of k claimants of item P gets: `floor(P / k)` paise
2. Remainder `P mod k` distributed 1 paise to first `(P mod k)` claimants sorted by `user_id`
3. `S_u = sum(P_{u,item})` for all items claimed by user u
4. `A_u = floor(A * (S_u / S))` where A = E - D
5. Compute `R = T - sum(S_u + A_u)`; distribute R paise 1-by-1 sorted by largest fractional remainder
6. **INVARIANT:** `sum(S_u + A_u) == T` always

**Unit tests:** 100 random receipt permutations must all pass.

### 5.2 Min-Cash-Flow Debt Simplification (debt_simplifier.py)

**Algorithm O(N log N) with max/min heaps:**
1. Compute net balance B(u) for each user
2. Verify sum(B(u)) == 0
3. Creditors max-heap, Debtors min-heap
4. Pop largest creditor + largest debtor, settle M = min(B_c, |B_d|)
5. Record edge u_d -> u_c : M paise; push remainders back

### 5.3 UPI Intent URI Generation (upi_generator.py)

Format: `upi://pay?pa={upi_id}&pn={name}&am={rupees.2f}&cu=INR&tn={note}`
Returns: `uri: str` + `qr_base64: str` (base64 SVG QR)

---

## 6. WebSocket Events

| Event | Direction | Payload |
|-------|-----------|---------|
| `PARTICIPANT_JOINED` | Server to All | `{user_id, display_name, avatar_color}` |
| `ITEM_CLAIM_TOGGLED` | Server to All | `{item_id, user_id, action, fraction}` |
| `TAX_RECALCULATED` | Server to All | `{per_user_totals: {user_id: paise}}` |
| `RECEIPT_LOCKED` | Server to All | `{receipt_id, final_splits}` |
| `SIMULATE_FRIENDS` | Client to Server | `{}` |

---

## 7. Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://splitsmart:splitsmart@localhost:5432/splitsmart
SYNC_DATABASE_URL=postgresql://splitsmart:splitsmart@localhost:5432/splitsmart

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET_KEY=change-me-in-production-32-chars-min
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# AI
GEMINI_API_KEY=your-google-ai-studio-key-here

# App
APP_ENV=development
CORS_ORIGINS=http://localhost:3000
```

---

## 8. Stage Completion Status

| Stage | Status | Notes |
|-------|--------|-------|
| Stage 1: Scaffold + DB + Docker | In Progress | Current stage |
| Stage 2: Math Engine + Sandbox | Pending | - |
| Stage 3: Vision AI + SSE | Pending | - |
| Stage 4: WebSocket Claim Room | Pending | - |
| Stage 5: Next.js Frontend | Pending | - |
| Stage 6: CI/CD + Production | Pending | - |
