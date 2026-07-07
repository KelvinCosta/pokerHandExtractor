"use client"

import { useEffect, useState } from "react"
import { fetchHandDetails } from "@/lib/api"
import type { HandDetails } from "@/lib/api.types"
import { X, Loader2, AlertCircle, Trophy, TrendingDown, Copy, Check } from "lucide-react"
import { currency } from "@/lib/poker-data"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"

interface HandViewerProps {
  handId: string | null
  onClose: () => void
}

// ─── Card Helpers ─────────────────────────────────────────────────────────────
const SUIT_SYMBOL: Record<string, string> = { s: "♠", h: "♥", d: "♦", c: "♣" }
const SUIT_COLOR: Record<string, string> = {
  s: "text-zinc-900",
  h: "text-rose-600",
  d: "text-sky-600",
  c: "text-zinc-900",
}
const SUIT_GLOW: Record<string, string> = {
  s: "",
  h: "drop-shadow-[0_0_6px_rgba(251,113,133,0.6)]",
  d: "drop-shadow-[0_0_6px_rgba(56,189,248,0.6)]",
  c: "drop-shadow-[0_0_6px_rgba(52,211,153,0.6)]",
}

function parseCard(raw: string): { rank: string; suit: string } | null {
  if (!raw || raw.length < 2) return null
  const suit = raw.slice(-1).toLowerCase()
  const rank = raw.slice(0, -1).toUpperCase()
  return { rank, suit }
}

function PlayingCard({ card, hidden = false, size = "md" }: { card?: string; hidden?: boolean; size?: "sm" | "md" }) {
  const dim = size === "sm"
    ? "h-14 w-10 text-sm"
    : "h-20 w-14 text-lg sm:h-24 sm:w-16 sm:text-xl"
  const suitDim = size === "sm" ? "text-[10px]" : "text-xs sm:text-sm"

  if (hidden || !card) {
    return (
      <div className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-white/10 shadow-lg",
        "bg-gradient-to-br from-[#1a1f3a] to-[#0d1021]",
        dim,
      )}>
        <div className="h-[calc(100%-6px)] w-[calc(100%-6px)] rounded-md border border-dashed border-white/15 opacity-40" />
      </div>
    )
  }

  const parsed = parseCard(card)
  if (!parsed) return null
  const { rank, suit } = parsed

  return (
    <div className={cn(
      "relative flex flex-col items-center justify-center rounded-lg border shadow-xl transition-transform duration-150 hover:scale-105",
      "bg-gradient-to-br from-zinc-50 to-zinc-100 border-zinc-200/20",
      dim,
    )}>
      {/* Top-left rank+suit */}
      <div className={cn("absolute left-1 top-1 flex flex-col items-center leading-none", SUIT_COLOR[suit])}>
        <span className={cn("font-black", size === "sm" ? "text-[9px]" : "text-[11px]")}>{rank}</span>
        <span className={cn(suitDim, "font-bold")}>{SUIT_SYMBOL[suit]}</span>
      </div>
      {/* Center suit */}
      <span className={cn("font-bold select-none", SUIT_COLOR[suit], SUIT_GLOW[suit], size === "sm" ? "text-base" : "text-2xl sm:text-3xl")}>
        {SUIT_SYMBOL[suit]}
      </span>
      {/* Bottom-right rank+suit (rotated) */}
      <div className={cn("absolute bottom-1 right-1 flex rotate-180 flex-col items-center leading-none", SUIT_COLOR[suit])}>
        <span className={cn("font-black", size === "sm" ? "text-[9px]" : "text-[11px]")}>{rank}</span>
        <span className={cn(suitDim, "font-bold")}>{SUIT_SYMBOL[suit]}</span>
      </div>
    </div>
  )
}

// ─── Action Pills ─────────────────────────────────────────────────────────────
const ACTION_STYLE: Record<string, string> = {
  BET:    "bg-amber-500/20 text-amber-300 border-amber-500/30",
  RAISE:  "bg-rose-500/20 text-rose-300 border-rose-500/30",
  CALL:   "bg-sky-500/15 text-sky-300 border-sky-500/25",
  CHECK:  "bg-zinc-700/60 text-zinc-400 border-zinc-600/40",
  FOLD:   "bg-zinc-800/60 text-zinc-500 border-zinc-700/40 line-through",
  "ALL-IN": "bg-rose-600/30 text-rose-200 border-rose-400/40 font-extrabold animate-pulse",
}

const STREET_STYLE: Record<string, string> = {
  PREFLOP: "text-violet-400 border-violet-500/30 bg-violet-500/10",
  FLOP:    "text-sky-400 border-sky-500/30 bg-sky-500/10",
  TURN:    "text-amber-400 border-amber-500/30 bg-amber-500/10",
  RIVER:   "text-rose-400 border-rose-500/30 bg-rose-500/10",
}

const STREET_ORDER = ["PREFLOP", "FLOP", "TURN", "RIVER"]

// ─── Felt Table ───────────────────────────────────────────────────────────────
function PokerTable({ data, isCash }: { data: HandDetails; isCash: boolean }) {
  const heroCards = data.player_cards?.find(p => p.player === data.player_nickname)?.cards?.split(" ") ?? []
  const villainsWithCards = data.player_cards?.filter(p => p.player !== data.player_nickname && p.cards) ?? []
  const board = data.board_cards ?? []

  return (
    <div className="relative flex flex-col items-center overflow-hidden rounded-2xl border border-white/5 py-8 px-4"
      style={{
        background: "radial-gradient(ellipse 80% 60% at 50% 50%, #0d3320 0%, #081a12 55%, #04100c 100%)",
        boxShadow: "inset 0 0 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.05)",
      }}>
      {/* Felt oval outline */}
      <div className="pointer-events-none absolute inset-6 rounded-[40%] border border-white/5 opacity-60" />

      {/* Board */}
      <div className="z-10 mb-8 flex flex-col items-center gap-2">
        <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/30">Board</span>
        <div className="flex gap-2">
          {[0, 1, 2, 3, 4].map(i => (
            <PlayingCard key={i} card={board[i]} hidden={!board[i]} />
          ))}
        </div>
      </div>

      {/* Players */}
      <div className="z-10 flex flex-wrap items-end justify-center gap-6">
        {/* Hero */}
        <div className="flex flex-col items-center gap-2">
          <div className="flex gap-1.5">
            <PlayingCard card={heroCards[0]} hidden={!heroCards[0]} />
            <PlayingCard card={heroCards[1]} hidden={!heroCards[1]} />
          </div>
          <div className={cn(
            "rounded-full border px-3 py-1 font-mono text-[10px] font-semibold",
            "bg-emerald-500/15 border-emerald-500/30 text-emerald-300",
          )}>
            HERO · {data.player_nickname}
          </div>
        </div>

        {/* Villains */}
        {villainsWithCards.map((villain, idx) => {
          const vCards = villain.cards.split(" ")
          return (
            <div key={idx} className="flex flex-col items-center gap-2 opacity-80">
              <div className="flex gap-1.5">
                <PlayingCard card={vCards[0]} hidden={!vCards[0]} />
                <PlayingCard card={vCards[1]} hidden={!vCards[1]} />
              </div>
              <div className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 font-mono text-[10px] font-semibold text-rose-400">
                {villain.player}
              </div>
            </div>
          )
        })}
      </div>

      {/* Pot badge */}
      <div className="mt-6 z-10 flex items-center gap-2 rounded-full border border-amber-500/20 bg-amber-500/10 px-4 py-1.5">
        <span className="h-2 w-2 rounded-full bg-amber-400 opacity-80" />
        <span className="font-mono text-xs text-amber-300">
          Final Pot: <span className="font-bold">{isCash ? currency(data.total_pot_final) : Math.round(data.total_pot_final).toLocaleString()}</span>
        </span>
      </div>
    </div>
  )
}

// ─── Copy Button ────────────────────────────────────────────────────────────────
function CopyButton({ data, isCash }: { data: HandDetails; isCash: boolean }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    let out = `Hand #${data.hand_id} (${data.game_type})\n`
    out += `Date: ${data.data_limpa}\n`
    out += `Final Pot: ${isCash ? currency(data.total_pot_final) : Math.round(data.total_pot_final).toLocaleString()}\n\n`
    
    const grouped: Record<string, typeof data.actions> = {}
    for (const act of data.actions || []) {
      let street = (act.street ?? "PREFLOP").toUpperCase()
      if (street === "PRE_FLOP") street = "PREFLOP"
      if (!grouped[street]) grouped[street] = []
      grouped[street].push(act)
    }
    
    const heroCards = data.player_cards?.find(p => p.player === data.player_nickname)?.cards ?? ""
    const board = data.board_cards ?? []
    
    for (const street of STREET_ORDER) {
      if (grouped[street]) {
        out += `--- ${street} ---\n`
        
        if (street === "PREFLOP" && heroCards) {
          out += `Dealt to Hero [${heroCards}]\n`
        } else if (street === "FLOP" && board.length >= 3) {
          out += `Board [${board.slice(0, 3).join(" ")}]\n`
        } else if (street === "TURN" && board.length >= 4) {
          out += `Board [${board.slice(0, 4).join(" ")}]\n`
        } else if (street === "RIVER" && board.length >= 5) {
          out += `Board [${board.slice(0, 5).join(" ")}]\n`
        }
        
        for (const act of grouped[street]) {
          const isAllIn = act.is_all_in ? " (All-in)" : ""
          let line = `${act.player}: ${act.action_type || act.action}`
          if (act.amount > 0) {
            line += ` ${isCash ? currency(act.amount) : Math.round(act.amount).toLocaleString()}`
          }
          out += `${line}${isAllIn}\n`
        }
        out += `\n`
      }
    }

    const villainsWithCards = data.player_cards?.filter(p => p.player !== data.player_nickname && p.cards) ?? []
    if (villainsWithCards.length > 0) {
      out += `--- SHOWDOWN ---\n`
      for (const v of villainsWithCards) {
        out += `${v.player} shows [${v.cards}]\n`
      }
      out += `\n`
    }

    navigator.clipboard.writeText(out.trim())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button 
      onClick={handleCopy}
      className="flex items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-800/50 px-2.5 py-1 text-xs text-zinc-300 transition-colors hover:bg-zinc-700 hover:text-zinc-100"
    >
      {copied ? <Check className="size-3 text-emerald-400" /> : <Copy className="size-3" />}
      {copied ? "Copied" : "Copy Actions"}
    </button>
  )
}

// ─── Action Log ───────────────────────────────────────────────────────────────
function ActionLog({ data, isCash }: { data: HandDetails; isCash: boolean }) {
  if (!data.actions?.length) {
    return <p className="py-6 text-center text-xs text-muted-foreground">No action data available.</p>
  }

  // Group actions by street
  const grouped: Record<string, typeof data.actions> = {}
  for (const act of data.actions) {
    let street = (act.street ?? "PREFLOP").toUpperCase()
    if (street === "PRE_FLOP") street = "PREFLOP"
    
    if (!grouped[street]) grouped[street] = []
    grouped[street].push(act)
  }

  return (
    <div className="flex flex-col gap-4">
      {STREET_ORDER.filter(s => grouped[s]).map(street => (
        <div key={street}>
          {/* Street header */}
          <div className={cn(
            "mb-2 inline-flex items-center gap-1.5 rounded-full border px-3 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-widest",
            STREET_STYLE[street] ?? "text-zinc-400 border-zinc-600 bg-zinc-800/40",
          )}>
            {street}
          </div>

          {/* Actions for this street */}
          <div className="flex flex-col gap-1">
            {grouped[street].map((act, i) => {
              const isHero = act.player === data.player_nickname
              const actionKey = act.is_all_in ? "ALL-IN" : act.action_type ?? "CHECK"
              const pillStyle = ACTION_STYLE[actionKey] ?? "bg-zinc-700/50 text-zinc-400 border-zinc-600/40"

              return (
                <div
                  key={i}
                  className={cn(
                    "flex items-center justify-between rounded-lg px-3 py-2 transition-colors",
                    isHero
                      ? "bg-emerald-500/5 hover:bg-emerald-500/10"
                      : "bg-zinc-900/40 hover:bg-zinc-800/40",
                  )}
                >
                  <div className="flex items-center gap-2.5">
                    {/* Player dot */}
                    <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", isHero ? "bg-emerald-400" : "bg-zinc-600")} />
                    {/* Player name */}
                    <span className={cn("font-mono text-xs font-medium", isHero ? "text-emerald-300" : "text-zinc-300")}>
                      {act.player}
                    </span>
                    {/* Action pill */}
                    <span className={cn("rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold", pillStyle)}>
                      {act.is_all_in ? "ALL-IN" : act.action_type}
                    </span>
                  </div>
                  {/* Amount */}
                  <span className={cn(
                    "font-mono text-xs tabular-nums",
                    act.amount > 0 ? "text-zinc-200" : "text-zinc-600",
                  )}>
                    {act.amount > 0 ? (isCash ? currency(act.amount) : Math.round(act.amount).toLocaleString()) : "—"}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {/* Any unlisted streets */}
      {Object.keys(grouped)
        .filter(s => !STREET_ORDER.includes(s))
        .map(street => (
          <div key={street}>
            <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-zinc-600 bg-zinc-800/40 px-3 py-0.5 font-mono text-[10px] text-zinc-400 uppercase tracking-widest">
              {street}
            </div>
            <div className="flex flex-col gap-1">
              {grouped[street].map((act, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-zinc-900/40 px-3 py-2">
                  <span className="font-mono text-xs text-zinc-300">{act.player}</span>
                  <span className="font-mono text-xs text-zinc-400">{act.action_type}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export function HandViewer({ handId, onClose }: HandViewerProps) {
  const [data, setData] = useState<HandDetails | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!handId) { setData(null); return }
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchHandDetails(handId)
      .then(res  => { if (!cancelled) setData(res) })
      .catch(err => { if (!cancelled) setError(err.message || "Failed to load hand") })
      .finally(()  => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [handId])

  if (!handId) return null

  const isWin = (data?.hero_net_profit ?? 0) >= 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md">
      <div
        className="relative flex max-h-[92vh] w-[95vw] max-w-2xl flex-col overflow-hidden rounded-2xl border border-white/8 bg-zinc-950 shadow-[0_32px_80px_rgba(0,0,0,0.8)] animate-in fade-in zoom-in-95 duration-200"
      >
        {/* ── Title Bar ───────────────────────────────────────────────────── */}
        <div className="flex shrink-0 items-center justify-between border-b border-white/6 bg-zinc-900/80 px-5 py-3.5">
          <div className="flex items-center gap-3">
            <div className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_2px_rgba(52,211,153,0.5)]" />
            <span className="text-sm font-bold tracking-tight text-zinc-100">Hand Replay</span>
            <code className="rounded-md bg-zinc-800 px-2 py-0.5 font-mono text-[10px] text-zinc-400">
              #{handId}
            </code>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* ── Content ─────────────────────────────────────────────────────── */}
        <ScrollArea className="flex-1 overflow-y-auto">
          {loading && (
            <div className="flex h-72 flex-col items-center justify-center gap-3 text-zinc-500">
              <Loader2 className="size-8 animate-spin text-emerald-500" />
              <p className="font-mono text-xs">Loading hand data…</p>
            </div>
          )}

          {error && (
            <div className="flex h-72 flex-col items-center justify-center gap-2 text-rose-400">
              <AlertCircle className="size-8" />
              <p className="font-medium text-sm">Failed to load hand</p>
              <p className="font-mono text-xs text-rose-500/70">{error}</p>
            </div>
          )}

          {!loading && !error && data && (() => {
            const isWin = (data.hero_net_profit_usd + data.hero_net_chips) > 0
            const isCash = data.game_type === "Rush & Cash" || data.game_type === "Regular Cash" || data.game_type === "All-In or Fold"
            
            return (
            <div className="flex flex-col gap-5 p-5">

              {/* ── KPI Strip ─────────────────────────────────────────────── */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  { label: "Date",       value: data.data_limpa },
                  { label: "Game Type",  value: data.game_type },
                  { label: "Final Pot",  value: isCash ? currency(data.total_pot_final) : Math.round(data.total_pot_final).toLocaleString() },
                  {
                    label: "Hero Result",
                    value: `${isWin ? "+" : ""}${isCash ? currency(data.hero_net_profit_usd + data.hero_net_chips) : Math.round(data.hero_net_profit_usd + data.hero_net_chips).toLocaleString()}`,
                    highlight: true,
                    win: isWin,
                  },
                ].map(item => (
                  <div key={item.label} className="rounded-xl border border-white/5 bg-zinc-900/60 px-4 py-3">
                    <p className="mb-1 font-mono text-[9px] uppercase tracking-widest text-zinc-500">{item.label}</p>
                    <div className="flex items-center gap-1.5">
                      {item.highlight && (
                        item.win
                          ? <Trophy className="size-3 text-emerald-400" />
                          : <TrendingDown className="size-3 text-rose-400" />
                      )}
                      <p className={cn(
                        "font-mono text-sm font-bold tabular-nums",
                        item.highlight
                          ? item.win ? "text-emerald-400" : "text-rose-400"
                          : "text-zinc-200",
                      )}>
                        {item.value}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              {/* ── Poker Table ───────────────────────────────────────────── */}
              <PokerTable data={data} isCash={isCash} />

              {/* ── Action Log ────────────────────────────────────────────── */}
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
                    Action History
                  </p>
                  <CopyButton data={data} isCash={isCash} />
                </div>
                <ActionLog data={data} isCash={isCash} />
              </div>

            </div>
          )})()}
        </ScrollArea>
      </div>
    </div>
  )
}
