import { describe, expect, it } from "vitest"
import {
  buildCitationThinkingEntry,
  extractUrlKeysFromMarkdown,
  filterCitationsForFooter,
  normalizeChatCitations,
  normalizeCitationUrlKey,
} from "./chat-citations"

describe("normalizeCitationUrlKey", () => {
  it("normalizes host, path, and trailing slash", () => {
    expect(normalizeCitationUrlKey("https://ClinicalTrials.gov/study/NCT01234567/")).toBe(
      "clinicaltrials.gov/study/nct01234567",
    )
  })
})

describe("filterCitationsForFooter", () => {
  it("hides citations whose URL is only used as an inline Markdown link", () => {
    const md =
      "See [the trial](https://clinicaltrials.gov/study/NCT01234567) for details. No bare URL."
    const items = normalizeChatCitations([
      { text: "NCT01234567", url: "https://clinicaltrials.gov/study/NCT01234567" },
    ])
    expect(filterCitationsForFooter(md, items)).toEqual([])
  })

  it("keeps citations when the same URL appears in the body but not as a markdown link target", () => {
    const md = "Registry: https://clinicaltrials.gov/study/NCT01234567"
    const items = normalizeChatCitations([
      { text: "NCT01234567", url: "https://clinicaltrials.gov/study/NCT01234567" },
    ])
    const out = filterCitationsForFooter(md, items)
    expect(out).toHaveLength(1)
    expect(out[0].url).toContain("NCT01234567")
  })

  it("keeps a citation when NCT appears in the answer text even if URL is not pasted", () => {
    const md = "Enrollment is defined in **NCT01234567** protocol."
    const items = normalizeChatCitations([
      { text: "Phase 3 lung trial", url: "https://clinicaltrials.gov/study/NCT01234567" },
    ])
    expect(filterCitationsForFooter(md, items)).toHaveLength(1)
  })

  it("drops citations with no connection to the body", () => {
    const md = "General discussion with no identifiers."
    const items = normalizeChatCitations([
      { text: "Other trial", url: "https://clinicaltrials.gov/study/NCT09999999" },
    ])
    expect(filterCitationsForFooter(md, items)).toEqual([])
  })

  it("dedupes by normalized URL", () => {
    const md = "Links https://fda.gov/foo and more."
    const items = normalizeChatCitations([
      { text: "a", url: "https://fda.gov/foo" },
      { text: "b", url: "https://www.fda.gov/foo/" },
    ])
    expect(filterCitationsForFooter(md, items)).toHaveLength(1)
  })
})

describe("buildCitationThinkingEntry", () => {
  it("includes counts, host summary, and raw markdown links", () => {
    const md = "Discussed in [PubMed entry](https://pubmed.ncbi.nlm.nih.gov/12345678/)."
    const items = normalizeChatCitations([
      { text: "Paper A", url: "https://pubmed.ncbi.nlm.nih.gov/12345678/" },
      { text: "Trial B", url: "https://clinicaltrials.gov/study/NCT01234567" },
    ])
    const footer = filterCitationsForFooter(md, items)
    const entry = buildCitationThinkingEntry(md, items, footer)
    expect(entry.title).toContain("Sources")
    expect(entry.thinkingLines.some((l) => l.includes("2"))).toBe(true)
    expect(entry.bullets.some((b) => b.includes("Paper A"))).toBe(true)
    expect(entry.bullets.some((b) => b.includes("pubmed.ncbi.nlm.nih.gov"))).toBe(true)
    expect(entry.bullets.some((b) => b.includes("clinicaltrials.gov"))).toBe(true)
  })

  it("still builds an entry when there are no citations", () => {
    const entry = buildCitationThinkingEntry("Hello.", [], [])
    expect(entry.thinkingLines.length).toBeGreaterThan(0)
    expect(entry.bullets.length).toBe(0)
  })
})

describe("extractUrlKeysFromMarkdown", () => {
  it("counts distinct normalized URLs", () => {
    const keys = extractUrlKeysFromMarkdown(
      "See https://Foo.COM/a and https://www.foo.com/a/ again.",
    )
    expect(keys.size).toBe(1)
  })
})
