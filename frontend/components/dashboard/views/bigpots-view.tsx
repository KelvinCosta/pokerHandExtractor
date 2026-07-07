"use client"

import { useState, useEffect, useRef } from "react"
import type { DashboardFilters, HandsListResponse, BigPotHand } from "@/lib/api.types"
import { fetchHandsList } from "@/lib/api"
import { HandViewer } from "@/components/dashboard/hand-viewer"
import { Button } from "@/components/ui/button"

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
import { ArrowDownIcon, ArrowUpIcon, ChevronLeft, ChevronRight } from "lucide-react"

export function BigPotsView({ filters }: { filters?: DashboardFilters }) {
  const [data, setData] = useState<HandsListResponse | null>(null)
  const [loading, setLoading] = useState(false)
  
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState<string>("timestamp")
  const [sortDesc, setSortDesc] = useState<boolean>(true)
  
  const [selectedHandId, setSelectedHandId] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    setPage(1)
  }, [filters])

  useEffect(() => {
    let cancelled = false

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    const loadData = async () => {
      setLoading(true)
      try {
        const response = await fetchHandsList({
          ...filters,
          page,
          limit: 20,
          sort_by: sortBy,
          sort_desc: sortDesc,
        }, controller.signal)
        
        if (!cancelled) {
          setData(response)
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return
        console.error("Error fetching hands:", err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    const timer = setTimeout(loadData, 300)
    return () => {
      cancelled = true
      clearTimeout(timer)
      controller.abort()
    }
  }, [filters, page, sortBy, sortDesc])

  const displayHands = data?.data || []
  const totalItems = data?.total || 0
  const totalPages = Math.ceil(totalItems / 20)

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortDesc(!sortDesc)
    } else {
      setSortBy(column)
      setSortDesc(true)
    }
  }

  const SortIcon = ({ column }: { column: string }) => {
    if (sortBy !== column) return null
    return sortDesc ? <ArrowDownIcon className="ml-1 inline-block h-3 w-3" /> : <ArrowUpIcon className="ml-1 inline-block h-3 w-3" />
  }

  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-4">
        
        <div className="rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold">Hands List</h2>
              <p className="text-xs text-muted-foreground">All hands played · sortable by pot size or net profit</p>
            </div>
            <span className="hidden font-mono text-[10px] uppercase tracking-widest text-muted-foreground sm:inline">
              {totalItems} hands
            </span>
          </div>
          <div className="overflow-x-auto scrollbar-thin">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-4">Hand ID</TableHead>
                  <TableHead className="cursor-pointer select-none hover:text-primary" onClick={() => handleSort("timestamp")}>
                    Timestamp <SortIcon column="timestamp" />
                  </TableHead>
                  <TableHead className="cursor-pointer select-none hover:text-primary" onClick={() => handleSort("pot_in_bb")}>
                    Pot (BB) <SortIcon column="pot_in_bb" />
                  </TableHead>
                  <TableHead className="cursor-pointer select-none pr-4 text-right hover:text-primary" onClick={() => handleSort("net_profit")}>
                    Result <SortIcon column="net_profit" />
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && displayHands.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground h-24">Loading...</TableCell>
                  </TableRow>
                ) : displayHands.length === 0 ? (
                   <TableRow>
                     <TableCell colSpan={4} className="text-center text-muted-foreground h-24">Nenhuma mão encontrada.</TableCell>
                   </TableRow>
                ) : (
                  displayHands.map((h) => (
                    <TableRow key={h.hand_id} className={cn(loading && "opacity-50")}>
                      <TableCell className="pl-4">
                        <button 
                          onClick={() => setSelectedHandId(h.hand_id)}
                          className="font-mono text-xs text-primary transition-colors hover:text-primary/80 hover:underline flex items-center gap-1.5"
                        >
                          <span>{h.hand_id.split("-")[0]}</span>
                          {h.has_analysis && <span title="AI Analyzed" className="text-sm">🧠</span>}
                        </button>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {new Date(h.timestamp).toLocaleDateString()} {new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
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
                          {h.is_cash === false ? `${Math.round(h.net_profit).toLocaleString()}` : currency(h.net_profit)}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border px-4 py-3">
              <div className="font-mono text-xs text-muted-foreground">
                Page {page} of {totalPages}
              </div>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  disabled={page <= 1 || loading}
                  onClick={() => setPage(p => p - 1)}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  disabled={page >= totalPages || loading}
                  onClick={() => setPage(p => p + 1)}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Modal View */}
      {selectedHandId && (
        <HandViewer handId={selectedHandId} onClose={() => setSelectedHandId(null)} />
      )}
    </div>
  )
}
