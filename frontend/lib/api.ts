/**
 * api.ts
 * Typed HTTP client for the Poker Analytics FastAPI backend.
 *
 * Design decisions:
 *  - Native fetch (no axios dependency added).
 *  - Every request goes through `apiPost()` which:
 *      1. Sets Content-Type: application/json
 *      2. Throws a typed ApiError on non-2xx
 *      3. Returns the parsed JSON body
 *  - BASE_URL is read from NEXT_PUBLIC_API_URL env var so the same build
 *    can target different environments (dev / staging / prod).
 *    Falls back to http://localhost:8000 for local dev.
 */

import type {
  DashboardFilters,
  HealthMetrics,
  PreflopMetrics,
  AuditStartRequest,
  AuditStartResponse,
  ChatMessageRequest,
  ChatMessageResponse,
  AuditCompleteRequest,
  AuditCompleteResponse,
  ApiError,
} from "./api.types"

// ─── Base configuration ───────────────────────────────────────────────────────
const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000"

// ─── Core fetch wrapper ───────────────────────────────────────────────────────
/**
 * POST helper with typed request / response bodies.
 * Throws an Error with `message` set to the backend's `detail` string
 * on any non-2xx response.
 */
async function apiPost<TBody, TResponse>(
  path: string,
  body: TBody,
  signal?: AbortSignal,
): Promise<TResponse> {
  const url = `${BASE_URL}${path}`

  const headers: Record<string, string> = { "Content-Type": "application/json" }
  
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token")
    if (token) {
      headers["Authorization"] = `Bearer ${token}`
    }
  }

  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    let message = `HTTP ${res.status} — ${res.statusText}`
    try {
      const err: ApiError = await res.json()
      if (typeof err.detail === "string") {
        message = err.detail
      } else if (Array.isArray(err.detail)) {
        // Pydantic validation error format
        message = err.detail.map((d) => d.msg).join("; ")
      }
    } catch {
      // non-JSON error body — keep the HTTP status message
    }
    throw new Error(message)
  }

  return res.json() as Promise<TResponse>
}

// ─── Dashboard endpoints ──────────────────────────────────────────────────────

/**
 * POST /api/dashboard/health
 * Returns aggregate profit & win-rate KPIs for the given filter window.
 * Pass an empty object `{}` to fetch all available data.
 */
export async function fetchHealthMetrics(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<HealthMetrics> {
  return apiPost<DashboardFilters, HealthMetrics>(
    "/api/dashboard/health",
    filters,
    signal,
  )
}

export async function fetchStakeBreakdown(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<any[]> {
  return apiPost<DashboardFilters, any[]>(
    "/api/dashboard/health/stake-breakdown",
    filters,
    signal,
  )
}

/**
 * POST /api/dashboard/preflop
 * Returns pre-flop stats: VPIP, PFR, Gap, 3-Bet.
 * Pass an empty object `{}` to fetch all available data.
 */
export async function fetchPreflopMetrics(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<PreflopMetrics> {
  return apiPost<DashboardFilters, PreflopMetrics>(
    "/api/dashboard/preflop",
    filters,
    signal,
  )
}

// ─── Audit / Chat endpoints ───────────────────────────────────────────────────
import type { 
  ProfitTrendPoint, 
  AnalyticsBentoMetrics, 
  PostflopEngineMetrics, 
  BigPotHand 
} from "./api.types"

/**
 * POST /api/dashboard/profit-trend
 * Returns the chronological evolution of hero_net_profit
 */
export async function fetchProfitTrend(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<ProfitTrendPoint[]> {
  return apiPost<DashboardFilters, ProfitTrendPoint[]>(
    "/api/dashboard/profit-trend",
    filters,
    signal,
  )
}

/**
 * POST /api/dashboard/analytics
 * Returns WWSF, WTSD, W$SD and Red/Blue line profit
 */
export async function fetchAnalyticsBento(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<AnalyticsBentoMetrics> {
  return apiPost<DashboardFilters, AnalyticsBentoMetrics>(
    "/api/dashboard/analytics",
    filters,
    signal,
  )
}

/**
 * POST /api/dashboard/engines/postflop
 * Returns C-Bet and Fold-to-C-Bet stats
 */
export async function fetchPostflopEngines(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<PostflopEngineMetrics> {
  return apiPost<DashboardFilters, PostflopEngineMetrics>(
    "/api/dashboard/engines/postflop",
    filters,
    signal,
  )
}

/**
 * POST /api/dashboard/big-pots
 * Returns list of >40bb pots
 */
export async function fetchBigPots(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<BigPotHand[]> {
  return apiPost<DashboardFilters, BigPotHand[]>(
    "/api/dashboard/big-pots",
    filters,
    signal,
  )
}

export async function fetchActionDistribution(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<any[]> {
  return apiPost<DashboardFilters, any[]>(
    "/api/dashboard/engines/action-distribution",
    filters,
    signal,
  )
}

export async function fetchBiggestRivals(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<any[]> {
  return apiPost<DashboardFilters, any[]>(
    "/api/dashboard/biggest-rivals",
    filters,
    signal,
  )
}

// ─── Audit / Chat endpoints ───────────────────────────────────────────────────

/**
 * POST /api/audit/start
 * Initialises a new audit session for a given hero.
 * Returns the session_id that must be persisted and sent on subsequent calls.
 */
export async function startAudit(
  req: AuditStartRequest,
  signal?: AbortSignal,
): Promise<AuditStartResponse> {
  return apiPost<AuditStartRequest, AuditStartResponse>(
    "/api/audit/start",
    req,
    signal,
  )
}

/**
 * POST /api/audit/message
 * Sends a player reply to the Socratic AI and returns the next AI message.
 */
export async function sendAuditMessage(
  req: ChatMessageRequest,
  signal?: AbortSignal,
): Promise<ChatMessageResponse> {
  return apiPost<ChatMessageRequest, ChatMessageResponse>(
    "/api/audit/message",
    req,
    signal,
  )
}

/**
 * POST /api/audit/complete
 * Closes the session and triggers the final behavioural report.
 * The session is deleted from server-side memory after this call.
 */
export async function completeAudit(
  req: AuditCompleteRequest,
  signal?: AbortSignal,
): Promise<AuditCompleteResponse> {
  return apiPost<AuditCompleteRequest, AuditCompleteResponse>(
    "/api/audit/complete",
    req,
    signal,
  )
}

/**
 * Upload helper for multipart/form-data.
 */
export async function apiUpload(
  path: string,
  formData: FormData,
  signal?: AbortSignal,
): Promise<any> {
  const url = `${BASE_URL}${path}`

  const headers: Record<string, string> = {}
  
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token")
    if (token) {
      headers["Authorization"] = `Bearer ${token}`
    }
  }

  const res = await fetch(url, {
    method: "POST",
    headers,
    body: formData,
    signal,
  })

  if (!res.ok) {
    let message = `HTTP ${res.status} — ${res.statusText}`
    try {
      const err: ApiError = await res.json()
      if (typeof err.detail === "string") {
        message = err.detail
      } else if (Array.isArray(err.detail)) {
        message = err.detail.map((d) => d.msg).join(", ")
      }
    } catch {
      // no JSON or bad format
    }
    throw new Error(message)
  }

  return res.json()
}
