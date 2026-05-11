"use client"

import dynamic from "next/dynamic"
import type { SetStateAction } from "react"
import { useCallback, useLayoutEffect, useMemo, useState, useSyncExternalStore } from "react"
import { flushSync } from "react-dom"
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

/** Ephemeral welcome (not saved to chat history); hidden after the first message. */

export default function RegulatoryIntelligencePage() {
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
  const [libraryOpen, setLibraryOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

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

  const onNewChat = useCallback(() => {
    const id = crypto.randomUUID()
    const next: RegulatorySessionMeta = { id, title: "New chat", updatedAt: Date.now() }
    setSessions((prev) => [next, ...prev])
    setActiveSessionId(id)
  }, [setSessions])

  const onSelectSession = useCallback(
    (id: string) => {
      setActiveSessionId(id)
      setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, updatedAt: Date.now() } : s)))
    },
    [setSessions],
  )

  const onDeleteSession = useCallback(
    (id: string) => {
      removeChatPayload(id)
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
      setSessions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, title, titlePinned: true, updatedAt: Date.now() } : s)),
      )
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
    (payload: { sessionId: string; title: string; messageCount: number }) => {
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== payload.sessionId) return s
          if (s.titlePinned) {
            return { ...s, updatedAt: Date.now() }
          }
          return { ...s, title: payload.title, updatedAt: Date.now() }
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
        libraryOpen={libraryOpen}
        onLibraryOpenChange={setLibraryOpen}
        settingsOpen={settingsOpen}
        onSettingsOpenChange={setSettingsOpen}
        onClearAllData={onClearAllData}
      />

      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        <ResearchAgentChat
          key={activeSessionId}
          variant="regulatory"
          presentation="enterprise"
          sessionId={activeSessionId}
          onSessionActivity={onSessionActivity}
          welcomeAgentName="Regulatory Assistant"
          welcomeAgentType="regulatory"
          inputPlaceholder="Ask for requirements, gaps, or summaries from your uploaded context…"
          enableDocumentContext
          persistHistory
          storageKey={chatStorageKey(activeSessionId)}
          fileAccept=".pdf,.docx,.txt,.csv"
        />
      </div>
    </div>
  )
}
