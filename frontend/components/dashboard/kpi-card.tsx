"use client"

import { cn } from "@/lib/utils"
import type { Kpi } from "@/lib/poker-data"
import {
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  TrendingUp,
  TrendingDown,
  Hash,
  Percent,
  Calendar,
  BarChart2,
  Activity,
} from "lucide-react"

// Map KPI id → contextual icon
const KPI_ICON: Record<string, React.ElementType> = {
  profit:    TrendingUp,
  winrate:   Activity,
  hands:     Hash,
  vpip_pfr:  Percent,
  std_dev:   BarChart2,
  sessions:  Calendar,
}

export function KpiCard({ kpi }: { kpi: Kpi }) {
  const TrendIcon =
    kpi.trend === "up"   ? ArrowUpRight :
    kpi.trend === "down" ? ArrowDownRight :
    Minus

  const isPositive = kpi.trend === "up"
  const isNegative = kpi.trend === "flat" ? false : kpi.trend === "down"
  const isNeutral  = kpi.trend === "flat"

  // Color system
  const accentCls   = isPositive ? "bg-[#10B981]" : isNegative ? "bg-[#FF3B3B]" : "bg-zinc-600"
  const glowCls     = isPositive ? "bg-[#10B981]/10" : isNegative ? "bg-[#FF3B3B]/10" : "bg-zinc-500/5"
  const valueCls    = isPositive ? "text-[#10B981]" : isNegative ? "text-[#FF3B3B]" : "text-foreground"
  const trendBadge  = isPositive
    ? "bg-[#10B981]/12 text-[#10B981]"
    : isNegative
      ? "bg-[#FF3B3B]/12 text-[#FF3B3B]"
      : "bg-zinc-800 text-zinc-400"
  const borderCls   = isPositive ? "hover:border-[#10B981]/25" : isNegative ? "hover:border-[#FF3B3B]/25" : "hover:border-border"

  const Icon = KPI_ICON[kpi.id] ?? Activity

  return (
    <div className={cn(
      "group relative flex overflow-hidden rounded-xl border border-border bg-card transition-all duration-300 hover:shadow-lg",
      borderCls,
    )}>
      {/* Left accent bar */}
      <div className={cn("w-1 shrink-0 rounded-l-xl transition-all duration-300 group-hover:w-1.5", accentCls)} />

      {/* Content */}
      <div className="relative flex flex-1 flex-col gap-3 p-4">
        {/* Ambient glow */}
        <div className={cn(
          "pointer-events-none absolute -right-6 -top-6 size-20 rounded-full blur-2xl transition-opacity duration-300 opacity-0 group-hover:opacity-100",
          glowCls,
        )} />

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Icon className="size-3.5 text-muted-foreground" />
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {kpi.label}
            </p>
          </div>
          {kpi.delta && (
            <span className={cn(
              "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 font-mono text-[9px] font-medium",
              trendBadge,
            )}>
              <TrendIcon className="size-3" />
              {kpi.delta}
            </span>
          )}
        </div>

        {/* Value */}
        <p className={cn(
          "font-mono text-2xl font-bold tracking-tight tabular-nums leading-none",
          valueCls,
        )}>
          {kpi.value}
        </p>

        {/* Hint */}
        {kpi.hint && (
          <p className="text-[11px] leading-tight text-muted-foreground">{kpi.hint}</p>
        )}
      </div>
    </div>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
export function KpiCardSkeleton() {
  return (
    <div className="relative flex overflow-hidden rounded-xl border border-border bg-card">
      <div className="w-1 shrink-0 rounded-l-xl bg-zinc-800" />
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="h-3 w-24 animate-pulse rounded bg-zinc-800" />
        <div className="h-7 w-32 animate-pulse rounded bg-zinc-800" />
        <div className="h-2.5 w-36 animate-pulse rounded bg-zinc-800/60" />
      </div>
    </div>
  )
}
