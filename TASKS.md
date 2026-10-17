# SplitSmart AI — Task Tracker

> **Project:** SplitSmart AI | **Started:** 2026-10-17
> **Rule:** Never advance to the next stage without explicit user approval.

---

## STAGE 1: Workspace Spec, Monorepo Scaffolding, Docker & Database Layer
**Status:** 🟡 In Progress

### 1.1 Root Tracking Files
- [x] Create `SPEC.md` with full architecture, schema, algorithms, API contracts
- [x] Create `TASKS.md` (this file)

### 1.2 Infrastructure / Docker
- [x] Create `docker-compose.yml` — PostgreSQL 16 (pgvector) + Redis 7
- [x] Create `.env.example` with all required environment variables

### 1.3 FastAPI Backend Scaffold (`apps/api`)
- [x] Create `apps/api/pyproject.toml` (dependencies: FastAPI, SQLAlchemy 2 async, asyncpg, Alembic, Pydantic v2, Celery, redis, python-jose, passlib, httpx)
- [x] Create `apps/api/Dockerfile`
- [x] Create `apps/api/app/config.py` — Pydantic BaseSettings
- [x] Create `apps/api/app/database.py` — AsyncEngine + AsyncSession
- [x] Create `apps/api/app/main.py` — FastAPI app, CORS, lifespan, exception handlers

### 1.4 Database Models (`apps/api/app/models/`)
- [x] `__init__.py` — Base + all model imports
- [x] `user.py` — User model
- [x] `group.py` — Group model with ENUM for currency
- [x] `group_member.py` — GroupMember with unique constraint
- [x] `receipt.py` — Receipt with ReceiptStatus ENUM + all paise columns + VECTOR(768)
- [x] `receipt_line_item.py` — LineItem model
- [x] `item_claim.py` — ItemClaim with unique constraint
- [x] `ledger_entry.py` — LedgerEntry with ACID-style tracking

### 1.5 Pydantic Schemas (`apps/api/app/schemas/`)
- [x] `common.py` — Shared base schemas, pagination
- [x] `user.py` — UserCreate, UserResponse, GuestUserCreate
- [x] `group.py` — GroupCreate, GroupResponse, MemberResponse
- [x] `receipt.py` — ReceiptResponse, LineItemResponse, ClaimResponse

### 1.6 API Routes (`apps/api/app/api/v1/`)
- [x] `health.py` — GET /api/v1/health (DB ping + Redis ping)
- [x] Stub routers for: auth, groups, receipts, rooms_ws, copilot, metrics (return 501 for now)

### 1.7 Alembic Migrations
- [x] Initialize Alembic in `apps/api/alembic/`
- [x] Configure `alembic.ini` + `env.py` with async engine
- [x] Generate initial migration (all 7 tables + pgvector extension)

### 1.8 Next.js Frontend Scaffold (`apps/web`)
- [x] Initialize Next.js 15 with TypeScript + Tailwind CSS + App Router
- [x] Configure `next.config.ts`, `tailwind.config.ts`, `tsconfig.json`
- [x] Create `src/app/layout.tsx` — Root layout, Google Fonts (Inter), dark theme
- [x] Create `src/app/page.tsx` — Landing page shell (dark-mode fintech hero)
- [x] Create `src/lib/api.ts` — Typed API client pointing to localhost:8000
- [x] Create `src/lib/types.ts` — TypeScript types matching Pydantic schemas
- [x] Create `src/lib/currency.ts` — Paise formatting utilities

### 1.9 Verification Gate
- [x] `docker compose up -d` → both services healthy
- [x] `alembic upgrade head` → all 7 tables created
- [x] `GET /api/v1/health` → 200 `{"status":"ok","db":"connected","redis":"connected"}`
- [x] Browser agent screenshot of health endpoint + landing page
- [ ] **USER APPROVAL REQUIRED** before Stage 2

---

## STAGE 2: Core Math Engine, Debt Graph Algorithm & 1-Click Recruiter Sandbox
**Status:** ⬜ Pending (awaiting Stage 1 approval)

### 2.1 Core Services
- [ ] `services/math_engine.py` — Proportional tax/discount distribution with paise invariant
- [ ] `services/debt_simplifier.py` — Min-Cash-Flow O(N log N) algorithm
- [ ] `services/upi_generator.py` — UPI deep link + QR code

### 2.2 Sandbox Endpoint
- [ ] `POST /api/v1/sandbox/init` — Creates "Goa Weekend Squad" demo group
  - 5 members (Aryan, Priya, Karan, Meera, Dev)
  - 4 receipts: 12-item restaurant bill, Blinkit grocery haul, beach shack, taxi split
  - Cross-debts that simplify from 11 transactions → 4

### 2.3 Group & Ledger Endpoints
- [ ] `GET/POST /api/v1/groups` — Group CRUD
- [ ] `GET /api/v1/groups/{id}/balances` — Net balance computation
- [ ] `GET /api/v1/groups/{id}/simplified` — Min-cash-flow result
- [ ] `POST /api/v1/ledger/settle` — Idempotent settlement entry

### 2.4 Tests
- [ ] `tests/test_math_engine.py` — 100 random permutations paise invariant
- [ ] `tests/test_debt_simplifier.py` — Optimal reduction + zero-sum invariant

### 2.5 Verification Gate
- [ ] `pytest tests/test_math_engine.py tests/test_debt_simplifier.py -v` → all pass
- [ ] Sandbox endpoint returns 201 with valid group/receipts
- [ ] **USER APPROVAL REQUIRED** before Stage 3

---

## STAGE 3: Async Vision AI Receipt Pipeline & Real-Time SSE Progress
**Status:** ⬜ Pending

### 3.1 Celery Worker
- [ ] `worker/celery_app.py` — Celery app with Redis broker
- [ ] Receipt processing task: upload → OCR → validate → ready

### 3.2 Vision OCR Service
- [ ] `services/vision_ocr.py` — Gemini Vision structured extraction
- [ ] Mock OCR fallback when GEMINI_API_KEY not set
- [ ] Pydantic output schema for receipt extraction

### 3.3 Receipt Upload API
- [ ] `POST /api/v1/receipts/upload` → 202 Accepted + job_id
- [ ] `GET /api/v1/receipts/{id}/events` → SSE stream
- [ ] Pipeline stages: UPLOADING → OCR_EXTRACTING → VALIDATING_MATH → READY_FOR_CLAIMS

### 3.4 Tests
- [ ] Integration test: upload sample image → poll SSE → verify DB line items

### 3.5 Verification Gate
- [ ] Receipt pipeline integration test passes
- [ ] **USER APPROVAL REQUIRED** before Stage 4

---

## STAGE 4: Multiplayer No-Login WebSocket Claim Room
**Status:** ⬜ Pending

### 4.1 Guest Auth
- [ ] `POST /api/v1/rooms/{code}/guest-join` — Issue scoped guest JWT

### 4.2 WebSocket Endpoint
- [ ] `WS /api/v1/rooms/{code}/ws` — Redis Pub/Sub backed
- [ ] Events: PARTICIPANT_JOINED, ITEM_CLAIM_TOGGLED, TAX_RECALCULATED, RECEIPT_LOCKED
- [ ] SIMULATE_FRIENDS action — 3 virtual roommates over 6 seconds

### 4.3 Finalize & Lock
- [ ] Finalize split → write ledger_entries in ACID transaction with idempotency key

### 4.4 Tests
- [ ] Concurrent WebSocket connection test
- [ ] Item toggle test with math recalculation

### 4.5 Verification Gate
- [ ] pytest WebSocket tests pass
- [ ] **USER APPROVAL REQUIRED** before Stage 5

---

## STAGE 5: Next.js Frontend — All Pages + Interactive Visualizations
**Status:** ⬜ Pending

### 5.1 Pages
- [ ] Landing page — Dark fintech hero, "Launch Instant Demo" button
- [ ] `/room/[code]` — Multiplayer claim room UI
- [ ] `/groups/[id]` — Debt simplifier graph + UPI settle modal
- [ ] `/dashboard` — Group overview + AI Copilot drawer
- [ ] `/metrics` — Public telemetry dashboard

### 5.2 Components
- [ ] ReceiptCard — Line item list with claim toggles
- [ ] AvatarPill — Colored participant indicator
- [ ] DebtGraph — SVG node-link visualization (raw vs simplified)
- [ ] UPISettleModal — QR code + deep link button
- [ ] CopilotDrawer — Chat interface
- [ ] MetricsDashboard — Live stats

### 5.3 Hooks
- [ ] `useRoomWebSocket` — WebSocket management
- [ ] `useReceiptSSE` — SSE streaming
- [ ] `useSandbox` — Demo sandbox initialization

### 5.4 Verification Gate
- [ ] Browser agent walkthrough: demo → receipt room → finalize → debt graph → settle
- [ ] **USER APPROVAL REQUIRED** before Stage 6

---

## STAGE 6: Rate Limiting, CI/CD & Production Readiness
**Status:** ⬜ Pending

### 6.1 Rate Limiting
- [ ] Redis sliding window middleware (AI endpoints: 10 req/min per IP)

### 6.2 CI/CD
- [ ] `.github/workflows/ci.yml` — pytest + ruff + next build

### 6.3 Documentation
- [ ] `README.md` — Portfolio-grade with Mermaid architecture diagram, 1-command setup

### 6.4 Verification Gate
- [ ] Full test suite passes
- [ ] Next.js production build succeeds
- [ ] README reviewed and approved

---

## Build Log

| Date | Stage | Action | Result |
|------|-------|--------|--------|
| 2026-10-17 | Stage 1 | Created SPEC.md + TASKS.md | ✅ Done |
| 2026-10-17 | Stage 1 | Created docker-compose.yml | In progress |
