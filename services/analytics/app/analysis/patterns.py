"""Pattern detection module: change points, anomalies, weekly clusters."""

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
import ruptures as rpt
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from app.db import get_db


async def load_metric_series(
    metric: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.Series:
    """Load a single metric as a time series.

    Args:
        metric: Metric name
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        Series with metric values indexed by date
    """
    async with get_db() as conn:
        async with conn.cursor() as cur:
            query = f"""
                SELECT date, {metric}
                FROM oura_daily
                WHERE {metric} IS NOT NULL
            """
            params: dict[str, Any] = {}

            if start_date:
                query += " AND date >= %(start)s"
                params["start"] = start_date
            if end_date:
                query += " AND date <= %(end)s"
                params["end"] = end_date

            query += " ORDER BY date ASC"

            await cur.execute(query, params)
            rows = await cur.fetchall()

    if not rows:
        return pd.Series(dtype=float)

    df = pd.DataFrame([dict(r) for r in rows])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")[metric]


def detect_change_points(
    series: np.ndarray,
    penalty: float = 10.0,
) -> list[dict[str, Any]]:
    """Detect change points using PELT algorithm.

    Args:
        series: Time series values
        penalty: Penalty parameter for PELT

    Returns:
        List of change point dicts with before/after means
    """
    if len(series) < 10:
        return []

    # Handle NaN by interpolation
    series_clean = pd.Series(series).interpolate().fillna(method="bfill").fillna(method="ffill").values

    try:
        # PELT algorithm with rbf model
        algo = rpt.Pelt(model="rbf", min_size=5).fit(series_clean)
        change_indices = algo.predict(pen=penalty)
    except Exception:
        return []

    # Remove the last index (always included by ruptures)
    change_indices = [i for i in change_indices if i < len(series)]

    results = []
    prev_idx = 0

    for idx in change_indices:
        if idx == len(series):
            continue

        before_mean = float(np.nanmean(series_clean[prev_idx:idx]))
        after_mean = float(np.nanmean(series_clean[idx:]))
        magnitude = abs(after_mean - before_mean)
        direction = "increase" if after_mean > before_mean else "decrease"

        results.append({
            "index": idx,
            "before_mean": before_mean,
            "after_mean": after_mean,
            "magnitude": magnitude,
            "direction": direction,
        })

        prev_idx = idx

    return results


def detect_anomalies(
    series: np.ndarray,
    threshold: float = 3.0,
    use_mad: bool = True,
) -> list[dict[str, Any]]:
    """Detect anomalies using robust z-score.

    Args:
        series: Time series values
        threshold: Z-score threshold for anomaly detection
        use_mad: Use Median Absolute Deviation for robustness

    Returns:
        List of anomaly dicts
    """
    if len(series) < 10:
        return []

    series = np.array(series, dtype=float)
    valid_mask = ~np.isnan(series)

    if valid_mask.sum() < 10:
        return []

    valid_series = series[valid_mask]

    if use_mad:
        # Median Absolute Deviation (robust to outliers)
        median = np.median(valid_series)
        mad = np.median(np.abs(valid_series - median))
        # Avoid division by zero
        if mad < 1e-10:
            mad = np.std(valid_series)
        # Modified z-score using MAD
        z_scores = 0.6745 * (series - median) / (mad + 1e-10)
    else:
        # Standard z-score
        mean = np.mean(valid_series)
        std = np.std(valid_series)
        if std < 1e-10:
            return []
        z_scores = (series - mean) / std

    # Find anomalies
    anomaly_mask = np.abs(z_scores) > threshold
    anomaly_indices = np.where(anomaly_mask & valid_mask)[0]

    results = []
    for idx in anomaly_indices:
        results.append({
            "index": int(idx),
            "value": float(series[idx]),
            "z_score": float(z_scores[idx]),
            "direction": "high" if z_scores[idx] > 0 else "low",
        })

    return results


async def load_weekly_data(
    features: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    """Load and aggregate data to weekly level.

    Args:
        features: List of features to include
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        DataFrame with weekly aggregated data
    """
    # Build safe column list
    safe_features = [f for f in features if f.isidentifier()]
    if not safe_features:
        return pd.DataFrame()

    feature_cols = ", ".join(safe_features)

    async with get_db() as conn:
        async with conn.cursor() as cur:
            query = f"""
                SELECT date, {feature_cols}
                FROM oura_daily
                WHERE 1=1
            """
            params: dict[str, Any] = {}

            if start_date:
                query += " AND date >= %(start)s"
                params["start"] = start_date
            if end_date:
                query += " AND date <= %(end)s"
                params["end"] = end_date

            query += " ORDER BY date ASC"

            await cur.execute(query, params)
            rows = await cur.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])
    df["date"] = pd.to_datetime(df["date"])

    # Add week info
    df["year"] = df["date"].dt.isocalendar().year
    df["week"] = df["date"].dt.isocalendar().week

    # Aggregate to weekly
    weekly = df.groupby(["year", "week"])[safe_features].mean().reset_index()

    return weekly


def cluster_weeks(
    weekly_df: pd.DataFrame,
    features: list[str],
    n_clusters: int = 4,
) -> dict[str, Any]:
    """Cluster weeks based on features.

    Args:
        weekly_df: DataFrame with weekly aggregated data
        features: Features to use for clustering
        n_clusters: Number of clusters

    Returns:
        Clustering result with week labels and cluster profiles
    """
    if weekly_df.empty or len(weekly_df) < n_clusters:
        return {"weeks": [], "cluster_profiles": {}}

    # Filter to available features
    available_features = [f for f in features if f in weekly_df.columns]
    if not available_features:
        return {"weeks": [], "cluster_profiles": {}}

    # Drop weeks with missing values
    clean_df = weekly_df.dropna(subset=available_features)
    if len(clean_df) < n_clusters:
        return {"weeks": [], "cluster_profiles": {}}

    # Scale features
    scaler = StandardScaler()
    X = scaler.fit_transform(clean_df[available_features])

    # Cluster
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    # Add labels
    clean_df = clean_df.copy()
    clean_df["cluster"] = labels

    # Create week labels
    weeks = []
    for _, row in clean_df.iterrows():
        weeks.append({
            "year": int(row["year"]),
            "week": int(row["week"]),
            "cluster": int(row["cluster"]),
            "label": None,  # Could add cluster labels later
        })

    # Compute cluster profiles (mean of each feature per cluster)
    cluster_profiles = {}
    for cluster_id in range(n_clusters):
        cluster_data = clean_df[clean_df["cluster"] == cluster_id][available_features]
        profile = cluster_data.mean().to_dict()
        cluster_profiles[str(cluster_id)] = {k: float(v) for k, v in profile.items()}

    return {"weeks": weeks, "cluster_profiles": cluster_profiles}


async def get_change_points(
    metric: str,
    start_date: date | None = None,
    end_date: date | None = None,
    penalty: float = 10.0,
) -> dict[str, Any]:
    """Get change points for a metric.

    Args:
        metric: Metric name
        start_date: Optional start date
        end_date: Optional end date
        penalty: PELT penalty parameter

    Returns:
        Dict with metric and change points
    """
    series = await load_metric_series(metric, start_date, end_date)
    if series.empty:
        return {"metric": metric, "change_points": []}

    change_points = detect_change_points(series.values, penalty)

    # Add dates to change points
    dates = series.index.tolist()
    for cp in change_points:
        if cp["index"] < len(dates):
            cp["date"] = dates[cp["index"]].strftime("%Y-%m-%d")

    return {"metric": metric, "change_points": change_points}


async def get_anomalies(
    metric: str,
    start_date: date | None = None,
    end_date: date | None = None,
    threshold: float = 3.0,
) -> dict[str, Any]:
    """Get anomalies for a metric.

    Args:
        metric: Metric name
        start_date: Optional start date
        end_date: Optional end date
        threshold: Z-score threshold

    Returns:
        Dict with metric and anomalies
    """
    series = await load_metric_series(metric, start_date, end_date)
    if series.empty:
        return {"metric": metric, "anomalies": []}

    anomalies = detect_anomalies(series.values, threshold)

    # Add dates to anomalies
    dates = series.index.tolist()
    for anomaly in anomalies:
        if anomaly["index"] < len(dates):
            anomaly["date"] = dates[anomaly["index"]].strftime("%Y-%m-%d")

    return {"metric": metric, "anomalies": anomalies}


async def get_weekly_clusters(
    features: list[str],
    n_clusters: int = 4,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Get weekly clustering results.

    Args:
        features: Features to use for clustering
        n_clusters: Number of clusters
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        Clustering result
    """
    weekly_df = await load_weekly_data(features, start_date, end_date)
    if weekly_df.empty:
        return {"weeks": [], "cluster_profiles": {}}

    return cluster_weeks(weekly_df, features, n_clusters)
