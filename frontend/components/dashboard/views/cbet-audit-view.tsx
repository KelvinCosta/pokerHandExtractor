"use client"

import { useEffect, useState } from "react"
import { fetchCbetTextures } from "@/lib/api"
import type { DashboardFilters, CbetTexturesResponse } from "@/lib/api.types"
import { 
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from "recharts"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { currency } from "@/lib/poker-data"
import { AlertCircle, Target, TrendingDown } from "lucide-react"

export function CbetAuditView({
  filters,
}: {
  filters?: DashboardFilters
  setFilters?: (f: DashboardFilters) => void
  setView?: (v: string) => void
}) {
  const [data, setData] = useState<CbetTexturesResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchCbetTextures(filters)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filters])

  if (loading) {
    return <div className="flex h-64 items-center justify-center text-sm text-muted-foreground animate-pulse">Loading C-Bet Analysis...</div>
  }

  if (!data) return null

  // Categorize for scatter coloring
  const getColor = (texture: string) => {
    if (texture.includes("monotone")) return "#3b82f6" // blue
    if (texture.includes("two-tone")) return "#10b981" // green
    if (texture.includes("rainbow")) return "#8b5cf6" // purple
    return "#f43f5e" // rose for paired/others
  }

  const texturesMap = Array.from(new Set(data.scatter.map(d => d.flop_suit_type)))
  const getTextureX = (t: string) => texturesMap.indexOf(t) + 1 + (Math.random() * 0.4 - 0.2) // jitter

  const finalScatter = data.scatter.map((d, i) => ({
    ...d,
    x: getTextureX(d.flop_suit_type),
  }))

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-3 mb-2">
        <div className="flex size-10 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-blue-500">
          <Target className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold tracking-tight">C-Bet Analysis</h2>
          <p className="text-sm text-muted-foreground">Flop texture sizing distribution & Value Owning tracker</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Scatter Chart - Sizing vs Texture */}
        <section className="rounded-xl border border-border bg-card p-5 shadow-sm">
          <h3 className="font-semibold mb-1">Sizing Distribution by Texture</h3>
          <p className="text-xs text-muted-foreground mb-6">How much you bet depending on the board suits</p>
          
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" opacity={0.5} vertical={false} />
                <XAxis 
                  type="number" 
                  dataKey="x" 
                  name="Texture" 
                  tickFormatter={(val) => {
                    const idx = Math.round(val) - 1
                    return texturesMap[idx] ? texturesMap[idx].substring(0, 8) : ""
                  }} 
                  ticks={texturesMap.map((_, i) => i + 1)}
                  domain={[0, texturesMap.length + 1]}
                  tick={{ fontSize: 10, fill: "#888" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis 
                  type="number" 
                  dataKey="sizing_flop_pct" 
                  name="Sizing %" 
                  unit="%" 
                  tick={{ fontSize: 10, fill: "#888" }}
                  axisLine={false}
                  tickLine={false}
                  domain={[0, 150]}
                />
                <Tooltip 
                  cursor={{ strokeDasharray: '3 3' }}
                  contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "8px", fontSize: "12px" }}
                  formatter={(value: number, name: string) => [
                    name === "sizing_flop_pct" ? `${value}% pot` : value, 
                    name === "sizing_flop_pct" ? "Sizing" : "Texture"
                  ]}
                  labelFormatter={() => ""}
                />
                <Scatter name="Bets" data={finalScatter} fill="#8884d8">
                  {finalScatter.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getColor(entry.flop_suit_type)} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Value Owning Tracker */}
        <section className="rounded-xl border border-rose-500/20 bg-card shadow-sm relative overflow-hidden flex flex-col">
          <div className="absolute top-0 right-0 p-32 bg-rose-500/5 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none" />
          
          <div className="p-5 pb-0 mb-4 flex items-center gap-2">
            <TrendingDown className="size-5 text-rose-500" />
            <div>
              <h3 className="font-semibold text-rose-100">Value Owning Tracker</h3>
              <p className="text-[10px] text-rose-500/70 uppercase font-semibold tracking-wider">Bets &gt; 60% pot on flop, got action, lost SD</p>
            </div>
          </div>

          <div className="overflow-x-auto flex-1 p-5 pt-0">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead className="text-xs">Hand ID</TableHead>
                  <TableHead className="text-xs">Texture</TableHead>
                  <TableHead className="text-right text-xs">Sizing</TableHead>
                  <TableHead className="text-right text-xs">Bet (BB)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.valueOwning.length > 0 ? data.valueOwning.map((vo: any) => (
                  <TableRow key={vo.hand_id} className="border-border/50 hover:bg-rose-500/10 transition-colors">
                    <TableCell className="font-mono text-xs">{vo.hand_id}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{vo.flop_suit_type}</TableCell>
                    <TableCell className="text-right font-mono text-xs text-rose-400 font-medium">
                      {vo.sizing_flop_pct}%
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-foreground">
                      {vo.hero_bet_bb} BB
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={4} className="h-24 text-center text-sm text-muted-foreground">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <AlertCircle className="size-5 text-emerald-500/50" />
                        No value owning leaks found!
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </section>

      </div>
    </div>
  )
}
