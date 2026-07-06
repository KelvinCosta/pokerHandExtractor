"use client"

import { useState } from "react"
import { apiUpload } from "@/lib/api"
import { UploadCloud, CheckCircle2, Loader2, RefreshCcw } from "lucide-react"

export function ImportView() {
  const [platform, setPlatform] = useState("ggpoker")
  const [heroName, setHeroName] = useState("")
  const [files, setFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files))
    }
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (files.length === 0) {
      setErrorMsg("Selecione pelo menos um arquivo ou diretório.")
      return
    }

    setLoading(true)
    setErrorMsg(null)
    setSuccessMsg(null)

    const formData = new FormData()
    formData.append("platform", platform)
    formData.append("hero_name", heroName)
    files.forEach((file) => {
      formData.append("files", file)
    })

    try {
      const result = await apiUpload("/api/etl/upload", formData)
      setSuccessMsg(`${result.message} - ${result.new_files} arquivos enviados, ${result.hands_processed} mãos carregadas!`)
      setFiles([])
    } catch (err: any) {
      setErrorMsg(err.message || "Erro no upload")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col p-6">
      <div className="mx-auto w-full max-w-3xl space-y-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">ETL de Histórico de Mãos</h2>
          <p className="text-muted-foreground">
            Faça upload dos seus arquivos brutos (.txt) para alimentar o Datalake.
          </p>
        </div>

        <form onSubmit={handleUpload} className="space-y-6 rounded-xl border border-border bg-card p-6 shadow-sm">
          {errorMsg && (
            <div className="rounded-md bg-destructive/15 p-4 text-sm font-medium text-destructive">
              {errorMsg}
            </div>
          )}

          {successMsg && (
            <div className="flex items-center gap-2 rounded-md bg-emerald-500/15 p-4 text-sm font-medium text-emerald-500">
              <CheckCircle2 className="size-5" />
              {successMsg}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Plataforma</label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="ggpoker">GGPoker</option>
                <option value="pokerstars" disabled>PokerStars (Em breve)</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Hero Name (Seu Nick)</label>
              <input
                type="text"
                required
                value={heroName}
                onChange={(e) => setHeroName(e.target.value)}
                placeholder="Ex: Lorkel"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Arquivos ou Diretório (.txt)</label>
            <div className="flex h-32 w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 bg-muted/30 transition-colors hover:bg-muted/50">
              <div className="flex flex-col items-center gap-2 text-center">
                <UploadCloud className="size-8 text-muted-foreground" />
                <div className="text-sm text-muted-foreground">
                  <label htmlFor="file-upload" className="cursor-pointer font-semibold text-primary hover:underline">
                    Selecionar Arquivos
                  </label>{" "}
                  ou{" "}
                  <label htmlFor="dir-upload" className="cursor-pointer font-semibold text-primary hover:underline">
                    Selecionar Pasta
                  </label>
                </div>
                <input
                  id="file-upload"
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleFileChange}
                />
                <input
                  id="dir-upload"
                  type="file"
                  multiple
                  /* @ts-ignore - webkitdirectory não está nativamente tipado no React DOM standard mas funciona nos navegadores modernos */
                  webkitdirectory="true"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
            </div>
            {files.length > 0 && (
              <p className="text-xs font-medium text-muted-foreground">
                {files.length} arquivo(s) selecionado(s).
              </p>
            )}
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading || files.length === 0}
              className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" /> Processando...
                </>
              ) : (
                <>
                  <RefreshCcw className="mr-2 size-4" /> Iniciar Importação
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
