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
pnpm build            # Production build
pnpm lint             # ESLint validation
```

### Backend (services/analytics)
```bash
uv sync               # Install dependencies
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload   # Dev server
uv run pytest         # Run tests
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
                  Next.js Frontend
```

### Backend Structure (services/analytics/app/)
- `main.py` - FastAPI app with CORS, lifespan, and all route definitions
- `oura/auth.py` - OAuth 2.0 token management with automatic refresh
- `oura/client.py` - Oura API HTTP client
- `pipelines/ingest.py` - Data ingestion from Oura API to normalized tables
- `pipelines/features.py` - Rolling means, lag features, deltas, variability metrics
- `analysis/correlations.py` - Spearman, lagged, and controlled correlations
- `analysis/patterns.py` - Change points (PELT), anomaly detection, weekly clustering
- `db.py` - Async PostgreSQL connection pooling
- `settings.py` - Environment configuration via pydantic-settings

### Frontend Structure (apps/web/src/)
- `app/` - Next.js App Router pages (dashboard, settings, OAuth callback)
- `components/ui/` - shadcn/ui components (Card, Button, Tabs, Dialog, etc.)
- `lib/api-client.ts` - Type-safe client for analytics API

### API Endpoints
- **Auth:** `GET /auth/url`, `POST /auth/oura/exchange`, `GET /auth/status`, `POST /auth/revoke`
- **Admin:** `POST /admin/ingest`, `POST /admin/features`
- **Analysis:** `POST /analyze/correlations/{spearman,lagged,controlled}`, `POST /analyze/patterns/{change-points,anomalies,weekly-clusters}`

## Key Patterns

- **Path alias:** `@/*` maps to `./src/*` in frontend
- **Shared schemas:** Zod schemas in `packages/shared` for frontend/backend type safety
- **OAuth flow:** Frontend redirects to Oura → callback at `/api/oura/callback` → exchanges code via analytics service
- **Token refresh:** Automatic with 2-minute buffer before expiry
- **Async throughout:** FastAPI async endpoints, psycopg async driver, Next.js server components

## Environment Variables

Required in `.env`:
```
OURA_CLIENT_ID=...
OURA_CLIENT_SECRET=...
```

Analytics service also uses:
- `DATABASE_URL` - PostgreSQL connection string
- `OURA_REDIRECT_URI` - OAuth callback URL (default: http://localhost:3000/api/oura/callback)
