/**
 * api.types.ts
 * TypeScript mirror of all Pydantic schemas defined in the backend.
 * Keep this file in sync with:
 *   - backend/src/api/schemas/filters.py  → DashboardFilters
 *   - backend/src/api/schemas/chat.py     → Audit* models
 *   - backend/src/api/routers/dashboard.py → response shapes
 *   - backend/src/api/routers/chat.py     → response shapes
 */

// ─── Dashboard Filter Payload ─────────────────────────────────────────────────
// Maps 1-to-1 with DashboardFilters (Pydantic). All fields optional.
// Sending {} retrieves all data (backend default).
export interface DashboardFilters {
  start_date?: string        // ISO date string "YYYY-MM-DD"
  end_date?: string          // ISO date string "YYYY-MM-DD"
  game_types?: string[]      // e.g. ["Rush & Cash"]
  stake?: number             // float, e.g. 0.05
  hero_name?: string         // default "Hero" on the backend
  platforms?: string[]
  search_query?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user_id: string
}

// ─── Dashboard Response Types ─────────────────────────────────────────────────
export interface HealthMetrics {
  total_hands: number
  profit_usd: number
  profit_bb: number
  bb_100: number
  std_dev_bb100?: number    // added in backend Milestone 1+
  total_sessions?: number   // added in backend Milestone 1+
  /** Populated only when the backend returns an error but 200 status */
  error?: string
}

export interface PreflopMetrics {
  total_hands: number
  vpip_pct: number
  pfr_pct: number
  gap_pct: number
  three_bet_pct: number
  /** Populated only when the backend returns an error but 200 status */
  error?: string
}

export interface ProfitTrendPoint {
  date: string
  cumulative_profit: number
  hero_net_profit: number
}

// ─── Audit / Chat Request Types ───────────────────────────────────────────────
export interface AnalyticsBentoMetrics {
  wwsf_pct: number
  wtsd_pct: number
  wssd_pct: number
  blue_line_profit: number
  red_line_profit: number
}

export interface PostflopEngineMetrics {
  cbet_flop_pct: number
  fold_to_cbet_flop_pct: number
}

export interface BigPotHand {
  hand_id: string
  timestamp: string
  pot_in_bb: number
  net_profit: number
}

export interface HandAction {
  player: string
  action_type: string
  street: string
  amount: number
  is_all_in: boolean
  invested_amount: number
  pot_odds: number
}

export interface HandDetails {
  hand_id: string
  date: string
  data_limpa: string
  game_type: string
  stake_level: number
  platform: string
  player_nickname: string
  hero_net_profit: number
  total_pot_final: number
  board_cards: string[]
  player_cards: { player: string; cards: string }[]
  actions: HandAction[]
}
export interface AuditStartRequest {
  hero_name: string
  start_date?: string
  end_date?: string
}

export interface ChatMessageRequest {
  session_id: string
  message: string
}

export interface AuditCompleteRequest {
  session_id: string
}

// ─── Audit / Chat Response Types ─────────────────────────────────────────────
export interface AuditStartResponse {
  session_id: string
  message: string
  diagnostic_summary: string[]
}

export interface ChatMessageResponse {
  session_id: string
  message: string
}

export interface FinalReport {
  player_id: string
  behavioral_profile: string
  recommendations: string[]
  [key: string]: unknown   // forward-compat with future backend fields
}

export interface AuditCompleteResponse {
  status: "completed"
  final_report: FinalReport | null
}

// ─── Generic API Error ────────────────────────────────────────────────────────
export interface ApiError {
  detail: string | { msg: string; type: string }[]
}
