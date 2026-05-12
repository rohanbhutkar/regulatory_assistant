export interface Message {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  agentName?: string
  agentType?: string
  metadata?: MessageMetadata
}

/** Optional per-step transparency from `node_progress` (search counts, errors, etc.). */
export interface QueryStepDetail {
  search_query_used?: string
  search_source?: string
  result_count?: number
  result_summary?: string
  error?: string
}

/** Single graph execution step (multi-agent query progress). */
export interface QueryStep {
  id: string
  name: string
  description: string
  status: "pending" | "in-progress" | "completed" | "error"
  agent: string
  detail?: QueryStepDetail
}

/** Slim execution trace row (aligned with server `_slim_execution_trace_for_ws`). */
export interface QueryProcessingExecutionTraceEntry {
  node_id?: string
  node_type?: string
  status?: string
  start_time?: string
  end_time?: string
  description?: string
  error?: string
  success?: boolean
  search_query_used?: string
  search_source?: string
  result_count?: number
  result_summary?: string
}

/** One deep-research transparency card (streaming “thinking” timeline). */
export interface DeepResearchTimelineEntry {
  key: string
  title: string
  timestamp?: string
  thinkingLines: string[]
  bullets: string[]
}

export const QUERY_PROCESSING_VERSION = 1

export interface QueryProcessingGraphPlanNodeSummary {
  id: string
  type: string
  description: string
  agent_type?: string
}

export interface QueryProcessingSnapshot {
  version: number
  query_steps: QueryStep[]
  deep_research_timeline: DeepResearchTimelineEntry[]
  /** Trimmed graph plan for replay / audit (not the full server plan). */
  graph_plan_summary?: {
    nodes: QueryProcessingGraphPlanNodeSummary[]
    reasoning?: string
  }
  /** Server-slimmed node timeline (completed / failed steps with optional search fields). */
  execution_trace?: QueryProcessingExecutionTraceEntry[]
}

export interface MessageMetadata {
  references?: Reference[]
  progress?: ProgressUpdate
  attachments?: Attachment[]
  action?: string
  criteria?: string
  isRefinement?: boolean
  /** Structured citations from synthesis (text + optional url) */
  citations?: Array<{ text: string; url?: string }>
  /** Captured query / deep-research UI state when the assistant turn completes */
  query_processing?: QueryProcessingSnapshot
  [key: string]: unknown
}

export interface Reference {
  id: string
  title: string
  source: string
  url?: string
  snippet?: string
}

export interface ProgressUpdate {
  currentStep: number
  totalSteps: number
  stepName: string
  status: "pending" | "in-progress" | "completed" | "error"
}

export interface Attachment {
  id: string
  name: string
  type: string
  size: number
  url: string
}

export interface Agent {
  id: string
  name: string
  description: string
  type: string
  capabilities: string[]
  status: "available" | "busy" | "offline"
}

export interface ChatSession {
  id: string
  personaId: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
}
