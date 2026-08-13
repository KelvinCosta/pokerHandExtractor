"use client"

import { useMemo, useState } from "react"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { currency, type Villain } from "@/lib/poker-data"
import { cn } from "@/lib/utils"
import { ArrowDown, ArrowUp, ChevronsUpDown, Skull } from "lucide-react"
import { useDashboard } from "@/hooks/useDashboard"
import type { DashboardFilters } from "@/lib/api.types"
import { getVillainTag, saveVillainTag } from "@/lib/api"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useEffect } from "react"

type SortKey = keyof Pick<Villain, "hands" | "net" | "vpip" | "pfr">

// Color systems for villain archetypes
const STYLE_BADGE: Record<Villain["style"], string> = {
  TAG:    "border-sky-500/40 bg-sky-500/10 text-sky-400",
  LAG:    "border-amber-500/40 bg-amber-500/10 text-amber-400",
  Nit:    "border-zinc-500/40 bg-zinc-700/40 text-zinc-400",
  Fish:   "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
  Reg:    "border-violet-500/40 bg-violet-500/10 text-violet-400",
  Maniac: "border-rose-500/40 bg-rose-500/10 text-rose-400",
}
const STYLE_ROW: Record<Villain["style"], string> = {
  TAG:    "",
  LAG:    "",
  Nit:    "",
  Fish:   "bg-emerald-500/3",
  Reg:    "",
  Maniac: "bg-rose-500/3",
}

// Avatar initials background per style
const STYLE_AVATAR: Record<Villain["style"], string> = {
  TAG:    "bg-sky-500/20 text-sky-400",
  LAG:    "bg-amber-500/20 text-amber-400",
  Nit:    "bg-zinc-700/60 text-zinc-400",
  Fish:   "bg-emerald-500/20 text-emerald-400",
  Reg:    "bg-violet-500/20 text-violet-400",
  Maniac: "bg-rose-500/20 text-rose-400",
}

const columns: { key: SortKey; label: string; fmt: (v: Villain) => string }[] = [
  { key: "hands",    label: "Hands",  fmt: (v) => v.hands.toLocaleString() },
  { key: "vpip",     label: "VPIP",   fmt: (v) => `${v.vpip}%` },
  { key: "pfr",      label: "PFR",    fmt: (v) => `${v.pfr}%` },
]

export function VillainsView({
  filters,
  setFilters,
  setView,
}: {
  filters?: DashboardFilters
  setFilters?: (f: DashboardFilters) => void
  setView?: (v: string) => void
}) {
  const { biggestRivals } = useDashboard(filters ?? {})
  const villains = (biggestRivals ?? []) as Villain[]

  const [sortKey, setSortKey] = useState<SortKey>("net")
  const [asc, setAsc]         = useState(true)

  const sorted = useMemo(
    () => [...villains].sort((a, b) => (asc ? a[sortKey] - b[sortKey] : b[sortKey] - a[sortKey])),
    [villains, sortKey, asc],
  )

  const rivals = useMemo(
    () => [...villains].filter((v) => v.net < 0).sort((a, b) => a.net - b.net).slice(0, 5),
    [villains],
  )
  const worst = Math.abs(rivals[0]?.net ?? 1)

  const toggle = (key: SortKey) => {
    if (key === sortKey) setAsc((v) => !v)
    else { setSortKey(key); setAsc(false) }
  }

  const handleVillainClick = (alias: string) => {
    if (setFilters) setFilters({ ...filters, search_query: alias })
    if (setView)    setView("bigpots")
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">

      {/* ── Opponent pool table ────────────────────────────────────────────── */}
      <section className="rounded-xl border border-border bg-card xl:col-span-2 overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <div>
            <h2 className="text-sm font-semibold">Opponent Pool</h2>
            <p className="text-xs text-muted-foreground">{villains.length} tracked villains · sortable</p>
          </div>
        </div>

        <div className="overflow-x-auto scrollbar-thin">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="pl-5">Villain</TableHead>
                <TableHead>
                  <SortBtn label="Net vs Hero" active={sortKey === "net"} asc={asc} onClick={() => toggle("net")} />
                </TableHead>
                {columns.map((c) => (
                  <TableHead key={c.key} className="hidden md:table-cell">
                    <SortBtn label={c.label} active={sortKey === c.key} asc={asc} onClick={() => toggle(c.key)} />
                  </TableHead>
                ))}
                <TableHead className="pr-5 text-right">Reads</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {sorted.map((v) => (
                <TableRow
                  key={v.id}
                  className={cn(
                    "group cursor-pointer border-border transition-colors hover:bg-muted/40",
                    STYLE_ROW[v.style],
                  )}
                  onClick={() => handleVillainClick(v.alias)}
                >
                  {/* Villain identity */}
                  <TableCell className="pl-5">
                    <div className="flex items-center gap-2.5">
                      {/* Avatar */}
                      <div className={cn(
                        "flex size-7 shrink-0 items-center justify-center rounded-lg font-mono text-[10px] font-bold",
                        STYLE_AVATAR[v.style],
                      )}>
                        {v.alias.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-mono text-sm font-medium">{v.alias}</p>
                        <span className={cn(
                          "rounded-full border px-1.5 py-px font-mono text-[9px] font-semibold uppercase tracking-wide",
                          STYLE_BADGE[v.style],
                        )}>
                          {v.style}
                        </span>
                      </div>
                    </div>
                  </TableCell>

                  {/* Net */}
                  <TableCell>
                    <div className="flex flex-col gap-0 items-start">
                      {v.net_usd !== undefined ? (
                        <>
                          {v.net_usd !== 0 && (
                            <span className={cn(
                              "font-mono text-sm font-bold tabular-nums",
                              v.net_usd < 0 ? "text-[#FF3B3B]" : "text-[#10B981]",
                            )}>
                              {v.net_usd < 0 ? "" : "+"}{currency(v.net_usd)}
                            </span>
                          )}
                          {v.net_chips !== 0 && (
                            <span className={cn(
                              "font-mono text-[10px] font-medium tabular-nums",
                              v.net_chips !== undefined && v.net_chips < 0 ? "text-[#FF3B3B]/80" : "text-[#10B981]/80",
                            )}>
                              {v.net_chips !== undefined && v.net_chips < 0 ? "" : "+"}{Math.round(v.net_chips || 0).toLocaleString()} chips
                            </span>
                          )}
                          {v.net_usd === 0 && v.net_chips === 0 && (
                            <span className="font-mono text-sm font-bold tabular-nums text-muted-foreground">$0</span>
                          )}
                        </>
                      ) : (
                        <span className={cn(
                          "font-mono text-sm font-bold tabular-nums",
                          v.net < 0 ? "text-[#FF3B3B]" : "text-[#10B981]",
                        )}>
                          {v.net < 0 ? "" : "+"}{currency(v.net)}
                        </span>
                      )}
                    </div>
                  </TableCell>

                  {/* Stats */}
                  {columns.map((c) => (
                    <TableCell key={c.key} className="hidden font-mono text-xs tabular-nums text-muted-foreground md:table-cell">
                      {c.fmt(v)}
                    </TableCell>
                  ))}

                  {/* Tags */}
                  <TableCell className="pr-5 text-right">
                    <VillainTagsEditor alias={v.alias} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>

      {/* ── Rivalry Board ─────────────────────────────────────────────────── */}
      <section className="rounded-xl border border-border bg-card p-5">
        <div className="mb-4 flex items-center gap-2">
          <Skull className="size-4 text-[#FF3B3B]" />
          <div>
            <h2 className="text-sm font-semibold">Rivalry Board</h2>
            <p className="text-[10px] text-muted-foreground">Opponents draining the most EV</p>
          </div>
        </div>

        <ul className="flex flex-col gap-3">
          {rivals.map((v, i) => (
            <li
              key={v.id}
              className="group relative cursor-pointer overflow-hidden rounded-xl border border-border bg-zinc-900/50 p-3.5 transition-all duration-200 hover:border-rose-500/20 hover:bg-rose-500/5"
              onClick={() => handleVillainClick(v.alias)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  {/* Rank */}
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-[#FF3B3B]/15 font-mono text-[11px] font-bold text-[#FF3B3B]">
                    {i + 1}
                  </span>
                  {/* Avatar */}
                  <div className={cn(
                    "flex size-8 shrink-0 items-center justify-center rounded-lg font-mono text-sm font-bold",
                    STYLE_AVATAR[v.style],
                  )}>
                    {v.alias.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <p className="font-mono text-sm font-semibold">{v.alias}</p>
                    <p className="font-mono text-[9px] text-muted-foreground">{v.hands.toLocaleString()} hands</p>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-1">
                  {v.net_usd !== undefined ? (
                    <div className="flex flex-col items-end gap-0">
                      {v.net_usd !== 0 && (
                        <span className="font-mono text-base font-bold tabular-nums text-[#FF3B3B]">
                          {currency(v.net_usd)}
                        </span>
                      )}
                      {v.net_chips !== 0 && (
                        <span className="font-mono text-[10px] font-medium tabular-nums text-[#FF3B3B]/80">
                          {Math.round(v.net_chips || 0).toLocaleString()} chips
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="font-mono text-base font-bold tabular-nums text-[#FF3B3B]">
                      {currency(v.net)}
                    </span>
                  )}
                  <span className={cn(
                    "rounded-full border px-1.5 py-px font-mono text-[9px] uppercase tracking-wide",
                    STYLE_BADGE[v.style],
                  )}>
                    {v.style}
                  </span>
                </div>
              </div>

              {/* Loss bar */}
              <div className="mt-3 h-1 overflow-hidden rounded-full bg-zinc-800">
                <div
                  className="h-full rounded-full bg-[#FF3B3B]/60 transition-all duration-500 group-hover:bg-[#FF3B3B]/80"
                  style={{ width: `${(Math.abs(v.net) / worst) * 100}%` }}
                />
              </div>

              {/* Tags */}
              {v.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {v.tags.map((t) => (
                    <span key={t} className="rounded-full bg-zinc-800/80 px-1.5 py-0.5 font-mono text-[9px] text-zinc-500">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </li>
          ))}

          {rivals.length === 0 && (
            <p className="py-6 text-center text-xs text-muted-foreground">No rivalry data yet.</p>
          )}
        </ul>
      </section>
    </div>
  )
}

function SortBtn({ label, active, asc, onClick }: {
  label: string; active: boolean; asc: boolean; onClick: () => void
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
      {active
        ? asc ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />
        : <ChevronsUpDown className="size-3 opacity-40" />}
    </button>
  )
}

function VillainTagsEditor({ alias }: { alias: string }) {
  const [note, setNote] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(false)
  
  useEffect(() => {
    getVillainTag(alias).then(r => setNote(r.note)).catch(() => {})
  }, [alias])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await saveVillainTag(alias, note || "")
      setEditing(false)
    } finally {
      setLoading(false)
    }
  }

  if (editing) {
    return (
      <form onSubmit={handleSave} className="flex items-center justify-end gap-2" onClick={e => e.stopPropagation()}>
        <Input 
          autoFocus
          value={note || ""} 
          onChange={e => setNote(e.target.value)}
          className="h-6 w-32 text-xs bg-black/50 font-mono" 
          placeholder="Tag/Note..."
          disabled={loading}
        />
        <Button type="submit" size="sm" variant="outline" className="h-6 px-2 text-xs font-mono" disabled={loading}>
          Save
        </Button>
      </form>
    )
  }

  return (
    <div 
      className="flex flex-wrap justify-end gap-1 min-h-6 min-w-[50px] cursor-text"
      onClick={(e) => { e.stopPropagation(); setEditing(true) }}
    >
      {note ? (
        <span className="rounded-full bg-zinc-800/80 px-2 py-0.5 font-mono text-[10px] text-zinc-300 border border-border">
          {note}
        </span>
      ) : (
        <span className="text-[10px] font-mono text-muted-foreground/50 opacity-0 group-hover:opacity-100 transition-opacity">
          Click to add note
        </span>
      )}
    </div>
  )
}
