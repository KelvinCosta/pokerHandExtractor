"use client"

import { cn } from "@/lib/utils"
import type { Metric } from "@/lib/poker-data"

// Renders a metric with a horizontal gradient band, optimal zone highlight and
// an animated marker. The gradient shifts red→yellow→green→yellow→red across the
// full scale so the "healthy" zone is visually obvious at a glance.
export function MetricGauge({ metric, scaleMax }: { metric: Metric; scaleMax: number }) {
  const pct = (n: number) => Math.min(100, Math.max(0, (n / scaleMax) * 100))

  const inRange    = metric.value >= metric.optimalLow && metric.value <= metric.optimalHigh
  const markerLeft = pct(metric.value)
  const bandLeft   = pct(metric.optimalLow)
  const bandWidth  = pct(metric.optimalHigh) - pct(metric.optimalLow)

  // Delta vs nearest optimal boundary
  let deltaLabel = ""
  if (metric.value < metric.optimalLow) {
    deltaLabel = `↑ ${(metric.optimalLow - metric.value).toFixed(1)}${metric.unit} to optimal`
  } else if (metric.value > metric.optimalHigh) {
    deltaLabel = `↓ ${(metric.value - metric.optimalHigh).toFixed(1)}${metric.unit} above optimal`
  } else {
    deltaLabel = "Within optimal range"
  }

  const statusColor = inRange ? "#10B981" : "#FF3B3B"
  const statusBg    = inRange ? "bg-[#10B981]/10 text-[#10B981]" : "bg-[#FF3B3B]/10 text-[#FF3B3B]"

  return (
    <div className="group rounded-xl border border-border bg-card p-4 transition-all duration-300 hover:border-white/10 hover:shadow-lg">
      {/* Header */}
      <div className="mb-4 flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">{metric.label}</p>
          {metric.note && (
            <p className="mt-0.5 text-[11px] text-muted-foreground">{metric.note}</p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <p
            className="font-mono text-2xl font-bold tabular-nums leading-none"
            style={{ color: statusColor }}
          >
            {metric.value}
            <span className="ml-0.5 text-sm font-normal text-muted-foreground">{metric.unit}</span>
          </p>
          <span className={cn("rounded-full px-2 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wide", statusBg)}>
            {inRange ? "Optimal ✓" : "Out of range"}
          </span>
        </div>
      </div>

      {/* Gauge track */}
      <div className="relative h-2.5 overflow-visible rounded-full bg-zinc-800">
        {/* Gradient background: red–yellow–green–yellow–red */}
        <div
          className="absolute inset-0 rounded-full opacity-30"
          style={{
            background: "linear-gradient(to right, #FF3B3B 0%, #F59E0B 25%, #10B981 50%, #F59E0B 75%, #FF3B3B 100%)",
          }}
        />

        {/* Optimal zone highlight */}
        <div
          className="absolute inset-y-0 rounded-full opacity-70"
          style={{
            left:       `${bandLeft}%`,
            width:      `${bandWidth}%`,
            background: "rgba(16,185,129,0.35)",
            boxShadow:  "0 0 8px rgba(16,185,129,0.4)",
          }}
        />

        {/* Marker */}
        <div
          className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background shadow-lg transition-all duration-500"
          style={{
            left:       `${markerLeft}%`,
            background: statusColor,
            boxShadow:  `0 0 8px ${statusColor}80`,
          }}
        />
      </div>

      {/* Scale labels */}
      <div className="mt-3 flex items-center justify-between font-mono text-[9px] text-muted-foreground/60">
        <span>0{metric.unit}</span>
        <span className="rounded-full border border-[#10B981]/30 bg-[#10B981]/5 px-2 py-0.5 text-[#10B981]/80">
          opt {metric.optimalLow}–{metric.optimalHigh}{metric.unit}
        </span>
        <span>{scaleMax}{metric.unit}</span>
      </div>

      {/* Delta hint */}
      <p className={cn("mt-2 font-mono text-[10px]", inRange ? "text-[#10B981]/70" : "text-[#F59E0B]/70")}>
        {deltaLabel}
      </p>
    </div>
  )
}
