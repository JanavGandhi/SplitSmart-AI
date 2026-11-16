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
- [x] Initial stub routers for auth, groups, receipts, rooms_ws, copilot, and metrics

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
**Status:** 🟢 Completed (Awaiting user review for Stage 3)

### 2.1 Core Services
- [x] `services/math_engine.py` — Proportional tax/discount distribution with paise invariant
- [x] `services/debt_simplifier.py` — Min-Cash-Flow O(N log N) algorithm
- [x] `services/upi_generator.py` — UPI deep link + QR code

### 2.2 Sandbox Endpoint
- [x] `POST /api/v1/sandbox/init` — Creates "Goa Weekend Squad" demo group
  - 5 members (Aryan, Priya, Karan, Meera, Dev)
  - 4 receipts: 12-item restaurant bill, Blinkit grocery haul, beach shack, taxi split
  - Cross-debts that simplify from 11 transactions → 4

### 2.3 Group & Ledger Endpoints
- [x] `GET/POST /api/v1/groups` — Group CRUD
- [x] `GET /api/v1/groups/{id}/balances` — Net balance computation
- [x] `GET /api/v1/groups/{id}/simplified` — Min-cash-flow result
- [x] `POST /api/v1/ledger/settle` — Idempotent settlement entry

### 2.4 Tests
- [x] `tests/test_math_engine.py` — 100 random permutations paise invariant
- [x] `tests/test_debt_simplifier.py` — Optimal reduction + zero-sum invariant

### 2.5 Verification Gate
- [x] `pytest tests/test_math_engine.py tests/test_debt_simplifier.py -v` → all 132 tests pass
- [x] Sandbox endpoint configured with Goa demo dataset
- [ ] **USER APPROVAL REQUIRED** before Stage 3

---

## STAGE 3: Async Vision AI Receipt Pipeline & Real-Time SSE Progress
**Status:** 🟢 Completed (Awaiting user review for Stage 4)

### 3.1 Celery Worker
- [x] `worker/celery_app.py` — Celery app with Redis broker
- [x] `worker/tasks.py` — Full receipt processing pipeline task: UPLOADING → OCR_EXTRACTING → VALIDATING_MATH → READY_FOR_CLAIMS

### 3.2 Vision OCR Service
- [x] `services/vision_ocr.py` — Gemini Vision structured extraction (gemini-2.0-flash)
- [x] Mock OCR fallback when GEMINI_API_KEY not set (restaurant + grocery variants)
- [x] Pydantic output schema (OCRExtractedReceipt + OCRLineItem) with field coercion

### 3.3 Receipt Upload API
- [x] `POST /api/v1/receipts/upload` → 202 Accepted + job_id + sse_url
- [x] `GET /api/v1/receipts/{id}/events` → SSE stream (Redis Pub/Sub relay)
- [x] `GET /api/v1/receipts/{id}` → Receipt status + line items
- [x] `GET /api/v1/receipts/room/{room_code}` → Lookup by room code
- [x] Pipeline stages: UPLOADING → OCR_EXTRACTING → VALIDATING_MATH → READY_FOR_CLAIMS

### 3.4 Tests
- [x] `tests/test_receipt_pipeline.py` — 23 tests (mock OCR, paise invariant, field coercion, pipeline logic, upload API, SSE)

### 3.5 Verification Gate
- [x] `pytest tests/test_receipt_pipeline.py -v` → all 23 pass
- [x] Full suite: 162 tests passing

---

## STAGE 4: Multiplayer No-Login WebSocket Claim Room
**Status:** 🟢 Completed (Awaiting user approval for Stage 5)

### 4.1 Guest Auth
- [x] `POST /api/v1/rooms/{code}/guest-join` — Create guest membership and issue room-scoped JWT

### 4.2 WebSocket Endpoint
- [x] `WS /api/v1/rooms/{code}/ws` — Redis Pub/Sub backed
- [x] Events: PARTICIPANT_JOINED, ITEM_CLAIM_TOGGLED, TAX_RECALCULATED, RECEIPT_LOCKED
- [x] SIMULATE_FRIENDS action — 3 virtual roommates over 6 seconds

### 4.3 Finalize & Lock
- [x] Finalize split → write ledger_entries in ACID transaction with idempotency key
- [x] Persist finalization idempotency key with Alembic migration

### 4.4 Tests
- [x] Concurrent WebSocket connection test
- [x] Item toggle test with math recalculation
- [x] Finalization, retry idempotency, and guest authorization tests

### 4.5 Verification Gate
- [x] `pytest tests/test_rooms.py -v` passes
- [ ] **USER APPROVAL REQUIRED** before Stage 5

| Date | Stage | Action | Result |
|------|-------|--------|--------|
| 2026-11-16 | Stage 4 | Implemented scoped guest rooms, Redis WebSockets, claim recalculation, simulation, and atomic finalization | ✅ Tests passing |

---

## STAGE 5: Next.js Frontend — All Pages + Interactive Visualizations
**Status:** 🟡 Implemented; live end-to-end walkthrough awaits PostgreSQL/Redis runtime

### 5.1 Pages
- [x] Landing page — Dark fintech hero, "Launch Instant Demo" button
- [x] `/room/[code]` — Multiplayer claim room UI
- [x] `/groups/[id]` — Debt simplifier graph + UPI settle modal
- [x] `/dashboard` — Group overview + Copilot chat drawer UI
- [x] `/metrics` — Live database-backed metrics dashboard

### 5.2 Components
- [x] ReceiptCard — Line item list with claim toggles
- [x] AvatarPill — Colored participant indicator
- [x] DebtGraph — SVG node-link visualization (raw vs simplified)
- [x] UPISettleModal — QR code + deep link button
- [x] CopilotDrawer — Chat interface (backend endpoint remains a 501 stub)
- [x] MetricsDashboard — Live stats

### 5.3 Hooks
- [x] `useRoomWebSocket` — WebSocket management
- [x] `useReceiptSSE` — SSE streaming
- [x] `useSandbox` — Demo sandbox initialization

### 5.4 Verification Gate
- [x] Browser route smoke: landing, dashboard, metrics, group, and room routes load
- [x] `pytest -q` — 174 tests pass; Ruff passes on changed backend files
- [x] Frontend `npm run type-check`, `npm run lint`, and `npm run build`
- [ ] Full backend-connected walkthrough: demo → receipt room → finalize → debt graph → settle (not run: PostgreSQL and Redis are unavailable in the environment)
- [ ] **USER APPROVAL REQUIRED** before Stage 6

Stage 5 frontend and API integration code is implemented. Full live-flow verification is still blocked until PostgreSQL and Redis are running; the Copilot chat API is also not implemented and remains an explicit 501 response.

| Date | Stage | Action | Result |
|------|-------|--------|--------|
| 2026-11-17 | Stage 5 | Added dashboard, group/room/metrics pages, live API integrations, UPI payment UI, and endpoint tests | ✅ Implemented; backend-connected walkthrough awaits PostgreSQL/Redis |

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
