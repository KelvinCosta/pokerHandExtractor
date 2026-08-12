"use client"

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { KpiCard, KpiCardSkeleton } from "@/components/dashboard/kpi-card"
import {
  currency,
} from "@/lib/poker-data"
import { cn } from "@/lib/utils"
import { useDashboard } from "@/hooks/useDashboard"
import { AlertTriangle } from "lucide-react"
import type { DashboardFilters } from "@/lib/api.types"

const chartConfig = {
  profit: { label: "Actual", color: "var(--chart-1)" },
  ev: { label: "All-in Adj (EV)", color: "var(--chart-2)" },
} satisfies ChartConfig

// ─── Helpers to map API data → KpiCard props ──────────────────────────────────
// Guard: the backend can return a partial error object { error: "...", total_hands: 0 }
// that passes the `!= null` check but is missing critical numeric fields.
function isValidHealth(h: unknown): h is {
  total_hands: number
  profit_usd: number
  bb_100: number
  std_dev_bb100?: number
  total_sessions?: number
} {
  if (!h || typeof h !== "object") return false
  const obj = h as Record<string, unknown>
  return (
    typeof obj.total_hands === "number" &&
    typeof obj.profit_usd  === "number" &&
    typeof obj.bb_100      === "number"
  )
}

function isValidPreflop(p: unknown): p is { vpip_pct: number; pfr_pct: number } {
  if (!p || typeof p !== "object") return false
  const obj = p as Record<string, unknown>
  return typeof obj.vpip_pct === "number" && typeof obj.pfr_pct === "number"
}

function buildLiveKpis(health: unknown, preflop: unknown) {
  const h = isValidHealth(health)  ? health  : null
  const p = isValidPreflop(preflop) ? preflop : null

  if (!h && !p) return null

  return [
    // ── Row 1: from /health ───────────────────────────────────────────────
    {
      id: "profit",
      label: "Net Profit",
      value: h ? `$${h.profit_usd.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—",
      raw: h?.profit_usd ?? 0,
      delta: "",
      trend: (h?.profit_usd ?? 0) >= 0 ? ("up" as const) : ("down" as const),
      hint: "Net profit in USD · all tracked hands",
    },
    {
      id: "winrate",
      label: "Win Rate",
      value: h ? `${h.bb_100.toFixed(2)} bb/100` : "—",
      raw: h?.bb_100 ?? 0,
      delta: "",
      trend: (h?.bb_100 ?? 0) >= 0 ? ("up" as const) : ("down" as const),
      hint: "Big blinds won per 100 hands",
    },
    {
      id: "hands",
      label: "Hands Played",
      value: h ? h.total_hands.toLocaleString("en-US") : "—",
      raw: h?.total_hands ?? 0,
      delta: "",
      trend: "up" as const,
      hint: "Total tracked hands",
    },
    // ── Row 2: VPIP/PFR from /preflop ────────────────────────────────────
    {
      id: "vpip_pfr",
      label: "VPIP / PFR",
      value: p ? `${p.vpip_pct} / ${p.pfr_pct}` : "—",
      raw: p?.vpip_pct ?? 0,
      delta: p ? `Gap: ${(p.vpip_pct - p.pfr_pct).toFixed(1)}` : "",
      trend: "flat" as const,
      hint: "Pre-flop aggression profile",
    },
    // ── Row 3: std_dev + sessions from /health ────────────────────────────
    {
      id: "std_dev",
      label: "Std Dev",
      value: h?.std_dev_bb100 != null ? `${h.std_dev_bb100.toFixed(1)} bb/100` : "—",
      raw: h?.std_dev_bb100 ?? 0,
      delta: "",
      trend: "flat" as const,
      hint: "Variance in bb/100 — lower is more consistent",
    },
    {
      id: "sessions",
      label: "Sessions",
      value: h?.total_sessions != null ? h.total_sessions.toLocaleString("en-US") : "—",
      raw: h?.total_sessions ?? 0,
      delta: "",
      trend: "up" as const,
      hint: "Distinct session days tracked",
    },
  ]
}

export function OverviewView({ filters }: { filters?: DashboardFilters }) {
  const { health, preflop, profitTrend, monthlyProfit, stakeBreakdown: liveStakeBreakdown, loading, error } = useDashboard(filters ?? {})
  const displayStakeBreakdown = liveStakeBreakdown || []
  const maxProfit = displayStakeBreakdown.length > 0 ? Math.max(...displayStakeBreakdown.map((s) => s.profit)) : 1

  // Build live KPI cards when data is available, else fall back to mock
  const liveKpis = buildLiveKpis(health, preflop)
  const displayKpis = liveKpis || []

  // Map live profitTrend or fall back to mock
  const displayProfitData = profitTrend && profitTrend.length > 0
    ? profitTrend.map((pt) => ({
        time: pt.date, // Use the full timestamp so each hand is a step in the area chart
        profit: pt.cumulative_profit,
      }))
    : []

  // Determinar o pico do gráfico atual (usando valor absoluto para pegar picos negativos tb)
  const chartMaxProfit = Math.max(
    ...displayProfitData.map((d) => Math.abs(d.profit))
  )

  const displayMonthlyProfit = monthlyProfit || []

  return (
    <div className="flex flex-col gap-4">
      {/* ── Live API status ──────────────────────────────────────────────── */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-[#FF3B3B]/20 bg-[#FF3B3B]/8 px-3 py-2 text-xs text-[#FF3B3B]">
          <AlertTriangle className="size-3.5 shrink-0" />
          <span>Backend unreachable — showing mock data. ({error})</span>
        </div>
      )}

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {loading && !liveKpis ? (
          // Rich skeleton placeholders while the first fetch is in flight
          Array.from({ length: 6 }).map((_, i) => (
            <KpiCardSkeleton key={i} />
          ))
        ) : (
          displayKpis.map((k) => (
            <div key={k.id} className="relative">
              <KpiCard kpi={k} />
              {/* Live data badge — only on live KPI cards */}
              {liveKpis?.some((lk) => lk.id === k.id) && (
                <span className="absolute right-2 top-2 rounded-full bg-[#10B981]/15 px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wide text-[#10B981]">
                  live
                </span>
              )}
            </div>
          ))
        )}
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
            <AreaChart data={displayProfitData} margin={{ left: 4, right: 8, top: 8 }}>
              <defs>
                <linearGradient id="fillProfit" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-profit)" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="var(--color-profit)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey={profitTrend && profitTrend.length > 0 ? "time" : "week"}
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                minTickGap={32}
                className="font-mono text-[10px]"
                tickFormatter={(value) => {
                  if (typeof value !== "string" || !value) return ""
                  // Backend returns "YYYY/MM/DD HH:MM:SS" — show only the date portion
                  if (value.includes(" ")) {
                    const datePart = value.split(" ")[0] // "YYYY/MM/DD"
                    const parts = datePart.split("/")
                    if (parts.length === 3 && parts[1] && parts[2]) {
                      return `${parts[2]}/${parts[1]}`  // "DD/MM"
                    }
                    return datePart // fallback: show raw date
                  }
                  return value
                }}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                width={48}
                tickFormatter={(v) => {
                  if (v === 0) return "$0"
                  if (chartMaxProfit < 1000) return `$${v.toFixed(0)}`
                  return `$${(v / 1000).toFixed(1).replace(/\.0$/, '')}k`
                }}
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
            {displayStakeBreakdown.map((s) => (
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
                  <div className="flex flex-col items-end gap-0">
                    {s.profit_usd !== 0 && (
                      <span className="w-16 text-right font-mono tabular-nums text-foreground">
                        {currency(s.profit_usd)}
                      </span>
                    )}
                    {s.profit_chips !== 0 && (
                      <span className="text-right font-mono text-[10px] tabular-nums text-muted-foreground">
                        {Math.round(s.profit_chips).toLocaleString("en-US")} chips
                      </span>
                    )}
                    {s.profit_usd === 0 && s.profit_chips === 0 && (
                      <span className="w-16 text-right font-mono tabular-nums text-foreground">
                        $0
                      </span>
                    )}
                  </div>
                  </div>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary/80"
                    style={{ width: `${((Math.abs(s.profit_usd) || Math.abs(s.profit_chips)) / maxProfit) * 100}%` }}
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

      {/* ── Monthly Profit Section ─────────────────────────────────────────── */}
      <section className="grid grid-cols-1 gap-4 xl:grid-cols-1 mt-2">
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Monthly Profit</h2>
              <p className="text-xs text-muted-foreground">Month-by-month financial performance</p>
            </div>
          </div>
          {displayMonthlyProfit.length === 0 ? (
            <div className="flex h-[240px] items-center justify-center text-sm text-muted-foreground">
              No monthly data available
            </div>
          ) : (
            <ChartContainer config={chartConfig} className="h-[240px] w-full">
              <BarChart data={displayMonthlyProfit} margin={{ left: 4, right: 8, top: 8, bottom: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis
                  dataKey="month"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  className="font-mono text-[10px]"
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  width={48}
                  tickFormatter={(v) => {
                    if (v === 0) return "$0"
                    if (Math.abs(v) < 1000) return `$${v.toFixed(0)}`
                    return `$${(v / 1000).toFixed(1).replace(/\.0$/, '')}k`
                  }}
                  className="font-mono text-[10px]"
                />
                <ChartTooltip
                  cursor={{ fill: "var(--border)", opacity: 0.1 }}
                  content={
                    <ChartTooltipContent
                      className="font-mono"
                      formatter={(value) => (
                        <span className="flex w-full justify-between gap-4">
                          <span className="capitalize text-muted-foreground">Profit</span>
                          <span className={cn("tabular-nums", Number(value) >= 0 ? "text-[#10B981]" : "text-[#FF3B3B]")}>
                            {currency(Number(value))}
                          </span>
                        </span>
                      )}
                    />
                  }
                />
                <Bar dataKey="profit" radius={[4, 4, 0, 0]} maxBarSize={60}>
                  {displayMonthlyProfit.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.profit >= 0 ? "var(--color-profit)" : "#FF3B3B"} />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          )}
        </div>
      </section>
    </div>
  )
}
