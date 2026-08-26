"use client"

import { useState, useEffect, useRef } from "react"
import { apiUpload, fetchProcessedFiles } from "@/lib/api"
import {
  UploadCloud, CheckCircle2, Loader2, RefreshCcw,
  AlertTriangle, X, FileText, AlertCircle,
} from "lucide-react"
import { cn } from "@/lib/utils"

function formatBytes(bytes: number) {
  if (bytes < 1024)       return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function ImportView() {
  const [platform,        setPlatform]        = useState("ggpoker")
  const [heroName,        setHeroName]        = useState("")
  const [files,           setFiles]           = useState<File[]>([])
  const [processedList,   setProcessedList]   = useState<string[]>([])
  const [versionMismatch, setVersionMismatch] = useState(false)
  const [loading,         setLoading]         = useState(false)
  const [successMsg,      setSuccessMsg]      = useState<string | null>(null)
  const [errorMsg,        setErrorMsg]        = useState<string | null>(null)
  const [isDragging,      setIsDragging]      = useState(false)
  const dropRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchProcessedFiles()
      .then(res => {
        setProcessedList(res.processed)
        setVersionMismatch(res.version_mismatch)
      })
      .catch(console.error)
  }, [])

  const processSelectedFiles = async (selectedFiles: File[]) => {
    const valid: File[] = []
    for (const file of selectedFiles) {
      let isSummary = false
      try {
        const text = await file.slice(0, 100).text()
        isSummary = text.startsWith("Tournament #")
      } catch (_) {}

      let name = file.name
      if (isSummary && !name.toLowerCase().endsWith("_summary.txt")) {
        const dot = name.lastIndexOf(".")
        if (dot > 0) name = name.slice(0, dot) + "_summary" + name.slice(dot)
      }

      if (!processedList.includes(name)) valid.push(file)
    }

    const skipped = selectedFiles.length - valid.length
    if (skipped > 0) {
      setErrorMsg(`${skipped} already-processed file(s) skipped.`)
      setTimeout(() => setErrorMsg(null), 5000)
    }
    setFiles((prev) => {
      const existingNames = new Set(prev.map((f) => f.name))
      return [...prev, ...valid.filter((f) => !existingNames.has(f.name))]
    })
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) await processSelectedFiles(Array.from(e.target.files))
    e.target.value = ""
  }

  // Drag and drop handlers
  const onDragOver  = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true)  }
  const onDragLeave = ()                      => setIsDragging(false)
  const onDrop      = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files) await processSelectedFiles(Array.from(e.dataTransfer.files))
  }

  const removeFile = (name: string) =>
    setFiles((prev) => prev.filter((f) => f.name !== name))

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (files.length === 0) { setErrorMsg("Select at least one file."); return }

    setLoading(true)
    setErrorMsg(null)
    setSuccessMsg(null)

    const CHUNK_SIZE = 500;
    let totalUploaded = 0;
    let totalProcessed = 0;

    try {
      for (let i = 0; i < files.length; i += CHUNK_SIZE) {
        const chunk = files.slice(i, i + CHUNK_SIZE);
        const formData = new FormData()
        formData.append("platform",  platform)
        formData.append("hero_name", heroName)
        chunk.forEach((file) => formData.append("files", file))

        const result = await apiUpload("/api/etl/upload", formData)
        totalUploaded += result.new_files || 0;
        totalProcessed += result.hands_processed || 0;
      }
      setSuccessMsg(`ETL completed successfully — ${totalUploaded} files uploaded, ${totalProcessed} hands processed.`)
      setFiles([])
    } catch (err: any) {
      setErrorMsg(err.message || "Upload error")
    } finally {
      setLoading(false)
    }
  }

  const handleReprocess = async () => {
    setLoading(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/etl/reprocess`,
        { method: "POST", headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` } },
      )
      if (!res.ok) throw new Error("Reprocess failed")
      const result = await res.json()
      setSuccessMsg(`${result.message} — ${result.new_files} files reprocessed, ${result.hands_processed} hands loaded.`)
      setVersionMismatch(false)
      fetchProcessedFiles().then(r => setProcessedList(r.processed)).catch(console.error)
    } catch (err: any) {
      setErrorMsg(err.message || "Reprocess error")
    } finally {
      setLoading(false)
    }
  }

  const totalBytes = files.reduce((sum, f) => sum + f.size, 0)

  return (
    <div className="flex flex-1 flex-col">
      <div className="mx-auto w-full max-w-2xl space-y-5 py-2">

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div>
          <h2 className="text-xl font-bold tracking-tight">Hand History ETL</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Upload raw hand history files (.txt) to feed the Silver Datalake.
          </p>
        </div>

        {/* ── Version mismatch alert ─────────────────────────────────────── */}
        {versionMismatch && (
          <div className="rounded-xl border border-amber-500/25 bg-amber-500/8 p-5">
            <div className="mb-1.5 flex items-center gap-2">
              <AlertTriangle className="size-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-amber-300">Schema Update Detected</h3>
            </div>
            <p className="mb-4 text-sm text-muted-foreground">
              The Datalake schema has been updated. No need to re-upload files — click below to rebuild automatically.
            </p>
            <button
              onClick={handleReprocess}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-amber-950 transition-colors hover:bg-amber-400 disabled:opacity-50"
            >
              {loading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCcw className="size-4" />}
              Rebuild Datalake
            </button>
          </div>
        )}

        {/* ── Form ────────────────────────────────────────────────────────── */}
        <form onSubmit={handleUpload} className="space-y-5 rounded-xl border border-border bg-card p-6">

          {/* Status messages */}
          {errorMsg && (
            <div className="flex items-start gap-2.5 rounded-lg border border-rose-500/20 bg-rose-500/8 p-3.5 text-sm text-rose-400">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}
          {successMsg && (
            <div className="flex items-start gap-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/8 p-3.5 text-sm text-emerald-400">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Config row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Platform</label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full rounded-lg border border-input bg-zinc-900/60 px-3 py-2 text-sm text-foreground outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20"
              >
                <option value="ggpoker">GGPoker</option>
                <option value="pokerstars">PokerStars</option>
                <option value="partypoker">PartyPoker</option>
                <option value="ipoker">iPoker Network</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Hero Nickname</label>
              <input
                type="text"
                required
                value={heroName}
                onChange={(e) => setHeroName(e.target.value)}
                placeholder="e.g. Lorkel"
                className="w-full rounded-lg border border-input bg-zinc-900/60 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/40 outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20"
              />
            </div>
          </div>

          {/* Drop zone */}
          <div className="space-y-1.5">
            <label className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Hand History Files (.txt)</label>
            <div
              ref={dropRef}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
              className={cn(
                "flex h-36 w-full flex-col items-center justify-center rounded-xl border-2 border-dashed transition-all duration-200",
                isDragging
                  ? "border-primary/60 bg-primary/8 scale-[1.01]"
                  : "border-zinc-700 bg-zinc-900/40 hover:border-zinc-600 hover:bg-zinc-900/60",
              )}
            >
              <UploadCloud className={cn("mb-2 size-8 transition-colors", isDragging ? "text-primary" : "text-muted-foreground/50")} />
              <p className="text-sm text-muted-foreground">
                Drag & drop files, or{" "}
                <label htmlFor="file-upload" className="cursor-pointer font-semibold text-primary hover:underline">browse</label>
                {" "}·{" "}
                <label htmlFor="dir-upload" className="cursor-pointer font-semibold text-primary hover:underline">select folder</label>
              </p>
              <p className="mt-1 font-mono text-[10px] text-muted-foreground/40">{platform.toUpperCase()} .txt format</p>
              <input id="file-upload" type="file" multiple className="hidden" onChange={handleFileChange} />
              {/* @ts-ignore */}
              <input id="dir-upload" type="file" multiple webkitdirectory="true" className="hidden" onChange={handleFileChange} />
            </div>
          </div>

          {/* Selected file list */}
          {files.length > 0 && (
            <div className="rounded-xl border border-border bg-zinc-900/40">
              <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  {files.length} file{files.length !== 1 ? "s" : ""} · {formatBytes(totalBytes)}
                </p>
                <button
                  type="button"
                  onClick={() => setFiles([])}
                  className="font-mono text-[10px] text-muted-foreground/60 hover:text-foreground transition-colors"
                >
                  Clear all
                </button>
              </div>
              <ul className="max-h-44 overflow-y-auto divide-y divide-border scrollbar-thin">
                {files.map((f) => (
                  <li key={f.name} className="flex items-center gap-2.5 px-4 py-2 hover:bg-zinc-800/40">
                    <FileText className="size-3.5 shrink-0 text-muted-foreground/50" />
                    <span className="flex-1 truncate font-mono text-xs text-zinc-300">{f.name}</span>
                    <span className="font-mono text-[10px] text-muted-foreground/50 shrink-0">{formatBytes(f.size)}</span>
                    <button
                      type="button"
                      onClick={() => removeFile(f.name)}
                      className="shrink-0 rounded p-0.5 text-muted-foreground/40 hover:bg-zinc-700 hover:text-foreground transition-colors"
                    >
                      <X className="size-3" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Submit */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading || files.length === 0}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-[0_0_16px_rgba(16,185,129,0.25)] transition-all hover:bg-primary/90 hover:shadow-[0_0_24px_rgba(16,185,129,0.35)] disabled:opacity-40 disabled:shadow-none"
            >
              {loading ? (
                <><Loader2 className="size-4 animate-spin" />Processing…</>
              ) : (
                <><UploadCloud className="size-4" />Start Import</>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
