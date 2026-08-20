"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"

export function useAuth() {
  const isAuthenticated = true
  const router = useRouter()

  const login = (token: string) => {
    router.push("/")
  }

  const logout = () => {
    // No-op for offline MVP
  }

  return { isAuthenticated, login, logout }
}
