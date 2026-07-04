"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)
  const router = useRouter()

  useEffect(() => {
    const token = localStorage.getItem("access_token")
    if (token) {
      setIsAuthenticated(true)
    } else {
      setIsAuthenticated(false)
      // Redireciona para o login se não estiver na página de login
      if (window.location.pathname !== "/login") {
        router.push("/login")
      }
    }
  }, [router])

  const login = (token: string) => {
    localStorage.setItem("access_token", token)
    setIsAuthenticated(true)
    router.push("/")
  }

  const logout = () => {
    localStorage.removeItem("access_token")
    setIsAuthenticated(false)
    router.push("/login")
  }

  return { isAuthenticated, login, logout }
}
