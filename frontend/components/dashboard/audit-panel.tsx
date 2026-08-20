"use client"

/**
 * audit-panel.tsx
 * Socratic AI Auditor chat panel.
 *
 * Renders:
 *  1. "Start Audit" form (idle phase) — hero name + optional date range
 *  2. Chat interface (active / sending phases) — message history + input
 *  3. "End Session" button → triggers /audit/complete
 *  4. Final Report card (done phase)
 *
 * All network logic lives in useAudit() — this component is pure UI.
 */

import { useState, useRef, useEffect, useCallback } from "react"
import { useAudit } from "@/hooks/useAudit"
import type { AuditPhase } from "@/hooks/useAudit"
import { cn } from "@/lib/utils"
import {
  Brain,
  Send,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  RotateCcw,
  ChevronDown,
  Zap,
  User,
  FileText,
} from "lucide-react"
import { Button } from "@/components/ui/button"

// ─── Phase labels for the status pill ─────────────────────────────────────────
const PHASE_LABEL: Record<AuditPhase, string> = {
  idle:       "Ready",
  starting:   "Initialising...",
  active:     "Live",
  sending:    "Thinking...",
  completing: "Generating report...",
  done:       "Completed",
}

const PHASE_COLOR: Record<AuditPhase, string> = {
  idle:       "bg-muted text-muted-foreground",
  starting:   "bg-[#F59E0B]/15 text-[#F59E0B]",
  active:     "bg-[#10B981]/15 text-[#10B981]",
  sending:    "bg-[#6366F1]/15 text-[#6366F1]",
  completing: "bg-[#F59E0B]/15 text-[#F59E0B]",
  done:       "bg-[#10B981]/15 text-[#10B981]",
}

// ─── Component ────────────────────────────────────────────────────────────────
export function AuditPanel() {
  const audit = useAudit()

  // Local input state
  const [heroName, setHeroName] = useState("Hero")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [userInput, setUserInput] = useState("")

  // Auto-scroll to the last message
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [audit.messages])

  const handleStart = useCallback(async () => {
    await audit.start(heroName.trim() || "Hero", startDate || undefined, endDate || undefined)
  }, [audit, heroName, startDate, endDate])

  const handleSend = useCallback(async () => {
    const msg = userInput.trim()
    if (!msg) return
    setUserInput("")
    await audit.send(msg)
  }, [audit, userInput])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  const isInFlight =
    audit.phase === "starting" ||
    audit.phase === "sending" ||
    audit.phase === "completing"

  // ── Idle / Start form ────────────────────────────────────────────────────
  if (audit.phase === "idle") {
    return (
      <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-6">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-[#6366F1]/15">
            <Brain className="size-5 text-[#6366F1]" />
          </div>
          <div>
            <h2 className="text-sm font-semibold">Behavioral Auditor</h2>
            <p className="text-xs text-muted-foreground">
              AI-driven Socratic review · LangGraph Agent
            </p>
          </div>
        </div>

        <div className="rounded-lg border border-dashed border-border bg-background/40 p-4 text-xs text-muted-foreground leading-relaxed">
          The auditor will analyse your pre-flop stats, detect behavioural
          patterns, and guide you through a Socratic dialogue to uncover
          hidden leaks. Session data is held in server RAM — not persisted.
        </div>

        {/* Config inputs */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              Hero Name
            </label>
            <input
              value={heroName}
              onChange={(e) => setHeroName(e.target.value)}
              placeholder="Hero"
              className="h-8 rounded border border-input bg-background px-3 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              Date Range (Optional)
            </label>
            <div className="flex gap-2">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="h-8 flex-1 rounded border border-input bg-background px-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-ring [color-scheme:dark]"
              />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="h-8 flex-1 rounded border border-input bg-background px-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-ring [color-scheme:dark]"
              />
            </div>
          </div>
        </div>

        {audit.error && (
          <div className="flex items-center gap-2 rounded-lg border border-[#FF3B3B]/20 bg-[#FF3B3B]/10 px-3 py-2 text-xs text-[#FF3B3B]">
            <AlertTriangle className="size-3.5 shrink-0" />
            {audit.error}
          </div>
        )}

        <Button
          onClick={handleStart}
          className="gap-2 bg-[#6366F1] text-white hover:bg-[#6366F1]/90"
        >
          <Zap className="size-4" />
          Start Audit Session
        </Button>
      </div>
    )
  }

  // ── Done — Final Report ──────────────────────────────────────────────────
  if (audit.phase === "done") {
    const report = audit.finalReport
    return (
      <div className="flex flex-col gap-4 rounded-xl border border-[#10B981]/30 bg-card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="size-5 text-[#10B981]" />
            <div>
              <h2 className="text-sm font-semibold">Audit Complete</h2>
              <p className="text-xs text-muted-foreground">
                Session {audit.sessionId?.slice(0, 8)}…
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={audit.reset} className="gap-1.5 text-xs">
            <RotateCcw className="size-3" />
            New Audit
          </Button>
        </div>

        {report ? (
          <div className="flex flex-col gap-3 rounded-lg border border-border bg-background/40 p-4">
            <div className="flex items-center gap-2">
              <FileText className="size-4 text-muted-foreground" />
              <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Final Report
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  Player
                </p>
                <p className="mt-0.5 font-mono text-sm font-semibold">{report.player_id}</p>
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  Behavioral Profile
                </p>
                <p className="mt-0.5 font-mono text-sm font-semibold text-[#F59E0B]">
                  {report.behavioral_profile}
                </p>
              </div>
            </div>

            {report.recommendations?.length > 0 && (
              <div>
                <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  Recommendations
                </p>
                <ul className="flex flex-col gap-1.5">
                  {report.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-foreground">
                      <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full bg-[#10B981]/15 font-mono text-[9px] text-[#10B981]">
                        {i + 1}
                      </span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">No report data returned from the server.</p>
        )}
      </div>
    )
  }

  // ── Active / Sending — Chat interface ────────────────────────────────────
  return (
    <div className="flex flex-col rounded-xl border border-border bg-card overflow-hidden">
      {/* Chat header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Brain className="size-4 text-[#6366F1]" />
          <span className="text-sm font-semibold">Behavioral Auditor</span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide",
              PHASE_COLOR[audit.phase],
            )}
          >
            {isInFlight && <Loader2 className="mr-1 inline size-2.5 animate-spin" />}
            {PHASE_LABEL[audit.phase]}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Session ID pill */}
          {audit.sessionId && (
            <span className="hidden font-mono text-[9px] text-muted-foreground sm:inline">
              {audit.sessionId.slice(0, 8)}…
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            disabled={isInFlight}
            onClick={audit.complete}
            className="h-7 gap-1 text-[10px]"
          >
            <ChevronDown className="size-3" />
            End &amp; Report
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={isInFlight}
            onClick={audit.reset}
            className="h-7 px-2 text-[10px] text-muted-foreground"
            title="Discard session"
          >
            <RotateCcw className="size-3" />
          </Button>
        </div>
      </div>

      {/* Diagnostic flags (shown once at the start) */}
      {audit.diagnosticSummary.length > 0 && (
        <div className="border-b border-border bg-[#FF3B3B]/5 px-4 py-2">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-[#FF3B3B]/70">
            Diagnostic flags
          </p>
          <ul className="flex flex-wrap gap-1.5">
            {audit.diagnosticSummary.map((flag, i) => (
              <li
                key={i}
                className="rounded-full bg-[#FF3B3B]/10 px-2 py-0.5 font-mono text-[10px] text-[#FF3B3B]"
              >
                {flag}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Message history */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin" style={{ maxHeight: 420 }}>
        <div className="flex flex-col gap-3">
          {audit.messages.map((msg, i) => {
            const isAI = msg.role === "ai"
            return (
              <div
                key={i}
                className={cn("flex gap-2.5", isAI ? "items-start" : "items-start flex-row-reverse")}
              >
                {/* Avatar */}
                <div
                  className={cn(
                    "flex size-7 shrink-0 items-center justify-center rounded-full",
                    isAI
                      ? "bg-[#6366F1]/15 text-[#6366F1]"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {isAI ? <Brain className="size-3.5" /> : <User className="size-3.5" />}
                </div>

                {/* Bubble */}
                <div
                  className={cn(
                    "max-w-[80%] rounded-xl px-3 py-2 text-xs leading-relaxed",
                    isAI
                      ? "bg-[#6366F1]/10 text-foreground"
                      : "bg-muted text-foreground",
                  )}
                >
                  {msg.content}
                </div>
              </div>
            )
          })}

          {/* Typing indicator */}
          {audit.phase === "sending" && (
            <div className="flex items-start gap-2.5">
              <div className="flex size-7 items-center justify-center rounded-full bg-[#6366F1]/15">
                <Brain className="size-3.5 text-[#6366F1]" />
              </div>
              <div className="flex items-center gap-1.5 rounded-xl bg-[#6366F1]/10 px-3 py-2">
                <span className="size-1.5 animate-bounce rounded-full bg-[#6366F1]/60 [animation-delay:0ms]" />
                <span className="size-1.5 animate-bounce rounded-full bg-[#6366F1]/60 [animation-delay:150ms]" />
                <span className="size-1.5 animate-bounce rounded-full bg-[#6366F1]/60 [animation-delay:300ms]" />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Error strip */}
      {audit.error && (
        <div className="flex items-center gap-2 border-t border-border bg-[#FF3B3B]/5 px-4 py-2 text-xs text-[#FF3B3B]">
          <AlertTriangle className="size-3.5 shrink-0" />
          {audit.error}
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-border p-3">
        <div className="flex gap-2">
          <textarea
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isInFlight}
            placeholder="Type your reply… (Enter to send, Shift+Enter for newline)"
            rows={2}
            className="flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 font-mono text-xs leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
          />
          <Button
            onClick={handleSend}
            disabled={isInFlight || !userInput.trim()}
            size="icon"
            className="size-[60px] shrink-0 bg-[#6366F1] hover:bg-[#6366F1]/90"
          >
            {isInFlight ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Send className="size-4" />
            )}
          </Button>
        </div>
        <p className="mt-1.5 font-mono text-[9px] text-muted-foreground/50">
          Session ID: {audit.sessionId ?? "—"} · Messages: {audit.messages.length}
        </p>
      </div>
    </div>
  )
}
