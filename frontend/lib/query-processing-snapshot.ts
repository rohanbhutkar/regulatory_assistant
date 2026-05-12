import type {
  DeepResearchTimelineEntry,
  QueryProcessingExecutionTraceEntry,
  QueryProcessingGraphPlanNodeSummary,
  QueryProcessingSnapshot,
  QueryStep,
  QueryStepDetail,
} from "@/lib/types/chat-types"
import { QUERY_PROCESSING_VERSION } from "@/lib/types/chat-types"

export type {
  DeepResearchTimelineEntry,
  QueryProcessingSnapshot,
  QueryStep,
} from "@/lib/types/chat-types"

export { QUERY_PROCESSING_VERSION }

/** Postgres / API metadata budgets — align with WS client slices (e.g. DR −40) and citation caps. */
export const QP_PERSIST_MAX_QUERY_STEPS = 60
export const QP_PERSIST_MAX_DR_ENTRIES = 40
export const QP_PERSIST_MAX_GRAPH_NODES = 80
export const QP_PERSIST_STR = 4000
export const QP_PERSIST_TITLE = 500
export const QP_PERSIST_STEP_NAME = 500
export const QP_PERSIST_STEP_DESC = 2000
export const QP_PERSIST_STEP_ID = 256
export const QP_PERSIST_AGENT = 128
export const QP_PERSIST_MAX_THINKING = 24
export const QP_PERSIST_MAX_BULLETS = 24
export const QP_PERSIST_REASONING = 4000
export const QP_PERSIST_NODE_DESC = 800
export const QP_PERSIST_MAX_EXEC_TRACE = 80
export const QP_PERSIST_EXEC_TRACE_STR = 1200
export const QP_PERSIST_STEP_SEARCH_QUERY = 800
export const QP_PERSIST_STEP_SOURCE = 128
export const QP_PERSIST_STEP_RESULT_SUMMARY = 500

function trimExecutionTrace(raw: unknown): QueryProcessingExecutionTraceEntry[] | undefined {
  if (!Array.isArray(raw) || raw.length === 0) return undefined
  const keys = new Set([
    "node_id",
    "node_type",
    "status",
    "start_time",
    "end_time",
    "description",
    "error",
    "success",
    "search_query_used",
    "search_source",
    "result_count",
    "result_summary",
  ])
  const out: QueryProcessingExecutionTraceEntry[] = []
  for (const ent of raw) {
    if (!ent || typeof ent !== "object") continue
    const e = ent as Record<string, unknown>
    const row: QueryProcessingExecutionTraceEntry = {}
    for (const k of keys) {
      if (!(k in e)) continue
      const v = e[k]
      if (k === "result_count" && typeof v === "number" && Number.isFinite(v)) {
        row.result_count = v
        continue
      }
      if (k === "success" && typeof v === "boolean") {
        row.success = v
        continue
      }
      if (typeof v === "string") {
        const s = v.slice(0, QP_PERSIST_EXEC_TRACE_STR)
        if (k === "node_id") row.node_id = s.slice(0, QP_PERSIST_STEP_ID)
        else if (k === "node_type") row.node_type = s.slice(0, 128)
        else if (k === "status") row.status = s.slice(0, 64)
        else if (k === "start_time") row.start_time = s.slice(0, 64)
        else if (k === "end_time") row.end_time = s.slice(0, 64)
        else if (k === "description") row.description = s
        else if (k === "error") row.error = s
        else if (k === "search_query_used") row.search_query_used = s.slice(0, QP_PERSIST_STEP_SEARCH_QUERY)
        else if (k === "search_source") row.search_source = s.slice(0, QP_PERSIST_STEP_SOURCE)
        else if (k === "result_summary") row.result_summary = s.slice(0, QP_PERSIST_STEP_RESULT_SUMMARY)
      }
    }
    if (Object.keys(row).length) out.push(row)
  }
  if (out.length === 0) return undefined
  return out.slice(-QP_PERSIST_MAX_EXEC_TRACE)
}

/** Merge one WebSocket `node_progress` payload into a running trace (shape-aligned with server `execution_trace`). */
export function upsertExecutionTraceFromNodeProgress(
  prev: QueryProcessingExecutionTraceEntry[],
  nodeData: Record<string, unknown>,
): QueryProcessingExecutionTraceEntry[] {
  const slice = trimExecutionTrace([nodeData])
  const row = slice?.[0]
  if (!row || !row.node_id) return prev
  const next = [...prev]
  const idx = next.findIndex((e) => e.node_id === row.node_id)
  if (idx < 0) next.push(row)
  else next[idx] = { ...next[idx], ...row }
  return next.slice(-QP_PERSIST_MAX_EXEC_TRACE)
}

function trimGraphPlanSummary(graphPlan: unknown): QueryProcessingSnapshot["graph_plan_summary"] | undefined {
  if (!graphPlan || typeof graphPlan !== "object") return undefined
  const gp = graphPlan as Record<string, unknown>
  const rawNodes = gp.nodes
  const reasoningRaw = typeof gp.reasoning === "string" ? gp.reasoning.slice(0, QP_PERSIST_REASONING) : undefined
  const reasoning = reasoningRaw?.trim() ? reasoningRaw : undefined
  const nodes: QueryProcessingGraphPlanNodeSummary[] = []
  if (Array.isArray(rawNodes)) {
    for (const raw of rawNodes.slice(0, 120)) {
      if (!raw || typeof raw !== "object") continue
      const n = raw as Record<string, unknown>
      const id = typeof n.id === "string" ? n.id : ""
      const type = typeof n.type === "string" ? n.type : "unknown"
      const desc = typeof n.description === "string" ? n.description : ""
      const agentType = typeof n.agent_type === "string" ? n.agent_type : undefined
      if (!id) continue
      const row: QueryProcessingGraphPlanNodeSummary = {
        id: id.slice(0, 256),
        type: type.slice(0, 128),
        description: desc.slice(0, QP_PERSIST_NODE_DESC),
      }
      if (agentType) row.agent_type = agentType.slice(0, QP_PERSIST_AGENT)
      nodes.push(row)
    }
  }
  if (nodes.length > 0) {
    return { nodes, ...(reasoning ? { reasoning } : {}) }
  }
  if (reasoning) {
    return { nodes: [], reasoning }
  }
  return undefined
}

/** Public helper: graph plan → persisted-style summary for live panels. */
export function graphPlanToProcessingSummary(
  graphPlan: unknown,
): QueryProcessingSnapshot["graph_plan_summary"] | undefined {
  return trimGraphPlanSummary(graphPlan)
}

function cloneQuerySteps(steps: QueryStep[]): QueryStep[] {
  return steps.map((s) => ({
    id: s.id,
    name: s.name,
    description: s.description,
    status: s.status,
    agent: s.agent,
    ...(s.detail ? { detail: { ...s.detail } } : {}),
  }))
}

function cloneDrTimeline(entries: DeepResearchTimelineEntry[]): DeepResearchTimelineEntry[] {
  return entries.map((e) => ({
    key: e.key,
    title: e.title,
    timestamp: e.timestamp,
    thinkingLines: [...e.thinkingLines],
    bullets: [...e.bullets],
  }))
}

/** Build `metadata.query_processing` before clearing live step / DR state. */
export function buildQueryProcessingSnapshot(args: {
  querySteps: QueryStep[]
  deepResearchTimeline: DeepResearchTimelineEntry[]
  graphPlan?: unknown
  executionTrace?: unknown
}): QueryProcessingSnapshot | undefined {
  const graph_plan_summary = trimGraphPlanSummary(args.graphPlan)
  const execution_trace = trimExecutionTrace(args.executionTrace)
  const hasSteps = args.querySteps.length > 0
  const hasDr = args.deepResearchTimeline.length > 0
  if (!hasSteps && !hasDr && !graph_plan_summary && !execution_trace?.length) return undefined
  return {
    version: QUERY_PROCESSING_VERSION,
    query_steps: cloneQuerySteps(args.querySteps),
    deep_research_timeline: cloneDrTimeline(args.deepResearchTimeline),
    graph_plan_summary,
    ...(execution_trace?.length ? { execution_trace } : {}),
  }
}

/** Coerce JSON from DB / localStorage into a snapshot (best-effort). */
export function parseQueryProcessingSnapshot(raw: unknown): QueryProcessingSnapshot | undefined {
  if (!raw || typeof raw !== "object") return undefined
  const o = raw as Record<string, unknown>
  const ver = o.version
  if (typeof ver !== "number" || ver < 1) return undefined

  const stepsRaw = o.query_steps
  const drRaw = o.deep_research_timeline
  const stepsArr = Array.isArray(stepsRaw) ? stepsRaw : []
  const drArr = Array.isArray(drRaw) ? drRaw : []

  const query_steps: QueryStep[] = []
  for (const s of stepsArr) {
    if (!s || typeof s !== "object") continue
    const r = s as Record<string, unknown>
    const status = r.status
    const st =
      status === "pending" || status === "in-progress" || status === "completed" || status === "error"
        ? status
        : "pending"
    const detailRaw = r.detail
    let detail: QueryStepDetail | undefined
    if (detailRaw && typeof detailRaw === "object") {
      const d = detailRaw as Record<string, unknown>
      detail = {}
      if (typeof d.search_query_used === "string") detail.search_query_used = d.search_query_used
      if (typeof d.search_source === "string") detail.search_source = d.search_source
      if (typeof d.result_count === "number" && Number.isFinite(d.result_count)) detail.result_count = d.result_count
      if (typeof d.result_summary === "string") detail.result_summary = d.result_summary
      if (typeof d.error === "string") detail.error = d.error
      if (Object.keys(detail).length === 0) detail = undefined
    }
    query_steps.push({
      id: String(r.id ?? ""),
      name: String(r.name ?? ""),
      description: String(r.description ?? ""),
      status: st,
      agent: String(r.agent ?? ""),
      ...(detail ? { detail } : {}),
    })
  }

  const deep_research_timeline: DeepResearchTimelineEntry[] = []
  for (const e of drArr) {
    if (!e || typeof e !== "object") continue
    const r = e as Record<string, unknown>
    const rawTl = r.thinkingLines ?? r.thinking_lines
    const rawBl = r.bullets
    const tl = Array.isArray(rawTl) ? rawTl.filter((x): x is string => typeof x === "string") : []
    const bl = Array.isArray(rawBl) ? rawBl.filter((x): x is string => typeof x === "string") : []
    deep_research_timeline.push({
      key: String(r.key ?? `k-${deep_research_timeline.length}`),
      title: String(r.title ?? ""),
      timestamp: typeof r.timestamp === "string" ? r.timestamp : undefined,
      thinkingLines: tl,
      bullets: bl,
    })
  }

  let graph_plan_summary: QueryProcessingSnapshot["graph_plan_summary"]
  const gps = o.graph_plan_summary
  if (gps && typeof gps === "object") {
    const g = gps as Record<string, unknown>
    const nn = g.nodes
    if (Array.isArray(nn) && nn.length) {
      const nodes: QueryProcessingGraphPlanNodeSummary[] = []
      for (const n of nn) {
        if (!n || typeof n !== "object") continue
        const x = n as Record<string, unknown>
        const row: QueryProcessingGraphPlanNodeSummary = {
          id: String(x.id ?? ""),
          type: String(x.type ?? ""),
          description: String(x.description ?? ""),
        }
        if (typeof x.agent_type === "string") row.agent_type = x.agent_type
        nodes.push(row)
      }
      graph_plan_summary = {
        nodes,
        reasoning: typeof g.reasoning === "string" ? g.reasoning : undefined,
      }
    } else if (typeof g.reasoning === "string" && g.reasoning.trim()) {
      graph_plan_summary = { nodes: [], reasoning: g.reasoning }
    }
  }

  const execution_trace = trimExecutionTrace(o.execution_trace)

  if (
    query_steps.length === 0 &&
    deep_research_timeline.length === 0 &&
    !graph_plan_summary &&
    !execution_trace?.length
  ) {
    return undefined
  }

  return {
    version: Number(o.version) || QUERY_PROCESSING_VERSION,
    query_steps,
    deep_research_timeline,
    graph_plan_summary,
    ...(execution_trace?.length ? { execution_trace } : {}),
  }
}

/** Size-bounded `query_processing` for `chatCompleteTurn` / Postgres. */
export function slimQueryProcessingForPersist(raw: unknown): Record<string, unknown> | undefined {
  const snap = parseQueryProcessingSnapshot(raw)
  if (!snap) return undefined

  const query_steps = snap.query_steps.slice(0, QP_PERSIST_MAX_QUERY_STEPS).map((s) => {
    const base: Record<string, unknown> = {
      id: s.id.slice(0, QP_PERSIST_STEP_ID),
      name: s.name.slice(0, QP_PERSIST_STEP_NAME),
      description: s.description.slice(0, QP_PERSIST_STEP_DESC),
      status: s.status,
      agent: s.agent.slice(0, QP_PERSIST_AGENT),
    }
    if (s.detail && Object.keys(s.detail).length) {
      const d = s.detail
      base.detail = {
        ...(d.search_query_used !== undefined
          ? { search_query_used: d.search_query_used.slice(0, QP_PERSIST_STEP_SEARCH_QUERY) }
          : {}),
        ...(d.search_source !== undefined
          ? { search_source: d.search_source.slice(0, QP_PERSIST_STEP_SOURCE) }
          : {}),
        ...(d.result_count !== undefined ? { result_count: d.result_count } : {}),
        ...(d.result_summary !== undefined
          ? { result_summary: d.result_summary.slice(0, QP_PERSIST_STEP_RESULT_SUMMARY) }
          : {}),
        ...(d.error !== undefined ? { error: d.error.slice(0, QP_PERSIST_STEP_RESULT_SUMMARY) } : {}),
      }
    }
    return base
  })

  const deep_research_timeline = snap.deep_research_timeline.slice(-QP_PERSIST_MAX_DR_ENTRIES).map((e) => ({
    key: e.key.slice(0, 128),
    title: e.title.slice(0, QP_PERSIST_TITLE),
    timestamp: e.timestamp !== undefined ? e.timestamp.slice(0, 64) : undefined,
    thinkingLines: e.thinkingLines
      .slice(0, QP_PERSIST_MAX_THINKING)
      .map((t) => t.slice(0, QP_PERSIST_STR)),
    bullets: e.bullets.slice(0, QP_PERSIST_MAX_BULLETS).map((b) => b.slice(0, QP_PERSIST_STR)),
  }))

  const out: Record<string, unknown> = {
    version: snap.version,
    query_steps,
    deep_research_timeline,
  }

  const gpsSnap = snap.graph_plan_summary
  if (gpsSnap) {
    const hasNodes = gpsSnap.nodes?.length
    const reasoningOnly =
      typeof gpsSnap.reasoning === "string" && gpsSnap.reasoning.trim().length > 0
    if (hasNodes) {
      out.graph_plan_summary = {
        nodes: gpsSnap.nodes.slice(0, QP_PERSIST_MAX_GRAPH_NODES).map((n) => ({
          id: n.id.slice(0, QP_PERSIST_STEP_ID),
          type: n.type.slice(0, QP_PERSIST_AGENT),
          description: n.description.slice(0, QP_PERSIST_NODE_DESC),
          ...(n.agent_type !== undefined ? { agent_type: n.agent_type.slice(0, QP_PERSIST_AGENT) } : {}),
        })),
        ...(gpsSnap.reasoning
          ? { reasoning: gpsSnap.reasoning.slice(0, QP_PERSIST_REASONING) }
          : {}),
      }
    } else if (reasoningOnly) {
      out.graph_plan_summary = {
        nodes: [],
        reasoning: gpsSnap.reasoning!.slice(0, QP_PERSIST_REASONING),
      }
    }
  }

  if (snap.execution_trace?.length) {
    out.execution_trace = snap.execution_trace.slice(-QP_PERSIST_MAX_EXEC_TRACE).map((row) => {
      const e: Record<string, unknown> = {}
      if (row.node_id !== undefined) e.node_id = String(row.node_id).slice(0, QP_PERSIST_STEP_ID)
      if (row.node_type !== undefined) e.node_type = String(row.node_type).slice(0, 128)
      if (row.status !== undefined) e.status = String(row.status).slice(0, 64)
      if (row.start_time !== undefined) e.start_time = String(row.start_time).slice(0, 64)
      if (row.end_time !== undefined) e.end_time = String(row.end_time).slice(0, 64)
      if (row.description !== undefined)
        e.description = String(row.description).slice(0, QP_PERSIST_EXEC_TRACE_STR)
      if (row.error !== undefined) e.error = String(row.error).slice(0, QP_PERSIST_EXEC_TRACE_STR)
      if (row.success !== undefined) e.success = row.success
      if (row.search_query_used !== undefined)
        e.search_query_used = String(row.search_query_used).slice(0, QP_PERSIST_STEP_SEARCH_QUERY)
      if (row.search_source !== undefined)
        e.search_source = String(row.search_source).slice(0, QP_PERSIST_STEP_SOURCE)
      if (row.result_count !== undefined) e.result_count = row.result_count
      if (row.result_summary !== undefined)
        e.result_summary = String(row.result_summary).slice(0, QP_PERSIST_STEP_RESULT_SUMMARY)
      return e
    })
  }

  return out
}
