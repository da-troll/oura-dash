import { z } from 'zod';

// ============================================
// Health Check
// ============================================

export const HealthResponse = z.object({
  ok: z.boolean(),
});

export type HealthResponse = z.infer<typeof HealthResponse>;

// ============================================
// Authentication
// ============================================

export const AuthStatusResponse = z.object({
  connected: z.boolean(),
  expiresAt: z.string().datetime().optional(),
  scopes: z.array(z.string()).optional(),
});

export type AuthStatusResponse = z.infer<typeof AuthStatusResponse>;

export const AuthUrlResponse = z.object({
  url: z.string().url(),
  state: z.string(),
});

export type AuthUrlResponse = z.infer<typeof AuthUrlResponse>;

export const ExchangeCodeRequest = z.object({
  code: z.string(),
  state: z.string().optional(),
});

export type ExchangeCodeRequest = z.infer<typeof ExchangeCodeRequest>;

export const ExchangeCodeResponse = z.object({
  success: z.boolean(),
  message: z.string().optional(),
});

export type ExchangeCodeResponse = z.infer<typeof ExchangeCodeResponse>;

// ============================================
// Time Series
// ============================================

export const SeriesMetricRequest = z.object({
  metric: z.string(),
  start: z.string().date(),
  end: z.string().date(),
  filters: z.record(z.string()).optional(),
});

export type SeriesMetricRequest = z.infer<typeof SeriesMetricRequest>;

export const SeriesPoint = z.object({
  x: z.string(), // YYYY-MM-DD
  y: z.number().nullable(),
});

export type SeriesPoint = z.infer<typeof SeriesPoint>;

export const SeriesMetricResponse = z.object({
  metric: z.string(),
  points: z.array(SeriesPoint),
});

export type SeriesMetricResponse = z.infer<typeof SeriesMetricResponse>;

// ============================================
// Correlations
// ============================================

export const SpearmanCorrelation = z.object({
  metric: z.string(),
  rho: z.number(),
  pValue: z.number(),
  n: z.number(),
});

export type SpearmanCorrelation = z.infer<typeof SpearmanCorrelation>;

export const SpearmanRequest = z.object({
  target: z.string(),
  candidates: z.array(z.string()),
  start: z.string().date().optional(),
  end: z.string().date().optional(),
});

export type SpearmanRequest = z.infer<typeof SpearmanRequest>;

export const SpearmanResponse = z.object({
  target: z.string(),
  correlations: z.array(SpearmanCorrelation),
});

export type SpearmanResponse = z.infer<typeof SpearmanResponse>;

export const LaggedCorrelationPoint = z.object({
  lag: z.number(),
  rho: z.number(),
  pValue: z.number(),
  n: z.number(),
});

export type LaggedCorrelationPoint = z.infer<typeof LaggedCorrelationPoint>;

export const LaggedCorrelationRequest = z.object({
  metricX: z.string(),
  metricY: z.string(),
  maxLag: z.number().int().min(1).max(14).default(7),
  start: z.string().date().optional(),
  end: z.string().date().optional(),
});

export type LaggedCorrelationRequest = z.infer<typeof LaggedCorrelationRequest>;

export const LaggedCorrelationResponse = z.object({
  metricX: z.string(),
  metricY: z.string(),
  lags: z.array(LaggedCorrelationPoint),
  bestLag: z.number(),
});

export type LaggedCorrelationResponse = z.infer<typeof LaggedCorrelationResponse>;

export const ControlledCorrelationRequest = z.object({
  metricX: z.string(),
  metricY: z.string(),
  controlVars: z.array(z.string()),
  start: z.string().date().optional(),
  end: z.string().date().optional(),
});

export type ControlledCorrelationRequest = z.infer<typeof ControlledCorrelationRequest>;

export const ControlledCorrelationResponse = z.object({
  metricX: z.string(),
  metricY: z.string(),
  rho: z.number(),
  pValue: z.number(),
  n: z.number(),
  controlledFor: z.array(z.string()),
});

export type ControlledCorrelationResponse = z.infer<typeof ControlledCorrelationResponse>;

// ============================================
// Patterns
// ============================================

export const ChangePoint = z.object({
  date: z.string().date(),
  index: z.number(),
  beforeMean: z.number(),
  afterMean: z.number(),
  magnitude: z.number(),
  direction: z.enum(['increase', 'decrease']),
});

export type ChangePoint = z.infer<typeof ChangePoint>;

export const ChangePointRequest = z.object({
  metric: z.string(),
  start: z.string().date().optional(),
  end: z.string().date().optional(),
  penalty: z.number().optional(),
});

export type ChangePointRequest = z.infer<typeof ChangePointRequest>;

export const ChangePointResponse = z.object({
  metric: z.string(),
  changePoints: z.array(ChangePoint),
});

export type ChangePointResponse = z.infer<typeof ChangePointResponse>;

export const Anomaly = z.object({
  date: z.string().date(),
  value: z.number(),
  zScore: z.number(),
  direction: z.enum(['high', 'low']),
});

export type Anomaly = z.infer<typeof Anomaly>;

export const AnomalyRequest = z.object({
  metric: z.string(),
  start: z.string().date().optional(),
  end: z.string().date().optional(),
  threshold: z.number().default(3.0),
});

export type AnomalyRequest = z.infer<typeof AnomalyRequest>;

export const AnomalyResponse = z.object({
  metric: z.string(),
  anomalies: z.array(Anomaly),
});

export type AnomalyResponse = z.infer<typeof AnomalyResponse>;

export const WeeklyCluster = z.object({
  year: z.number(),
  week: z.number(),
  cluster: z.number(),
  label: z.string().optional(),
});

export type WeeklyCluster = z.infer<typeof WeeklyCluster>;

export const WeeklyClusterRequest = z.object({
  features: z.array(z.string()),
  nClusters: z.number().int().min(2).max(10).default(4),
  start: z.string().date().optional(),
  end: z.string().date().optional(),
});

export type WeeklyClusterRequest = z.infer<typeof WeeklyClusterRequest>;

export const WeeklyClusterResponse = z.object({
  weeks: z.array(WeeklyCluster),
  clusterProfiles: z.record(z.string(), z.record(z.string(), z.number())),
});

export type WeeklyClusterResponse = z.infer<typeof WeeklyClusterResponse>;

// ============================================
// Admin / Sync
// ============================================

export const SyncRequest = z.object({
  start: z.string().date(),
  end: z.string().date(),
});

export type SyncRequest = z.infer<typeof SyncRequest>;

export const SyncResponse = z.object({
  status: z.enum(['completed', 'failed', 'in_progress']),
  daysProcessed: z.number().optional(),
  message: z.string().optional(),
});

export type SyncResponse = z.infer<typeof SyncResponse>;

// ============================================
// Error Responses
// ============================================

export const ErrorResponse = z.object({
  error: z.string(),
  message: z.string(),
  details: z.record(z.string(), z.unknown()).optional(),
});

export type ErrorResponse = z.infer<typeof ErrorResponse>;
