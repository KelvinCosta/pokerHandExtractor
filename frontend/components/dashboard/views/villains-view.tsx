"use client"

import { useMemo, useState } from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { currency, type Villain } from "@/lib/poker-data"
import { cn } from "@/lib/utils"
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react"
import { useDashboard } from "@/hooks/useDashboard"
import type { DashboardFilters } from "@/lib/api.types"

type SortKey = keyof Pick<Villain, "hands" | "net" | "vpip" | "pfr" | "threeBet" | "wtsd">

const styleColor: Record<Villain["style"], string> = {
  TAG: "border-chart-2/40 text-chart-2",
  LAG: "border-warning/40 text-warning",
  Nit: "border-muted-foreground/40 text-muted-foreground",
  Fish: "border-primary/40 text-primary",
  Reg: "border-chart-5/40 text-chart-5",
  Maniac: "border-loss/40 text-loss",
}

const columns: { key: SortKey; label: string; fmt: (v: Villain) => string }[] = [
  { key: "hands", label: "Hands", fmt: (v) => v.hands.toLocaleString() },
  { key: "vpip", label: "VPIP", fmt: (v) => `${v.vpip}%` },
  { key: "pfr", label: "PFR", fmt: (v) => `${v.pfr}%` },
  { key: "threeBet", label: "3-Bet", fmt: (v) => `${v.threeBet}%` },
  { key: "wtsd", label: "WTSD", fmt: (v) => `${v.wtsd}%` },
]

export function VillainsView({ filters, setFilters, setView }: { filters?: DashboardFilters, setFilters?: (f: DashboardFilters) => void, setView?: (v: string) => void }) {
  const { biggestRivals, loading } = useDashboard(filters ?? {})
  const villains = biggestRivals ?? []
  
  const [sortKey, setSortKey] = useState<SortKey>("net")
  const [asc, setAsc] = useState(true)

  const sorted = useMemo(() => {
    return [...villains].sort((a, b) => (asc ? a[sortKey] - b[sortKey] : b[sortKey] - a[sortKey]))
  }, [villains, sortKey, asc])

  // Rivalry ranking = villains who took the most money (most negative net)
  const rivals = useMemo(
    () => [...villains].filter((v) => v.net < 0).sort((a, b) => a.net - b.net).slice(0, 4),
    [villains],
  )
  const worst = Math.abs(rivals[0]?.net ?? 1)

  const toggle = (key: SortKey) => {
    if (key === sortKey) setAsc((v) => !v)
    else {
      setSortKey(key)
      setAsc(false)
    }
  }

  const handleVillainClick = (alias: string) => {
    if (setFilters) setFilters({ ...filters, search_query: alias })
    if (setView) setView("bigpots")
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <section className="rounded-lg border border-border bg-card xl:col-span-2">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold">Opponent Pool</h2>
            <p className="text-xs text-muted-foreground">{villains.length} tracked villains · sortable</p>
          </div>
        </div>
        <div className="overflow-x-auto scrollbar-thin">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-4">Villain</TableHead>
                <TableHead>
                  <SortBtn label="Net vs Hero" active={sortKey === "net"} asc={asc} onClick={() => toggle("net")} />
                </TableHead>
                {columns.map((c) => (
                  <TableHead key={c.key} className="hidden md:table-cell">
                    <SortBtn label={c.label} active={sortKey === c.key} asc={asc} onClick={() => toggle(c.key)} />
                  </TableHead>
                ))}
                <TableHead className="pr-4 text-right">Reads</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((v) => (
                <TableRow key={v.id} className="group cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => handleVillainClick(v.alias)}>
                  <TableCell className="pl-4">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-medium">{v.alias}</span>
                      <Badge variant="outline" className={cn("h-5 px-1.5 text-[10px]", styleColor[v.style])}>
                        {v.style}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span
                      className={cn(
                        "font-mono text-sm font-semibold tabular-nums",
                        v.net < 0 ? "text-loss" : "text-primary",
                      )}
                    >
                      {v.net < 0 ? "" : "+"}
                      {currency(v.net)}
                    </span>
                  </TableCell>
                  {columns.map((c) => (
                    <TableCell key={c.key} className="hidden font-mono text-xs tabular-nums text-muted-foreground md:table-cell">
                      {c.fmt(v)}
                    </TableCell>
                  ))}
                  <TableCell className="pr-4 text-right">
                    <div className="flex flex-wrap justify-end gap-1">
                      {v.tags.slice(0, 2).map((t) => (
                        <span
                          key={t}
                          className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-semibold">Rivalry Board</h2>
        <p className="mb-4 text-xs text-muted-foreground">Opponents taking the most from the hero</p>
        <ul className="flex flex-col gap-3">
          {rivals.map((v, i) => (
            <li key={v.id} className="rounded-md border border-border bg-background/40 p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex size-5 items-center justify-center rounded bg-loss/15 font-mono text-[11px] font-bold text-loss">
                    {i + 1}
                  </span>
                  <span className="font-mono text-sm font-medium">{v.alias}</span>
                </div>
                <span className="font-mono text-sm font-semibold tabular-nums text-loss">
                  {currency(v.net)}
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-loss/70"
                  style={{ width: `${(Math.abs(v.net) / worst) * 100}%` }}
                />
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {v.tags.map((t) => (
                  <span key={t} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                    {t}
                  </span>
                ))}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function SortBtn({
  label,
  active,
  asc,
  onClick,
}: {
  label: string
  active: boolean
  asc: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1 font-medium transition-colors hover:text-foreground",
        active ? "text-foreground" : "text-muted-foreground",
      )}
    >
      {label}
      {active ? (
        asc ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />
      ) : (
        <ChevronsUpDown className="size-3 opacity-50" />
      )}
    </button>
  )
}
