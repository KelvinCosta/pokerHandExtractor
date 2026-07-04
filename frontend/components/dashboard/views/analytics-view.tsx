"use client"

import { cn } from "@/lib/utils"
import {
  analyticsKpis,
  biggestRivals,
  currency,
  evBarSeries,
  topLeaks,
} from "@/lib/poker-data"
import {
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  TrendingUp,
  Zap,
  AlertTriangle,
  Skull,
} from "lucide-react"

// ─── Severity helpers ────────────────────────────────────────────────────────
const severityBadge: Record<string, string> = {
  critical: "bg-[#FF3B3B]/15 text-[#FF3B3B] border-[#FF3B3B]/30",
  major:    "bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/30",
  minor:    "bg-muted text-muted-foreground border-border",
}
const severityBar: Record<string, string> = {
  critical: "bg-[#FF3B3B]/80",
  major:    "bg-[#F59E0B]/80",
  minor:    "bg-muted-foreground/60",
}

// ─── Sub-component: Analytics KPI Card ───────────────────────────────────────
function AnalyticsKpiCard({
  kpi,
}: {
  kpi: (typeof analyticsKpis)[number]
}) {
  const TrendIcon =
    kpi.trend === "up"
      ? ArrowUpRight
      : kpi.trend === "down"
        ? ArrowDownRight
        : Minus

  const isProfit   = kpi.id === "total_profit" || kpi.id === "winrate"
  const isPurple   = kpi.id === "hands_played"
  const isAmber    = kpi.id === "vpip_pfr"

  const valueCls = isProfit
    ? "text-[#10B981]"
    : isPurple
      ? "text-[#6366F1]"
      : isAmber
        ? "text-[#F59E0B]"
        : "text-foreground"

  const glowCls = isProfit
    ? "bg-[#10B981]/8"
    : isPurple
      ? "bg-[#6366F1]/8"
      : isAmber
        ? "bg-[#F59E0B]/8"
        : "bg-primary/5"

  const trendCls =
    kpi.trend === "up"
      ? "bg-[#10B981]/15 text-[#10B981]"
      : kpi.trend === "down"
        ? "bg-loss/12 text-loss"
        : "bg-muted text-muted-foreground"

  return (
    <div
      className="group relative overflow-hidden rounded-xl border border-border bg-card p-5 transition-all duration-300 hover:border-white/10 hover:shadow-lg"
    >
      {/* Ambient glow blob */}
      <div
        className={cn(
          "pointer-events-none absolute -right-8 -top-8 size-24 rounded-full blur-2xl transition-opacity duration-300 opacity-0 group-hover:opacity-100",
          glowCls,
        )}
      />

      <div className="flex items-start justify-between">
        <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {kpi.label}
        </p>
        <span
          className={cn(
            "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 font-mono text-[10px] font-medium",
            trendCls,
          )}
        >
          <TrendIcon className="size-3" />
          {kpi.delta}
        </span>
      </div>

      <p
        className={cn(
          "mt-3 font-mono text-3xl font-bold tracking-tight tabular-nums",
          valueCls,
        )}
      >
        {kpi.value}
      </p>
      <p className="mt-1.5 text-xs text-muted-foreground">{kpi.hint}</p>
    </div>
  )
}

// ─── Sub-component: EV Bar Chart (pure CSS/flex — no recharts) ────────────────
function EvBarChart() {
  const maxVal = Math.max(...evBarSeries.flatMap((p) => [Math.abs(p.actual), Math.abs(p.ev)]))

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <TrendingUp className="size-4 text-[#10B981]" />
            Expected Value — Weekly Breakdown
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Actual winnings vs all-in adjusted EV · Last 12 weeks
          </p>
        </div>
        <div className="hidden items-center gap-4 font-mono text-[10px] sm:flex">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <span className="size-2 rounded-full bg-[#10B981]" /> Actual
          </span>
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <span className="size-2 rounded-full bg-[#6366F1]" /> EV
          </span>
        </div>
      </div>

      {/* Chart area */}
      <div className="relative">
        {/* Zero baseline label */}
        <div className="absolute left-0 top-1/2 z-10 -translate-y-1/2">
          <span className="font-mono text-[9px] text-muted-foreground/60">0</span>
        </div>

        {/* Zero line */}
        <div className="absolute inset-x-6 top-1/2 h-px bg-border" />

        {/* Bars container */}
        <div className="flex items-end justify-around gap-1 pl-6" style={{ height: 220 }}>
          {evBarSeries.map((pt) => {
            const actualPct = (Math.abs(pt.actual) / maxVal) * 46 // 46% of half-height
            const evPct     = (Math.abs(pt.ev)     / maxVal) * 46
            const actualPos = pt.actual >= 0
            const evPos     = pt.ev     >= 0

            return (
              <div key={pt.week} className="group/bar flex flex-1 flex-col items-center gap-0.5">
                {/* Positive zone (top half) */}
                <div className="flex w-full flex-col items-center justify-end" style={{ height: "50%" }}>
                  <div className="flex w-full items-end justify-center gap-0.5">
                    {actualPos && (
                      <div
                        className="w-[42%] rounded-t-sm bg-[#10B981]/80 transition-all group-hover/bar:bg-[#10B981]"
                        style={{ height: `${actualPct}%` }}
                        title={`Actual: $${pt.actual.toLocaleString()}`}
                      />
                    )}
                    {evPos && (
                      <div
                        className="w-[42%] rounded-t-sm bg-[#6366F1]/60 transition-all group-hover/bar:bg-[#6366F1]/80"
                        style={{ height: `${evPct}%` }}
                        title={`EV: $${pt.ev.toLocaleString()}`}
                      />
                    )}
                    {/* Spacers for negative bars so columns stay aligned */}
                    {!actualPos && <div className="w-[42%]" />}
                    {!evPos     && <div className="w-[42%]" />}
                  </div>
                </div>

                {/* Negative zone (bottom half) */}
                <div className="flex w-full flex-col items-center justify-start" style={{ height: "50%" }}>
                  <div className="flex w-full items-start justify-center gap-0.5">
                    {!actualPos && (
                      <div
                        className="w-[42%] rounded-b-sm bg-[#FF3B3B]/70 transition-all group-hover/bar:bg-[#FF3B3B]/90"
                        style={{ height: `${actualPct}%` }}
                        title={`Actual: -$${Math.abs(pt.actual).toLocaleString()}`}
                      />
                    )}
                    {!evPos && (
                      <div
                        className="w-[42%] rounded-b-sm bg-[#F59E0B]/50 transition-all group-hover/bar:bg-[#F59E0B]/70"
                        style={{ height: `${evPct}%` }}
                        title={`EV: -$${Math.abs(pt.ev).toLocaleString()}`}
                      />
                    )}
                    {actualPos && <div className="w-[42%]" />}
                    {evPos     && <div className="w-[42%]" />}
                  </div>
                </div>

                {/* Week label */}
                <span className="mt-1 font-mono text-[9px] text-muted-foreground/70">
                  {pt.week}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Y-axis hint */}
      <p className="mt-3 text-right font-mono text-[9px] text-muted-foreground/50">
        USD / session week
      </p>
    </div>
  )
}

// ─── Sub-component: Top Leaks Table ──────────────────────────────────────────
function TopLeaksTable() {
  const worst = Math.abs(topLeaks[0].lostEv)

  return (
    <div className="flex flex-col rounded-xl border border-border bg-card overflow-hidden">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <AlertTriangle className="size-4 text-[#F59E0B]" />
        <div>
          <h2 className="text-sm font-semibold">Top Leaks</h2>
          <p className="text-[10px] text-muted-foreground">
            Biggest EV losses vs GTO benchmark
          </p>
        </div>
      </div>

      <ul className="flex flex-col divide-y divide-border">
        {topLeaks.map((leak, i) => (
          <li key={leak.id} className="group px-4 py-3 transition-colors hover:bg-muted/30">
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-start gap-2.5">
                {/* Row rank */}
                <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded bg-muted font-mono text-[10px] font-bold text-muted-foreground">
                  {i + 1}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-xs font-medium text-foreground">
                    {leak.spot}
                  </p>
                  <div className="mt-0.5 flex items-center gap-2">
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {leak.street}
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      ·
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {leak.hands.toLocaleString()} hands
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex shrink-0 flex-col items-end gap-1.5">
                <span
                  className={cn(
                    "font-mono text-sm font-bold tabular-nums text-[#FF3B3B]",
                  )}
                >
                  {leak.lostEv.toFixed(2)}
                </span>
                <span
                  className={cn(
                    "rounded-full border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide",
                    severityBadge[leak.severity],
                  )}
                >
                  {leak.severity}
                </span>
              </div>
            </div>

            {/* Progress bar relative to worst leak */}
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted">
              <div
                className={cn("h-full rounded-full transition-all", severityBar[leak.severity])}
                style={{ width: `${(Math.abs(leak.lostEv) / worst) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

// ─── Sub-component: Biggest Rivals ───────────────────────────────────────────
function BiggestRivals() {
  const worst = Math.abs(biggestRivals[0].net)

  const styleBadge: Record<string, string> = {
    TAG:    "border-[#6366F1]/40 text-[#6366F1]",
    LAG:    "border-[#F59E0B]/40 text-[#F59E0B]",
    Fish:   "border-[#10B981]/40 text-[#10B981]",
    Maniac: "border-[#FF3B3B]/40 text-[#FF3B3B]",
    Nit:    "border-muted-foreground/40 text-muted-foreground",
    Reg:    "border-[#A855F7]/40 text-[#A855F7]",
  }

  return (
    <div className="flex flex-col rounded-xl border border-border bg-card overflow-hidden">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Skull className="size-4 text-[#FF3B3B]" />
        <div>
          <h2 className="text-sm font-semibold">Biggest Rivals</h2>
          <p className="text-[10px] text-muted-foreground">
            Opponents taking the most from the hero
          </p>
        </div>
      </div>

      <ul className="flex flex-col gap-0 divide-y divide-border">
        {biggestRivals.map((rival, i) => (
          <li
            key={rival.alias}
            className="group flex flex-col gap-2 px-4 py-3.5 transition-colors hover:bg-muted/30"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                {/* Rank badge */}
                <span className="flex size-6 items-center justify-center rounded bg-[#FF3B3B]/15 font-mono text-[11px] font-bold text-[#FF3B3B]">
                  {i + 1}
                </span>
                <div>
                  <p className="font-mono text-sm font-semibold">{rival.alias}</p>
                  <p className="font-mono text-[10px] text-muted-foreground">
                    {rival.hands.toLocaleString()} hands
                  </p>
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <span className="font-mono text-base font-bold tabular-nums text-[#FF3B3B]">
                  {currency(rival.net)}
                </span>
                <span
                  className={cn(
                    "rounded-full border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide",
                    styleBadge[rival.style] ?? "border-border text-muted-foreground",
                  )}
                >
                  {rival.style}
                </span>
              </div>
            </div>

            {/* Loss bar */}
            <div className="h-1 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-[#FF3B3B]/60 transition-all group-hover:bg-[#FF3B3B]/80"
                style={{ width: `${(Math.abs(rival.net) / worst) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

// ─── Main Analytics View ──────────────────────────────────────────────────────
export function AnalyticsView() {
  return (
    <div className="flex flex-col gap-5">

      {/* ── Row 1: 4 KPI Cards ─────────────────────────────────────────────── */}
      <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {analyticsKpis.map((kpi) => (
          <AnalyticsKpiCard key={kpi.id} kpi={kpi} />
        ))}
      </section>

      {/* ── Row 2: EV Bar Chart (full width) ────────────────────────────────── */}
      <section>
        <EvBarChart />
      </section>

      {/* ── Row 3: Two-column base ──────────────────────────────────────────── */}
      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <TopLeaksTable />
        <BiggestRivals />
      </section>

    </div>
  )
}
