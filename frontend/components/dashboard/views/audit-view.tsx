"use client"

/**
 * audit-view.tsx
 * View rendered when the user selects "AI Auditor" in the sidebar.
 * Combines the FilterBar (optional date scoping) with the AuditPanel.
 */

import { AuditPanel } from "@/components/dashboard/audit-panel"
import { Brain } from "lucide-react"

export function AuditView() {
  return (
    <div className="flex flex-col gap-5">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 rounded-xl border border-dashed border-border bg-card/40 px-4 py-3">
        <Brain className="size-5 text-[#6366F1] shrink-0" />
        <div>
          <p className="text-xs leading-relaxed text-muted-foreground">
            <span className="font-medium text-foreground">Socratic AI Auditor</span>{" "}
            — The LangGraph agent runs a 3-node pipeline: the{" "}
            <span className="font-mono text-[#10B981]">Analytical Engine</span> generates
            your diagnostic report, the{" "}
            <span className="font-mono text-[#6366F1]">Inquisitor</span> drives the dialogue,
            and the{" "}
            <span className="font-mono text-[#F59E0B]">Final Reporter</span> produces
            your behavioural profile. All stateful via{" "}
            <span className="font-mono text-muted-foreground">session_id</span>.
          </p>
        </div>
      </div>

      {/* ── Chat Panel ──────────────────────────────────────────────────── */}
      <AuditPanel />
    </div>
  )
}
