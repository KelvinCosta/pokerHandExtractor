"use client"

import { cn } from "@/lib/utils"
import type { Kpi } from "@/lib/poker-data"
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react"

export function KpiCard({ kpi }: { kpi: Kpi }) {
  const TrendIcon = kpi.trend === "up" ? ArrowUpRight : kpi.trend === "down" ? ArrowDownRight : Minus
  // "down" is not inherently bad (e.g. lower std dev / variance is good), so color neutrally there.
  const positive = kpi.trend === "up"
  const neutral = kpi.trend === "down"

  return (
    <div className="group relative overflow-hidden rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/30">
      <div className="flex items-start justify-between">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {kpi.label}
        </p>
        <span
          className={cn(
            "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 font-mono text-[10px] font-medium",
            positive && "bg-primary/12 text-primary",
            neutral && "bg-muted text-muted-foreground",
            !positive && !neutral && "bg-loss/12 text-loss",
          )}
        >
          <TrendIcon className="size-3" />
          {kpi.delta}
        </span>
      </div>
      <p className="mt-2 font-mono text-2xl font-semibold tracking-tight tabular-nums">{kpi.value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{kpi.hint}</p>
      <div className="pointer-events-none absolute -right-6 -top-6 size-16 rounded-full bg-primary/5 opacity-0 blur-xl transition-opacity group-hover:opacity-100" />
    </div>
  )
}
