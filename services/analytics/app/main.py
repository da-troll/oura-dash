"""Main FastAPI application."""

from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.analysis import correlations, patterns
from app.oura import auth as oura_auth
from app.pipelines import features, ingest
from app.db import get_db
from app.schemas import (
    AnomalyResponse,
    AuthStatusResponse,
    AuthUrlResponse,
    ChangePointResponse,
    ControlledCorrelationResponse,
    DashboardResponse,
    DashboardSummary,
    ExchangeCodeRequest,
    ExchangeCodeResponse,
    HealthResponse,
    LaggedCorrelationResponse,
    SpearmanResponse,
    SyncResponse,
    TrendPoint,
    WeeklyClusterResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="Oura Analytics",
    description="Personal analytics service for Oura Ring data",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(ok=True)


# ============================================
# Dashboard Endpoints
# ============================================


@app.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard() -> DashboardResponse:
    """Get dashboard summary data."""
    # Check auth status
    status = await oura_auth.get_auth_status()
    if not status["connected"]:
        return DashboardResponse(
            connected=False,
            summary=DashboardSummary(),
            readiness_trend=[],
        )

    async with get_db() as conn:
        async with conn.cursor() as cur:
            # Get 7-day averages
            await cur.execute("""
                SELECT
                    AVG(readiness_score) as readiness_avg,
                    AVG(sleep_score) as sleep_avg,
                    AVG(activity_score) as activity_avg,
                    AVG(steps) as steps_avg,
                    COUNT(*) as days_with_data
                FROM oura_daily
                WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                AND (readiness_score IS NOT NULL
                     OR sleep_score IS NOT NULL
                     OR activity_score IS NOT NULL
                     OR steps IS NOT NULL)
            """)
            summary_row = await cur.fetchone()

            # Get 28-day readiness trend with rolling baseline
            await cur.execute("""
                WITH daily_data AS (
                    SELECT
                        date,
                        readiness_score as value,
                        AVG(readiness_score) OVER (
                            ORDER BY date
                            ROWS BETWEEN 27 PRECEDING AND CURRENT ROW
                        ) as baseline
                    FROM oura_daily
                    WHERE date >= CURRENT_DATE - INTERVAL '28 days'
                    ORDER BY date
                )
                SELECT date, value, baseline
                FROM daily_data
                ORDER BY date
            """)
            trend_rows = await cur.fetchall()

    summary = DashboardSummary(
        readiness_avg=round(summary_row["readiness_avg"], 1) if summary_row["readiness_avg"] else None,
        sleep_avg=round(summary_row["sleep_avg"], 1) if summary_row["sleep_avg"] else None,
        activity_avg=round(summary_row["activity_avg"], 1) if summary_row["activity_avg"] else None,
        steps_avg=round(summary_row["steps_avg"]) if summary_row["steps_avg"] else None,
        days_with_data=summary_row["days_with_data"] or 0,
    )

    readiness_trend = [
        TrendPoint(
            date=str(row["date"]),
            value=row["value"],
            baseline=round(row["baseline"], 1) if row["baseline"] else None,
        )
        for row in trend_rows
    ]

    return DashboardResponse(
        connected=True,
        summary=summary,
        readiness_trend=readiness_trend,
    )


# ============================================
# OAuth Endpoints
# ============================================


@app.get("/auth/url", response_model=AuthUrlResponse)
async def get_auth_url() -> AuthUrlResponse:
    """Get Oura OAuth authorization URL."""
    url, state = await oura_auth.get_auth_url()
    return AuthUrlResponse(url=url, state=state)


@app.post("/auth/oura/exchange", response_model=ExchangeCodeResponse)
async def exchange_code(request: ExchangeCodeRequest) -> ExchangeCodeResponse:
    """Exchange OAuth authorization code for tokens.

    This endpoint is called by the Next.js callback handler.
    The client_secret is used here on the server side.
    """
    try:
        tokens = await oura_auth.exchange_code(request.code)
        await oura_auth.store_tokens(tokens)
        return ExchangeCodeResponse(success=True, message="Connected to Oura")
    except oura_auth.OAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/auth/status", response_model=AuthStatusResponse)
async def get_auth_status() -> AuthStatusResponse:
    """Get current authentication status."""
    status = await oura_auth.get_auth_status()
    return AuthStatusResponse(
        connected=status["connected"],
        expires_at=status.get("expires_at"),
        scopes=status.get("scopes"),
    )


@app.post("/auth/revoke")
async def revoke_auth():
    """Disconnect from Oura (clear stored tokens)."""
    await oura_auth.clear_auth()
    return {"success": True, "message": "Disconnected from Oura"}


# ============================================
# Admin Endpoints
# ============================================


@app.post("/admin/ingest", response_model=SyncResponse)
async def admin_ingest(
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Run the full ingestion pipeline for a date range.

    This fetches data from Oura API, stores raw payloads,
    and normalizes into the daily tables.
    """
    try:
        result = await ingest.run_full_ingest(start, end)
        return SyncResponse(
            status="completed",
            days_processed=result["days_processed"],
            message=f"Ingested {result['days_processed']} days, {result['tags_processed']} tags",
        )
    except oura_auth.OAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/features", response_model=SyncResponse)
async def admin_features(
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Compute derived features for a date range.

    This computes rolling means, lags, deltas, and variability features
    from the daily data.
    """
    try:
        days_processed = await features.recompute_features(start, end)
        return SyncResponse(
            status="completed",
            days_processed=days_processed,
            message=f"Computed features for {days_processed} days",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Correlation Endpoints
# ============================================


@app.post("/analyze/correlations/spearman", response_model=SpearmanResponse)
async def analyze_spearman(
    target: str = Query(..., description="Target metric"),
    candidates: list[str] = Query(..., description="Candidate metrics"),
    start: date | None = Query(None, description="Start date (optional)"),
    end: date | None = Query(None, description="End date (optional)"),
):
    """Compute Spearman correlations between target and candidate metrics."""
    result = await correlations.get_spearman_correlations(
        target, candidates, start, end
    )
    return SpearmanResponse(
        target=result["target"],
        correlations=[
            {
                "metric": c["metric"],
                "rho": c["rho"],
                "p_value": c["p_value"],
                "n": c["n"],
            }
            for c in result["correlations"]
        ],
    )


@app.post("/analyze/correlations/lagged", response_model=LaggedCorrelationResponse)
async def analyze_lagged(
    metric_x: str = Query(..., description="Predictor metric"),
    metric_y: str = Query(..., description="Target metric"),
    max_lag: int = Query(7, description="Maximum lag to test"),
    start: date | None = Query(None, description="Start date (optional)"),
    end: date | None = Query(None, description="End date (optional)"),
):
    """Compute lagged correlations to find if X predicts Y."""
    result = await correlations.get_lagged_correlations(
        metric_x, metric_y, max_lag, start, end
    )
    return LaggedCorrelationResponse(
        metric_x=result["metric_x"],
        metric_y=result["metric_y"],
        lags=[
            {
                "lag": l["lag"],
                "rho": l["rho"],
                "p_value": l["p_value"],
                "n": l["n"],
            }
            for l in result["lags"]
        ],
        best_lag=result["best_lag"],
    )


@app.post("/analyze/correlations/controlled", response_model=ControlledCorrelationResponse)
async def analyze_controlled(
    metric_x: str = Query(..., description="First metric"),
    metric_y: str = Query(..., description="Second metric"),
    control_vars: list[str] = Query(..., description="Variables to control for"),
    start: date | None = Query(None, description="Start date (optional)"),
    end: date | None = Query(None, description="End date (optional)"),
):
    """Compute partial correlation controlling for confounders."""
    result = await correlations.get_controlled_correlation(
        metric_x, metric_y, control_vars, start, end
    )
    return ControlledCorrelationResponse(
        metric_x=result["metric_x"],
        metric_y=result["metric_y"],
        rho=result["rho"],
        p_value=result["p_value"],
        n=result["n"],
        controlled_for=result["controlled_for"],
    )


# ============================================
# Pattern Endpoints
# ============================================


@app.post("/analyze/patterns/change-points", response_model=ChangePointResponse)
async def analyze_change_points(
    metric: str = Query(..., description="Metric to analyze"),
    start: date | None = Query(None, description="Start date (optional)"),
    end: date | None = Query(None, description="End date (optional)"),
    penalty: float = Query(10.0, description="PELT penalty parameter"),
):
    """Detect change points in a metric time series."""
    result = await patterns.get_change_points(metric, start, end, penalty)
    return ChangePointResponse(
        metric=result["metric"],
        change_points=[
            {
                "date": cp.get("date", ""),
                "index": cp["index"],
                "before_mean": cp["before_mean"],
                "after_mean": cp["after_mean"],
                "magnitude": cp["magnitude"],
                "direction": cp["direction"],
            }
            for cp in result["change_points"]
        ],
    )


@app.post("/analyze/patterns/anomalies", response_model=AnomalyResponse)
async def analyze_anomalies(
    metric: str = Query(..., description="Metric to analyze"),
    start: date | None = Query(None, description="Start date (optional)"),
    end: date | None = Query(None, description="End date (optional)"),
    threshold: float = Query(3.0, description="Z-score threshold"),
):
    """Detect anomalies in a metric time series."""
    result = await patterns.get_anomalies(metric, start, end, threshold)
    return AnomalyResponse(
        metric=result["metric"],
        anomalies=[
            {
                "date": a.get("date", ""),
                "value": a["value"],
                "z_score": a["z_score"],
                "direction": a["direction"],
            }
            for a in result["anomalies"]
        ],
    )


@app.post("/analyze/patterns/weekly-clusters", response_model=WeeklyClusterResponse)
async def analyze_weekly_clusters(
    features_list: list[str] = Query(..., alias="features", description="Features for clustering"),
    n_clusters: int = Query(4, description="Number of clusters"),
    start: date | None = Query(None, description="Start date (optional)"),
    end: date | None = Query(None, description="End date (optional)"),
):
    """Cluster weeks based on feature patterns."""
    result = await patterns.get_weekly_clusters(features_list, n_clusters, start, end)
    return WeeklyClusterResponse(
        weeks=[
            {
                "year": w["year"],
                "week": w["week"],
                "cluster": w["cluster"],
                "label": w.get("label"),
            }
            for w in result["weeks"]
        ],
        cluster_profiles=result["cluster_profiles"],
    )
