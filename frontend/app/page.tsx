"use client"

import { useState } from "react"
import { Sidebar, type ViewId } from "@/components/dashboard/sidebar"
import { Topbar } from "@/components/dashboard/topbar"
import { OverviewView } from "@/components/dashboard/views/overview-view"
import { AnalyticsView } from "@/components/dashboard/views/analytics-view"
import { EnginesView } from "@/components/dashboard/views/engines-view"
import { VillainsView } from "@/components/dashboard/views/villains-view"
import { BigPotsView } from "@/components/dashboard/views/bigpots-view"
import { PopulationView } from "@/components/dashboard/views/population-view"
import { cn } from "@/lib/utils"
import { Activity, BarChart2, Layers, Radar, Spade, Target, Users } from "lucide-react"


const meta: Record<ViewId, { title: string; subtitle: string }> = {
  overview:   { title: "General Health",           subtitle: "Global KPIs, profit trend & edge distribution" },
  analytics:  { title: "Analytics Dashboard",      subtitle: "Telemetry Bento · EV chart, leaks & rivals" },
  engines:    { title: "Pre / Post-Flop Engines",  subtitle: "Aggression, continuation & showdown metrics" },
  villains:   { title: "Villain Mapping",           subtitle: "Opponent pool, rivalry board & reads" },
  bigpots:    { title: "Big Pots & River Audit",   subtitle: "High-value hands & final-street decisions" },
  population: { title: "Population (MDA)",          subtitle: "Mass data analysis across the field" },
}


const mobileNav: { id: ViewId; label: string; icon: React.ElementType }[] = [
  { id: "overview",   label: "Health",    icon: Activity  },
  { id: "analytics", label: "Analytics", icon: BarChart2  },
  { id: "engines",   label: "Engines",   icon: Layers     },
  { id: "villains",  label: "Villains",  icon: Users      },
  { id: "bigpots",   label: "Big Pots",  icon: Target     },
  { id: "population",label: "MDA",       icon: Radar      },
]


export default function Page() {
  const [view, setView] = useState<ViewId>("overview")

  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <Sidebar active={view} onSelect={setView} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={meta[view].title} subtitle={meta[view].subtitle} />

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

        <main className="flex-1 overflow-y-auto p-4 scrollbar-thin md:p-6">
          {view === "overview"   && <OverviewView />}
          {view === "analytics"  && <AnalyticsView />}
          {view === "engines"    && <EnginesView />}
          {view === "villains"   && <VillainsView />}
          {view === "bigpots"    && <BigPotsView />}
          {view === "population" && <PopulationView />}
        </main>

      </div>
    </div>
  )
}
