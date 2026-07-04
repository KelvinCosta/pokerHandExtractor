"use client"

import { useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import { Spade, Loader2 } from "lucide-react"

export default function LoginPage() {
  const { login } = useAuth()
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    const url = isLogin ? "http://localhost:8000/auth/login" : "http://localhost:8000/auth/register"
    
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      })
      
      const data = await res.json()
      
      if (!res.ok) {
        throw new Error(data.detail || "Erro de autenticação")
      }
      
      // Sucesso
      login(data.access_token)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-background text-foreground">
      <div className="w-full max-w-md space-y-8 rounded-xl border border-border bg-card p-10 shadow-lg">
        <div className="flex flex-col items-center gap-2">
          <div className="flex size-12 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Spade className="size-6" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight">Overlay Analytics</h2>
          <p className="text-sm text-muted-foreground">
            {isLogin ? "Entre com suas credenciais" : "Crie sua conta para acessar o datalake"}
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive text-center font-medium">
              {error}
            </div>
          )}
          
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-foreground">Email</label>
              <input
                type="email"
                required
                className="mt-1 block w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">Senha</label>
              <input
                type="password"
                required
                className="mt-1 block w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex w-full justify-center rounded-md bg-primary px-3 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50"
          >
            {loading ? <Loader2 className="mr-2 size-5 animate-spin" /> : (isLogin ? "Entrar" : "Registrar")}
          </button>
        </form>

        <div className="text-center text-sm">
          <span className="text-muted-foreground">
            {isLogin ? "Não tem uma conta? " : "Já tem uma conta? "}
          </span>
          <button
            onClick={() => {
              setIsLogin(!isLogin)
              setError(null)
            }}
            className="font-semibold text-primary hover:underline"
          >
            {isLogin ? "Registre-se" : "Faça Login"}
          </button>
        </div>
      </div>
    </div>
  )
}
