"use client"

import type { ReactNode } from "react"
import { QueryProgress } from "@/components/chat/query-progress"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"
import type {
  DeepResearchTimelineEntry,
  QueryProcessingExecutionTraceEntry,
  QueryProcessingSnapshot,
  QueryStep,
} from "@/lib/types/chat-types"
import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

export type QueryProcessingPanelProps = {
  querySteps: QueryStep[]
  currentStep?: string
  deepResearchTimeline: DeepResearchTimelineEntry[]
  deepResearchSlideIndex: number
  onDeepResearchSlideIndexChange: (index: number) => void
  /** `live` while streaming; `replay` for saved / dialog view. */
  queryProgressMode?: "live" | "replay"
  /** Optional spinner / icon column (e.g. loading strip). */
  leading?: ReactNode
  contentClassName?: string
  graphPlanSummary?: QueryProcessingSnapshot["graph_plan_summary"]
  executionTrace?: QueryProcessingExecutionTraceEntry[]
}

export function QueryProcessingPanel({
  querySteps,
  currentStep,
  deepResearchTimeline,
  deepResearchSlideIndex,
  onDeepResearchSlideIndexChange,
  queryProgressMode = "live",
  leading,
  contentClassName,
  graphPlanSummary,
  executionTrace,
}: QueryProcessingPanelProps) {
  const reasoning = graphPlanSummary?.reasoning?.trim()
  const planNodes = graphPlanSummary?.nodes?.length ? graphPlanSummary.nodes.slice(0, 40) : []
  const traceRows = executionTrace?.length ? executionTrace.slice(-60) : []

  return (
    <div className={cn("flex gap-3 w-full pb-1", contentClassName)}>
      {leading !== undefined && leading !== null ? (
        <div className="flex-shrink-0 h-8 w-8 rounded-lg flex items-center justify-center">{leading}</div>
      ) : null}
      <div className="flex-1 min-w-0 space-y-3">
        {querySteps.length > 0 ? (
          <QueryProgress steps={querySteps} currentStep={currentStep} mode={queryProgressMode} />
        ) : (
          <div className="bg-muted/50 border border-border/40 rounded-lg px-3 py-2 max-w-2xl">
            <p className="text-xs text-muted-foreground">Analyzing your query and planning execution…</p>
          </div>
        )}

        {(reasoning || planNodes.length > 0) && (
          <Collapsible defaultOpen={false} className="group max-w-2xl rounded-lg border border-border/50 bg-muted/20 overflow-hidden">
            <CollapsibleTrigger
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-foreground hover:bg-muted/40"
            >
              <ChevronDown className="h-4 w-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
              <span>Graph plan</span>
              {planNodes.length > 0 ? (
                <span className="text-xs font-normal text-muted-foreground">
                  ({planNodes.length} node{planNodes.length === 1 ? "" : "s"})
                </span>
              ) : null}
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="border-t border-border/40 px-3 py-2 space-y-2 text-xs">
                {planNodes.length > 0 ? (
                  <ul className="space-y-1 list-none pl-0 max-h-48 overflow-y-auto">
                    {planNodes.map((n) => (
                      <li key={n.id} className="text-muted-foreground">
                        <span className="font-medium text-foreground">{n.id}</span>{" "}
                        <span className="text-muted-foreground/80">({n.type})</span> —{" "}
                        <span className="break-words">{n.description}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {reasoning ? (
                  <div className="rounded-md bg-background/80 border border-border/40 p-2 max-h-56 overflow-y-auto whitespace-pre-wrap break-words text-foreground/90">
                    {reasoning}
                  </div>
                ) : null}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {traceRows.length > 0 && (
          <Collapsible defaultOpen={false} className="group max-w-2xl rounded-lg border border-border/50 bg-muted/20 overflow-hidden">
            <CollapsibleTrigger
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-foreground hover:bg-muted/40"
            >
              <ChevronDown className="h-4 w-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
              <span>Execution log</span>
              <span className="text-xs font-normal text-muted-foreground">
                ({traceRows.length} event{traceRows.length === 1 ? "" : "s"})
              </span>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <ul className="border-t border-border/40 max-h-64 overflow-y-auto px-3 py-2 space-y-2 text-xs list-none pl-0">
                {traceRows.map((row, i) => (
                  <li
                    key={`${row.node_id ?? "n"}-${row.start_time ?? i}-${i}`}
                    className="rounded border border-border/30 bg-background/60 px-2 py-1.5"
                  >
                    <div className="font-medium text-foreground">
                      {row.node_id ?? "—"}{" "}
                      <span className="text-muted-foreground font-normal">({row.node_type ?? "?"})</span>{" "}
                      <span
                        className={cn(
                          "text-[10px] uppercase tracking-wide",
                          row.status === "failed" ? "text-destructive" : "text-muted-foreground",
                        )}
                      >
                        {row.status ?? ""}
                      </span>
                    </div>
                    {row.description ? (
                      <p className="mt-0.5 text-muted-foreground line-clamp-2">{row.description}</p>
                    ) : null}
                    {row.search_query_used ? (
                      <p className="mt-1 text-[11px] text-foreground/85 whitespace-pre-wrap break-words">
                        <span className="text-muted-foreground">Q:</span> {row.search_query_used}
                      </p>
                    ) : null}
                    {row.result_summary ? (
                      <p className="mt-0.5 text-[11px] text-foreground/85">{row.result_summary}</p>
                    ) : null}
                    {row.error ? <p className="mt-0.5 text-destructive/90 text-[11px]">{row.error}</p> : null}
                  </li>
                ))}
              </ul>
            </CollapsibleContent>
          </Collapsible>
        )}

        {deepResearchTimeline.length > 0 && (
          <Collapsible defaultOpen className="group max-w-2xl rounded-lg border border-border/60 bg-card/90 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between gap-2 border-b border-border/50 bg-muted/30 px-3 py-2 shrink-0">
              <CollapsibleTrigger
                type="button"
                className="flex min-w-0 flex-1 items-center gap-2 text-left rounded-sm hover:bg-muted/50 py-0.5 -my-0.5"
              >
                <ChevronDown className="h-4 w-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
                <p className="text-sm font-semibold text-foreground truncate">Agent thinking</p>
              </CollapsibleTrigger>
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  disabled={deepResearchSlideIndex <= 0}
                  aria-label="Previous thought"
                  onClick={() => onDeepResearchSlideIndexChange(Math.max(0, deepResearchSlideIndex - 1))}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-xs text-muted-foreground tabular-nums min-w-[3.5rem] text-center">
                  {deepResearchSlideIndex + 1} / {deepResearchTimeline.length}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  disabled={deepResearchSlideIndex >= deepResearchTimeline.length - 1}
                  aria-label="Next thought"
                  onClick={() =>
                    onDeepResearchSlideIndexChange(
                      Math.min(deepResearchTimeline.length - 1, deepResearchSlideIndex + 1),
                    )
                  }
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <CollapsibleContent>
              {(() => {
                const entry = deepResearchTimeline[deepResearchSlideIndex]
                if (!entry) {
                  return (
                    <div className="px-4 py-6 text-sm text-muted-foreground">Updating agent thinking…</div>
                  )
                }
                return (
                  <div key={entry.key} className="px-4 py-3 min-h-[6rem] transition-opacity">
                    <h3 className="text-base font-semibold text-foreground leading-tight">{entry.title}</h3>
                    {entry.timestamp ? (
                      <p className="text-xs text-muted-foreground mt-1 tabular-nums">{entry.timestamp}</p>
                    ) : null}
                    {entry.thinkingLines.length > 0 ? (
                      <ul className="mt-3 space-y-2 list-none pl-0">
                        {entry.thinkingLines.map((t, j) => (
                          <li
                            key={j}
                            className="border-l-[3px] border-primary/35 pl-3 text-sm leading-relaxed text-foreground/90 [&_.prose]:my-0 [&_.prose_p]:mb-1 [&_.prose_p:last-child]:mb-0"
                          >
                            <div className="prose prose-sm max-w-none prose-slate dark:prose-invert [&_p]:whitespace-pre-wrap [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{t}</ReactMarkdown>
                            </div>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    {entry.bullets.length > 0 ? (
                      <div className="mt-3 space-y-2">
                        {entry.bullets.map((b, j) => (
                          <div
                            key={j}
                            className="border-l-[3px] border-muted-foreground/25 pl-3 text-sm leading-relaxed text-foreground/90 [&_.prose]:my-0 [&_.prose_p]:mb-1 [&_.prose_p:last-child]:mb-0"
                          >
                            <div className="prose prose-sm max-w-none prose-slate dark:prose-invert [&_p]:whitespace-pre-wrap [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5 [&_li>p]:my-1 [&_li>p:first-child]:mt-0 [&_li>p:last-child]:mb-0">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{b}</ReactMarkdown>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                )
              })()}
              <div className="flex flex-wrap gap-1.5 px-3 py-2 border-t border-border/40 bg-muted/20 shrink-0">
                {deepResearchTimeline.map((e, i) => (
                  <button
                    key={e.key}
                    type="button"
                    onClick={() => onDeepResearchSlideIndexChange(i)}
                    className={cn(
                      "h-2 min-w-2 rounded-full transition-all",
                      i === deepResearchSlideIndex
                        ? "w-6 bg-primary"
                        : "w-2 bg-muted-foreground/30 hover:bg-muted-foreground/50",
                    )}
                    aria-label={`Thought ${i + 1}: ${e.title}`}
                  />
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>
    </div>
  )
}
