"use client"

import { useState } from "react"
import Link from "next/link"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { RegulatorySessionMeta } from "@/lib/regulatory-chat-sessions"
import { cn } from "@/lib/utils"
import {
  ChevronDown,
  Loader2,
  MessageSquarePlus,
  MoreHorizontal,
  Search,
  Settings,
  Star,
  Trash2,
} from "lucide-react"

const CHAT_PREVIEW_LIMIT = 10

interface RegulatorySidebarProps {
  sessions: RegulatorySessionMeta[]
  visibleSessions: RegulatorySessionMeta[]
  activeSessionId: string
  onNewChat: () => void
  onSelectSession: (id: string) => void
  onDeleteSession: (id: string) => void
  onRenameSession: (id: string, title: string) => void
  onToggleStar: (id: string) => void
  starredOnly: boolean
  onStarredOnlyChange: (value: boolean) => void
  searchQuery: string
  onSearchQueryChange: (value: string) => void
  searchPanelOpen: boolean
  onSearchPanelOpenChange: (value: boolean) => void
  settingsOpen: boolean
  onSettingsOpenChange: (value: boolean) => void
  onClearAllData: () => void
  className?: string
  /** When set, show a small loading indicator on that session row (research in flight). */
  pendingResearchSessionId?: string | null
}

export function RegulatorySidebar({
  sessions,
  visibleSessions,
  activeSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
  onToggleStar,
  starredOnly,
  onStarredOnlyChange,
  searchQuery,
  onSearchQueryChange,
  searchPanelOpen,
  onSearchPanelOpenChange,
  settingsOpen,
  onSettingsOpenChange,
  onClearAllData,
  className,
  pendingResearchSessionId,
}: RegulatorySidebarProps) {
  const sessionList = sessions ?? []
  const visibleList = visibleSessions ?? []

  const [chatsExpanded, setChatsExpanded] = useState(false)
  const [brandLogoFailed, setBrandLogoFailed] = useState(false)
  const [renameId, setRenameId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState("")
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null)

  const showMore = visibleList.length > CHAT_PREVIEW_LIMIT
  const displayedChats = chatsExpanded
    ? visibleList
    : visibleList.slice(0, CHAT_PREVIEW_LIMIT)

  const openRename = (s: RegulatorySessionMeta) => {
    setRenameId(s.id)
    setRenameValue(s.title)
    setMenuOpenId(null)
  }

  const commitRename = () => {
    if (renameId && renameValue.trim()) {
      onRenameSession(renameId, renameValue.trim())
    }
    setRenameId(null)
  }

  const starredCount = sessionList.filter((s) => s.starred).length

  return (
    <aside
      className={cn(
        "flex flex-col h-full min-h-0 w-[272px] shrink-0 border-r border-border/50 bg-muted/30 text-foreground",
        className,
      )}
    >
      <div className="shrink-0 px-2 pt-3 pb-2 border-b border-border/40">
        <Link
          href="/regulatory-intelligence"
          className="flex items-center gap-2.5 rounded-xl px-2 py-2 hover:bg-background/80 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-muted/30"
          aria-label="Lotor Lab — Regulatory intelligence home"
        >
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border/60 bg-card shadow-sm">
            {brandLogoFailed ? (
              <span className="text-[10px] font-semibold text-muted-foreground" aria-hidden>
                LL
              </span>
            ) : (
              <img
                src="/lotor-lab-logo.png"
                alt=""
                width={36}
                height={36}
                decoding="async"
                className="h-7 w-7 object-contain"
                onError={() => setBrandLogoFailed(true)}
              />
            )}
          </div>
          <div className="min-w-0 flex flex-col text-left leading-tight">
            <span className="text-sm font-semibold tracking-tight text-foreground truncate">Lotor Lab</span>
            <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground truncate">
              Regulatory
            </span>
          </div>
        </Link>
      </div>

      <div className="p-3 space-y-1 border-b border-border/40">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 h-10 px-3 rounded-xl text-sm font-medium hover:bg-background/80"
          onClick={onNewChat}
        >
          <MessageSquarePlus className="h-4 w-4 text-muted-foreground" />
          New chat
        </Button>
        <Button
          variant={searchPanelOpen ? "secondary" : "ghost"}
          className="w-full justify-start gap-3 h-10 px-3 rounded-xl text-sm hover:bg-background/80"
          type="button"
          onClick={() => onSearchPanelOpenChange(!searchPanelOpen)}
        >
          <Search className="h-4 w-4 text-muted-foreground" />
          Search chats
        </Button>
        {searchPanelOpen && (
          <Input
            placeholder="Filter by title…"
            value={searchQuery}
            onChange={(e) => onSearchQueryChange(e.target.value)}
            className="h-9 rounded-lg text-sm"
            autoFocus
          />
        )}
        <Button
          variant={starredOnly ? "secondary" : "ghost"}
          className="w-full justify-start gap-3 h-10 px-3 rounded-xl text-sm hover:bg-background/80"
          type="button"
          onClick={() => onStarredOnlyChange(!starredOnly)}
        >
          <Star
            className={cn("h-4 w-4", starredOnly ? "fill-amber-400 text-amber-500" : "text-muted-foreground")}
          />
          Starred
          {starredCount > 0 && (
            <span className="ml-auto text-[11px] tabular-nums text-muted-foreground">{starredCount}</span>
          )}
        </Button>
      </div>

      <div className="flex flex-1 flex-col min-h-0 border-t border-border/30">
        <div className="px-3 pt-2 pb-1 shrink-0">
          <p className="px-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Chats</p>
        </div>
        <ScrollArea className="flex-1 min-h-0 min-w-0 px-2">
        <div className="min-w-0 space-y-0.5 pr-2 pb-3">
          {displayedChats.length === 0 ? (
            <p className="px-2 py-6 text-xs text-muted-foreground text-center leading-relaxed">
              {sessionList.length === 0
                ? "No chats yet. Start with New chat."
                : "No chats match filters. Clear search or starred view."}
            </p>
          ) : (
            displayedChats.map((s) => (
              <div key={s.id} className="relative group/item min-w-0">
                <div
                  className={cn(
                    "flex w-full min-w-0 max-w-full items-center gap-1 overflow-hidden rounded-xl pl-2 pr-1 py-1.5 text-left text-sm transition-colors",
                    s.id === activeSessionId
                      ? "bg-[#d3e3fd]/80 dark:bg-primary/20 text-foreground"
                      : "hover:bg-background/80",
                  )}
                >
                  <button
                    type="button"
                    className="min-w-0 flex-1 overflow-hidden py-1 pl-0 pr-0.5 text-left font-medium rounded-lg"
                    onClick={() => onSelectSession(s.id)}
                    title={s.title}
                  >
                    <span className="block truncate">{s.title}</span>
                  </button>
                  <div className="flex shrink-0 items-center gap-0">
                    {pendingResearchSessionId === s.id && (
                      <Loader2
                        className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground"
                        aria-label="Reply in progress"
                      />
                    )}
                    <button
                      type="button"
                      className="shrink-0 p-1.5 rounded-md hover:bg-background/60"
                      aria-label={s.starred ? "Unstar" : "Star chat"}
                      onClick={() => onToggleStar(s.id)}
                    >
                      <Star
                        className={cn(
                          "h-3.5 w-3.5",
                          s.starred ? "fill-amber-400 text-amber-500" : "text-muted-foreground/40",
                        )}
                      />
                    </button>
                    <button
                      type="button"
                      className="shrink-0 p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                      aria-label="Delete chat"
                      title="Delete chat"
                      onClick={(e) => {
                        e.stopPropagation()
                        setDeleteId(s.id)
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      className="shrink-0 p-1.5 rounded-md opacity-70 hover:opacity-100 hover:bg-background/60"
                      aria-label="Chat actions"
                      onClick={() => setMenuOpenId(menuOpenId === s.id ? null : s.id)}
                    >
                      <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                    </button>
                  </div>
                </div>
                {menuOpenId === s.id && (
                  <>
                    <button
                      type="button"
                      aria-label="Close menu"
                      className="fixed inset-0 z-40 cursor-default"
                      onClick={() => setMenuOpenId(null)}
                    />
                    <div className="absolute right-2 top-full z-50 mt-0.5 w-44 rounded-lg border border-border/60 bg-background shadow-md py-1 text-sm">
                      <button
                        type="button"
                        className="w-full px-3 py-2 text-left hover:bg-muted/80"
                        onClick={() => openRename(s)}
                      >
                        Rename
                      </button>
                      <button
                        type="button"
                        className="w-full px-3 py-2 text-left text-destructive hover:bg-muted/80 flex items-center gap-2"
                        onClick={() => {
                          setDeleteId(s.id)
                          setMenuOpenId(null)
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
          {showMore && (
            <button
              type="button"
              onClick={() => setChatsExpanded((e) => !e)}
              className="w-full flex items-center justify-center gap-1 py-2 text-xs text-muted-foreground hover:text-foreground"
            >
              {chatsExpanded ? (
                <>
                  Show less <ChevronDown className="h-3 w-3 rotate-180" />
                </>
              ) : (
                <>
                  Show more ({visibleList.length - CHAT_PREVIEW_LIMIT}) <ChevronDown className="h-3 w-3" />
                </>
              )}
            </button>
          )}
        </div>
      </ScrollArea>
      </div>

      <div className="p-3 border-t border-border/40 space-y-1 shrink-0">
        
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 h-10 px-3 rounded-xl text-sm text-muted-foreground hover:text-foreground"
          type="button"
          onClick={() => onSettingsOpenChange(true)}
        >
          <Settings className="h-4 w-4" />
          Settings & help
        </Button>
      </div>

      <Dialog open={renameId !== null} onOpenChange={(o) => !o && setRenameId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Rename chat</DialogTitle>
          </DialogHeader>
          <Input value={renameValue} onChange={(e) => setRenameValue(e.target.value)} onKeyDown={(e) => e.key === "Enter" && commitRename()} />
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setRenameId(null)}>
              Cancel
            </Button>
            <Button onClick={commitRename}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteId !== null} onOpenChange={(o) => !o && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this chat?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the conversation from this device. Uploaded context for this session is cleared from the list when you delete.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (deleteId) onDeleteSession(deleteId)
                setDeleteId(null)
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={settingsOpen} onOpenChange={onSettingsOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Settings & help</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              Chats are stored locally in your browser. Clearing site data or using another device will not sync
              conversations.
            </p>
            <p>
              For requirement mining and document context, upload files from the composer. The assistant uses the
              full regulatory and clinical data stack automatically.
            </p>
          </div>
          <DialogFooter className="flex-col sm:flex-col gap-2">
            <Button
              variant="destructive"
              className="w-full"
              onClick={() => {
                onClearAllData()
                onSettingsOpenChange(false)
              }}
            >
              Clear all regulatory chats on this device
            </Button>
            <Button variant="outline" className="w-full" onClick={() => onSettingsOpenChange(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  )
}
