"use client"

import { useState } from "react"
import Link from "next/link"
import * as DropdownMenu from "@radix-ui/react-dropdown-menu"
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

function sessionDisplayTitle(s: RegulatorySessionMeta): string {
  const t = typeof s.title === "string" ? s.title.trim() : ""
  return t || "New chat"
}

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

  const showMore = visibleList.length > CHAT_PREVIEW_LIMIT
  const displayedChats = chatsExpanded ? visibleList : visibleList.slice(0, CHAT_PREVIEW_LIMIT)

  const openRename = (s: RegulatorySessionMeta) => {
    setRenameId(s.id)
    setRenameValue(sessionDisplayTitle(s))
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

      <div className="shrink-0 p-3 space-y-1 border-b border-border/40">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 h-10 px-3 rounded-xl text-sm font-medium hover:bg-background/80"
          type="button"
          onClick={onNewChat}
        >
          <MessageSquarePlus className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="truncate">New chat</span>
        </Button>
        <Button
          variant={searchPanelOpen ? "secondary" : "ghost"}
          className="w-full justify-start gap-3 h-10 px-3 rounded-xl text-sm hover:bg-background/80"
          type="button"
          onClick={() => onSearchPanelOpenChange(!searchPanelOpen)}
        >
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="truncate">Search chats</span>
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
            className={cn("h-4 w-4 shrink-0", starredOnly ? "fill-amber-400 text-amber-500" : "text-muted-foreground")}
          />
          <span className="truncate">Starred</span>
          {starredCount > 0 && (
            <span className="ml-auto shrink-0 text-[11px] tabular-nums text-muted-foreground">{starredCount}</span>
          )}
        </Button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col border-t border-border/30">
        <div className="shrink-0 px-3 pt-2 pb-1.5">
          <p className="px-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Chats</p>
        </div>

        <div className="min-h-0 flex-1 min-w-0 overflow-y-auto overflow-x-hidden px-2 [scrollbar-gutter:stable]">
          <div className="min-w-0 space-y-1 pb-3">
            {displayedChats.length === 0 ? (
              <p className="px-2 py-6 text-center text-xs leading-relaxed text-muted-foreground">
                {sessionList.length === 0
                  ? "No chats yet. Start with New chat."
                  : "No chats match filters. Clear search or starred view."}
              </p>
            ) : (
              displayedChats.map((s) => {
                const label = sessionDisplayTitle(s)
                const isActive = s.id === activeSessionId
                const isPending = pendingResearchSessionId === s.id

                return (
                  <div
                    key={s.id}
                    className={cn(
                      "grid w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-1 rounded-xl px-1.5 py-1 text-sm transition-colors",
                      isActive
                        ? "bg-[#d3e3fd]/80 ring-1 ring-border/40 dark:bg-primary/20 dark:ring-border/30"
                        : "hover:bg-background/80",
                    )}
                  >
                    <button
                      type="button"
                      className="min-h-8 min-w-0 overflow-hidden rounded-lg py-1 pl-1 pr-0.5 text-left font-medium text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-transparent"
                      onClick={() => onSelectSession(s.id)}
                      title={label}
                    >
                      <span className={cn("block truncate", !s.title?.trim() && "text-muted-foreground")}>
                        {label}
                      </span>
                    </button>

                    <div className="flex shrink-0 items-center justify-end gap-0.5 pr-0.5">
                      {isPending && (
                        <span
                          className="inline-flex h-8 w-8 shrink-0 items-center justify-center"
                          role="status"
                          aria-label="Reply in progress"
                        >
                          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" aria-hidden />
                        </span>
                      )}
                      <button
                        type="button"
                        className={cn(
                          "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground outline-none transition-colors",
                          "hover:bg-background/70 hover:text-foreground",
                          "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-transparent",
                        )}
                        aria-label={s.starred ? "Unstar chat" : "Star chat"}
                        aria-pressed={Boolean(s.starred)}
                        onClick={(e) => {
                          e.stopPropagation()
                          onToggleStar(s.id)
                        }}
                      >
                        <Star
                          className={cn(
                            "h-3.5 w-3.5",
                            s.starred ? "fill-amber-400 text-amber-500" : "text-muted-foreground",
                          )}
                        />
                      </button>
                      <button
                        type="button"
                        className={cn(
                          "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground outline-none transition-colors",
                          "hover:bg-destructive/10 hover:text-destructive",
                          "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-transparent",
                        )}
                        aria-label="Delete chat"
                        title="Delete chat"
                        onClick={(e) => {
                          e.stopPropagation()
                          setDeleteId(s.id)
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>

                      <DropdownMenu.Root modal={false}>
                        <DropdownMenu.Trigger asChild>
                          <button
                            type="button"
                            className={cn(
                              "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground outline-none transition-colors",
                              "hover:bg-background/70 hover:text-foreground",
                              "data-[state=open]:bg-background/80 data-[state=open]:text-foreground",
                              "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-transparent",
                            )}
                            aria-label="More chat actions"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </button>
                        </DropdownMenu.Trigger>
                        <DropdownMenu.Portal>
                          <DropdownMenu.Content
                            side="bottom"
                            align="end"
                            sideOffset={6}
                            collisionPadding={12}
                            className={cn(
                              "z-[100] min-w-[10rem] overflow-hidden rounded-lg border border-border/60 bg-popover p-1 text-popover-foreground shadow-lg",
                            )}
                          >
                            <DropdownMenu.Item
                              className={cn(
                                "flex cursor-pointer select-none items-center rounded-md px-2 py-2 text-sm outline-none",
                                "focus:bg-accent focus:text-accent-foreground data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground",
                              )}
                              onSelect={() => openRename(s)}
                            >
                              Rename
                            </DropdownMenu.Item>
                            <DropdownMenu.Item
                              className={cn(
                                "flex cursor-pointer select-none items-center gap-2 rounded-md px-2 py-2 text-sm text-destructive outline-none",
                                "focus:bg-destructive/10 focus:text-destructive data-[highlighted]:bg-destructive/10 data-[highlighted]:text-destructive",
                              )}
                              onSelect={() => setDeleteId(s.id)}
                            >
                              <Trash2 className="h-3.5 w-3.5 shrink-0" />
                              Delete…
                            </DropdownMenu.Item>
                          </DropdownMenu.Content>
                        </DropdownMenu.Portal>
                      </DropdownMenu.Root>
                    </div>
                  </div>
                )
              })
            )}

            {showMore && (
              <button
                type="button"
                onClick={() => setChatsExpanded((e) => !e)}
                className="mt-1 flex w-full items-center justify-center gap-1 rounded-lg py-2 text-xs text-muted-foreground transition-colors hover:bg-background/60 hover:text-foreground"
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
        </div>
      </div>

      <div className="shrink-0 space-y-1 border-t border-border/40 p-3">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 rounded-xl px-3 py-2 h-10 text-sm text-muted-foreground hover:text-foreground"
          type="button"
          onClick={() => onSettingsOpenChange(true)}
        >
          <Settings className="h-4 w-4 shrink-0" />
          <span className="truncate">Settings & help</span>
        </Button>
      </div>

      <Dialog open={renameId !== null} onOpenChange={(o) => !o && setRenameId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Rename chat</DialogTitle>
          </DialogHeader>
          <Input
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && commitRename()}
          />
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
          <DialogFooter className="flex-col gap-2 sm:flex-col">
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
