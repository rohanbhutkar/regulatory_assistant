"use client"

import type React from "react"

import { useState, useRef, useEffect, useId } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { BarChart3, BookMarked, Loader2, Paperclip, Send } from "lucide-react"
import { cn } from "@/lib/utils"

export type ChatInputDeepResearchProps = {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
}

interface ChatInputProps {
  onSendMessage: (message: string, attachments?: File[]) => void
  isLoading?: boolean
  placeholder?: string
  fileAccept?: string
  variant?: "default" | "enterprise"
  /** Shown on the right of the enterprise toolbar (e.g. agent selector + send) */
  toolbarRight?: React.ReactNode
  /** When `id` changes, replace the draft in the textarea and focus it (e.g. sample query chips). */
  composeRequest?: { id: number; text: string } | null
  /** Renders next to the send button (compact vs full graph on the backend). */
  deepResearch?: ChatInputDeepResearchProps | null
}

export function ChatInput({
  onSendMessage,
  isLoading = false,
  placeholder = "Ask a question...",
  fileAccept = ".pdf,.doc,.docx,.txt,.csv,.xlsx",
  variant = "default",
  toolbarRight,
  composeRequest = null,
  deepResearch = null,
}: ChatInputProps) {
  const deepResearchHintId = useId()
  const [message, setMessage] = useState("")
  const [attachments, setAttachments] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!composeRequest) return
    setMessage(composeRequest.text)
    queueMicrotask(() => {
      const el = textareaRef.current
      if (!el) return
      el.focus()
      const len = composeRequest.text.length
      try {
        el.setSelectionRange(len, len)
      } catch {
        /* ignore */
      }
    })
  }, [composeRequest])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !isLoading) {
      onSendMessage(message, attachments)
      setMessage("")
      setAttachments([])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setAttachments(Array.from(e.target.files))
    }
  }

  const deepResearchToggle =
    deepResearch != null ? (
      <div
        className="flex min-w-0 max-w-full items-center gap-1.5 shrink"
        title={
          deepResearch.checked
            ? "Deep research on: full multi-step graph and more sources."
            : "Deep research off: faster runs with up to 5 steps and 3 search sources."
        }
      >
        <Switch
          id={deepResearchHintId}
          checked={deepResearch.checked}
          onCheckedChange={deepResearch.onCheckedChange}
          disabled={isLoading}
          aria-describedby={`${deepResearchHintId}-desc`}
          className="shrink-0 scale-90"
        />
        <Label
          htmlFor={deepResearchHintId}
          className="min-w-0 truncate text-xs font-medium cursor-pointer text-muted-foreground leading-none"
        >
          Deep research
        </Label>
        <span id={`${deepResearchHintId}-desc`} className="sr-only">
          {deepResearch.checked
            ? "Full multi-step graph and more sources."
            : "Faster runs: up to 5 steps and 3 search sources."}
        </span>
      </div>
    ) : null

  if (variant === "enterprise") {
    return (
      <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {attachments.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-2 px-3 py-1.5 bg-muted/80 rounded-full text-sm border border-border/50"
              >
                <span className="text-foreground truncate max-w-[220px]">{file.name}</span>
                <button
                  type="button"
                  onClick={() => setAttachments(attachments.filter((_, i) => i !== index))}
                  className="text-muted-foreground hover:text-foreground"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="rounded-2xl border border-border/60 bg-background shadow-md shadow-black/5 dark:shadow-black/20 overflow-hidden">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            className={cn(
              "min-h-[56px] max-h-[200px] resize-none border-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0",
              "rounded-none px-4 pt-4 pb-2 text-[15px] leading-relaxed bg-transparent placeholder:text-muted-foreground/70",
            )}
          />
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            accept={fileAccept}
          />
          <div className="flex items-stretch gap-2 px-2 pb-2 pt-1 border-t border-border/40 overflow-hidden min-w-0">
            <div className="flex items-center gap-0.5 shrink-0">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-9 w-9 rounded-full text-muted-foreground hover:text-foreground"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                title="Add files"
              >
                <Paperclip className="h-5 w-5" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-9 w-9 rounded-full text-muted-foreground hover:text-foreground"
                disabled
                title="Data sources"
              >
                <BarChart3 className="h-5 w-5" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-9 w-9 rounded-full text-muted-foreground hover:text-foreground"
                disabled
                title="Reference"
              >
                <BookMarked className="h-5 w-5" />
              </Button>
            </div>
            <div className="flex min-w-0 flex-1 items-center justify-end gap-1.5 sm:gap-2">
              <div className="flex min-w-0 items-center justify-end gap-1.5 overflow-hidden">
                {toolbarRight}
                {deepResearchToggle}
              </div>
              <Button
                type="submit"
                disabled={!message.trim() || isLoading}
                size="icon"
                className="h-10 w-10 shrink-0 rounded-full"
              >
                {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
              </Button>
            </div>
          </div>
        </div>
      </form>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {attachments.map((file, index) => (
            <div key={index} className="flex items-center gap-2 px-3 py-1 bg-secondary rounded-lg text-sm">
              <span className="text-foreground">{file.name}</span>
              <button
                type="button"
                onClick={() => setAttachments(attachments.filter((_, i) => i !== index))}
                className="text-muted-foreground hover:text-foreground"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 items-end">
        <div className="flex-1 relative min-w-0">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            className="min-h-[60px] max-h-[200px] resize-none pr-12 bg-card border-border/50 focus:border-primary"
          />
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            accept={fileAccept}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute bottom-2 right-2"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
          >
            <Paperclip className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0 justify-end pb-0.5">
          {deepResearchToggle}
          <Button type="submit" disabled={!message.trim() || isLoading} size="lg" className="shrink-0">
            {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
          </Button>
        </div>
      </div>
    </form>
  )
}
