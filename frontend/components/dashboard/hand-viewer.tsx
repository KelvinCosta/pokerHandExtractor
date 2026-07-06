"use client"

import { useEffect, useState } from "react"
import { fetchHandDetails } from "@/lib/api"
import type { HandDetails } from "@/lib/api.types"
import { X, Activity } from "lucide-react"
import { currency } from "@/lib/poker-data"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"

interface HandViewerProps {
  handId: string | null
  onClose: () => void
}

const formatCard = (c: string) => {
  if (!c) return ""
  return c.replace(/s/g, "♠").replace(/h/g, "♥").replace(/d/g, "♦").replace(/c/g, "♣")
}

function GraphicalCard({ card, hidden = false }: { card?: string; hidden?: boolean }) {
  if (hidden || !card) {
    return (
      <div className="flex h-16 w-11 flex-col items-center justify-center rounded-md border border-white/10 bg-gradient-to-br from-indigo-900 to-indigo-950 shadow-sm sm:h-20 sm:w-14">
        <div className="h-full w-full rounded-sm border-[2px] border-dashed border-white/20 opacity-30" />
      </div>
    )
  }

  const display = formatCard(card)
  const isRed = display.includes("♥") || display.includes("♦")

  return (
    <div className="relative flex h-16 w-11 flex-col items-center justify-center rounded-md border border-border bg-white shadow-sm sm:h-20 sm:w-14">
      <span className={cn("text-lg font-bold sm:text-xl", isRed ? "text-red-600" : "text-black")}>
        {display.slice(0, -1)}
      </span>
      <span className={cn("absolute bottom-1 right-1 text-[10px] sm:text-xs", isRed ? "text-red-600" : "text-black")}>
        {display.slice(-1)}
      </span>
    </div>
  )
}

export function HandViewer({ handId, onClose }: HandViewerProps) {
  const [data, setData] = useState<HandDetails | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!handId) {
      setData(null)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)
    
    fetchHandDetails(handId)
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Failed to load hand")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [handId])

  if (!handId) return null

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Activity className="size-8 animate-spin text-primary" />
        </div>
      )
    }

    if (error) {
      return (
        <div className="flex h-64 flex-col items-center justify-center text-loss">
          <p className="font-medium">Error loading hand</p>
          <p className="text-xs">{error}</p>
        </div>
      )
    }

    if (!data) return null

    const heroCards = data.player_cards?.find(p => p.player === data.player_nickname)?.cards?.split(" ") || []

    return (
      <div className="flex flex-col gap-6 p-4 sm:p-6">
        
        {/* Header Stats */}
        <div className="grid grid-cols-2 gap-4 rounded-lg border border-border bg-muted/30 p-4 sm:grid-cols-4">
          <div>
            <p className="text-[10px] uppercase text-muted-foreground">Date</p>
            <p className="font-mono text-sm font-medium">{data.data_limpa}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase text-muted-foreground">Type</p>
            <p className="font-mono text-sm font-medium">{data.game_type}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase text-muted-foreground">Final Pot</p>
            <p className="font-mono text-sm font-medium">{currency(data.total_pot_final)}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase text-muted-foreground">Hero Net</p>
            <p className={cn("font-mono text-sm font-bold", data.hero_net_profit >= 0 ? "text-primary" : "text-loss")}>
              {data.hero_net_profit >= 0 ? "+" : ""}{currency(data.hero_net_profit)}
            </p>
          </div>
        </div>

        {/* Graphical Representation */}
        <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-[#0B0F19] p-6 shadow-inner relative overflow-hidden">
          <div className="absolute inset-x-4 top-1/2 -mt-16 h-32 rounded-full border border-white/5 bg-white/5 blur-sm" />
          
          <div className="z-10 mb-8 flex flex-col items-center">
            <Badge variant="outline" className="mb-3 bg-background/50 backdrop-blur">
              Board
            </Badge>
            <div className="flex gap-2">
              {[0, 1, 2, 3, 4].map(i => (
                <GraphicalCard key={i} card={data.board_cards?.[i]} hidden={!data.board_cards?.[i]} />
              ))}
            </div>
          </div>

          <div className="z-10 flex flex-col items-center">
            <Badge variant="secondary" className="mb-3 bg-primary/20 text-primary hover:bg-primary/30">
              Hero ({data.player_nickname})
            </Badge>
            <div className="flex gap-2">
              <GraphicalCard card={heroCards[0]} hidden={!heroCards[0]} />
              <GraphicalCard card={heroCards[1]} hidden={!heroCards[1]} />
            </div>
          </div>
        </div>

        {/* Action Table (Compact) */}
        <div>
          <h3 className="mb-3 text-sm font-semibold">Action History</h3>
          <div className="rounded-lg border border-border bg-card overflow-hidden">
            <ScrollArea className="h-[250px]">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-muted/95 backdrop-blur z-10 shadow-sm border-b border-border">
                  <tr>
                    <th className="px-4 py-2 font-medium text-muted-foreground">Street</th>
                    <th className="px-4 py-2 font-medium text-muted-foreground">Player</th>
                    <th className="px-4 py-2 font-medium text-muted-foreground">Action</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.actions?.map((act, i) => {
                    const isHero = act.player === data.player_nickname
                    const isAggressive = act.action_type === "RAISE" || act.action_type === "BET"
                    
                    return (
                      <tr key={i} className={cn("transition-colors hover:bg-muted/30", isHero && "bg-primary/5")}>
                        <td className="px-4 py-2 font-mono text-[10px] text-muted-foreground">{act.street}</td>
                        <td className={cn("px-4 py-2 font-medium", isHero ? "text-primary" : "text-foreground")}>
                          {act.player}
                        </td>
                        <td className="px-4 py-2">
                          <span className={cn(
                            "rounded px-1.5 py-0.5 font-mono text-[10px]",
                            isAggressive ? "bg-loss/20 text-loss" : 
                            act.action_type === "FOLD" ? "text-muted-foreground" : "bg-muted"
                          )}>
                            {act.action_type}
                          </span>
                          {act.is_all_in && (
                            <span className="ml-2 font-bold uppercase text-loss text-[9px]">All-in</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-right font-mono tabular-nums">
                          {act.amount > 0 ? currency(act.amount) : "-"}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </ScrollArea>
          </div>
        </div>
        
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm transition-all duration-200">
      <div className="relative flex max-h-[90vh] w-[95vw] max-w-2xl flex-col overflow-hidden rounded-xl border border-border bg-background shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        
        {/* Title Bar */}
        <div className="flex items-center justify-between border-b border-border bg-muted/30 px-4 py-3">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold">Hand Viewer</h2>
            <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
              {handId}
            </span>
          </div>
          <button 
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Scrollable content body */}
        <div className="overflow-y-auto">
          {renderContent()}
        </div>
      </div>
    </div>
  )
}
