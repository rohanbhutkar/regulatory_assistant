import { describe, expect, it } from "vitest"
import { slimMetadataForChatPersist } from "./chat-persistence-api"
import {
  QUERY_PROCESSING_VERSION,
  QP_PERSIST_MAX_DR_ENTRIES,
  QP_PERSIST_MAX_QUERY_STEPS,
  QP_PERSIST_STR,
} from "./query-processing-snapshot"

describe("slimMetadataForChatPersist", () => {
  it("preserves bounded query_processing", () => {
    const out = slimMetadataForChatPersist({
      confidence: 0.9,
      query_processing: {
        version: QUERY_PROCESSING_VERSION,
        query_steps: [
          {
            id: "n1",
            name: "Search",
            description: "Look up sources",
            status: "completed",
            agent: "search",
            detail: {
              search_query_used: "foo trial",
              result_count: 3,
              result_summary: "3 hits",
            },
          },
        ],
        deep_research_timeline: [
          { key: "dr-1", title: "Brief", thinkingLines: ["line"], bullets: ["• one"] },
        ],
        execution_trace: [
          {
            node_id: "s1",
            node_type: "search",
            status: "completed",
            result_summary: "ok",
          },
        ],
      },
    })
    expect(out.query_processing).toBeDefined()
    const qp = out.query_processing as Record<string, unknown>
    expect(qp.version).toBe(QUERY_PROCESSING_VERSION)
    expect((qp.query_steps as unknown[]).length).toBe(1)
    expect((qp.deep_research_timeline as unknown[]).length).toBe(1)
    const steps = qp.query_steps as Array<{ detail?: { result_summary?: string } }>
    expect(steps[0].detail?.result_summary).toBe("3 hits")
    expect(Array.isArray(qp.execution_trace)).toBe(true)
    expect((qp.execution_trace as unknown[]).length).toBe(1)
  })

  it("truncates query_steps to hard cap", () => {
    const steps = Array.from({ length: QP_PERSIST_MAX_QUERY_STEPS + 12 }, (_, i) => ({
      id: `step-${i}`,
      name: "N",
      description: "D",
      status: "completed" as const,
      agent: "a",
    }))
    const out = slimMetadataForChatPersist({
      query_processing: {
        version: QUERY_PROCESSING_VERSION,
        query_steps: steps,
        deep_research_timeline: [],
      },
    })
    const qp = out.query_processing as Record<string, unknown>
    expect((qp.query_steps as unknown[]).length).toBe(QP_PERSIST_MAX_QUERY_STEPS)
  })

  it("keeps only the last deep_research entries and truncates long strings", () => {
    const long = "z".repeat(QP_PERSIST_STR + 800)
    const entries = Array.from({ length: QP_PERSIST_MAX_DR_ENTRIES + 6 }, (_, i) => ({
      key: `k-${i}`,
      title: `title-${i}`,
      thinkingLines: [long],
      bullets: [long],
    }))
    const out = slimMetadataForChatPersist({
      query_processing: {
        version: QUERY_PROCESSING_VERSION,
        query_steps: [],
        deep_research_timeline: entries,
      },
    })
    const qp = out.query_processing as Record<string, unknown>
    const dr = qp.deep_research_timeline as Array<{ thinkingLines: string[]; bullets: string[]; title: string }>
    expect(dr.length).toBe(QP_PERSIST_MAX_DR_ENTRIES)
    expect(dr[0].thinkingLines[0].length).toBe(QP_PERSIST_STR)
    expect(dr[0].bullets[0].length).toBe(QP_PERSIST_STR)
    expect(dr[0].title).toBe(`title-${entries.length - QP_PERSIST_MAX_DR_ENTRIES}`)
  })

  it("preserves graph_plan_summary with reasoning only", () => {
    const out = slimMetadataForChatPersist({
      query_processing: {
        version: QUERY_PROCESSING_VERSION,
        query_steps: [],
        deep_research_timeline: [],
        graph_plan_summary: { nodes: [], reasoning: "Planner rationale only." },
      },
    })
    const qp = out.query_processing as Record<string, unknown>
    const gps = qp.graph_plan_summary as { nodes: unknown[]; reasoning?: string }
    expect(gps.reasoning).toContain("Planner rationale")
    expect(Array.isArray(gps.nodes)).toBe(true)
    expect(gps.nodes.length).toBe(0)
  })

  it("omits invalid query_processing", () => {
    const out = slimMetadataForChatPersist({
      query_processing: { version: 0, query_steps: [], deep_research_timeline: [] },
    })
    expect(out.query_processing).toBeUndefined()
  })
})
