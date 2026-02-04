"""Pydantic schemas mirroring the shared Zod schemas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


# ============================================
# Health Check
# ============================================


class HealthResponse(BaseModel):
    """Health check response."""

    ok: bool


# ============================================
# Authentication
# ============================================


class AuthStatusResponse(BaseModel):
    """Authentication status response."""

    connected: bool
    expires_at: datetime | None = None
    scopes: list[str] | None = None


class AuthUrlResponse(BaseModel):
    """OAuth authorization URL response."""

    url: str
    state: str


class ExchangeCodeRequest(BaseModel):
    """Request to exchange OAuth code for tokens."""

    code: str
    state: str | None = None


class ExchangeCodeResponse(BaseModel):
    """Response from token exchange."""

    success: bool
    message: str | None = None


# ============================================
# Time Series
# ============================================


class SeriesMetricRequest(BaseModel):
    """Request for time series data."""

    metric: str
    start: date
    end: date
    filters: dict[str, str] | None = None


class SeriesPoint(BaseModel):
    """Single point in a time series."""

    x: str  # YYYY-MM-DD
    y: float | None


class SeriesMetricResponse(BaseModel):
    """Response with time series data."""

    metric: str
    points: list[SeriesPoint]


# ============================================
# Correlations
# ============================================


class SpearmanCorrelation(BaseModel):
    """Single Spearman correlation result."""

    metric: str
    rho: float
    p_value: float
    n: int


class SpearmanRequest(BaseModel):
    """Request for Spearman correlation analysis."""

    target: str
    candidates: list[str]
    start: date | None = None
    end: date | None = None


class SpearmanResponse(BaseModel):
    """Response with Spearman correlation results."""

    target: str
    correlations: list[SpearmanCorrelation]


class LaggedCorrelationPoint(BaseModel):
    """Correlation at a specific lag."""

    lag: int
    rho: float
    p_value: float
    n: int


class LaggedCorrelationRequest(BaseModel):
    """Request for lagged correlation analysis."""

    metric_x: str
    metric_y: str
    max_lag: int = 7
    start: date | None = None
    end: date | None = None


class LaggedCorrelationResponse(BaseModel):
    """Response with lagged correlation results."""

    metric_x: str
    metric_y: str
    lags: list[LaggedCorrelationPoint]
    best_lag: int


class ControlledCorrelationRequest(BaseModel):
    """Request for partial correlation controlling for variables."""

    metric_x: str
    metric_y: str
    control_vars: list[str]
    start: date | None = None
    end: date | None = None


class ControlledCorrelationResponse(BaseModel):
    """Response with controlled correlation results."""

    metric_x: str
    metric_y: str
    rho: float
    p_value: float
    n: int
    controlled_for: list[str]


# ============================================
# Patterns
# ============================================


class ChangePoint(BaseModel):
    """Detected change point in a time series."""

    date: date
    index: int
    before_mean: float
    after_mean: float
    magnitude: float
    direction: Literal["increase", "decrease"]


class ChangePointRequest(BaseModel):
    """Request for change point detection."""

    metric: str
    start: date | None = None
    end: date | None = None
    penalty: float | None = None


class ChangePointResponse(BaseModel):
    """Response with detected change points."""

    metric: str
    change_points: list[ChangePoint]


class Anomaly(BaseModel):
    """Detected anomaly."""

    date: date
    value: float
    z_score: float
    direction: Literal["high", "low"]


class AnomalyRequest(BaseModel):
    """Request for anomaly detection."""

    metric: str
    start: date | None = None
    end: date | None = None
    threshold: float = 3.0


class AnomalyResponse(BaseModel):
    """Response with detected anomalies."""

    metric: str
    anomalies: list[Anomaly]


class WeeklyCluster(BaseModel):
    """Weekly cluster assignment."""

    year: int
    week: int
    cluster: int
    label: str | None = None


class WeeklyClusterRequest(BaseModel):
    """Request for weekly clustering."""

    features: list[str]
    n_clusters: int = 4
    start: date | None = None
    end: date | None = None


class WeeklyClusterResponse(BaseModel):
    """Response with weekly cluster assignments."""

    weeks: list[WeeklyCluster]
    cluster_profiles: dict[str, dict[str, float]]


# ============================================
# Admin / Sync
# ============================================


class SyncRequest(BaseModel):
    """Request to sync data from Oura."""

    start: date
    end: date


class SyncResponse(BaseModel):
    """Response from sync operation."""

    status: Literal["completed", "failed", "in_progress"]
    days_processed: int | None = None
    message: str | None = None


# ============================================
# Dashboard
# ============================================


class DashboardSummary(BaseModel):
    """Summary metrics for dashboard."""

    readiness_avg: float | None = None
    sleep_score_avg: float | None = None
    activity_avg: float | None = None
    steps_avg: float | None = None
    hrv_avg: float | None = None
    rhr_avg: float | None = None
    sleep_hours_avg: float | None = None
    calories_avg: float | None = None
    days_with_data: int = 0


class TrendPoint(BaseModel):
    """Point in trend data."""

    date: str
    value: float | None
    baseline: float | None = None


class TrendSeries(BaseModel):
    """A named trend series."""

    name: str
    data: list[TrendPoint]


class DashboardResponse(BaseModel):
    """Dashboard data response."""

    connected: bool
    summary: DashboardSummary
    trends: list[TrendSeries] = []


# ============================================
# Error Responses
# ============================================


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    message: str
    details: dict | None = None
