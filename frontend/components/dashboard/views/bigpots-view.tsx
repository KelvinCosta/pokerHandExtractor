"use client"

import { useState, useEffect, useRef } from "react"
import type { DashboardFilters, HandsListResponse } from "@/lib/api.types"
import { fetchHandsList } from "@/lib/api"
import { HandViewer } from "@/components/dashboard/hand-viewer"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { currency } from "@/lib/poker-data"
import { ArrowDownIcon, ArrowUpIcon, ChevronLeft, ChevronRight, ChevronsUpDown, ExternalLink } from "lucide-react"

const PAGE_SIZE = 20

export function BigPotsView({ filters }: { filters?: DashboardFilters }) {
  const [data, setData]         = useState<HandsListResponse | null>(null)
  const [loading, setLoading]   = useState(false)
  const [page, setPage]         = useState(1)
  const [sortBy, setSortBy]     = useState<string>("timestamp")
  const [sortDesc, setSortDesc] = useState<boolean>(true)
  const [selectedHandId, setSelectedHandId] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Reset to page 1 on filter change
  useEffect(() => { setPage(1) }, [filters])

  useEffect(() => {
    let cancelled = false
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const load = async () => {
      setLoading(true)
      try {
        const response = await fetchHandsList(
          { ...filters, page, limit: PAGE_SIZE, sort_by: sortBy, sort_desc: sortDesc },
          controller.signal,
        )
        if (!cancelled) setData(response)
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    const timer = setTimeout(load, 300)
    return () => { cancelled = true; clearTimeout(timer); controller.abort() }
  }, [filters, page, sortBy, sortDesc])

  const hands      = data?.data ?? []
  const totalItems = data?.total ?? 0
  const totalPages = Math.ceil(totalItems / PAGE_SIZE)

  const handleSort = (col: string) => {
    if (sortBy === col) setSortDesc((d) => !d)
    else { setSortBy(col); setSortDesc(true) }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-xl border border-border bg-card overflow-hidden">

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <div>
            <h2 className="text-sm font-semibold">Hands Database</h2>
            <p className="text-xs text-muted-foreground">
              All tracked hands · sortable by pot or net profit
            </p>
          </div>
          <span className="hidden font-mono text-[10px] uppercase tracking-widest text-muted-foreground sm:inline">
            {totalItems.toLocaleString()} hands
          </span>
        </div>

        {/* ── Table ───────────────────────────────────────────────────────── */}
        <div className="overflow-x-auto scrollbar-thin">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="pl-5 text-xs">Hand ID</TableHead>
                <SortHead label="Timestamp" col="timestamp" active={sortBy} desc={sortDesc} onSort={handleSort} />
                <SortHead label="Pot (BB)"   col="pot_in_bb"  active={sortBy} desc={sortDesc} onSort={handleSort} />
                <SortHead label="Result"     col="net_profit" active={sortBy} desc={sortDesc} onSort={handleSort} className="pr-5 text-right" />
              </TableRow>
            </TableHeader>

            <TableBody>
              {loading && hands.length === 0 ? (
                // Skeleton rows
                Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={i} className="border-border">
                    <TableCell className="pl-5"><div className="h-3.5 w-28 animate-pulse rounded bg-zinc-800" /></TableCell>
                    <TableCell><div className="h-3.5 w-32 animate-pulse rounded bg-zinc-800" /></TableCell>
                    <TableCell><div className="h-3.5 w-16 animate-pulse rounded bg-zinc-800" /></TableCell>
                    <TableCell className="pr-5 text-right"><div className="ml-auto h-3.5 w-16 animate-pulse rounded bg-zinc-800" /></TableCell>
                  </TableRow>
                ))
              ) : hands.length === 0 ? (
                <TableRow className="border-border">
                  <TableCell colSpan={4} className="h-28 text-center text-sm text-muted-foreground">
                    No hands found.
                  </TableCell>
                </TableRow>
              ) : (
                hands.map((h) => {
                  const isWin    = h.net_profit > 0
                  const bigPot   = (h.pot_in_bb ?? 0) >= 30  // highlight big pots
                  const bigLoss  = h.net_profit < -2

                  return (
                    <TableRow
                      key={h.hand_id}
                      className={cn(
                        "group border-border transition-colors",
                        loading && "opacity-40",
                        bigPot && !bigLoss
                          ? "bg-[#10B981]/3 hover:bg-[#10B981]/8"
                          : bigLoss
                          ? "bg-[#FF3B3B]/3 hover:bg-[#FF3B3B]/8"
                          : "hover:bg-muted/30",
                      )}
                    >
                      {/* Hand ID */}
                      <TableCell className="pl-5">
                        <button
                          onClick={() => setSelectedHandId(h.hand_id)}
                          className="group/btn flex items-center gap-1.5 font-mono text-xs text-primary transition-colors hover:text-primary/80"
                        >
                          <span>{h.hand_id.split("-")[0]}</span>
                          <ExternalLink className="size-3 opacity-0 transition-opacity group-hover/btn:opacity-100" />
                          {h.has_analysis && <span title="AI Analyzed" className="text-[10px]">🧠</span>}
                          {h.has_note     && <span title="Has Note"    className="text-[10px]">📝</span>}
                        </button>
                      </TableCell>

                      {/* Timestamp */}
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {new Date(h.timestamp).toLocaleDateString()} {" "}
                        {new Date(h.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </TableCell>

                      {/* Pot */}
                      <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                        {(h.pot_in_bb ?? 0).toFixed(1)}bb
                        {bigPot && (
                          <span className="ml-1.5 rounded-full bg-amber-500/15 px-1 py-0.5 font-mono text-[8px] uppercase text-amber-400">
                            Big
                          </span>
                        )}
                      </TableCell>

                      {/* Result */}
                      <TableCell className="pr-5 text-right">
                        <span className={cn(
                          "font-mono text-sm font-semibold tabular-nums",
                          isWin ? "text-[#10B981]" : "text-[#FF3B3B]",
                        )}>
                          {isWin ? "+" : ""}
                          {h.is_cash === false
                            ? `${Math.round(h.net_profit).toLocaleString()}`
                            : currency(h.net_profit)}
                        </span>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>

        {/* ── Pagination ──────────────────────────────────────────────────── */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border px-5 py-3">
            <span className="font-mono text-xs text-muted-foreground">
              {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, totalItems)} of {totalItems.toLocaleString()}
            </span>
            <div className="flex items-center gap-1">
              <PageBtn disabled={page <= 1 || loading} onClick={() => setPage(1)} label="«" />
              <PageBtn disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)} label="‹" />
              {/* Page number pills */}
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const start = Math.max(1, Math.min(page - 2, totalPages - 4))
                const p = start + i
                return (
                  <button
                    key={p}
                    disabled={loading}
                    onClick={() => setPage(p)}
                    className={cn(
                      "flex h-7 w-7 items-center justify-center rounded-md font-mono text-xs transition-colors",
                      p === page
                        ? "bg-primary/20 text-primary ring-1 ring-primary/40"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    {p}
                  </button>
                )
              })}
              <PageBtn disabled={page >= totalPages || loading} onClick={() => setPage((p) => p + 1)} label="›" />
              <PageBtn disabled={page >= totalPages || loading} onClick={() => setPage(totalPages)} label="»" />
            </div>
          </div>
        )}
      </div>

      {/* Modal */}
      {selectedHandId && (
        <HandViewer handId={selectedHandId} onClose={() => setSelectedHandId(null)} />
      )}
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────
function SortHead({
  label, col, active, desc, onSort, className,
}: {
  label: string; col: string; active: string; desc: boolean
  onSort: (c: string) => void; className?: string
}) {
  const isActive = active === col
  return (
    <TableHead className={cn("cursor-pointer select-none", className)}>
      <button
        onClick={() => onSort(col)}
        className={cn(
          "inline-flex items-center gap-1 font-medium transition-colors hover:text-foreground",
          isActive ? "text-foreground" : "text-muted-foreground",
        )}
      >
        {label}
        {isActive
          ? desc
            ? <ArrowDownIcon className="size-3" />
            : <ArrowUpIcon className="size-3" />
          : <ChevronsUpDown className="size-3 opacity-40" />}
      </button>
    </TableHead>
  )
}

function PageBtn({ disabled, onClick, label }: { disabled: boolean; onClick: () => void; label: string }) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className="flex h-7 w-7 items-center justify-center rounded-md font-mono text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
    >
      {label}
    </button>
  )
}
