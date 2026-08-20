"use client"

import { Search } from "lucide-react"

export function Topbar({
  title,
  subtitle,
  searchQuery,
  onSearchChange,
}: {
  title: string
  subtitle: string
  searchQuery?: string
  onSearchChange?: (q: string | undefined) => void
}) {
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-4 border-b border-border bg-background/90 px-4 backdrop-blur-md md:px-6">

      {/* ── View title ─────────────────────────────────────────────────────── */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2.5">
          <h1 className="truncate text-sm font-semibold tracking-tight text-foreground md:text-base">
            {title}
          </h1>
          {/* Live pill */}
          <span className="hidden items-center gap-1.5 rounded-full border border-[#10B981]/30 bg-[#10B981]/10 px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest text-[#10B981] sm:inline-flex">
            <span className="size-1.5 animate-pulse rounded-full bg-[#10B981]" />
            Live
          </span>
        </div>
        <p className="truncate font-mono text-[10px] text-muted-foreground/70">{subtitle}</p>
      </div>

      {/* ── Search ─────────────────────────────────────────────────────────── */}
      <div className="hidden items-center md:flex">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground/50" />
          <input
            placeholder="Filter hands, villains…"
            value={searchQuery ?? ""}
            onChange={(e) => onSearchChange?.(e.target.value || undefined)}
            className="h-8 w-52 rounded-lg border border-input bg-zinc-900/60 pl-8 pr-3 font-mono text-xs text-foreground placeholder:text-muted-foreground/40 outline-none transition-all focus:border-primary/40 focus:bg-zinc-900 focus:ring-1 focus:ring-primary/20"
          />
        </div>
      </div>

      {/* ── Mobile search icon ─────────────────────────────────────────────── */}
      <button className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground md:hidden">
        <Search className="size-4" />
      </button>
    </header>
  )
}
