/**
 * Coerce API/WebSocket citation payloads into { text, url } for the chat UI.
 * Backend sends CitationLink[]; older payloads may be plain strings.
 */
export type CitationItem = { text: string; url: string }

const URL_RE = /https?:\/\/[^\s\|\]\)\"'<>]+/i

function stripTrailingPunct(url: string): string {
  return url.replace(/[)\].,'\"»]+$/, "")
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
