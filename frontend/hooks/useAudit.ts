/**
 * useAudit.ts
 * React hook managing the full lifecycle of a Socratic Audit session.
 *
 * State machine:
 *   idle → starting → active → completing → done
 *                   ↳ (sending) ← user sends message
 *
 * Usage:
 *   const audit = useAudit()
 *   await audit.start("Hero")
 *   await audit.send("Minha resposta...")
 *   await audit.complete()
 *   console.log(audit.finalReport)
 */
"use client"

import { useState, useCallback } from "react"
import { startAudit, sendAuditMessage, completeAudit } from "@/lib/api"
import type {
  FinalReport,
  AuditStartResponse,
} from "@/lib/api.types"

// ─── Types ────────────────────────────────────────────────────────────────────

export type AuditPhase =
  | "idle"        // No session yet
  | "starting"    // POST /audit/start in flight
  | "active"      // Session open, awaiting user input
  | "sending"     // POST /audit/message in flight
  | "completing"  // POST /audit/complete in flight
  | "done"        // Final report received, session closed

export interface ChatMessage {
  role: "ai" | "user"
  content: string
  timestamp: number
}

export interface AuditState {
  phase: AuditPhase

  /** UUID from the backend — persisted across all turns */
  sessionId: string | null

  /** Red flags raised by the analytical engine at session start */
  diagnosticSummary: string[]

  /** Full chat history rendered by the UI */
  messages: ChatMessage[]

  /** Present only after completeAudit() succeeds */
  finalReport: FinalReport | null

  error: string | null

  // ── Actions ──────────────────────────────────────────────────────────────
  /** Initialise a new session for the given hero name */
  start: (heroName: string, startDate?: string, endDate?: string) => Promise<void>

  /** Send a player reply and append the AI response to the chat */
  send: (message: string) => Promise<void>

  /** Close the session and retrieve the final behavioural report */
  complete: () => Promise<void>

  /** Reset everything back to idle (useful for "Start new audit") */
  reset: () => void
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAudit(): AuditState {
  const [phase, setPhase] = useState<AuditPhase>("idle")
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [diagnosticSummary, setDiagnosticSummary] = useState<string[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [finalReport, setFinalReport] = useState<FinalReport | null>(null)
  const [error, setError] = useState<string | null>(null)

  // ── Helpers ────────────────────────────────────────────────────────────────
  const appendMessage = useCallback((role: "ai" | "user", content: string) => {
    setMessages((prev) => [...prev, { role, content, timestamp: Date.now() }])
  }, [])

  // ── start ──────────────────────────────────────────────────────────────────
  const start = useCallback(
    async (heroName: string, startDate?: string, endDate?: string) => {
      setPhase("starting")
      setError(null)
      setMessages([])
      setDiagnosticSummary([])
      setFinalReport(null)
      setSessionId(null)

      try {
        const res: AuditStartResponse = await startAudit({
          hero_name: heroName,
          ...(startDate && { start_date: startDate }),
          ...(endDate   && { end_date:   endDate   }),
        })

        // Persist the session_id — every subsequent call needs it
        setSessionId(res.session_id)
        setDiagnosticSummary(res.diagnostic_summary ?? [])

        // The first AI message opens the conversation
        appendMessage("ai", res.message)

        setPhase("active")
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to start audit session")
        setPhase("idle")
      }
    },
    [appendMessage],
  )

  // ── send ───────────────────────────────────────────────────────────────────
  const send = useCallback(
    async (message: string) => {
      if (!sessionId) {
        setError("No active session. Call start() first.")
        return
      }
      if (phase !== "active") return

      // Optimistically append the user message so the UI feels instant
      appendMessage("user", message)
      setPhase("sending")
      setError(null)

      try {
        const res = await sendAuditMessage({ session_id: sessionId, message })
        appendMessage("ai", res.message)
        setPhase("active")
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to send message")
        // Keep the session active so the user can retry
        setPhase("active")
      }
    },
    [sessionId, phase, appendMessage],
  )

  // ── complete ───────────────────────────────────────────────────────────────
  const complete = useCallback(async () => {
    if (!sessionId) {
      setError("No active session. Call start() first.")
      return
    }
    if (phase !== "active") return

    setPhase("completing")
    setError(null)

    try {
      const res = await completeAudit({ session_id: sessionId })
      setFinalReport(res.final_report)
      setPhase("done")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to complete audit")
      setPhase("active")
    }
  }, [sessionId, phase])

  // ── reset ──────────────────────────────────────────────────────────────────
  const reset = useCallback(() => {
    setPhase("idle")
    setSessionId(null)
    setDiagnosticSummary([])
    setMessages([])
    setFinalReport(null)
    setError(null)
  }, [])

  return {
    phase,
    sessionId,
    diagnosticSummary,
    messages,
    finalReport,
    error,
    start,
    send,
    complete,
    reset,
  }
}
