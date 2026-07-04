"use client"

import { cn } from "@/lib/utils"
import type { Metric } from "@/lib/poker-data"

// Renders a metric with a horizontal band showing the "optimal" range and a marker
// for the current value. Marker turns red when outside the healthy band.
export function MetricGauge({ metric, scaleMax }: { metric: Metric; scaleMax: number }) {
  const pct = (n: number) => Math.min(100, Math.max(0, (n / scaleMax) * 100))
  const inRange = metric.value >= metric.optimalLow && metric.value <= metric.optimalHigh
  const markerLeft = pct(metric.value)
  const bandLeft = pct(metric.optimalLow)
  const bandWidth = pct(metric.optimalHigh) - pct(metric.optimalLow)

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-baseline justify-between">
        <div>
          <p className="text-sm font-medium">{metric.label}</p>
          <p className="text-[11px] text-muted-foreground">{metric.note}</p>
        </div>
        <p
          className={cn(
            "font-mono text-lg font-semibold tabular-nums",
            inRange ? "text-foreground" : "text-loss",
          )}
        >
          {metric.value}
          <span className="ml-0.5 text-xs text-muted-foreground">{metric.unit}</span>
        </p>
      </div>

      <div className="relative mt-4 h-2 rounded-full bg-muted">
        <div
          className="absolute inset-y-0 rounded-full bg-primary/25"
          style={{ left: `${bandLeft}%`, width: `${bandWidth}%` }}
        />
        <div
          className={cn(
            "absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background",
            inRange ? "bg-primary" : "bg-loss",
          )}
          style={{ left: `${markerLeft}%` }}
        />
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[10px] text-muted-foreground">
        <span>0</span>
        <span className="text-primary/70">
          opt {metric.optimalLow}–{metric.optimalHigh}
        </span>
        <span>{scaleMax}</span>
      </div>
    </div>
  )
}
