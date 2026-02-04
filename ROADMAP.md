# Oura Lab Feature Roadmap

Generated from AI analysis of the codebase. Prioritized by impact and implementation complexity.

---

## Phase 1: Quick Wins (Low Effort, High Value)

### 1.1 Annual Metric Heatmap
**Type:** Data Visualization
**Effort:** Low
**Value:** High

A GitHub-style calendar heatmap showing any metric over the past year. Each day is a colored square - instantly reveals weekly, monthly, and seasonal patterns.

**User Value:** "My readiness is always low on Mondays" or "My sleep tanked during that stressful project in April" - visible at a glance.

**Implementation:**
- Backend: New endpoint returning `{date, value}` for last 365 days
- Frontend: Use `react-calendar-heatmap` library with metric dropdown

---

### 1.2 Sleep Architecture View
**Type:** Data Visualization
**Effort:** Low
**Value:** High

Stacked bar chart showing sleep stage percentages (Deep, REM, Light) per night. Focus on sleep *quality* over quantity.

**User Value:** See how lifestyle affects sleep structure - e.g., alcohol crushes REM% even when total sleep time is unchanged.

**Implementation:**
- Backend: Calculate stage percentages from existing `sleep_rem_seconds`, `sleep_deep_seconds`, `sleep_total_seconds`
- Frontend: Recharts stacked bar chart with date on X-axis

---

### 1.3 Chronotype & Social Jetlag
**Type:** Analysis
**Effort:** Low
**Value:** Medium-High

Calculate user's natural chronotype (Morning Lark vs Night Owl) from weekend sleep patterns. Measure "Social Jetlag" - the mismatch between weekday and weekend sleep timing.

**User Value:** High Social Jetlag score explains persistent fatigue. Clear goal: align weekday sleep closer to natural patterns.

**Implementation:**
- Backend: Use `is_weekend` flag, calculate sleep midpoint, compare weekday vs weekend averages
- Frontend: Dashboard card with chronotype icon and Social Jetlag score (e.g., "1h 15m")

---

## Phase 2: Core Analytics Expansion

### 2.1 Workout Recovery Pattern Analysis
**Type:** Correlation/Analysis
**Effort:** Medium
**Value:** High

Analyze relationship between workout type/duration/intensity and next-day/second-day recovery (Readiness, HRV, RHR).

**User Value:** Fine-tune training schedule. Discover that HIIT suppresses HRV for 48 hours while long runs boost next-day Readiness.

**Implementation:**
- Backend: Normalize workout data into structured table, group by type, calculate D+1 and D+2 impact on recovery metrics
- Frontend: Bar chart per workout type showing average metric changes

---

### 2.2 Granger Causality Testing
**Type:** Statistical Analysis
**Effort:** Medium
**Value:** Medium-High

Statistical test to determine if one metric helps predict another beyond its own history. More robust than lagged correlation.

**User Value:** Discover true leading indicators. "Your medium_activity_minutes from 2 days ago Granger-causes your readiness_score (p < 0.05)"

**Implementation:**
- Backend: Use `statsmodels.grangercausalitytests()`
- Frontend: Add section in Correlations tab with human-readable results

---

### 2.3 Automated Weekly Review
**Type:** Feature
**Effort:** Medium
**Value:** High

Auto-generated weekly digest: averages, best/worst days, anomalies, change points, tag-to-outcome connections.

**User Value:** Proactive insights without manual exploration. Connects behavior to outcomes: "You logged 'alcohol' Friday, HRV dropped 10% Saturday."

**Implementation:**
- Backend: Scheduled job (APScheduler) running weekly analysis, storing report in DB
- Frontend: Reports page with list of weekly reviews, notification badge for new reports

---

## Phase 3: Predictive Intelligence

### 3.1 "Readiness for Tomorrow" Prediction
**Type:** Machine Learning
**Effort:** Medium-High
**Value:** Very High

Predict tomorrow's Readiness Score range based on today's activities and recent data.

**User Value:** Proactive health management. Low prediction → go to bed earlier, skip morning workout.

**Implementation:**
- Backend: XGBoost/LightGBM model trained on user data. Features: today's metrics + rolling averages. Target: D+1 readiness_score.
- Frontend: Prominent dashboard widget: "Tomorrow's Predicted Readiness: 78-84"

---

### 3.2 "What If?" Scenario Planner
**Type:** ML-Powered Feature
**Effort:** High
**Value:** Very High

Interactive tool: "What would my Readiness be if I sleep 8 hours and walk 12,000 steps today?"

**User Value:** Gamifies self-improvement. Direct feedback loop between actions and predicted outcomes from personal data.

**Implementation:**
- Backend: Train GradientBoostingRegressor on user data. Endpoint accepts slider inputs, returns prediction.
- Frontend: Modal/page with sliders for inputs, real-time prediction display

---

### 3.3 Illness Onset Detection
**Type:** ML / Anomaly Detection
**Effort:** High
**Value:** Very High

Early-warning system detecting patterns preceding illness: elevated RHR, suppressed HRV, rising temperature over multiple days.

**User Value:** 24-48 hour warning of physiological strain. Prioritize rest to potentially lessen illness severity.

**Implementation:**
- Backend: Requires user to tag sick days for labeling. Train classifier on 2-day deltas and 3-day rolling averages of RHR, HRV, temperature.
- Frontend: Notification when "Systemic Strain" score crosses threshold

---

## Phase 4: Advanced Causal Analysis

### 4.1 Causal Impact Analysis with Tags
**Type:** Statistical Analysis
**Effort:** High
**Value:** Very High

Estimate causal impact of tagged behaviors. Compare actual next-day metrics to a statistical forecast of what would have happened *without* that behavior.

**User Value:** Move beyond correlation to causation. "Logging 'alcohol' Friday appears to have caused Saturday HRV to be 12ms lower than expected."

**Implementation:**
- Backend: Bayesian Structural Time Series (BSTS) using `tfp.sts`. Train on pre-event data, predict counterfactual, measure difference.
- Frontend: Select tag + metric, display time series with actual vs predicted counterfactual and confidence interval

---

## Implementation Priority Matrix

| Feature | Effort | Value | Priority |
|---------|--------|-------|----------|
| Annual Metric Heatmap | Low | High | 🔴 P1 |
| Sleep Architecture View | Low | High | 🔴 P1 |
| Chronotype & Social Jetlag | Low | Medium-High | 🔴 P1 |
| Workout Recovery Analysis | Medium | High | 🟡 P2 |
| Granger Causality | Medium | Medium-High | 🟡 P2 |
| Automated Weekly Review | Medium | High | 🟡 P2 |
| Tomorrow's Readiness Prediction | Medium-High | Very High | 🟢 P3 |
| "What If?" Scenario Planner | High | Very High | 🟢 P3 |
| Illness Onset Detection | High | Very High | 🟢 P3 |
| Causal Impact Analysis | High | Very High | 🔵 P4 |

---

## Data Requirements

### Already Available
- Sleep metrics (duration, efficiency, stages, HRV, RHR)
- Activity metrics (steps, calories, activity score)
- Readiness metrics (score, contributors)
- Daily/weekend flags

### Needs Enhancement
- **Tags:** Need user tagging system for behaviors (alcohol, meditation, stress, etc.)
- **Workouts:** Raw workout data exists but needs normalization into structured table
- **Illness tracking:** Need user input for sick days to train illness detection

---

## Technical Dependencies

### New Libraries (Backend)
- `statsmodels` - Granger causality testing
- `tensorflow-probability` - Causal impact analysis (BSTS)
- `scikit-learn` / `xgboost` / `lightgbm` - ML predictions
- `apscheduler` - Scheduled weekly reports

### New Libraries (Frontend)
- `react-calendar-heatmap` - Annual heatmap visualization

---

## Suggested First Sprint

1. **Annual Metric Heatmap** - Quick visual win, high user delight
2. **Sleep Architecture View** - Uses existing data, adds depth to sleep insights
3. **Chronotype & Social Jetlag** - Simple calculation, actionable insight

These three features can be shipped together as a "Deep Insights" release.
