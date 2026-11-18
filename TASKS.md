# SplitSmart AI — Task Tracker

> **Project:** SplitSmart AI | **Started:** 2026-10-17
> **Rule:** Never advance to the next stage without explicit user approval.

---

## STAGE 1: Workspace Spec, Monorepo Scaffolding, Docker & Database Layer
**Status:** 🟢 Completed

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
- [x] User approved proceeding to Stage 2

---

## STAGE 2: Core Math Engine, Debt Graph Algorithm & 1-Click Recruiter Sandbox
**Status:** 🟢 Completed

### 2.1 Core Services
- [x] `services/math_engine.py` — Proportional tax/discount distribution with paise invariant
- [x] `services/debt_simplifier.py` — Min-Cash-Flow O(N log N) algorithm
- [x] `services/upi_generator.py` — UPI deep link + QR code

### 2.2 One-Click Sandbox (Removed)
- [x] Removed `POST /api/v1/sandbox/init` and its seeder implementation.

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
- [x] User approved proceeding to Stage 3

---

## STAGE 3: Async Vision AI Receipt Pipeline & Real-Time SSE Progress
**Status:** 🟢 Completed

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
- [x] User approved proceeding to Stage 4

---

## STAGE 4: Multiplayer No-Login WebSocket Claim Room
**Status:** 🟢 Completed

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
- [x] User approved proceeding to Stage 5

| Date | Stage | Action | Result |
|------|-------|--------|--------|
| 2026-11-16 | Stage 4 | Implemented scoped guest rooms, Redis WebSockets, claim recalculation, simulation, and atomic finalization | ✅ Tests passing |

---

## STAGE 5: Next.js Frontend — All Pages + Interactive Visualizations
**Status:** 🟡 Implemented; live end-to-end walkthrough awaits Docker runtime

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
- [x] CopilotDrawer — Chat interface with configured Gemini backend
- [x] MetricsDashboard — Live stats

### 5.3 Hooks
- [x] `useRoomWebSocket` — WebSocket management
- [x] `useReceiptSSE` — SSE streaming
- [x] `useSandbox` — Removed with the one-click demo feature.

### 5.4 Verification Gate
- [x] Browser route smoke: landing, dashboard, metrics, group, and room routes load
- [x] `pytest -q` — 183 tests pass; `ruff check app tests` passes
- [x] Frontend `npm run type-check`, `npm run lint`, and `npm run build`
- [ ] Full backend-connected walkthrough: demo → receipt room → finalize → debt graph → settle (not run: Docker is unavailable in the environment)
- [x] User approved proceeding to Stage 6

Stage 5 pages and API integrations are implemented. The backend-connected walkthrough requires the Docker Compose stack; Copilot additionally requires `GEMINI_API_KEY`.

| Date | Stage | Action | Result |
|------|-------|--------|--------|
| 2026-11-16 | Stage 5 | Added dashboard, group/room/metrics pages, live API integrations, UPI payment UI, and endpoint tests | ✅ Implemented; live walkthrough needs the Compose services |

---

## STAGE 6: Rate Limiting, CI/CD & Production Readiness
**Status:** 🟡 Implemented; live Docker verification unavailable in this environment

### 6.1 Rate Limiting
- [x] Redis atomic sliding window limit for Copilot: 10 requests/minute per client IP
- [x] Redis atomic sliding window limit for receipt uploads: 20 requests/hour per client IP

### 6.2 CI/CD
- [x] `.github/workflows/ci.yml` — backend tests/lint and frontend type-check/lint/build

### 6.3 Documentation
- [x] `README.md` — Mermaid architecture diagram, one-command Docker Compose setup, API and privacy notes

### 6.4 Verification Gate
- [x] Full backend test suite passes
- [x] `ruff check app tests` passes
- [x] Next.js type-check, lint, and production build pass
- [ ] Run `docker compose up --build` and complete the live browser walkthrough (Docker is unavailable in this environment)
- [ ] README reviewed and approved

---

## Build Log

| Date | Stage | Action | Result |
|------|-------|--------|--------|
| 2026-10-17 | Stage 1 | Created SPEC.md + TASKS.md | ✅ Done |
| 2026-10-17 | Stage 1 | Created docker-compose.yml | In progress |
| 2026-11-16 | Stage 6 | Added Gemini Copilot API, Redis rate limits, CI workflow, and full-stack Compose setup | ✅ Tests/builds pass; live Docker walkthrough remains pending |
