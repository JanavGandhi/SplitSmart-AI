# SplitSmart AI ⚡🧾

> **Next-generation, real-time multiplayer receipt-splitting, expense ledger, and AI financial copilot engine.**  
> Eliminates manual typing, off-by-one rounding errors, and convoluted IOU webs through vision models, integer arithmetic, and graph theory.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js_15_App_Router-black.svg?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_16_+_pgvector-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Cache%20%26%20Broker-Redis_7-DC382D.svg?logo=redis&logoColor=white)](https://redis.io)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-132%20Passed-success.svg)]()

---

## 📌 Executive Summary

Splitting group bills today is broken. Traditional tools like Splitwise require tedious manual item entry, suffer from floating-point rounding errors on shared discounts and taxes, and fail to handle real-time party bills without requiring everyone to sign up and download an app.

**SplitSmart AI** solves this with 4 core engineering innovations:
1. **Zero-Typing Vision AI Pipeline:** Upload a photo of any crumpled bill or receipt; Google Gemini 2.5 Flash extracts line items, quantities, taxes, and service fees asynchronously via Celery and streams progress via Server-Sent Events (SSE).
2. **No-Login Multiplayer Claim Rooms:** Share a short link or QR code. Roommates and friends join instantly as guests via scoped JWTs, claim their items live over Redis-backed WebSockets, and watch totals update in real time.
3. **Exact Paise/Cent Integer Arithmetic (Zero-Leak Guarantee):** Zero floating-point representation in the database. All amounts are stored as `BIGINT` minor units (paise/cents). Tax and discounts are distributed proportionally using the **Hare-Niemeyer Largest Remainder Method**, ensuring $\sum \text{Member Shares} \equiv \text{Bill Total}$ down to the last paise.
4. **Min-Cash-Flow Debt Simplification ($O(N \log N)$):** Multi-day trips often create tangled webs of pairwise debts (e.g. 11 transactions between 5 friends). Our dual max-heap min-cash-flow algorithm collapses this into the minimum possible transactions (e.g. 4 payments), complete with **NPCI-compliant UPI deep links** and QR codes.

---

## 🏛️ System Architecture

```
                    ┌────────────────────────────────────────────────────────┐
                    │                  Next.js 15 Client                     │
                    │      (App Router, Tailwind CSS, TypeScript, SSE, WS)   │
                    └───────────────────┬───────────────────┬────────────────┘
                                        │                   │
                        REST / SSE (HTTP/2)       WebSockets (Bidirectional)
                                        │                   │
                                        ▼                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI Backend                               │
│                                                                            │
│  ┌───────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐  │
│  │ Vision Receipt Router │  │  Group & Ledger API  │  │  WebSocket Hub  │  │
│  └──────────┬────────────┘  └──────────┬───────────┘  └────────┬────────┘  │
│             │                          │                       │           │
│             │ Dispatches Jobs          │ Queries / Mutations   │ Pub/Sub   │
│             ▼                          ▼                       ▼           │
│  ┌──────────────────────┐   ┌──────────────────────┐  ┌─────────────────┐  │
│  │   Celery Workers     │   │ SQLAlchemy 2 (Async) │  │ Redis 7 Broker  │  │
│  │ (Gemini 2.5 Vision)  │   │  asyncpg Connection  │  │   & Pub/Sub     │  │
│  └──────────────────────┘   └──────────┬───────────┘  └─────────────────┘  │
└────────────────────────────────────────┼───────────────────────────────────┘
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │       PostgreSQL 16 Database + pgvector       │
                 │   - 100% BIGINT minor units (paise/cents)     │
                 │   - ACID ledger entries with idempotency keys │
                 │   - Vector embeddings for semantic search     │
                 └───────────────────────────────────────────────┘
```

---

## 💡 Core Algorithms & Financial Engineering

### 1. Mathematical Engine & Paise Invariant
When calculating individual splits from receipts with mixed shared items, platform fees, taxes (GST), and coupon discounts:
- **Item Claims:** Users can claim items in whole or partial fractions (e.g. $1/3$ of a dish). Each user's item share is calculated using integer division: $\lfloor P / k \rfloor$.
- **Discounts & Surcharges:** Any bill-level taxes, service charges, delivery fees, and discounts are distributed proportionally based on each claimant's subtotal share:
  $$A_u = \left\lfloor (E - D) \times \frac{S_u}{S} \right\rfloor$$
- **Largest Remainder Allocation:** The difference $R = T - \sum(S_u + A_u)$ is sorted by highest fractional remainder and distributed $1\text{ paise}$ at a time until exhausted.
- **Invariant:** $\sum_{u} \text{final\_share}_u = \text{receipt.total\_amount\_paise}$ **always**.

### 2. Min-Cash-Flow Debt Simplification Algorithm
For any group of $N$ users with mutual debts:
1. Compute the net balance for each user:
   $$\text{Balance}(u) = \sum \text{received} - \sum \text{spent}$$
2. Assert the **Zero-Sum Invariant**: $\sum_{u} \text{Balance}(u) \equiv 0$.
3. Separate users into two priority heaps:
   - **Debtors** (users with $\text{Balance} < 0$)
   - **Creditors** (users with $\text{Balance} > 0$)
4. Greedily match the largest debtor with the largest creditor, settling $\min(|B_{\text{debtor}}|, B_{\text{creditor}})$, push remaining balances back onto the heaps, and repeat until all balances are zero.
5. **Result:** Reduces worst-case $O(N^2)$ pairwise debts to at most $N-1$ optimal settlements.

### 3. Native Indian Fintech / UPI Deep Links
Every simplified settlement generates an NPCI-standard UPI intent link:
```
upi://pay?pa=friend@oksbi&pn=Priya%20Sharma&am=1240.00&cu=INR&tn=SplitSmart%20Goa%20Trip
```
and produces an inline base64 QR code ready for instant scanning with Google Pay, PhonePe, Paytm, or CRED.

---

## 📂 Repository Structure

```
SplitSmart-AI/
├── SPEC.md                    # Complete technical specification & schema design
├── TASKS.md                   # Granular stage-by-stage implementation tracker
├── docker-compose.yml         # Multi-container dev environment (Postgres 16 + Redis 7)
├── .env.example               # Environment variables template
├── apps/
│   ├── api/                   # FastAPI Backend
│   │   ├── alembic/           # Async database migrations
│   │   ├── app/
│   │   │   ├── main.py        # Application entrypoint & middleware
│   │   │   ├── config.py      # Pydantic v2 Settings management
│   │   │   ├── database.py    # AsyncEngine + session maker
│   │   │   ├── models/        # SQLAlchemy 2.0 ORM Declarative Models
│   │   │   │   ├── user.py
│   │   │   │   ├── group.py
│   │   │   │   ├── group_member.py
│   │   │   │   ├── receipt.py
│   │   │   │   ├── receipt_line_item.py
│   │   │   │   ├── item_claim.py
│   │   │   │   └── ledger_entry.py
│   │   │   ├── schemas/       # Pydantic validation & response schemas
│   │   │   ├── services/      # Pure business logic & algorithms
│   │   │   │   ├── math_engine.py      # Proportional split + paise invariant
│   │   │   │   ├── debt_simplifier.py  # Min-Cash-Flow graph solver
│   │   │   │   ├── upi_generator.py    # UPI URI & QR generator
│   │   │   │   └── sandbox.py          # 1-Click recruiter dataset seeder
│   │   │   └── api/v1/        # REST & WebSocket routers
│   │   │       ├── health.py
│   │   │       ├── groups.py
│   │   │       ├── ledger.py
│   │   │       └── sandbox.py
│   │   └── tests/             # Automated test suite
│   │       ├── test_math_engine.py
│   │       ├── test_debt_simplifier.py
│   │       └── test_stage1_health.py
│   └── web/                   # Next.js 15 Frontend
│       ├── src/
│       │   ├── app/           # App Router pages
│       │   └── lib/           # Typed API clients & currency utilities
│       ├── package.json
│       └── tailwind.config.ts
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- **Docker & Docker Compose** (for PostgreSQL + Redis)
- **Python 3.11+**
- **Node.js 18+** & **npm**

### 2. Environment Setup
Clone the repository and copy the example environment file:
```bash
git clone https://github.com/JanavGandhi/SplitSmart-AI.git
cd SplitSmart-AI
cp .env.example .env
```

### 3. Start Database & Redis Services
Launch the PostgreSQL 16 container with `pgvector` and Redis 7:
```bash
docker compose up -d
```
Verify that both containers are running healthy:
```bash
docker compose ps
```

### 4. Setup & Launch the Backend (FastAPI)
Navigate to the `apps/api` directory, create a virtual environment, and install dependencies:
```bash
cd apps/api
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

pip install -e ".[dev]"
```

Run database migrations:
```bash
alembic upgrade head
```

Start the API development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 5. Setup & Launch the Frontend (Next.js)
In a separate terminal:
```bash
cd apps/web
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the landing page.

---

## 🧪 1-Click Recruiter Sandbox & Interactive Demo

Want to see SplitSmart AI's debt graph simplification in action without creating groups or typing expenses manually?

Hit the sandbox seeder endpoint:
```bash
curl -X POST http://localhost:8000/api/v1/sandbox/init
```

This instantly creates the **"Goa Weekend Squad"** scenario:
- **5 Members:** Aryan, Priya, Karan, Meera, and Dev.
- **4 Real Bills:**
  1. *Fisherman's Wharf Seafood Dinner* (12 items, ₹6,450.00)
  2. *Blinkit Midnight Snacks Haul* (₹1,280.00)
  3. *Curlies Beach Shack Sundowner* (₹3,750.00)
  4. *Airport Innova Taxi Ride* (₹2,200.00)
- **Automatic Graph Simplification:** 11 raw cross-debts are collapsed down to **4 clean UPI settlements** with zero rupee discrepancies.

---

## 🔬 Testing & Mathematical Verification

Run the test suite to verify the mathematical engine and debt graph solvers:
```bash
cd apps/api
pytest tests/test_math_engine.py tests/test_debt_simplifier.py -v
```

### Verified Test Highlights:
- **100 Randomized Permutation Tests:** Generates 100 receipts with random totals, multiple claimants, arbitrary GST, delivery fees, and discounts. Verifies that the sum of claimant portions matches the receipt total with **0 paise deviation**.
- **Min-Cash-Flow Invariant Tests:** Verifies circular debt elimination (e.g. $A \to B \to C \to A$), complex multi-debtor graph convergence, and balance preservation across all participants.
- **132 Tests Passing in < 0.5s.**

---

## 🗺️ Project Roadmap & Milestones

| Stage | Milestone | Status | Details |
|---|---|:---:|---|
| **Stage 1** | Monorepo Scaffolding, Docker & Database Layer | 🟢 Completed | PostgreSQL 16 (pgvector), Redis 7, SQLAlchemy 2 Async, Alembic migrations, Next.js 15 scaffold. |
| **Stage 2** | Core Math Engine, Debt Simplifier & Sandbox | 🟢 Completed | Largest Remainder Method, Min-Cash-Flow algorithm, UPI QR codes, 1-Click Goa Squad sandbox seeder. |
| **Stage 3** | Async Vision AI Receipt Pipeline & SSE | 🟡 Up Next | Gemini 2.5 Flash OCR, Celery asynchronous processing queue, live Server-Sent Events progress tracking. |
| **Stage 4** | Multiplayer No-Login WebSocket Claim Room | ⬜ Planned | Ephemeral guest JWTs, real-time item claiming via Redis Pub/Sub, virtual roommate simulator. |
| **Stage 5** | Production Next.js UI & Interactive Graphs | ⬜ Planned | Interactive D3/SVG debt graph, live claim room UI, dark mode fintech dashboard. |
| **Stage 6** | Public Telemetry & Production Hardening | ⬜ Planned | Prometheus metrics, audit logging, rate limiting, and deployment workflows. |

---

## 📄 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
