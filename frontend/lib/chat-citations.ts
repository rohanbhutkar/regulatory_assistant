import type { DeepResearchTimelineEntry } from "@/lib/types/chat-types"

/**
 * Coerce API/WebSocket citation payloads into { text, url } for the chat UI.
 * Backend sends CitationLink[]; older payloads may be plain strings.
 */
export type CitationItem = { text: string; url: string }

const URL_RE = /https?:\/\/[^\s\|\]\)\"'<>]+/i

/** Markdown inline links: `[label](url)` */
const MD_LINK_URL_RE = /\[[^\]]*\]\((https?:\/\/[^)\s]+)\)/gi

const RAW_URL_RE = /https?:\/\/[^\s|\]\)"'<>]+/gi

const NCT_RE = /\bNCT\d{8}\b/gi

function stripTrailingPunct(url: string): string {
  return url.replace(/[)\].,'\"»]+$/, "")
}

/** Stable key for deduping / matching URLs across the answer and citation list. */
export function normalizeCitationUrlKey(url: string): string {
  const cleaned = stripTrailingPunct(url.trim())
  if (!cleaned) return ""
  try {
    const u = new URL(cleaned.startsWith("http") ? cleaned : `https://${cleaned}`)
    const host = u.hostname.replace(/^www\./i, "").toLowerCase()
    let path = u.pathname.replace(/\/+$/, "") || ""
    const search = u.search || ""
    return `${host}${path}${search}`.toLowerCase()
  } catch {
    return cleaned.toLowerCase()
  }
}

export function extractUrlKeysFromMarkdown(md: string): Set<string> {
  const keys = new Set<string>()
  if (!md) return keys
  for (const m of md.matchAll(RAW_URL_RE)) {
    const k = normalizeCitationUrlKey(m[0])
    if (k) keys.add(k)
  }
  return keys
}

/** URLs that already appear as clickable `[text](url)` in the body — hide from footer to reduce clutter. */
function extractInlineMarkdownLinkUrlKeys(md: string): Set<string> {
  const keys = new Set<string>()
  if (!md) return keys
  for (const m of md.matchAll(MD_LINK_URL_RE)) {
    const k = normalizeCitationUrlKey(m[1])
    if (k) keys.add(k)
  }
  return keys
}

/**
 * Replace `[label](url)` with `label ` so identifiers embedded only in the URL
 * (not meant to be read as in-line citations) do not count as "referenced".
 */
function bodyPlainForIdMatching(md: string): string {
  return md.replace(/\[[^\]]*\]\((https?:\/\/[^)]+)\)/gi, (full) => {
    const m = full.match(/^\[([^\]]*)\]\((https?:\/\/[^)]+)\)/i)
    return m ? `${m[1]} ` : " "
  })
}

function extractNctIds(s: string): string[] {
  const out: string[] = []
  for (const m of s.matchAll(NCT_RE)) {
    out.push(m[0].toUpperCase())
  }
  return [...new Set(out)]
}

function extractPmids(s: string): string[] {
  const fromLabel = [...s.matchAll(/\bPMID[:\s]*(\d{7,9})\b/gi)].map((x) => x[1])
  const fromUrl = [...s.matchAll(/pubmed\.ncbi\.nlm\.nih\.gov\/(\d{7,9})\b/gi)].map((x) => x[1])
  return [...new Set([...fromLabel, ...fromUrl])]
}

function pmidReferencedInBody(pmid: string, body: string): boolean {
  const b = body.toLowerCase()
  return (
    b.includes(`pubmed.ncbi.nlm.nih.gov/${pmid}`) ||
    b.includes(`pubmed.ncbi.nlm.nih.gov/${pmid}/`) ||
    b.includes(`pmid:${pmid}`) ||
    b.includes(`pmid ${pmid}`) ||
    b.includes(`pmid=${pmid}`)
  )
}

function nctReferencedInBody(nct: string, body: string): boolean {
  return body.toUpperCase().includes(nct.toUpperCase())
}

/**
 * Keep only citations that are actually used in the answer, and drop URLs that are
 * already shown as Markdown links in the body (avoids duplicate link rows).
 *
 * @param markdown - assistant message markdown (same string rendered above the footer)
 * @param items - already normalized citations
 * @param max - hard cap after filtering (safety)
 */
export function filterCitationsForFooter(
  markdown: string,
  items: CitationItem[],
  max = 28,
): CitationItem[] {
  const body = markdown || ""
  const bodyUrlKeys = extractUrlKeysFromMarkdown(body)
  const inlineLinkKeys = extractInlineMarkdownLinkUrlKeys(body)
  const bodyLower = body.toLowerCase()
  const bodyForIds = bodyPlainForIdMatching(body)

  const out: CitationItem[] = []
  const pushedDedupe = new Set<string>()

  for (const c of items) {
    let keep = false

    const haystack = `${c.text}\n${c.url}`

    if (c.url.trim()) {
      const key = normalizeCitationUrlKey(c.url)
      if (key && bodyUrlKeys.has(key)) {
        if (inlineLinkKeys.has(key)) {
          continue
        }
        keep = true
      }
    }

    if (!keep) {
      for (const nct of extractNctIds(haystack)) {
        if (nctReferencedInBody(nct, bodyForIds)) {
          keep = true
          break
        }
      }
    }

    if (!keep) {
      for (const pmid of extractPmids(haystack)) {
        if (pmidReferencedInBody(pmid, bodyForIds)) {
          keep = true
          break
        }
      }
    }

    // Text-only / odd payloads: long label quoted verbatim in the answer
    if (!keep && !c.url.trim() && c.text.trim().length >= 14) {
      const t = c.text.trim().toLowerCase()
      const prefix = t.slice(0, Math.min(96, t.length))
      if (prefix.length >= 14 && bodyLower.includes(prefix)) {
        keep = true
      }
    }

    if (!keep) continue

    // Drop rows whose URL is already a clickable inline link in the body (any match path).
    if (c.url.trim() && inlineLinkKeys.has(normalizeCitationUrlKey(c.url))) {
      continue
    }

    const dedupeKey = c.url.trim()
      ? normalizeCitationUrlKey(c.url)
      : `text:${c.text.trim().slice(0, 120).toLowerCase()}`
    if (pushedDedupe.has(dedupeKey)) continue
    pushedDedupe.add(dedupeKey)

    out.push(c)
    if (out.length >= max) break
  }

  return out
}

const CITATION_THINKING_MAX_LIST = 22

function safeMarkdownLinkLabel(text: string, max = 120): string {
  const t = text.replace(/\s+/g, " ").trim().slice(0, max)
  return (t || "Source").replace(/\[/g, "(").replace(/\]/g, ")")
}

function summarizeHostsFromCitations(items: CitationItem[]): string {
  const m = new Map<string, number>()
  for (const c of items) {
    if (!c.url.trim()) continue
    try {
      const host = new URL(c.url.trim().startsWith("http") ? c.url.trim() : `https://${c.url.trim()}`)
        .hostname.replace(/^www\./i, "")
        .toLowerCase()
      m.set(host, (m.get(host) || 0) + 1)
    } catch {
      /* skip bad URLs */
    }
  }
  return [...m.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([h, n]) => `${h} ×${n}`)
    .join(", ")
}

/**
 * One “Agent thinking” slide: narrative + full pre-filter source list for transparency.
 */
export function buildCitationThinkingEntry(
  answerMarkdown: string,
  allNormalized: CitationItem[],
  footerShown: CitationItem[],
): DeepResearchTimelineEntry {
  const nAll = allNormalized.length
  const nFooter = footerShown.length
  const hosts = summarizeHostsFromCitations(allNormalized)
  const urlKeysInAnswer = extractUrlKeysFromMarkdown(answerMarkdown).size

  const thinkingLines: string[] = []
  if (nAll === 0) {
    thinkingLines.push(
      "No structured citation objects were returned with this synthesis (sources may still appear only as plain text or Markdown links in the answer).",
    )
  } else {
    thinkingLines.push(
      `The synthesis payload included **${nAll}** source row${nAll === 1 ? "" : "s"} (short labels plus optional URLs).`,
    )
    thinkingLines.push(
      `The answer body contains roughly **${urlKeysInAnswer}** distinct URL string(s) after normalization — those are used together with visible NCT/PMID tokens when deciding what belongs in the compact footer.`,
    )
    if (nFooter !== nAll) {
      thinkingLines.push(
        `**Footer after relevance rules:** **${nFooter}** row${nFooter === 1 ? "" : "s"}. Rows drop out when they are not echoed in the prose, duplicate another row, or repeat a URL that is already an inlined \`[text](url)\` link in the answer.`,
      )
    } else {
      thinkingLines.push(
        `All **${nFooter}** structured source row${nFooter === 1 ? "" : "s"} passed the footer checks for this reply (or the model only returned that many).`,
      )
    }
    if (hosts) {
      thinkingLines.push(`**Host mix in the raw list:** ${hosts}`)
    }
  }

  const bullets: string[] = []
  if (nAll > 0) {
    bullets.push(
      `**Full list from the model (${nAll}) — pre–footer filter.** The bubble footer shows the relevance-filtered subset (${nFooter}).`,
    )
    for (const c of allNormalized.slice(0, CITATION_THINKING_MAX_LIST)) {
      const label = safeMarkdownLinkLabel(c.text || c.url || "Source")
      if (c.url.trim()) {
        bullets.push(`- [${label}](${c.url.trim()})`)
      } else {
        bullets.push(`- ${label}`)
      }
    }
    if (nAll > CITATION_THINKING_MAX_LIST) {
      bullets.push(
        `- _…and **${nAll - CITATION_THINKING_MAX_LIST}** more not shown in this card (cap ${CITATION_THINKING_MAX_LIST})._`,
      )
    }
  }

  return {
    key: `dr-citations-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    title: "Sources & citations (evidence trail)",
    timestamp: new Date().toISOString(),
    thinkingLines,
    bullets,
  }
}

export function normalizeChatCitations(raw: unknown): CitationItem[] {
  if (!Array.isArray(raw)) return []

  const out: CitationItem[] = []
  for (const item of raw) {
    if (item !== null && typeof item === "object" && "text" in item) {
      const o = item as { text?: unknown; url?: unknown }
      const text = String(o.text ?? "").trim()
      const url = String(o.url ?? "").trim()
      if (!text && !url) continue
      out.push({ text: text || url, url })
      continue
    }
    if (typeof item === "string") {
      const s = item.trim()
      if (!s) continue
      const m = s.match(URL_RE)
      const url = m ? stripTrailingPunct(m[0]) : ""
      let text = s
      if (url) {
        text = s
          .replace(url, "")
          .replace(/URL:\s*/gi, "")
          .replace(/\|/g, " ")
          .replace(/\s{2,}/g, " ")
          .trim()
      }
      out.push({ text: (text || url).slice(0, 600), url })
    }
  }

  const seen = new Set<string>()
  return out.filter((c) => {
    const k = `${c.url}\0${c.text.slice(0, 120)}`
    if (seen.has(k)) return false
    seen.add(k)
    return true
  })
}
