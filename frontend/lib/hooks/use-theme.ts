"use client"

import { useEffect, useState } from "react"

export type Theme = "light" | "dark"

export function useTheme() {
  const [theme, setTheme] = useState<Theme | undefined>(undefined)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const savedTheme = localStorage.getItem("theme") as Theme | null
    const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
    const initialTheme = savedTheme || systemTheme

    setTheme(initialTheme)
    document.documentElement.classList.toggle("dark", initialTheme === "dark")

    console.log("[v0] Theme initialized:", initialTheme)
  }, [])

  const toggleTheme = () => {
    if (!theme) return

    const newTheme = theme === "dark" ? "light" : "dark"
    console.log("[v0] Toggling theme from", theme, "to", newTheme)

    setTheme(newTheme)
    localStorage.setItem("theme", newTheme)
    document.documentElement.classList.toggle("dark", newTheme === "dark")
  }

  return {
    theme: mounted ? theme : "dark",
    toggleTheme,
    mounted,
  }
}
