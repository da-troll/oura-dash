"""Correlation analysis module."""

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from app.db import get_db


async def load_analysis_data(
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    """Load daily and feature data for analysis.

    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        DataFrame with merged daily and feature data
    """
    async with get_db() as conn:
        async with conn.cursor() as cur:
            query = """
                SELECT d.*, f.*
                FROM oura_daily d
                LEFT JOIN oura_features_daily f ON d.date = f.date
                WHERE 1=1
            """
            params: dict[str, Any] = {}

            if start_date:
                query += " AND d.date >= %(start)s"
                params["start"] = start_date
            if end_date:
                query += " AND d.date <= %(end)s"
                params["end"] = end_date

            query += " ORDER BY d.date ASC"

            await cur.execute(query, params)
            rows = await cur.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])
    # Handle duplicate 'date' columns from the join
    if "date" in df.columns:
        df = df.loc[:, ~df.columns.duplicated()]
    return df


def compute_spearman_correlations(
    df: pd.DataFrame,
    target: str,
    candidates: list[str],
) -> list[dict[str, Any]]:
    """Compute Spearman correlations between target and candidate metrics.

    Args:
        df: DataFrame with metric data
        target: Target metric name
        candidates: List of candidate metric names

    Returns:
        List of correlation results sorted by |rho| descending
    """
    if target not in df.columns:
        return []

    results = []
    target_series = df[target].dropna()

    for candidate in candidates:
        if candidate not in df.columns or candidate == target:
            continue

        candidate_series = df[candidate].dropna()

        # Align series
        common_idx = target_series.index.intersection(candidate_series.index)
        if len(common_idx) < 10:
            continue

        x = target_series.loc[common_idx]
        y = candidate_series.loc[common_idx]

        # Compute Spearman correlation
        rho, p_value = stats.spearmanr(x, y)

        if not np.isnan(rho):
            results.append({
                "metric": candidate,
                "rho": float(rho),
                "p_value": float(p_value),
                "n": len(common_idx),
            })

    # Sort by absolute rho descending
    results.sort(key=lambda r: abs(r["rho"]), reverse=True)
    return results


def compute_lagged_correlations(
    df: pd.DataFrame,
    metric_x: str,
    metric_y: str,
    max_lag: int = 7,
) -> dict[str, Any]:
    """Compute correlations at various lags to find if X predicts Y.

    Args:
        df: DataFrame with metric data
        metric_x: Predictor metric
        metric_y: Target metric
        max_lag: Maximum lag to test

    Returns:
        Dict with lag correlations and best lag
    """
    if metric_x not in df.columns or metric_y not in df.columns:
        return {"metric_x": metric_x, "metric_y": metric_y, "lags": [], "best_lag": 0}

    results = []
    best_rho = 0
    best_lag = 0

    x = df[metric_x].dropna()
    y = df[metric_y].dropna()

    for lag in range(max_lag + 1):
        if lag == 0:
            x_lagged = x
            y_aligned = y
        else:
            # X at time t predicts Y at time t+lag
            x_lagged = x.iloc[:-lag] if lag > 0 else x
            y_aligned = y.iloc[lag:] if lag > 0 else y

        # Align indices
        common_idx = x_lagged.index.intersection(y_aligned.index)
        if len(common_idx) < 10:
            continue

        x_vals = x_lagged.loc[common_idx]
        y_vals = y_aligned.loc[common_idx]

        rho, p_value = stats.spearmanr(x_vals, y_vals)

        if not np.isnan(rho):
            results.append({
                "lag": lag,
                "rho": float(rho),
                "p_value": float(p_value),
                "n": len(common_idx),
            })

            if abs(rho) > abs(best_rho):
                best_rho = rho
                best_lag = lag

    return {
        "metric_x": metric_x,
        "metric_y": metric_y,
        "lags": results,
        "best_lag": best_lag,
    }


def compute_controlled_correlation(
    df: pd.DataFrame,
    metric_x: str,
    metric_y: str,
    control_vars: list[str],
) -> dict[str, Any]:
    """Compute partial correlation controlling for confounders.

    Uses regression residuals method for partial correlation.

    Args:
        df: DataFrame with metric data
        metric_x: First metric
        metric_y: Second metric
        control_vars: Variables to control for

    Returns:
        Controlled correlation result
    """
    required_cols = [metric_x, metric_y] + control_vars
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return {
            "metric_x": metric_x,
            "metric_y": metric_y,
            "rho": 0,
            "p_value": 1,
            "n": 0,
            "controlled_for": control_vars,
        }

    # Drop rows with any NaN in required columns
    clean_df = df[required_cols].dropna()

    if len(clean_df) < 10:
        return {
            "metric_x": metric_x,
            "metric_y": metric_y,
            "rho": 0,
            "p_value": 1,
            "n": len(clean_df),
            "controlled_for": control_vars,
        }

    # Partial correlation via regression residuals
    from sklearn.linear_model import LinearRegression

    X_controls = clean_df[control_vars].values
    x = clean_df[metric_x].values
    y = clean_df[metric_y].values

    # Regress X on controls
    reg_x = LinearRegression().fit(X_controls, x)
    residuals_x = x - reg_x.predict(X_controls)

    # Regress Y on controls
    reg_y = LinearRegression().fit(X_controls, y)
    residuals_y = y - reg_y.predict(X_controls)

    # Correlate residuals
    rho, p_value = stats.spearmanr(residuals_x, residuals_y)

    return {
        "metric_x": metric_x,
        "metric_y": metric_y,
        "rho": float(rho) if not np.isnan(rho) else 0,
        "p_value": float(p_value) if not np.isnan(p_value) else 1,
        "n": len(clean_df),
        "controlled_for": control_vars,
    }


async def get_spearman_correlations(
    target: str,
    candidates: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Get Spearman correlations for a target metric.

    Args:
        target: Target metric name
        candidates: List of candidate metrics
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        Dict with target and correlation results
    """
    df = await load_analysis_data(start_date, end_date)
    if df.empty:
        return {"target": target, "correlations": []}

    correlations = compute_spearman_correlations(df, target, candidates)
    return {"target": target, "correlations": correlations}


async def get_lagged_correlations(
    metric_x: str,
    metric_y: str,
    max_lag: int = 7,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Get lagged correlations between two metrics.

    Args:
        metric_x: Predictor metric
        metric_y: Target metric
        max_lag: Maximum lag to test
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        Dict with lag correlation results
    """
    df = await load_analysis_data(start_date, end_date)
    if df.empty:
        return {"metric_x": metric_x, "metric_y": metric_y, "lags": [], "best_lag": 0}

    return compute_lagged_correlations(df, metric_x, metric_y, max_lag)


async def get_controlled_correlation(
    metric_x: str,
    metric_y: str,
    control_vars: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Get controlled (partial) correlation between two metrics.

    Args:
        metric_x: First metric
        metric_y: Second metric
        control_vars: Variables to control for
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        Controlled correlation result
    """
    df = await load_analysis_data(start_date, end_date)
    if df.empty:
        return {
            "metric_x": metric_x,
            "metric_y": metric_y,
            "rho": 0,
            "p_value": 1,
            "n": 0,
            "controlled_for": control_vars,
        }

    return compute_controlled_correlation(df, metric_x, metric_y, control_vars)
