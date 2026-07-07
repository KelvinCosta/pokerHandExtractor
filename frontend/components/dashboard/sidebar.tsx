"use client"

import { cn } from "@/lib/utils"
import {
  Activity,
  BarChart2,
  Crosshair,
  Layers,
  Radar,
  Spade,
  Target,
  Users,
  Waves,
  BrainCircuit,
} from "lucide-react"

export type ViewId =
  | "overview"
  | "analytics"
  | "ranges"
  | "engines"
  | "villains"
  | "tournaments"
  | "bigpots"
  | "population"
  | "audit"
  | "import"

const nav: {
  group: string
  items: { id: ViewId; label: string; icon: React.ElementType; badge?: string }[]
}[] = [
  {
    group: "Telemetry",
    items: [
      { id: "overview",     label: "General Health",          icon: Activity  },
      { id: "analytics",    label: "Analytics Dashboard",     icon: BarChart2, badge: "NEW" },
      { id: "ranges",       label: "Preflop Ranges",          icon: Radar,     badge: "NEW" },
      { id: "engines",      label: "Pre / Post-Flop Engines", icon: Layers    },
      { id: "villains",     label: "Villain Mapping",         icon: Users     },
      { id: "tournaments",  label: "Tournaments",             icon: Target    },
      { id: "bigpots",      label: "Hands Database",          icon: Spade     },
    ],
  },
  {
    group: "ETL",
    items: [
      { id: "import", label: "Import Data", icon: Waves },
    ],
  },
]

export function Sidebar({
  active,
  onSelect,
}: {
  active: ViewId
  onSelect: (id: ViewId) => void
}) {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">

      {/* ── Brand ──────────────────────────────────────────────────────────── */}
      <div className="flex h-14 items-center gap-2.5 border-b border-sidebar-border px-4">
        <div className="relative flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-[0_0_12px_2px_rgba(16,185,129,0.3)]">
          <Spade className="size-4" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-bold tracking-tight">Overlay</p>
          <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground/70">
            Telemetry
          </p>
        </div>
        {/* Live status dot */}
        <div className="ml-auto flex items-center gap-1.5">
          <span className="relative flex size-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#10B981] opacity-60" />
            <span className="relative inline-flex size-2 rounded-full bg-[#10B981]" />
          </span>
          <span className="font-mono text-[9px] uppercase tracking-widest text-[#10B981]/70">Live</span>
        </div>
      </div>

      {/* ── Nav ────────────────────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto px-2.5 py-4 scrollbar-thin">
        {nav.map((section) => (
          <div key={section.group} className="mb-5">
            {/* Section label */}
            <div className="mb-1.5 flex items-center gap-2 px-2">
              <div className="h-px flex-1 bg-sidebar-border" />
              <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-muted-foreground/50">
                {section.group}
              </p>
              <div className="h-px flex-1 bg-sidebar-border" />
            </div>

            <ul className="flex flex-col gap-0.5">
              {section.items.map((item) => {
                const Icon = item.icon
                const isActive = active === item.id
                return (
                  <li key={item.id}>
                    <button
                      onClick={() => onSelect(item.id)}
                      className={cn(
                        "group relative flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-all duration-150",
                        isActive
                          ? "bg-sidebar-accent text-foreground"
                          : "text-muted-foreground hover:bg-sidebar-accent/40 hover:text-foreground",
                      )}
                    >
                      {/* Active left bar */}
                      <div className={cn(
                        "absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-primary transition-all duration-150",
                        isActive ? "opacity-100" : "opacity-0",
                      )} />

                      <Icon className={cn(
                        "size-4 shrink-0 transition-colors duration-150",
                        isActive ? "text-primary" : "text-muted-foreground/60 group-hover:text-muted-foreground",
                      )} />

                      <span className="truncate text-left flex-1 text-sm">{item.label}</span>

                      {item.badge && (
                        <span className={cn(
                          "rounded-full px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide",
                          item.badge === "NEW"
                            ? "bg-primary/15 text-primary"
                            : item.badge === "AI"
                            ? "bg-violet-500/15 text-violet-400"
                            : "bg-muted text-muted-foreground",
                        )}>
                          {item.badge}
                        </span>
                      )}
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}

        {/* ── AI Auditor teaser (coming soon) ──────────────────────────────── */}
        <div className="mb-4">
          <div className="flex items-center gap-2 px-2 mb-1.5">
            <div className="h-px flex-1 bg-sidebar-border" />
            <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-muted-foreground/50">Audit</p>
            <div className="h-px flex-1 bg-sidebar-border" />
          </div>
          <div className="rounded-lg border border-dashed border-violet-500/20 bg-violet-500/5 p-3">
            <div className="mb-1.5 flex items-center gap-2">
              <BrainCircuit className="size-4 text-violet-400" />
              <span className="text-sm font-medium text-foreground">Behavioral Auditor</span>
            </div>
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              AI tilt detection & Socratic review.
            </p>
            <span className="mt-2.5 inline-flex items-center gap-1 rounded-full bg-violet-500/15 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide text-violet-400">
              <Crosshair className="size-3" /> Module B
            </span>
          </div>
        </div>
      </nav>

      {/* ── Footer — data layer status ──────────────────────────────────────── */}
      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-2 rounded-lg px-2 py-1.5">
          <div className="flex size-6 items-center justify-center rounded-md bg-[#10B981]/10">
            <Waves className="size-3.5 text-[#10B981]" />
          </div>
          <div className="leading-tight">
            <p className="text-[11px] font-medium text-foreground">Silver Layer</p>
            <p className="font-mono text-[9px] text-muted-foreground/60">synced 4m ago</p>
          </div>
          <div className="ml-auto size-2 rounded-full bg-[#10B981] shadow-[0_0_6px_rgba(16,185,129,0.6)]" />
        </div>
      </div>
    </aside>
  )
}
