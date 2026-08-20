"use client"

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { popFoldToSteal, populationStyles } from "@/lib/poker-data"
import { cn } from "@/lib/utils"

const foldConfig = {
  fold: { label: "Fold to Steal", color: "var(--chart-1)" },
} satisfies ChartConfig

export function PopulationView() {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-dashed border-border bg-card/50 px-4 py-3">
        <p className="text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Mass Data Analysis</span> — aggregated
          behavior across <span className="font-mono text-primary">312,480</span> cross-referenced
          opponents in the tracked pool.
        </p>
      </div>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold">Field Composition</h2>
          <p className="mb-4 text-xs text-muted-foreground">Player archetypes &amp; their baseline win rate</p>
          <ul className="flex flex-col gap-3">
            {populationStyles.map((s) => (
              <li key={s.style}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="font-medium">{s.style}</span>
                  <div className="flex items-center gap-3 font-mono tabular-nums">
                    <span className="text-muted-foreground">{s.avgVpip}% vpip</span>
                    <span className={cn("w-16 text-right", s.avgWinrate >= 0 ? "text-primary" : "text-loss")}>
                      {s.avgWinrate > 0 ? "+" : ""}
                      {s.avgWinrate} bb
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-chart-2" style={{ width: `${s.share * 2.4}%` }} />
                  </div>
                  <span className="w-8 text-right font-mono text-[11px] text-muted-foreground">{s.share}%</span>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold">Fold to Steal by Position</h2>
          <p className="mb-4 text-xs text-muted-foreground">Population blind-defense tendencies</p>
          <ChartContainer config={foldConfig} className="h-[240px] w-full">
            <BarChart data={popFoldToSteal} margin={{ left: 4, right: 8, top: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="pos" tickLine={false} axisLine={false} tickMargin={8} className="font-mono text-[10px]" />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={32}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
                className="font-mono text-[10px]"
              />
              <ChartTooltip content={<ChartTooltipContent className="font-mono" />} />
              <Bar dataKey="fold" fill="var(--color-fold)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ChartContainer>
          <p className="mt-2 font-mono text-[10px] text-muted-foreground">
            Lower fold % = wider steal-defense. Attack UTG/MP steals, respect BB.
          </p>
        </div>
      </section>
    </div>
  )
}
