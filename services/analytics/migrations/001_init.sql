-- Oura Analytics Database Schema
-- Version: 001_init

-- ============================================
-- Raw Oura API Payloads (for debugging + backfills)
-- ============================================

CREATE TABLE IF NOT EXISTS oura_raw (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,                    -- "sleep", "readiness", "activity", "tags", etc.
    day DATE NULL,                           -- The day this data belongs to (if applicable)
    payload JSONB NOT NULL,                  -- Raw API response
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oura_raw_source_day ON oura_raw(source, day);
CREATE INDEX IF NOT EXISTS idx_oura_raw_fetched_at ON oura_raw(fetched_at);

-- ============================================
-- Single-user OAuth Token Store (id=1 always)
-- ============================================

CREATE TABLE IF NOT EXISTS oura_auth (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    token_type TEXT NOT NULL,
    scope TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- Canonical Daily-Grain Table
-- One row per date, local timezone
-- ============================================

CREATE TABLE IF NOT EXISTS oura_daily (
    date DATE PRIMARY KEY,

    -- Calendar context
    weekday SMALLINT NOT NULL,               -- 0=Monday, 6=Sunday
    is_weekend BOOLEAN NOT NULL,
    season TEXT NULL,                        -- spring, summer, fall, winter
    is_holiday BOOLEAN NOT NULL DEFAULT FALSE,
    holiday_name TEXT NULL,

    -- Sleep metrics
    sleep_total_seconds INT NULL,
    sleep_efficiency NUMERIC NULL,
    sleep_rem_seconds INT NULL,
    sleep_deep_seconds INT NULL,
    sleep_light_seconds INT NULL,
    sleep_latency_seconds INT NULL,
    sleep_restlessness NUMERIC NULL,
    sleep_bedtime_start TIMESTAMPTZ NULL,
    sleep_bedtime_end TIMESTAMPTZ NULL,
    sleep_regularity NUMERIC NULL,
    sleep_score INT NULL,

    -- Readiness metrics
    readiness_score INT NULL,
    readiness_temperature_deviation NUMERIC NULL,
    readiness_resting_heart_rate INT NULL,
    readiness_hrv_balance INT NULL,
    readiness_recovery_index INT NULL,
    readiness_activity_balance INT NULL,

    -- Activity metrics
    activity_score INT NULL,
    steps INT NULL,
    cal_total INT NULL,
    cal_active INT NULL,
    met_minutes INT NULL,
    training_load NUMERIC NULL,
    low_activity_minutes INT NULL,
    medium_activity_minutes INT NULL,
    high_activity_minutes INT NULL,
    sedentary_minutes INT NULL,

    -- Heart rate (daily aggregates)
    hr_lowest INT NULL,
    hr_average NUMERIC NULL,
    hrv_average NUMERIC NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oura_daily_weekday ON oura_daily(weekday);
CREATE INDEX IF NOT EXISTS idx_oura_daily_is_weekend ON oura_daily(is_weekend);

-- ============================================
-- Tags per Day (normalized)
-- ============================================

CREATE TABLE IF NOT EXISTS oura_day_tags (
    date DATE NOT NULL REFERENCES oura_daily(date) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (date, tag)
);

CREATE INDEX IF NOT EXISTS idx_oura_day_tags_tag ON oura_day_tags(tag);

-- ============================================
-- Derived Features Table (ML-ready)
-- ============================================

CREATE TABLE IF NOT EXISTS oura_features_daily (
    date DATE PRIMARY KEY REFERENCES oura_daily(date) ON DELETE CASCADE,

    -- Rolling means for readiness
    rm_3_readiness_score NUMERIC NULL,
    rm_7_readiness_score NUMERIC NULL,
    rm_14_readiness_score NUMERIC NULL,
    rm_28_readiness_score NUMERIC NULL,

    -- Rolling means for sleep
    rm_3_sleep_total_seconds NUMERIC NULL,
    rm_7_sleep_total_seconds NUMERIC NULL,
    rm_14_sleep_total_seconds NUMERIC NULL,
    rm_28_sleep_total_seconds NUMERIC NULL,

    -- Rolling means for activity
    rm_7_steps NUMERIC NULL,
    rm_14_steps NUMERIC NULL,
    rm_28_steps NUMERIC NULL,

    -- Deltas vs baseline
    delta_readiness_vs_rm7 NUMERIC NULL,
    delta_sleep_vs_rm7 NUMERIC NULL,
    delta_steps_vs_rm7 NUMERIC NULL,

    -- Lag features for sleep
    lag_1_sleep_total_seconds INT NULL,
    lag_2_sleep_total_seconds INT NULL,
    lag_3_sleep_total_seconds INT NULL,
    lag_4_sleep_total_seconds INT NULL,
    lag_5_sleep_total_seconds INT NULL,
    lag_6_sleep_total_seconds INT NULL,
    lag_7_sleep_total_seconds INT NULL,

    -- Lag features for readiness
    lag_1_readiness_score INT NULL,
    lag_2_readiness_score INT NULL,
    lag_3_readiness_score INT NULL,

    -- Rolling standard deviation (variability)
    sd_7_sleep_total_seconds NUMERIC NULL,
    sd_14_sleep_total_seconds NUMERIC NULL,
    sd_7_readiness_score NUMERIC NULL,
    sd_7_steps NUMERIC NULL,

    -- Trend indicators (slope of linear fit)
    trend_7_readiness_score NUMERIC NULL,
    trend_7_sleep_total_seconds NUMERIC NULL,

    -- Timestamps
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- Trigger to update updated_at on oura_daily
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_oura_daily_updated_at ON oura_daily;
CREATE TRIGGER update_oura_daily_updated_at
    BEFORE UPDATE ON oura_daily
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_oura_features_daily_updated_at ON oura_features_daily;
CREATE TRIGGER update_oura_features_daily_updated_at
    BEFORE UPDATE ON oura_features_daily
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_oura_auth_updated_at ON oura_auth;
CREATE TRIGGER update_oura_auth_updated_at
    BEFORE UPDATE ON oura_auth
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
