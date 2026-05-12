"use client"

import { useMemo, useState } from "react"
import { cn } from "@/lib/utils"
import type { Message } from "@/lib/types/chat-types"
import { normalizeChatCitations } from "@/lib/chat-citations"
import { parseQueryProcessingSnapshot } from "@/lib/query-processing-snapshot"
import { QueryProcessingPanel } from "@/components/chat/query-processing-panel"
import { User, Bot, FileText, ExternalLink, RotateCcw, Brain } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

const LOTOR_POC_DISCLAIMER = "This is a proof-of-concept response from a Lotor Lab agent"

interface MessageBubbleProps {
  message: Message
  onRegenerate?: () => void
  /** Gemini-style: assistant text on canvas; user in soft pill */
  appearance?: "default" | "enterprise"
}

export function MessageBubble({
  message,
  onRegenerate,
  appearance = "default",
}: MessageBubbleProps) {
  const isUser = message.role === "user"
  const ent = appearance === "enterprise"
  const citationItems = normalizeChatCitations(message.metadata?.citations)
  const thinkingSnapshot = useMemo(
    () => parseQueryProcessingSnapshot(message.metadata?.query_processing),
    [message.metadata?.query_processing],
  )
  const showThinking =
    !isUser &&
    message.agentType !== "progress" &&
    thinkingSnapshot &&
    (thinkingSnapshot.query_steps.length > 0 ||
      thinkingSnapshot.deep_research_timeline.length > 0 ||
      !!thinkingSnapshot.graph_plan_summary?.nodes?.length ||
      !!(thinkingSnapshot.graph_plan_summary?.reasoning && thinkingSnapshot.graph_plan_summary.reasoning.trim()) ||
      (thinkingSnapshot.execution_trace?.length ?? 0) > 0)
  const [thinkingOpen, setThinkingOpen] = useState(false)
  const [replaySlideIndex, setReplaySlideIndex] = useState(0)
  const markdownComponents = {
    table: ({ children }: { children?: React.ReactNode }) => (
      <div className="not-prose my-4 w-full overflow-x-auto rounded-xl border border-border/60 bg-card/70 shadow-sm">
        <table className="w-full min-w-max border-collapse text-xs">{children}</table>
      </div>
    ),
    thead: ({ children }: { children?: React.ReactNode }) => (
      <thead className="bg-muted/70 text-foreground">{children}</thead>
    ),
    th: ({ children }: { children?: React.ReactNode }) => (
      <th className="border-b border-border/60 px-3.5 py-2.5 text-left align-bottom font-semibold whitespace-nowrap">
        {children}
      </th>
    ),
    td: ({ children }: { children?: React.ReactNode }) => (
      <td className="min-w-[10rem] max-w-[28rem] whitespace-pre-wrap break-words border-t border-border/40 px-3.5 py-2.5 align-top">
        {children}
      </td>
    ),
  }

  return (
    <>
    <div
      className={cn(
        "flex mb-6 animate-fade-in w-full",
        ent ? (isUser ? "flex-row-reverse gap-3" : "flex-row gap-4") : isUser ? "flex-row-reverse gap-3" : "flex-row gap-3",
      )}
    >
      {/* Avatar — hidden for enterprise assistant for cleaner doc-style layout */}
      <div
        className={cn(
          "flex-shrink-0 h-8 w-8 rounded-lg flex items-center justify-center",
          ent && !isUser && "hidden",
          isUser && !ent && "bg-primary",
          isUser && ent && "bg-muted",
          !isUser && !ent && "bg-secondary",
        )}
      >
        {isUser ? (
          <User className={cn("h-4 w-4", ent ? "text-foreground" : "text-white")} />
        ) : (
          <Bot className="h-4 w-4 text-foreground" />
        )}
      </div>

      {/* Message Content */}
      <div className={cn("flex-1 min-w-0 space-y-1.5", isUser ? "items-end" : "items-start")}>
        {/* Header */}
        <div
          className={cn(
            "flex items-center gap-2 flex-wrap",
            isUser ? "flex-row-reverse" : "flex-row",
            ent && "mb-1",
          )}
        >
          <span className={cn("text-xs font-semibold text-foreground", ent && !isUser && "text-[13px] font-medium")}>
            {isUser ? "You" : message.agentName || "AI Agent"}
          </span>
          {message.agentType && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
              {message.agentType}
            </Badge>
          )}
          <span className="text-[10px] text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          {showThinking && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 px-2 text-[11px] font-medium gap-1"
              onClick={() => {
                if (thinkingSnapshot) {
                  const n = thinkingSnapshot.deep_research_timeline.length
                  setReplaySlideIndex(n > 0 ? n - 1 : 0)
                }
                setThinkingOpen(true)
              }}
            >
              <Brain className="h-3.5 w-3.5" />
              Show my thinking
            </Button>
          )}
        </div>

        {/* Message Bubble */}
        <div
          className={cn(
            "max-w-full break-words overflow-hidden",
            ent
              ? isUser
                ? "rounded-[1.25rem] px-4 py-3 ml-auto max-w-[85%] bg-muted/90 text-foreground border border-border/30"
                : "rounded-none px-0 py-0 w-full max-w-full bg-transparent border-0"
              : "rounded-lg px-4 py-3",
            !ent && isUser && "bg-primary text-white ml-auto",
            !ent && !isUser && "bg-card border border-border/50",
          )}
        >
          <div 
            className={cn(
              "prose prose-sm max-w-none",
              isUser
                ? ent
                  ? "text-foreground"
                  : "prose-invert"
                : "prose-slate dark:prose-invert",
              ent && !isUser && "prose-headings:font-semibold prose-headings:tracking-tight prose-p:leading-relaxed",
              // Custom prose overrides for chat
              "[&_h1]:text-lg [&_h1]:font-semibold [&_h1]:mb-2 [&_h1]:mt-3 first:[&_h1]:mt-0",
              "[&_h2]:text-base [&_h2]:font-semibold [&_h2]:mb-2 [&_h2]:mt-3 first:[&_h2]:mt-0",
              "[&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mb-1.5 [&_h3]:mt-2 first:[&_h3]:mt-0",
              "[&_h4]:text-sm [&_h4]:font-medium [&_h4]:mb-1.5 [&_h4]:mt-2 first:[&_h4]:mt-0",
              "[&_h5]:text-sm [&_h5]:font-medium [&_h5]:mb-1 [&_h5]:mt-2 first:[&_h5]:mt-0",
              "[&_h6]:text-xs [&_h6]:font-medium [&_h6]:mb-1 [&_h6]:mt-2 first:[&_h6]:mt-0",
              "[&_p]:text-sm [&_p]:leading-relaxed [&_p]:mb-2 [&_p]:whitespace-pre-wrap last:[&_p]:mb-0",
              "[&_ul]:text-sm [&_ul]:mb-2 [&_ul]:ml-0 [&_ul]:pl-5 [&_ul]:list-disc",
              "[&_ol]:text-sm [&_ol]:mb-2 [&_ol]:ml-0 [&_ol]:pl-5 [&_ol]:list-decimal",
              "[&_li]:mb-1.5 [&_li]:leading-relaxed [&_li]:pl-1",
              "[&_li>p]:my-1 [&_li>p:first-child]:mt-0 [&_li>p:last-child]:mb-0",
              "[&_li>ul]:mt-1.5 [&_li>ol]:mt-1.5 [&_li>ul]:list-[circle]",
              "[&_code]:text-xs [&_code]:px-1.5 [&_code]:py-0.5",
              "[&_pre]:text-xs [&_pre]:p-3 [&_pre]:my-2",
              "[&_blockquote]:text-sm [&_blockquote]:pl-3 [&_blockquote]:border-l-2 [&_blockquote]:my-2",
              !isUser && "[&>:not(.not-prose)]:max-w-[52rem]",
              "[&_a]:text-sm [&_a]:underline [&_a]:underline-offset-2"
            )}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          </div>
          {!isUser && (
            <p className="not-prose mt-2 text-[11px] leading-snug text-muted-foreground border-t border-border/40 pt-2">
              {LOTOR_POC_DISCLAIMER}
            </p>
          )}
        </div>

        {!isUser && onRegenerate && (
          <div className="flex items-center gap-1 mt-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-muted-foreground"
              onClick={onRegenerate}
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Regenerate
            </Button>
          </div>
        )}

        {/* Progress Indicator */}
        {message.metadata?.progress && (
          <div className="bg-card border border-border/50 rounded-lg p-2.5 max-w-md">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-foreground">{message.metadata.progress.stepName}</span>
              <span className="text-[10px] text-muted-foreground">
                {message.metadata.progress.currentStep} / {message.metadata.progress.totalSteps}
              </span>
            </div>
            <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{
                  width: `${(message.metadata.progress.currentStep / message.metadata.progress.totalSteps) * 100}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* Citations (structured links from synthesis) */}
        {!isUser && citationItems.length > 0 && (
          <div className="space-y-1.5 max-w-full mt-2">
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
              Sources & citations
            </span>
            <ul className="list-none space-y-1.5 p-0 m-0">
              {citationItems.map((c, idx) => (
                <li
                  key={`${c.url || "nourl"}-${idx}-${c.text.slice(0, 40)}`}
                  className="text-xs leading-snug flex items-start gap-2 rounded-md border border-border/50 bg-card/60 px-2.5 py-2"
                >
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />
                  <span className="min-w-0 flex-1">
                    {c.url ? (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary font-medium underline underline-offset-2 break-all hover:text-primary/90"
                      >
                        {c.text || c.url}
                      </a>
                    ) : (
                      <span className="text-foreground break-words">{c.text}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* References */}
        {message.metadata?.references && message.metadata.references.length > 0 && (
          <div className="space-y-1.5 max-w-full">
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">References</span>
            <div className="grid gap-1.5">
              {message.metadata.references.map((ref) => (
                <div
                  key={ref.id}
                  className="bg-card border border-border/50 rounded-lg p-2.5 hover:border-primary/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 space-y-0.5 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <FileText className="h-3 w-3 text-primary flex-shrink-0" />
                        <span className="text-xs font-medium text-foreground truncate">{ref.title}</span>
                      </div>
                      <p className="text-[10px] text-muted-foreground truncate">{ref.source}</p>
                      {ref.snippet && <p className="text-[10px] text-muted-foreground line-clamp-2 leading-relaxed">{ref.snippet}</p>}
                    </div>
                    {ref.url && (
                      <Button variant="ghost" size="icon" className="flex-shrink-0 h-6 w-6" asChild>
                        <a href={ref.url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Attachments */}
        {message.metadata?.attachments && message.metadata.attachments.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.metadata.attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="flex items-center gap-1.5 px-2.5 py-1.5 bg-card border border-border/50 rounded-lg text-xs"
              >
                <FileText className="h-3 w-3 text-primary" />
                <span className="text-foreground">{attachment.name}</span>
                <span className="text-[10px] text-muted-foreground">({(attachment.size / 1024).toFixed(1)} KB)</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>

      {showThinking && thinkingSnapshot && (
        <Dialog open={thinkingOpen} onOpenChange={setThinkingOpen}>
          <DialogContent className="max-w-3xl max-h-[min(85vh,720px)] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Query processing</DialogTitle>
            </DialogHeader>
            <div className="pt-1">
              <QueryProcessingPanel
                querySteps={thinkingSnapshot.query_steps}
                currentStep={undefined}
                deepResearchTimeline={thinkingSnapshot.deep_research_timeline}
                deepResearchSlideIndex={replaySlideIndex}
                onDeepResearchSlideIndexChange={setReplaySlideIndex}
                queryProgressMode="replay"
                graphPlanSummary={thinkingSnapshot.graph_plan_summary}
                executionTrace={thinkingSnapshot.execution_trace}
              />
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  )
}
