"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { bigHands, currency, riverDecisions } from "@/lib/poker-data"
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

export function BigPotsView() {
  const maxEv = Math.max(...riverDecisions.map((d) => Math.abs(d.evPerBB)))

  return (
    <div className="flex flex-col gap-4">
      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold">River Decision EV</h2>
          <p className="mb-4 text-xs text-muted-foreground">Expected value per big blind by action type</p>
          <ul className="flex flex-col gap-3">
            {riverDecisions.map((d) => {
              const positive = d.evPerBB >= 0
              return (
                <li key={d.action}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="font-medium">{d.action}</span>
                    <span className="font-mono text-[11px] text-muted-foreground">{d.count.toLocaleString()} spots</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="relative h-2 flex-1 rounded-full bg-muted">
                      <div
                        className={cn(
                          "absolute inset-y-0 rounded-full",
                          positive ? "left-1/2 bg-primary/80" : "right-1/2 bg-loss/80",
                        )}
                        style={{ width: `${(Math.abs(d.evPerBB) / maxEv) * 50}%` }}
                      />
                      <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
                    </div>
                    <span
                      className={cn(
                        "w-12 text-right font-mono text-xs font-semibold tabular-nums",
                        positive ? "text-primary" : "text-loss",
                      )}
                    >
                      {positive ? "+" : ""}
                      {d.evPerBB.toFixed(2)}
                    </span>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>

        <div className="rounded-lg border border-border bg-card xl:col-span-2">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold">Big Pot Audit</h2>
              <p className="text-xs text-muted-foreground">High-value hands (200bb+) &amp; river decisions</p>
            </div>
            <span className="hidden font-mono text-[10px] uppercase tracking-widest text-muted-foreground sm:inline">
              {bigHands.length} flagged
            </span>
          </div>
          <div className="overflow-x-auto scrollbar-thin">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-4">Hand</TableHead>
                  <TableHead className="hidden md:table-cell">Board</TableHead>
                  <TableHead>Pot</TableHead>
                  <TableHead>River</TableHead>
                  <TableHead className="hidden sm:table-cell">vs</TableHead>
                  <TableHead className="pr-4 text-right">Result</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {bigHands.map((h) => (
                  <TableRow key={h.id}>
                    <TableCell className="pl-4">
                      <Cards str={h.hand} />
                      <span className="mt-1 block font-mono text-[10px] text-muted-foreground">
                        {h.position} · {h.stake}
                      </span>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      <Cards str={h.board} />
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                      {h.potBB}bb
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[10px]",
                          h.riverAction === "Bluff" && "border-warning/40 text-warning",
                          h.riverAction === "Value Bet" && "border-primary/40 text-primary",
                        )}
                      >
                        {h.riverAction}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden font-mono text-xs text-muted-foreground sm:table-cell">
                      {h.villain}
                    </TableCell>
                    <TableCell className="pr-4 text-right">
                      <span
                        className={cn(
                          "font-mono text-sm font-semibold tabular-nums",
                          h.result === "won" ? "text-primary" : "text-loss",
                        )}
                      >
                        {h.netUSD < 0 ? "" : "+"}
                        {currency(h.netUSD)}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </section>
    </div>
  )
}
