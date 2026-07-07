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

export function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token")
    if (token) headers["Authorization"] = `Bearer ${token}`
  }
  return headers
}

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

async function apiGet<TResponse>(
  path: string,
  params?: Record<string, string>,
  signal?: AbortSignal,
): Promise<TResponse> {
  const query = params ? "?" + new URLSearchParams(params).toString() : ""
  const url = `${BASE_URL}${path}${query}`

  const headers: Record<string, string> = { "Content-Type": "application/json" }
  
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token")
    if (token) {
      headers["Authorization"] = `Bearer ${token}`
    }
  }

  const res = await fetch(url, {
    method: "GET",
    headers,
    signal,
  })

  if (!res.ok) {
    throw new Error(`HTTP ${res.status} — ${res.statusText}`)
  }

  return res.json() as Promise<TResponse>
}

// ─── Dashboard endpoints ──────────────────────────────────────────────────────

export async function fetchDashboardMetadata(filters: DashboardFilters = {}): Promise<{
  stakes: string[]
  game_types: string[]
  min_date?: string
  max_date?: string
}> {
  return apiPost("/api/dashboard/metadata", filters)
}

export async function fetchHandDetails(handId: string): Promise<any> {
  const url = `${BASE_URL}/api/dashboard/hand/${encodeURIComponent(handId)}`
  const headers: Record<string, string> = {}
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token")
    if (token) headers["Authorization"] = `Bearer ${token}`
  }
  const res = await fetch(url, { method: "GET", headers: getHeaders() })
  if (!res.ok) throw new Error("Failed to fetch hand details")
  return res.json()
}

export async function fetchProcessedFiles(): Promise<{processed: string[], version_mismatch: boolean}> {
  const res = await fetch(`${BASE_URL}/api/etl/processed`, {
    headers: getHeaders(),
  })
  if (!res.ok) {
    return {processed: [], version_mismatch: false}
  }
  return res.json()
}

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
 * POST /api/dashboard/monthly-profit
 * Returns profit/loss grouped by YYYY-MM
 */
export async function fetchMonthlyProfit(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<MonthlyProfitPoint[]> {
  return apiPost<DashboardFilters, MonthlyProfitPoint[]>(
    "/api/dashboard/monthly-profit",
    filters,
    signal,
  )
}

/**
 * POST /api/dashboard/tournaments
 * Returns a list of tournaments
 */
export async function fetchTournamentsList(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<TournamentSummary[]> {
  return apiPost<DashboardFilters, TournamentSummary[]>(
    "/api/dashboard/tournaments",
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
 * POST /api/dashboard/hands
 * Returns paginated and sorted list of hands
 */
export async function fetchHandsList(
  filters: HandsListFilters,
  signal?: AbortSignal,
): Promise<HandsListResponse> {
  return apiPost<HandsListFilters, HandsListResponse>(
    "/api/dashboard/hands",
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

export async function fetchRanges(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<any> {
  return apiPost<DashboardFilters, any>(
    "/api/dashboard/ranges",
    filters,
    signal,
  )
}

// ─── AI Analysis ──────────────────────────────────────────────────────────────
export interface AiAnalysisResponse {
  analysis_id: string
  raw_analysis: string
  agent_version: string
}

export interface AiFeedbackRequest {
  is_useful: boolean
  comments?: string
}

export async function analyzeHand(handId: string, signal?: AbortSignal): Promise<AiAnalysisResponse> {
  // We use POST with empty body, but our apiPost wrapper expects a body.
  return apiPost<Record<string, never>, AiAnalysisResponse>(
    `/api/ai/analyze/${handId}`,
    {},
    signal,
  )
}

export async function submitAnalysisFeedback(
  feedback: AiFeedbackRequest,
  signal?: AbortSignal,
): Promise<any> {
  return apiPost<AiFeedbackRequest, any>(
    "/api/ai/feedback",
    feedback,
    signal,
  )
}

export async function getHandNote(handId: string, signal?: AbortSignal): Promise<{ note: string }> {
  return apiGet<{ note: string }>(
    `/api/dashboard/hand/${handId}/note`,
    undefined,
    signal,
  )
}

export async function saveHandNote(handId: string, note: string, signal?: AbortSignal): Promise<any> {
  return apiPost<{ note: string }, any>(
    `/api/dashboard/hand/${handId}/note`,
    { note },
    signal,
  )
}

export async function fetchCbetTextures(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<import("./api.types").CbetTexturesResponse> {
  return apiPost<DashboardFilters, import("./api.types").CbetTexturesResponse>(
    "/api/dashboard/engines/cbet-textures",
    filters,
    signal,
  )
}

export async function fetchRiverAudit(
  filters: DashboardFilters = {},
  signal?: AbortSignal,
): Promise<import("./api.types").RiverAuditResponse> {
  return apiPost<DashboardFilters, import("./api.types").RiverAuditResponse>(
    "/api/dashboard/engines/river-audit",
    filters,
    signal,
  )
}

export async function getVillainTag(player: string, signal?: AbortSignal): Promise<{ note: string }> {
  return apiGet<{ note: string }>(
    `/api/dashboard/villains/${encodeURIComponent(player)}/tag`,
    undefined,
    signal,
  )
}

export async function saveVillainTag(player: string, note: string, signal?: AbortSignal): Promise<any> {
  return apiPost<{ note: string }, any>(
    `/api/dashboard/villains/${encodeURIComponent(player)}/tag`,
    { note },
    signal,
  )
}
