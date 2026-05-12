"use client"

import React from "react"
import { CheckCircle2, ChevronDown, Circle, History, Loader2 } from "lucide-react"
import type { QueryStep } from "@/lib/types/chat-types"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"

export type { QueryStep }

interface QueryProgressProps {
  steps: QueryStep[]
  currentStep?: string
  /** `replay`: saved trace (no header spinner). Default `live`. */
  mode?: "live" | "replay"
}

function stepHasExpandableDetail(step: QueryStep): boolean {
  const d = step.detail
  if (!d) return false
  return Boolean(
    d.search_query_used ||
      d.search_source ||
      d.result_summary ||
      d.error ||
      (typeof d.result_count === "number" && Number.isFinite(d.result_count)),
  )
}

function StepDetailPanel({ step }: { step: QueryStep }) {
  const d = step.detail
  if (!d) return null
  const rows: { label: string; value: string }[] = []
  if (d.search_query_used) rows.push({ label: "Query used", value: d.search_query_used })
  if (d.search_source) rows.push({ label: "Source", value: d.search_source })
  if (typeof d.result_count === "number" && Number.isFinite(d.result_count)) {
    rows.push({ label: "Count", value: String(d.result_count) })
  }
  if (d.result_summary) rows.push({ label: "Summary", value: d.result_summary })
  if (d.error) rows.push({ label: "Error", value: d.error })
  if (rows.length === 0) return null
  return (
    <div className="mt-2 space-y-1.5 rounded-md border border-border/50 bg-background/80 px-2.5 py-2 text-xs">
      {rows.map((r) => (
        <div key={r.label} className="min-w-0">
          <span className="font-medium text-muted-foreground">{r.label}</span>
          <p className="mt-0.5 whitespace-pre-wrap break-words text-foreground/90">{r.value}</p>
        </div>
      ))}
    </div>
  )
}

export function QueryProgress({ steps, currentStep, mode = "live" }: QueryProgressProps) {
  const replay = mode === "replay"
  return (
    <div className="min-w-0 max-w-full bg-muted/50 border border-border/40 rounded-lg p-4 sm:max-w-2xl space-y-3">
      <div className="flex items-center gap-2 mb-4">
        {replay ? (
          <History className="h-4 w-4 text-muted-foreground" />
        ) : (
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
        )}
        <span className="text-sm font-medium text-foreground">
          {replay ? "Query steps (saved)" : "Processing Query"}
        </span>
      </div>

      <div className="space-y-2">
        {steps.map((step, index) => {
          const isCurrentStep = step.id === currentStep
          const isCompleted = step.status === "completed"
          const isError = step.status === "error"
          const expandable = stepHasExpandableDetail(step)
          const preview =
            step.detail?.result_summary ||
            step.detail?.error ||
            (typeof step.detail?.result_count === "number"
              ? `${step.detail.result_count} result(s)`
              : null)

          return (
            <div
              key={step.id}
              className={cn(
                "rounded-md p-2 transition-colors",
                isCurrentStep ? "bg-primary/10" : "",
              )}
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : isCurrentStep && !replay ? (
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  ) : isCurrentStep && replay ? (
                    <Circle className="h-4 w-4 text-primary" />
                  ) : isError ? (
                    <Circle className="h-4 w-4 text-destructive" />
                  ) : (
                    <Circle className="h-4 w-4 text-muted-foreground/40" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex min-w-0 items-center gap-2">
                    <span
                      className={cn(
                        "min-w-0 truncate text-sm font-medium",
                        isCompleted
                          ? "text-muted-foreground"
                          : isCurrentStep
                            ? "text-foreground"
                            : "text-muted-foreground/60",
                      )}
                    >
                      {index + 1}. {step.name}
                    </span>
                    {step.agent ? (
                      <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                        {step.agent}
                      </span>
                    ) : null}
                  </div>
                  {step.description ? (
                    <p
                      className={cn(
                        "text-xs mt-0.5 line-clamp-3 break-words",
                        isCurrentStep ? "text-muted-foreground" : "text-muted-foreground/60",
                      )}
                    >
                      {step.description}
                    </p>
                  ) : null}

                  {expandable ? (
                    <Collapsible className="mt-1.5 group">
                      <CollapsibleTrigger
                        type="button"
                        className="flex w-full min-w-0 items-center gap-1 rounded-sm py-0.5 text-left text-xs text-primary hover:underline"
                      >
                        <ChevronDown className="h-3.5 w-3.5 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
                        <span className="font-medium">Step details</span>
                        {preview ? (
                          <span className="min-w-0 truncate text-muted-foreground font-normal">
                            — {preview}
                          </span>
                        ) : null}
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <StepDetailPanel step={step} />
                      </CollapsibleContent>
                    </Collapsible>
                  ) : null}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
