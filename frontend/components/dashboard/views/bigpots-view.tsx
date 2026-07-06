"use client"

import { useState } from "react"
import { useDashboard } from "@/hooks/useDashboard"
import type { DashboardFilters } from "@/lib/api.types"
import { HandViewer } from "@/components/dashboard/hand-viewer"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { bigHands, currency } from "@/lib/poker-data"
import { cn } from "@/lib/utils"

const suitColor = (card: string) =>
  card.includes("♥") || card.includes("♦") ? "text-loss" : "text-foreground"

function Cards({ str }: { str: string }) {
  return (
    <span className="flex flex-wrap gap-1 font-mono text-sm">
      {str.split(" ").map((c, i) => (
        <span
          key={i}
          className={cn(
            "inline-flex min-w-6 items-center justify-center rounded border border-border bg-background px-1 py-0.5 text-xs",
            suitColor(c),
          )}
        >
          {c}
        </span>
      ))}
    </span>
  )
}

export function BigPotsView({ filters }: { filters?: DashboardFilters }) {
  const { bigPots, loading, error } = useDashboard(filters ?? {})
  const displayHands = bigPots || []
  
  const [selectedHandId, setSelectedHandId] = useState<string | null>(null)

  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-4">
        
        <div className="rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold">Big Pot Audit</h2>
              <p className="text-xs text-muted-foreground">High-value hands (200bb+) &amp; river decisions</p>
            </div>
            <span className="hidden font-mono text-[10px] uppercase tracking-widest text-muted-foreground sm:inline">
              {displayHands.length} flagged
            </span>
          </div>
          <div className="overflow-x-auto scrollbar-thin">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-4">Hand ID</TableHead>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Pot (BB)</TableHead>
                  <TableHead className="pr-4 text-right">Result (USD)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayHands.length === 0 ? (
                   <TableRow>
                     <TableCell colSpan={4} className="text-center text-muted-foreground h-24">Nenhuma mão grande encontrada.</TableCell>
                   </TableRow>
                ) : (
                  displayHands.map((h) => (
                    <TableRow key={h.hand_id}>
                      <TableCell className="pl-4">
                        <button 
                          onClick={() => setSelectedHandId(h.hand_id)}
                          className="font-mono text-xs text-primary transition-colors hover:text-primary/80 hover:underline"
                        >
                          {h.hand_id.split("-")[0]}
                        </button>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {new Date(h.timestamp).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                        {(h.pot_in_bb ?? 0).toFixed(1)}bb
                      </TableCell>
                      <TableCell className="pr-4 text-right">
                        <span
                          className={cn(
                            "font-mono text-sm font-semibold tabular-nums",
                            h.net_profit > 0 ? "text-primary" : "text-loss",
                          )}
                        >
                          {h.net_profit < 0 ? "" : "+"}
                          {currency(h.net_profit)}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </section>

      {/* Modal View */}
      {selectedHandId && (
        <HandViewer handId={selectedHandId} onClose={() => setSelectedHandId(null)} />
      )}
    </div>
  )
}
