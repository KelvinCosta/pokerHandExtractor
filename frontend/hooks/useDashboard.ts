/**
 * useDashboard.ts
 * React hook that owns the dashboard filter state and fetches
 * /api/dashboard/health and /api/dashboard/preflop in parallel.
 *
 * Usage:
 *   const { health, preflop, loading, error, refetch } = useDashboard(filters)
 *
 * The hook re-fetches automatically whenever `filters` changes.
 * It also cleans up in-flight requests on unmount (AbortController).
 */
"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { fetchHealthMetrics, fetchPreflopMetrics, fetchProfitTrend, fetchAnalyticsBento, fetchPostflopEngines, fetchBigPots } from "@/lib/api"
import type { DashboardFilters, HealthMetrics, PreflopMetrics, ProfitTrendPoint, AnalyticsBentoMetrics, PostflopEngineMetrics, BigPotHand } from "@/lib/api.types"

export interface DashboardState {
  /** Current filter values */
  filters: DashboardFilters

  /** Data returned by /api/dashboard/health */
  health: HealthMetrics | null
  /** Data returned by /api/dashboard/preflop */
  preflop: PreflopMetrics | null
  /** Data returned by /api/dashboard/profit-trend */
  profitTrend: ProfitTrendPoint[] | null
  /** Data returned by /api/dashboard/analytics */
  analytics: AnalyticsBentoMetrics | null
  /** Data returned by /api/dashboard/engines/postflop */
  postflop: PostflopEngineMetrics | null
  /** Data returned by /api/dashboard/big-pots */
  bigPots: BigPotHand[] | null

  loading: boolean
  error: string | null

  /** Manually trigger a re-fetch with the current filters */
  refetch: () => void
}

/** Initial filter state — empty means "all data" */
const DEFAULT_FILTERS: DashboardFilters = {}

export function useDashboard(filters: DashboardFilters = DEFAULT_FILTERS): DashboardState {
  const [health, setHealth] = useState<HealthMetrics | null>(null)
  const [preflop, setPreflop] = useState<PreflopMetrics | null>(null)
  const [profitTrend, setProfitTrend] = useState<ProfitTrendPoint[] | null>(null)
  const [analytics, setAnalytics] = useState<AnalyticsBentoMetrics | null>(null)
  const [postflop, setPostflop] = useState<PostflopEngineMetrics | null>(null)
  const [bigPots, setBigPots] = useState<BigPotHand[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Used to force a manual re-fetch without changing filters
  const [tick, setTick] = useState(0)
  const refetch = useCallback(() => setTick((t) => t + 1), [])

  // Track the latest AbortController so we can cancel stale requests
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    // Cancel any in-flight request from a previous render
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    let cancelled = false

    const load = async () => {
      setLoading(true)
      setError(null)

      try {
        // Parallel fetch — all requests share the same filter payload and signal
        const payload = { ...filters }
        
        const [healthData, preflopData, profitTrendData, analyticsData, postflopData, bigPotsData] = await Promise.all([
          fetchHealthMetrics(payload, controller.signal),
          fetchPreflopMetrics(payload, controller.signal),
          fetchProfitTrend(payload, controller.signal),
          fetchAnalyticsBento(payload, controller.signal),
          fetchPostflopEngines(payload, controller.signal),
          fetchBigPots(payload, controller.signal),
        ])

        if (!cancelled) {
          setHealth(healthData)
          setPreflop(preflopData)
          setProfitTrend(profitTrendData)
          setAnalytics(analyticsData)
          setPostflop(postflopData)
          setBigPots(bigPotsData)
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, tick])

  return { filters, health, preflop, profitTrend, analytics, postflop, bigPots, loading, error, refetch }
}
