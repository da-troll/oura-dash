"""Ingestion pipeline: Oura API → raw → daily tables."""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.db import get_db
from app.oura.client import oura_client


def resolve_sleep_day(sleep_session: dict[str, Any]) -> date | None:
    """Map a sleep session to the date of waking up.

    This is the canonical mapping rule: sleep sessions are attributed
    to the day on which the person woke up, not when they went to bed.

    Args:
        sleep_session: Sleep session data from Oura API

    Returns:
        The date of waking (bedtime_end), or None if not available
    """
    bedtime_end = sleep_session.get("bedtime_end")
    if not bedtime_end:
        # Fallback to day field if available
        day_str = sleep_session.get("day")
        if day_str:
            return date.fromisoformat(day_str)
        return None

    # Parse the ISO datetime and extract the date
    if isinstance(bedtime_end, str):
        # Remove timezone info if present and parse
        try:
            dt = datetime.fromisoformat(bedtime_end.replace("Z", "+00:00"))
            return dt.date()
        except ValueError:
            return None

    return None


async def ingest_raw_data(
    start_date: date,
    end_date: date,
    data_types: list[str] | None = None,
) -> dict[str, int]:
    """Fetch raw data from Oura API and store in oura_raw table.

    Args:
        start_date: Start of date range
        end_date: End of date range
        data_types: Optional list of data types to fetch. Defaults to all.

    Returns:
        Dict with counts of records fetched per data type
    """
    if data_types is None:
        data_types = [
            "daily_sleep",
            "sleep",
            "daily_readiness",
            "daily_activity",
            "tag",
            "workout",
            "session",
        ]

    counts: dict[str, int] = {}

    fetch_map = {
        "daily_sleep": oura_client.fetch_daily_sleep,
        "sleep": oura_client.fetch_sleep_sessions,
        "daily_readiness": oura_client.fetch_daily_readiness,
        "daily_activity": oura_client.fetch_daily_activity,
        "tag": oura_client.fetch_tags,
        "workout": oura_client.fetch_workouts,
        "session": oura_client.fetch_sessions,
    }

    async with get_db() as conn:
        for data_type in data_types:
            if data_type not in fetch_map:
                continue

            fetch_fn = fetch_map[data_type]
            records = await fetch_fn(start_date, end_date)
            counts[data_type] = len(records)

            for record in records:
                # Determine the day for this record
                day = record.get("day")
                if data_type == "sleep":
                    # For sleep sessions, use the wake-up date
                    resolved_day = resolve_sleep_day(record)
                    day = str(resolved_day) if resolved_day else day

                await conn.execute(
                    """
                    INSERT INTO oura_raw (source, day, payload, fetched_at)
                    VALUES (%(source)s, %(day)s, %(payload)s, %(fetched_at)s)
                    """,
                    {
                        "source": data_type,
                        "day": day,
                        "payload": json.dumps(record),
                        "fetched_at": datetime.now(timezone.utc),
                    },
                )

        await conn.commit()

    return counts


async def normalize_daily_data(start_date: date, end_date: date) -> int:
    """Normalize raw data into oura_daily table.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Number of days processed
    """
    days_processed = 0
    current = start_date

    async with get_db() as conn:
        while current <= end_date:
            # Fetch raw data for this day
            async with conn.cursor() as cur:
                # Get daily_sleep data (for score)
                await cur.execute(
                    """
                    SELECT payload FROM oura_raw
                    WHERE source = 'daily_sleep' AND day = %(day)s
                    ORDER BY fetched_at DESC LIMIT 1
                    """,
                    {"day": str(current)},
                )
                sleep_row = await cur.fetchone()
                daily_sleep_data = sleep_row["payload"] if sleep_row else {}

                # Get sleep session data (for actual durations and HRV)
                await cur.execute(
                    """
                    SELECT payload FROM oura_raw
                    WHERE source = 'sleep' AND day = %(day)s
                    ORDER BY fetched_at DESC LIMIT 1
                    """,
                    {"day": str(current)},
                )
                sleep_session_row = await cur.fetchone()
                sleep_session_data = sleep_session_row["payload"] if sleep_session_row else {}

                # Get daily_readiness data
                await cur.execute(
                    """
                    SELECT payload FROM oura_raw
                    WHERE source = 'daily_readiness' AND day = %(day)s
                    ORDER BY fetched_at DESC LIMIT 1
                    """,
                    {"day": str(current)},
                )
                readiness_row = await cur.fetchone()
                readiness_data = readiness_row["payload"] if readiness_row else {}

                # Get daily_activity data
                await cur.execute(
                    """
                    SELECT payload FROM oura_raw
                    WHERE source = 'daily_activity' AND day = %(day)s
                    ORDER BY fetched_at DESC LIMIT 1
                    """,
                    {"day": str(current)},
                )
                activity_row = await cur.fetchone()
                activity_data = activity_row["payload"] if activity_row else {}

            # Extract metrics
            weekday = current.weekday()  # 0=Monday, 6=Sunday
            is_weekend = weekday >= 5

            # Determine season (Northern Hemisphere)
            month = current.month
            if month in (3, 4, 5):
                season = "spring"
            elif month in (6, 7, 8):
                season = "summer"
            elif month in (9, 10, 11):
                season = "fall"
            else:
                season = "winter"

            # Sleep metrics from sleep session (actual durations in seconds)
            sleep_total = sleep_session_data.get("total_sleep_duration")
            sleep_efficiency = sleep_session_data.get("efficiency")
            sleep_rem = sleep_session_data.get("rem_sleep_duration")
            sleep_deep = sleep_session_data.get("deep_sleep_duration")
            sleep_latency = sleep_session_data.get("latency")
            sleep_restfulness = sleep_session_data.get("restless_periods")
            sleep_score = daily_sleep_data.get("score")

            # HRV from sleep session
            hrv_average = sleep_session_data.get("average_hrv")
            hr_lowest = sleep_session_data.get("lowest_heart_rate")
            hr_average = sleep_session_data.get("average_heart_rate")

            # Readiness metrics
            readiness_score = readiness_data.get("score")
            readiness_contributors = readiness_data.get("contributors", {})
            readiness_temp = readiness_contributors.get("body_temperature")
            readiness_rhr = readiness_contributors.get("resting_heart_rate")
            readiness_hrv = readiness_contributors.get("hrv_balance")
            readiness_recovery = readiness_contributors.get("recovery_index")
            readiness_activity = readiness_contributors.get("activity_balance")

            # Activity metrics
            activity_score = activity_data.get("score")
            steps = activity_data.get("steps")
            cal_total = activity_data.get("total_calories")
            cal_active = activity_data.get("active_calories")
            met_minutes = activity_data.get("met", {}).get("minutes") if isinstance(activity_data.get("met"), dict) else activity_data.get("equivalent_walking_distance")
            low_activity = activity_data.get("low_activity_met_minutes")
            medium_activity = activity_data.get("medium_activity_met_minutes")
            high_activity = activity_data.get("high_activity_met_minutes")
            sedentary = activity_data.get("sedentary_met_minutes")

            # Only insert if we have some data
            if daily_sleep_data or sleep_session_data or readiness_data or activity_data:
                await conn.execute(
                    """
                    INSERT INTO oura_daily (
                        date, weekday, is_weekend, season, is_holiday,
                        sleep_total_seconds, sleep_efficiency, sleep_rem_seconds,
                        sleep_deep_seconds, sleep_latency_seconds, sleep_restlessness, sleep_score,
                        readiness_score, readiness_temperature_deviation, readiness_resting_heart_rate,
                        readiness_hrv_balance, readiness_recovery_index, readiness_activity_balance,
                        activity_score, steps, cal_total, cal_active, met_minutes,
                        low_activity_minutes, medium_activity_minutes, high_activity_minutes, sedentary_minutes,
                        hr_lowest, hr_average, hrv_average
                    )
                    VALUES (
                        %(date)s, %(weekday)s, %(is_weekend)s, %(season)s, %(is_holiday)s,
                        %(sleep_total_seconds)s, %(sleep_efficiency)s, %(sleep_rem_seconds)s,
                        %(sleep_deep_seconds)s, %(sleep_latency_seconds)s, %(sleep_restlessness)s, %(sleep_score)s,
                        %(readiness_score)s, %(readiness_temperature_deviation)s, %(readiness_resting_heart_rate)s,
                        %(readiness_hrv_balance)s, %(readiness_recovery_index)s, %(readiness_activity_balance)s,
                        %(activity_score)s, %(steps)s, %(cal_total)s, %(cal_active)s, %(met_minutes)s,
                        %(low_activity_minutes)s, %(medium_activity_minutes)s, %(high_activity_minutes)s, %(sedentary_minutes)s,
                        %(hr_lowest)s, %(hr_average)s, %(hrv_average)s
                    )
                    ON CONFLICT (date) DO UPDATE SET
                        weekday = EXCLUDED.weekday,
                        is_weekend = EXCLUDED.is_weekend,
                        season = EXCLUDED.season,
                        sleep_total_seconds = COALESCE(EXCLUDED.sleep_total_seconds, oura_daily.sleep_total_seconds),
                        sleep_efficiency = COALESCE(EXCLUDED.sleep_efficiency, oura_daily.sleep_efficiency),
                        sleep_rem_seconds = COALESCE(EXCLUDED.sleep_rem_seconds, oura_daily.sleep_rem_seconds),
                        sleep_deep_seconds = COALESCE(EXCLUDED.sleep_deep_seconds, oura_daily.sleep_deep_seconds),
                        sleep_latency_seconds = COALESCE(EXCLUDED.sleep_latency_seconds, oura_daily.sleep_latency_seconds),
                        sleep_restlessness = COALESCE(EXCLUDED.sleep_restlessness, oura_daily.sleep_restlessness),
                        sleep_score = COALESCE(EXCLUDED.sleep_score, oura_daily.sleep_score),
                        readiness_score = COALESCE(EXCLUDED.readiness_score, oura_daily.readiness_score),
                        readiness_temperature_deviation = COALESCE(EXCLUDED.readiness_temperature_deviation, oura_daily.readiness_temperature_deviation),
                        readiness_resting_heart_rate = COALESCE(EXCLUDED.readiness_resting_heart_rate, oura_daily.readiness_resting_heart_rate),
                        readiness_hrv_balance = COALESCE(EXCLUDED.readiness_hrv_balance, oura_daily.readiness_hrv_balance),
                        readiness_recovery_index = COALESCE(EXCLUDED.readiness_recovery_index, oura_daily.readiness_recovery_index),
                        readiness_activity_balance = COALESCE(EXCLUDED.readiness_activity_balance, oura_daily.readiness_activity_balance),
                        activity_score = COALESCE(EXCLUDED.activity_score, oura_daily.activity_score),
                        steps = COALESCE(EXCLUDED.steps, oura_daily.steps),
                        cal_total = COALESCE(EXCLUDED.cal_total, oura_daily.cal_total),
                        cal_active = COALESCE(EXCLUDED.cal_active, oura_daily.cal_active),
                        met_minutes = COALESCE(EXCLUDED.met_minutes, oura_daily.met_minutes),
                        low_activity_minutes = COALESCE(EXCLUDED.low_activity_minutes, oura_daily.low_activity_minutes),
                        medium_activity_minutes = COALESCE(EXCLUDED.medium_activity_minutes, oura_daily.medium_activity_minutes),
                        high_activity_minutes = COALESCE(EXCLUDED.high_activity_minutes, oura_daily.high_activity_minutes),
                        sedentary_minutes = COALESCE(EXCLUDED.sedentary_minutes, oura_daily.sedentary_minutes),
                        hr_lowest = COALESCE(EXCLUDED.hr_lowest, oura_daily.hr_lowest),
                        hr_average = COALESCE(EXCLUDED.hr_average, oura_daily.hr_average),
                        hrv_average = COALESCE(EXCLUDED.hrv_average, oura_daily.hrv_average),
                        updated_at = NOW()
                    """,
                    {
                        "date": current,
                        "weekday": weekday,
                        "is_weekend": is_weekend,
                        "season": season,
                        "is_holiday": False,
                        "sleep_total_seconds": sleep_total,
                        "sleep_efficiency": sleep_efficiency,
                        "sleep_rem_seconds": sleep_rem,
                        "sleep_deep_seconds": sleep_deep,
                        "sleep_latency_seconds": sleep_latency,
                        "sleep_restlessness": sleep_restfulness,
                        "sleep_score": sleep_score,
                        "readiness_score": readiness_score,
                        "readiness_temperature_deviation": readiness_temp,
                        "readiness_resting_heart_rate": readiness_rhr,
                        "readiness_hrv_balance": readiness_hrv,
                        "readiness_recovery_index": readiness_recovery,
                        "readiness_activity_balance": readiness_activity,
                        "activity_score": activity_score,
                        "steps": steps,
                        "cal_total": cal_total,
                        "cal_active": cal_active,
                        "met_minutes": met_minutes,
                        "low_activity_minutes": low_activity,
                        "medium_activity_minutes": medium_activity,
                        "high_activity_minutes": high_activity,
                        "sedentary_minutes": sedentary,
                        "hr_lowest": hr_lowest,
                        "hr_average": hr_average,
                        "hrv_average": hrv_average,
                    },
                )
                days_processed += 1

            current += timedelta(days=1)

        await conn.commit()

    return days_processed


async def ingest_tags(start_date: date, end_date: date) -> int:
    """Normalize tags from raw data into oura_day_tags table.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Number of tags processed
    """
    tags_processed = 0

    async with get_db() as conn:
        async with conn.cursor() as cur:
            # Get all tag records in the date range
            await cur.execute(
                """
                SELECT day, payload FROM oura_raw
                WHERE source = 'tag' AND day >= %(start)s AND day <= %(end)s
                """,
                {"start": str(start_date), "end": str(end_date)},
            )
            tag_rows = await cur.fetchall()

        for row in tag_rows:
            day = row["day"]
            payload = row["payload"]

            if not day:
                continue

            # Parse tag text from payload
            tag_text = payload.get("tag_type_code") or payload.get("text")
            if not tag_text:
                continue

            # Ensure the day exists in oura_daily first
            await conn.execute(
                """
                INSERT INTO oura_daily (date, weekday, is_weekend, season, is_holiday)
                VALUES (
                    %(date)s,
                    EXTRACT(DOW FROM %(date)s::date)::int,
                    EXTRACT(DOW FROM %(date)s::date) IN (0, 6),
                    CASE
                        WHEN EXTRACT(MONTH FROM %(date)s::date) IN (3,4,5) THEN 'spring'
                        WHEN EXTRACT(MONTH FROM %(date)s::date) IN (6,7,8) THEN 'summer'
                        WHEN EXTRACT(MONTH FROM %(date)s::date) IN (9,10,11) THEN 'fall'
                        ELSE 'winter'
                    END,
                    FALSE
                )
                ON CONFLICT (date) DO NOTHING
                """,
                {"date": day},
            )

            # Insert tag
            await conn.execute(
                """
                INSERT INTO oura_day_tags (date, tag)
                VALUES (%(date)s, %(tag)s)
                ON CONFLICT (date, tag) DO NOTHING
                """,
                {"date": day, "tag": tag_text},
            )
            tags_processed += 1

        await conn.commit()

    return tags_processed


async def run_full_ingest(start_date: date, end_date: date) -> dict[str, Any]:
    """Run the full ingestion pipeline.

    1. Fetch raw data from Oura API
    2. Normalize into oura_daily
    3. Process tags

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Summary of ingestion results
    """
    # Step 1: Ingest raw data
    raw_counts = await ingest_raw_data(start_date, end_date)

    # Step 2: Normalize to daily
    days_processed = await normalize_daily_data(start_date, end_date)

    # Step 3: Process tags
    tags_processed = await ingest_tags(start_date, end_date)

    return {
        "status": "completed",
        "raw_counts": raw_counts,
        "days_processed": days_processed,
        "tags_processed": tags_processed,
    }
