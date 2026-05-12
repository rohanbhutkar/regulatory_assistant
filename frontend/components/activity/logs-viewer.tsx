"use client"

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { X, Terminal, Trash2, Filter } from "lucide-react"
import { cn } from "@/lib/utils"

interface LogEntry {
  timestamp: string
  message: string
  source: string
  level: "debug" | "info" | "warning" | "error"
}

/** Match multi-agent chat: NEXT_PUBLIC_AGENT_WS_URL or derive from NEXT_PUBLIC_API_URL. */
function getAgentWsRoot(): string {
  const explicit = process.env.NEXT_PUBLIC_AGENT_WS_URL?.trim()
  if (explicit) {
    return explicit.replace(/\/$/, "")
  }
  const api = process.env.NEXT_PUBLIC_API_URL?.trim() || "http://127.0.0.1:8001"
  try {
    const u = new URL(api)
    const proto = u.protocol === "https:" ? "wss:" : "ws:"
    return `${proto}//${u.host}/ws`
  } catch {
    return "ws://127.0.0.1:8001/ws"
  }
}

const MAX_STORED_LOGS = 500
const PING_MS = 25_000

export type BackendLogsContextValue = {
  open: () => void
  close: () => void
  toggle: () => void
  isOpen: boolean
  errorCount: number
}

const BackendLogsContext = createContext<BackendLogsContextValue | null>(null)

export function useBackendLogs(): BackendLogsContextValue {
  const ctx = useContext(BackendLogsContext)
  if (!ctx) {
    throw new Error("useBackendLogs must be used within BackendLogsProvider")
  }
  return ctx
}

export function BackendLogsProvider({ children }: { children: React.ReactNode }) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [filter, setFilter] = useState<"all" | "error" | "warning" | "info">("all")
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const pushSystem = useCallback((message: string, level: LogEntry["level"] = "info") => {
    setLogs((prev) =>
      [
        ...prev,
        {
          timestamp: new Date().toISOString(),
          message,
          source: "system",
          level,
        },
      ].slice(-MAX_STORED_LOGS),
    )
  }, [])

  useEffect(() => {
    let cancelled = false
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let pingTimer: ReturnType<typeof setInterval> | null = null
    let attempt = 0
    let activeWs: WebSocket | null = null

    const clearPing = () => {
      if (pingTimer) {
        clearInterval(pingTimer)
        pingTimer = null
      }
    }

    const connect = () => {
      if (cancelled) return

      clearPing()
      activeWs?.close()
      activeWs = null

      const clientId = `logs_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`
      const root = getAgentWsRoot()
      const url = `${root}/${clientId}`

      const ws = new WebSocket(url)
      activeWs = ws
      wsRef.current = ws

      ws.onopen = () => {
        if (cancelled) return
        attempt = 0
        pushSystem("✅ Logs WebSocket connected")
        pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }))
          }
        }, PING_MS)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === "pong") return

          if (data.type === "log_event" && data.log) {
            setLogs((prev) => [...prev, data.log as LogEntry].slice(-MAX_STORED_LOGS))
            return
          }
          if (data.type === "activity_event" && data.message) {
            const logEntry: LogEntry = {
              timestamp: data.timestamp || new Date().toISOString(),
              message: data.message,
              source: data.operation_type || "activity",
              level: data.event_type?.includes("error")
                ? "error"
                : data.event_type?.includes("warning")
                  ? "warning"
                  : "info",
            }
            setLogs((prev) => [...prev, logEntry].slice(-MAX_STORED_LOGS))
          }
        } catch {
          /* ignore malformed frames */
        }
      }

      ws.onerror = () => {
        /* connection errors are surfaced via onclose + pushSystem */
      }

      ws.onclose = () => {
        clearPing()
        wsRef.current = null
        if (cancelled) return

        attempt += 1
        const delay = Math.min(30_000, Math.round(800 * Math.pow(1.6, Math.min(attempt, 14))))
        pushSystem(`Logs WebSocket disconnected — reconnecting in ~${Math.ceil(delay / 1000)}s`, "warning")

        reconnectTimer = setTimeout(() => {
          reconnectTimer = null
          connect()
        }, delay)
      }
    }

    connect()

    return () => {
      cancelled = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      clearPing()
      activeWs?.close()
      wsRef.current = null
    }
  }, [pushSystem])

  useEffect(() => {
    if (!scrollAreaRef.current) return
    const scrollContainer = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]")
    if (scrollContainer) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight
    }
  }, [logs])

  const filteredLogs = logs.filter((log) => {
    if (filter === "all") return true
    return log.level === filter
  })

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case "error":
        return "text-red-500 bg-red-500/10 border-red-500/20"
      case "warning":
        return "text-yellow-500 bg-yellow-500/10 border-yellow-500/20"
      case "info":
        return "text-blue-500 bg-blue-500/10 border-blue-500/20"
      default:
        return "text-gray-500 bg-gray-500/10 border-gray-500/20"
    }
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString()
    } catch {
      return timestamp
    }
  }

  const clearLogs = () => {
    setLogs([])
  }

  const errorCount = useMemo(() => logs.filter((l) => l.level === "error").length, [logs])

  const open = useCallback(() => setIsOpen(true), [])
  const close = useCallback(() => setIsOpen(false), [])
  const toggle = useCallback(() => setIsOpen((o) => !o), [])

  const ctxValue = useMemo<BackendLogsContextValue>(
    () => ({
      open,
      close,
      toggle,
      isOpen,
      errorCount,
    }),
    [open, close, toggle, isOpen, errorCount],
  )

  return (
    <BackendLogsContext.Provider value={ctxValue}>
      {children}
      {isOpen ? (
        <div className="fixed top-16 right-4 z-50 w-[min(600px,calc(100vw-2rem))] max-h-[min(600px,calc(100vh-5rem))]">
          <Card className="shadow-2xl">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <Terminal className="h-5 w-5 shrink-0" />
                  <CardTitle className="text-lg truncate">Backend Logs</CardTitle>
                  <Badge variant="secondary" className="shrink-0">
                    {logs.length} logs
                  </Badge>
                  {errorCount > 0 && (
                    <Badge variant="destructive" className="shrink-0">
                      {errorCount} errors
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() =>
                      setFilter(filter === "all" ? "error" : filter === "error" ? "warning" : filter === "warning" ? "info" : "all")
                    }
                    title="Filter"
                  >
                    <Filter className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={clearLogs} title="Clear logs">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsOpen(false)} title="Close">
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="flex gap-1 mt-2 flex-wrap">
                <Button
                  variant={filter === "all" ? "default" : "ghost"}
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => setFilter("all")}
                >
                  All ({logs.length})
                </Button>
                <Button
                  variant={filter === "error" ? "default" : "ghost"}
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => setFilter("error")}
                >
                  Errors ({logs.filter((l) => l.level === "error").length})
                </Button>
                <Button
                  variant={filter === "warning" ? "default" : "ghost"}
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => setFilter("warning")}
                >
                  Warnings ({logs.filter((l) => l.level === "warning").length})
                </Button>
                <Button
                  variant={filter === "info" ? "default" : "ghost"}
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => setFilter("info")}
                >
                  Info ({logs.filter((l) => l.level === "info").length})
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[min(450px,calc(100vh-14rem))]" ref={scrollAreaRef}>
                <div className="p-3 space-y-1 font-mono text-xs">
                  {filteredLogs.length === 0 ? (
                    <div className="text-center text-sm text-muted-foreground py-8">
                      No logs {filter !== "all" ? `with level ${filter}` : ""}
                    </div>
                  ) : (
                    filteredLogs.map((log, index) => (
                      <div key={index} className={cn("p-2 rounded border", getLogLevelColor(log.level))}>
                        <div className="flex items-start gap-2">
                          <span className="text-muted-foreground text-[10px] min-w-[60px]">
                            {formatTimestamp(log.timestamp)}
                          </span>
                          <Badge variant="outline" className={cn("text-[10px] h-4", getLogLevelColor(log.level))}>
                            {log.level}
                          </Badge>
                          <span className="flex-1 break-words">{log.message}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </BackendLogsContext.Provider>
  )
}
