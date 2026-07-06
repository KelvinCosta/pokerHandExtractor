"use client"

import { useState, useEffect, useRef } from "react"
import type { DashboardFilters, TournamentSummary } from "@/lib/api.types"
import { fetchTournamentsList } from "@/lib/api"
import { type ViewId } from "@/components/dashboard/sidebar"
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
import { ArrowDownIcon, ArrowUpIcon } from "lucide-react"

export function TournamentsView({ 
  filters,
  setFilters,
  setView
}: { 
  filters?: DashboardFilters,
  setFilters: (f: DashboardFilters) => void,
  setView: (v: ViewId) => void
}) {
  const [data, setData] = useState<TournamentSummary[]>([])
  const [loading, setLoading] = useState(false)
  
  const [sortBy, setSortBy] = useState<keyof TournamentSummary>("date")
  const [sortDesc, setSortDesc] = useState<boolean>(true)
  
  const abortControllerRef = useRef<AbortController | null>(null)

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
        const response = await fetchTournamentsList({
          ...filters
        }, controller.signal)
        
        if (!cancelled) {
          setData(response)
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return
        console.error("Error fetching tournaments:", err)
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
  }, [filters])

  const handleSort = (column: keyof TournamentSummary) => {
    if (sortBy === column) {
      setSortDesc(!sortDesc)
    } else {
      setSortBy(column)
      setSortDesc(true)
    }
  }

  const SortIcon = ({ column }: { column: keyof TournamentSummary }) => {
    if (sortBy !== column) return null
    return sortDesc ? <ArrowDownIcon className="ml-1 inline-block h-3 w-3" /> : <ArrowUpIcon className="ml-1 inline-block h-3 w-3" />
  }

  const sortedData = [...data].sort((a, b) => {
    let valA = a[sortBy] ?? ""
    let valB = b[sortBy] ?? ""
    
    if (valA < valB) return sortDesc ? 1 : -1
    if (valA > valB) return sortDesc ? -1 : 1
    return 0
  })

  const handleRowClick = (tourney: TournamentSummary) => {
    const searchString = tourney.source_file.split(".")[0].replace("_summary", "")
    setFilters({ ...(filters || {}), search_query: searchString })
    setView("bigpots")
  }

  return (
    <div className="flex flex-col gap-4">
      <section className="flex flex-col gap-4">
        
        <div className="rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold">Tournaments Summary</h2>
              <p className="text-xs text-muted-foreground">Click on a tournament to view its hands</p>
            </div>
            <span className="hidden font-mono text-[10px] uppercase tracking-widest text-muted-foreground sm:inline">
              {data.length} events
            </span>
          </div>
          <div className="overflow-x-auto scrollbar-thin">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="cursor-pointer select-none hover:text-primary pl-4" onClick={() => handleSort("date")}>
                    Date <SortIcon column="date" />
                  </TableHead>
                  <TableHead className="cursor-pointer select-none hover:text-primary" onClick={() => handleSort("source_file")}>
                    Tournament <SortIcon column="source_file" />
                  </TableHead>
                  <TableHead className="cursor-pointer select-none text-right hover:text-primary" onClick={() => handleSort("buy_in")}>
                    Buy-in <SortIcon column="buy_in" />
                  </TableHead>
                  <TableHead className="cursor-pointer select-none text-right hover:text-primary" onClick={() => handleSort("prize")}>
                    Prize <SortIcon column="prize" />
                  </TableHead>
                  <TableHead className="cursor-pointer select-none pr-4 text-right hover:text-primary" onClick={() => handleSort("profit")}>
                    Net Profit <SortIcon column="profit" />
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && data.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground h-24">Loading...</TableCell>
                  </TableRow>
                ) : sortedData.length === 0 ? (
                   <TableRow>
                     <TableCell colSpan={5} className="text-center text-muted-foreground h-24">Nenhum torneio encontrado.</TableCell>
                   </TableRow>
                ) : (
                  sortedData.map((t, idx) => (
                    <TableRow 
                      key={idx} 
                      className={cn("cursor-pointer hover:bg-muted/50 transition-colors group", loading && "opacity-50")}
                      onClick={() => handleRowClick(t)}
                    >
                      <TableCell className="pl-4 font-mono text-xs">
                        {t.date ? t.date : "N/A"}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate">
                        <span className="font-mono text-xs text-primary group-hover:underline">
                          {t.source_file.replace(".txt", "").replace("_summary", "")}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs tabular-nums text-muted-foreground">
                        {currency(t.buy_in + (t.buy_in * t.rebuys))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs tabular-nums">
                        {t.prize > 0 ? currency(t.prize) : "—"}
                      </TableCell>
                      <TableCell className="pr-4 text-right">
                        <span className={cn(
                          "inline-block rounded-md px-2 py-0.5 font-mono text-xs tabular-nums font-semibold",
                          t.profit > 0 ? "bg-[#10B981]/15 text-[#10B981]" : t.profit < 0 ? "text-[#FF3B3B]" : "text-muted-foreground"
                        )}>
                          {t.profit > 0 ? "+" : ""}{currency(t.profit)}
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
    </div>
  )
}
