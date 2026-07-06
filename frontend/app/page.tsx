"use client"

import { useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import { Sidebar, type ViewId } from "@/components/dashboard/sidebar"
import { Topbar } from "@/components/dashboard/topbar"
import { FilterBar } from "@/components/dashboard/filter-bar"
import { OverviewView } from "@/components/dashboard/views/overview-view"
import { AnalyticsView } from "@/components/dashboard/views/analytics-view"
import { EnginesView } from "@/components/dashboard/views/engines-view"
import { VillainsView } from "@/components/dashboard/views/villains-view"
import { BigPotsView } from "@/components/dashboard/views/bigpots-view"
import { PopulationView } from "@/components/dashboard/views/population-view"
import { AuditView } from "@/components/dashboard/views/audit-view"
import { ImportView } from "@/components/dashboard/views/import-view"
import { cn } from "@/lib/utils"
import type { DashboardFilters } from "@/lib/api.types"
import { Activity, BarChart2, Brain, Layers, Radar, Spade, Target, Users, Waves } from "lucide-react"

// ─── View metadata ─────────────────────────────────────────────────────────────
const meta: Record<ViewId, { title: string; subtitle: string; hasFilters: boolean }> = {
  overview:   { title: "General Health",           subtitle: "Global KPIs, profit trend & edge distribution", hasFilters: true  },
  analytics:  { title: "Analytics Dashboard",      subtitle: "Telemetry Bento · EV chart, leaks & rivals",   hasFilters: true  },
  engines:    { title: "Pre / Post-Flop Engines",  subtitle: "Aggression, continuation & showdown metrics",  hasFilters: true  },
  villains:   { title: "Villain Mapping",           subtitle: "Opponent pool, rivalry board & reads",         hasFilters: true },
  bigpots:    { title: "Big Pots & River Audit",   subtitle: "High-value hands & final-street decisions",    hasFilters: true  },
  population: { title: "Population (MDA)",          subtitle: "Mass data analysis across the field",          hasFilters: false },
  audit:      { title: "AI Behavioral Auditor",    subtitle: "Socratic dialogue · LangGraph Agent pipeline", hasFilters: false },
  import:     { title: "Import Data (ETL)",        subtitle: "Upload raw poker hand histories for processing",hasFilters: false },
}

// ─── Mobile nav items ──────────────────────────────────────────────────────────
const mobileNav: { id: ViewId; label: string; icon: React.ElementType }[] = [
  { id: "overview",   label: "Health",    icon: Activity   },
  { id: "analytics",  label: "Analytics", icon: BarChart2  },
  { id: "engines",    label: "Engines",   icon: Layers     },
  { id: "villains",   label: "Villains",  icon: Users      },
  { id: "bigpots",    label: "Big Pots",  icon: Target     },
  // TODO: Habilitar quando o Job de ETL estiver pronto no Milestone 6
  // { id: "population", label: "MDA",       icon: Radar      },
  // TODO: Habilitar quando o LangGraph AI for implementado
  // { id: "audit",      label: "Audit",     icon: Brain      },
  { id: "import",     label: "Import",    icon: Waves      },
]

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function Page() {
  const { isAuthenticated, logout } = useAuth()
  const [view, setView] = useState<ViewId>("overview")

  // Global dashboard filters — shared across API-connected views
  const [filters, setFilters] = useState<DashboardFilters>({})

  const currentMeta = meta[view]

  if (isAuthenticated === null) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 text-muted-foreground">
          <Spade className="size-8 animate-pulse text-primary" />
          <p className="text-sm font-medium">Validando credenciais...</p>
        </div>
      </div>
    )
  }

  if (isAuthenticated === false) {
    return null // O useEffect do useAuth vai redirecionar
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <Sidebar active={view} onSelect={setView} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar 
          title={currentMeta.title} 
          subtitle={currentMeta.subtitle} 
          searchQuery={filters.search_query}
          onSearchChange={(q) => setFilters({ ...filters, search_query: q })}
        />

        {/* Mobile brand + nav */}
        <div className="lg:hidden">
          <div className="flex items-center gap-2 border-b border-border px-4 py-2">
            <div className="flex size-6 items-center justify-center rounded bg-primary text-primary-foreground">
              <Spade className="size-3.5" />
            </div>
            <span className="text-sm font-semibold">Overlay</span>
          </div>
          <div className="flex gap-1 overflow-x-auto border-b border-border px-3 py-2 scrollbar-thin">
            {mobileNav.map((item) => {
              const Icon = item.icon
              const isActive = view === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => setView(item.id)}
                  className={cn(
                    "flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    isActive ? "bg-secondary text-foreground" : "text-muted-foreground",
                  )}
                >
                  <Icon className={cn("size-3.5", isActive && "text-primary")} />
                  {item.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Global filter bar — shown only for views that support live API data */}
        {currentMeta.hasFilters && (
          <div className="border-b border-border px-4 py-2 md:px-6">
            <FilterBar filters={filters} onChange={setFilters} />
          </div>
        )}

        <main className="flex-1 overflow-y-auto p-4 scrollbar-thin md:p-6">
          {view === "overview"   && <OverviewView filters={filters} />}
          {view === "analytics"  && <AnalyticsView filters={filters} />}
          {view === "engines"    && <EnginesView filters={filters} />}
          {view === "villains"   && <VillainsView filters={filters} />}
          {view === "bigpots"    && <BigPotsView filters={filters} />}
          {/* TODO: Reabilitar as abas no futuro
          {view === "population" && <PopulationView />}
          {view === "audit"      && <AuditView />}
          */}
          {view === "import"     && <ImportView />}
        </main>
      </div>
    </div>
  )
}
