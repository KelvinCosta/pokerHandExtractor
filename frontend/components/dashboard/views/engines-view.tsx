"use client"

import { useDashboard } from "@/hooks/useDashboard"
import type { DashboardFilters } from "@/lib/api.types"

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { MetricGauge } from "@/components/dashboard/metric-gauge"


const distConfig = {
  fold: { label: "Fold", color: "var(--chart-4)" },
  call: { label: "Call", color: "var(--chart-3)" },
  raise: { label: "Raise", color: "var(--chart-1)" },
} satisfies ChartConfig

export function EnginesView({ filters }: { filters?: DashboardFilters }) {
  const { preflop, postflop, actionDistribution, loading, error } = useDashboard(filters ?? {})

  const livePreflopMetrics = preflop ? [
    { key: "vpip", label: "VPIP", value: preflop.vpip_pct, unit: "%", trend: "up", delta: "Optimal", hint: "Voluntarily put $ in pot" },
    { key: "pfr", label: "PFR", value: preflop.pfr_pct, unit: "%", trend: "up", delta: "Good", hint: "Pre-flop raise" },
    { key: "three_bet", label: "3-Bet", value: preflop.three_bet_pct, unit: "%", trend: "up", delta: "Aggressive", hint: "Re-raise before flop" },
  ] : [];

  const livePostflopMetrics = postflop ? [
    { key: "cbet_flop", label: "C-Bet Flop", value: postflop.cbet_flop_pct, unit: "%", trend: "up", delta: "Aggressive", hint: "Bet flop as pre-flop raiser" },
    { key: "fold_cbet_flop", label: "Fold to Flop C-Bet", value: postflop.fold_to_cbet_flop_pct, unit: "%", trend: "down", delta: "Sticky", hint: "Fold when facing C-Bet" }
  ] : [];

  return (
    <div className="flex flex-col gap-4">
      <section>
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-sm font-semibold">Pre-Flop Engine</h2>
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            aggression & range control
          </span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {livePreflopMetrics.map((m) => (
            <MetricGauge key={m.key} metric={m as any} scaleMax={m.unit === "%" ? 100 : m.key === "gap" ? 10 : 100} />
          ))}
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-sm font-semibold">Post-Flop Engine</h2>
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            barreling & showdown value
          </span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {livePostflopMetrics.map((m) => (
            <MetricGauge key={m.key} metric={m as any} scaleMax={m.unit === "x" ? 5 : 100} />
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-semibold">Action Distribution by Street</h2>
        <p className="mb-4 text-xs text-muted-foreground">
          How the hero distributes fold / call / raise across each betting round
        </p>
        <ChartContainer config={distConfig} className="h-[260px] w-full">
          <BarChart data={actionDistribution || []} margin={{ left: -16, right: 8, top: 16 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis dataKey="street" tickLine={false} axisLine={false} tickMargin={8} className="font-mono text-[10px]" />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={32}
              tickFormatter={(v) => `${v}%`}
              className="font-mono text-[10px]"
            />
            <ChartTooltip content={<ChartTooltipContent className="font-mono" />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="fold" stackId="a" fill="var(--color-fold)" radius={[0, 0, 0, 0]} />
            <Bar dataKey="call" stackId="a" fill="var(--color-call)" />
            <Bar dataKey="raise" stackId="a" fill="var(--color-raise)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ChartContainer>
      </section>
    </div>
  )
}
