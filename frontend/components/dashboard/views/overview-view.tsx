"use client"

import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  XAxis,
  YAxis,
} from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { KpiCard } from "@/components/dashboard/kpi-card"
import {
  currency,
  healthKpis,
  profitSeries,
  stakeBreakdown,
} from "@/lib/poker-data"
import { cn } from "@/lib/utils"

const chartConfig = {
  profit: { label: "Actual", color: "var(--chart-1)" },
  ev: { label: "All-in Adj (EV)", color: "var(--chart-2)" },
} satisfies ChartConfig

export function OverviewView() {
  const maxProfit = Math.max(...stakeBreakdown.map((s) => s.profit))

  return (
    <div className="flex flex-col gap-4">
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {healthKpis.map((k) => (
          <KpiCard key={k.id} kpi={k} />
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-4 xl:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Cumulative Profit</h2>
              <p className="text-xs text-muted-foreground">Actual winnings vs all-in adjusted (EV)</p>
            </div>
            <div className="flex items-center gap-4 font-mono text-[11px]">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span className="size-2 rounded-full bg-chart-1" /> Actual
              </span>
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span className="size-2 rounded-full bg-chart-2" /> EV
              </span>
            </div>
          </div>
          <ChartContainer config={chartConfig} className="h-[280px] w-full">
            <AreaChart data={profitSeries} margin={{ left: 4, right: 8, top: 8 }}>
              <defs>
                <linearGradient id="fillProfit" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-profit)" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="var(--color-profit)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="week"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                minTickGap={24}
                className="font-mono text-[10px]"
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                width={48}
                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                className="font-mono text-[10px]"
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    className="font-mono"
                    formatter={(value, name) => (
                      <span className="flex w-full justify-between gap-4">
                        <span className="capitalize text-muted-foreground">{name}</span>
                        <span className="tabular-nums">{currency(Number(value))}</span>
                      </span>
                    )}
                  />
                }
              />
              <Area
                dataKey="ev"
                type="monotone"
                stroke="var(--color-ev)"
                strokeWidth={1.5}
                strokeDasharray="4 3"
                fill="transparent"
              />
              <Area
                dataKey="profit"
                type="monotone"
                stroke="var(--color-profit)"
                strokeWidth={2}
                fill="url(#fillProfit)"
              />
            </AreaChart>
          </ChartContainer>
        </div>

        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold">Profit by Stake</h2>
          <p className="mb-4 text-xs text-muted-foreground">Where the edge is coming from</p>
          <ul className="flex flex-col gap-3">
            {stakeBreakdown.map((s) => (
              <li key={s.stake}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="font-mono font-medium">{s.stake}</span>
                  <div className="flex items-center gap-3">
                    <span
                      className={cn(
                        "font-mono tabular-nums",
                        s.winrate >= 4 ? "text-primary" : s.winrate >= 2 ? "text-warning" : "text-muted-foreground",
                      )}
                    >
                      {s.winrate} bb/100
                    </span>
                    <span className="w-16 text-right font-mono tabular-nums text-foreground">
                      {currency(s.profit)}
                    </span>
                  </div>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary/80"
                    style={{ width: `${(s.profit / maxProfit) * 100}%` }}
                  />
                </div>
                <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                  {(s.hands / 1000).toFixed(0)}k hands
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  )
}
