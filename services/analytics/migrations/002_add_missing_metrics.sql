-- Oura Analytics Database Schema
-- Version: 002_add_missing_metrics
-- Adds stress, SpO2, cardiovascular age, sleep extras, activity contributors,
-- readiness extras, workout/session aggregation, personal info, and new features.

-- ============================================
-- New columns on oura_daily
-- ============================================

-- Stress metrics (from /usercollection/daily_stress)
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS stress_high_minutes INT NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS recovery_high_minutes INT NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS stress_day_summary TEXT NULL;

-- SpO2 metrics (from /usercollection/daily_spo2)
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS spo2_average NUMERIC NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS breathing_disturbance_index NUMERIC NULL;

-- Cardiovascular age (from /usercollection/daily_cardiovascular_age)
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS vascular_age INT NULL;

-- Sleep session extras
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS sleep_breath_average NUMERIC NULL;

-- Activity contributors (from daily_activity -> contributors)
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS activity_meet_daily_targets INT NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS activity_move_every_hour INT NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS activity_recovery_time INT NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS activity_training_frequency INT NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS activity_training_volume INT NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS non_wear_seconds INT NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS inactivity_alerts INT NULL;

-- Readiness extras (from daily_readiness -> contributors)
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS readiness_sleep_balance INT NULL;

-- Workout aggregation (from oura_raw workout data)
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS workout_count INT NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS workout_total_minutes NUMERIC NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS workout_total_calories NUMERIC NULL;

-- Session aggregation (from oura_raw session data)
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS session_count INT NULL;
ALTER TABLE oura_daily ADD COLUMN IF NOT EXISTS session_total_minutes NUMERIC NULL;

-- ============================================
-- Personal info table (single-row, like oura_auth)
-- ============================================

CREATE TABLE IF NOT EXISTS oura_personal_info (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    age INT NULL,
    weight NUMERIC NULL,
    height NUMERIC NULL,
    biological_sex TEXT NULL,
    email TEXT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS update_oura_personal_info_updated_at ON oura_personal_info;
CREATE TRIGGER update_oura_personal_info_updated_at
    BEFORE UPDATE ON oura_personal_info
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- New columns on oura_features_daily
-- ============================================

-- HRV rolling features
ALTER TABLE oura_features_daily ADD COLUMN IF NOT EXISTS rm_7_hrv_average NUMERIC NULL;
ALTER TABLE oura_features_daily ADD COLUMN IF NOT EXISTS rm_14_hrv_average NUMERIC NULL;
ALTER TABLE oura_features_daily ADD COLUMN IF NOT EXISTS rm_28_hrv_average NUMERIC NULL;
ALTER TABLE oura_features_daily ADD COLUMN IF NOT EXISTS delta_hrv_vs_rm7 NUMERIC NULL;
ALTER TABLE oura_features_daily ADD COLUMN IF NOT EXISTS sd_7_hrv_average NUMERIC NULL;
ALTER TABLE oura_features_daily ADD COLUMN IF NOT EXISTS trend_7_hrv_average NUMERIC NULL;

-- Stress rolling features
ALTER TABLE oura_features_daily ADD COLUMN IF NOT EXISTS rm_7_stress_high_minutes NUMERIC NULL;
ALTER TABLE oura_features_daily ADD COLUMN IF NOT EXISTS rm_14_stress_high_minutes NUMERIC NULL;

-- SpO2 rolling features
ALTER TABLE oura_features_daily ADD COLUMN IF NOT EXISTS rm_7_spo2_average NUMERIC NULL;

-- Workout rolling features
ALTER TABLE oura_features_daily ADD COLUMN IF NOT EXISTS rm_7_workout_total_minutes NUMERIC NULL;
