/**
 * API client for the analytics service.
 */

const ANALYTICS_BASE_URL =
  process.env.ANALYTICS_BASE_URL || "http://localhost:8001";

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

export class ApiClientError extends Error {
  constructor(
    public status: number,
    public data: ApiError
  ) {
    super(data.message);
    this.name = "ApiClientError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: ApiError;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        error: "unknown_error",
        message: response.statusText || "An unknown error occurred",
      };
    }
    throw new ApiClientError(response.status, errorData);
  }
  return response.json();
}

/**
 * Fetch from the analytics API (server-side only).
 */
export async function analyticsApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${ANALYTICS_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  return handleResponse<T>(response);
}

// ============================================
// Auth endpoints
// ============================================

export interface AuthUrlResponse {
  url: string;
  state: string;
}

export interface AuthStatusResponse {
  connected: boolean;
  expiresAt?: string;
  scopes?: string[];
}

export interface ExchangeCodeResponse {
  success: boolean;
  message?: string;
}

export async function getAuthUrl(): Promise<AuthUrlResponse> {
  return analyticsApi<AuthUrlResponse>("/auth/url");
}

export async function exchangeCode(code: string): Promise<ExchangeCodeResponse> {
  return analyticsApi<ExchangeCodeResponse>("/auth/oura/exchange", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export async function getAuthStatus(): Promise<AuthStatusResponse> {
  return analyticsApi<AuthStatusResponse>("/auth/status");
}

export async function revokeAuth(): Promise<{ success: boolean }> {
  return analyticsApi<{ success: boolean }>("/auth/revoke", {
    method: "POST",
  });
}

// ============================================
// Health check
// ============================================

export interface HealthResponse {
  ok: boolean;
}

export async function healthCheck(): Promise<HealthResponse> {
  return analyticsApi<HealthResponse>("/health");
}

// ============================================
// Dashboard
// ============================================

export interface DashboardSummary {
  readiness_avg: number | null;
  sleep_avg: number | null;
  activity_avg: number | null;
  steps_avg: number | null;
  days_with_data: number;
}

export interface TrendPoint {
  date: string;
  value: number | null;
  baseline: number | null;
}

export interface DashboardResponse {
  connected: boolean;
  summary: DashboardSummary;
  readiness_trend: TrendPoint[];
}

export async function getDashboard(): Promise<DashboardResponse> {
  return analyticsApi<DashboardResponse>("/dashboard");
}
