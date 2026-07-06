"use client"

/**
 * filter-bar.tsx
 * Compact filter bar rendered inside the Topbar area.
 * Provides all inputs that map to the DashboardFilters payload:
 *   start_date / end_date / game_types / stake / hero_name
 *
 * Props:
 *   filters    → current DashboardFilters state (controlled)
 *   onChange   → called whenever any filter changes
 *   loading    → disables inputs while a request is in flight
 */

import { useCallback, useEffect, useState } from "react"
import type { DashboardFilters } from "@/lib/api.types"
import { Button } from "@/components/ui/button"
import { RotateCcw } from "lucide-react"
import { cn } from "@/lib/utils"

// ─── Preset stake levels matching the backend dataset ─────────────────────────
const ALL_STAKE_OPTIONS: { label: string; value: number | undefined }[] = [
  { label: "All",     value: undefined },
  { label: "NL2",    value: 0.02 },
  { label: "NL5",    value: 0.05 },
  { label: "NL10",   value: 0.10 },
  { label: "NL25",   value: 0.25 },
  { label: "NL50",   value: 0.50 },
  { label: "NL100",  value: 1.00 },
  { label: "NL200",  value: 2.00 },
  { label: "NL500",  value: 5.00 },
  { label: "NL1000", value: 10.00 },
]

const ALL_GAME_TYPE_OPTIONS: { label: string; value: string | undefined }[] = [
  { label: "All Types", value: undefined },
  { label: "Rush & Cash", value: "Rush & Cash" },
  { label: "Regular Cash", value: "Regular Cash" },
  { label: "Tournaments", value: "Tournament" },
  { label: "Spin & Gold", value: "Spin & Gold" },
  { label: "Mystery Battle Royale", value: "Mystery Battle Royale" },
  { label: "All-In or Fold", value: "All-In or Fold" },
]

const EMPTY_FILTERS: DashboardFilters = {}

interface FilterBarProps {
  filters: DashboardFilters
  onChange: (f: DashboardFilters) => void
  loading?: boolean
  className?: string
}

export function FilterBar({ filters, onChange, loading = false, className }: FilterBarProps) {
  const [availableStakes, setAvailableStakes] = useState<number[]>([])
  const [availableGameTypes, setAvailableGameTypes] = useState<string[]>([])
  const [minDate, setMinDate] = useState<string | undefined>()
  const [maxDate, setMaxDate] = useState<string | undefined>()

  useEffect(() => {
    let cancelled = false;
    import("@/lib/api").then(({ fetchDashboardMetadata }) => {
      fetchDashboardMetadata().then(res => {
        if (!cancelled) {
          setAvailableStakes(res.stakes || [])
          setAvailableGameTypes(res.game_types || [])
          setMinDate(res.min_date)
          setMaxDate(res.max_date)
        }
      }).catch(() => {})
    })
    return () => { cancelled = true }
  }, [])

  const STAKE_OPTIONS = ALL_STAKE_OPTIONS.filter(
    (o) => o.value === undefined || availableStakes.includes(o.value)
  )

  const GAME_TYPE_OPTIONS = ALL_GAME_TYPE_OPTIONS.filter(
    (o) => o.value === undefined || availableGameTypes.length === 0 || availableGameTypes.includes(o.value)
  )

  const patch = useCallback(
    (partial: Partial<DashboardFilters>) =>
      onChange({ ...filters, ...partial }),
    [filters, onChange],
  )

  const reset = useCallback(() => onChange(EMPTY_FILTERS), [onChange])

  const selectedStake = STAKE_OPTIONS.find((o) => o.value === filters.stake) ?? STAKE_OPTIONS[0]
  
  // Como o filtro aceita array, pegamos o primeiro elemento selecionado se houver, ou 'All Types'
  const currentTypeVal = filters.game_types && filters.game_types.length > 0 ? filters.game_types[0] : undefined
  const selectedGameType = GAME_TYPE_OPTIONS.find((o) => o.value === currentTypeVal) ?? GAME_TYPE_OPTIONS[0]

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card/60 px-3 py-2 backdrop-blur-sm",
        className,
      )}
    >
      {/* ── Date Range ────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1.5">
        <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          From
        </label>
        <input
          type="date"
          disabled={loading}
          value={filters.start_date ?? ""}
          min={minDate}
          max={maxDate}
          onChange={(e) => patch({ start_date: e.target.value || undefined })}
          className="h-7 rounded border border-input bg-background px-2 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50 [color-scheme:dark]"
        />
        <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          To
        </label>
        <input
          type="date"
          disabled={loading}
          value={filters.end_date ?? ""}
          min={minDate}
          max={maxDate}
          onChange={(e) => patch({ end_date: e.target.value || undefined })}
          className="h-7 rounded border border-input bg-background px-2 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50 [color-scheme:dark]"
        />
      </div>

      <div className="h-4 w-px bg-border" />

      {/* ── Game Type ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1.5">
        <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground" title="Game Type">
          Type
        </label>
        <select
          disabled={loading}
          value={selectedGameType.label}
          onChange={(e) => {
            const opt = GAME_TYPE_OPTIONS.find((o) => o.label === e.target.value)
            patch({ game_types: opt?.value ? [opt.value] : undefined })
          }}
          className="h-7 cursor-pointer rounded border border-input bg-background px-2 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
        >
          {GAME_TYPE_OPTIONS.map((gt) => (
            <option key={gt.label} value={gt.label}>
              {gt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="h-4 w-px bg-border" />

      {/* ── Stake ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1.5">
        <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Stake
        </label>
        <select
          disabled={loading}
          value={selectedStake.label}
          onChange={(e) => {
            const opt = STAKE_OPTIONS.find((o) => o.label === e.target.value)
            patch({ stake: opt?.value })
          }}
          className="h-7 rounded border border-input bg-background px-2 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
        >
          {STAKE_OPTIONS.map((o) => (
            <option key={o.label} value={o.label}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {/* ── Reset ─────────────────────────────────────────────────────────── */}
      <Button
        variant="ghost"
        size="sm"
        disabled={loading}
        onClick={reset}
        className="ml-auto h-7 gap-1.5 px-2 text-[10px] text-muted-foreground hover:text-foreground"
        title="Reset all filters"
      >
        <RotateCcw className="size-3" />
        Reset
      </Button>
    </div>
  )
}
