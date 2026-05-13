"use client"

import dynamic from "next/dynamic"
import type { SetStateAction } from "react"
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, useSyncExternalStore } from "react"
import { flushSync } from "react-dom"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { RegulatorySidebar } from "@/components/regulatory/regulatory-sidebar"
import {
  chatStorageKey,
  clearAllRegulatoryChatData,
  getRegulatorySessionIndexServerSnapshot,
  getRegulatorySessionIndexSnapshot,
  loadSessionIndex,
  type RegulatorySessionMeta,
  removeChatPayload,
  saveSessionIndex,
  subscribeRegulatorySessionIndex,
} from "@/lib/regulatory-chat-sessions"
import {
  chatBootstrap,
  chatCreateSession,
  chatDeleteSession,
  chatListSessions,
  chatPatchSession,
  remoteChatPersistenceEnabled,
} from "@/lib/chat-persistence-api"

const ResearchAgentChat = dynamic(
  () => import("@/components/chat/research-agent-chat").then((m) => m.ResearchAgentChat),
  {
    ssr: false,
    loading: () => (
      <div className="flex-1 flex flex-col min-h-0 min-w-0 border-l border-border/40 bg-[#fafafa] dark:bg-background">
        <div className="h-14 shrink-0 border-b border-border/40 bg-muted/20 animate-pulse" />
        <div className="flex-1 flex flex-col items-center justify-center p-8 gap-4 max-w-3xl mx-auto w-full">
          <div className="h-8 w-48 rounded-md bg-muted/40 animate-pulse" />
          <div className="h-32 w-full rounded-xl bg-muted/30 animate-pulse" />
          <div className="h-24 w-full rounded-xl bg-muted/25 animate-pulse" />
          <p className="text-xs text-muted-foreground pt-4">Loading assistant…</p>
        </div>
      </div>
    ),
  },
)

function RegulatoryIntelligenceRemote() {
  const [sessions, setSessions] = useState<RegulatorySessionMeta[]>([])
  const [activeSessionId, setActiveSessionId] = useState("")
  const [ready, setReady] = useState(false)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [pendingResearchIds, setPendingResearchIds] = useState<Set<string>>(() => new Set())
  const [starredOnly, setStarredOnly] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [searchPanelOpen, setSearchPanelOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const sessionsRef = useRef(sessions)
  sessionsRef.current = sessions

  const refreshSessions = useCallback(async () => {
    const list = await chatListSessions("regulatory")
    setSessions(list)
    return list
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        await chatBootstrap()
        const list = await chatListSessions("regulatory")
        if (cancelled) return
        if (list.length === 0) {
          const created = await chatCreateSession({ title: "New chat" })
          setSessions([created])
          setActiveSessionId(created.id)
        } else {
          setSessions(list)
          setActiveSessionId((id) => {
            if (id && list.some((s) => s.id === id)) return id
            return list[0].id
          })
        }
        setHistoryError(null)
      } catch (e) {
        if (!cancelled) {
          setHistoryError(e instanceof Error ? e.message : String(e))
          setSessions([])
          setActiveSessionId("")
        }
      } finally {
        if (!cancelled) setReady(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const visibleSessions = useMemo(() => {
    let list = [...sessions].sort((a, b) => b.updatedAt - a.updatedAt)
    if (starredOnly) list = list.filter((s) => s.starred)
    const q = searchQuery.trim().toLowerCase()
    if (q) list = list.filter((s) => s.title.toLowerCase().includes(q))
    return list
  }, [sessions, starredOnly, searchQuery])

  const onResearchRunChange = useCallback((sessionId: string, running: boolean) => {
    setPendingResearchIds((prev) => {
      const next = new Set(prev)
      if (running) next.add(sessionId)
      else next.delete(sessionId)
      return next
    })
  }, [])

  const mountedChatSessionIds = useMemo(() => {
    const m = new Set<string>()
    if (activeSessionId) m.add(activeSessionId)
    pendingResearchIds.forEach((id) => m.add(id))
    return Array.from(m)
  }, [activeSessionId, pendingResearchIds])

  const onNewChat = useCallback(async () => {
    try {
      const created = await chatCreateSession({ title: "New chat" })
      setSessions((prev) => [created, ...prev])
      setActiveSessionId(created.id)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const onSelectSession = useCallback((id: string) => {
    setActiveSessionId(id)
  }, [])

  const onDeleteSession = useCallback(
    async (id: string) => {
      try {
        await chatDeleteSession(id)
      } catch (e) {
        toast.error(e instanceof Error ? e.message : String(e))
        return
      }
      setPendingResearchIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
      const remaining = sessions.filter((s) => s.id !== id)
      if (remaining.length === 0) {
        try {
          const created = await chatCreateSession({ title: "New chat" })
          setSessions([created])
          setActiveSessionId(created.id)
        } catch (e) {
          toast.error(e instanceof Error ? e.message : String(e))
        }
        return
      }
      let nextFirstId = remaining[0].id
      flushSync(() => {
        setSessions(remaining)
      })
      flushSync(() => {
        setActiveSessionId((current) => (current === id ? nextFirstId : current))
      })
      void refreshSessions()
    },
    [refreshSessions, sessions],
  )

  const onRenameSession = useCallback(async (id: string, title: string) => {
    try {
      const updated = await chatPatchSession(id, { title, titlePinned: true })
      setSessions((prev) =>
        prev.map((s) => (s.id === id ? { ...updated, titlePinned: true } : s)),
      )
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const onToggleStar = useCallback(
    async (id: string) => {
      const cur = sessions.find((s) => s.id === id)
      const nextStar = !cur?.starred
      try {
        const updated = await chatPatchSession(id, { starred: nextStar })
        setSessions((prev) => prev.map((s) => (s.id === id ? updated : s)))
      } catch (e) {
        toast.error(e instanceof Error ? e.message : String(e))
      }
    },
    [sessions],
  )

  const onSessionActivity = useCallback(
    (payload: {
      sessionId: string
      title: string
      messageCount: number
      bumpOrder?: boolean
      lastMessageAt?: number
    }) => {
      const bump = payload.bumpOrder === true
      const orderAt = payload.lastMessageAt ?? Date.now()
      const cur = sessionsRef.current.find((s) => s.id === payload.sessionId)
      if (cur && !cur.titlePinned) {
        void chatPatchSession(payload.sessionId, { title: payload.title }).catch(() => {})
      }
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== payload.sessionId) return s
          if (s.titlePinned) {
            return bump ? { ...s, updatedAt: orderAt } : s
          }
          return bump
            ? { ...s, title: payload.title, updatedAt: orderAt }
            : { ...s, title: payload.title }
        }),
      )
    },
    [],
  )

  const onClearAllData = useCallback(async () => {
    try {
      for (const s of sessions) {
        await chatDeleteSession(s.id)
      }
      const created = await chatCreateSession({ title: "New chat" })
      setSessions([created])
      setActiveSessionId(created.id)
      setPendingResearchIds(new Set())
      setStarredOnly(false)
      setSearchQuery("")
      setSearchPanelOpen(false)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e))
    }
  }, [sessions])

  if (!ready) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-muted-foreground text-sm">
        Loading workspace…
      </div>
    )
  }

  if (historyError && sessions.length === 0) {
    return (
      <div className="h-screen flex flex-col items-center justify-center gap-3 bg-background p-6 text-center">
        <p className="text-sm text-muted-foreground max-w-md">
          Chat history is unavailable ({historyError}). You can still use the app once the database is configured.
        </p>
      </div>
    )
  }

  if (!activeSessionId || sessions.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-muted-foreground text-sm">
        Loading workspace…
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-row overflow-hidden bg-background relative">
      {historyError && (
        <div className="absolute top-2 left-1/2 z-50 -translate-x-1/2 rounded-md bg-amber-100 dark:bg-amber-950 px-3 py-1.5 text-xs text-amber-900 dark:text-amber-100 shadow">
          History sync issue: {historyError}
        </div>
      )}
      <RegulatorySidebar
        sessions={sessions}
        visibleSessions={visibleSessions}
        activeSessionId={activeSessionId}
        onNewChat={() => void onNewChat()}
        onSelectSession={onSelectSession}
        onDeleteSession={(id) => void onDeleteSession(id)}
        onRenameSession={(id, t) => void onRenameSession(id, t)}
        onToggleStar={(id) => void onToggleStar(id)}
        starredOnly={starredOnly}
        onStarredOnlyChange={setStarredOnly}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        searchPanelOpen={searchPanelOpen}
        onSearchPanelOpenChange={setSearchPanelOpen}
        settingsOpen={settingsOpen}
        onSettingsOpenChange={setSettingsOpen}
        onClearAllData={() => void onClearAllData()}
        pendingResearchSessionIds={Array.from(pendingResearchIds)}
      />

      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
        {mountedChatSessionIds.map((chatSessionId) => (
          <div
            key={chatSessionId}
            className={cn(
              "absolute inset-0 flex min-h-0 min-w-0 flex-col overflow-hidden bg-[#fafafa] dark:bg-background",
              chatSessionId === activeSessionId ? "z-10 visible" : "z-0 invisible pointer-events-none",
            )}
            aria-hidden={chatSessionId !== activeSessionId}
          >
            <ResearchAgentChat
              variant="regulatory"
              presentation="enterprise"
              sessionId={chatSessionId}
              onSessionActivity={onSessionActivity}
              welcomeAgentName="Regulatory Assistant"
              welcomeAgentType="regulatory"
              inputPlaceholder="Ask for requirements, gaps, or summaries from your uploaded context…"
              enableDocumentContext
              persistHistory={false}
              remotePersistence
              onResearchRunChange={onResearchRunChange}
              onConfirmDeleteSession={onDeleteSession}
              fileAccept=".pdf,.docx,.txt,.csv"
            />
          </div>
        ))}
      </div>
    </div>
  )
}

export default function RegulatoryIntelligencePage() {
  const useRemote = remoteChatPersistenceEnabled()

  if (useRemote) {
    return <RegulatoryIntelligenceRemote />
  }

  const indexJson = useSyncExternalStore(
    subscribeRegulatorySessionIndex,
    getRegulatorySessionIndexSnapshot,
    getRegulatorySessionIndexServerSnapshot,
  )

  const sessions = useMemo((): RegulatorySessionMeta[] => {
    try {
      const arr = JSON.parse(indexJson) as RegulatorySessionMeta[]
      return Array.isArray(arr) ? arr : []
    } catch {
      return []
    }
  }, [indexJson])

  const [activeSessionId, setActiveSessionId] = useState("")
  const [starredOnly, setStarredOnly] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [searchPanelOpen, setSearchPanelOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [pendingResearchIds, setPendingResearchIds] = useState<Set<string>>(() => new Set())

  const setSessions = useCallback((updater: SetStateAction<RegulatorySessionMeta[]>) => {
    const prev = loadSessionIndex()
    const next = typeof updater === "function" ? (updater as (p: RegulatorySessionMeta[]) => RegulatorySessionMeta[])(prev) : updater
    saveSessionIndex(next)
  }, [])

  useLayoutEffect(() => {
    if (sessions.length === 0) return
    setActiveSessionId((id) => (id && sessions.some((s) => s.id === id) ? id : sessions[0].id))
  }, [sessions])

  const visibleSessions = useMemo(() => {
    let list = [...sessions].sort((a, b) => b.updatedAt - a.updatedAt)
    if (starredOnly) list = list.filter((s) => s.starred)
    const q = searchQuery.trim().toLowerCase()
    if (q) list = list.filter((s) => s.title.toLowerCase().includes(q))
    return list
  }, [sessions, starredOnly, searchQuery])

  const onResearchRunChange = useCallback((sessionId: string, running: boolean) => {
    setPendingResearchIds((prev) => {
      const next = new Set(prev)
      if (running) next.add(sessionId)
      else next.delete(sessionId)
      return next
    })
  }, [])

  const mountedChatSessionIds = useMemo(() => {
    const m = new Set<string>()
    if (activeSessionId) m.add(activeSessionId)
    pendingResearchIds.forEach((id) => m.add(id))
    return Array.from(m)
  }, [activeSessionId, pendingResearchIds])

  const onNewChat = useCallback(() => {
    const id = crypto.randomUUID()
    const next: RegulatorySessionMeta = { id, title: "New chat", updatedAt: Date.now() }
    setSessions((prev) => [next, ...prev])
    setActiveSessionId(id)
  }, [setSessions])

  const onSelectSession = useCallback((id: string) => {
    setActiveSessionId(id)
  }, [])

  const onDeleteSession = useCallback(
    (id: string) => {
      removeChatPayload(id)
      setPendingResearchIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
      let nextFirstId = ""
      flushSync(() => {
        setSessions((prev) => {
          const filtered = prev.filter((s) => s.id !== id)
          const next =
            filtered.length > 0
              ? filtered
              : [{ id: crypto.randomUUID(), title: "New chat", updatedAt: Date.now() }]
          nextFirstId = next[0].id
          return next
        })
      })
      flushSync(() => {
        setActiveSessionId((current) => (current === id ? nextFirstId : current))
      })
    },
    [setSessions],
  )

  const onRenameSession = useCallback(
    (id: string, title: string) => {
      setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title, titlePinned: true } : s)))
    },
    [setSessions],
  )

  const onToggleStar = useCallback(
    (id: string) => {
      setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, starred: !s.starred } : s)))
    },
    [setSessions],
  )

  const onSessionActivity = useCallback(
    (payload: {
      sessionId: string
      title: string
      messageCount: number
      bumpOrder?: boolean
      lastMessageAt?: number
    }) => {
      const bump = payload.bumpOrder === true
      const orderAt = payload.lastMessageAt ?? Date.now()
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== payload.sessionId) return s
          if (s.titlePinned) {
            return bump ? { ...s, updatedAt: orderAt } : s
          }
          return bump
            ? { ...s, title: payload.title, updatedAt: orderAt }
            : { ...s, title: payload.title }
        }),
      )
    },
    [setSessions],
  )

  const onClearAllData = useCallback(() => {
    clearAllRegulatoryChatData()
    const id = crypto.randomUUID()
    saveSessionIndex([{ id, title: "New chat", updatedAt: Date.now() }])
    setActiveSessionId(id)
    setPendingResearchIds(new Set())
    setStarredOnly(false)
    setSearchQuery("")
    setSearchPanelOpen(false)
  }, [])

  if (!activeSessionId || sessions.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-muted-foreground text-sm">
        Loading workspace…
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-row overflow-hidden bg-background">
      <RegulatorySidebar
        sessions={sessions}
        visibleSessions={visibleSessions}
        activeSessionId={activeSessionId}
        onNewChat={onNewChat}
        onSelectSession={onSelectSession}
        onDeleteSession={onDeleteSession}
        onRenameSession={onRenameSession}
        onToggleStar={onToggleStar}
        starredOnly={starredOnly}
        onStarredOnlyChange={setStarredOnly}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        searchPanelOpen={searchPanelOpen}
        onSearchPanelOpenChange={setSearchPanelOpen}
        settingsOpen={settingsOpen}
        onSettingsOpenChange={setSettingsOpen}
        onClearAllData={onClearAllData}
        pendingResearchSessionIds={Array.from(pendingResearchIds)}
      />

      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
        {mountedChatSessionIds.map((chatSessionId) => (
          <div
            key={chatSessionId}
            className={cn(
              "absolute inset-0 flex min-h-0 min-w-0 flex-col overflow-hidden bg-[#fafafa] dark:bg-background",
              chatSessionId === activeSessionId ? "z-10 visible" : "z-0 invisible pointer-events-none",
            )}
            aria-hidden={chatSessionId !== activeSessionId}
          >
            <ResearchAgentChat
              variant="regulatory"
              presentation="enterprise"
              sessionId={chatSessionId}
              onSessionActivity={onSessionActivity}
              welcomeAgentName="Regulatory Assistant"
              welcomeAgentType="regulatory"
              inputPlaceholder="Ask for requirements, gaps, or summaries from your uploaded context…"
              enableDocumentContext
              persistHistory
              storageKey={chatStorageKey(chatSessionId)}
              onResearchRunChange={onResearchRunChange}
              onConfirmDeleteSession={onDeleteSession}
              fileAccept=".pdf,.docx,.txt,.csv"
            />
          </div>
        ))}
      </div>
    </div>
  )
}
