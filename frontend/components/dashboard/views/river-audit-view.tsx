"use client"

import { useEffect, useState } from "react"
import { fetchRiverAudit } from "@/lib/api"
import type { DashboardFilters, RiverAuditResponse } from "@/lib/api.types"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { currency } from "@/lib/poker-data"
import { cn } from "@/lib/utils"
import { HandViewer } from "@/components/dashboard/hand-viewer"
import { Anchor, ArrowDownRight, ArrowUpRight, Ban, CheckCircle2, ShieldCheck, Waves, ExternalLink } from "lucide-react"

export function RiverAuditView({
  filters,
}: {
  filters?: DashboardFilters
  setFilters?: (f: DashboardFilters) => void
  setView?: (v: string) => void
}) {
  const [data, setData] = useState<RiverAuditResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedHandId, setSelectedHandId] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    fetchRiverAudit(filters)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filters])

  if (loading) {
    return <div className="flex h-64 items-center justify-center text-sm text-muted-foreground animate-pulse">Calculating River EV...</div>
  }

  if (!data) return null

  const { summary, hero_bets, hero_calls } = data

  const isPositiveLeak = summary.net_leak < 0 // missed value - saved money

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="flex size-10 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-500">
          <Waves className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold tracking-tight">River Audit</h2>
          <p className="text-sm text-muted-foreground">Bet sizing EV and Call efficiency</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <ArrowUpRight className="size-4 text-emerald-500" />
            <h3 className="text-xs font-semibold uppercase tracking-wider">Saved Money</h3>
          </div>
          <p className="font-mono text-2xl font-bold text-emerald-400">{currency(summary.saved_money)}</p>
          <p className="text-xs text-muted-foreground mt-1">Value saved by checking or folding correctly</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <ArrowDownRight className="size-4 text-rose-500" />
            <h3 className="text-xs font-semibold uppercase tracking-wider">Missed Value</h3>
          </div>
          <p className="font-mono text-2xl font-bold text-rose-400">{currency(summary.missed_value)}</p>
          <p className="text-xs text-muted-foreground mt-1">Value lost by betting too small</p>
        </div>

        <div className={cn(
          "rounded-xl border p-5 relative overflow-hidden",
          isPositiveLeak ? "bg-emerald-500/10 border-emerald-500/30" : "bg-rose-500/10 border-rose-500/30"
        )}>
          <div className="flex items-center gap-2 text-muted-foreground mb-2 relative z-10">
            <Anchor className={cn("size-4", isPositiveLeak ? "text-emerald-500" : "text-rose-500")} />
            <h3 className={cn("text-xs font-semibold uppercase tracking-wider", isPositiveLeak ? "text-emerald-500" : "text-rose-500")}>
              Net River Leak
            </h3>
          </div>
          <p className={cn("font-mono text-2xl font-bold relative z-10", isPositiveLeak ? "text-emerald-400" : "text-rose-400")}>
            {isPositiveLeak ? "+" : ""}{currency(-summary.net_leak)}
          </p>
          <p className="text-xs text-muted-foreground mt-1 relative z-10">Overall impact on your bankroll</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        
        {/* River Bets */}
        <section className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="border-b border-border px-5 py-4">
            <h3 className="font-semibold">River Bets (EV vs 75% Pot)</h3>
            <p className="text-xs text-muted-foreground mt-1">Were you conservative, optimal or did you over-extract?</p>
          </div>
          <div className="overflow-x-auto max-h-[400px] scrollbar-thin">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead className="text-xs pl-5">Hand ID</TableHead>
                  <TableHead className="text-right text-xs">Sizing</TableHead>
                  <TableHead className="text-right text-xs">Diff (USD)</TableHead>
                  <TableHead className="text-right text-xs pr-5">Impact</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {hero_bets.length > 0 ? hero_bets.map((bet) => (
                  <TableRow key={bet.hand_id} className="border-border/50 transition-colors">
                    <TableCell className="pl-5">
                      <button
                        onClick={() => setSelectedHandId(bet.hand_id)}
                        className="group/btn flex items-center gap-1.5 font-mono text-xs text-primary transition-colors hover:text-primary/80"
                      >
                        <span>{bet.hand_id.split("-")[0] ?? bet.hand_id}</span>
                        <ExternalLink className="size-3 opacity-0 transition-opacity group-hover/btn:opacity-100" />
                      </button>
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs font-medium">
                      {bet.sizing_pct}%
                    </TableCell>
                    <TableCell className={cn(
                      "text-right font-mono text-xs",
                      bet.diferenca_dolares > 0 ? "text-emerald-400" : bet.diferenca_dolares < 0 ? "text-rose-400" : "text-muted-foreground"
                    )}>
                      {bet.diferenca_dolares > 0 ? "+" : ""}{currency(bet.diferenca_dolares)}
                    </TableCell>
                    <TableCell className="text-right pr-5">
                      <span className={cn(
                        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase",
                        bet.impacto_no_caixa === "Optimal" ? "bg-zinc-800 text-zinc-300" :
                        bet.impacto_no_caixa === "Missed Value" ? "bg-amber-500/20 text-amber-500" :
                        bet.impacto_no_caixa === "Saved" ? "bg-emerald-500/20 text-emerald-500" :
                        bet.impacto_no_caixa === "Max Extraction" ? "bg-blue-500/20 text-blue-500" :
                        bet.impacto_no_caixa === "All-In" ? "bg-purple-500/20 text-purple-500" :
                        "bg-rose-500/20 text-rose-500" // Wasted
                      )}>
                        {bet.impacto_no_caixa}
                      </span>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={4} className="h-24 text-center text-sm text-muted-foreground">
                      No river bets found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </section>

        {/* River Calls */}
        <section className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="border-b border-border px-5 py-4">
            <h3 className="font-semibold">River Calls</h3>
            <p className="text-xs text-muted-foreground mt-1">Hero Calls vs Crying Calls</p>
          </div>
          <div className="overflow-x-auto max-h-[400px] scrollbar-thin">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead className="text-xs pl-5">Hand ID</TableHead>
                  <TableHead className="text-right text-xs">Call Amount</TableHead>
                  <TableHead className="text-right text-xs pr-5">Result</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {hero_calls.length > 0 ? hero_calls.map((call) => (
                  <TableRow key={call.hand_id} className="border-border/50 transition-colors">
                    <TableCell className="pl-5">
                      <button
                        onClick={() => setSelectedHandId(call.hand_id)}
                        className="group/btn flex items-center gap-1.5 font-mono text-xs text-primary transition-colors hover:text-primary/80"
                      >
                        <span>{call.hand_id.split("-")[0] ?? call.hand_id}</span>
                        <ExternalLink className="size-3 opacity-0 transition-opacity group-hover/btn:opacity-100" />
                      </button>
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs font-medium">
                      {currency(call.valor_do_call)}
                    </TableCell>
                    <TableCell className="text-right pr-5">
                      <div className="flex justify-end">
                        {call.resultado === "Hero Call" ? (
                          <div className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-emerald-500">
                            <ShieldCheck className="size-3" />
                            <span className="text-[10px] font-semibold uppercase tracking-wide">Hero Call</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 rounded-full bg-rose-500/10 px-2 py-0.5 text-rose-500">
                            <Ban className="size-3" />
                            <span className="text-[10px] font-semibold uppercase tracking-wide">Crying Call</span>
                          </div>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={3} className="h-24 text-center text-sm text-muted-foreground">
                      No river calls found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </section>

      </div>

      {selectedHandId && (
        <HandViewer handId={selectedHandId} onClose={() => setSelectedHandId(null)} />
      )}
    </div>
  )
}
