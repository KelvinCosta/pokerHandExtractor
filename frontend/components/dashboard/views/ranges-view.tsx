"use client"

import { useState, useEffect } from "react"
import type { DashboardFilters } from "@/lib/api.types"
import { fetchRanges } from "@/lib/api"
import { Loader2, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { BigPotsView } from "@/components/dashboard/views/bigpots-view"

const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
const POSITIONS = ["ALL", "UTG", "MP", "CO", "BTN", "SB", "BB"]

interface RangesViewProps {
  filters: DashboardFilters
}

export function RangesView({ filters }: RangesViewProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<{ dealt: any[], played: any[] } | null>(null)
  
  const [position, setPosition] = useState("ALL")
  const [selectedHand, setSelectedHand] = useState<string | null>(null)
  
  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    
    fetchRanges(filters)
      .then((res) => {
        if (!active) return
        if (res.error) {
          setError(res.error)
          setData(null)
        } else {
          setData(res)
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message || "Erro ao carregar ranges.")
          setData(null)
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
      
    return () => { active = false }
  }, [filters])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-border bg-card">
        <Loader2 className="size-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-destructive/20 bg-destructive/10 p-6 text-center text-destructive">
        <p>{error}</p>
      </div>
    )
  }

  // Pre-process data into a dictionary for fast lookup
  const getHandKey = (r1: string, r2: string) => {
    if (r1 === r2) return `${r1}${r2}`
    if (RANKS.indexOf(r1) < RANKS.indexOf(r2)) return `${r1}${r2}s`
    return `${r2}${r1}o`
  }

  const handStats = new Map<string, { dealt: number, played: number }>()
  
  if (data) {
    // Aggregation logic depending on selected position
    const dealtData = data.dealt || []
    const playedData = data.played || []
    
    dealtData.forEach((row) => {
      if (position === "ALL" || row.hero_position === position) {
        const current = handStats.get(row.range_hand) || { dealt: 0, played: 0 }
        current.dealt += row.len
        handStats.set(row.range_hand, current)
      }
    })
    
    playedData.forEach((row) => {
      if (position === "ALL" || row.hero_position === position) {
        const current = handStats.get(row.range_hand) || { dealt: 0, played: 0 }
        current.played += row.len
        handStats.set(row.range_hand, current)
      }
    })
  }
  
  const getColor = (dealt: number, played: number) => {
    if (dealt === 0) return "bg-muted/20 text-muted-foreground/30"
    const freq = played / dealt
    
    if (freq === 0) return "bg-slate-800 text-slate-400"
    if (freq < 0.1) return "bg-blue-900/80 text-blue-100"
    if (freq < 0.25) return "bg-teal-700 text-teal-50"
    if (freq < 0.5) return "bg-green-600 text-green-50"
    if (freq < 0.75) return "bg-yellow-600 text-yellow-50"
    if (freq < 0.9) return "bg-orange-500 text-orange-50"
    return "bg-red-500 text-white font-bold"
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Análise de Ranges (Pré-flop)</h2>
          <p className="text-muted-foreground">
            Visualize as frequências das mãos iniciais que você joga (VPIP) por posição.
          </p>
        </div>
        
        <div className="flex gap-2 bg-card p-1 border rounded-lg overflow-x-auto">
          {POSITIONS.map(pos => (
            <button
              key={pos}
              onClick={() => setPosition(pos)}
              className={cn(
                "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                position === pos 
                  ? "bg-primary text-primary-foreground" 
                  : "hover:bg-muted text-muted-foreground"
              )}
            >
              {pos}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card p-6 shadow-sm overflow-x-auto">
        <div className="mx-auto" style={{ minWidth: "600px", maxWidth: "800px" }}>
          {/* Add grid-cols-13 to tailwind config if not present, or use inline style */}
          <div className="grid gap-1" style={{ gridTemplateColumns: "repeat(13, minmax(0, 1fr))" }}>
            {RANKS.map((r1, i) => (
              RANKS.map((r2, j) => {
                const key = getHandKey(r1, r2)
                const stats = handStats.get(key) || { dealt: 0, played: 0 }
                const freq = stats.dealt > 0 ? ((stats.played / stats.dealt) * 100).toFixed(0) : "0"
                
                return (
                  <div
                    key={`${r1}${r2}`}
                    onClick={() => { if (stats.dealt > 0) setSelectedHand(key) }}
                    className={cn(
                      "aspect-square rounded-sm flex flex-col items-center justify-center p-1 text-xs cursor-pointer transition-all hover:scale-105 hover:z-10 hover:shadow-md",
                      getColor(stats.dealt, stats.played)
                    )}
                    title={`${key}: Jogou ${stats.played} de ${stats.dealt} vezes (${freq}%)`}
                  >
                    <span className="font-semibold">{key}</span>
                    {stats.dealt > 0 && (
                      <span className="text-[10px] opacity-75">{freq}%</span>
                    )}
                  </div>
                )
              })
            ))}
          </div>
          
          {/* Legend */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4 text-sm text-muted-foreground">
            <span className="font-medium text-foreground mr-2">Frequência (VPIP):</span>
            <div className="flex items-center gap-1"><div className="w-4 h-4 rounded-sm bg-slate-800"></div> 0%</div>
            <div className="flex items-center gap-1"><div className="w-4 h-4 rounded-sm bg-blue-900/80"></div> 1-10%</div>
            <div className="flex items-center gap-1"><div className="w-4 h-4 rounded-sm bg-teal-700"></div> 10-25%</div>
            <div className="flex items-center gap-1"><div className="w-4 h-4 rounded-sm bg-green-600"></div> 25-50%</div>
            <div className="flex items-center gap-1"><div className="w-4 h-4 rounded-sm bg-yellow-600"></div> 50-75%</div>
            <div className="flex items-center gap-1"><div className="w-4 h-4 rounded-sm bg-red-500"></div> 90%+</div>
          </div>
        </div>
      </div>

      {selectedHand && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 animate-in fade-in zoom-in-95">
          <div className="relative flex flex-col w-full max-w-6xl max-h-[90vh] bg-card border border-border shadow-2xl rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h2 className="font-semibold text-lg flex items-center gap-2">
                <span className="bg-primary/20 text-primary px-2 py-0.5 rounded text-sm">{selectedHand}</span>
                Mãos Jogadas
              </h2>
              <button onClick={() => setSelectedHand(null)} className="p-1 hover:bg-muted rounded-md transition-colors"><X className="size-5" /></button>
            </div>
            <div className="flex-1 overflow-auto p-4 bg-muted/20">
              <BigPotsView filters={{ ...filters, hole_cards_range: selectedHand }} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
