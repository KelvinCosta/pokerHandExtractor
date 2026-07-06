/**
 * useDashboard.ts
 * React hook that owns the dashboard filter state and fetches
 * all dashboard endpoints in parallel.
 *
 * Usage:
 *   const { health, preflop, loading, error, refetch } = useDashboard(filters)
 *
 * Performance:
 *   - Filters are JSON-serialized to a stable string to avoid spurious effect
 *     re-runs caused by new object references with the same values.
 *   - A 400ms debounce prevents 9 simultaneous requests on every keystroke.
 *   - AbortController cancels stale requests when filters change mid-flight.
 */
"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { fetchHealthMetrics, fetchPreflopMetrics, fetchProfitTrend, fetchMonthlyProfit, fetchAnalyticsBento, fetchPostflopEngines, fetchActionDistribution, fetchBiggestRivals, fetchStakeBreakdown } from "@/lib/api"
import type { DashboardFilters, HealthMetrics, PreflopMetrics, ProfitTrendPoint, MonthlyProfitPoint, AnalyticsBentoMetrics, PostflopEngineMetrics } from "@/lib/api.types"

export interface DashboardState {
  /** Current filter values */
  filters: DashboardFilters

  /** Data returned by /api/dashboard/health */
  health: HealthMetrics | null
  /** Data returned by /api/dashboard/health/stake-breakdown */
  stakeBreakdown: any[] | null
  /** Data returned by /api/dashboard/preflop */
  preflop: PreflopMetrics | null
  /** Data returned by /api/dashboard/profit-trend */
  profitTrend: ProfitTrendPoint[] | null
  /** Data returned by /api/dashboard/monthly-profit */
  monthlyProfit: MonthlyProfitPoint[] | null
  /** Data returned by /api/dashboard/analytics */
  analytics: AnalyticsBentoMetrics | null
  /** Data returned by /api/dashboard/engines/postflop */
  postflop: PostflopEngineMetrics | null
  /** Data returned by /api/dashboard/engines/action-distribution */
  actionDistribution: any[] | null

  /** Data returned by /api/dashboard/biggest-rivals */
  biggestRivals: any[] | null

  /** Metadata global (stakes e game types presentes no banco) */
  metadata: { stakes: number[]; game_types: string[] } | null

  loading: boolean
  error: string | null

  /** Manually trigger a re-fetch with the current filters */
  refetch: () => void
}

/** Initial filter state — empty means "all data" */
const DEFAULT_FILTERS: DashboardFilters = {}

/** Debounce delay in ms — prevents spamming 9 endpoints per keystroke */
const DEBOUNCE_MS = 400

export function useDashboard(filters: DashboardFilters = DEFAULT_FILTERS): DashboardState {
  const [health, setHealth] = useState<HealthMetrics | null>(null)
  const [stakeBreakdown, setStakeBreakdown] = useState<any[] | null>(null)
  const [preflop, setPreflop] = useState<PreflopMetrics | null>(null)
  const [profitTrend, setProfitTrend] = useState<ProfitTrendPoint[] | null>(null)
  const [monthlyProfit, setMonthlyProfit] = useState<MonthlyProfitPoint[] | null>(null)
  const [analytics, setAnalytics] = useState<AnalyticsBentoMetrics | null>(null)
  const [postflop, setPostflop] = useState<PostflopEngineMetrics | null>(null)
  const [actionDistribution, setActionDistribution] = useState<any[] | null>(null)
  const [bigPots, setBigPots] = useState<BigPotHand[] | null>(null)
  const [biggestRivals, setBiggestRivals] = useState<any[] | null>(null)
  const [metadata, setMetadata] = useState<{ stakes: number[]; game_types: string[] } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Used to force a manual re-fetch without changing filters
  const [tick, setTick] = useState(0)
  const refetch = useCallback(() => setTick((t) => t + 1), [])

  // Track the latest AbortController so we can cancel stale requests
  const abortRef = useRef<AbortController | null>(null)

  // ── Stabilisation: serialize filters to a string so the fetch effect only
  // re-fires when the VALUES change, not just the object reference.
  const filtersKey = JSON.stringify(filters)

  // ── Debounce: wait DEBOUNCE_MS after the last filter change before fetching.
  // This prevents 9 simultaneous API calls on every keystroke.
  const [debouncedKey, setDebouncedKey] = useState(filtersKey)
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedKey(filtersKey), DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [filtersKey])

  // ── Fetch Global Metadata once on mount ────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    import("@/lib/api").then(({ fetchDashboardMetadata }) => {
      fetchDashboardMetadata().then(res => {
        if (!cancelled) setMetadata(res)
      }).catch(() => {}) // Ignore errors for metadata
    })
    return () => { cancelled = true }
  }, [])

  // ── Main fetch effect — only fires after the debounce settles ────────────────
  useEffect(() => {
    // Cancel any in-flight request from a previous render
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    let cancelled = false

    const load = async () => {
      setLoading(true)
      setError(null)

      // Re-hydrate filters from the stable string so we always use current values
      const payload = JSON.parse(debouncedKey) as DashboardFilters

      try {
        // Parallel fetch — all requests share the same filter payload and signal
        const [healthData, stakeData, preflopData, profitTrendData, monthlyProfitData, analyticsData, postflopData, actionDistData, rivalsData] = await Promise.all([
          fetchHealthMetrics(payload, controller.signal),
          fetchStakeBreakdown(payload, controller.signal),
          fetchPreflopMetrics(payload, controller.signal),
          fetchProfitTrend(payload, controller.signal),
          fetchMonthlyProfit(payload, controller.signal),
          fetchAnalyticsBento(payload, controller.signal),
          fetchPostflopEngines(payload, controller.signal),
          fetchActionDistribution(payload, controller.signal),
          fetchBiggestRivals(payload, controller.signal),
        ])

        if (!cancelled) {
          setHealth(healthData)
          setStakeBreakdown(stakeData)
          setPreflop(preflopData)
          setProfitTrend(profitTrendData)
          setMonthlyProfit(monthlyProfitData)
          setAnalytics(analyticsData)
          setPostflop(postflopData)
          setActionDistribution(actionDistData)
          setBiggestRivals(rivalsData)
        }
      } catch (err: unknown) {
        if (cancelled) return
        // AbortError is intentional — don't surface as user-visible error
        if (err instanceof DOMException && err.name === "AbortError") return
        setError(err instanceof Error ? err.message : "Unknown error fetching dashboard data")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()

    return () => {
      cancelled = true
      controller.abort()
    }
  // debouncedKey is a stable string — safe to use as the sole filter dependency
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedKey, tick])

  return { filters, health, stakeBreakdown, preflop, profitTrend, monthlyProfit, analytics, postflop, actionDistribution, biggestRivals, loading, error, refetch }
}
