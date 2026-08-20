"use client"

import { useDashboard } from "@/hooks/useDashboard"
import type { DashboardFilters } from "@/lib/api.types"

import { cn } from "@/lib/utils"
import {
  currency,
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

// ─── Sub-component: EV Bar Chart (pure CSS — absolute px positioning) ────────
function EvBarChart() {
  // Total px height of the chart canvas (must match the style below)
  const CHART_H = 220
  // Each half (pos / neg zone) gets this many usable pixels
  const HALF_H  = 96

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

      {/* Chart canvas — relative anchor for absolute bars */}
      <div className="relative w-full overflow-hidden" style={{ height: CHART_H }}>

        {/* Zero-line + label */}
        <div
          className="absolute inset-x-0 h-px bg-border"
          style={{ top: HALF_H + 12 }}   // 12 px top padding
        />
        <span
          className="absolute left-0 font-mono text-[9px] text-muted-foreground/50"
          style={{ top: HALF_H + 12 - 7 }}
        >
          0
        </span>

        {/* Column grid — flex distributes columns evenly */}
        <div className="absolute inset-0 flex gap-1 px-1 pt-3">
          {evBarSeries.map((pt) => {
            const actualPx = Math.max(2, Math.round((Math.abs(pt.actual) / maxVal) * HALF_H))
            const evPx     = Math.max(2, Math.round((Math.abs(pt.ev)     / maxVal) * HALF_H))
            const aPos     = pt.actual >= 0
            const ePos     = pt.ev     >= 0
            // Zero-line sits at top = HALF_H + 12 (accounting for pt-3 = 12px)
            const zeroY    = HALF_H   // relative to the column div's top (pt-3 absorbed)

            return (
              <div
                key={pt.week}
                className="group/bar relative flex-1"
                style={{ height: CHART_H - 12 }}
              >
                {/* Actual bar — green (pos) or red (neg) */}
                <div
                  className={[
                    "absolute w-[44%] transition-all duration-200",
                    aPos
                      ? "rounded-t-sm bg-[#10B981]/80 group-hover/bar:bg-[#10B981]"
                      : "rounded-b-sm bg-[#FF3B3B]/70 group-hover/bar:bg-[#FF3B3B]/90",
                  ].join(" ")}
                  style={
                    aPos
                      ? { bottom: CHART_H - 12 - zeroY, height: actualPx, left: "4%" }
                      : { top:    zeroY + 1,             height: actualPx, left: "4%" }
                  }
                  title={`Actual: ${pt.actual >= 0 ? "" : "-"}$${Math.abs(pt.actual).toLocaleString()}`}
                />

                {/* EV bar — indigo (pos) or amber (neg) */}
                <div
                  className={[
                    "absolute w-[44%] transition-all duration-200",
                    ePos
                      ? "rounded-t-sm bg-[#6366F1]/60 group-hover/bar:bg-[#6366F1]/80"
                      : "rounded-b-sm bg-[#F59E0B]/50 group-hover/bar:bg-[#F59E0B]/70",
                  ].join(" ")}
                  style={
                    ePos
                      ? { bottom: CHART_H - 12 - zeroY, height: evPx, right: "4%" }
                      : { top:    zeroY + 1,             height: evPx, right: "4%" }
                  }
                  title={`EV: ${pt.ev >= 0 ? "" : "-"}$${Math.abs(pt.ev).toLocaleString()}`}
                />

                {/* Week label */}
                <span className="absolute bottom-0 left-1/2 -translate-x-1/2 font-mono text-[9px] text-muted-foreground/60">
                  {pt.week}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      <p className="mt-2 text-right font-mono text-[9px] text-muted-foreground/40">
        USD / session week · hover for tooltip
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
function BiggestRivals({ rivals }: { rivals: any[] }) {
  if (!rivals || rivals.length === 0) return null;
  const worst = Math.abs(rivals[0].net)

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
        {rivals.map((rival, i) => (
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
                {rival.net_usd !== undefined ? (
                  <div className="flex flex-col items-end gap-0">
                    {rival.net_usd !== 0 && (
                      <span className="font-mono text-base font-bold tabular-nums text-[#FF3B3B]">
                        {currency(rival.net_usd)}
                      </span>
                    )}
                    {rival.net_chips !== 0 && (
                      <span className="font-mono text-[10px] font-medium tabular-nums text-[#FF3B3B]/80">
                        {Math.round(rival.net_chips || 0).toLocaleString()} chips
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="font-mono text-base font-bold tabular-nums text-[#FF3B3B]">
                    {currency(rival.net)}
                  </span>
                )}
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

// ─── Main View ────────────────────────────────────────────────────────────────
export function AnalyticsView({ filters }: { filters?: DashboardFilters }) {
  const { analytics, biggestRivals: liveRivals, loading, error } = useDashboard(filters ?? {})

  const liveKpis = analytics ? [
    {
      id: "wwsf",
      label: "WWSF (Won When Saw Flop)",
      value: `${analytics.wwsf_pct}%`,
      trend: analytics.wwsf_pct > 45 ? "up" : "down",
      delta: analytics.wwsf_pct > 45 ? "Good" : "Leak",
      hint: "Ideal: > 45%",
    },
    {
      id: "wtsd",
      label: "WTSD (Went to Showdown)",
      value: `${analytics.wtsd_pct}%`,
      trend: (analytics.wtsd_pct >= 28 && analytics.wtsd_pct <= 32) ? "up" : "down",
      delta: (analytics.wtsd_pct >= 28 && analytics.wtsd_pct <= 32) ? "Optimal" : "Leak",
      hint: "Ideal: 28% - 32%",
    },
    {
      id: "wssd",
      label: "W$SD (Won $ at Showdown)",
      value: `${analytics.wssd_pct}%`,
      trend: analytics.wssd_pct >= 50 ? "up" : "down",
      delta: analytics.wssd_pct >= 50 ? "Winning" : "Bleeding",
      hint: "Ideal: > 50%",
    },
    {
      id: "red_line",
      label: "Red Line (Non-Showdown)",
      value: (analytics.red_line_profit !== 0 || analytics.red_line_chips === 0) 
             ? `$${analytics.red_line_profit.toFixed(2)}` 
             : `${Math.round(analytics.red_line_chips).toLocaleString()} chips`,
      trend: (analytics.red_line_profit >= 0 || analytics.red_line_chips >= 0) ? "up" : "down",
      delta: (analytics.red_line_profit >= 0 || analytics.red_line_chips >= 0) ? "Aggressive" : "Passive",
      hint: "Profit won before SD",
    }
  ] : [];

  return (
    <div className="flex flex-col gap-5">

      {/* ── Row 1: 4 KPI Cards ─────────────────────────────────────────────── */}
      <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {liveKpis.map((kpi) => (
          <AnalyticsKpiCard key={kpi.id} kpi={kpi as any} />
        ))}
      </section>

      {/* ── Row 2: EV Bar Chart (full width) ────────────────────────────────── */}
      <section>
        {/* TODO: Implementar extração de EV real no Parser/Loader ETL 
            (Atualmente oculto pois usava Mock Data com valores absurdos de EV)
        <EvBarChart />
        */}
      </section>

      {/* ── Row 3: Two-column base ──────────────────────────────────────────── */}
      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {/* TODO: Implementar Machine Learning de Leaks vs GTO Benchmark
        <TopLeaksTable />
        */}
        <BiggestRivals rivals={liveRivals || []} />
      </section>

    </div>
  )
}
