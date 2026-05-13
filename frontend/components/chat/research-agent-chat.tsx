"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { MessageBubble } from "./message-bubble"
import { ChatInput } from "./chat-input"
import { QueryProcessingPanel } from "./query-processing-panel"
import { type QueryStep } from "./query-progress"
import {
  buildQueryProcessingSnapshot,
  graphPlanToProcessingSummary,
  upsertExecutionTraceFromNodeProgress,
} from "@/lib/query-processing-snapshot"
import { Button } from "@/components/ui/button"
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
import type {
  Message,
  DeepResearchTimelineEntry,
  QueryProcessingExecutionTraceEntry,
  QueryProcessingSnapshot,
  QueryStepDetail,
} from "@/lib/types/chat-types"
import { Trash2, Square, Terminal, User } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { useStudyDesignerOptional } from "@/lib/contexts/study-designer-context"
import { ENDPOINTS } from "@/lib/config/api"
import { chatAppendMessage, chatCompleteTurn, chatListMessages } from "@/lib/chat-persistence-api"
import {
  buildCitationThinkingEntry,
  filterCitationsForFooter,
  normalizeChatCitations,
} from "@/lib/chat-citations"
import { titleFromFirstUserMessage } from "@/lib/regulatory-chat-sessions"
import { useBackendLogs } from "@/components/activity/logs-viewer"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

const DEFAULT_RESEARCH_WELCOME = `Welcome to the Clinical Knowledge Agent Platform! I'm here to help you with your research queries. 

I have access to 15+ specialized AI agents including:
- Clinical Trials Database (80K+ trials)
- PubMed Literature Search
- Claims Data Analysis (2.9M+ records)
- Site Selection & Mapping
- Trial Simulation & Budget Modeling
- Payer Data & Market Analysis

What would you like to explore today?`

const REGULATORY_SUGGESTION_CHIPS: { label: string; prompt: string }[] = [
  {
    label: "FDA label vs protocol",
    prompt:
      "Compare my uploaded inclusion/exclusion language to the latest FDA-approved USPI for [drug] and list concrete conflicts with citations.",
  },
  {
    label: "EMA EPAR & post-auth",
    prompt:
      "What does EMA publish for [product]—EPAR, PSUSA, shortages, referrals, or orphan status—and which excerpts matter for my EU filing story?",
  },
  {
    label: "China CDE / NMPA path",
    prompt:
      "Which CDE technical guidelines, NMPA drug registration notices, or zwfw service pages apply to a Phase III oncology program in China? Prefer official .gov.cn sources.",
  },
  {
    label: "Trial + literature landscape",
    prompt:
      "Summarize similar trials (ClinicalTrials.gov / EU CTIS / ISRCTN) and key PubMed work for [molecule] in [indication], with NCT/PMID links I can paste into a briefing book.",
  },
  {
    label: "OpenFDA safety signals",
    prompt:
      "What enforcement, label change, or FAERS-style signals does OpenFDA show for [drug] in the last five years, and how should I phrase limitations for executives?",
  },
  {
    label: "FDA vs EMA vs NMPA",
    prompt:
      "Map FDA, EMA, and NMPA expectations for [topic—e.g., pediatric investigation plans, adaptive designs, real-world evidence] at my current development stage, with agency-specific citations.",
  },
  {
    label: "NIH funding context",
    prompt:
      "Who is funded on NIH RePORTER for [disease / modality] and how does that competitive grant landscape affect our regulatory positioning?",
  },
  {
    label: "Guidance evidence table",
    prompt:
      "Build a compact table of ICH / FDA / EMA guidances I must satisfy for an IND amendment, with agency, title, URL, and how each row ties to the uploaded protocol section.",
  },
]

/** Shown if `public/lotor-lab-logo.png` fails to load. */
function LotorLabLogoFallback({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex h-full w-full items-center justify-center rounded-2xl border border-dashed border-border/70 bg-muted/30 text-[11px] font-medium text-muted-foreground",
        className,
      )}
      role="img"
      aria-label="Lotor Lab raccoon logo"
    >
      Logo
    </div>
  )
}

function formatGraphNodeIdForDisplay(name: string, index: number): string {
  if (!name) return `Step ${index + 1}`
  const formatted = name
    .replace(/^(search_|analyze_|synthesize_|extract_|generate_|protocol_|filter_|replan_)/, "")
    .replace(/_/g, " ")
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
  return formatted || name
}

/** Backend synthetic progress id — pre-graph “assessing query / planning” (not a graph node). */
const ORCHESTRATION_PLANNING_NODE_ID = "query_analysis"

function planningStepFromGraphPlan(
  graphPlan: { nodes?: unknown[]; reasoning?: unknown } | null | undefined,
): QueryStep {
  const reasoningRaw =
    graphPlan && typeof graphPlan === "object" && "reasoning" in graphPlan
      ? (graphPlan as { reasoning?: unknown }).reasoning
      : undefined
  const reasoning =
    typeof reasoningRaw === "string" && reasoningRaw.trim() ? reasoningRaw.trim() : ""
  const description =
    reasoning.length > 360 ? `${reasoning.slice(0, 360)}…` : reasoning || "Analyzing query and creating execution plan"
  return {
    id: ORCHESTRATION_PLANNING_NODE_ID,
    name: formatGraphNodeIdForDisplay(ORCHESTRATION_PLANNING_NODE_ID, 0),
    description,
    status: "completed",
    agent: "analysis",
  }
}

/** One stable first row for orchestration planning + graph steps (drops duplicate planner id from nodes if any). */
function withPlanningStepFirst(
  graphPlan: { nodes?: unknown[]; reasoning?: unknown } | null | undefined,
  graphSteps: QueryStep[],
): QueryStep[] {
  const body = graphSteps.filter((s) => s.id !== ORCHESTRATION_PLANNING_NODE_ID)
  return [planningStepFromGraphPlan(graphPlan), ...body]
}

/** Build progress steps from API graph_plan.nodes; preserve "completed" per id when replanning. */
function graphPlanToQuerySteps(
  graphPlan: { nodes?: unknown[] } | null | undefined,
  completedIds?: Set<string>,
): QueryStep[] {
  const nodes = graphPlan?.nodes
  if (!nodes || !Array.isArray(nodes)) return []
  return nodes.map((raw: unknown, index: number) => {
    const node = raw as Record<string, unknown>
    const nodeId = (typeof node.id === "string" && node.id) || `step-${index}`
    const nodeType = typeof node.type === "string" ? node.type : "unknown"
    const nodeDescription = typeof node.description === "string" ? node.description : ""
    const nodeParameters = (node.parameters as Record<string, unknown>) || {}
    const nodeName = formatGraphNodeIdForDisplay(nodeId, index)
    let enhancedDescription = nodeDescription
    if (typeof nodeParameters.source === "string") {
      enhancedDescription += ` (source: ${nodeParameters.source})`
    } else if (typeof nodeParameters.analysis_type === "string") {
      enhancedDescription += ` (${nodeParameters.analysis_type})`
    } else if (typeof nodeParameters.section_type === "string") {
      enhancedDescription += ` (${nodeParameters.section_type})`
    }
    const status: QueryStep["status"] = completedIds?.has(nodeId) ? "completed" : "pending"
    return {
      id: nodeId,
      name: nodeName,
      description: enhancedDescription || `${nodeType}: ${nodeName}`,
      status,
      agent: nodeType,
    }
  })
}

function mergeNodeProgressDetail(
  prev: QueryStepDetail | undefined,
  nodeData: Record<string, unknown>,
): QueryStepDetail | undefined {
  const n: QueryStepDetail = { ...prev }
  if (typeof nodeData.search_query_used === "string" && nodeData.search_query_used.trim()) {
    n.search_query_used = nodeData.search_query_used.trim().slice(0, 800)
  }
  if (typeof nodeData.search_source === "string" && nodeData.search_source.trim()) {
    n.search_source = nodeData.search_source.trim().slice(0, 128)
  }
  if (typeof nodeData.result_summary === "string" && nodeData.result_summary.trim()) {
    n.result_summary = nodeData.result_summary.trim().slice(0, 500)
  }
  if (typeof nodeData.error === "string" && nodeData.error.trim()) {
    n.error = nodeData.error.trim().slice(0, 500)
  }
  if (typeof nodeData.result_count === "number" && Number.isFinite(nodeData.result_count)) {
    n.result_count = nodeData.result_count
  }
  const has =
    (n.search_query_used && n.search_query_used.length > 0) ||
    (n.search_source && n.search_source.length > 0) ||
    (n.result_summary && n.result_summary.length > 0) ||
    (n.error && n.error.length > 0) ||
    n.result_count !== undefined
  if (!has) return prev
  return n
}

function asTrimmedStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return []
  return v
    .filter((x): x is string => typeof x === "string")
    .map((s) => s.trim())
    .filter(Boolean)
}

/** HTTP base for the multi-agent backend (align with NEXT_PUBLIC_AGENT_WS_URL host when API URL unset). */
function getAgentHttpBase(): string {
  const explicit = process.env.NEXT_PUBLIC_API_URL?.trim()
  if (explicit) return explicit.replace(/\/$/, "")
  const ws = process.env.NEXT_PUBLIC_AGENT_WS_URL || "ws://127.0.0.1:8001/ws"
  try {
    const u = new URL(ws.replace(/^ws/i, "http"))
    return `${u.protocol}//${u.host}`
  } catch {
    return "http://127.0.0.1:8001"
  }
}

export type ResearchRestPayload = {
  query: string
  conversation_history: { role: string; content: string; timestamp?: string }[]
  selected_agents: string[]
  study_context?: Record<string, unknown>
  selected_trials?: unknown
  deep_research?: boolean
  regulatory_document_ids?: string[]
}

export type ResearchRestResponse = {
  success?: boolean
  synthesis?: {
    answer?: string
    citations?: unknown[]
    confidence?: unknown
    data_quality?: unknown
  }
  graph_plan?: { nodes?: { id?: string; type?: string; description?: string; agent_type?: string }[] }
  metadata?: { processing_time?: number }
  execution_trace?: unknown[]
}

async function fetchResearchViaRest(body: ResearchRestPayload): Promise<ResearchRestResponse> {
  const res = await fetch(`${getAgentHttpBase()}/api/research/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const text = await res.text()
  if (!res.ok) {
    throw new Error(text?.slice(0, 500) || `Request failed (${res.status})`)
  }
  return JSON.parse(text) as ResearchRestResponse
}

export interface ResearchAgentChatProps {
  variant?: "research" | "regulatory"
  welcomeContent?: string
  welcomeAgentName?: string
  welcomeAgentType?: string
  inputPlaceholder?: string
  enableDocumentContext?: boolean
  persistHistory?: boolean
  storageKey?: string
  fileAccept?: string
  /** Gemini Enterprise–style layout (sidebar is composed on the page) */
  presentation?: "default" | "enterprise"
  /** When set with onSessionActivity, syncs chat title with multi-session sidebar */
  sessionId?: string
  onSessionActivity?: (payload: {
    sessionId: string
    title: string
    messageCount: number
    bumpOrder?: boolean
    lastMessageAt?: number
  }) => void
  /** When true with variant regulatory, messages load/save via /api/chat (Postgres). */
  remotePersistence?: boolean
  /** Regulatory: notify parent when this session’s assistant run starts or finishes (supports multiple concurrent sessions). */
  onResearchRunChange?: (sessionId: string, running: boolean) => void
  /** When set with enterprise + sessionId, header delete confirms via sidebar API instead of clearing local state only. */
  onConfirmDeleteSession?: (sessionId: string) => void | Promise<void>
}

function deserializeMessages(raw: string): Message[] {
  const arr = JSON.parse(raw) as Array<Omit<Message, "timestamp"> & { timestamp: string }>
  return arr.map((m) => ({
    ...m,
    timestamp: new Date(m.timestamp),
  }))
}

export function ResearchAgentChat({
  variant = "research",
  welcomeContent = DEFAULT_RESEARCH_WELCOME,
  welcomeAgentName = "Study Design Assistant",
  welcomeAgentType = "orchestrator",
  inputPlaceholder = "Ask about clinical trials, protocols, or research data...",
  enableDocumentContext = false,
  persistHistory = false,
  storageKey = "research-agent-chat-history",
  fileAccept,
  presentation = "default",
  sessionId,
  onSessionActivity,
  remotePersistence = false,
  onResearchRunChange,
  onConfirmDeleteSession,
}: ResearchAgentChatProps) {
  const backendLogs = useBackendLogs()
  const studyDesigner = useStudyDesignerOptional()
  const agentActions = studyDesigner?.agentActions ?? null
  const studyContext = studyDesigner?.studyContext ?? null
  const selectedTrials = studyDesigner?.selectedTrials ?? null

  const welcomeMessage = useMemo(
    (): Message => ({
      id: "welcome",
      role: "assistant",
      content: welcomeContent,
      timestamp: new Date(),
      agentName: welcomeAgentName,
      agentType: welcomeAgentType,
    }),
    [welcomeContent, welcomeAgentName, welcomeAgentType],
  )

  /** Shown only before the first message; never stored in messages or localStorage. */
  const regulatoryEphemeralWelcomeMarkdown =
    variant === "regulatory" && welcomeContent === DEFAULT_RESEARCH_WELCOME ? "" : welcomeContent
  const regulatoryEphemeralAgentName =
    variant === "regulatory" && welcomeAgentName === "Study Design Assistant"
      ? "Regulatory Assistant"
      : welcomeAgentName

  const [messages, setMessages] = useState<Message[]>(() => {
    if (typeof window === "undefined") {
      return variant === "regulatory" ? [] : [welcomeMessage]
    }
    if (remotePersistence && variant === "regulatory") {
      return []
    }
    if (persistHistory && storageKey) {
      try {
        const raw = localStorage.getItem(storageKey)
        if (raw) {
          const parsed = deserializeMessages(raw)
          if (parsed.length) {
            if (variant === "regulatory") {
              const withoutWelcome = parsed.filter((m) => m.id !== "welcome")
              return withoutWelcome.length > 0 ? withoutWelcome : []
            }
            return parsed
          }
        }
      } catch {
        /* ignore */
      }
    }
    if (variant === "research") {
      try {
        localStorage.removeItem("research-agent-chat-history")
      } catch {
        /* ignore */
      }
    }
    return variant === "regulatory" ? [] : [welcomeMessage]
  })

  const [regulatoryLogoFallback, setRegulatoryLogoFallback] = useState(false)
  const composeRequestIdRef = useRef(0)
  const [composeRequest, setComposeRequest] = useState<{ id: number; text: string } | null>(null)
  const [sessionDocuments, setSessionDocuments] = useState<{ id: string; filename: string; charCount?: number }[]>([])
  const [querySteps, setQuerySteps] = useState<QueryStep[]>([])
  const [currentStep, setCurrentStep] = useState<string | undefined>()
  const [isLoading, setIsLoading] = useState(false)
  /** When off, backend uses compact graph (fewer sources/steps). When on, full deep-research graph budget. */
  const [deepResearchEnabled, setDeepResearchEnabled] = useState(false)
  const showRegulatoryEphemeralWelcome =
    variant === "regulatory" && messages.length === 0 && !isLoading
  const [deepResearchTimeline, setDeepResearchTimeline] = useState<DeepResearchTimelineEntry[]>([])
  const [deepResearchSlideIndex, setDeepResearchSlideIndex] = useState(0)
  const [liveGraphPlanSummary, setLiveGraphPlanSummary] = useState<
    QueryProcessingSnapshot["graph_plan_summary"] | undefined
  >(undefined)
  const [liveExecutionTrace, setLiveExecutionTrace] = useState<QueryProcessingExecutionTraceEntry[]>([])
  const liveExecutionTraceRef = useRef<QueryProcessingExecutionTraceEntry[]>([])
  const drTimelineLenRef = useRef(0)
  const queryStepsRef = useRef<QueryStep[]>([])
  const deepResearchTimelineRef = useRef<DeepResearchTimelineEntry[]>([])
  const [sessionDeleteDialogOpen, setSessionDeleteDialogOpen] = useState(false)
  /** Remote regulatory: block sidebar activity until history fetch finishes (avoids reorder on tab open). */
  const [regulatoryHistoryReady, setRegulatoryHistoryReady] = useState(
    () => !(remotePersistence && variant === "regulatory"),
  )
  const sessionActivityBaselineLenRef = useRef<number | null>(null)
  const sessionActivityBaselineLastTsRef = useRef<number | null>(null)
  const abortResearchRef = useRef(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const progressStripRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!remotePersistence || variant !== "regulatory" || !sessionId) {
      setRegulatoryHistoryReady(true)
      return
    }
    const ac = new AbortController()
    setRegulatoryHistoryReady(false)
    sessionActivityBaselineLenRef.current = null
    sessionActivityBaselineLastTsRef.current = null
    ;(async () => {
      try {
        const rows = await chatListMessages(sessionId)
        if (ac.signal.aborted) return
        const mapped: Message[] = rows.map((m) => ({
          id: m.id,
          role: m.role as Message["role"],
          content: m.content,
          timestamp: new Date(m.timestamp),
          metadata: (m.metadata || undefined) as Message["metadata"],
        }))
        setMessages(mapped)
      } catch (e) {
        if (ac.signal.aborted) return
        toast.error("Could not load chat history", {
          description: e instanceof Error ? e.message : String(e),
        })
        setMessages([])
      } finally {
        if (!ac.signal.aborted) setRegulatoryHistoryReady(true)
      }
    })()
    return () => ac.abort()
  }, [sessionId, remotePersistence, variant])

  useEffect(() => {
    if (variant !== "regulatory" || !sessionId || !onResearchRunChange) return
    onResearchRunChange(sessionId, isLoading)
    return () => {
      onResearchRunChange(sessionId, false)
    }
  }, [variant, sessionId, isLoading, onResearchRunChange])

  useEffect(() => {
    return () => {
      const w = wsRef.current
      if (!w) return
      const ping = (w as { pingInterval?: ReturnType<typeof setInterval> }).pingInterval
      if (ping) clearInterval(ping)
      if (w.readyState === WebSocket.OPEN || w.readyState === WebSocket.CONNECTING) {
        w.close()
      }
      wsRef.current = null
    }
  }, [sessionId])

  useEffect(() => {
    queryStepsRef.current = querySteps
  }, [querySteps])

  useEffect(() => {
    deepResearchTimelineRef.current = deepResearchTimeline
  }, [deepResearchTimeline])

  useEffect(() => {
    liveExecutionTraceRef.current = liveExecutionTrace
  }, [liveExecutionTrace])

  useEffect(() => {
    const n = deepResearchTimeline.length
    if (n > drTimelineLenRef.current) {
      setDeepResearchSlideIndex(n - 1)
    } else if (n === 0) {
      setDeepResearchSlideIndex(0)
    } else if (n > 0) {
      setDeepResearchSlideIndex((i) => Math.min(i, n - 1))
    }
    drTimelineLenRef.current = n
  }, [deepResearchTimeline])

  useEffect(() => {
    if (!persistHistory || !storageKey || typeof window === "undefined") return
    if (remotePersistence && variant === "regulatory") return
    try {
      if (messages.length <= 1) return
      localStorage.setItem(
        storageKey,
        JSON.stringify(messages.map((m) => ({ ...m, timestamp: m.timestamp.toISOString() }))),
      )
    } catch {
      /* ignore */
    }
  }, [messages, persistHistory, storageKey, remotePersistence, variant])

  const sidebarTitle = useMemo(() => {
    const firstUser = messages.find((m) => m.role === "user")
    return firstUser ? titleFromFirstUserMessage(firstUser.content) : "New chat"
  }, [messages])

  useEffect(() => {
    if (!sessionId || !onSessionActivity) return
    if (remotePersistence && variant === "regulatory" && !regulatoryHistoryReady) return

    const len = messages.length
    const lastTs = len ? Math.max(...messages.map((m) => m.timestamp.getTime())) : Date.now()

    if (sessionActivityBaselineLenRef.current === null) {
      sessionActivityBaselineLenRef.current = len
      sessionActivityBaselineLastTsRef.current = lastTs
      onSessionActivity({
        sessionId,
        title: sidebarTitle,
        messageCount: len,
        bumpOrder: false,
        lastMessageAt: lastTs,
      })
      return
    }

    const prevLen = sessionActivityBaselineLenRef.current
    const prevLastTs = sessionActivityBaselineLastTsRef.current ?? 0
    const lenChanged = prevLen !== len
    const lastMessageAdvanced = lastTs > prevLastTs

    if (lenChanged || lastMessageAdvanced) {
      sessionActivityBaselineLenRef.current = len
      sessionActivityBaselineLastTsRef.current = lastTs
      onSessionActivity({
        sessionId,
        title: sidebarTitle,
        messageCount: len,
        bumpOrder: true,
        lastMessageAt: lastTs,
      })
      return
    }

    onSessionActivity({
      sessionId,
      title: sidebarTitle,
      messageCount: len,
      bumpOrder: false,
      lastMessageAt: lastTs,
    })
  }, [
    sessionId,
    sidebarTitle,
    messages,
    onSessionActivity,
    remotePersistence,
    variant,
    regulatoryHistoryReady,
  ])

  const PROGRESS_STRIP_H_KEY = "research-agent-progress-strip-px"
  const [progressStripHeightPx, setProgressStripHeightPx] = useState(280)
  const progressStripHeightRef = useRef(280)
  const progressStripDragRef = useRef<{ startY: number; startH: number } | null>(null)

  useEffect(() => {
    if (typeof window === "undefined") return
    try {
      const raw = sessionStorage.getItem(PROGRESS_STRIP_H_KEY)
      if (raw) {
        const n = parseInt(raw, 10)
        if (!Number.isNaN(n)) {
          const h = Math.min(560, Math.max(120, n))
          setProgressStripHeightPx(h)
          progressStripHeightRef.current = h
        }
      }
    } catch {
      /* ignore */
    }
  }, [])

  const handleSendMessage = async (
    content: string,
    attachments?: File[],
    options?: { skipUserMessage?: boolean },
  ) => {
    const skipUserMessage = options?.skipUserMessage ?? false
    const turnSessionId = sessionId ?? ""

    const userPersistId =
      remotePersistence && variant === "regulatory" && turnSessionId && !skipUserMessage
        ? typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? crypto.randomUUID()
          : `user-${Date.now()}`
        : ""

    const userMessage: Message = {
      id: userPersistId || `user-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date(),
      metadata: attachments
        ? {
            attachments: attachments.map((file) => ({
              id: `file-${Date.now()}-${file.name}`,
              name: file.name,
              type: file.type,
              size: file.size,
              url: URL.createObjectURL(file),
            })),
          }
        : undefined,
    }

    if (remotePersistence && variant === "regulatory" && turnSessionId && !skipUserMessage) {
      try {
        await chatAppendMessage(turnSessionId, {
          id: userMessage.id,
          role: "user",
          content,
          metadata: {},
        })
      } catch (e) {
        toast.error("Could not save message to history", {
          description: e instanceof Error ? e.message : String(e),
        })
        return
      }
    }

    let conversationBase = messages
    if (!skipUserMessage) {
      conversationBase = [...messages, userMessage]
      setMessages(conversationBase)
    }
    setIsLoading(true)
    abortResearchRef.current = false

    const persistRemoteAssistant = async (userClientId: string, ai: Message) => {
      if (!remotePersistence || variant !== "regulatory" || !turnSessionId || !userClientId) return
      try {
        await chatCompleteTurn(turnSessionId, {
          user_message_client_id: userClientId,
          assistant: {
            id: ai.id,
            content: ai.content,
            metadata: (ai.metadata || {}) as Record<string, unknown>,
          },
        })
      } catch (e) {
        toast.error("Could not save reply to history", {
          description: e instanceof Error ? e.message : String(e),
        })
      }
    }

    const lowerContent = content.toLowerCase()

    if (variant === "research") {

      // Handle trial selection commands
      if ((lowerContent.includes("select") || lowerContent.includes("pick") || lowerContent.includes("choose") || lowerContent.includes("find") || lowerContent.includes("filter") || lowerContent.includes("refine") || lowerContent.includes("narrow")) && 
        (lowerContent.includes("trial") || lowerContent.includes("trials"))) {
      
      // Determine if this is a refinement or new selection
      const isRefinement = lowerContent.includes("filter") || 
                          lowerContent.includes("refine") || 
                          lowerContent.includes("narrow") || 
                          lowerContent.includes("then") ||
                          lowerContent.includes("also") ||
                          lowerContent.includes("only") ||
                          (lowerContent.includes("to") && !lowerContent.includes("filter to"))
      
      
      // Extract the FULL criteria from the message for enhanced smart search
      // Remove only action words, preserve all search details
      const criteria = content
        .replace(/^(pick|select|choose|find|show|get|give me|display)\s+/i, '')
        .replace(/^all\s+(of\s+)?the\s+/i, '')
        .replace(/\s+trials?\s*$/i, '')
        .trim()
      
      
      
      // Execute the trial selection
      if (agentActions && agentActions.selectTrials) {
        await agentActions.selectTrials(criteria, isRefinement)
        
        // Add a response message
        const actionMessage: Message = {
          id: `action-${Date.now()}`,
          role: "assistant",
          content: isRefinement 
            ? `I've refined the selected trials to only those matching "${criteria}". The Reference Trials tab now shows the filtered results.`
            : `I've selected trials matching "${criteria}" and updated the Reference Trials tab. You can now see the selected trials in the Reference Trials section.`,
          timestamp: new Date(),
          agentName: "Study Design Assistant",
          agentType: "research",
          metadata: {
            action: isRefinement ? "refine_trials" : "select_trials",
            criteria: criteria,
            isRefinement: isRefinement
          }
        }
        
        setMessages((prev) => [...prev, actionMessage])
        setIsLoading(false)
        return
      } else {
        // Fall through to WebSocket processing
      }
    }
    
    // Handle simulation commands
    if (lowerContent.includes("run simulation") || lowerContent.includes("simulate")) {
      let simulationType = "startup"
      if (lowerContent.includes("budget")) {
        simulationType = "budget"
      } else if (lowerContent.includes("enrollment")) {
        simulationType = "enrollment"
      }
      
      if (agentActions && agentActions.runSimulation) {
        await agentActions.runSimulation(simulationType)
      } else {
      }
      
      const actionMessage: Message = {
        id: `action-${Date.now()}`,
        role: "assistant",
        content: `I've started a ${simulationType} simulation and switched to the Simulation tab. The results will appear shortly.`,
        timestamp: new Date(),
        agentName: "Study Design Assistant",
        agentType: "research",
        metadata: {
          action: "run_simulation",
          simulationType: simulationType
        }
      }
      
      setMessages((prev) => [...prev, actionMessage])
      setIsLoading(false)
      return
    }
    
    // Handle criteria generation commands
    if (lowerContent.includes("generate criteria") || lowerContent.includes("create criteria")) {
      let indication = "general"
      if (lowerContent.includes("obesity")) {
        indication = "obesity"
      } else if (lowerContent.includes("diabetes")) {
        indication = "diabetes"
      } else if (lowerContent.includes("cancer")) {
        indication = "cancer"
      }
      
      if (agentActions && agentActions.generateCriteria) {
        await agentActions.generateCriteria(indication)
      } else {
      }
      
      const actionMessage: Message = {
        id: `action-${Date.now()}`,
        role: "assistant",
        content: `I've generated inclusion/exclusion criteria for ${indication} studies and switched to the IE Criteria tab.`,
        timestamp: new Date(),
        agentName: "Study Design Assistant",
        agentType: "research",
        metadata: {
          action: "generate_criteria",
          indication: indication
        }
      }
      
      setMessages((prev) => [...prev, actionMessage])
      setIsLoading(false)
      return
    }
    
    // Handle site selection commands
    if (lowerContent.includes("select sites") || lowerContent.includes("find sites")) {
      let criteria = "optimal"
      if (lowerContent.includes("high performing")) {
        criteria = "high performing"
      } else if (lowerContent.includes("fast enrolling")) {
        criteria = "fast enrolling"
      }
      
      if (agentActions && agentActions.selectSites) {
        await agentActions.selectSites(criteria)
      } else {
      }
      
      const actionMessage: Message = {
        id: `action-${Date.now()}`,
        role: "assistant",
        content: `I've analyzed and selected ${criteria} sites for your study and switched to the Site Selection tab.`,
        timestamp: new Date(),
        agentName: "Study Design Assistant",
        agentType: "research",
        metadata: {
          action: "select_sites",
          criteria: criteria
        }
      }
      
      setMessages((prev) => [...prev, actionMessage])
      setIsLoading(false)
      return
    }
    
    // Handle tab switching commands
    if (lowerContent.includes("switch to") || lowerContent.includes("go to") || lowerContent.includes("show")) {
      let targetTab = ""
      if (lowerContent.includes("reference") || lowerContent.includes("trials")) {
        targetTab = "reference-trials"
      } else if (lowerContent.includes("criteria") || lowerContent.includes("inclusion") || lowerContent.includes("exclusion")) {
        targetTab = "ie-criteria"
      } else if (lowerContent.includes("site") || lowerContent.includes("sites")) {
        targetTab = "site-selection"
      } else if (lowerContent.includes("simulation") || lowerContent.includes("simulate")) {
        targetTab = "simulation"
      } else if (lowerContent.includes("budget") || lowerContent.includes("cost")) {
        targetTab = "budget"
      } else if (lowerContent.includes("protocol") || lowerContent.includes("title")) {
        targetTab = "protocol-title"
      } else if (lowerContent.includes("rationale")) {
        targetTab = "rationale"
      } else if (lowerContent.includes("objectives")) {
        targetTab = "objectives"
      } else if (lowerContent.includes("endpoints")) {
        targetTab = "endpoints"
      } else if (lowerContent.includes("design")) {
        targetTab = "overall-design"
      } else if (lowerContent.includes("schema")) {
        targetTab = "schema"
      } else if (lowerContent.includes("soa") || lowerContent.includes("schedule")) {
        targetTab = "soa"
      }
      
      if (targetTab) {
        if (agentActions && agentActions.switchToTab) {
          agentActions.switchToTab(targetTab)
        } else {
        }
        
        const actionMessage: Message = {
          id: `action-${Date.now()}`,
          role: "assistant",
          content: `I've switched to the ${targetTab.replace('-', ' ')} tab for you.`,
          timestamp: new Date(),
          agentName: "Study Design Assistant",
          agentType: "research",
          metadata: {
            action: "switch_tab",
            targetTab: targetTab
          }
        }
        
        setMessages((prev) => [...prev, actionMessage])
        setIsLoading(false)
        return
      }
    }
    }

    let regulatoryDocumentIds: string[] = Array.from(new Set(sessionDocuments.map((d) => d.id)))
    if (enableDocumentContext && attachments?.length) {
      for (const file of attachments) {
        try {
          const fd = new FormData()
          fd.append("file", file)
          const res = await fetch(ENDPOINTS.regulatoryDocuments, { method: "POST", body: fd })
          if (!res.ok) {
            const errText = await res.text()
            throw new Error(errText || `Upload failed (${res.status})`)
          }
          const meta = (await res.json()) as {
            document_id: string
            filename: string
            char_count?: number
          }
          regulatoryDocumentIds = Array.from(new Set([...regulatoryDocumentIds, meta.document_id]))
          setSessionDocuments((prev) => [
            ...prev,
            { id: meta.document_id, filename: meta.filename, charCount: meta.char_count },
          ])
        } catch (e) {
          toast.error(e instanceof Error ? e.message : "Document upload failed")
          setIsLoading(false)
          return
        }
      }
    }

    const researchRestPayload: ResearchRestPayload = {
      query: content,
      conversation_history: conversationBase.slice(-5).map((msg) => ({
        role: msg.role,
        content: msg.content,
        timestamp:
          msg.timestamp instanceof Date ? msg.timestamp.toISOString() : String(msg.timestamp ?? ""),
      })),
      selected_agents: [],
      study_context: (studyContext as Record<string, unknown> | undefined) || undefined,
      selected_trials: selectedTrials || undefined,
      deep_research: deepResearchEnabled,
      regulatory_document_ids:
        enableDocumentContext && regulatoryDocumentIds.length > 0
          ? regulatoryDocumentIds
          : undefined,
    }

    let queryCompleted = false
    let recoveryAttempted = false

    const applyRestJsonToChat = (json: ResearchRestResponse) => {
        const synthesis = json.synthesis
        const answer =
          typeof synthesis?.answer === "string" && synthesis.answer.trim()
            ? synthesis.answer
            : "The server returned no answer text."
        const assistantId =
          remotePersistence && variant === "regulatory" && typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
            ? crypto.randomUUID()
            : `ai-${Date.now()}`
        const graphPlan = json.graph_plan
        const completedIds = new Set<string>()
        if (graphPlan?.nodes && Array.isArray(graphPlan.nodes)) {
          for (const n of graphPlan.nodes) {
            if (n && typeof n === "object" && typeof n.id === "string" && n.id) completedIds.add(n.id)
          }
        }
        const restSteps = withPlanningStepFirst(graphPlan, graphPlanToQuerySteps(graphPlan, completedIds))
        const normalizedCitations = normalizeChatCitations(synthesis?.citations)
        const footerCitations = filterCitationsForFooter(answer, normalizedCitations)
        const citationDr = buildCitationThinkingEntry(answer, normalizedCitations, footerCitations)
        const queryProcessing = buildQueryProcessingSnapshot({
          querySteps: restSteps,
          deepResearchTimeline: [citationDr],
          graphPlan,
          executionTrace: json.execution_trace,
        })
        const aiMessage: Message = {
          id: assistantId,
          role: "assistant",
          content: answer,
          timestamp: new Date(),
          agentName: "Multi-Agent Research Platform",
          agentType: "research",
          metadata: {
            citations: normalizedCitations,
            confidence: synthesis?.confidence ?? 0.8,
            data_quality: synthesis?.data_quality ?? "good",
            processing_time: json.metadata?.processing_time ?? 0,
            agents_used:
              json.graph_plan?.nodes
                ?.map((n) => (typeof n.agent_type === "string" ? n.agent_type : ""))
                .filter(Boolean) as string[] | undefined,
            ...(queryProcessing ? { query_processing: queryProcessing } : {}),
          },
        }
        setMessages((prev) => [...prev, aiMessage])
        setIsLoading(false)
        setQuerySteps([])
        setCurrentStep(undefined)
        setDeepResearchTimeline([])
        deepResearchTimelineRef.current = []
        setLiveGraphPlanSummary(undefined)
        setLiveExecutionTrace([])
        void persistRemoteAssistant(userPersistId, aiMessage)
    }

    const tryHttpRecovery = async () => {
      if (abortResearchRef.current || recoveryAttempted || queryCompleted) return
      recoveryAttempted = true
      try {
        toast.message("Finishing via HTTP", {
          description: "WebSocket closed before the final message — fetching the same query over HTTP.",
        })
        const json = await fetchResearchViaRest(researchRestPayload)
        queryCompleted = true
        applyRestJsonToChat(json)
      } catch (e) {
        setIsLoading(false)
        const msg = e instanceof Error ? e.message : String(e)
        toast.error("Could not recover answer", { description: msg })
        setMessages((prev) => [
          ...prev,
          {
            id: `ai-err-${Date.now()}`,
            role: "assistant",
            content: `The research connection dropped before the final answer arrived, and the HTTP fallback also failed.\n\n**Error:** ${msg}\n\n**Tip:** Ensure the API is reachable at ${getAgentHttpBase()} and try again. Demo / mock responses are disabled so you always see real errors.`,
            timestamp: new Date(),
            agentName: "System",
            agentType: "research",
          },
        ])
      }
    }

    try {
      // Try to connect to Multi-Agent Backend WebSocket (port 8001)
      const wsUrl = process.env.NEXT_PUBLIC_AGENT_WS_URL || "ws://127.0.0.1:8001/ws"
      const clientId = `client-${Date.now()}`
      const ws = new WebSocket(`${wsUrl}/${clientId}`)
      wsRef.current = ws

      ws.onopen = () => {
        setDeepResearchTimeline([])
        deepResearchTimelineRef.current = []
        setLiveGraphPlanSummary(undefined)
        setLiveExecutionTrace([])
        drTimelineLenRef.current = 0

        // Start keep-alive ping every 30 seconds
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }))
          }
        }, 30000)
        
        // Store ping interval on WebSocket for cleanup
        ;(ws as any).pingInterval = pingInterval
        
        const queryMessage = {
          type: "query",
          data: {
            query: content,
            conversation_history: conversationBase.slice(-5).map((msg) => ({
              role: msg.role,
              content: msg.content,
              timestamp: msg.timestamp instanceof Date ? msg.timestamp.toISOString() : msg.timestamp,
            })),
            selected_agents: [],
            study_context: studyContext || undefined,
            selected_trials: selectedTrials || undefined,
            workspace: variant,
            deep_research: deepResearchEnabled,
            regulatory_document_ids:
              enableDocumentContext && regulatoryDocumentIds.length > 0
                ? regulatoryDocumentIds
                : undefined,
          },
        }
        
        ws.send(JSON.stringify(queryMessage))
      }
      
      ws.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data)
          
          // Handle pong responses to keep-alive pings
          if (data.type === "pong") {
            return
          }

          const pushDr = (entry: Omit<DeepResearchTimelineEntry, "key"> & { key?: string }) => {
            const key = entry.key ?? `dr-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
            setDeepResearchTimeline((prev) => {
              const next = [...prev, { ...entry, key }].slice(-40)
              deepResearchTimelineRef.current = next
              return next
            })
          }

          if (data.type === "research_brief_ready") {
            const d = (data.data || {}) as Record<string, unknown>
            const thinking = asTrimmedStringArray(d.thinking_lines)
            const bullets: string[] = []
            const brief = typeof d.brief === "string" ? d.brief.trim() : ""
            if (brief) {
              bullets.push(
                brief.length > 2200 ? `${brief.slice(0, 2200)}…` : brief,
              )
            }
            for (const a of asTrimmedStringArray(d.assumptions).slice(0, 14)) {
              bullets.push(`Assumption: ${a}`)
            }
            for (const m of asTrimmedStringArray(
              Array.isArray(d.must_have_facts) ? d.must_have_facts : [],
            ).slice(0, 14)) {
              bullets.push(`Must-have checkpoint: ${m}`)
            }
            pushDr({
              title: "Research brief & scope",
              timestamp: typeof data.timestamp === "string" ? data.timestamp : undefined,
              thinkingLines: thinking,
              bullets,
            })
            return
          }
          if (data.type === "research_outline_ready") {
            const d = (data.data || {}) as Record<string, unknown>
            const thinking = asTrimmedStringArray(d.thinking_lines)
            const bullets: string[] = []
            const preview = Array.isArray(d.sections_preview) ? d.sections_preview : []
            for (const raw of preview.slice(0, 14)) {
              if (!raw || typeof raw !== "object") continue
              const s = raw as Record<string, unknown>
              const sid = typeof s.section_id === "string" ? s.section_id : ""
              const title = typeof s.title === "string" ? s.title : ""
              const n = typeof s.sub_question_count === "number" ? s.sub_question_count : 0
              bullets.push(`[${sid}] ${title} — ${n} sub-question(s)`)
              const subs = Array.isArray(s.sub_questions_preview) ? s.sub_questions_preview : []
              for (const sq of subs) {
                if (typeof sq === "string" && sq.trim()) bullets.push(`  • ${sq.trim()}`)
              }
            }
            pushDr({
              title: "Research outline",
              timestamp: typeof data.timestamp === "string" ? data.timestamp : undefined,
              thinkingLines: thinking,
              bullets,
            })
            return
          }
          if (data.type === "deep_research_phase") {
            const d = (data.data || {}) as Record<string, unknown>
            const thinking = asTrimmedStringArray(d.thinking_lines)
            const bullets: string[] = []
            if (typeof d.message === "string" && d.message.trim()) {
              bullets.push(d.message.trim())
            }
            if (typeof d.execution_order_preview === "string" && d.execution_order_preview.trim()) {
              bullets.push(`Order: ${d.execution_order_preview}`)
            }
            if (typeof d.planner_reasoning === "string" && d.planner_reasoning.trim()) {
              const pr = d.planner_reasoning.trim()
              bullets.push(pr.length > 3500 ? `${pr.slice(0, 3500)}…` : pr)
            }
            const ns = Array.isArray(d.node_summary) ? d.node_summary : []
            for (const raw of ns.slice(0, 24)) {
              if (!raw || typeof raw !== "object") continue
              const n = raw as Record<string, unknown>
              const id = typeof n.id === "string" ? n.id : ""
              const typ = typeof n.type === "string" ? n.type : ""
              const desc = typeof n.description === "string" ? n.description : ""
              if (id) bullets.push(`${id} (${typ}): ${desc}`)
            }
            const omitted = d.extra_nodes_omitted
            if (typeof omitted === "number" && omitted > 0) {
              bullets.push(`… and ${omitted} more node(s) not listed here.`)
            }
            const refl = d.reflection
            if (refl && typeof refl === "object") {
              const rf = refl as Record<string, unknown>
              if (rf.usefulness_score !== undefined) {
                bullets.push(`Usefulness score: ${String(rf.usefulness_score)}`)
              }
              if (rf.source_quality !== undefined) {
                bullets.push(`Source quality: ${String(rf.source_quality)}`)
              }
              if (typeof rf.rationale === "string" && rf.rationale.trim()) {
                const rat = rf.rationale.trim()
                bullets.push(rat.length > 1200 ? `${rat.slice(0, 1200)}…` : rat)
              }
              if (typeof rf.what_changed === "string" && rf.what_changed.trim()) {
                const wc = rf.what_changed.trim()
                bullets.push(`Draft update: ${wc.length > 600 ? `${wc.slice(0, 600)}…` : wc}`)
              }
            }
            if (typeof d.working_answer_excerpt === "string" && d.working_answer_excerpt.trim()) {
              const ex = d.working_answer_excerpt.trim()
              bullets.push(`Working answer (excerpt): ${ex.length > 900 ? `${ex.slice(0, 900)}…` : ex}`)
            }
            if (d.skip_remaining_searches === true) {
              bullets.push("Later searches may be skipped based on this reflection.")
            }
            const phaseLabel =
              typeof data.phase === "string" && data.phase
                ? data.phase.replace(/_/g, " ")
                : "Deep research"
            pushDr({
              title: phaseLabel,
              timestamp: typeof data.timestamp === "string" ? data.timestamp : undefined,
              thinkingLines: thinking,
              bullets,
            })
            return
          }
          if (data.type === "subruns_merged") {
            const d = (data.data || {}) as Record<string, unknown>
            pushDr({
              title: "Parallel branches merged",
              timestamp: typeof data.timestamp === "string" ? data.timestamp : undefined,
              thinkingLines: asTrimmedStringArray(d.thinking_lines),
              bullets: [],
            })
            return
          }
          if (data.type === "verifier_result") {
            const d = (data.data || {}) as Record<string, unknown>
            const passed = d.passed === true
            const thinking = asTrimmedStringArray(d.thinking_lines)
            const detail = asTrimmedStringArray(d.detail_bullets)
            pushDr({
              title: passed ? "Verifier: passed" : "Verifier: gaps found",
              timestamp: typeof data.timestamp === "string" ? data.timestamp : undefined,
              thinkingLines: thinking,
              bullets: detail,
            })
            return
          }
          if (data.type === "replan_started") {
            const d = (data.data || {}) as Record<string, unknown>
            const round = d.round
            const maxR = d.max_rounds
            const roundLabel =
              typeof round === "number" && typeof maxR === "number"
                ? ` (round ${round}/${maxR})`
                : ""
            const thinking = asTrimmedStringArray(d.thinking_lines)
            const gapBullets = asTrimmedStringArray(d.gap_bullets)
            const addBullets: string[] = []
            const adds = Array.isArray(d.planned_additions) ? d.planned_additions : []
            for (const raw of adds) {
              if (!raw || typeof raw !== "object") continue
              const n = raw as Record<string, unknown>
              const id = typeof n.id === "string" ? n.id : ""
              const typ = typeof n.type === "string" ? n.type : ""
              const desc = typeof n.description === "string" ? n.description : ""
              if (id) addBullets.push(`Add ${id} [${typ}]: ${desc}`)
            }
            pushDr({
              title: `Replanning${roundLabel}`,
              timestamp: typeof data.timestamp === "string" ? data.timestamp : undefined,
              thinkingLines: thinking,
              bullets: [...gapBullets, ...addBullets],
            })
            const gp = data.data?.graph_plan as { nodes?: unknown[]; reasoning?: unknown } | undefined
            if (gp?.nodes && Array.isArray(gp.nodes)) {
              setQuerySteps((prev) => {
                const completed = new Set<string>()
                for (const s of prev) {
                  if (s.status === "completed") completed.add(s.id)
                }
                return withPlanningStepFirst(gp, graphPlanToQuerySteps(gp, completed))
              })
            }
            return
          }
          
          // Handle query_started with graph plan
          if (data.type === "query_started") {
            const graphPlan = data.data?.graph_plan
            const steps = graphPlanToQuerySteps(graphPlan)
            if (steps.length > 0) {
              setQuerySteps(withPlanningStepFirst(graphPlan, steps))
            }
            setLiveGraphPlanSummary(graphPlanToProcessingSummary(graphPlan))
            return
          }
          
          // Handle node_progress updates
          if (data.type === "node_progress") {
            const nodeData = data.data as Record<string, unknown> | undefined
            const nodeId = typeof nodeData?.node_id === "string" ? nodeData.node_id : undefined
            const status = typeof nodeData?.status === "string" ? nodeData.status : undefined

            if (nodeId) {
              if (status === "started" || status === "in_progress") {
                setCurrentStep(nodeId)
              }
              setLiveExecutionTrace((prev) => upsertExecutionTraceFromNodeProgress(prev, nodeData || {}))
              setQuerySteps((prev) => {
                const idx = prev.findIndex((s) => s.id === nodeId)
                const mergedDetail = mergeNodeProgressDetail(
                  idx >= 0 ? prev[idx]?.detail : undefined,
                  nodeData || {},
                )
                if (idx < 0) {
                  const name = formatGraphNodeIdForDisplay(nodeId, prev.length)
                  const desc =
                    typeof nodeData?.description === "string" && nodeData.description
                      ? nodeData.description
                      : "Additional research step"
                  const agent =
                    typeof nodeData?.node_type === "string" ? nodeData.node_type : "unknown"
                  let st: QueryStep["status"] = "pending"
                  if (status === "started" || status === "in_progress") st = "in-progress"
                  else if (status === "completed" || status === "skipped") st = "completed"
                  else if (status === "failed") st = "error"
                  const row: QueryStep = {
                    id: nodeId,
                    name,
                    description: desc,
                    status: st,
                    agent,
                  }
                  if (mergedDetail) row.detail = mergedDetail
                  if (nodeId === ORCHESTRATION_PLANNING_NODE_ID) {
                    const rest = prev.filter((s) => s.id !== ORCHESTRATION_PLANNING_NODE_ID)
                    return [row, ...rest]
                  }
                  return [...prev, row]
                }
                return prev.map((step) => {
                  if (step.id !== nodeId) return step
                  const updates: Partial<QueryStep> = {}
                  if (status === "started" || status === "in_progress") {
                    updates.status = "in-progress"
                  } else if (status === "completed" || status === "skipped") {
                    updates.status = "completed"
                  } else if (status === "failed") {
                    updates.status = "error"
                  }
                  const incomingDesc =
                    typeof nodeData?.description === "string" ? nodeData.description.trim() : ""
                  if (incomingDesc) {
                    updates.description = incomingDesc
                  }
                  const nextDetail = mergeNodeProgressDetail(step.detail, nodeData || {})
                  return {
                    ...step,
                    ...updates,
                    ...(nextDetail ? { detail: nextDetail } : {}),
                  }
                })
              })
            }
            return
          }
          
          if (data.type === "query_completed") {
            if (queryCompleted) return
            queryCompleted = true
            const synthesis = data.data?.synthesis
            const answer = synthesis?.answer || "I've processed your query. Here's what I found..."

            const assistantWsId =
              remotePersistence && variant === "regulatory" && typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
                ? crypto.randomUUID()
                : `ai-${Date.now()}`
            const serverTrace = data.data?.execution_trace
            const executionTraceForSnap =
              Array.isArray(serverTrace) && serverTrace.length > 0 ? serverTrace : liveExecutionTraceRef.current
            const normalizedCitations = normalizeChatCitations(synthesis?.citations)
            const footerCitations = filterCitationsForFooter(answer, normalizedCitations)
            const citationDr = buildCitationThinkingEntry(answer, normalizedCitations, footerCitations)
            const drTimelineForSnap = [...deepResearchTimelineRef.current, citationDr].slice(-40)
            const queryProcessing = buildQueryProcessingSnapshot({
              querySteps: queryStepsRef.current,
              deepResearchTimeline: drTimelineForSnap,
              graphPlan: data.data?.graph_plan,
              executionTrace: executionTraceForSnap,
            })
            const aiMessage: Message = {
              id: assistantWsId,
              role: "assistant",
              content: answer,
              timestamp: new Date(),
              agentName: "Multi-Agent Research Platform",
              agentType: "research",
              metadata: {
                citations: normalizedCitations,
                confidence: synthesis?.confidence || 0.8,
                data_quality: synthesis?.data_quality || "good",
                processing_time: data.data?.processing_time || 0,
                agents_used: data.data?.graph_plan?.nodes?.map((n: any) => n.agent_type) || [],
                ...(queryProcessing ? { query_processing: queryProcessing } : {}),
              },
            }

            setMessages((prev) => [...prev, aiMessage])
            setIsLoading(false)

            // Clear progress steps & deep-research cards (snapshot already captured on the message)
            setQuerySteps([])
            setCurrentStep(undefined)
            setDeepResearchTimeline([])
            deepResearchTimelineRef.current = []
            setLiveGraphPlanSummary(undefined)
            setLiveExecutionTrace([])
            if ((ws as any).pingInterval) {
              clearInterval((ws as any).pingInterval)
            }

            ws.close()
            void persistRemoteAssistant(userPersistId, aiMessage)

            // Study-design side effects only (regulatory chat has no agentActions). Never block the bubble above.
            void (async () => {
              try {
                const lowerAnswer = answer.toLowerCase()

                if (
                  (lowerAnswer.includes("found") || lowerAnswer.includes("identified")) &&
                  lowerAnswer.includes("trial")
                ) {
                  const criteria = content
                    .replace(/^(pick|select|choose|find|show|get|give me|display)\s+/i, "")
                    .replace(/^all\s+(of\s+)?the\s+/i, "")
                    .replace(/\s+trials?\s*$/i, "")
                    .trim()

                  if (criteria && agentActions && agentActions.selectTrials) {
                    await agentActions.selectTrials(criteria, false)
                  }
                }

                const graphPlan = data.data?.graph_plan
                const executionResults = data.data?.results || data.data?.execution_results

                if (graphPlan && graphPlan.nodes && executionResults && agentActions) {
                  const sectionMapping: { [key: string]: string } = {
                    title: "title",
                    introduction: "introduction",
                    rationale: "rationale",
                    background: "background",
                    hypothesis: "hypothesis",
                    primary_objectives: "primary_objectives",
                    secondary_objectives: "secondary_objectives",
                    primary_endpoints: "primary_endpoints",
                    secondary_endpoints: "secondary_endpoints",
                    inclusion_criteria: "inclusion_criteria",
                    exclusion_criteria: "exclusion_criteria",
                    study_design: "study_design",
                    schedule_of_activities: "soa",
                    schema: "schema",
                  }

                  for (const node of graphPlan.nodes) {
                    if (node.type === "protocol_generate" || node.type === "protocol_full") {
                      const nodeResults = executionResults[node.id]

                      if (nodeResults) {
                        if (node.type === "protocol_generate") {
                          const result = Array.isArray(nodeResults) ? nodeResults[0] : nodeResults
                          const sectionType = result?.section_type || node.parameters?.section_type
                          const sectionId = sectionMapping[sectionType as string]
                          const sectionContent = result?.content

                          if (sectionId && sectionContent) {
                            await agentActions.updateProtocolSection?.(sectionId, sectionContent)

                            if (
                              sectionId === "rationale" ||
                              sectionId === "introduction" ||
                              sectionId === "background"
                            ) {
                              agentActions.switchToTab?.("rationale")
                            } else if (sectionId.includes("objectives")) {
                              agentActions.switchToTab?.("objectives")
                            } else if (sectionId.includes("endpoints")) {
                              agentActions.switchToTab?.("endpoints")
                            } else if (sectionId.includes("criteria")) {
                              agentActions.switchToTab?.("ie-criteria")
                            } else if (sectionId === "study_design") {
                              agentActions.switchToTab?.("overall-design")
                            } else if (sectionId === "soa") {
                              agentActions.switchToTab?.("soa")
                            } else if (sectionId === "schema") {
                              agentActions.switchToTab?.("schema")
                            }
                          }
                        }

                        if (node.type === "protocol_full") {
                          const result = Array.isArray(nodeResults) ? nodeResults[0] : nodeResults
                          const sections = result?.protocol_sections

                          if (sections) {
                            for (const [sectionType, secContent] of Object.entries(sections)) {
                              const sectionId = sectionMapping[sectionType]
                              if (sectionId && typeof secContent === "string") {
                                await agentActions.updateProtocolSection?.(sectionId, secContent)
                              }
                            }
                            agentActions.switchToTab?.("protocol-title")
                          }
                        }
                      }
                    }

                    if (node.type === "synthesize" || node.type === "synthesis") {
                      const nodeId = node.id?.toLowerCase() || ""
                      const nodeDesc = node.description?.toLowerCase() || ""

                      if (
                        nodeId.includes("rationale") ||
                        nodeDesc.includes("rationale") ||
                        nodeDesc.includes("study rationale")
                      ) {
                        const nodeResults = executionResults[node.id]

                        if (nodeResults && synthesis?.answer) {
                          await agentActions.updateProtocolSection?.("rationale", synthesis.answer)
                          agentActions.switchToTab?.("rationale")
                        }
                      }

                      if (nodeId.includes("background") || nodeDesc.includes("background")) {
                        const nodeResults = executionResults[node.id]
                        if (nodeResults && synthesis?.answer) {
                          await agentActions.updateProtocolSection?.("background", synthesis.answer)
                          agentActions.switchToTab?.("rationale")
                        }
                      }

                      if (nodeId.includes("objective") || nodeDesc.includes("objective")) {
                        const nodeResults = executionResults[node.id]
                        if (nodeResults && synthesis?.answer) {
                          await agentActions.updateProtocolSection?.("primary_objectives", synthesis.answer)
                          agentActions.switchToTab?.("objectives")
                        }
                      }
                    }
                  }
                }
              } catch (e) {
                toast.error("Could not apply follow-up actions from this answer", {
                  description: e instanceof Error ? e.message : String(e),
                })
              }
            })()
          } else if (data.type === "node_started" || data.type === "node_completed") {
            // Handle progress updates
          } else if (data.type === "error") {
            const errText =
              typeof data.error === "string" && data.error.trim()
                ? data.error
                : typeof data.message === "string" && data.message.trim()
                  ? data.message
                  : "Multi-agent processing error"
            throw new Error(errText)
          }
        } catch {
          toast.error("Chat connection error", {
            description: "The research stream sent a message that could not be processed.",
          })
          setIsLoading(false)
          ws.close()
        }
      }
      
      ws.onerror = () => {}

      ws.addEventListener("close", () => {
        const ping = (ws as { pingInterval?: ReturnType<typeof setInterval> }).pingInterval
        if (ping) clearInterval(ping)
        if (wsRef.current === ws) wsRef.current = null
        if (!queryCompleted && !abortResearchRef.current) {
          void tryHttpRecovery()
        }
      })
    } catch (error) {
      setIsLoading(false)
      toast.error("Could not open WebSocket", {
        description: error instanceof Error ? error.message : String(error),
      })
      void fetchResearchViaRest(researchRestPayload)
        .then((json) => {
          queryCompleted = true
          applyRestJsonToChat(json)
        })
        .catch((e) => {
          const msg = e instanceof Error ? e.message : String(e)
          setMessages((prev) => [
            ...prev,
            {
              id: `ai-err-${Date.now()}`,
              role: "assistant",
              content: `Could not connect over WebSocket or HTTP.\n\n**Error:** ${msg}\n\nCheck ${getAgentHttpBase()} and NEXT_PUBLIC_AGENT_WS_URL / NEXT_PUBLIC_API_URL.`,
              timestamp: new Date(),
              agentName: "System",
              agentType: "research",
            },
          ])
        })
    }
  }

  const handleStopGeneration = () => {
    abortResearchRef.current = true
    const w = wsRef.current
    if (w && w.readyState === WebSocket.OPEN) {
      const ping = (w as unknown as { pingInterval?: ReturnType<typeof setInterval> }).pingInterval
      if (ping) clearInterval(ping)
      w.close()
      if (wsRef.current === w) wsRef.current = null
    }
    setIsLoading(false)
    setQuerySteps([])
    setCurrentStep(undefined)
    setDeepResearchTimeline([])
    deepResearchTimelineRef.current = []
    setLiveGraphPlanSummary(undefined)
    setLiveExecutionTrace([])
  }

  const handleRegenerateAssistant = (assistantIndex: number) => {
    setMessages((m) => {
      if (assistantIndex <= 0) return m
      const prevUser = m[assistantIndex - 1]
      if (!prevUser || prevUser.role !== "user") return m
      const userContent = prevUser.content
      queueMicrotask(() =>
        void handleSendMessage(userContent, undefined, { skipUserMessage: true }),
      )
      return m.slice(0, assistantIndex)
    })
  }

  const handleClearChat = () => {
    setMessages(variant === "regulatory" ? [] : [{ ...welcomeMessage, timestamp: new Date() }])
    setSessionDocuments([])

    if (typeof window !== "undefined" && storageKey) {
      try {
        localStorage.removeItem(storageKey)
      } catch {
        /* ignore */
      }
    }
    if (variant === "research") {
      try {
        localStorage.removeItem("research-agent-chat-history")
      } catch {
        /* ignore */
      }
    }
  }

  const handleTrashButtonClick = () => {
    if (onConfirmDeleteSession && sessionId) {
      setSessionDeleteDialogOpen(true)
      return
    }
    handleClearChat()
  }

  const handleConfirmDeleteSession = async () => {
    if (!sessionId || !onConfirmDeleteSession) return
    try {
      await onConfirmDeleteSession(sessionId)
      setSessionDeleteDialogOpen(false)
    } catch (e) {
      toast.error("Could not delete chat", {
        description: e instanceof Error ? e.message : String(e),
      })
    }
  }

  const isEnterprise = presentation === "enterprise"

  const bubbleAppearance = isEnterprise ? "enterprise" : "default"

  return (
    <div
      className={cn(
        "flex flex-col h-full w-full overflow-hidden",
        isEnterprise ? "bg-[#fafafa] dark:bg-background" : "bg-background",
      )}
    >
      {isEnterprise ? (
        <header className="flex items-center justify-between px-5 py-3.5 border-b border-border/40 bg-background/90 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <h1 className="text-[17px] font-medium text-foreground truncate">Regulatory Assistant</h1>
            <Badge variant="secondary" className="rounded-full text-[10px] font-normal px-2 py-0">
              Preview
            </Badge>
          </div>
          <div className="flex items-center gap-0.5 relative">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => backendLogs.open()}
              className="h-9 w-9 rounded-full relative"
              title="Backend logs"
              type="button"
            >
              <Terminal className="h-4 w-4" />
              {backendLogs.errorCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-0.5 text-[10px] font-medium text-destructive-foreground">
                  {backendLogs.errorCount > 9 ? "9+" : backendLogs.errorCount}
                </span>
              )}
            </Button>
            {isLoading && (
              <Button variant="outline" size="sm" onClick={handleStopGeneration} className="h-8 gap-1 rounded-full ml-1">
                <Square className="h-3.5 w-3.5" />
                Stop
              </Button>
            )}
            <div className="ml-1 flex h-9 w-9 items-center justify-center rounded-full bg-muted border border-border/50">
              <User className="h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </header>
      ) : (
        <div className="flex items-center justify-end px-4 sm:px-6 py-3 border-b border-border/40 flex-shrink-0 bg-card/50">
          <div className="flex items-center gap-2 flex-wrap">
            {isLoading && (
              <Button variant="outline" size="sm" onClick={handleStopGeneration} className="h-8 gap-1">
                <Square className="h-3.5 w-3.5" />
                Stop
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => backendLogs.open()}
              className="h-8 w-8 relative"
              title="Backend logs"
              type="button"
            >
              <Terminal className="h-3.5 w-3.5" />
              {backendLogs.errorCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-destructive px-0.5 text-[9px] font-medium text-destructive-foreground">
                  {backendLogs.errorCount > 9 ? "9+" : backendLogs.errorCount}
                </span>
              )}
            </Button>
            <Button variant="ghost" size="icon" onClick={handleTrashButtonClick} className="h-8 w-8" title={onConfirmDeleteSession && sessionId ? "Delete chat" : "Clear chat"}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* flex-1 column: messages get remaining height; progress strip is max-height + scrolls internally */}
      <div className="flex flex-1 flex-col min-h-0 w-full overflow-hidden">
        <div
          ref={scrollAreaRef}
          className={cn(
            "flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden overscroll-y-contain",
            "[scrollbar-gutter:stable]",
          )}
        >
          <div
            className={cn(
              "mx-auto w-full py-6 space-y-4",
              isEnterprise ? "max-w-6xl px-4 sm:px-8 lg:px-10" : "max-w-5xl px-4 sm:px-6",
            )}
          >
            {showRegulatoryEphemeralWelcome && (
              <div
                className={cn(
                  "w-full flex flex-col items-center justify-center text-center px-4",
                  "min-h-[min(44vh,26rem)] py-8 sm:py-12 pb-6",
                )}
              >
                <div className="mb-6 relative flex h-[128px] w-[128px] shrink-0 items-center justify-center">
                  <div
                    className="pointer-events-none absolute inset-[-20%] rounded-full bg-gradient-to-br from-amber-200/40 via-transparent to-sky-200/30 blur-2xl dark:from-amber-500/15 dark:to-sky-500/10"
                    aria-hidden
                  />
                  <div className="relative z-10 flex h-28 w-28 items-center justify-center overflow-hidden rounded-2xl border border-border/80 bg-card/80 shadow-sm">
                    {regulatoryLogoFallback ? (
                      <LotorLabLogoFallback className="h-full w-full" />
                    ) : (
                      <img
                        src="/lotor-lab-logo.png"
                        alt="Lotor Lab raccoon logo"
                        width={112}
                        height={112}
                        decoding="async"
                        fetchPriority="high"
                        className="h-[5.5rem] w-[5.5rem] object-contain"
                        onError={() => setRegulatoryLogoFallback(true)}
                      />
                    )}
                  </div>
                </div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-2">
                  Lotor Lab
                </p>
                <h2 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight mb-3 text-balance max-w-lg">
                  {regulatoryEphemeralAgentName}
                </h2>
                <p className="text-muted-foreground text-sm sm:text-base max-w-lg mb-8 text-pretty leading-relaxed">
                  Grounded answers from FDA, EMA, China agencies, trial registries, literature, and more—upload context or
                  start from a sample question below.
                </p>
                {regulatoryEphemeralWelcomeMarkdown.trim() ? (
                  <div
                    className={cn(
                      "prose prose-sm max-w-xl mx-auto prose-slate dark:prose-invert text-center mb-10",
                      "prose-p:text-muted-foreground prose-p:text-sm sm:prose-p:text-base prose-p:leading-relaxed",
                      "[&_strong]:text-foreground/90",
                    )}
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {regulatoryEphemeralWelcomeMarkdown}
                    </ReactMarkdown>
                  </div>
                ) : null}
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-3 w-full max-w-2xl text-left sm:text-center">
                  Sample queries
                </p>
                <div className="flex flex-wrap gap-2 justify-center max-w-3xl">
                  {REGULATORY_SUGGESTION_CHIPS.map((chip) => (
                    <button
                      key={chip.label}
                      type="button"
                      onClick={() => {
                        composeRequestIdRef.current += 1
                        setComposeRequest({ id: composeRequestIdRef.current, text: chip.prompt })
                      }}
                      className="rounded-full border border-border/60 bg-background px-3.5 py-2 text-left sm:text-center text-sm text-foreground/90 hover:bg-muted/80 hover:border-border transition-colors shadow-sm max-w-[20rem] sm:max-w-none"
                    >
                      {chip.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((message, idx) => {
              const isLastAssistant =
                message.role === "assistant" && idx === messages.length - 1 && !isLoading
              return (
                <MessageBubble
                  key={message.id}
                  message={message}
                  appearance={bubbleAppearance}
                  onRegenerate={isLastAssistant ? () => handleRegenerateAssistant(idx) : undefined}
                />
              )
            })}
          </div>
        </div>

        {isLoading && (
          <div
            className="shrink-0 w-full flex flex-col min-h-0 border-t border-border/50 bg-muted/20 dark:bg-muted/10"
            role="status"
            aria-live="polite"
            aria-label="Agent progress"
          >
            <div
              role="separator"
              aria-orientation="horizontal"
              aria-label="Resize agent progress panel"
              onPointerDown={(e) => {
                e.preventDefault()
                progressStripDragRef.current = {
                  startY: e.clientY,
                  startH: progressStripHeightRef.current,
                }
                ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
              }}
              onPointerMove={(e) => {
                const d = progressStripDragRef.current
                if (!d || !e.buttons) return
                const delta = d.startY - e.clientY
                const next = Math.min(560, Math.max(120, d.startH + delta))
                progressStripHeightRef.current = next
                setProgressStripHeightPx(next)
              }}
              onPointerUp={(e) => {
                progressStripDragRef.current = null
                try {
                  sessionStorage.setItem(PROGRESS_STRIP_H_KEY, String(progressStripHeightRef.current))
                } catch {
                  /* ignore */
                }
                try {
                  ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
                } catch {
                  /* ignore */
                }
              }}
              onPointerCancel={(e) => {
                progressStripDragRef.current = null
                try {
                  ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
                } catch {
                  /* ignore */
                }
              }}
              className="h-2 w-full cursor-row-resize shrink-0 touch-none border-b border-border/30 bg-muted/40 hover:bg-muted/60 flex items-center justify-center group"
            >
              <span className="h-1 w-10 rounded-full bg-border group-hover:bg-muted-foreground/40" />
            </div>
            <div
              ref={progressStripRef}
              style={{ height: progressStripHeightPx }}
              className={cn(
                "min-h-0 w-full overflow-y-auto overflow-x-hidden overscroll-y-contain",
                "[scrollbar-gutter:stable]",
              )}
            >
            <div className={cn("mx-auto w-full", isEnterprise ? "max-w-3xl px-4 sm:px-8 py-3" : "max-w-5xl px-4 sm:px-6 py-3")}>
              <QueryProcessingPanel
                leading={
                  <div className="h-8 w-8 rounded-lg bg-muted flex items-center justify-center">
                    <div className="h-4 w-4 border-2 border-muted-foreground/20 border-t-muted-foreground rounded-full animate-spin" />
                  </div>
                }
                querySteps={querySteps}
                currentStep={currentStep}
                deepResearchTimeline={deepResearchTimeline}
                deepResearchSlideIndex={deepResearchSlideIndex}
                onDeepResearchSlideIndexChange={setDeepResearchSlideIndex}
                queryProgressMode="live"
                graphPlanSummary={liveGraphPlanSummary}
                executionTrace={liveExecutionTrace.length > 0 ? liveExecutionTrace : undefined}
              />
            </div>
            </div>
          </div>
        )}
      </div>

      <div
        className={cn(
          "flex-shrink-0 w-full",
          isEnterprise
            ? "px-4 sm:px-8 pb-6 pt-2 bg-gradient-to-t from-[#fafafa] to-transparent dark:from-background"
            : "px-4 sm:px-6 py-3 border-t border-border/40 bg-card/30",
        )}
      >
        <div className={cn("w-full space-y-2", !isEnterprise && "max-w-5xl mx-auto")}>
          {enableDocumentContext && sessionDocuments.length > 0 && (
            <div className="flex flex-wrap gap-2 items-center justify-center sm:justify-start">
              <span className="text-xs font-medium text-muted-foreground">Session context:</span>
              {sessionDocuments.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-1.5 px-2.5 py-1 bg-secondary rounded-full text-xs text-foreground border border-border/40"
                >
                  <span className="truncate max-w-[200px]">{doc.filename}</span>
                  <button
                    type="button"
                    className="text-muted-foreground hover:text-foreground"
                    aria-label={`Remove ${doc.filename}`}
                    onClick={() => setSessionDocuments((prev) => prev.filter((d) => d.id !== doc.id))}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
          <ChatInput
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            placeholder={
              isEnterprise ? "Ask anything or upload documents for full multi-source analysis…" : inputPlaceholder
            }
            fileAccept={fileAccept}
            variant={isEnterprise ? "enterprise" : "default"}
            composeRequest={composeRequest}
            deepResearch={{
              checked: deepResearchEnabled,
              onCheckedChange: setDeepResearchEnabled,
            }}
          />
        </div>
      </div>

      <AlertDialog open={sessionDeleteDialogOpen} onOpenChange={setSessionDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this chat?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the session and its history. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => void handleConfirmDeleteSession()}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {isEnterprise && (
        <p className="text-center text-[11px] text-muted-foreground/80 pb-3 px-4 shrink-0">
          Generative AI may produce inaccurate or incomplete regulatory information. Verify against official sources.
        </p>
      )}
    </div>
  )
}
