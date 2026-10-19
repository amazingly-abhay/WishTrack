# WishTrack

WishTrack is a modern, privacy-focused wishlist Progressive Web App (PWA) with a companion Chromium Manifest V3 browser extension. It enables users to save products from multiple e-commerce sites, securely track prices for at least 365 days, and receive instant notifications on price drops, target hits, and new 365-day lows.

---

## 🏛 Monorepo Structure

```text
wishtrack/
├── apps/
│   ├── web/                  # React + TypeScript + Vite PWA
│   ├── extension/            # Chromium Manifest V3 browser extension
│   └── api/                  # FastAPI backend (Modular Monolith)
├── workers/
│   ├── scheduler/            # Finds due items and schedules checks
│   └── price_worker/         # Performs rate-limited checks and alert evals
├── docs/
│   ├── PROJECT_SPEC.md       # Single source of truth specifications
│   ├── CURRENT_STATE_AND_INTERVIEW.md  # Implementation state & interview QA
│   ├── FLOWS.md              # Data and user flow documentation
│   ├── ARCHITECTURE_AND_DECISIONS.md   # Architectural design & rationale
│   └── DECISIONS.md          # Architectural Decision Records (ADRs)
├── tests/                    # End-to-end and shared test fixtures
├── .env.example              # Template environment variables
├── .gitignore                # Git ignore configuration
└── README.md                 # Project setup and operations guide
```

---

## 🚀 Getting Started (Local Development without Docker)

### Prerequisites
- **Python:** 3.11+
- **Node.js:** 20+ (with `npm`)
- **PostgreSQL 16** (or SQLite for local development/testing)
- **Redis 7** (or in-memory mock for local unit testing)

### 1. Backend Setup (`apps/api`)
```bash
# Navigate to backend
cd apps/api

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp ../../.env.example .env

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
API Documentation will be available at: `http://localhost:8000/docs`

### 2. Frontend PWA Setup (`apps/web`)
```bash
# Navigate to frontend
cd apps/web

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
PWA will be available at: `http://localhost:5173`

### 3. Browser Extension Setup (`apps/extension`)
```bash
# Navigate to extension
cd apps/extension
npm install
npm run build
```
Load the unpacked extension from `apps/extension/dist` in Chrome/Brave via `chrome://extensions`.

---

## 🧪 Running Tests
```bash
# Backend tests
cd apps/api
pytest tests/ -v

# Frontend tests
cd apps/web
npm test
```

---

## 📜 Development Guidelines
- Follow `docs/PROJECT_SPEC.md` strictly as the single source of truth.
- Update `docs/CURRENT_STATE_AND_INTERVIEW.md`, `docs/FLOWS.md`, and `docs/ARCHITECTURE_AND_DECISIONS.md` on every major exit.
