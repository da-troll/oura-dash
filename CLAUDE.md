# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Oura Lab is a personal analytics application for Oura Ring data. Full-stack monorepo with:
- **Frontend:** Next.js 16 with React 19 and TypeScript (`apps/web/`)
- **Backend:** FastAPI (Python 3.11+) with async PostgreSQL (`services/analytics/`)
- **Shared types:** TypeScript package with Zod schemas (`packages/shared/`)

## Build and Development Commands

### Frontend (apps/web)
```bash
pnpm install          # Install dependencies
pnpm dev              # Dev server at http://localhost:3000
pnpm build            # Production build (standalone output for Docker)
pnpm lint             # ESLint validation
```

### Backend (services/analytics)
```bash
uv sync               # Install dependencies (uses uv for fast installs)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload   # Dev server
uv run pytest         # Run tests (currently no tests configured)
```

### Shared Package (packages/shared)
```bash
npm run build         # Compile TypeScript
npm run dev           # Watch mode
```

### Full Stack (Docker Compose)
```bash
docker-compose up -d  # Start PostgreSQL (5433), analytics (8001), web (3000)
```

## Architecture

```
Oura Cloud API ↔ FastAPI Analytics Service ↔ PostgreSQL
                        ↑
                  Next.js Frontend (BFF pattern for OAuth)
```

### Data Flow
1. **Ingestion**: OAuth-authenticated requests to Oura API → raw JSON stored → normalized to `oura_daily`
2. **Feature Engineering**: `oura_daily` → derived metrics → `oura_features_daily`
3. **Analysis**: Frontend requests → FastAPI computes correlations/patterns → returns insights
4. **Visualization**: Frontend renders charts with Recharts using API data

## Frontend Structure (apps/web)

### Page Routes (App Router)
- `/` - Root page (redirects to dashboard)
- `/dashboard` - Summary metrics, trends, and key statistics
- `/correlations` - Interactive tools for Spearman, lagged, and partial correlations
- `/patterns` - Change point detection, anomaly detection, weekly clustering
- `/insights` - Annual heatmaps, sleep architecture visualization, chronotype analysis
- `/settings` - OAuth connection management, manual sync triggers

### API Routes (Backend-for-Frontend)
- `/api/oura/auth` - Initiates OAuth flow, redirects to Oura
- `/api/oura/callback` - OAuth callback handler, exchanges code for tokens

### Component Structure
- `app/` - Next.js pages using App Router
- `components/ui/` - shadcn/ui base components (Button, Card, Tabs, Dialog, etc.)
- `components/theme-provider.tsx` - Dark/light mode context
- `components/theme-toggle.tsx` - Theme switcher component
- `lib/api-client.ts` - Thin wrapper for analytics API calls (not consistently used)

### State Management
- **Local state only**: React `useState` and `useEffect` hooks in page components
- **No global state**: No Redux, Zustand, or similar libraries
- **Data fetching**: Direct `fetch` calls to analytics service in `useEffect`

### Styling & UI
- **Tailwind CSS**: Utility-first styling (`tailwind.config.mjs`, `globals.css`)
- **shadcn/ui**: Pre-built component library with Tailwind integration
- **Theme variables**: CSS custom properties in `globals.css` for light/dark modes
- **Icons**: `lucide-react` for consistent iconography

### Key Dependencies
- `next@16.x` - React framework with App Router
- `react@19.x` - UI library
- `recharts` - Chart library for all visualizations
- `tailwindcss` - Styling framework
- `lucide-react` - Icon library
- `next-themes` - Dark mode management
- `zod` - Schema validation (from `packages/shared`)

## Backend Structure (services/analytics)

### Application Layout (app/)
- `main.py` - FastAPI app, CORS config, lifespan management, all route definitions
- `schemas.py` - Pydantic models for request/response validation (mirrors Zod schemas)
- `db.py` - Async PostgreSQL connection pooling with `psycopg`
- `settings.py` - Environment configuration using `pydantic-settings`

### OAuth & API Client (app/oura/)
- `auth.py` - OAuth 2.0 flow (authorization URL, token exchange, automatic refresh)
- `client.py` - HTTP client for Oura API with token management

### Data Pipelines (app/pipelines/)
- `ingest.py` - Three-stage ingestion:
  1. `ingest_raw_data()` - Fetches from Oura API, stores raw JSON in `oura_raw`
  2. `normalize_daily_data()` - Parses raw JSON, populates structured `oura_daily`
  3. `ingest_tags()` - Processes tags into `oura_day_tags`
- `features.py` - Feature engineering:
  - `recompute_features()` - Generates derived metrics from `oura_daily`:
    - Rolling means (7-day, 14-day, 28-day windows)
    - Standard deviations for variability metrics
    - Deltas (current value vs rolling mean)
    - Lagged features (1-day, 7-day lags)
    - Trend indicators

### Analysis Modules (app/analysis/)
- `correlations.py` - Statistical correlation analysis:
  - Spearman rank correlations (handles non-linear relationships)
  - Lagged correlations (time-shifted relationships)
  - Partial correlations (controlled for confounders)
  - Uses `pandas` and `scipy.stats`
- `patterns.py` - Pattern detection:
  - Change point detection using PELT algorithm (`ruptures` library)
  - Anomaly detection with z-score and IQR methods (`scipy.stats`)
  - Weekly clustering with K-means (`scikit-learn`)

### API Endpoints (all in main.py)

#### Authentication
- `GET /auth/url` - Generate Oura OAuth authorization URL
- `POST /auth/oura/exchange` - Exchange authorization code for access/refresh tokens
- `GET /auth/status` - Check if user has valid Oura API connection
- `POST /auth/revoke` - Revoke Oura access and delete stored tokens

#### Dashboard
- `GET /dashboard` - Summary metrics and trends for main dashboard

#### Correlations
- `POST /analyze/correlations/spearman` - Compute Spearman rank correlations
- `POST /analyze/correlations/lagged` - Analyze time-shifted correlations
- `POST /analyze/correlations/controlled` - Calculate partial correlations

#### Patterns
- `POST /analyze/patterns/change-points` - Detect significant metric shifts
- `POST /analyze/patterns/anomalies` - Find unusual values (outliers)
- `POST /analyze/patterns/weekly-clusters` - Group weeks into behavioral patterns

#### Insights
- `GET /insights/heatmap` - Annual metric heatmap data
- `GET /insights/sleep-architecture` - Sleep stage distribution and patterns
- `GET /insights/chronotype` - Sleep timing analysis, chronotype classification, social jetlag

#### Admin
- `POST /admin/ingest` - Trigger full data ingestion pipeline
- `POST /admin/features` - Trigger feature engineering pipeline

### Key Backend Dependencies
- `fastapi` - Web framework with async support
- `uvicorn` - ASGI server
- `psycopg[binary]` - Async PostgreSQL driver
- `pandas` - Data manipulation and analysis
- `numpy` - Numerical computing
- `scipy` - Statistical functions
- `scikit-learn` - Machine learning (clustering)
- `statsmodels` - Advanced statistical modeling
- `ruptures` - Change point detection algorithms
- `httpx` - HTTP client for Oura API calls

## Database Schema

### Tables

#### `oura_auth`
Single-row table storing OAuth credentials:
- `access_token` - Current Oura API access token
- `refresh_token` - Token for refreshing expired access tokens
- `expires_at` - Timestamp when access token expires

#### `oura_raw`
Raw JSON payloads from Oura API:
- `source` - Data type (e.g., 'sleep', 'daily_activity', 'readiness')
- `day` - Date of the data
- `data` - Raw JSON payload from Oura API

#### `oura_daily`
Main structured data table (one row per day):
- **Sleep metrics**: `sleep_score`, `sleep_total_seconds`, `sleep_rem_seconds`, `sleep_deep_seconds`, `sleep_light_seconds`, `sleep_awake_seconds`, `sleep_latency_seconds`, `sleep_efficiency`, `sleep_restfulness`, `sleep_timing`
- **Activity metrics**: `steps`, `cal_active`, `cal_total`, `meters_total`, `equivalent_walking_distance`, `activity_score`, `activity_high`, `activity_medium`, `activity_low`, `activity_sedentary_seconds`, `activity_rest_mode_state`
- **Readiness metrics**: `readiness_score`, `hrv_average`, `resting_heart_rate`, `body_temperature_celsius`, `readiness_temperature_deviation`
- **Meta**: `date` (primary key), timestamps

#### `oura_day_tags`
User tags for days:
- `date` - Day being tagged (foreign key to `oura_daily`)
- `tag` - String tag label

#### `oura_features_daily`
Derived metrics from feature engineering:
- **Rolling means**: `rm_7_*`, `rm_14_*`, `rm_28_*` (7/14/28-day moving averages)
- **Variability**: `std_7_*`, `std_14_*`, `std_28_*` (rolling standard deviations)
- **Deltas**: `delta_*_vs_rm7` (current value vs 7-day mean)
- **Lags**: `lag_1_*`, `lag_7_*` (previous day/week values)
- **Trends**: Derived trend indicators

### Relationships
- `oura_daily` ← `oura_day_tags` (one-to-many on `date`)
- `oura_daily` ← `oura_features_daily` (one-to-one on `date`)

### Migration Strategy
- SQL migrations stored in `services/analytics/migrations/`
- **Note**: Initial migration file `001_init.sql` is currently missing

## Shared Package (packages/shared)

### Purpose
- Single source of truth for data structures using Zod schemas
- Provides TypeScript types for frontend and backend API contracts
- Located in `src/schemas.ts`

### Current Limitations
- **Backend duplication**: Backend defines parallel Pydantic models in `services/analytics/app/schemas.py`
- **Not fully integrated**: Backend doesn't consume the shared package directly
- **Frontend-only usage**: Currently only used on the frontend

### Schemas Defined
All request/response schemas for API endpoints (correlations, patterns, dashboard, etc.)

## Key Patterns & Conventions

### Frontend
- **Path alias**: `@/*` maps to `./src/*` in imports
- **Component naming**: PascalCase for React components
- **Styling**: Tailwind utility classes, avoid custom CSS
- **Data fetching**: `fetch` with `useEffect` (consider consistent use of `lib/api-client.ts`)
- **Error handling**: Try-catch blocks with user-friendly error messages

### Backend
- **Async-first**: All endpoints and database calls use `async`/`await`
- **Type safety**: Pydantic models for validation
- **Error responses**: FastAPI HTTPException with appropriate status codes
- **Database**: Context managers for connection handling
- **Token refresh**: Automatic with 2-minute buffer before expiry in `oura/auth.py`

### OAuth Flow
1. Frontend initiates: `/api/oura/auth` → redirects to Oura authorization page
2. User authorizes on Oura's site
3. Oura redirects to: `/api/oura/callback?code=...`
4. Callback exchanges code via analytics service: `POST /auth/oura/exchange`
5. Analytics service stores tokens in `oura_auth` table
6. Subsequent API calls use stored tokens (auto-refresh on expiry)

### Data Pipeline
1. **Ingest** (`POST /admin/ingest`): Oura API → `oura_raw` → `oura_daily`
2. **Features** (`POST /admin/features`): `oura_daily` → compute derived metrics → `oura_features_daily`
3. **Analyze**: Endpoints read from `oura_daily` and `oura_features_daily` to compute insights

## Environment Variables

### Required in `.env`
```bash
# Oura API OAuth credentials
OURA_CLIENT_ID=...
OURA_CLIENT_SECRET=...

# Database connection (analytics service)
DATABASE_URL=postgresql://user:password@localhost:5433/oura

# OAuth callback (analytics service)
OURA_REDIRECT_URI=http://localhost:3000/api/oura/callback

# Frontend API endpoint (frontend)
NEXT_PUBLIC_ANALYTICS_URL=http://localhost:8001
```

### Example Files
- `.env.example` files provided in relevant directories
- Docker Compose passes environment variables to containers

## Testing

**Current Status**: No test suite configured
- No unit tests for frontend or backend
- No integration tests
- No end-to-end tests

**Testing Commands Listed**: `uv run pytest` is documented but will not find tests

## Docker & Deployment

### Docker Compose Services
- **`db`**: PostgreSQL 15 on port 5433
- **`analytics`**: FastAPI backend on port 8001
- **`web`**: Next.js frontend on port 3000

### Dockerfiles
- `services/analytics/Dockerfile` - Uses `uv` for fast Python dependency installation
- `apps/web/Dockerfile` - Uses Next.js standalone output for minimal image size

### Production Build
- Frontend: `next build` creates optimized production bundle
- Backend: Runs directly from source with `uvicorn`

## Development Workflow

### Adding a New Metric
1. Update Oura API ingestion in `services/analytics/app/pipelines/ingest.py`
2. Add column to `oura_daily` table (migration needed)
3. Update feature engineering in `services/analytics/app/pipelines/features.py`
4. Add Pydantic model in `services/analytics/app/schemas.py`
5. Add Zod schema in `packages/shared/src/schemas.ts`
6. Update frontend UI to display new metric

### Adding a New Analysis
1. Create analysis function in `services/analytics/app/analysis/`
2. Add endpoint in `services/analytics/app/main.py`
3. Create Pydantic request/response models
4. Add corresponding Zod schemas
5. Create frontend page or component to trigger and display analysis

### Debugging Tips
- **Frontend**: Check browser console for errors, verify API URL is correct
- **Backend**: Check FastAPI auto-docs at `http://localhost:8001/docs`
- **Database**: Connect directly with `psql` to inspect data
- **OAuth**: Check token expiry in `oura_auth` table, verify client ID/secret
- **CORS**: Ensure frontend origin is allowed in `main.py` CORS middleware
