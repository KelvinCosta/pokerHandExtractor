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

export type ViewId = "overview" | "analytics" | "engines" | "villains" | "bigpots" | "population" | "audit" | "import"

const nav: {
  group: string
  items: { id: ViewId; label: string; icon: React.ElementType; badge?: string }[]
}[] = [
  {
    group: "Telemetry",
    items: [
      { id: "overview",   label: "General Health",         icon: Activity  },
      { id: "analytics",  label: "Analytics Dashboard",    icon: BarChart2, badge: "NEW" },
      { id: "engines",    label: "Pre / Post-Flop Engines", icon: Layers    },
      { id: "villains",   label: "Villain Mapping",         icon: Users     },
      { id: "bigpots",    label: "Big Pots & River",        icon: Target    },
      { id: "population", label: "Population (MDA)",        icon: Radar     },
    ],
  },
  {
    group: "Audit",
    items: [
      { id: "audit", label: "AI Auditor", icon: BrainCircuit, badge: "AI" },
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
    <aside className="hidden w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
      <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-5">
        <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Spade className="size-4" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-tight">Overlay</p>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            Telemetry
          </p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 scrollbar-thin">
        {nav.map((section) => (
          <div key={section.group} className="mb-6">
            <p className="mb-2 px-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {section.group}
            </p>
            <ul className="flex flex-col gap-0.5">
              {section.items.map((item) => {
                const Icon = item.icon
                const isActive = active === item.id
                return (
                  <li key={item.id}>
                    <button
                      onClick={() => onSelect(item.id)}
                      className={cn(
                        "group flex w-full items-center gap-3 rounded-md px-2.5 py-2 text-sm transition-colors",
                        isActive
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground",
                      )}
                    >
                      <Icon
                        className={cn(
                          "size-4 shrink-0",
                          isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground",
                        )}
                      />
                      <span className="truncate text-left flex-1">{item.label}</span>
                      {item.badge && (
                        <span className="rounded-full bg-primary/15 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide text-primary">
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

        <div className="mb-6">
          <p className="mb-2 px-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            Audit
          </p>
          <div className="rounded-lg border border-dashed border-sidebar-border bg-sidebar-accent/30 p-3">
            <div className="mb-1.5 flex items-center gap-2">
              <BrainCircuit className="size-4 text-warning" />
              <span className="text-sm font-medium">Behavioral Auditor</span>
            </div>
            <p className="text-xs leading-relaxed text-muted-foreground">
              AI tilt detection & Socratic review.
            </p>
            <span className="mt-2 inline-flex items-center gap-1 rounded-full bg-warning/15 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-warning">
              <Crosshair className="size-3" /> Module B
            </span>
          </div>
        </div>
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5">
          <Waves className="size-4 text-primary" />
          <div className="leading-tight">
            <p className="text-xs font-medium">Silver Layer</p>
            <p className="font-mono text-[10px] text-muted-foreground">synced 4m ago</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
