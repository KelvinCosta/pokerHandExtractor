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

import { useCallback } from "react"
import type { DashboardFilters } from "@/lib/api.types"
import { Button } from "@/components/ui/button"
import { RotateCcw } from "lucide-react"
import { cn } from "@/lib/utils"

// ─── Preset stake levels matching the backend dataset ─────────────────────────
const STAKE_OPTIONS: { label: string; value: number | undefined }[] = [
  { label: "All",     value: undefined },
  { label: "NL2",    value: 0.02 },
  { label: "NL5",    value: 0.05 },
  { label: "NL10",   value: 0.10 },
  { label: "NL25",   value: 0.25 },
  { label: "NL50",   value: 0.50 },
  { label: "NL100",  value: 1.00 },
  { label: "NL200",  value: 2.00 },
  { label: "NL500",  value: 5.00 },
]

const GAME_TYPE_OPTIONS = ["Rush & Cash", "Zone Poker", "Regular"]

const EMPTY_FILTERS: DashboardFilters = {}

interface FilterBarProps {
  filters: DashboardFilters
  onChange: (f: DashboardFilters) => void
  loading?: boolean
  className?: string
}

export function FilterBar({ filters, onChange, loading = false, className }: FilterBarProps) {

  const patch = useCallback(
    (partial: Partial<DashboardFilters>) =>
      onChange({ ...filters, ...partial }),
    [filters, onChange],
  )

  const reset = useCallback(() => onChange(EMPTY_FILTERS), [onChange])

  const selectedStake = STAKE_OPTIONS.find((o) => o.value === filters.stake) ?? STAKE_OPTIONS[0]

  // Toggle a game type in/out of the array
  const toggleGameType = (gt: string) => {
    const current = filters.game_types ?? []
    const next = current.includes(gt)
      ? current.filter((t) => t !== gt)
      : [...current, gt]
    patch({ game_types: next.length > 0 ? next : undefined })
  }

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card/60 px-3 py-2 backdrop-blur-sm",
        className,
      )}
    >
      {/* ── Hero Name ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1.5">
        <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Hero
        </label>
        <input
          disabled={loading}
          value={filters.hero_name ?? ""}
          onChange={(e) => patch({ hero_name: e.target.value || undefined })}
          placeholder="Hero"
          className="h-7 w-24 rounded border border-input bg-background px-2 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
        />
      </div>

      <div className="h-4 w-px bg-border" />

      {/* ── Date Range ────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1.5">
        <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          From
        </label>
        <input
          type="date"
          disabled={loading}
          value={filters.start_date ?? ""}
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
          onChange={(e) => patch({ end_date: e.target.value || undefined })}
          className="h-7 rounded border border-input bg-background px-2 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50 [color-scheme:dark]"
        />
      </div>

      <div className="h-4 w-px bg-border" />

      {/* ── Game Type ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1.5">
        <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Type
        </label>
        <div className="flex gap-1">
          {GAME_TYPE_OPTIONS.map((gt) => {
            const active = (filters.game_types ?? []).includes(gt)
            return (
              <button
                key={gt}
                disabled={loading}
                onClick={() => toggleGameType(gt)}
                className={cn(
                  "h-7 rounded px-2 font-mono text-[10px] transition-colors disabled:opacity-50",
                  active
                    ? "bg-primary/20 text-primary ring-1 ring-primary/40"
                    : "bg-muted text-muted-foreground hover:text-foreground",
                )}
              >
                {gt}
              </button>
            )
          })}
        </div>
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
